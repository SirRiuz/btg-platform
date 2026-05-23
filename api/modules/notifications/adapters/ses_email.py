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
from modules.notifications.ports import EmailMessage, EmailSender


_logger = logging.getLogger(__name__)


class SesEmailAdapter(EmailSender):
    """AWS SES implementation of the :class:`EmailSender` port.

    Wraps ``boto3.client('ses').send_email`` (a synchronous SDK call) in
    :func:`asyncio.to_thread` so it never blocks the event loop. boto3
    already handles retries with exponential backoff internally.

    The adapter is *intentionally* talkative on failure: every
    ``ClientError`` is decomposed into structured fields
    (``aws_error_code``, ``aws_error_message``, ``aws_request_id``,
    ``http_status``) plus a curated ``diagnostic_hint`` from
    :mod:`modules.notifications.diagnostics`. The combination is what
    turns a 1am page from "SES failed" into "MessageRejected, recipient
    not verified in sandbox, here's the AWS console link".
    """

    def __init__(self, *, region: str, from_email: str) -> None:
        self._from_email = from_email
        self._region = region
        self._client = boto3.client("ses", region_name=region)

    async def send(self, message: EmailMessage) -> None:
        """Deliver ``message`` via SES.

        Raises:
            NotificationDeliveryError: SES rejected the message or a
                transport-level error occurred. Carries the AWS error
                code so dashboards can group failures by root cause.
        """
        body: dict[str, dict[str, str]] = {
            "Text": {"Charset": "UTF-8", "Data": message.body_text},
        }
        if message.body_html is not None:
            body["Html"] = {"Charset": "UTF-8", "Data": message.body_html}

        params: dict[str, Any] = {
            "Source": self._from_email,
            "Destination": {"ToAddresses": [message.to]},
            "Message": {
                "Subject": {"Charset": "UTF-8", "Data": message.subject},
                "Body": body,
            },
        }

        try:
            response = await asyncio.to_thread(self._client.send_email, **params)
        except ClientError as exc:
            meta = extract_error_metadata(exc)
            diagnostic = hint_for(service="ses", code=meta["aws_error_code"])
            _logger.error(
                "ses.send_email.failed",
                extra={
                    **meta,
                    "to": message.to,
                    "from": self._from_email,
                    "region": self._region,
                    "subject": message.subject,
                    "diagnostic_hint": diagnostic,
                },
            )
            raise NotificationDeliveryError(
                channel="email",
                reason=f"{meta['aws_error_code']}: {meta['aws_error_message']}",
                aws_error_code=meta["aws_error_code"],
                aws_request_id=meta["aws_request_id"],
            ) from exc
        except BotoCoreError as exc:
            # Connection / DNS / signing-machinery failures — boto3 hasn't
            # even reached AWS yet, so there is no aws_error_code.
            _logger.error(
                "ses.send_email.transport_failed",
                extra={
                    "to": message.to,
                    "from": self._from_email,
                    "region": self._region,
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                    "diagnostic_hint": (
                        "boto3 could not reach AWS. Check connectivity, DNS "
                        "(sts.amazonaws.com, email.<region>.amazonaws.com), "
                        "and that the boto3 version is current."
                    ),
                },
            )
            raise NotificationDeliveryError(
                channel="email", reason=type(exc).__name__
            ) from exc

        _logger.info(
            "ses.send_email.success",
            extra={
                "to": message.to,
                "from": self._from_email,
                "subject": message.subject,
                "message_id": response.get("MessageId", ""),
                "region": self._region,
            },
        )
