"""Phone number normalization — the boundary between user input and adapters.

Every SMS that leaves the platform travels through here first. We use
the ``phonenumbers`` library (the same library Google uses inside
Android) because:

* It validates the number against real numbering plans, not just a regex.
* It accepts local formats (``300 123 4567``) and normalizes them to
  E.164 using a configurable default region — required by the BTG brief
  ("funcione globalmente, fallback Colombia").
* AWS SNS requires E.164 anyway; normalizing upstream avoids
  per-adapter parsing.

The normalizer raises :class:`InvalidPhoneError` on garbage input — the
caller decides whether to skip the SMS channel (current behavior) or
surface the error to the user.
"""

# Python
import logging

# Libs
import phonenumbers

# Constants
from constants.notifications_exceptions import InvalidPhoneError

# Core
from core.settings import PHONE_DEFAULT_REGION


_logger = logging.getLogger(__name__)


def normalize_to_e164(raw: str, *, default_region: str | None = None) -> str:
    """Parse ``raw`` and return the canonical E.164 representation.

    Examples (with ``default_region='CO'``)::

        normalize_to_e164("+57 322 343 8015")   -> "+573223438015"
        normalize_to_e164("3223438015")         -> "+573223438015"
        normalize_to_e164("+1-555-555-5555")    -> "+15555555555"
        normalize_to_e164("abc")                -> raises InvalidPhoneError

    Args:
        raw: Whatever the user typed. Whitespace, dashes, parentheses
            are tolerated — the library strips them.
        default_region: ISO-3166 alpha-2 country code used when ``raw``
            has no ``+<cc>`` prefix. Defaults to
            ``PHONE_DEFAULT_REGION`` from settings (``CO`` by default).

    Raises:
        InvalidPhoneError: when ``phonenumbers`` cannot parse the input
            or returns ``is_valid_number() == False``.
    """
    region = default_region or PHONE_DEFAULT_REGION
    try:
        parsed = phonenumbers.parse(raw, region)
    except phonenumbers.NumberParseException as exc:
        _logger.warning("phone.normalize: unparseable input (%s)", exc)
        raise InvalidPhoneError() from exc

    if not phonenumbers.is_valid_number(parsed):
        _logger.warning("phone.normalize: parsed but invalid number")
        raise InvalidPhoneError()

    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def mask_for_log(e164: str) -> str:
    """Return a privacy-preserving form of an E.164 number for logging.

    Keeps the country prefix and the last 4 digits — enough to trace a
    delivery in support tickets, not enough to reconstruct the full
    number from logs. Falls back to ``"<masked>"`` if input is too short.
    """
    if len(e164) < 6:
        return "<masked>"
    return f"{e164[:3]}***{e164[-4:]}"
