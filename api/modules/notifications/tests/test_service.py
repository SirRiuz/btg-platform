# Python
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

# Libs
import pytest

# Constants
from constants.notifications_exceptions import NotificationDeliveryError

# Module
from modules.notifications.ports import EmailMessage, EmailSender, SmsMessage, SmsSender
from modules.notifications.service import NotificationService


def _run(coro):
    return asyncio.run(coro)


def _profile(*, email="user@example.com", phone="+573223438015", first_name="Mateo"):
    """Return an object that looks like ``UserProfileResponse`` for the service."""
    return SimpleNamespace(email=email, phone=phone, first_name=first_name)


class _FakeEmail(EmailSender):
    def __init__(self):
        self.calls: list[EmailMessage] = []

    async def send(self, message):
        self.calls.append(message)


class _FakeSms(SmsSender):
    def __init__(self):
        self.calls: list[SmsMessage] = []

    async def send(self, message):
        self.calls.append(message)


class _FailingEmail(EmailSender):
    async def send(self, message):
        raise NotificationDeliveryError(channel="email", reason="ProviderDown")


class _FailingSms(SmsSender):
    async def send(self, message):
        raise NotificationDeliveryError(channel="sms", reason="ProviderDown")


def _account_mock(*, email_ok: bool, sms_ok: bool, profile=None):
    """Build an Account-like object with the routing flags pre-set."""
    return SimpleNamespace(
        get_profile=AsyncMock(return_value=profile or _profile()),
        can_receive_email=AsyncMock(return_value=email_ok),
        can_receive_sms=AsyncMock(return_value=sms_ok),
    )


class TestRouting:

    def test_sends_email_when_email_enabled_only(self):
        email = _FakeEmail()
        sms = _FakeSms()
        svc = NotificationService(
            email_sender=email, sms_sender=sms,
            account=_account_mock(email_ok=True, sms_ok=False),
        )

        _run(svc.notify_subscription_confirmed(
            user_id="u1", fund_name="DEUDAPRIVADA", amount=50_000, new_balance=450_000
        ))

        assert len(email.calls) == 1
        assert len(sms.calls) == 0
        assert "DEUDAPRIVADA" in email.calls[0].subject

    def test_sends_sms_when_sms_enabled_only(self):
        email = _FakeEmail()
        sms = _FakeSms()
        svc = NotificationService(
            email_sender=email, sms_sender=sms,
            account=_account_mock(email_ok=False, sms_ok=True),
        )

        _run(svc.notify_subscription_confirmed(
            user_id="u1", fund_name="DEUDAPRIVADA", amount=50_000, new_balance=450_000
        ))

        assert len(email.calls) == 0
        assert len(sms.calls) == 1
        # E.164 normalized.
        assert sms.calls[0].to == "+573223438015"

    def test_sends_both_when_both_enabled(self):
        email = _FakeEmail()
        sms = _FakeSms()
        svc = NotificationService(
            email_sender=email, sms_sender=sms,
            account=_account_mock(email_ok=True, sms_ok=True),
        )

        _run(svc.notify_subscription_confirmed(
            user_id="u1", fund_name="FDO-ACCIONES", amount=250_000, new_balance=250_000
        ))

        assert len(email.calls) == 1
        assert len(sms.calls) == 1

    def test_sends_nothing_when_both_disabled(self):
        email = _FakeEmail()
        sms = _FakeSms()
        svc = NotificationService(
            email_sender=email, sms_sender=sms,
            account=_account_mock(email_ok=False, sms_ok=False),
        )

        _run(svc.notify_subscription_confirmed(
            user_id="u1", fund_name="X", amount=1, new_balance=0
        ))

        assert email.calls == []
        assert sms.calls == []

    def test_master_switch_off_skips_everything(self):
        email = _FakeEmail()
        sms = _FakeSms()
        account = _account_mock(email_ok=True, sms_ok=True)
        svc = NotificationService(
            email_sender=email, sms_sender=sms, account=account, enabled=False
        )

        _run(svc.notify_subscription_confirmed(
            user_id="u1", fund_name="X", amount=1, new_balance=0
        ))

        # Profile not even loaded — the master switch short-circuits before.
        account.get_profile.assert_not_awaited()
        assert email.calls == []
        assert sms.calls == []


class TestChannelIsolation:

    def test_email_failure_does_not_block_sms(self):
        sms = _FakeSms()
        svc = NotificationService(
            email_sender=_FailingEmail(), sms_sender=sms,
            account=_account_mock(email_ok=True, sms_ok=True),
        )

        # Must NOT raise.
        _run(svc.notify_subscription_confirmed(
            user_id="u1", fund_name="X", amount=1, new_balance=0
        ))

        assert len(sms.calls) == 1  # SMS went out despite email failing

    def test_sms_failure_does_not_block_email(self):
        email = _FakeEmail()
        svc = NotificationService(
            email_sender=email, sms_sender=_FailingSms(),
            account=_account_mock(email_ok=True, sms_ok=True),
        )

        _run(svc.notify_subscription_confirmed(
            user_id="u1", fund_name="X", amount=1, new_balance=0
        ))

        assert len(email.calls) == 1  # Email went out despite SMS failing

    def test_failures_logged_but_swallowed(self, caplog):
        import logging

        svc = NotificationService(
            email_sender=_FailingEmail(), sms_sender=_FailingSms(),
            account=_account_mock(email_ok=True, sms_ok=True),
        )
        with caplog.at_level(logging.WARNING):
            _run(svc.notify_subscription_confirmed(
                user_id="u1", fund_name="X", amount=1, new_balance=0
            ))

        # Both channels logged their failure with reason=ProviderDown.
        messages = [r.message for r in caplog.records]
        assert any("notify.email.failed" in m for m in messages)
        assert any("notify.sms.failed" in m for m in messages)

    def test_cancelled_event_uses_cancelled_template(self):
        email = _FakeEmail()
        svc = NotificationService(
            email_sender=email, sms_sender=_FakeSms(),
            account=_account_mock(email_ok=True, sms_ok=False),
        )

        _run(svc.notify_subscription_cancelled(
            user_id="u1", fund_name="DEUDAPRIVADA", amount=50_000, new_balance=500_000
        ))

        # The cancellation copy mentions "cancelled" / "Refunded".
        assert "cancelled" in email.calls[0].subject.lower()
        assert "Refunded" in email.calls[0].body_text or "refund" in email.calls[0].body_text.lower()
