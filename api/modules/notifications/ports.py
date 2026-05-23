"""Hexagonal ports for the notifications module.

The two abstract base classes here — :class:`EmailSender` and
:class:`SmsSender` — are the only types the :class:`NotificationService`
depends on. Adapters (SES, SNS, logging, future Resend/Twilio) plug into
these ports without the service learning anything about them.

The two ``Message`` dataclasses are also part of the contract: they are
the unit of work that crosses the port. They are frozen so an adapter
cannot accidentally mutate a payload mid-flight, and they normalize the
fields every adapter needs (``to``, content) so adapters never have to
reach back into the domain.
"""

# Python
from abc import ABC, abstractmethod
from dataclasses import dataclass

# Libs
from pydantic import EmailStr


@dataclass(frozen=True, slots=True)
class EmailMessage:
    """The unit of work crossing the :class:`EmailSender` port.

    Attributes:
        to: Validated email address (Pydantic ``EmailStr``).
        subject: One-line summary of the notification.
        body_text: Plain-text body — always required so email clients
            that strip HTML still render a meaningful message.
        body_html: Optional HTML body. When provided, AWS SES sends a
            multipart/alternative payload so the client picks the format
            it prefers.
    """

    to: EmailStr
    subject: str
    body_text: str
    body_html: str | None = None


@dataclass(frozen=True, slots=True)
class SmsMessage:
    """The unit of work crossing the :class:`SmsSender` port.

    Attributes:
        to: Phone number in E.164 (``+<country><number>``). Normalization
            happens BEFORE the message is built (see
            :func:`modules.notifications.phone.normalize_to_e164`) — by
            the time it reaches an adapter, the value is trusted.
        body: SMS body. Should fit in a single GSM-7 segment
            (≤ 160 chars) to avoid multi-part billing — the templates
            enforce this where it matters.
    """

    to: str
    body: str


class EmailSender(ABC):
    """Outbound email port.

    Concrete adapters (SES, Resend, …) implement :meth:`send` to actually
    deliver the message. The contract is intentionally narrow — one
    method, one message type, async — so a future port migration is a
    rename, not a refactor.
    """

    @abstractmethod
    async def send(self, message: EmailMessage) -> None:
        """Deliver ``message`` over the underlying provider.

        Raises:
            NotificationDeliveryError: when the provider rejects the
                message or the network round-trip fails. The exception
                is caught by :class:`NotificationService`; adapters
                should NOT swallow errors themselves.
        """


class SmsSender(ABC):
    """Outbound SMS port — symmetric to :class:`EmailSender`."""

    @abstractmethod
    async def send(self, message: SmsMessage) -> None:
        """Deliver ``message`` over the underlying provider.

        Raises:
            NotificationDeliveryError: same contract as
                :meth:`EmailSender.send`.
        """
