# Python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SubscriptionConfirmedTemplate:
    """Notification copy for a successful subscription.

    All four formats (``subject``, ``body_text``, ``body_html``,
    ``sms_body``) are computed from the same underlying state, so a copy
    change in one place stays consistent across channels.

    Templates are pure functions of their init fields — they do NOT
    consult settings, the database or the network. That keeps them
    trivially unit-testable and reusable from any future caller (a
    weekly digest email, a customer-service replay tool, ...).
    """

    user_name: str
    fund_name: str
    amount: int
    new_balance: int

    @property
    def subject(self) -> str:
        return f"Subscription confirmed for fund {self.fund_name}"

    @property
    def body_text(self) -> str:
        return (
            f"Hi {self.user_name},\n\n"
            f"Your subscription to fund {self.fund_name} was successful.\n"
            f"Amount subscribed: ${self.amount:,} COP.\n"
            f"Available balance: ${self.new_balance:,} COP.\n\n"
            "If you didn't request this transaction, contact support immediately.\n\n"
            "— BTG Pactual"
        )

    @property
    def body_html(self) -> str:
        # Intentionally minimal HTML — inline styles only, no remote
        # assets — so every email client (Gmail, Outlook, Apple Mail,
        # corporate webmail) renders it identically.
        return (
            f"<p>Hi <strong>{self.user_name}</strong>,</p>"
            f"<p>Your subscription to fund <strong>{self.fund_name}</strong> "
            "was successful.</p>"
            "<ul>"
            f"<li>Amount subscribed: <strong>${self.amount:,} COP</strong></li>"
            f"<li>Available balance: <strong>${self.new_balance:,} COP</strong></li>"
            "</ul>"
            "<p>If you didn't request this transaction, contact support immediately.</p>"
            "<p>— BTG Pactual</p>"
        )

    @property
    def sms_body(self) -> str:
        # Keep it tight: under 160 GSM-7 chars means single-segment billing.
        return (
            f"BTG: Subscription to {self.fund_name} confirmed. "
            f"Amount: ${self.amount:,}. Balance: ${self.new_balance:,}."
        )
