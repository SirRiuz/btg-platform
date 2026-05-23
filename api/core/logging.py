"""Structured (JSON) logging configuration for the API.

A custom :class:`logging.Formatter` emits one JSON object per record. Any
keyword passed via ``logger.X("message", extra={...})`` ends up as a
flat key in that object — exactly what log aggregators (CloudWatch
Insights, ELK, Loki) want.

Why a custom formatter instead of ``python-json-logger``?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* No extra dependency.
* The "redaction" hook (see :data:`_REDACT_KEYS`) lives next to the
  formatter, so a future engineer adding a sensitive field is forced to
  acknowledge it once instead of trusting transitive defaults.
* boto3's ``botocore`` logger is the noisiest of the bunch — we control
  its level explicitly from settings rather than trying to filter it
  per-record.

Configuration is **idempotent**: calling :func:`configure_logging` more
than once is safe — the second call short-circuits if the root logger is
already wired with our handler. That matters because the FastAPI
lifespan can re-import the module during ``--reload`` cycles.
"""

# Python
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


# LogRecord attributes set by ``logging`` itself; everything ELSE in
# ``record.__dict__`` is an extra= field passed by the caller, which is
# what we want to serialize.
_RESERVED_LOG_KEYS = {
    "args", "asctime", "created", "exc_info", "exc_text", "filename",
    "funcName", "levelname", "levelno", "lineno", "message", "module",
    "msecs", "msg", "name", "pathname", "process", "processName",
    "relativeCreated", "stack_info", "thread", "threadName", "taskName",
    "color_message",
}

# Substring → redaction marker. A field whose KEY contains any of these
# substrings is replaced with the marker in the output. Defense in depth
# against an accidental ``extra={"aws_secret_access_key": ...}``.
_REDACT_KEYS = (
    "secret", "password", "passwd", "authorization", "token",
)
_REDACTION_MARKER = "***REDACTED***"


def _redact(key: str, value: Any) -> Any:
    """Return ``value`` unless ``key`` looks like a secret name."""
    lower = key.lower()
    if any(needle in lower for needle in _REDACT_KEYS):
        return _REDACTION_MARKER
    return value


class JsonFormatter(logging.Formatter):
    """Emit each :class:`LogRecord` as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        # Resolve the message body (handles %-style args from logger.X(
        # "user_id=%s", uid) calls).
        message = record.getMessage()

        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc)
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
        }

        # Promote every extra= field to a top-level key.
        for key, value in record.__dict__.items():
            if key in _RESERVED_LOG_KEYS:
                continue
            payload[key] = _redact(key, value)

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(*, level: str = "INFO", boto_debug: bool = False) -> None:
    """Wire the root logger with the JSON handler. Idempotent.

    Args:
        level: Root log level. ``DEBUG`` is the only level where
            ``botocore``/``boto3`` will also be set to DEBUG (so every
            AWS request gets dumped); for any other root level the AWS
            SDK loggers stay at ``WARNING`` so they don't drown the rest.
        boto_debug: Override for the AWS SDK loggers when you want
            verbose boto3 output even with an INFO root.
    """
    root = logging.getLogger()
    # Idempotency: if we already attached our handler, just sync the
    # level (the env var may have changed across a reload) and return.
    if getattr(root, "_json_handler_installed", False):
        root.setLevel(level)
        return

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonFormatter())

    # Replace any pre-existing handlers (uvicorn / fastapi dev install
    # their own colored handler) so we don't get duplicate output.
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(level)
    root._json_handler_installed = True  # type: ignore[attr-defined]

    # AWS SDK loggers — only verbose when explicitly asked. boto3 at
    # DEBUG prints every request body, response headers and signing
    # parameters, which is exactly what you want when an SES/SNS call
    # is failing in mysterious ways, but it floods logs at any other
    # time.
    aws_level = "DEBUG" if (level == "DEBUG" or boto_debug) else "WARNING"
    for name in ("boto3", "botocore", "botocore.endpoint", "urllib3"):
        logging.getLogger(name).setLevel(aws_level)
