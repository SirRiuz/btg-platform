# ACCOUNTS MODULE — STRING CONSTANTS (messages + machine-readable codes)


class AccountMessages:
    """Human-readable, English domain messages for the accounts module."""

    USER_NOT_FOUND = "User not found"
    SETTINGS_UPDATED = "Settings updated successfully"


class AccountErrorCodes:
    """Machine-readable error codes returned in the ``error`` field of responses."""

    USER_NOT_FOUND = "USER_NOT_FOUND"
