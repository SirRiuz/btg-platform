# Constants
from constants.exceptions import DomainError
from constants.funds import FundErrorCodes, FundMessages


class FundError(DomainError):
    """Base class for funds-domain errors. Subclasses bind ``code``, ``status_code`` and ``message``."""

    code: str = "FUND_ERROR"
    status_code: int = 400


class FundNotFoundError(FundError):
    """Raised when a fund lookup by id fails.

    The exception is parameterized at raise-time with the missing id so the
    handler-formatted message points to the offending value, matching the
    style of the auth/accounts domain errors.
    """

    code = FundErrorCodes.FUND_NOT_FOUND
    status_code = 404

    def __init__(self, fund_id: int) -> None:
        super().__init__(FundMessages.FUND_NOT_FOUND.format(fund_id=fund_id))


class FundAlreadyExistsError(FundError):
    """Raised when creating a fund collides with an existing id or nombre.

    The two unique constraints (``_id`` and ``nombre``) surface through the
    same exception type but with distinct messages — ``from_id`` and
    ``from_nombre`` make it explicit which constraint fired so the API
    returns a precise 409 without leaking unrelated state.
    """

    code = FundErrorCodes.FUND_ALREADY_EXISTS
    status_code = 409

    def __init__(self, message: str) -> None:
        super().__init__(message)

    @classmethod
    def from_id(cls, fund_id: int) -> "FundAlreadyExistsError":
        return cls(FundMessages.FUND_ID_ALREADY_EXISTS.format(fund_id=fund_id))

    @classmethod
    def from_nombre(cls, nombre: str) -> "FundAlreadyExistsError":
        return cls(FundMessages.FUND_NAME_ALREADY_EXISTS.format(nombre=nombre))


class FundAlreadyInactiveError(FundError):
    """Raised when soft-deleting a fund that is already inactive."""

    code = FundErrorCodes.FUND_ALREADY_INACTIVE
    status_code = 409
    message = FundMessages.FUND_ALREADY_INACTIVE
