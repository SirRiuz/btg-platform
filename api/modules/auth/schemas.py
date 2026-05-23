# Python
import re
from enum import Enum

# Libs
import phonenumbers
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict

# Constants
from constants.auth import AuthValidationMessages

# Core
from core.settings import PHONE_DEFAULT_REGION


class UserRole(str, Enum):
    """Authorization role assigned to a user account.

    ``USER`` is the default; ``ADMIN`` is reserved for operators that may
    bypass user-scoped restrictions. The role is embedded as a JWT claim
    so the ``require_role`` dependency can authorize requests without an
    extra database hit.
    """

    USER = "USER"
    ADMIN = "ADMIN"


# Pre-compiled regexes for the field validators. Compiling once at import
# time avoids paying the regex-compilation cost on every request.
_NAME_RE = re.compile(r"^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]{2,50}$")
_PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,128}$")


class RegisterRequest(BaseModel):
    """Payload for ``POST /auth/register``.

    Fields are validated and normalized at the boundary so the rest of the
    code can trust the shapes it receives:

    * ``email`` is lowercased for case-insensitive uniqueness.
    * ``phone`` is stripped of internal whitespace and validated against a
      lenient E.164-ish format (country code optional).
    * ``password`` must satisfy the minimum strength policy.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    email: EmailStr = Field(..., max_length=100)
    phone: str = Field(..., min_length=7, max_length=20)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("first_name", "last_name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        """Ensure the name contains only letters (incl. Spanish accents) and spaces.

        Digits and punctuation are rejected to keep the stored profile
        sortable and printable on user-facing surfaces (greetings, emails,
        receipts).
        """
        if not _NAME_RE.match(value):
            raise ValueError(AuthValidationMessages.NAME_FORMAT)
        return value

    @field_validator("password")
    @classmethod
    def _validate_password_strength(cls, value: str) -> str:
        """Enforce the minimum password policy.

        Requires 8-128 characters with at least one uppercase letter, one
        lowercase letter and one digit. This is the floor for a sensible
        baseline; in production we would defer to a strength estimator
        such as ``zxcvbn`` so passphrases like ``correct horse battery
        staple`` pass without forcing mixed case.
        """
        if not _PASSWORD_RE.match(value):
            raise ValueError(AuthValidationMessages.PASSWORD_POLICY)
        return value

    @field_validator("email")
    @classmethod
    def _lowercase_email(cls, value: str) -> str:
        """Normalize the email to lowercase.

        The unique index and all lookups operate on the lowercased form, so
        ``Mateo@Example.com`` and ``mateo@example.com`` are treated as the
        same identity. Local-part case sensitivity allowed by the RFC is
        intentionally ignored — virtually no real-world provider honours it.
        """
        return value.lower()

    @field_validator("phone")
    @classmethod
    def _normalize_phone(cls, value: str) -> str:
        """Parse with ``phonenumbers`` and return the canonical E.164 form.

        Accepts whatever the user types — ``"+57 322 343 8015"``,
        ``"+573223438015"``, ``"3223438015"``, ``"322-343-8015"`` — and
        normalizes to ``"+573223438015"``. Numbers without an explicit
        ``+<cc>`` prefix are interpreted in ``PHONE_DEFAULT_REGION``
        (``CO`` by default, see ``core/settings.py``) so the BTG brief's
        local-Colombia flow keeps working.

        Storing E.164 in MongoDB lets the notifications module dispatch
        SMS to *any* country (via AWS SNS) without per-call parsing.
        """
        try:
            parsed = phonenumbers.parse(value, PHONE_DEFAULT_REGION)
        except phonenumbers.NumberParseException as exc:
            raise ValueError(AuthValidationMessages.PHONE_FORMAT) from exc
        if not phonenumbers.is_valid_number(parsed):
            raise ValueError(AuthValidationMessages.PHONE_FORMAT)
        return phonenumbers.format_number(
            parsed, phonenumbers.PhoneNumberFormat.E164
        )


class LoginRequest(BaseModel):
    """Payload for ``POST /auth/login``.

    Only ``email`` and ``password`` are required. The same normalization
    applied at registration (lowercasing the email) is repeated here so a
    user can log in with any case variant of the address they signed up
    with.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _lowercase_email(cls, value: str) -> str:
        """Normalize the email to lowercase to match the stored form."""
        return value.lower()


class UserResponse(BaseModel):
    """Public projection of a user — never includes ``password_hash``.

    Used both in :class:`RegisterResponse` and by any future endpoint that
    returns user data. Keeping it as a dedicated schema (rather than
    serializing the raw Mongo document) ensures sensitive fields can never
    leak by accident as the model grows.
    """

    id: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    balance: int
    role: UserRole


class TokenResponse(BaseModel):
    """OAuth2-style response carrying the access token.

    The literal ``token_type="bearer"`` matches the convention expected by
    clients using the standard ``Authorization: Bearer <token>`` header.
    """

    access_token: str
    token_type: str = "bearer"


class RegisterResponse(TokenResponse):
    """Response for ``POST /auth/register`` — the issued token plus the user."""

    user: UserResponse


class LogoutResponse(BaseModel):
    """Response for ``POST /auth/logout`` — a single human-readable confirmation."""

    message: str
