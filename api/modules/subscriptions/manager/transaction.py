# Python
import uuid
from datetime import datetime, timezone
from typing import Any

# Libs
from pymongo import ASCENDING, DESCENDING

# Core
from core.manager import BaseManager

# Module
from modules.subscriptions.schemas import TransactionDTO, TransactionType


def _transaction_from_doc(doc: dict[str, Any]) -> TransactionDTO:
    """Project a raw Mongo document into the public DTO.

    ``related_subscription_id`` may be present or absent (cancellations
    delete the Subscription before/at the same time as writing the
    Transaction; we still record the id so support can join the dots in
    an investigation, but consumers must treat it as opaque).
    """
    related = doc.get("related_subscription_id")
    return TransactionDTO(
        id=doc["_id"],
        type=doc["type"],
        fund_id=doc["fund_id"],
        fund_nombre=doc["fund_nombre"],
        amount=doc["amount"],
        balance_before=doc["balance_before"],
        balance_after=doc["balance_after"],
        timestamp=doc["timestamp"],
        related_subscription_id=str(related) if related is not None else None,
    )


class TransactionManager(BaseManager):
    """Data-access layer for the ``transactions`` audit log.

    Design constraints — non-negotiable:

    * The collection is **append-only**. There are no update or delete
      paths in this manager, and there are no admin endpoints for either.
      Audit integrity is the whole point of this collection: a row is
      what was true at a point in time.
    * The primary key is a UUID v4 minted in Python (per the BTG brief,
      which requires an "identificador único"). Using UUIDs decouples
      the id from Mongo's clock-driven ObjectId and makes ids
      independently grep-able in distributed logs.
    * ``fund_nombre`` is denormalized at write-time. A later rename of
      the fund must NOT mutate historical transactions — they reflect
      the world as it was the day the money moved.

    Indexes:

    * ``(user_id, timestamp desc)`` — the natural shape of
      ``GET /me/transactions`` (newest first, paginated).
    * ``type`` — supports admin/reporting queries by movement type.
    """

    COLLECTION = "transactions"

    async def ensure_indexes(self) -> None:
        """Create the supporting indexes if missing — idempotent."""
        await self._col().create_index(
            [("user_id", ASCENDING), ("timestamp", DESCENDING)],
            name="by_user_recent",
        )
        await self._col().create_index([("type", ASCENDING)], name="by_type")

    async def create(
        self,
        *,
        user_id: str,
        fund_id: int,
        fund_nombre: str,
        type_: TransactionType,
        amount: int,
        balance_before: int,
        balance_after: int,
        related_subscription_id: str | None = None,
        session=None,
        transaction_id: str | None = None,
    ) -> TransactionDTO:
        """Append a new immutable audit row and return its DTO.

        ``session`` is honored — when the caller is running inside a
        MongoDB multi-document transaction, the insert participates so it
        is rolled back along with the balance change and the subscription
        write if any step fails.

        ``transaction_id`` may be supplied by the caller (used by
        ``subscribe`` to share the same UUID with the Subscription's
        ``transaction_id`` back-reference); otherwise one is minted here.

        Args:
            user_id: Owner of the movement (string form of the
                User._id).
            fund_id: Fund the movement is about.
            fund_nombre: Denormalized fund name at the time of the movement.
            type_: ``OPEN`` or ``CANCEL``.
            amount: Money moved (always positive).
            balance_before: User's balance before the movement.
            balance_after: User's balance after the movement.
            related_subscription_id: Optional link to the affected
                Subscription document, kept as a string. Useful for
                cross-referencing in audits; treat as opaque.
            session: Mongo client session to enrol the insert in a
                transaction (optional).
            transaction_id: Pre-generated UUID v4 (optional).

        Returns:
            The freshly-persisted Transaction as a DTO.
        """
        tx_id = transaction_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        document: dict[str, Any] = {
            "_id": tx_id,
            "user_id": user_id,
            "fund_id": fund_id,
            "fund_nombre": fund_nombre,
            "type": type_.value,
            "amount": amount,
            "balance_before": balance_before,
            "balance_after": balance_after,
            "timestamp": now,
            "related_subscription_id": related_subscription_id,
        }
        await self._col().insert_one(document, session=session)
        return _transaction_from_doc(document)

    async def list_for_user(
        self,
        user_id: str,
        *,
        skip: int = 0,
        limit: int = 20,
        type_: TransactionType | None = None,
    ) -> tuple[list[TransactionDTO], int]:
        """Return the user's audit rows, newest first, plus the total count.

        Filters are user-scoped — there is no path that allows reading
        another user's rows from this layer. Total counts the filtered
        set *before* pagination, which is what UI clients need.
        """
        query: dict[str, Any] = {"user_id": user_id}
        if type_ is not None:
            query["type"] = type_.value

        total = await self._col().count_documents(query)
        cursor = (
            self._col()
            .find(query)
            .sort("timestamp", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        items = [_transaction_from_doc(doc) async for doc in cursor]
        return items, total


class Transaction:
    """Public Django-style entry point for the ``transactions`` collection.

    Following the project convention, ``Transaction.objects`` is the
    single import path callers use. Same precedent as ``User``,
    ``Account``, ``Fund``.
    """

    objects = TransactionManager()
