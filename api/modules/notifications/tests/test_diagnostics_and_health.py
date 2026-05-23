# Python
import asyncio
import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

# Libs
import pytest
from botocore.exceptions import ClientError

# Module
from modules.notifications.diagnostics import (
    CheckResult,
    NotificationsHealth,
    log_startup_validation,
    validate_notifications_config,
)


def _run(coro):
    return asyncio.run(coro)


def _aws_settings(*, from_email="noreply@example.com", region="us-east-1"):
    return SimpleNamespace(
        notifications_provider="aws",
        aws_region=region,
        ses_from_email=from_email,
        sns_sender_id="FundsApp",
    )


def _log_settings():
    return SimpleNamespace(
        notifications_provider="log",
        aws_region="us-east-1",
        ses_from_email=None,
        sns_sender_id="FundsApp",
    )


def _ses_ok():
    """Build a stub SES client that succeeds on both probes."""
    client = MagicMock()
    client.get_send_quota.return_value = {
        "Max24HourSend": 200, "SentLast24Hours": 1, "MaxSendRate": 1,
    }
    client.get_identity_verification_attributes.return_value = {
        "VerificationAttributes": {
            "noreply@example.com": {"VerificationStatus": "Success"},
        }
    }
    return client


def _sns_ok(*, in_sandbox: bool = False):
    client = MagicMock()
    client.get_sms_attributes.return_value = {
        "attributes": {
            "DefaultSenderID": "FundsApp",
            "MonthlySpendLimit": "1.00",
            "DefaultSMSType": "Transactional",
        }
    }
    client.get_sms_sandbox_account_status.return_value = {"IsInSandbox": in_sandbox}
    return client


class TestValidateConfig:

    def test_log_provider_returns_healthy_without_aws_calls(self):
        report = _run(validate_notifications_config(settings_obj=_log_settings()))
        assert report.overall == "healthy"
        assert all(c.status == "ok" for c in report.checks)

    def test_aws_all_ok_returns_healthy(self):
        report = _run(validate_notifications_config(
            settings_obj=_aws_settings(),
            ses_client=_ses_ok(),
            sns_client=_sns_ok(in_sandbox=False),
        ))
        assert report.overall == "healthy"
        # All four probes present.
        names = {c.name for c in report.checks}
        assert names == {"ses.credentials", "ses.from_email", "sns.attributes", "sns.sandbox"}

    def test_sandbox_degrades_to_warning(self):
        report = _run(validate_notifications_config(
            settings_obj=_aws_settings(),
            ses_client=_ses_ok(),
            sns_client=_sns_ok(in_sandbox=True),
        ))
        assert report.overall == "degraded"
        sandbox = next(c for c in report.checks if c.name == "sns.sandbox")
        assert sandbox.status == "warning"
        assert "Exit SMS sandbox" in (sandbox.error or "")

    def test_unverified_from_email_is_error(self):
        ses = _ses_ok()
        ses.get_identity_verification_attributes.return_value = {
            "VerificationAttributes": {
                "noreply@example.com": {"VerificationStatus": "Pending"},
            }
        }
        report = _run(validate_notifications_config(
            settings_obj=_aws_settings(),
            ses_client=ses,
            sns_client=_sns_ok(),
        ))
        assert report.overall == "unhealthy"
        check = next(c for c in report.checks if c.name == "ses.from_email")
        assert check.status == "error"
        assert "NOT verified" in (check.error or "")

    def test_missing_from_email_is_error(self):
        s = _aws_settings(from_email=None)
        report = _run(validate_notifications_config(
            settings_obj=s,
            ses_client=_ses_ok(),
            sns_client=_sns_ok(),
        ))
        assert report.overall == "unhealthy"
        check = next(c for c in report.checks if c.name == "ses.from_email")
        assert check.status == "error"

    def test_aws_credentials_error_propagates_as_error(self):
        ses = MagicMock()
        ses.get_send_quota.side_effect = ClientError(
            {
                "Error": {"Code": "InvalidClientTokenId", "Message": "bad key"},
                "ResponseMetadata": {"RequestId": "r1", "HTTPStatusCode": 403},
            },
            "GetSendQuota",
        )
        report = _run(validate_notifications_config(
            settings_obj=_aws_settings(),
            ses_client=ses,
            sns_client=_sns_ok(),
        ))
        assert report.overall == "unhealthy"
        check = next(c for c in report.checks if c.name == "ses.credentials")
        assert check.status == "error"
        assert check.details["aws_error_code"] == "InvalidClientTokenId"


class TestStartupLogging:
    """``log_startup_validation`` must never raise — the API has to come
    up even when AWS is misconfigured."""

    def test_logs_summary_and_per_check(self, caplog, monkeypatch):
        # Patch the validator to skip the real boto3 calls.
        async def fake_validate(*, settings_obj, **_kw):
            return NotificationsHealth(
                overall="degraded",
                checks=[
                    CheckResult("ses.credentials", "ok", {"region": "us-east-1"}),
                    CheckResult("sns.sandbox", "warning", {"in_sandbox": True},
                                error="exit sandbox"),
                ],
                timestamp="2026-05-22T00:00:00Z",
            )

        import modules.notifications.diagnostics as diag
        monkeypatch.setattr(diag, "validate_notifications_config", fake_validate)

        with caplog.at_level(logging.INFO):
            _run(log_startup_validation(_aws_settings()))

        messages = [r.message for r in caplog.records]
        assert "notifications.startup.validated" in messages
        assert "notifications.startup.ses.credentials" in messages
        assert "notifications.startup.sns.sandbox" in messages

    def test_does_not_raise_when_validator_blows_up(self, caplog, monkeypatch):
        async def boom(*, settings_obj, **_kw):
            raise RuntimeError("unexpected")

        import modules.notifications.diagnostics as diag
        monkeypatch.setattr(diag, "validate_notifications_config", boom)

        # Must NOT raise.
        _run(log_startup_validation(_aws_settings()))
