# Libs
import pytest

# Constants
from constants.notifications_exceptions import InvalidPhoneError

# Module
from modules.notifications.phone import mask_for_log, normalize_to_e164


class TestNormalizeToE164:

    def test_accepts_e164(self):
        assert normalize_to_e164("+573223438015") == "+573223438015"

    def test_accepts_local_colombian_and_normalizes(self):
        # Default region is CO (PHONE_DEFAULT_REGION); 322... is a
        # valid Colombian mobile prefix.
        assert normalize_to_e164("3223438015") == "+573223438015"

    def test_accepts_formatted_input(self):
        assert normalize_to_e164("+57 322 343 8015") == "+573223438015"
        assert normalize_to_e164("(322) 343-8015") == "+573223438015"

    def test_default_region_override(self):
        # US number entered without +1: explicit region overrides the setting.
        assert normalize_to_e164("2125550100", default_region="US") == "+12125550100"

    def test_rejects_garbage(self):
        with pytest.raises(InvalidPhoneError):
            normalize_to_e164("abc12345")

    def test_rejects_too_short(self):
        with pytest.raises(InvalidPhoneError):
            normalize_to_e164("123")


class TestMaskForLog:

    def test_keeps_country_prefix_and_last_four(self):
        assert mask_for_log("+573223438015") == "+57***8015"

    def test_short_input_returns_placeholder(self):
        assert mask_for_log("12345") == "<masked>"
