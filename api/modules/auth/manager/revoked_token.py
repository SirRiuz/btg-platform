# Python
from datetime import datetime, timezone

# Libs
from pymongo import ASCENDING

# Core
from core.manager import BaseManager


class RevokedTokenManager(BaseManager):
    """Data-access layer for the ``revoked_tokens`` blacklist.

    Stores the JWT ``jti`` of every token explicitly invalidated via
    ``/auth/logout``. The decision dependency
    (:func:`modules.auth.dependencies.get_current_user`) consults this
    collection on every authenticated request, so revocation takes
    effect on the very next call — there is no in-process cache to
    invalidate.

    Note: for a production deployment the natural home for this set is
    Redis with a TTL matching the JWT lifetime — sub-millisecond lookups
    and free expiration. Mongo is used here because the project already
    has it wired up; the index keeps lookups cheap (single key,
    equality), so the overhead is acceptable for the technical test.
    """

    COLLECTION = "revoked_tokens"

    async def ensure_indexes(self) -> None:
        """Create the unique index on ``jti`` if missing.

        Idempotent (Mongo skips identical specs). Uniqueness guarantees
        that :meth:`add` can be implemented as an upsert without ever
        producing duplicate blacklist entries.
        """
        await self._col().create_index([("jti", ASCENDING)], unique=True, name="uniq_jti")

    async def add(self, *, jti: str, user_id: str) -> None:
        """Revoke a token by adding its ``jti`` to the blacklist.

        Implemented as an upsert with ``$setOnInsert`` so calling
        ``add()`` twice with the same ``jti`` is a no-op rather than a
        500: a network retry that hits the endpoint a second time, or a
        legitimately double-tap from the client, both succeed without
        rewriting the original ``revoked_at`` timestamp.

        Args:
            jti: The unique JWT identifier extracted from the token's
                ``jti`` claim.
            user_id: The user the revoked token belonged to. Kept for
                auditing — there is no enforcement on this side.
        """
        await self._col().update_one(
            {"jti": jti},
            {
                "$setOnInsert": {
                    "jti": jti,
                    "user_id": user_id,
                    "revoked_at": datetime.now(timezone.utc),
                }
            },
            upsert=True,
        )

    async def is_revoked(self, jti: str) -> bool:
        """Return ``True`` if the given ``jti`` is in the blacklist.

        Uses ``count_documents(..., limit=1)`` rather than ``find_one``
        to avoid fetching the document body — we only care whether at
        least one row exists. With the unique index on ``jti`` this is a
        single-key equality check, effectively constant-time at our
        scale.
        """
        return (await self._col().count_documents({"jti": jti}, limit=1)) > 0


class RevokedToken:
    """Public Django-style entry point for the ``revoked_tokens`` collection.

    Mirrors the pattern used by :class:`User` (and the existing
    ``Healthcheck`` feature): the class is a thin holder so callers
    can write ``await RevokedToken.objects.is_revoked(jti)`` instead of
    importing the manager directly. Tests rely on this same path to
    monkeypatch behavior per-test.
    """

    objects = RevokedTokenManager()
