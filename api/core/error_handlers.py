# FastApi
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Constants
from constants.exceptions import DomainError, ValidationExceptions


def _payload(*, error: str, message: str, details: object | None = None) -> dict:
    body: dict = {"error": error, "message": message}
    if details is not None:
        body["details"] = details
    return body


def register_error_handlers(app: FastAPI) -> None:
    """Attach domain → HTTP exception mappers to the FastAPI app.

    A single handler for :class:`DomainError` covers every concrete
    subclass (``AuthError``, ``AccountError``, …) thanks to Python's
    exception MRO — adding a new module's error hierarchy does not require
    editing this file as long as the new base inherits from ``DomainError``.
    """

    @app.exception_handler(DomainError)
    async def _domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(error=exc.code, message=exc.message),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Pydantic v2 returns errors with `ctx` containing the original
        # ValueError instance for `@field_validator` failures. That is
        # not JSON-serializable by Starlette's default encoder; wrap with
        # `jsonable_encoder` so FastAPI converts Exception -> str safely.
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_payload(
                error=ValidationExceptions.CODE,
                message=ValidationExceptions.FAILED_MESSAGE,
                details=jsonable_encoder(exc.errors()),
            ),
        )
