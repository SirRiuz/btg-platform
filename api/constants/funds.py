# FUNDS MODULE — STRING CONSTANTS (messages + machine-readable codes)


class FundMessages:
    """Human-readable, English domain messages for the funds module."""

    FUND_NOT_FOUND = "Fund with id {fund_id} not found"
    FUND_ID_ALREADY_EXISTS = "A fund with id {fund_id} already exists"
    FUND_NAME_ALREADY_EXISTS = "A fund with nombre '{nombre}' already exists"
    FUND_ALREADY_INACTIVE = "The fund is already inactive"
    FUND_DEACTIVATED = "Fund {nombre} deactivated successfully"


class FundErrorCodes:
    """Machine-readable error codes returned in the ``error`` field of responses."""

    FUND_NOT_FOUND = "FUND_NOT_FOUND"
    FUND_ALREADY_EXISTS = "FUND_ALREADY_EXISTS"
    FUND_ALREADY_INACTIVE = "FUND_ALREADY_INACTIVE"


class FundValidationMessages:
    """Validation error messages raised by Pydantic field validators."""

    NOMBRE_LENGTH = "Nombre must be between 3 and 100 characters"
    MONTO_MINIMO_POSITIVE = "monto_minimo must be greater than 0"
    DESCRIPCION_LENGTH = "Descripcion must be at most 500 characters"
    LIMIT_RANGE = "limit must be between 1 and 100"
    SKIP_NON_NEGATIVE = "skip must be greater than or equal to 0"
