# Constants
from constants.auth import AuthErrorCodes, AuthMessages
from constants.exceptions import DomainError


class AuthError(DomainError):
    """Base class for auth-domain errors. Subclasses bind ``code``, ``status_code`` and ``message``."""

    code: str = "AUTH_ERROR"
    status_code: int = 400


class EmailAlreadyExistsError(AuthError):
    code = AuthErrorCodes.EMAIL_ALREADY_EXISTS
    status_code = 409
    message = AuthMessages.EMAIL_ALREADY_EXISTS


class PhoneAlreadyExistsError(AuthError):
    code = AuthErrorCodes.PHONE_ALREADY_EXISTS
    status_code = 409
    message = AuthMessages.PHONE_ALREADY_EXISTS


class InvalidCredentialsError(AuthError):
    code = AuthErrorCodes.INVALID_CREDENTIALS
    status_code = 401
    message = AuthMessages.INVALID_CREDENTIALS


class InactiveUserError(AuthError):
    code = AuthErrorCodes.INACTIVE_USER
    status_code = 403
    message = AuthMessages.INACTIVE_USER


class TokenRevokedError(AuthError):
    code = AuthErrorCodes.TOKEN_REVOKED
    status_code = 401
    message = AuthMessages.TOKEN_REVOKED


class InvalidTokenError(AuthError):
    code = AuthErrorCodes.INVALID_TOKEN
    status_code = 401
    message = AuthMessages.INVALID_TOKEN


class MissingTokenError(AuthError):
    code = AuthErrorCodes.MISSING_TOKEN
    status_code = 401
    message = AuthMessages.MISSING_TOKEN


class InsufficientRoleError(AuthError):
    code = AuthErrorCodes.INSUFFICIENT_ROLE
    status_code = 403
    message = AuthMessages.INSUFFICIENT_ROLE
