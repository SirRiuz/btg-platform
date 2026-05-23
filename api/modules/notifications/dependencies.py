"""Factories that wire concrete adapters into the abstract ports.

The factory is the *only* place in the codebase that knows which
provider is in use. Flipping ``NOTIFICATIONS_PROVIDER`` from ``log`` to
``aws`` (or to a future ``resend`` / ``twilio``) is a one-line change
here — nothing in :class:`NotificationService` or the call sites is
aware of the provider's identity.

Each factory is memoized at module level so the heavy boto3 clients are
constructed once per process, not per request. The
:func:`get_notification_service` accessor returns the live singleton.
"""

# Python
import logging
from functools import lru_cache

# Constants
from constants.notifications import NotificationProviders

# Core
from core.settings import (
    AWS_REGION,
    NOTIFICATIONS_ENABLED,
    NOTIFICATIONS_PROVIDER,
    SES_FROM_EMAIL,
    SNS_SENDER_ID,
)

# Module
from modules.accounts.manager import Account
from modules.notifications.adapters import (
    LoggingAdapter,
    SesEmailAdapter,
    SnsSmsAdapter,
)
from modules.notifications.ports import EmailSender, SmsSender
from modules.notifications.service import NotificationService


_logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_email_sender() -> EmailSender:
    """Return the :class:`EmailSender` chosen by ``NOTIFICATIONS_PROVIDER``."""
    if NOTIFICATIONS_PROVIDER == NotificationProviders.LOG:
        _logger.info("Email channel using LoggingAdapter (provider=log).")
        return LoggingAdapter()
    if NOTIFICATIONS_PROVIDER == NotificationProviders.AWS:
        _logger.info(
            "Email channel using SesEmailAdapter (region=%s, from=%s).",
            AWS_REGION,
            SES_FROM_EMAIL,
        )
        return SesEmailAdapter(region=AWS_REGION, from_email=SES_FROM_EMAIL)
    raise RuntimeError(
        f"Unknown NOTIFICATIONS_PROVIDER={NOTIFICATIONS_PROVIDER!r}; "
        f"expected one of: {NotificationProviders.LOG}, {NotificationProviders.AWS}."
    )


@lru_cache(maxsize=1)
def get_sms_sender() -> SmsSender:
    """Return the :class:`SmsSender` chosen by ``NOTIFICATIONS_PROVIDER``."""
    if NOTIFICATIONS_PROVIDER == NotificationProviders.LOG:
        _logger.info("SMS channel using LoggingAdapter (provider=log).")
        return LoggingAdapter()
    if NOTIFICATIONS_PROVIDER == NotificationProviders.AWS:
        _logger.info(
            "SMS channel using SnsSmsAdapter (region=%s, sender_id=%s).",
            AWS_REGION,
            SNS_SENDER_ID,
        )
        return SnsSmsAdapter(region=AWS_REGION, sender_id=SNS_SENDER_ID)
    raise RuntimeError(
        f"Unknown NOTIFICATIONS_PROVIDER={NOTIFICATIONS_PROVIDER!r}."
    )


@lru_cache(maxsize=1)
def get_notification_service() -> NotificationService:
    """Return the process-wide singleton :class:`NotificationService`."""
    return NotificationService(
        email_sender=get_email_sender(),
        sms_sender=get_sms_sender(),
        account=Account.objects,
        enabled=NOTIFICATIONS_ENABLED,
    )


def reset_cache() -> None:
    """Clear the memoization caches — exposed for tests only.

    Each test that flips ``NOTIFICATIONS_PROVIDER`` calls this so the
    next ``get_*`` returns a fresh adapter built against the new value.
    """
    get_email_sender.cache_clear()
    get_sms_sender.cache_clear()
    get_notification_service.cache_clear()
