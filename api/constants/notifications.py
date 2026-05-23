# NOTIFICATIONS MODULE — STRING CONSTANTS


class NotificationMessages:
    """Human-readable, English domain messages for the notifications module."""

    DELIVERY_FAILED = "Failed to deliver {channel} notification: {reason}"
    INVALID_PHONE = "Phone number is not a valid E.164 number"


class NotificationErrorCodes:
    """Machine-readable error codes."""

    DELIVERY_FAILED = "NOTIFICATION_DELIVERY_FAILED"
    INVALID_PHONE = "INVALID_PHONE"


class NotificationProviders:
    """Allowed values of the ``NOTIFICATIONS_PROVIDER`` setting."""

    LOG = "log"
    AWS = "aws"


class SmsLimits:
    """Numerical limits used to validate SMS payloads."""

    # 160 GSM-7 characters fit in a single SMS segment. Anything beyond
    # that is sent as multi-part (concatenated SMS) — same delivery, but
    # the carrier bills per segment. We surface this as a soft check at
    # template-rendering time.
    SINGLE_SEGMENT_MAX = 160
