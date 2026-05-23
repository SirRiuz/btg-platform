# Python
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

# Libs
from bson import ObjectId
from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError

# Constants
from constants.subscriptions_exceptions import (
    AlreadySubscribedError,
    AmountBelowMinimumError,
    FundInactiveError,
    InsufficientBalanceError,
    InvalidAmountError,
    SubscriptionNotFoundError,
)

# Core
from core.manager import BaseManager

# Module
from modules.funds.manager import Fund
from modules.subscriptions.manager.atomic import atomic_session
from modules.subscriptions.manager.transaction import Transaction
from modules.subscriptions.schemas import (
    CancelResultDTO,
    SubscribeResultDTO,
    SubscriptionDTO,
    TransactionType,
)


_logger = logging.getLogger(__name__)


def _subscription_from_doc(doc: dict[str, Any]) -> SubscriptionDTO:
    """Project a raw Mongo document into the public DTO.

    ``user_id`` is the ObjectId of the User; the DTO doesn't expose it
    because every read path is already user-scoped by the JWT. Exposing
    it would only help an attacker correlate subscriptions across users.
    """
    return SubscriptionDTO(
        id=str(doc["_id"]),
        fund_id=doc["fund_id"],
        fund_nombre=doc["fund_nombre"],
        amount=doc["amount"],
        subscribed_at=doc["subscribed_at"],
    )


class SubscriptionManager(BaseManager):
    """Sole authority on subscription lifecycle and money movement.

    Every method here treats the **money-conservation invariant** as
    non-negotiable:

        for each user, at any instant,
            balance_now + Σ(active_subscription.amount) == 500_000

    The platform issues 500 000 COP of credit when a user is created
    (see ``UserManager``); after that, money only moves between the
    user's ``balance`` and their active subscriptions. The manager
    enforces this by making every state change atomic — either through
    a true MongoDB multi-document transaction (when the cluster supports
    them) or through a conditional ``$inc`` followed by compensating
    actions on failure.

    The compound unique index on ``(user_id, fund_id)`` enforces the
    "one active subscription per fund" rule at the storage layer. The
    fast-path pre-check (:meth:`_has_active_subscription`) renders a
    friendly 409 before the insert; the unique index catches concurrent
    inserts that slip through.

    Method return types are Pydantic DTOs — the future subscriptions UI
    and any background workers consume the same shapes.
    """

    COLLECTION = "subscriptions"

    # The fund_nombre is denormalized on the Subscription document (in
    # addition to the Transaction document). The brief only required it
    # on Transaction, but storing it on Subscription too avoids N+1
    # lookups in ``list_active_subscriptions`` and keeps the per-user
    # listing self-contained — a fund rename does not retro-affect a
    # user's "what am I currently subscribed to" view.

    def _users(self):
        """Direct handle to the ``users`` collection.

        ``UserManager``/``AccountManager`` intentionally do **not** expose
        balance debit/credit primitives — the subscriptions module owns
        money movement, period. Centralizing the ops here keeps every
        balance mutation in one auditable place, which is what makes the
        money-conservation invariant verifiable.
        """
        return self._db()["users"]

    async def ensure_indexes(self) -> None:
        """Create the supporting indexes if missing — idempotent."""
        await self._col().create_index(
            [("user_id", ASCENDING), ("fund_id", ASCENDING)],
            unique=True,
            name="uniq_user_fund",
        )
        await self._col().create_index(
            [("user_id", ASCENDING), ("subscribed_at", DESCENDING)],
            name="by_user_recent",
        )

    # ---------- Public API ----------

    async def subscribe(
        self,
        *,
        user_id: str,
        fund_id: int,
        amount: int | None = None,
    ) -> SubscribeResultDTO:
        """Subscribe ``user_id`` to ``fund_id`` for ``amount`` COP.

        When ``amount`` is ``None`` the fund's ``monto_minimo`` is used.
        The operation is atomic with respect to:

        * the User's ``balance`` (decremented by ``amount``);
        * the Subscription document (inserted);
        * the Transaction audit row (appended).

        Either all three commit or none of them do — guaranteed by a real
        MongoDB transaction when the cluster supports it, or by
        compensating actions in the standalone-Mongo fallback.

        Raises:
            FundNotFoundError: the fund does not exist (from ``FundManager``).
            FundInactiveError: the fund is soft-deleted.
            InvalidAmountError: ``amount`` is not a positive integer.
            AmountBelowMinimumError: ``amount`` < ``monto_minimo``.
            AlreadySubscribedError: the user has an active subscription
                to this fund (race-safe — the unique index is the
                authoritative guard).
            InsufficientBalanceError: the user's ``balance`` < ``amount``.
                Carries the BTG-brief-exact Spanish message.
        """
        fund = await Fund.objects.get_fund_by_id(fund_id)
        if not fund.activo:
            raise FundInactiveError(fund.nombre)

        effective_amount = amount if amount is not None else fund.monto_minimo
        if effective_amount <= 0:
            raise InvalidAmountError()
        if effective_amount < fund.monto_minimo:
            raise AmountBelowMinimumError(fund.nombre, fund.monto_minimo)

        if await self._has_active_subscription(user_id=user_id, fund_id=fund.id):
            raise AlreadySubscribedError(fund.nombre)

        # Pre-allocate identifiers so the same UUID can be linked from
        # the Subscription document (``transaction_id``) back to the
        # Transaction row — useful for support investigations.
        subscription_oid = ObjectId()
        transaction_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        balance_decremented = False
        subscription_inserted = False

        async with atomic_session() as session:
            try:
                balance_before, balance_after = await self._debit_balance(
                    user_id=user_id,
                    amount=effective_amount,
                    fund_nombre=fund.nombre,
                    session=session,
                )
                balance_decremented = True

                subscription_doc: dict[str, Any] = {
                    "_id": subscription_oid,
                    "user_id": ObjectId(user_id),
                    "fund_id": fund.id,
                    "fund_nombre": fund.nombre,
                    "amount": effective_amount,
                    "subscribed_at": now,
                    "transaction_id": transaction_id,
                }
                try:
                    await self._col().insert_one(subscription_doc, session=session)
                    subscription_inserted = True
                except DuplicateKeyError as exc:
                    # Lost the race — the unique compound index just fired.
                    raise AlreadySubscribedError(fund.nombre) from exc

                transaction = await Transaction.objects.create(
                    user_id=user_id,
                    fund_id=fund.id,
                    fund_nombre=fund.nombre,
                    type_=TransactionType.OPEN,
                    amount=effective_amount,
                    balance_before=balance_before,
                    balance_after=balance_after,
                    related_subscription_id=str(subscription_oid),
                    transaction_id=transaction_id,
                    session=session,
                )
            except Exception:
                # In transaction mode (session is not None) we let the
                # exception propagate so the transaction aborts cleanly.
                # In fallback mode we manually undo whatever already landed.
                if session is None:
                    await self._compensate_subscribe(
                        user_id=user_id,
                        amount=effective_amount,
                        subscription_oid=subscription_oid,
                        balance_decremented=balance_decremented,
                        subscription_inserted=subscription_inserted,
                    )
                raise

        _logger.info(
            "subscribe.ok user_id=%s fund_id=%s amount=%s tx_id=%s",
            user_id,
            fund.id,
            effective_amount,
            transaction_id,
        )

        subscription_dto = SubscriptionDTO(
            id=str(subscription_oid),
            fund_id=fund.id,
            fund_nombre=fund.nombre,
            amount=effective_amount,
            subscribed_at=now,
        )
        return SubscribeResultDTO(
            subscription=subscription_dto,
            transaction=transaction,
            new_balance=balance_after,
        )

    async def cancel(
        self, *, user_id: str, subscription_id: str
    ) -> CancelResultDTO:
        """Cancel an active subscription, returning the exact ``amount`` to the user.

        The credited amount is what the user *actually* invested — not
        the fund's ``monto_minimo``. A user who subscribed above the
        minimum gets their full amount back.

        Ownership is enforced atomically: ``find_one_and_delete`` matches
        on both ``_id`` AND ``user_id``, so an attacker forging another
        user's subscription id sees the same "no match" path as a
        non-existent id — and both surface as
        :class:`SubscriptionNotFoundError`. This is a deliberate
        information-leak guard, mirroring how the auth module collapses
        "unknown email" and "wrong password" into one response.

        Raises:
            SubscriptionNotFoundError: subscription does not exist OR is
                not owned by ``user_id``.
        """
        if not ObjectId.is_valid(subscription_id):
            raise SubscriptionNotFoundError()
        subscription_oid = ObjectId(subscription_id)

        balance_credited = False

        async with atomic_session() as session:
            deleted = await self._col().find_one_and_delete(
                {"_id": subscription_oid, "user_id": ObjectId(user_id)},
                session=session,
            )
            if deleted is None:
                raise SubscriptionNotFoundError()

            try:
                balance_before, balance_after = await self._credit_balance(
                    user_id=user_id, amount=deleted["amount"], session=session
                )
                balance_credited = True

                transaction = await Transaction.objects.create(
                    user_id=user_id,
                    fund_id=deleted["fund_id"],
                    fund_nombre=deleted["fund_nombre"],
                    type_=TransactionType.CANCEL,
                    amount=deleted["amount"],
                    balance_before=balance_before,
                    balance_after=balance_after,
                    related_subscription_id=subscription_id,
                    session=session,
                )
            except Exception:
                if session is None:
                    await self._compensate_cancel(
                        deleted_subscription=deleted,
                        user_id=user_id,
                        balance_credited=balance_credited,
                    )
                raise

        _logger.info(
            "cancel.ok user_id=%s fund_id=%s amount=%s sub_id=%s tx_id=%s",
            user_id,
            deleted["fund_id"],
            deleted["amount"],
            subscription_id,
            transaction.id,
        )

        return CancelResultDTO(
            fund_nombre=deleted["fund_nombre"],
            amount_returned=deleted["amount"],
            new_balance=balance_after,
            transaction=transaction,
        )

    async def list_active_subscriptions(self, user_id: str) -> list[SubscriptionDTO]:
        """Return the user's active subscriptions, newest first.

        Always user-scoped. Inactive subscriptions don't exist as a
        concept in this collection — cancellation deletes the row and
        the audit lives in ``transactions``.
        """
        cursor = (
            self._col()
            .find({"user_id": ObjectId(user_id)})
            .sort("subscribed_at", DESCENDING)
        )
        return [_subscription_from_doc(doc) async for doc in cursor]

    async def get_user_total_invested(self, user_id: str) -> int:
        """Return Σ(active_subscription.amount) for the user.

        Backed by an aggregation pipeline so the database does the work
        (instead of streaming every row to the client). Returns ``0``
        when the user has no active subscriptions.
        """
        pipeline = [
            {"$match": {"user_id": ObjectId(user_id)}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
        ]
        async for doc in self._col().aggregate(pipeline):
            return int(doc["total"])
        return 0

    # ---------- Internal balance primitives ----------

    async def _debit_balance(
        self,
        *,
        user_id: str,
        amount: int,
        fund_nombre: str,
        session,
    ) -> tuple[int, int]:
        """Atomically debit ``amount`` from the user's balance.

        Implemented as a conditional ``find_one_and_update`` with matcher
        ``{_id, balance: {$gte: amount}}``. The matcher itself encodes
        the "enough balance" precondition — concurrent requests cannot
        both win, even without a real transaction, because Mongo
        serializes single-document updates.

        Returns:
            ``(balance_before, balance_after)``.

        Raises:
            InsufficientBalanceError: with the brief-exact Spanish message.
        """
        updated = await self._users().find_one_and_update(
            {"_id": ObjectId(user_id), "balance": {"$gte": amount}},
            {"$inc": {"balance": -amount}},
            projection={"balance": 1},
            return_document=ReturnDocument.AFTER,
            session=session,
        )
        if updated is None:
            raise InsufficientBalanceError(fund_nombre)
        balance_after = int(updated["balance"])
        balance_before = balance_after + amount
        return balance_before, balance_after

    async def _credit_balance(
        self, *, user_id: str, amount: int, session
    ) -> tuple[int, int]:
        """Atomically credit ``amount`` to the user's balance.

        The user is guaranteed to exist (``get_current_user`` already
        loaded the document); we still go through ``find_one_and_update``
        to make the operation atomic and to read the post-update balance
        in a single round-trip.

        Returns:
            ``(balance_before, balance_after)``.
        """
        updated = await self._users().find_one_and_update(
            {"_id": ObjectId(user_id)},
            {"$inc": {"balance": +amount}},
            projection={"balance": 1},
            return_document=ReturnDocument.AFTER,
            session=session,
        )
        if updated is None:
            # Should not happen: the JWT pipeline confirmed the user exists.
            raise RuntimeError(f"credit_balance: user {user_id} disappeared")
        balance_after = int(updated["balance"])
        balance_before = balance_after - amount
        return balance_before, balance_after

    # ---------- Internal helpers ----------

    async def _has_active_subscription(self, *, user_id: str, fund_id: int) -> bool:
        """Best-effort pre-check used to render a friendly 409.

        The unique compound index on ``(user_id, fund_id)`` is what
        actually guarantees uniqueness — this check is purely for UX.
        """
        existing = await self._col().find_one(
            {"user_id": ObjectId(user_id), "fund_id": fund_id},
            projection={"_id": 1},
        )
        return existing is not None

    async def _compensate_subscribe(
        self,
        *,
        user_id: str,
        amount: int,
        subscription_oid: ObjectId,
        balance_decremented: bool,
        subscription_inserted: bool,
    ) -> None:
        """Fallback-mode compensation for a failed ``subscribe``.

        Undoes work in reverse order — subscription first, then balance —
        so that an observer that catches us mid-compensation can never
        see "subscription with no money debited from balance".

        If a compensating op itself fails the error is logged with full
        context: this is the one inconsistency window the standalone
        fallback can produce, and ops needs the breadcrumb to reconcile
        by hand.
        """
        if subscription_inserted:
            try:
                await self._col().delete_one({"_id": subscription_oid})
            except Exception:  # noqa: BLE001
                _logger.exception(
                    "compensate_subscribe: failed to delete subscription %s; "
                    "manual reconciliation needed (user_id=%s, amount=%s)",
                    subscription_oid,
                    user_id,
                    amount,
                )
        if balance_decremented:
            try:
                await self._users().update_one(
                    {"_id": ObjectId(user_id)},
                    {"$inc": {"balance": amount}},
                )
            except Exception:  # noqa: BLE001
                _logger.exception(
                    "compensate_subscribe: failed to restore balance for "
                    "user_id=%s amount=%s; MONEY MAY BE LOST.",
                    user_id,
                    amount,
                )

    async def _compensate_cancel(
        self,
        *,
        deleted_subscription: dict[str, Any],
        user_id: str,
        balance_credited: bool,
    ) -> None:
        """Fallback-mode compensation for a failed ``cancel``.

        Symmetrical to :meth:`_compensate_subscribe`: re-insert the
        deleted subscription, and if we already credited the balance,
        debit it back. Any failure here is logged loudly — it is the
        only inconsistency window in the fallback path.
        """
        try:
            await self._col().insert_one(deleted_subscription)
        except Exception:  # noqa: BLE001
            _logger.exception(
                "compensate_cancel: failed to reinsert subscription %s; "
                "manual reconciliation needed (user_id=%s).",
                deleted_subscription.get("_id"),
                user_id,
            )
        if balance_credited:
            try:
                await self._users().update_one(
                    {"_id": ObjectId(user_id)},
                    {"$inc": {"balance": -deleted_subscription["amount"]}},
                )
            except Exception:  # noqa: BLE001
                _logger.exception(
                    "compensate_cancel: failed to debit balance back for "
                    "user_id=%s amount=%s; DOUBLE-CREDIT POSSIBLE.",
                    user_id,
                    deleted_subscription["amount"],
                )


class Subscription:
    """Public Django-style entry point for the ``subscriptions`` collection.

    Other modules import this and call ``Subscription.objects.<method>()``
    — mirroring the pattern used by :class:`User`, :class:`Account`,
    :class:`Fund` and :class:`Transaction`.
    """

    objects = SubscriptionManager()
