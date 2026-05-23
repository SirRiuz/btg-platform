# Constants
from constants.notifications import SmsLimits

# Module
from modules.notifications.templates import (
    SubscriptionCancelledTemplate,
    SubscriptionConfirmedTemplate,
)


class TestSubscriptionConfirmedTemplate:

    def test_subject_includes_fund_name(self):
        tpl = SubscriptionConfirmedTemplate(
            user_name="Mateo", fund_name="DEUDAPRIVADA",
            amount=50_000, new_balance=450_000,
        )
        assert "DEUDAPRIVADA" in tpl.subject

    def test_amounts_use_thousand_separator(self):
        tpl = SubscriptionConfirmedTemplate(
            user_name="Mateo", fund_name="FDO-ACCIONES",
            amount=250_000, new_balance=750_000,
        )
        # f-string formatting uses ',' for thousands.
        assert "250,000" in tpl.body_text
        assert "750,000" in tpl.body_text

    def test_html_body_includes_amount_and_balance(self):
        tpl = SubscriptionConfirmedTemplate(
            user_name="Mateo", fund_name="X", amount=42_000, new_balance=458_000,
        )
        assert "42,000" in tpl.body_html
        assert "458,000" in tpl.body_html

    def test_sms_body_fits_in_single_segment_for_typical_fund_names(self):
        """Single-segment SMS = single-segment billing.

        Tested across the catalog of seeded fund names.
        """
        for fund_name in [
            "FPV_BTG_PACTUAL_RECAUDADORA",
            "FPV_BTG_PACTUAL_ECOPETROL",
            "DEUDAPRIVADA",
            "FDO-ACCIONES",
            "FPV_BTG_PACTUAL_DINAMICA",
        ]:
            tpl = SubscriptionConfirmedTemplate(
                user_name="Mateo", fund_name=fund_name,
                amount=999_999, new_balance=1,
            )
            assert len(tpl.sms_body) <= SmsLimits.SINGLE_SEGMENT_MAX, (
                f"{fund_name}: {len(tpl.sms_body)} chars"
            )


class TestSubscriptionCancelledTemplate:

    def test_subject_mentions_cancellation(self):
        tpl = SubscriptionCancelledTemplate(
            user_name="Mateo", fund_name="DEUDAPRIVADA",
            amount=50_000, new_balance=500_000,
        )
        assert "cancelled" in tpl.subject.lower()

    def test_sms_body_mentions_refund(self):
        tpl = SubscriptionCancelledTemplate(
            user_name="Mateo", fund_name="X",
            amount=10_000, new_balance=510_000,
        )
        assert "Refund" in tpl.sms_body or "refund" in tpl.sms_body
