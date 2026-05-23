# Constants
from constants.exceptions import DomainError
from constants.notifications import NotificationErrorCodes, NotificationMessages


class NotificationError(DomainError):
    """Base for notifications-domain errors."""

    code: str = "NOTIFICATION_ERROR"
    status_code: int = 500


class NotificationDeliveryError(NotificationError):
    """Raised by adapters when the underlying provider returns an error.

    The exception is *not* surfaced to API callers — every send happens
    inside the :class:`NotificationService` channel guards, which catch
    it, log it, and move on. The class exists so the call site can
    distinguish a delivery failure from a programming bug (which still
    raises a vanilla exception and bubbles up).

    The ``aws_error_code`` field is the *machine-readable* code AWS
    returned (e.g. ``MessageRejected``, ``Throttling``). Carrying it on
    the exception lets ops dashboards group failures by root cause
    without having to grep the human ``reason`` string.
    """

    code = NotificationErrorCodes.DELIVERY_FAILED
    status_code = 502  # Bad gateway — accurate if it ever escaped

    def __init__(
        self,
        *,
        channel: str,
        reason: str,
        aws_error_code: str | None = None,
        aws_request_id: str | None = None,
    ) -> None:
        self.channel = channel
        self.reason = reason
        self.aws_error_code = aws_error_code
        self.aws_request_id = aws_request_id
        super().__init__(
            NotificationMessages.DELIVERY_FAILED.format(channel=channel, reason=reason)
        )


class InvalidPhoneError(NotificationError):
    """Raised by the phone normalizer when input is unparseable."""

    code = NotificationErrorCodes.INVALID_PHONE
    status_code = 422
    message = NotificationMessages.INVALID_PHONE
