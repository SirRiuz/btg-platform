# Python
from datetime import datetime, timezone
from typing import Any

# Libs
from bson import ObjectId
from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError

# Constants
from constants.auth_exceptions import EmailAlreadyExistsError, PhoneAlreadyExistsError

# Core
from core.manager import BaseManager
from core.security import hash_password

# Module
from modules.auth.schemas import UserRole


# Business default: every new account starts with this credit balance
# (matches the BTG Pactual technical-test brief).
INITIAL_BALANCE = 500000

# Default notification preferences applied at registration. Defined here
# (next to where they're written) so the auth module owns the lifecycle of
# the user document. The accounts module reads/mutates these afterwards.
DEFAULT_SETTINGS = {"allow_email": True, "allow_sms": False}


class UserManager(BaseManager):
    """Data-access layer for the ``users`` collection.

    Concentrates every read/write against the ``users`` collection so the
    rest of the codebase never holds a Motor handle directly. Following
    the project's Django-style ``<Feature>.objects.<query>()`` convention,
    instances are not created at call sites — callers always go through
    :attr:`User.objects`.

    Two safety nets work together to guarantee uniqueness of ``email``
    and ``phone``:

    * :meth:`find_conflict` provides a fast, user-friendly pre-check that
      tells :meth:`create` which constraint will fire, so the API returns
      a precise ``EmailAlreadyExistsError`` / ``PhoneAlreadyExistsError``
      instead of a generic 409.
    * The unique indexes created by :meth:`ensure_indexes` are the
      authoritative defense — they catch any race that slips between the
      pre-check and the insert.
    """

    COLLECTION = "users"

    async def ensure_indexes(self) -> None:
        """Create the unique indexes on ``email`` and ``phone`` if missing.

        Idempotent — Mongo's ``createIndex`` is a no-op when an index with
        the same name/spec already exists. Invoked from the FastAPI
        ``lifespan`` so the very first write is already protected.
        """
        await self._col().create_index([("email", ASCENDING)], unique=True, name="uniq_email")
        await self._col().create_index([("phone", ASCENDING)], unique=True, name="uniq_phone")

    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        """Return the user whose ``email`` matches, case-insensitively.

        The lookup compares against the lowercased form so callers don't
        need to normalize first. Returns ``None`` when no match is found
        — login uses this to distinguish "unknown email" from "wrong
        password" internally, while exposing a single generic error to the
        client.
        """
        return await self._col().find_one({"email": email.lower()})

    async def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        """Return the user document for the given ``ObjectId`` string.

        Defensively validates the string before round-tripping it to
        Mongo: invalid hexadecimal returns ``None`` rather than raising,
        because the most common caller is :func:`get_current_user` and a
        malformed ``sub`` claim should surface as "invalid token", not as
        a 500.
        """
        if not ObjectId.is_valid(user_id):
            return None
        return await self._col().find_one({"_id": ObjectId(user_id)})

    async def find_conflict(self, *, email: str, phone: str) -> str | None:
        """Pre-check ``email`` and ``phone`` uniqueness in a single round-trip.

        Returns the string ``"email"`` when the email is taken,
        ``"phone"`` when the phone is taken, or ``None`` when neither is.
        A single ``$or`` query avoids paying for two reads in the happy
        path. Note that this is a *best-effort* check — a concurrent
        insert may slip through between this call and
        :meth:`create`'s insert; the unique index plus the
        ``DuplicateKeyError`` handler in :meth:`create` is what makes
        registration race-safe.
        """
        existing = await self._col().find_one(
            {"$or": [{"email": email.lower()}, {"phone": phone}]},
            projection={"email": 1, "phone": 1},
        )
        if existing is None:
            return None
        if existing.get("email") == email.lower():
            return "email"
        return "phone"

    async def create(
        self,
        *,
        first_name: str,
        last_name: str,
        email: str,
        phone: str,
        password: str,
    ) -> dict[str, Any]:
        """Persist a new user and return the resulting document.

        Responsibilities, in order:

        1. Run :meth:`find_conflict` to fail fast with a precise domain
           exception when the email or phone is already taken.
        2. Hash the plaintext password with bcrypt — the raw value is
           never logged, returned or written to disk.
        3. Insert the document with the business defaults
           (``balance=INITIAL_BALANCE``, ``role=USER``,
           ``notification_preference=EMAIL``, ``is_active=True``) plus
           ``created_at`` / ``updated_at`` timestamps in UTC.
        4. If the insert fails with :class:`DuplicateKeyError` despite
           the pre-check (a race between two concurrent registrations),
           the offending field is identified from the Mongo
           ``keyPattern`` and the matching domain exception is raised so
           the API still returns a precise 409.

        Returns:
            dict: The freshly persisted document, with ``_id`` populated.

        Raises:
            EmailAlreadyExistsError: ``email`` is already taken (pre-check or race).
            PhoneAlreadyExistsError: ``phone`` is already taken (pre-check or race).
        """
        conflict = await self.find_conflict(email=email, phone=phone)
        if conflict == "email":
            raise EmailAlreadyExistsError()
        if conflict == "phone":
            raise PhoneAlreadyExistsError()

        now = datetime.now(timezone.utc)
        document = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email.lower(),
            "phone": phone,
            "password_hash": hash_password(password),
            "balance": INITIAL_BALANCE,
            "settings": dict(DEFAULT_SETTINGS),
            "role": UserRole.USER.value,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        try:
            result = await self._col().insert_one(document)
        except DuplicateKeyError as exc:
            # Race: another insert won between find_conflict() and insert_one().
            # The duplicate-key error tells us which constraint fired.
            key = (exc.details or {}).get("keyPattern", {})
            if "email" in key:
                raise EmailAlreadyExistsError() from exc
            raise PhoneAlreadyExistsError() from exc

        document["_id"] = result.inserted_id
        return document


class User:
    """Public Django-style entry point for the ``users`` collection.

    Following the project convention (see ``core/manager.py``), the
    feature class is intentionally a thin holder — it doesn't store user
    state, it merely exposes ``User.objects`` as the single import path
    callers use to reach the manager. This keeps query sites readable
    (``await User.objects.get_by_email(...)``) and lets us swap the
    manager out for tests with a single ``monkeypatch``.
    """

    objects = UserManager()
