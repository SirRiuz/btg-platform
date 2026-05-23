# Python
import logging

# Module
from modules.notifications.phone import mask_for_log
from modules.notifications.ports import (
    EmailMessage,
    EmailSender,
    SmsMessage,
    SmsSender,
)


_logger = logging.getLogger(__name__)

_PREFIX = "[LOGGING ADAPTER]"


class LoggingAdapter(EmailSender, SmsSender):
    """Both-port adapter that logs instead of calling any provider.

    Two roles:

    1. **Local development** — let engineers exercise the full
       subscribe/cancel flow without AWS credentials. Logs show the
       exact payload that would have been sent.
    2. **Tests** — integration tests can wire this in and assert on the
       captured log records, instead of mocking the boto3 client.

    The class deliberately raises NOTHING (except programming errors
    like ``TypeError``), so it cannot be the source of a notification
    failure during local development.
    """

    async def send(self, message: EmailMessage | SmsMessage) -> None:
        """Single ``send`` implements both ports.

        The ABCs both declare ``async send(message)`` with different
        argument types — Python's nominal subtyping treats this as one
        method that accepts either, which is exactly what we want here.
        """
        if isinstance(message, EmailMessage):
            self._log_email(message)
        elif isinstance(message, SmsMessage):
            self._log_sms(message)
        else:
            raise TypeError(f"Unsupported message type: {type(message).__name__}")

    def _log_email(self, msg: EmailMessage) -> None:
        _logger.info(
            "%s EMAIL to=%s subject=%s\nbody_text=%s\nbody_html=%s",
            _PREFIX,
            msg.to,
            msg.subject,
            msg.body_text,
            msg.body_html if msg.body_html is not None else "<none>",
        )

    def _log_sms(self, msg: SmsMessage) -> None:
        # In dev we DO log the full phone number — it's the engineer's
        # own test number — and the full body — because the whole point
        # is "show me what would have been sent". Production never runs
        # this adapter (provider=aws), so no PII leaks to prod logs.
        _logger.info(
            "%s SMS to=%s (masked=%s)\nbody=%s",
            _PREFIX,
            msg.to,
            mask_for_log(msg.to),
            msg.body,
        )
