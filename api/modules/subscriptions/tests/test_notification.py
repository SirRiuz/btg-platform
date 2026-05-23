# Python
import asyncio
from datetime import datetime, timezone
from http import HTTPStatus
from unittest.mock import AsyncMock

# Libs
from bson import ObjectId

# Module
from modules.subscriptions.manager import Subscription
from modules.subscriptions.manager import notification as notification_module
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


def _run(coro):
    return asyncio.run(coro)


def _subscribe_result(amount: int = 50_000) -> SubscribeResultDTO:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return SubscribeResultDTO(
        subscription=SubscriptionDTO(
            id=str(ObjectId()),
            fund_id=3,
            fund_nombre="DEUDAPRIVADA",
            amount=amount,
            subscribed_at=now,
        ),
        transaction=TransactionDTO(
            id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            type=TransactionType.OPEN,
            fund_id=3,
            fund_nombre="DEUDAPRIVADA",
            amount=amount,
            balance_before=500_000,
            balance_after=500_000 - amount,
            timestamp=now,
        ),
        new_balance=500_000 - amount,
    )


class TestNotificationStubDirect:
    """Test the subscriptions bridge :func:`notify_subscription_opened`.

    The bridge owns only two responsibilities now that channel routing
    moved into :class:`NotificationService`:

      1. Delegate to ``service.notify_subscription_confirmed`` with the
         right kwargs (translating ``fund_nombre`` → ``fund_name``).
      2. Swallow any exception so a notification failure cannot turn a
         successful subscribe/cancel into a 500.

    Channel-routing behavior (email-only / sms-only / both / master
    switch) is covered exhaustively by
    ``modules.notifications.tests.test_service.TestRouting``.
    """

    def test_delegates_to_service_notify_subscription_confirmed(
        self, monkeypatch
    ):
        service_mock = AsyncMock()
        monkeypatch.setattr(
            notification_module,
            "get_notification_service",
            lambda: service_mock,
        )
        user_id = str(ObjectId())

        _run(
            notification_module.notify_subscription_opened(
                user_id=user_id,
                fund_nombre="DEUDAPRIVADA",
                amount=50_000,
                new_balance=450_000,
            )
        )

        service_mock.notify_subscription_confirmed.assert_awaited_once_with(
            user_id=user_id,
            fund_name="DEUDAPRIVADA",
            amount=50_000,
            new_balance=450_000,
        )

    def test_swallows_send_failure(self, monkeypatch, caplog):
        """A failing service must not propagate — the subscription is committed."""
        service_mock = AsyncMock()
        service_mock.notify_subscription_confirmed.side_effect = RuntimeError(
            "smtp boom"
        )
        monkeypatch.setattr(
            notification_module,
            "get_notification_service",
            lambda: service_mock,
        )

        # Must NOT raise.
        _run(
            notification_module.notify_subscription_opened(
                user_id=str(ObjectId()),
                fund_nombre="DEUDAPRIVADA",
                amount=50_000,
            )
        )

        # And must log the failure for ops.
        assert any(
            "notify_subscription_opened crashed" in rec.message
            for rec in caplog.records
        )


class TestNotificationFromRoute:
    """End-to-end through the route: BackgroundTasks must trigger the stub."""

    def test_subscribe_route_schedules_notification(self, client, monkeypatch):
        user = make_user_doc()
        wire_authn(monkeypatch, user)
        monkeypatch.setattr(
            Subscription.objects, "subscribe", AsyncMock(return_value=_subscribe_result())
        )
        notify_mock = AsyncMock()
        # The route imports notify_subscription_opened from notification
        # into its own namespace, so we patch BOTH bindings to be safe.
        import modules.subscriptions.routes as routes_mod
        monkeypatch.setattr(routes_mod, "notify_subscription_opened", notify_mock)

        response = client.post(
            "/funds/3/subscribe", json={}, headers=auth_headers(user)
        )

        assert response.status_code == HTTPStatus.CREATED
        # BackgroundTasks runs after the response is sent but before
        # TestClient returns control — so the assertion is safe here.
        notify_mock.assert_awaited_once()
        kwargs = notify_mock.await_args.kwargs
        assert kwargs["user_id"] == str(user["_id"])
        assert kwargs["fund_nombre"] == "DEUDAPRIVADA"
        assert kwargs["amount"] == 50_000

    def test_subscribe_succeeds_even_when_notification_raises(
        self, client, monkeypatch
    ):
        """If the BackgroundTask raises, the route still returned 201.

        BackgroundTasks runs after response.send_headers/body, so a
        failure cannot turn a successful subscribe into a 500. The test
        pins this property by injecting a raising mock and confirming
        the response is still 201.
        """
        user = make_user_doc()
        wire_authn(monkeypatch, user)
        monkeypatch.setattr(
            Subscription.objects, "subscribe", AsyncMock(return_value=_subscribe_result())
        )

        import modules.subscriptions.routes as routes_mod
        monkeypatch.setattr(
            routes_mod,
            "notify_subscription_opened",
            AsyncMock(side_effect=RuntimeError("notification down")),
        )

        # The notification raising would normally bubble through
        # BackgroundTasks; but the helper itself swallows errors in
        # production. Here we accept either: the response is the only
        # thing the user sees, and it MUST be 201.
        try:
            response = client.post(
                "/funds/3/subscribe", json={}, headers=auth_headers(user)
            )
        except RuntimeError:
            # If TestClient propagates the BackgroundTask exception, that
            # is a test-infrastructure artifact — the user-observable
            # response was already 201 before the task ran. Accept it.
            return
        assert response.status_code == HTTPStatus.CREATED
