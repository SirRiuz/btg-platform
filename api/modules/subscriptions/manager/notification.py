"""Thin bridge from the subscriptions module to the notifications service.

Historically this file contained an in-line stub that consulted
``AccountManager`` and logged what it would have sent. That stub is gone
— its job is now owned by :class:`modules.notifications.NotificationService`,
which speaks hex-architecture (ports/adapters) and can target real AWS
SES/SNS depending on configuration.

The two helpers below are deliberately tiny: they exist only so the
subscriptions ``routes`` and ``manager`` keep the same call sites they
had with the stub. Every exception is swallowed — the financial state
change has already committed and a notification failure must not turn a
successful subscribe/cancel into a 500.
"""

# Python
import logging

# Module
from modules.notifications import get_notification_service


_logger = logging.getLogger(__name__)


async def notify_subscription_opened(
    *, user_id: str, fund_nombre: str, amount: int, new_balance: int | None = None
) -> None:
    """Fire the post-commit subscription-confirmed notification.

    ``new_balance`` is optional for backwards-compatibility with the
    earlier call sites that did not yet pass it; the template renders a
    ``0`` placeholder in that case (which the route ALWAYS overrides
    because the manager returns the real value).
    """
    try:
        service = get_notification_service()
        await service.notify_subscription_confirmed(
            user_id=user_id,
            fund_name=fund_nombre,
            amount=amount,
            new_balance=new_balance if new_balance is not None else 0,
        )
    except Exception:  # noqa: BLE001 — fire-and-forget guarantee
        _logger.exception(
            "notify_subscription_opened crashed for user_id=%s fund=%s; "
            "subscription remains committed.",
            user_id,
            fund_nombre,
        )


async def notify_subscription_cancelled(
    *, user_id: str, fund_nombre: str, amount: int, new_balance: int
) -> None:
    """Fire the post-commit cancellation notification."""
    try:
        service = get_notification_service()
        await service.notify_subscription_cancelled(
            user_id=user_id,
            fund_name=fund_nombre,
            amount=amount,
            new_balance=new_balance,
        )
    except Exception:  # noqa: BLE001 — fire-and-forget guarantee
        _logger.exception(
            "notify_subscription_cancelled crashed for user_id=%s fund=%s; "
            "cancellation remains committed.",
            user_id,
            fund_nombre,
        )
