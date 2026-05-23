# Python
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

# Libs
import pytest
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

# Constants
from constants.subscriptions_exceptions import (
    AlreadySubscribedError,
    AmountBelowMinimumError,
    FundInactiveError,
    InsufficientBalanceError,
    SubscriptionNotFoundError,
)

# Module
from modules.funds.manager import Fund
from modules.funds.schemas import Categoria, FundResponseDTO, PerfilRiesgo
from modules.subscriptions.manager import Subscription, Transaction
from modules.subscriptions.schemas import TransactionDTO, TransactionType


def _run(coro):
    return asyncio.run(coro)


def _fund_dto(
    *,
    id_: int = 3,
    nombre: str = "DEUDAPRIVADA",
    monto_minimo: int = 50_000,
    activo: bool = True,
) -> FundResponseDTO:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return FundResponseDTO(
        id=id_,
        nombre=nombre,
        monto_minimo=monto_minimo,
        categoria=Categoria.FIC,
        descripcion=None,
        perfil_riesgo=PerfilRiesgo.BAJO,
        activo=activo,
        created_at=now,
        updated_at=now,
    )


def _tx_dto(*, type_=TransactionType.OPEN, amount=50_000, balance_after=450_000) -> TransactionDTO:
    return TransactionDTO(
        id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        type=type_,
        fund_id=3,
        fund_nombre="DEUDAPRIVADA",
        amount=amount,
        balance_before=balance_after + (amount if type_ is TransactionType.OPEN else -amount),
        balance_after=balance_after,
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def _stub_collections(
    monkeypatch,
    *,
    existing_subscription: dict | None = None,
    sub_insert_raises: Exception | None = None,
    users_find_returns: dict | None = None,
):
    """Wire MagicMocks for both the subscriptions and users collections.

    Returns the two mocks so the test can assert on call args.
    """
    sub_col = MagicMock()
    sub_col.find_one = AsyncMock(return_value=existing_subscription)
    sub_col.insert_one = AsyncMock(side_effect=sub_insert_raises)
    sub_col.delete_one = AsyncMock()
    sub_col.find_one_and_delete = AsyncMock()

    users_col = MagicMock()
    users_col.find_one_and_update = AsyncMock(return_value=users_find_returns)
    users_col.update_one = AsyncMock()

    monkeypatch.setattr(Subscription.objects, "_col", lambda self=Subscription.objects: sub_col)
    monkeypatch.setattr(Subscription.objects, "_users", lambda self=Subscription.objects: users_col)

    return sub_col, users_col


class TestSubscribeManager:

    def test_default_amount_uses_monto_minimo(self, monkeypatch):
        monkeypatch.setattr(
            Fund.objects, "get_fund_by_id", AsyncMock(return_value=_fund_dto())
        )
        # Balance starts at 500k, user can afford 50k
        _, users_col = _stub_collections(
            monkeypatch,
            users_find_returns={"_id": ObjectId(), "balance": 450_000},
        )
        tx_mock = AsyncMock(return_value=_tx_dto(amount=50_000, balance_after=450_000))
        monkeypatch.setattr(Transaction.objects, "create", tx_mock)

        result = _run(
            Subscription.objects.subscribe(user_id=str(ObjectId()), fund_id=3)
        )

        # The $inc debit was for the fund's monto_minimo (50 000).
        update_args = users_col.find_one_and_update.await_args
        assert update_args.args[1] == {"$inc": {"balance": -50_000}}
        # The subscription/result amount reflects the same value.
        assert result.subscription.amount == 50_000
        assert result.new_balance == 450_000

    def test_explicit_amount_above_minimum_succeeds(self, monkeypatch):
        monkeypatch.setattr(
            Fund.objects, "get_fund_by_id", AsyncMock(return_value=_fund_dto())
        )
        _, users_col = _stub_collections(
            monkeypatch,
            users_find_returns={"_id": ObjectId(), "balance": 300_000},
        )
        monkeypatch.setattr(
            Transaction.objects, "create",
            AsyncMock(return_value=_tx_dto(amount=200_000, balance_after=300_000)),
        )

        result = _run(
            Subscription.objects.subscribe(
                user_id=str(ObjectId()), fund_id=3, amount=200_000
            )
        )

        assert result.subscription.amount == 200_000
        assert result.new_balance == 300_000
        # The conditional matcher includes the $gte guard.
        matcher = users_col.find_one_and_update.await_args.args[0]
        assert matcher["balance"] == {"$gte": 200_000}

    def test_amount_below_minimum_raises(self, monkeypatch):
        monkeypatch.setattr(
            Fund.objects, "get_fund_by_id", AsyncMock(return_value=_fund_dto())
        )
        _stub_collections(monkeypatch, users_find_returns={"balance": 0})

        with pytest.raises(AmountBelowMinimumError):
            _run(
                Subscription.objects.subscribe(
                    user_id=str(ObjectId()), fund_id=3, amount=10_000
                )
            )

    def test_inactive_fund_raises(self, monkeypatch):
        monkeypatch.setattr(
            Fund.objects,
            "get_fund_by_id",
            AsyncMock(return_value=_fund_dto(activo=False)),
        )
        _stub_collections(monkeypatch)

        with pytest.raises(FundInactiveError):
            _run(
                Subscription.objects.subscribe(user_id=str(ObjectId()), fund_id=3)
            )

    def test_balance_exactly_equals_amount_succeeds_with_zero_balance(
        self, monkeypatch
    ):
        """Boundary: balance == amount must succeed and leave balance == 0."""
        monkeypatch.setattr(
            Fund.objects, "get_fund_by_id", AsyncMock(return_value=_fund_dto())
        )
        _, users_col = _stub_collections(
            monkeypatch,
            users_find_returns={"_id": ObjectId(), "balance": 0},
        )
        monkeypatch.setattr(
            Transaction.objects, "create",
            AsyncMock(return_value=_tx_dto(amount=500_000, balance_after=0)),
        )

        result = _run(
            Subscription.objects.subscribe(
                user_id=str(ObjectId()), fund_id=3, amount=500_000
            )
        )

        assert result.new_balance == 0

    def test_insufficient_balance_raises_with_english_message(self, monkeypatch):
        """When the $gte matcher rejects the update we surface InsufficientBalanceError.

        The exact wording lives in ``constants/subscriptions.py`` — the
        test pins the format produced by that template so a translation
        change in one place automatically updates this assertion.
        """
        monkeypatch.setattr(
            Fund.objects, "get_fund_by_id", AsyncMock(return_value=_fund_dto())
        )
        # find_one_and_update returns None → conditional matcher rejected the write.
        _stub_collections(monkeypatch, users_find_returns=None)

        with pytest.raises(InsufficientBalanceError) as exc_info:
            _run(
                Subscription.objects.subscribe(
                    user_id=str(ObjectId()), fund_id=3, amount=50_000
                )
            )
        assert str(exc_info.value) == (
            "Insufficient balance to subscribe to fund DEUDAPRIVADA"
        )

    def test_fast_path_409_when_subscription_exists(self, monkeypatch):
        """Pre-check finds an existing sub — no balance touched."""
        monkeypatch.setattr(
            Fund.objects, "get_fund_by_id", AsyncMock(return_value=_fund_dto())
        )
        _, users_col = _stub_collections(
            monkeypatch, existing_subscription={"_id": ObjectId()}
        )

        with pytest.raises(AlreadySubscribedError):
            _run(
                Subscription.objects.subscribe(user_id=str(ObjectId()), fund_id=3)
            )
        # Balance was never touched.
        users_col.find_one_and_update.assert_not_awaited()

    def test_concurrent_subscribe_loses_to_unique_index_and_compensates(self, monkeypatch):
        """Race: pre-check sees no sub; another request lands the insert first.

        The compound unique index fires DuplicateKeyError on our insert.
        Fallback mode must compensate the balance debit.
        """
        monkeypatch.setattr(
            Fund.objects, "get_fund_by_id", AsyncMock(return_value=_fund_dto())
        )
        sub_col, users_col = _stub_collections(
            monkeypatch,
            existing_subscription=None,  # pre-check is clean
            users_find_returns={"_id": ObjectId(), "balance": 450_000},
            sub_insert_raises=DuplicateKeyError("uniq_user_fund"),
        )

        with pytest.raises(AlreadySubscribedError):
            _run(
                Subscription.objects.subscribe(user_id=str(ObjectId()), fund_id=3)
            )

        # Compensation: balance restored with the inverse $inc.
        compensating_call = users_col.update_one.await_args
        assert compensating_call.args[1] == {"$inc": {"balance": 50_000}}

    def test_transaction_insert_failure_compensates_balance_and_subscription(
        self, monkeypatch
    ):
        """If the Transaction insert fails, BOTH prior steps must be undone."""
        monkeypatch.setattr(
            Fund.objects, "get_fund_by_id", AsyncMock(return_value=_fund_dto())
        )
        sub_col, users_col = _stub_collections(
            monkeypatch,
            users_find_returns={"_id": ObjectId(), "balance": 450_000},
        )
        monkeypatch.setattr(
            Transaction.objects, "create",
            AsyncMock(side_effect=RuntimeError("simulated DB outage")),
        )

        with pytest.raises(RuntimeError):
            _run(
                Subscription.objects.subscribe(user_id=str(ObjectId()), fund_id=3)
            )

        # Compensation: delete the subscription and restore balance.
        sub_col.delete_one.assert_awaited_once()
        compensating = users_col.update_one.await_args
        assert compensating.args[1] == {"$inc": {"balance": 50_000}}

    def test_transaction_carries_balance_before_and_after(self, monkeypatch):
        monkeypatch.setattr(
            Fund.objects, "get_fund_by_id", AsyncMock(return_value=_fund_dto())
        )
        _stub_collections(
            monkeypatch,
            users_find_returns={"_id": ObjectId(), "balance": 425_000},
        )
        tx_mock = AsyncMock(return_value=_tx_dto(amount=75_000, balance_after=425_000))
        monkeypatch.setattr(Transaction.objects, "create", tx_mock)

        _run(
            Subscription.objects.subscribe(
                user_id=str(ObjectId()), fund_id=3, amount=75_000
            )
        )

        kwargs = tx_mock.await_args.kwargs
        assert kwargs["balance_before"] == 500_000  # 425_000 + 75_000
        assert kwargs["balance_after"] == 425_000
        assert kwargs["type_"] == TransactionType.OPEN
        # The audit row carries the BTG-required UUID identifier.
        assert kwargs["transaction_id"]


class TestCancelManager:

    def test_returns_amount_to_balance_and_deletes_sub(self, monkeypatch):
        sub_id = ObjectId()
        user_oid = ObjectId()
        sub_doc = {
            "_id": sub_id,
            "user_id": user_oid,
            "fund_id": 3,
            "fund_nombre": "DEUDAPRIVADA",
            "amount": 100_000,
            "subscribed_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "transaction_id": "x",
        }
        sub_col, users_col = _stub_collections(
            monkeypatch,
            users_find_returns={"_id": user_oid, "balance": 500_000},
        )
        sub_col.find_one_and_delete = AsyncMock(return_value=sub_doc)
        tx_mock = AsyncMock(
            return_value=_tx_dto(
                type_=TransactionType.CANCEL, amount=100_000, balance_after=500_000
            )
        )
        monkeypatch.setattr(Transaction.objects, "create", tx_mock)

        result = _run(
            Subscription.objects.cancel(
                user_id=str(user_oid), subscription_id=str(sub_id)
            )
        )

        # Subscription was deleted.
        sub_col.find_one_and_delete.assert_awaited_once()
        # Balance credited with the exact amount.
        credit = users_col.find_one_and_update.await_args
        assert credit.args[1] == {"$inc": {"balance": 100_000}}
        # Transaction is of type CANCEL.
        assert tx_mock.await_args.kwargs["type_"] == TransactionType.CANCEL
        assert result.amount_returned == 100_000
        assert result.new_balance == 500_000

    def test_returns_original_amount_when_user_invested_above_minimum(
        self, monkeypatch
    ):
        sub_id = ObjectId()
        user_oid = ObjectId()
        sub_doc = {
            "_id": sub_id,
            "user_id": user_oid,
            "fund_id": 3,
            "fund_nombre": "DEUDAPRIVADA",
            "amount": 250_000,  # user invested ABOVE minimo (50 000)
            "subscribed_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "transaction_id": "x",
        }
        sub_col, _ = _stub_collections(
            monkeypatch,
            users_find_returns={"_id": user_oid, "balance": 500_000},
        )
        sub_col.find_one_and_delete = AsyncMock(return_value=sub_doc)
        monkeypatch.setattr(
            Transaction.objects, "create",
            AsyncMock(return_value=_tx_dto(type_=TransactionType.CANCEL, amount=250_000)),
        )

        result = _run(
            Subscription.objects.cancel(
                user_id=str(user_oid), subscription_id=str(sub_id)
            )
        )

        assert result.amount_returned == 250_000

    def test_nonexistent_or_not_owned_raises_subscription_not_found(self, monkeypatch):
        sub_col, _ = _stub_collections(monkeypatch)
        # find_one_and_delete matches on {_id, user_id} — returns None
        # both when the id is missing AND when the id belongs to another
        # user. Either way the manager must raise SubscriptionNotFoundError.
        sub_col.find_one_and_delete = AsyncMock(return_value=None)

        with pytest.raises(SubscriptionNotFoundError):
            _run(
                Subscription.objects.cancel(
                    user_id=str(ObjectId()), subscription_id=str(ObjectId())
                )
            )

    def test_invalid_subscription_id_raises_not_found(self, monkeypatch):
        _stub_collections(monkeypatch)
        with pytest.raises(SubscriptionNotFoundError):
            _run(
                Subscription.objects.cancel(
                    user_id=str(ObjectId()), subscription_id="not-an-oid"
                )
            )


class TestListAndAggregate:

    def test_get_user_total_invested_returns_zero_when_empty(self, monkeypatch):
        sub_col = MagicMock()
        # Aggregate yields nothing → total is 0.
        sub_col.aggregate = MagicMock(return_value=_async_iter([]))
        monkeypatch.setattr(Subscription.objects, "_col", lambda self=Subscription.objects: sub_col)

        result = _run(Subscription.objects.get_user_total_invested(str(ObjectId())))
        assert result == 0

    def test_get_user_total_invested_sums_amounts(self, monkeypatch):
        sub_col = MagicMock()
        sub_col.aggregate = MagicMock(return_value=_async_iter([{"_id": None, "total": 175_000}]))
        monkeypatch.setattr(Subscription.objects, "_col", lambda self=Subscription.objects: sub_col)

        result = _run(Subscription.objects.get_user_total_invested(str(ObjectId())))
        assert result == 175_000


# ---------- Helpers ----------


def _async_iter(items):
    class _Iter:
        def __init__(self, items):
            self._items = list(items)

        def __aiter__(self):
            return self

        async def __anext__(self):
            if not self._items:
                raise StopAsyncIteration
            return self._items.pop(0)

    return _Iter(items)
