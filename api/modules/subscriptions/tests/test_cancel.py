# Python
from datetime import datetime, timezone
from http import HTTPStatus
from unittest.mock import AsyncMock

# Libs
from bson import ObjectId

# Constants
from constants.subscriptions_exceptions import SubscriptionNotFoundError

# Module
from modules.subscriptions.manager import Subscription
from modules.subscriptions.schemas import (
    CancelResultDTO,
    TransactionDTO,
    TransactionType,
)
from modules.subscriptions.tests.conftest import (
    auth_headers,
    make_user_doc,
    wire_authn,
)


def _cancel_result(
    *,
    fund_nombre: str = "DEUDAPRIVADA",
    amount: int = 50_000,
    new_balance: int = 500_000,
    transaction_id: str = "22222222-2222-4222-8222-222222222222",
) -> CancelResultDTO:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return CancelResultDTO(
        fund_nombre=fund_nombre,
        amount_returned=amount,
        new_balance=new_balance,
        transaction=TransactionDTO(
            id=transaction_id,
            type=TransactionType.CANCEL,
            fund_id=3,
            fund_nombre=fund_nombre,
            amount=amount,
            balance_before=new_balance - amount,
            balance_after=new_balance,
            timestamp=now,
            related_subscription_id=str(ObjectId()),
        ),
    )


class TestCancelRoute:

    def test_cancel_returns_amount_and_new_balance(self, client, monkeypatch):
        """Happy path: response carries the brief-required fields."""
        user = make_user_doc(balance=450_000)
        wire_authn(monkeypatch, user)
        sub_id = str(ObjectId())
        cancel_mock = AsyncMock(return_value=_cancel_result(amount=50_000, new_balance=500_000))
        monkeypatch.setattr(Subscription.objects, "cancel", cancel_mock)

        response = client.delete(f"/subscriptions/{sub_id}", headers=auth_headers(user))

        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert body["amount_returned"] == 50_000
        assert body["new_balance"] == 500_000
        assert body["fund_nombre"] == "DEUDAPRIVADA"
        assert body["transaction_id"]
        cancel_mock.assert_awaited_once_with(
            user_id=str(user["_id"]), subscription_id=sub_id
        )

    def test_cancel_returns_original_amount_not_monto_minimo(self, client, monkeypatch):
        """A user who subscribed ABOVE the minimum gets their actual amount back."""
        user = make_user_doc(balance=250_000)
        wire_authn(monkeypatch, user)
        # User subscribed with 250 000 on DEUDAPRIVADA (monto_minimo=50 000)
        monkeypatch.setattr(
            Subscription.objects,
            "cancel",
            AsyncMock(
                return_value=_cancel_result(
                    fund_nombre="DEUDAPRIVADA",
                    amount=250_000,  # the actual subscribed amount
                    new_balance=500_000,
                )
            ),
        )

        response = client.delete(
            f"/subscriptions/{ObjectId()}", headers=auth_headers(user)
        )

        assert response.status_code == HTTPStatus.OK
        # 250 000 returned — NOT the 50 000 monto_minimo. This pin is what
        # protects users who invested above the minimum from being short-changed.
        assert response.json()["amount_returned"] == 250_000

    def test_cancel_nonexistent_subscription_returns_404(self, client, monkeypatch):
        user = make_user_doc()
        wire_authn(monkeypatch, user)
        monkeypatch.setattr(
            Subscription.objects,
            "cancel",
            AsyncMock(side_effect=SubscriptionNotFoundError()),
        )

        response = client.delete(
            f"/subscriptions/{ObjectId()}", headers=auth_headers(user)
        )

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["error"] == "SUBSCRIPTION_NOT_FOUND"
        assert response.json()["message"] == "Subscription not found"

    def test_cancel_other_user_subscription_returns_404_not_403(
        self, client, monkeypatch
    ):
        """Security pin: ownership mismatch must look identical to not-found.

        Returning 403 would let an attacker enumerate subscription IDs
        across users. We always collapse to 404. The manager owns the
        check — the test verifies the route does not leak the difference.
        """
        attacker = make_user_doc()
        wire_authn(monkeypatch, attacker)
        # Manager raises SubscriptionNotFoundError both for missing AND
        # for "exists but not yours". Verify same status + same body.
        monkeypatch.setattr(
            Subscription.objects,
            "cancel",
            AsyncMock(side_effect=SubscriptionNotFoundError()),
        )

        response = client.delete(
            f"/subscriptions/{ObjectId()}", headers=auth_headers(attacker)
        )

        assert response.status_code == HTTPStatus.NOT_FOUND  # NOT 403
        assert response.json()["error"] == "SUBSCRIPTION_NOT_FOUND"

    def test_cancel_with_invalid_objectid_returns_404(self, client, monkeypatch):
        """A malformed id is collapsed to the same 404 — never a 500."""
        user = make_user_doc()
        wire_authn(monkeypatch, user)
        monkeypatch.setattr(
            Subscription.objects,
            "cancel",
            AsyncMock(side_effect=SubscriptionNotFoundError()),
        )

        response = client.delete(
            "/subscriptions/not-an-objectid", headers=auth_headers(user)
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_cancel_without_jwt_returns_401(self, client):
        response = client.delete(f"/subscriptions/{ObjectId()}")
        assert response.status_code == HTTPStatus.UNAUTHORIZED
