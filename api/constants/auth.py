# AUTH MODULE — STRING CONSTANTS (messages + machine-readable codes)


class AuthMessages:
    """Human-readable, English domain messages for the auth module."""

    EMAIL_ALREADY_EXISTS = "Email is already registered"
    PHONE_ALREADY_EXISTS = "Phone number is already registered"
    INVALID_CREDENTIALS = "Invalid credentials"
    INACTIVE_USER = "Account is disabled"
    TOKEN_REVOKED = "Token has been revoked"
    INVALID_TOKEN = "Invalid token"
    MISSING_TOKEN = "Authentication token is missing"
    INSUFFICIENT_ROLE = "Insufficient permissions"
    LOGOUT_SUCCESS = "Session closed successfully"


class AuthErrorCodes:
    """Machine-readable error codes returned in the ``error`` field of responses."""

    EMAIL_ALREADY_EXISTS = "EMAIL_ALREADY_EXISTS"
    PHONE_ALREADY_EXISTS = "PHONE_ALREADY_EXISTS"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    INACTIVE_USER = "INACTIVE_USER"
    TOKEN_REVOKED = "TOKEN_REVOKED"
    INVALID_TOKEN = "INVALID_TOKEN"
    MISSING_TOKEN = "MISSING_TOKEN"
    INSUFFICIENT_ROLE = "INSUFFICIENT_ROLE"


class AuthValidationMessages:
    """Validation error messages raised by Pydantic field validators."""

    NAME_FORMAT = "Only letters and spaces, 2-50 characters"
    PASSWORD_POLICY = (
        "Password must be 8-128 characters with at least 1 uppercase letter, "
        "1 lowercase letter and 1 digit"
    )
    PHONE_FORMAT = (
        "Phone must be 7-15 digits with an optional leading '+'. Spaces are allowed."
    )
