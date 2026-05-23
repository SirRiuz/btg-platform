"""Notification orchestration — the hex-architecture core of the module.

The :class:`NotificationService` is the only class HTTP-side code knows
about. It receives concrete adapter instances by *port* type via
constructor injection (hexagonal architecture), and it owns three
responsibilities:

1. **Routing**: consult the user's per-channel preferences via
   :class:`AccountManager` and skip channels the user opted out of.
2. **Failure isolation**: a failure on one channel must NOT affect the
   other, and must NOT propagate to the caller — the caller's
   transactional commit already happened.
3. **Composition**: pair a template (the "what") with an adapter (the
   "how") to actually deliver the message.

Adding a new event type is mechanical: declare a new template, add a
``notify_<event>`` method that mirrors the existing pair. No
modifications to ports or adapters.

Adding a new channel (push, WhatsApp) means adding a new port + a new
sender to the constructor — the existing methods don't change.
"""

# Python
import logging
from typing import Protocol

# Constants
from constants.notifications_exceptions import (
    InvalidPhoneError,
    NotificationDeliveryError,
)

# Module
from modules.notifications.phone import normalize_to_e164
from modules.notifications.ports import (
    EmailMessage,
    EmailSender,
    SmsMessage,
    SmsSender,
)
from modules.notifications.templates import (
    SubscriptionCancelledTemplate,
    SubscriptionConfirmedTemplate,
)


_logger = logging.getLogger(__name__)


class _AccountPort(Protocol):
    """Structural type for the account dependency.

    Declaring a Protocol (instead of importing the concrete
    ``AccountManager``) keeps the unit tests trivial — any object with
    these four async methods satisfies the port, and the test suite can
    pass plain mocks without inheriting from anything.
    """

    async def get_profile(self, user_id: str): ...
    async def can_receive_email(self, user_id: str) -> bool: ...
    async def can_receive_sms(self, user_id: str) -> bool: ...


class NotificationService:
    """High-level notifications entry point used by other modules.

    Constructed once at app startup by
    :func:`modules.notifications.dependencies.get_notification_service`
    and shared across requests. Holds no per-request state, so it is
    inherently thread-safe.
    """

    def __init__(
        self,
        *,
        email_sender: EmailSender,
        sms_sender: SmsSender,
        account: _AccountPort,
        enabled: bool = True,
    ) -> None:
        self._email = email_sender
        self._sms = sms_sender
        self._account = account
        self._enabled = enabled

    # ---------- Public event-driven API ----------

    async def notify_subscription_confirmed(
        self,
        *,
        user_id: str,
        fund_name: str,
        amount: int,
        new_balance: int,
    ) -> None:
        """Notify the user about a successful subscription.

        See :meth:`_dispatch` for the routing & failure-isolation rules.
        This method is the public contract consumed by the subscriptions
        module post-commit.
        """
        if not self._enabled:
            _logger.info(
                "notify.skip.master_switch_off",
                extra={"event": "subscription_confirmed", "user_id": user_id},
            )
            return

        _logger.info(
            "notify.subscription_confirmed.start",
            extra={
                "user_id": user_id,
                "fund_name": fund_name,
                "amount": amount,
                "new_balance": new_balance,
            },
        )
        profile = await self._account.get_profile(user_id)
        template = SubscriptionConfirmedTemplate(
            user_name=profile.first_name,
            fund_name=fund_name,
            amount=amount,
            new_balance=new_balance,
        )
        await self._dispatch(user_id=user_id, profile=profile, template=template)

    async def notify_subscription_cancelled(
        self,
        *,
        user_id: str,
        fund_name: str,
        amount: int,
        new_balance: int,
    ) -> None:
        """Notify the user about a cancellation. Symmetric to ``confirmed``."""
        if not self._enabled:
            _logger.info(
                "notify.skip.master_switch_off",
                extra={"event": "subscription_cancelled", "user_id": user_id},
            )
            return

        _logger.info(
            "notify.subscription_cancelled.start",
            extra={
                "user_id": user_id,
                "fund_name": fund_name,
                "amount": amount,
                "new_balance": new_balance,
            },
        )
        profile = await self._account.get_profile(user_id)
        template = SubscriptionCancelledTemplate(
            user_name=profile.first_name,
            fund_name=fund_name,
            amount=amount,
            new_balance=new_balance,
        )
        await self._dispatch(user_id=user_id, profile=profile, template=template)

    # ---------- Dispatch core ----------

    async def _dispatch(self, *, user_id: str, profile, template) -> None:
        """Route a rendered template to the user's enabled channels.

        Each channel is wrapped in its own try/except so a SMS failure
        never blocks an email send and vice versa. Errors are logged
        with WARNING and swallowed — by contract, the subscription that
        triggered this dispatch was already committed, and no
        notification problem may revert it.
        """
        if await self._account.can_receive_email(user_id):
            try:
                await self._email.send(
                    EmailMessage(
                        to=profile.email,
                        subject=template.subject,
                        body_text=template.body_text,
                        body_html=template.body_html,
                    )
                )
            except NotificationDeliveryError as exc:
                _logger.warning(
                    "notify.email.failed",
                    extra={
                        "user_id": user_id,
                        "channel": "email",
                        "reason": exc.reason,
                        "aws_error_code": exc.aws_error_code,
                        "aws_request_id": exc.aws_request_id,
                    },
                )
            except Exception:  # noqa: BLE001 — channel isolation guarantee
                _logger.exception(
                    "notify.email.unexpected",
                    extra={"user_id": user_id, "channel": "email"},
                )
        else:
            _logger.info(
                "notify.skip.channel_disabled",
                extra={"user_id": user_id, "channel": "email"},
            )

        if await self._account.can_receive_sms(user_id):
            try:
                normalized = normalize_to_e164(profile.phone)
            except InvalidPhoneError:
                _logger.warning(
                    "notify.sms.skip_invalid_phone",
                    extra={"user_id": user_id, "channel": "sms"},
                )
                return

            try:
                await self._sms.send(
                    SmsMessage(to=normalized, body=template.sms_body)
                )
            except NotificationDeliveryError as exc:
                _logger.warning(
                    "notify.sms.failed",
                    extra={
                        "user_id": user_id,
                        "channel": "sms",
                        "reason": exc.reason,
                        "aws_error_code": exc.aws_error_code,
                        "aws_request_id": exc.aws_request_id,
                    },
                )
            except Exception:  # noqa: BLE001 — channel isolation guarantee
                _logger.exception(
                    "notify.sms.unexpected",
                    extra={"user_id": user_id, "channel": "sms"},
                )
        else:
            _logger.info(
                "notify.skip.channel_disabled",
                extra={"user_id": user_id, "channel": "sms"},
            )
