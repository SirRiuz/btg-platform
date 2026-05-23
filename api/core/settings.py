"""Typed, validated application settings.

Everything that varies between local dev / staging / Lambda production
lives here. The single :class:`Settings` instance is built once at
import time from ``os.environ`` (and indirectly the ``.env`` file, via
docker-compose) and is the **only** place in the codebase that reads
environment variables directly.

Backwards compatibility note
----------------------------
Older modules in this codebase import constants directly
(``from core.settings import MONGO_URI``). To avoid a sweeping refactor,
the original module-level constants are still exported — they now read
from the :class:`Settings` singleton instead of ``os.environ`` directly.

Security note
-------------
``AWS_SECRET_ACCESS_KEY`` is typed as ``SecretStr`` so it never appears
in ``repr()``/serialization output. The settings logger at startup also
excludes it explicitly. AWS credentials are only required when running
locally with ``NOTIFICATIONS_PROVIDER=aws`` — in Lambda, the IAM role
attached to the function provides credentials automatically and the
two env vars should be omitted.
"""

# Python
import logging
import os
from typing import Literal

# Libs
from pydantic import EmailStr, Field, SecretStr, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_logger = logging.getLogger(__name__)


# Recognized AWS regions for SES + SNS at the time of writing. Pinning the
# allow-list catches typos (``us-east1`` vs ``us-east-1``) before they
# blow up boto3 with a confusing endpoint error.
_VALID_AWS_REGIONS = {
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "ca-central-1",
    "sa-east-1",
    "eu-west-1", "eu-west-2", "eu-west-3", "eu-central-1", "eu-north-1",
    "eu-south-1",
    "ap-south-1", "ap-southeast-1", "ap-southeast-2", "ap-northeast-1",
    "ap-northeast-2", "ap-northeast-3", "ap-east-1",
    "me-south-1", "af-south-1",
}


class Settings(BaseSettings):
    """Application configuration, loaded from environment variables.

    Fields are intentionally typed strictly (``EmailStr``, ``SecretStr``,
    ``Literal``) so a typo in ``.env`` fails fast at boot instead of
    surfacing as a confusing runtime error from boto3 / pymongo / pyjwt
    later. Cross-field invariants (e.g. "AWS credentials required when
    provider=aws and not in Lambda") are enforced by the
    ``check_aws_*`` model validators.
    """

    model_config = SettingsConfigDict(
        env_file=None,            # docker-compose / process env is the source of truth
        case_sensitive=False,
        extra="ignore",
    )

    # ---------- Core ----------

    debug: bool = Field(
        default=False,
        description="Toggles verbose error pages and other dev-only behaviors.",
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description=(
            "Root log level. DEBUG also enables ``botocore``/``boto3`` debug "
            "logging — every AWS request/response gets dumped, including "
            "headers. Use sparingly and never in production."
        ),
    )

    allower_cors_origins: str = Field(
        default="",
        description="Comma-separated list of allowed CORS origins.",
    )

    # ---------- MongoDB ----------

    mongo_uri: str = Field(
        ...,
        description="MongoDB connection URI (with credentials and authSource).",
    )

    mongo_db_name: str = Field(
        ...,
        description="MongoDB database name used by the application.",
    )

    # ---------- Auth / JWT ----------

    jwt_secret_key: SecretStr = Field(
        ...,
        description="HMAC secret used to sign access tokens.",
    )

    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm.",
    )

    jwt_expiration_minutes: int | None = Field(
        default=None,
        description=(
            "Token lifetime in minutes. ``None`` disables expiration "
            "(intentional for the technical test)."
        ),
    )

    bcrypt_rounds: int = Field(
        default=12,
        ge=4,
        le=15,
        description="bcrypt cost factor. Lower values speed up tests.",
    )

    # ---------- Notifications ----------

    notifications_enabled: bool = Field(
        default=True,
        description=(
            "Master switch. ``False`` silences every notification without "
            "removing the integration code."
        ),
    )

    notifications_provider: Literal["aws", "log"] = Field(
        default="log",
        description=(
            "Selects the adapter wiring. ``log`` writes messages to stdout "
            "(dev/test default). ``aws`` calls SES + SNS for real."
        ),
    )

    aws_region: str = Field(
        default="us-east-1",
        description="AWS region for both SES and SNS clients.",
        examples=["us-east-1", "eu-west-1", "sa-east-1"],
    )

    aws_access_key_id: str | None = Field(
        default=None,
        description=(
            "IAM user access key. Required only when "
            "``notifications_provider=aws`` AND the app is NOT running in "
            "Lambda (Lambda gets credentials from its execution role)."
        ),
    )

    aws_secret_access_key: SecretStr | None = Field(
        default=None,
        description=(
            "IAM user secret key. Wrapped in ``SecretStr`` so it never "
            "leaks via ``repr()`` or serialization."
        ),
    )

    ses_from_email: EmailStr | None = Field(
        default=None,
        description=(
            "Verified SES identity used as the ``From:`` address. "
            "Required when ``notifications_provider=aws``."
        ),
    )

    sns_sender_id: str = Field(
        default="BTGPactual",
        max_length=11,
        pattern=r"^[A-Za-z0-9]+$",
        description=(
            "Alphanumeric sender id shown to SMS recipients. Honored in "
            "most of LATAM/Europe/Asia; silently replaced by a long number "
            "in USA/Canada. AWS hard-cap: 11 alphanumeric characters."
        ),
    )

    # ---------- Phone normalization ----------

    phone_default_region: str = Field(
        default="CO",
        min_length=2,
        max_length=2,
        description=(
            "ISO-3166 alpha-2 country code used to interpret phone numbers "
            "entered without a ``+<cc>`` prefix."
        ),
    )

    # ---------- Field validators / parsers ----------

    @model_validator(mode="before")
    @classmethod
    def _coerce_empty_strings(cls, data):
        """Treat ``""`` env vars as "unset".

        docker-compose passes empty strings for unset variables (e.g.
        ``JWT_EXPIRATION_MINUTES=``); without this coercion, Pydantic
        tries to parse them and fails. We map ``""`` to ``None`` for the
        optional integer fields and to the field default for the rest.
        """
        if not isinstance(data, dict):
            return data
        cleaned = {}
        for key, value in data.items():
            if isinstance(value, str) and value.strip() == "":
                # Skip — let Pydantic fall back to the field default.
                continue
            cleaned[key] = value
        return cleaned

    # ---------- Cross-field validators ----------

    @computed_field
    @property
    def is_running_in_lambda(self) -> bool:
        """``True`` when the process is running inside an AWS Lambda.

        Detection uses ``AWS_LAMBDA_FUNCTION_NAME`` — the canonical env
        var Lambda always sets at runtime. The flag drives the
        credential-requirement validator below: in Lambda, credentials
        come from the execution role and the two access-key env vars
        should be ABSENT.
        """
        return bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

    @model_validator(mode="after")
    def _check_aws_region_known(self) -> "Settings":
        if self.aws_region not in _VALID_AWS_REGIONS:
            raise ValueError(
                f"AWS_REGION={self.aws_region!r} is not in the recognized "
                f"region list. Set one of: {sorted(_VALID_AWS_REGIONS)}."
            )
        return self

    @model_validator(mode="after")
    def _check_ses_from_email_present_when_aws(self) -> "Settings":
        if self.notifications_provider == "aws" and self.ses_from_email is None:
            raise ValueError(
                "NOTIFICATIONS_PROVIDER=aws requires SES_FROM_EMAIL to be set "
                "to a verified SES identity in the configured region."
            )
        return self

    @model_validator(mode="after")
    def _check_aws_credentials_present_when_needed(self) -> "Settings":
        """Outside Lambda + provider=aws → access key and secret are mandatory.

        Inside Lambda, credentials are injected by the runtime via the
        execution role; the two env vars should be omitted on purpose.
        Failing fast here saves engineers from confusing
        ``UnrecognizedClientException`` errors at first send.
        """
        if self.notifications_provider != "aws":
            return self
        if self.is_running_in_lambda:
            return self
        missing = []
        if not self.aws_access_key_id:
            missing.append("AWS_ACCESS_KEY_ID")
        if self.aws_secret_access_key is None:
            missing.append("AWS_SECRET_ACCESS_KEY")
        if missing:
            raise ValueError(
                "NOTIFICATIONS_PROVIDER=aws (running outside Lambda) "
                f"requires the following env vars to be set: {', '.join(missing)}. "
                "In production on Lambda, OMIT both and rely on the IAM execution role."
            )
        return self

    # ---------- Diagnostics ----------

    def log_startup_summary(self) -> None:
        """Log a one-line snapshot of the effective config — without secrets.

        Called from the FastAPI ``lifespan`` so engineers reading boot
        logs immediately see which provider, region and identities are
        in play. Secrets are never included.
        """
        _logger.info(
            "settings.loaded debug=%s mongo_db=%s notifications_enabled=%s "
            "notifications_provider=%s aws_region=%s ses_from_email=%s "
            "sns_sender_id=%s phone_default_region=%s is_running_in_lambda=%s",
            self.debug,
            self.mongo_db_name,
            self.notifications_enabled,
            self.notifications_provider,
            self.aws_region,
            self.ses_from_email,
            self.sns_sender_id,
            self.phone_default_region,
            self.is_running_in_lambda,
        )


# Single process-wide instance. Build once at import time so validation
# errors surface immediately at boot, not at the first incoming request.
settings = Settings()


# ---------------- Backwards-compatible module-level exports ----------------
#
# Existing imports across the codebase use ``from core.settings import X``
# style. Keeping these aliases means a refactor to the typed Settings
# instance does not require touching every call site.

DEBUG: bool = settings.debug
LOG_LEVEL: str = settings.log_level

ALLOWER_CORS_ORIGINS: list[str] = [
    origin.strip()
    for origin in settings.allower_cors_origins.split(",")
    if origin.strip()
]

MONGO_URI: str = settings.mongo_uri
MONGO_DB_NAME: str = settings.mongo_db_name

JWT_SECRET_KEY: str = settings.jwt_secret_key.get_secret_value()
JWT_ALGORITHM: str = settings.jwt_algorithm
JWT_EXPIRATION_MINUTES: int | None = settings.jwt_expiration_minutes

BCRYPT_ROUNDS: int = settings.bcrypt_rounds

NOTIFICATIONS_ENABLED: bool = settings.notifications_enabled
NOTIFICATIONS_PROVIDER: str = settings.notifications_provider
AWS_REGION: str = settings.aws_region
SES_FROM_EMAIL: str = settings.ses_from_email or ""
SNS_SENDER_ID: str = settings.sns_sender_id
PHONE_DEFAULT_REGION: str = settings.phone_default_region
