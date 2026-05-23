# Constants
from constants.accounts import AccountErrorCodes, AccountMessages
from constants.exceptions import DomainError


class AccountError(DomainError):
    """Base class for accounts-domain errors. Subclasses bind ``code``, ``status_code`` and ``message``."""

    code: str = "ACCOUNT_ERROR"
    status_code: int = 400


class UserNotFoundError(AccountError):
    code = AccountErrorCodes.USER_NOT_FOUND
    status_code = 404
    message = AccountMessages.USER_NOT_FOUND
