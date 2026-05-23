# Python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SubscriptionCancelledTemplate:
    """Notification copy for a subscription cancellation.

    Mirror of :class:`SubscriptionConfirmedTemplate` — same shape, same
    discipline. The fact that they are two distinct classes (rather than
    one parameterized by ``event_type``) is deliberate: each event will
    grow its own copy and possibly its own fields over time
    (cancellation date, refund eta, ...), and a class-per-event keeps
    those evolutions independent.
    """

    user_name: str
    fund_name: str
    amount: int
    new_balance: int

    @property
    def subject(self) -> str:
        return f"Subscription cancelled for fund {self.fund_name}"

    @property
    def body_text(self) -> str:
        return (
            f"Hi {self.user_name},\n\n"
            f"You cancelled your subscription to fund {self.fund_name}.\n"
            f"Refunded amount: ${self.amount:,} COP.\n"
            f"Available balance: ${self.new_balance:,} COP.\n\n"
            "If you didn't request this cancellation, contact support immediately.\n\n"
            "— Investment Funds Platform"
        )

    @property
    def body_html(self) -> str:
        return (
            f"<p>Hi <strong>{self.user_name}</strong>,</p>"
            f"<p>You cancelled your subscription to fund "
            f"<strong>{self.fund_name}</strong>.</p>"
            "<ul>"
            f"<li>Refunded amount: <strong>${self.amount:,} COP</strong></li>"
            f"<li>Available balance: <strong>${self.new_balance:,} COP</strong></li>"
            "</ul>"
            "<p>If you didn't request this cancellation, contact support immediately.</p>"
            "<p>— Investment Funds Platform</p>"
        )

    @property
    def sms_body(self) -> str:
        return (
            f"Funds: Subscription to {self.fund_name} cancelled. "
            f"Refund: ${self.amount:,}. Balance: ${self.new_balance:,}."
        )
