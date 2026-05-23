"""Tests for the money-conservation invariant.

The invariant the platform must uphold is:

    for each user, at any instant,
        balance_now + Σ(active_subscription.amount) == 500_000  (initial credit)

These tests do not exercise concurrency against a real database — that
belongs in an integration suite against a replica set. They DO pin the
manager's behavior against the simulated balance and the DTOs it
returns, so a refactor that violates the invariant fails loudly here.
"""

# Python
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

# Libs
from bson import ObjectId

# Module
from modules.funds.manager import Fund
from modules.funds.schemas import Categoria, FundResponseDTO, PerfilRiesgo
from modules.subscriptions.manager import Subscription, Transaction
from modules.subscriptions.schemas import TransactionDTO, TransactionType


INITIAL_BALANCE = 500_000


def _run(coro):
    return asyncio.run(coro)


def _fund(*, id: int = 3, monto_minimo: int = 50_000, nombre: str = "DEUDAPRIVADA"):
    return FundResponseDTO(
        id=id,
        nombre=nombre,
        monto_minimo=monto_minimo,
        categoria=Categoria.FIC,
        descripcion=None,
        perfil_riesgo=PerfilRiesgo.BAJO,
        activo=True,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


class _InMemoryBalance:
    """Tiny in-memory shim of the users collection so we can chain ops.

    The real ``find_one_and_update`` with ``$inc`` is replaced by direct
    arithmetic — that is enough to verify the invariant *given* the
    manager's call pattern. The test does NOT prove atomicity (no
    concurrency here); that property is the responsibility of Mongo
    itself, and is exercised by the integration suite.
    """

    def __init__(self, *, user_oid: ObjectId, initial: int = INITIAL_BALANCE) -> None:
        self.user_oid = user_oid
        self.balance = initial

    async def find_one_and_update(self, matcher, update, **_kwargs):
        delta = update["$inc"]["balance"]
        # Honor the $gte guard (insufficient balance returns None).
        guard = matcher.get("balance", {}).get("$gte")
        if guard is not None and self.balance < guard:
            return None
        self.balance += delta
        return {"_id": self.user_oid, "balance": self.balance}


def _stub_for_invariant(monkeypatch, *, balance_shim: _InMemoryBalance):
    """Wire the manager onto the balance shim + capturing collections."""
    # Fund manager
    monkeypatch.setattr(Fund.objects, "get_fund_by_id", AsyncMock(return_value=_fund()))

    # Subscription collection: track inserts/deletes so we can sum amounts.
    inserted: dict[ObjectId, dict] = {}

    sub_col = MagicMock()

    async def _find_one(query, **_kwargs):
        # Pre-check: return None if no sub for this user+fund.
        for sub in inserted.values():
            if (
                sub["user_id"] == query.get("user_id")
                and sub["fund_id"] == query.get("fund_id")
            ):
                return sub
        return None

    async def _insert_one(doc, **_kwargs):
        inserted[doc["_id"]] = doc

    async def _find_one_and_delete(query, **_kwargs):
        for oid, sub in list(inserted.items()):
            if oid == query["_id"] and sub["user_id"] == query["user_id"]:
                del inserted[oid]
                return sub
        return None

    sub_col.find_one = AsyncMock(side_effect=_find_one)
    sub_col.insert_one = AsyncMock(side_effect=_insert_one)
    sub_col.find_one_and_delete = AsyncMock(side_effect=_find_one_and_delete)

    monkeypatch.setattr(
        Subscription.objects, "_col", lambda self=Subscription.objects: sub_col
    )
    monkeypatch.setattr(
        Subscription.objects, "_users", lambda self=Subscription.objects: balance_shim
    )

    # Transaction.create just returns a stub DTO — the audit log content
    # is irrelevant for the invariant test.
    async def _make_tx(*, type_, amount, balance_before, balance_after, **_kwargs):
        return TransactionDTO(
            id=str(ObjectId()),
            type=type_,
            fund_id=3,
            fund_nombre="DEUDAPRIVADA",
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

    monkeypatch.setattr(Transaction.objects, "create", AsyncMock(side_effect=_make_tx))

    return sub_col, inserted


def _sum_invested(inserted: dict[ObjectId, dict]) -> int:
    return sum(sub["amount"] for sub in inserted.values())


class TestMoneyConservation:

    def test_invariant_after_subscribe(self, monkeypatch):
        user_oid = ObjectId()
        shim = _InMemoryBalance(user_oid=user_oid)
        _, inserted = _stub_for_invariant(monkeypatch, balance_shim=shim)

        _run(Subscription.objects.subscribe(user_id=str(user_oid), fund_id=3))

        assert shim.balance + _sum_invested(inserted) == INITIAL_BALANCE

    def test_invariant_after_subscribe_then_cancel(self, monkeypatch):
        user_oid = ObjectId()
        shim = _InMemoryBalance(user_oid=user_oid)
        sub_col, inserted = _stub_for_invariant(monkeypatch, balance_shim=shim)

        sub_result = _run(
            Subscription.objects.subscribe(user_id=str(user_oid), fund_id=3)
        )
        assert shim.balance + _sum_invested(inserted) == INITIAL_BALANCE

        # Cancel must restore the user to the initial state.
        _run(
            Subscription.objects.cancel(
                user_id=str(user_oid), subscription_id=sub_result.subscription.id
            )
        )
        assert shim.balance == INITIAL_BALANCE
        assert _sum_invested(inserted) == 0

    def test_invariant_after_multiple_subscribes(self, monkeypatch):
        """Subscribe to three different funds — invariant still holds."""
        user_oid = ObjectId()
        shim = _InMemoryBalance(user_oid=user_oid)
        _, inserted = _stub_for_invariant(monkeypatch, balance_shim=shim)

        for fund_id, amount in [(3, 50_000), (4, 100_000), (5, 75_000)]:
            # Re-stub fund lookup per iteration so monto_minimo AND id are
            # in range — the manager copies fund.id into the subscription
            # doc, so a stale id=3 would trip the duplicate-subscription
            # check on the second iteration.
            monkeypatch.setattr(
                Fund.objects,
                "get_fund_by_id",
                AsyncMock(
                    return_value=_fund(
                        id=fund_id, monto_minimo=amount, nombre=f"F{fund_id}"
                    )
                ),
            )
            _run(
                Subscription.objects.subscribe(
                    user_id=str(user_oid), fund_id=fund_id, amount=amount
                )
            )

        assert shim.balance + _sum_invested(inserted) == INITIAL_BALANCE
        assert shim.balance == INITIAL_BALANCE - (50_000 + 100_000 + 75_000)

    def test_insufficient_balance_does_not_mutate_state(self, monkeypatch):
        """A failed subscribe must leave balance AND inserted set unchanged."""
        from constants.subscriptions_exceptions import InsufficientBalanceError
        import pytest

        user_oid = ObjectId()
        shim = _InMemoryBalance(user_oid=user_oid, initial=10_000)  # too poor
        _, inserted = _stub_for_invariant(monkeypatch, balance_shim=shim)

        with pytest.raises(InsufficientBalanceError):
            _run(
                Subscription.objects.subscribe(
                    user_id=str(user_oid), fund_id=3, amount=50_000
                )
            )

        # Balance untouched, no subscription written.
        assert shim.balance == 10_000
        assert _sum_invested(inserted) == 0
