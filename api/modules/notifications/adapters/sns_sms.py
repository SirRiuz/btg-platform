# Python
import asyncio
import logging
from typing import Any

# Libs
import boto3
from botocore.exceptions import BotoCoreError, ClientError

# Constants
from constants.notifications_exceptions import NotificationDeliveryError

# Module
from modules.notifications.diagnostics import (
    extract_error_metadata,
    hint_for,
)
from modules.notifications.phone import mask_for_log
from modules.notifications.ports import SmsMessage, SmsSender


_logger = logging.getLogger(__name__)


class SnsSmsAdapter(SmsSender):
    """AWS SNS implementation of the :class:`SmsSender` port.

    Publishes directly to a phone number (``PhoneNumber`` parameter), NOT
    to a topic — the platform needs targeted, transactional SMS, not
    broadcasts.

    Two ``MessageAttributes`` shape every send:

    * ``AWS.SNS.SMS.SenderID`` — alphanumeric sender id; honored in
      most of LATAM/Europe/Asia, silently replaced by a long number in
      USA/Canada.
    * ``AWS.SNS.SMS.SMSType=Transactional`` — opts out of promotional
      throttling for materially better latency at the same price.

    Privacy: in INFO logs the phone number is masked to ``+57***1234``
    (country prefix + last 4). The full number is only logged at DEBUG
    level, on the assumption that DEBUG is only enabled when an engineer
    is actively troubleshooting in a controlled environment.
    """

    def __init__(self, *, region: str, sender_id: str = "BTGPactual") -> None:
        self._sender_id = sender_id
        self._region = region
        self._client = boto3.client("sns", region_name=region)

    async def send(self, message: SmsMessage) -> None:
        """Deliver ``message`` via SNS.

        Raises:
            NotificationDeliveryError: SNS rejected the message or a
                transport-level error occurred. Carries the AWS error
                code so dashboards can group failures by root cause.
        """
        params: dict[str, Any] = {
            "PhoneNumber": message.to,
            "Message": message.body,
            "MessageAttributes": {
                "AWS.SNS.SMS.SenderID": {
                    "DataType": "String",
                    "StringValue": self._sender_id,
                },
                "AWS.SNS.SMS.SMSType": {
                    "DataType": "String",
                    "StringValue": "Transactional",
                },
            },
        }

        masked = mask_for_log(message.to)

        try:
            response = await asyncio.to_thread(self._client.publish, **params)
        except ClientError as exc:
            meta = extract_error_metadata(exc)
            diagnostic = hint_for(service="sns", code=meta["aws_error_code"])
            _logger.error(
                "sns.publish.failed",
                extra={
                    **meta,
                    "to_masked": masked,
                    "sender_id": self._sender_id,
                    "region": self._region,
                    "diagnostic_hint": diagnostic,
                },
            )
            # Full destination only at DEBUG. INFO/WARNING/ERROR stay masked.
            _logger.debug(
                "sns.publish.failed.full_target",
                extra={"to_full": message.to, "aws_request_id": meta["aws_request_id"]},
            )
            raise NotificationDeliveryError(
                channel="sms",
                reason=f"{meta['aws_error_code']}: {meta['aws_error_message']}",
                aws_error_code=meta["aws_error_code"],
                aws_request_id=meta["aws_request_id"],
            ) from exc
        except BotoCoreError as exc:
            _logger.error(
                "sns.publish.transport_failed",
                extra={
                    "to_masked": masked,
                    "region": self._region,
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                    "diagnostic_hint": (
                        "boto3 could not reach AWS. Check connectivity and "
                        "the sns.<region>.amazonaws.com endpoint."
                    ),
                },
            )
            raise NotificationDeliveryError(
                channel="sms", reason=type(exc).__name__
            ) from exc

        _logger.info(
            "sns.publish.success",
            extra={
                "to_masked": masked,
                "sender_id": self._sender_id,
                "message_id": response.get("MessageId", ""),
                "region": self._region,
            },
        )
        _logger.debug(
            "sns.publish.success.full_target",
            extra={"to_full": message.to, "message_id": response.get("MessageId", "")},
        )
