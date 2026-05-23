# Python
from datetime import datetime, timezone
from http import HTTPStatus
from unittest.mock import AsyncMock

# Libs
from bson import ObjectId

# Module
from modules.subscriptions.manager import Subscription, Transaction
from modules.subscriptions.schemas import (
    SubscriptionDTO,
    TransactionDTO,
    TransactionType,
)
from modules.subscriptions.tests.conftest import (
    auth_headers,
    make_user_doc,
    wire_authn,
)


def _sub_dto(*, fund_id: int, amount: int, fund_nombre: str = "DEUDAPRIVADA") -> SubscriptionDTO:
    return SubscriptionDTO(
        id=str(ObjectId()),
        fund_id=fund_id,
        fund_nombre=fund_nombre,
        amount=amount,
        subscribed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def _tx_dto(
    *,
    type_: TransactionType,
    fund_id: int = 3,
    fund_nombre: str = "DEUDAPRIVADA",
    amount: int = 50_000,
    balance_before: int = 500_000,
    balance_after: int = 450_000,
    when: datetime | None = None,
) -> TransactionDTO:
    return TransactionDTO(
        id=str(ObjectId()),
        type=type_,
        fund_id=fund_id,
        fund_nombre=fund_nombre,
        amount=amount,
        balance_before=balance_before,
        balance_after=balance_after,
        timestamp=when or datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


class TestListMySubscriptions:

    def test_returns_only_current_user_subscriptions(self, client, monkeypatch):
        user = make_user_doc(balance=350_000)
        wire_authn(monkeypatch, user)
        list_mock = AsyncMock(
            return_value=[
                _sub_dto(fund_id=3, amount=100_000),
                _sub_dto(fund_id=4, amount=50_000, fund_nombre="FDO-ACCIONES"),
            ]
        )
        monkeypatch.setattr(Subscription.objects, "list_active_subscriptions", list_mock)
        monkeypatch.setattr(
            Subscription.objects, "get_user_total_invested", AsyncMock(return_value=150_000)
        )

        response = client.get("/me/subscriptions", headers=auth_headers(user))

        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert body["total"] == 2
        assert body["total_invested"] == 150_000
        assert body["current_balance"] == 350_000
        # The manager was invoked with the JWT-derived user id (no path / body input).
        list_mock.assert_awaited_once_with(str(user["_id"]))

    def test_returns_money_conservation_invariant_components(self, client, monkeypatch):
        """`total_invested + current_balance` should reflect the initial 500 000.

        The response carries both — the test pins that the route exposes
        them so the frontend can render the invariant directly.
        """
        user = make_user_doc(balance=200_000)
        wire_authn(monkeypatch, user)
        monkeypatch.setattr(
            Subscription.objects,
            "list_active_subscriptions",
            AsyncMock(return_value=[_sub_dto(fund_id=3, amount=300_000)]),
        )
        monkeypatch.setattr(
            Subscription.objects, "get_user_total_invested", AsyncMock(return_value=300_000)
        )

        response = client.get("/me/subscriptions", headers=auth_headers(user))

        body = response.json()
        assert body["current_balance"] + body["total_invested"] == 500_000

    def test_list_subscriptions_without_jwt_returns_401(self, client):
        response = client.get("/me/subscriptions")
        assert response.status_code == HTTPStatus.UNAUTHORIZED


class TestListMyTransactions:

    def test_returns_all_types_ordered_desc(self, client, monkeypatch):
        """The manager guarantees DESC order — verify the route preserves it."""
        user = make_user_doc()
        wire_authn(monkeypatch, user)
        newer = _tx_dto(
            type_=TransactionType.CANCEL,
            when=datetime(2026, 2, 1, tzinfo=timezone.utc),
        )
        older = _tx_dto(
            type_=TransactionType.OPEN,
            when=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        list_mock = AsyncMock(return_value=([newer, older], 2))
        monkeypatch.setattr(Transaction.objects, "list_for_user", list_mock)

        response = client.get("/me/transactions", headers=auth_headers(user))

        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert [item["type"] for item in body["items"]] == ["CANCEL", "OPEN"]
        assert body["total"] == 2
        list_mock.assert_awaited_once_with(
            str(user["_id"]), skip=0, limit=20, type_=None
        )

    def test_pagination(self, client, monkeypatch):
        user = make_user_doc()
        wire_authn(monkeypatch, user)
        list_mock = AsyncMock(return_value=([], 100))
        monkeypatch.setattr(Transaction.objects, "list_for_user", list_mock)

        response = client.get(
            "/me/transactions?skip=20&limit=10", headers=auth_headers(user)
        )

        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert body["skip"] == 20
        assert body["limit"] == 10
        assert body["total"] == 100
        list_mock.assert_awaited_once_with(
            str(user["_id"]), skip=20, limit=10, type_=None
        )

    def test_filter_by_type(self, client, monkeypatch):
        user = make_user_doc()
        wire_authn(monkeypatch, user)
        list_mock = AsyncMock(
            return_value=([_tx_dto(type_=TransactionType.CANCEL)], 1)
        )
        monkeypatch.setattr(Transaction.objects, "list_for_user", list_mock)

        response = client.get(
            "/me/transactions?type=CANCEL", headers=auth_headers(user)
        )

        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert all(item["type"] == "CANCEL" for item in body["items"])
        list_mock.assert_awaited_once_with(
            str(user["_id"]), skip=0, limit=20, type_=TransactionType.CANCEL
        )

    def test_list_transactions_without_jwt_returns_401(self, client):
        response = client.get("/me/transactions")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_invalid_limit_returns_422(self, client, monkeypatch):
        user = make_user_doc()
        wire_authn(monkeypatch, user)

        response = client.get("/me/transactions?limit=500", headers=auth_headers(user))

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
