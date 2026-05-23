# Python
import asyncio
from unittest.mock import AsyncMock, MagicMock

# Libs
import pytest
from botocore.exceptions import ClientError

# Constants
from constants.notifications_exceptions import NotificationDeliveryError

# Module
from modules.notifications.adapters.ses_email import SesEmailAdapter
from modules.notifications.adapters.sns_sms import SnsSmsAdapter
from modules.notifications.ports import EmailMessage, SmsMessage


def _run(coro):
    return asyncio.run(coro)


class TestSesEmailAdapter:
    """Adapter wiring tests — we stub the underlying boto3 client and
    assert the exact parameters that reach it. This keeps the suite fast
    and offline; full integration against ``moto`` belongs in a separate
    suite that the CI pipeline runs less frequently."""

    def test_calls_boto3_with_correct_params(self, monkeypatch):
        boto_client = MagicMock()
        adapter = SesEmailAdapter(region="us-east-1", from_email="from@x.com")
        adapter._client = boto_client

        _run(adapter.send(EmailMessage(
            to="to@x.com", subject="Sub", body_text="text", body_html="<p>html</p>"
        )))

        boto_client.send_email.assert_called_once()
        kwargs = boto_client.send_email.call_args.kwargs
        assert kwargs["Source"] == "from@x.com"
        assert kwargs["Destination"]["ToAddresses"] == ["to@x.com"]
        assert kwargs["Message"]["Subject"] == {"Charset": "UTF-8", "Data": "Sub"}
        assert kwargs["Message"]["Body"]["Text"] == {"Charset": "UTF-8", "Data": "text"}
        assert kwargs["Message"]["Body"]["Html"] == {"Charset": "UTF-8", "Data": "<p>html</p>"}

    def test_omits_html_when_not_provided(self, monkeypatch):
        boto_client = MagicMock()
        adapter = SesEmailAdapter(region="us-east-1", from_email="from@x.com")
        adapter._client = boto_client

        _run(adapter.send(EmailMessage(
            to="to@x.com", subject="Sub", body_text="text", body_html=None,
        )))

        body = boto_client.send_email.call_args.kwargs["Message"]["Body"]
        assert "Html" not in body
        assert body["Text"]["Data"] == "text"

    def test_client_error_raises_delivery_error_with_aws_code(self):
        boto_client = MagicMock()
        boto_client.send_email.side_effect = ClientError(
            {"Error": {"Code": "MessageRejected", "Message": "boom"}},
            "SendEmail",
        )
        adapter = SesEmailAdapter(region="us-east-1", from_email="from@x.com")
        adapter._client = boto_client

        with pytest.raises(NotificationDeliveryError) as exc_info:
            _run(adapter.send(EmailMessage(
                to="to@x.com", subject="s", body_text="t",
            )))
        assert exc_info.value.channel == "email"
        # `aws_error_code` carries the machine-readable AWS code; `reason`
        # is the richer human string ("MessageRejected: boom") and is not
        # asserted strictly.
        assert exc_info.value.aws_error_code == "MessageRejected"


class TestSnsSmsAdapter:

    def test_calls_boto3_publish_with_phone_number_and_attributes(self):
        boto_client = MagicMock()
        adapter = SnsSmsAdapter(region="us-east-1", sender_id="BTGPactual")
        adapter._client = boto_client

        _run(adapter.send(SmsMessage(to="+573223438015", body="hi")))

        boto_client.publish.assert_called_once()
        kwargs = boto_client.publish.call_args.kwargs
        assert kwargs["PhoneNumber"] == "+573223438015"
        assert kwargs["Message"] == "hi"

    def test_uses_transactional_sms_type(self):
        boto_client = MagicMock()
        adapter = SnsSmsAdapter(region="us-east-1", sender_id="BTGPactual")
        adapter._client = boto_client

        _run(adapter.send(SmsMessage(to="+573223438015", body="hi")))

        attrs = boto_client.publish.call_args.kwargs["MessageAttributes"]
        assert attrs["AWS.SNS.SMS.SMSType"]["StringValue"] == "Transactional"

    def test_includes_sender_id_attribute(self):
        boto_client = MagicMock()
        adapter = SnsSmsAdapter(region="us-east-1", sender_id="MyBank")
        adapter._client = boto_client

        _run(adapter.send(SmsMessage(to="+573223438015", body="hi")))

        attrs = boto_client.publish.call_args.kwargs["MessageAttributes"]
        assert attrs["AWS.SNS.SMS.SenderID"]["StringValue"] == "MyBank"

    def test_client_error_raises_delivery_error_with_aws_code(self):
        boto_client = MagicMock()
        boto_client.publish.side_effect = ClientError(
            {"Error": {"Code": "InvalidParameter", "Message": "boom"}},
            "Publish",
        )
        adapter = SnsSmsAdapter(region="us-east-1", sender_id="BTGPactual")
        adapter._client = boto_client

        with pytest.raises(NotificationDeliveryError) as exc_info:
            _run(adapter.send(SmsMessage(to="+573223438015", body="hi")))
        assert exc_info.value.channel == "sms"
        assert exc_info.value.aws_error_code == "InvalidParameter"
