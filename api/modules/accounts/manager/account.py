# Python
import logging
from datetime import datetime, timezone
from typing import Any

# Libs
from bson import ObjectId
from pymongo import ReturnDocument

# Constants
from constants.accounts_exceptions import UserNotFoundError

# Core
from core.manager import BaseManager

# Module
from modules.accounts.schemas import NotificationSettingsDTO, UserProfileResponse


_logger = logging.getLogger(__name__)

# Defaults applied when a user document is missing a ``settings`` sub-doc
# (e.g. legacy rows written before the schema change). New users get the
# same defaults explicitly written at registration by ``UserManager.create``.
_DEFAULT_ALLOW_EMAIL = True
_DEFAULT_ALLOW_SMS = False


def _settings_from_doc(doc: dict[str, Any]) -> NotificationSettingsDTO:
    """Project the embedded ``settings`` sub-document into a typed DTO.

    Missing keys fall back to the defaults so the rest of the code never
    has to worry about a partially-populated document — important for
    documents written before the schema migration.
    """
    settings = doc.get("settings") or {}
    return NotificationSettingsDTO(
        allow_email=bool(settings.get("allow_email", _DEFAULT_ALLOW_EMAIL)),
        allow_sms=bool(settings.get("allow_sms", _DEFAULT_ALLOW_SMS)),
    )


def _profile_from_doc(doc: dict[str, Any]) -> UserProfileResponse:
    """Project a User document into the public :class:`UserProfileResponse`."""
    return UserProfileResponse(
        id=str(doc["_id"]),
        first_name=doc["first_name"],
        last_name=doc["last_name"],
        email=doc["email"],
        phone=doc["phone"],
        balance=doc["balance"],
        role=doc["role"],
        settings=_settings_from_doc(doc),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


class AccountManager(BaseManager):
    """Reusable read/write surface for account-level operations.

    Operates on the ``users`` collection (shared with :class:`User`) but
    exposes a narrower, profile-oriented vocabulary intended to be
    consumed by:

    * The HTTP layer (``GET /accounts/me``, settings updates).
    * Other modules that need to **read** lightweight preferences
      (notifications, funds) — they should reach for
      :meth:`can_receive_email` / :meth:`can_receive_sms` rather than
      pulling the whole user document.

    Methods return **DTOs** (Pydantic models) or primitives, never raw
    Motor documents — that's what decouples consumers from the database
    layout. Mutations use atomic ``$set`` operations to avoid lost-update
    races between concurrent toggle requests.
    """

    COLLECTION = "users"

    # ---------- Reads ----------

    async def get_profile(self, user_id: str) -> UserProfileResponse:
        """Return the full public profile for the user with ``user_id``.

        Args:
            user_id: The Mongo ObjectId of the user, as a string.

        Raises:
            UserNotFoundError: When no user matches ``user_id`` (also when
                ``user_id`` is not a valid ObjectId).
        """
        doc = await self._get_doc(user_id)
        return _profile_from_doc(doc)

    async def get_notification_settings(self, user_id: str) -> NotificationSettingsDTO:
        """Return only the notification settings (cheaper than ``get_profile``).

        Use this from notification dispatchers or other read-only consumers
        that don't need the personal fields.

        Raises:
            UserNotFoundError: When ``user_id`` does not match any user.
        """
        doc = await self._get_doc(user_id, projection={"settings": 1})
        return _settings_from_doc(doc)

    # ---------- Writes (atomic) ----------

    async def update_email_notifications(
        self, user_id: str, enabled: bool
    ) -> NotificationSettingsDTO:
        """Toggle ``settings.allow_email`` and return the updated settings.

        The operation is a single atomic ``find_one_and_update`` with
        ``$set`` on the specific nested key — so a concurrent SMS-toggle
        and email-toggle never overwrite each other.

        Args:
            user_id: The user's ObjectId, as a string.
            enabled: New value for ``settings.allow_email``.

        Raises:
            UserNotFoundError: When ``user_id`` does not match any user.
        """
        return await self._set_setting(user_id, "allow_email", enabled)

    async def update_sms_notifications(
        self, user_id: str, enabled: bool
    ) -> NotificationSettingsDTO:
        """Toggle ``settings.allow_sms`` — same contract as :meth:`update_email_notifications`."""
        return await self._set_setting(user_id, "allow_sms", enabled)

    # ---------- Permission helpers (for cross-module consumption) ----------

    async def can_receive_email(self, user_id: str) -> bool:
        """Return ``True`` iff the user opted in to email notifications.

        Defensive contract for cross-module consumers (notifications,
        funds, …): treats a missing/invalid user as "no permission" and
        logs a warning, rather than raising. This way a stale ``user_id``
        does not turn a notification dispatch into a 500.
        """
        return await self._can_receive(user_id, "allow_email", default=_DEFAULT_ALLOW_EMAIL)

    async def can_receive_sms(self, user_id: str) -> bool:
        """Return ``True`` iff the user opted in to SMS notifications. Same contract as :meth:`can_receive_email`."""
        return await self._can_receive(user_id, "allow_sms", default=_DEFAULT_ALLOW_SMS)

    # ---------- Internal helpers ----------

    async def _get_doc(
        self, user_id: str, projection: dict[str, int] | None = None
    ) -> dict[str, Any]:
        if not ObjectId.is_valid(user_id):
            raise UserNotFoundError()
        doc = await self._col().find_one({"_id": ObjectId(user_id)}, projection=projection)
        if doc is None:
            raise UserNotFoundError()
        return doc

    async def _set_setting(
        self, user_id: str, field: str, enabled: bool
    ) -> NotificationSettingsDTO:
        if not ObjectId.is_valid(user_id):
            raise UserNotFoundError()
        updated = await self._col().find_one_and_update(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    f"settings.{field}": enabled,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            projection={"settings": 1},
            return_document=ReturnDocument.AFTER,
        )
        if updated is None:
            raise UserNotFoundError()
        return _settings_from_doc(updated)

    async def _can_receive(self, user_id: str, field: str, *, default: bool) -> bool:
        if not ObjectId.is_valid(user_id):
            _logger.warning("can_receive_%s: invalid user_id %r", field, user_id)
            return False
        doc = await self._col().find_one(
            {"_id": ObjectId(user_id)}, projection={"settings": 1}
        )
        if doc is None:
            _logger.warning("can_receive_%s: user_id %s not found", field, user_id)
            return False
        settings = doc.get("settings") or {}
        return bool(settings.get(field, default))


class Account:
    """Public Django-style entry point for the accounts feature.

    Other modules import this and call ``Account.objects.<method>()``::

        from modules.accounts.manager import Account

        if await Account.objects.can_receive_email(user_id):
            ...

    The class is intentionally a thin holder — the real surface is
    :class:`AccountManager`. Tests monkeypatch methods on
    ``Account.objects`` directly.
    """

    objects = AccountManager()
