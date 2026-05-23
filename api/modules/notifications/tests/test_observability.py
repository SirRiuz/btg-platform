# Python
import asyncio
import logging
from unittest.mock import MagicMock

# Libs
import pytest
from botocore.exceptions import ClientError

# Constants
from constants.notifications_exceptions import NotificationDeliveryError

# Module
from modules.notifications.adapters.ses_email import SesEmailAdapter
from modules.notifications.adapters.sns_sms import SnsSmsAdapter
from modules.notifications.diagnostics import (
    DIAGNOSTIC_HINTS_SES,
    DIAGNOSTIC_HINTS_SNS,
    extract_error_metadata,
    hint_for,
)
from modules.notifications.ports import EmailMessage, SmsMessage


def _run(coro):
    return asyncio.run(coro)


def _ses_client_with_error(code: str, message: str, request_id: str = "req-123"):
    client = MagicMock()
    client.send_email.side_effect = ClientError(
        {
            "Error": {"Code": code, "Message": message},
            "ResponseMetadata": {"RequestId": request_id, "HTTPStatusCode": 400},
        },
        "SendEmail",
    )
    return client


def _sns_client_with_error(code: str, message: str, request_id: str = "req-456"):
    client = MagicMock()
    client.publish.side_effect = ClientError(
        {
            "Error": {"Code": code, "Message": message},
            "ResponseMetadata": {"RequestId": request_id, "HTTPStatusCode": 400},
        },
        "Publish",
    )
    return client


class TestSesErrorLogging:

    def test_logs_aws_code_message_request_id_and_diagnostic(self, caplog):
        client = _ses_client_with_error(
            "MessageRejected",
            "Email address is not verified.",
            "abc-def-123",
        )
        adapter = SesEmailAdapter(region="us-east-1", from_email="from@x.com")
        adapter._client = client

        with caplog.at_level(logging.ERROR):
            with pytest.raises(NotificationDeliveryError) as exc_info:
                _run(adapter.send(EmailMessage(
                    to="to@x.com", subject="s", body_text="t",
                )))

        # The structured fields must all land in extras.
        record = next(r for r in caplog.records if r.message == "ses.send_email.failed")
        assert record.aws_error_code == "MessageRejected"
        assert "not verified" in record.aws_error_message
        assert record.aws_request_id == "abc-def-123"
        assert record.http_status == 400
        assert record.to == "to@x.com"
        assert record.region == "us-east-1"
        # The diagnostic hint is the one from the SES table, not the fallback.
        assert "sandbox" in record.diagnostic_hint.lower()

        # The exception preserves the code so consumers can group by root cause.
        assert exc_info.value.aws_error_code == "MessageRejected"
        assert exc_info.value.aws_request_id == "abc-def-123"

    def test_logs_unknown_code_falls_back_to_generic_hint(self, caplog):
        client = _ses_client_with_error("SomeFutureError", "boom")
        adapter = SesEmailAdapter(region="us-east-1", from_email="from@x.com")
        adapter._client = client

        with caplog.at_level(logging.ERROR):
            with pytest.raises(NotificationDeliveryError):
                _run(adapter.send(EmailMessage(
                    to="to@x.com", subject="s", body_text="t",
                )))

        record = next(r for r in caplog.records if r.message == "ses.send_email.failed")
        assert "CloudTrail" in record.diagnostic_hint

    def test_success_log_includes_message_id(self, caplog):
        client = MagicMock()
        client.send_email.return_value = {"MessageId": "0102018f-deadbeef"}
        adapter = SesEmailAdapter(region="us-east-1", from_email="from@x.com")
        adapter._client = client

        with caplog.at_level(logging.INFO):
            _run(adapter.send(EmailMessage(
                to="to@x.com", subject="s", body_text="t",
            )))

        record = next(r for r in caplog.records if r.message == "ses.send_email.success")
        assert record.message_id == "0102018f-deadbeef"
        assert record.region == "us-east-1"


class TestSnsErrorLogging:

    def test_masks_phone_in_info_logs(self, caplog):
        client = MagicMock()
        client.publish.return_value = {"MessageId": "sns-msg-1"}
        adapter = SnsSmsAdapter(region="us-east-1", sender_id="BTGPactual")
        adapter._client = client

        with caplog.at_level(logging.INFO):
            _run(adapter.send(SmsMessage(to="+573223438015", body="hi")))

        record = next(r for r in caplog.records if r.message == "sns.publish.success")
        assert record.to_masked == "+57***8015"
        # INFO level never carries the full destination.
        assert not hasattr(record, "to_full")

    def test_full_phone_only_logged_at_debug_level(self, caplog):
        client = MagicMock()
        client.publish.return_value = {"MessageId": "sns-msg-2"}
        adapter = SnsSmsAdapter(region="us-east-1", sender_id="BTGPactual")
        adapter._client = client

        with caplog.at_level(logging.DEBUG):
            _run(adapter.send(SmsMessage(to="+573223438015", body="hi")))

        debug_records = [r for r in caplog.records if r.levelname == "DEBUG"]
        assert any(getattr(r, "to_full", None) == "+573223438015" for r in debug_records)

    def test_failure_log_includes_aws_code_and_diagnostic(self, caplog):
        client = _sns_client_with_error("InvalidParameter", "Invalid phone number.")
        adapter = SnsSmsAdapter(region="us-east-1", sender_id="BTGPactual")
        adapter._client = client

        with caplog.at_level(logging.ERROR):
            with pytest.raises(NotificationDeliveryError) as exc_info:
                _run(adapter.send(SmsMessage(to="+573223438015", body="hi")))

        record = next(r for r in caplog.records if r.message == "sns.publish.failed")
        assert record.aws_error_code == "InvalidParameter"
        assert record.aws_request_id == "req-456"
        # SNS-specific diagnostic table fires.
        assert "E.164" in record.diagnostic_hint or "sandbox" in record.diagnostic_hint
        # Even the failure log keeps the destination masked.
        assert record.to_masked == "+57***8015"
        assert not hasattr(record, "to_full")
        # Exception carries the code.
        assert exc_info.value.aws_error_code == "InvalidParameter"


class TestDiagnosticHintTable:
    """Pin a few well-known codes so a refactor cannot silently drop them."""

    @pytest.mark.parametrize("code", [
        "MessageRejected", "MailFromDomainNotVerified", "AccessDenied",
        "InvalidClientTokenId", "SignatureDoesNotMatch", "Throttling",
    ])
    def test_ses_codes_have_hints(self, code):
        assert code in DIAGNOSTIC_HINTS_SES
        assert hint_for(service="ses", code=code) != ""

    @pytest.mark.parametrize("code", [
        "InvalidParameter", "AuthorizationError", "ThrottlingException",
        "EndpointDisabled", "OptedOut",
    ])
    def test_sns_codes_have_hints(self, code):
        assert code in DIAGNOSTIC_HINTS_SNS
        assert hint_for(service="sns", code=code) != ""

    def test_unknown_code_returns_generic_hint(self):
        assert "CloudTrail" in hint_for(service="ses", code="ZZZ")
        assert "CloudTrail" in hint_for(service="sns", code="YYY")


class TestExtractErrorMetadata:

    def test_pulls_all_four_fields(self):
        exc = ClientError(
            {
                "Error": {"Code": "Throttling", "Message": "Slow down"},
                "ResponseMetadata": {"RequestId": "req-9", "HTTPStatusCode": 400},
            },
            "SendEmail",
        )
        meta = extract_error_metadata(exc)
        assert meta == {
            "aws_error_code": "Throttling",
            "aws_error_message": "Slow down",
            "aws_request_id": "req-9",
            "http_status": 400,
        }

    def test_missing_response_returns_safe_defaults(self):
        exc = ClientError({}, "SendEmail")
        meta = extract_error_metadata(exc)
        assert meta["aws_error_code"] == "Unknown"
        assert meta["aws_request_id"] == ""


class TestSecretsNeverInLogs:
    """Defense in depth: even if a secret slips into an extra=, the JSON
    formatter must redact it."""

    def test_redactor_replaces_secret_like_keys(self):
        from core.logging import _redact, _REDACTION_MARKER

        assert _redact("aws_secret_access_key", "abc") == _REDACTION_MARKER
        assert _redact("jwt_secret_key", "xyz") == _REDACTION_MARKER
        assert _redact("authorization", "Bearer xx") == _REDACTION_MARKER
        # Safe fields pass through.
        assert _redact("aws_request_id", "req-1") == "req-1"
        assert _redact("aws_error_code", "Throttling") == "Throttling"
