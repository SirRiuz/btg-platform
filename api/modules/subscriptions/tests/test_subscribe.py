# Python
from datetime import datetime, timezone
from http import HTTPStatus
from unittest.mock import AsyncMock

# Libs
from bson import ObjectId

# Constants
from constants.subscriptions_exceptions import (
    AlreadySubscribedError,
    AmountBelowMinimumError,
    FundInactiveError,
    InsufficientBalanceError,
)
from constants.funds_exceptions import FundNotFoundError

# Module
from modules.subscriptions.manager import Subscription
from modules.subscriptions.schemas import (
    SubscribeResultDTO,
    SubscriptionDTO,
    TransactionDTO,
    TransactionType,
)
from modules.subscriptions.tests.conftest import (
    auth_headers,
    make_user_doc,
    wire_authn,
)


def _subscribe_result(
    *,
    fund_id: int = 3,
    fund_nombre: str = "DEUDAPRIVADA",
    amount: int = 50_000,
    new_balance: int = 450_000,
) -> SubscribeResultDTO:
    """Build a canonical SubscribeResultDTO so individual tests stay short."""
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return SubscribeResultDTO(
        subscription=SubscriptionDTO(
            id=str(ObjectId()),
            fund_id=fund_id,
            fund_nombre=fund_nombre,
            amount=amount,
            subscribed_at=now,
        ),
        transaction=TransactionDTO(
            id="11111111-1111-4111-8111-111111111111",
            type=TransactionType.OPEN,
            fund_id=fund_id,
            fund_nombre=fund_nombre,
            amount=amount,
            balance_before=new_balance + amount,
            balance_after=new_balance,
            timestamp=now,
            related_subscription_id=str(ObjectId()),
        ),
        new_balance=new_balance,
    )


class TestSubscribeRoute:

    def test_subscribe_with_default_amount_uses_monto_minimo(self, client, monkeypatch):
        """No body → manager invoked with amount=None (it defaults to monto_minimo)."""
        user = make_user_doc()
        wire_authn(monkeypatch, user)
        subscribe_mock = AsyncMock(return_value=_subscribe_result(amount=50_000))
        monkeypatch.setattr(Subscription.objects, "subscribe", subscribe_mock)

        response = client.post(
            "/funds/3/subscribe", json={}, headers=auth_headers(user)
        )

        assert response.status_code == HTTPStatus.CREATED
        body = response.json()
        assert body["subscription"]["amount"] == 50_000
        subscribe_mock.assert_awaited_once_with(
            user_id=str(user["_id"]), fund_id=3, amount=None
        )

    def test_subscribe_with_explicit_amount_above_minimum_succeeds(
        self, client, monkeypatch
    ):
        user = make_user_doc()
        wire_authn(monkeypatch, user)
        subscribe_mock = AsyncMock(return_value=_subscribe_result(amount=150_000, new_balance=350_000))
        monkeypatch.setattr(Subscription.objects, "subscribe", subscribe_mock)

        response = client.post(
            "/funds/3/subscribe",
            json={"amount": 150_000},
            headers=auth_headers(user),
        )

        assert response.status_code == HTTPStatus.CREATED
        body = response.json()
        assert body["subscription"]["amount"] == 150_000
        assert body["new_balance"] == 350_000
        assert body["transaction"]["type"] == "OPEN"
        subscribe_mock.assert_awaited_once_with(
            user_id=str(user["_id"]), fund_id=3, amount=150_000
        )

    def test_subscribe_with_amount_below_minimum_returns_422(self, client, monkeypatch):
        user = make_user_doc()
        wire_authn(monkeypatch, user)
        monkeypatch.setattr(
            Subscription.objects,
            "subscribe",
            AsyncMock(side_effect=AmountBelowMinimumError("DEUDAPRIVADA", 50_000)),
        )

        response = client.post(
            "/funds/3/subscribe", json={"amount": 10_000}, headers=auth_headers(user)
        )

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        body = response.json()
        assert body["error"] == "AMOUNT_BELOW_MINIMUM"
        assert "50000" in body["message"]
        assert "DEUDAPRIVADA" in body["message"]

    def test_subscribe_with_amount_exceeding_balance_returns_insufficient_balance(
        self, client, monkeypatch
    ):
        """Mirrors the BTG-brief case but with the project's English strings.

        The error code (``INSUFFICIENT_BALANCE``) is the stable contract;
        the human message is pinned against the constant so a translation
        change in one place automatically updates the test.
        """
        user = make_user_doc(balance=10_000)
        wire_authn(monkeypatch, user)
        monkeypatch.setattr(
            Subscription.objects,
            "subscribe",
            AsyncMock(side_effect=InsufficientBalanceError("FDO-ACCIONES")),
        )

        response = client.post(
            "/funds/4/subscribe", json={"amount": 250_000}, headers=auth_headers(user)
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST
        body = response.json()
        assert body["error"] == "INSUFFICIENT_BALANCE"
        assert body["message"] == "Insufficient balance to subscribe to fund FDO-ACCIONES"

    def test_subscribe_to_nonexistent_fund_returns_404(self, client, monkeypatch):
        user = make_user_doc()
        wire_authn(monkeypatch, user)
        monkeypatch.setattr(
            Subscription.objects, "subscribe", AsyncMock(side_effect=FundNotFoundError(999))
        )

        response = client.post(
            "/funds/999/subscribe", json={}, headers=auth_headers(user)
        )

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["error"] == "FUND_NOT_FOUND"

    def test_subscribe_to_inactive_fund_returns_410(self, client, monkeypatch):
        user = make_user_doc()
        wire_authn(monkeypatch, user)
        monkeypatch.setattr(
            Subscription.objects,
            "subscribe",
            AsyncMock(side_effect=FundInactiveError("FDO-ACCIONES")),
        )

        response = client.post(
            "/funds/4/subscribe", json={}, headers=auth_headers(user)
        )

        assert response.status_code == HTTPStatus.GONE
        body = response.json()
        assert body["error"] == "FUND_INACTIVE"
        assert "FDO-ACCIONES" in body["message"]

    def test_subscribe_twice_to_same_fund_returns_409(self, client, monkeypatch):
        user = make_user_doc()
        wire_authn(monkeypatch, user)
        monkeypatch.setattr(
            Subscription.objects,
            "subscribe",
            AsyncMock(side_effect=AlreadySubscribedError("DEUDAPRIVADA")),
        )

        response = client.post(
            "/funds/3/subscribe", json={}, headers=auth_headers(user)
        )

        assert response.status_code == HTTPStatus.CONFLICT
        body = response.json()
        assert body["error"] == "ALREADY_SUBSCRIBED"
        assert "DEUDAPRIVADA" in body["message"]
        assert "already subscribed" in body["message"]

    def test_subscribe_without_jwt_returns_401(self, client):
        response = client.post("/funds/3/subscribe", json={})
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.json()["error"] == "MISSING_TOKEN"

    def test_subscribe_with_zero_amount_rejected_by_pydantic(self, client, monkeypatch):
        user = make_user_doc()
        wire_authn(monkeypatch, user)

        response = client.post(
            "/funds/3/subscribe", json={"amount": 0}, headers=auth_headers(user)
        )

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert response.json()["error"] == "VALIDATION_ERROR"

    def test_subscribe_with_negative_amount_rejected_by_pydantic(
        self, client, monkeypatch
    ):
        user = make_user_doc()
        wire_authn(monkeypatch, user)

        response = client.post(
            "/funds/3/subscribe", json={"amount": -1}, headers=auth_headers(user)
        )

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_subscribe_response_carries_transaction_uuid_and_new_balance(
        self, client, monkeypatch
    ):
        user = make_user_doc()
        wire_authn(monkeypatch, user)
        result = _subscribe_result(amount=75_000, new_balance=425_000)
        monkeypatch.setattr(
            Subscription.objects, "subscribe", AsyncMock(return_value=result)
        )

        response = client.post(
            "/funds/1/subscribe", json={"amount": 75_000}, headers=auth_headers(user)
        )

        assert response.status_code == HTTPStatus.CREATED
        body = response.json()
        # The brief requires the response include the transaction id.
        assert body["transaction"]["id"] == result.transaction.id
        assert body["new_balance"] == 425_000
