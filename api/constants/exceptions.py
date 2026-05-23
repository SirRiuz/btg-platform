# EXCEPTION STRINGS GROUPED BY RELATED ISSUES / USE CASES
#
# Only truly cross-module constants belong here. Module-specific vocabulary
# lives next to the module file (e.g. `constants/auth.py`,
# `constants/accounts.py`).


class DatabaseExceptions:
    MONGO_NOT_INITIALIZED = "Mongo connection not initialized. Call connect_to_mongo() on startup."


class ValidationExceptions:
    """Generic input-validation strings used by the global RequestValidationError handler."""

    FAILED_MESSAGE = "Invalid input data"
    CODE = "VALIDATION_ERROR"


class DomainError(Exception):
    """Shared base class for domain-layer exceptions across all modules.

    Subclasses must set ``code`` (machine-readable, e.g. ``EMAIL_ALREADY_EXISTS``),
    ``status_code`` (HTTP status) and ``message`` (human-readable string).
    Registering a single handler for this base class in
    ``core/error_handlers.py`` automatically covers every concrete subclass
    (``AuthError``, ``AccountError``, …) — no per-module handler boilerplate.
    """

    code: str = "DOMAIN_ERROR"
    status_code: int = 400
    message: str = ""

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message
