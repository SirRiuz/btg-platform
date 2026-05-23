"""Self-diagnosis for the notifications module.

Two responsibilities live here:

1. **Diagnostic hints** — string-keyed mappings from AWS error codes to
   the *specific actionable advice* an engineer needs the moment that
   error fires. Pulled out of the adapters so they live in one
   maintainable place and so tests can iterate them.

2. **Configuration validation** — read-only AWS calls
   (``get_send_quota``, ``get_identity_verification_attributes``,
   ``get_sms_attributes``, ``get_sms_sandbox_account_status``) that
   surface common misconfigurations BEFORE the first real send. Run at
   FastAPI lifespan and re-exposed by the ``/health/notifications``
   endpoint.

The validators never raise — every failure surfaces as a structured
``CheckResult`` so the caller (lifespan or HTTP handler) can decide
what to do with it. The notifications module is fire-and-forget; a
misconfigured AWS account must not crash the API.
"""

# Python
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


_logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────
#  Diagnostic hints
# ──────────────────────────────────────────────────────────────────────────
#
# Map AWS error code → actionable advice. The "fallback" entries are
# returned by :func:`hint_for` when the code is unknown.

DIAGNOSTIC_HINTS_SES: dict[str, str] = {
    "MessageRejected": (
        "Email rejected. In SES sandbox, BOTH the from and to addresses must "
        "be verified — verify the recipient at AWS Console → SES → Verified "
        "identities, or request production access to bypass."
    ),
    "MailFromDomainNotVerified": (
        "The SES_FROM_EMAIL domain is not verified. Verify it at AWS Console "
        "→ SES → Verified identities (Domain) and complete the DNS records."
    ),
    "AccessDenied": (
        "The IAM principal does not have ses:SendEmail. Attach a policy "
        "granting ses:SendEmail on the verified identity ARN."
    ),
    "InvalidClientTokenId": (
        "AWS_ACCESS_KEY_ID is invalid, expired or doesn't exist. Rotate the "
        "access key (AWS Console → IAM → Users → Security credentials)."
    ),
    "SignatureDoesNotMatch": (
        "AWS_SECRET_ACCESS_KEY does not match the access key id — likely a "
        "copy-paste error or a stale value. Rotate and replace."
    ),
    "Throttling": (
        "Exceeded the SES sending rate. Implement client-side backoff or "
        "request a quota increase (AWS Console → SES → Account dashboard)."
    ),
    "ConfigurationSetDoesNotExist": (
        "Referenced a non-existent SES configuration set. Either create it "
        "or remove the parameter from the request."
    ),
    "AccountSendingPausedException": (
        "AWS paused this account's sending — usually because the bounce or "
        "complaint rate crossed a threshold. Investigate metrics and contact "
        "AWS Support to restore sending."
    ),
}

DIAGNOSTIC_HINTS_SNS: dict[str, str] = {
    "InvalidParameter": (
        "Phone number not in E.164 (+<cc><number>), or the destination is "
        "not verified in the SNS SMS sandbox. Verify at AWS Console → SNS "
        "→ Mobile → Sandbox destination phone numbers, or request "
        "production access."
    ),
    "InvalidParameterValue": (
        "Same as InvalidParameter: check the E.164 format and verification "
        "status of the destination."
    ),
    "AuthorizationError": (
        "IAM principal lacks sns:Publish. Attach a policy allowing "
        "sns:Publish (scoped to the target phone or '*')."
    ),
    "AccessDeniedException": (
        "Same as AuthorizationError — missing sns:Publish IAM permission."
    ),
    "ThrottlingException": (
        "Exceeded the SNS SMS rate. Implement backoff or contact AWS to "
        "raise the limit."
    ),
    "EndpointDisabled": (
        "The destination is disabled, typically because the user replied "
        "STOP. The number is on the opt-out list."
    ),
    "OptedOut": (
        "The destination opted out via STOP. The platform must not re-send "
        "until the user opts back in (REPLY START)."
    ),
}


_UNKNOWN_HINT = (
    "Unknown AWS error code. Use the aws_request_id and CloudTrail "
    "(or AWS Support) to investigate further."
)


def hint_for(*, service: str, code: str) -> str:
    """Return the actionable hint for an AWS error code."""
    table = DIAGNOSTIC_HINTS_SES if service == "ses" else DIAGNOSTIC_HINTS_SNS
    return table.get(code, _UNKNOWN_HINT)


def extract_error_metadata(client_error) -> dict[str, Any]:
    """Pull AWS error code, message, request id and HTTP status from a ``ClientError``.

    boto3's ``ClientError`` stores everything in ``exc.response`` — the
    fields are present even when AWS returns a partial body, but we use
    ``.get()`` everywhere to stay defensive against future SDK changes.
    """
    response = getattr(client_error, "response", {}) or {}
    error = response.get("Error", {}) or {}
    metadata = response.get("ResponseMetadata", {}) or {}
    return {
        "aws_error_code": error.get("Code", "Unknown"),
        "aws_error_message": error.get("Message", str(client_error)),
        "aws_request_id": metadata.get("RequestId", ""),
        "http_status": metadata.get("HTTPStatusCode", 0),
    }


# ──────────────────────────────────────────────────────────────────────────
#  Startup / health-check validation
# ──────────────────────────────────────────────────────────────────────────


@dataclass
class CheckResult:
    """One row in the notifications-health snapshot."""

    name: str
    status: str             # "ok" | "warning" | "error"
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "details": self.details,
            "error": self.error,
        }


@dataclass
class NotificationsHealth:
    """Aggregate health report — what ``/health/notifications`` returns."""

    overall: str             # "healthy" | "degraded" | "unhealthy"
    checks: list[CheckResult]
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.overall,
            "checks": [c.to_dict() for c in self.checks],
            "timestamp": self.timestamp,
        }


async def validate_notifications_config(
    *, settings_obj, ses_client=None, sns_client=None
) -> NotificationsHealth:
    """Run read-only AWS checks against the current configuration.

    Args:
        settings_obj: The ``Settings`` instance — we read provider,
            region, ses_from_email, sns_sender_id from it. Accepting it
            as a parameter (rather than importing) keeps the function
            test-friendly.
        ses_client: Optional override (used by tests). Defaults to a
            fresh ``boto3.client('ses')`` when ``None``.
        sns_client: Optional override (used by tests). Defaults to a
            fresh ``boto3.client('sns')`` when ``None``.

    Returns:
        A :class:`NotificationsHealth` with one :class:`CheckResult` per
        probe. ``overall`` is derived from the worst individual status:
        any ``error`` → ``unhealthy``; any ``warning`` → ``degraded``;
        else ``healthy``.
    """
    if settings_obj.notifications_provider != "aws":
        # Nothing to probe — the log adapter is always healthy.
        return NotificationsHealth(
            overall="healthy",
            checks=[
                CheckResult(
                    name="provider",
                    status="ok",
                    details={"provider": settings_obj.notifications_provider},
                )
            ],
            timestamp=_now_iso(),
        )

    import boto3  # local import: keeps non-aws code paths free of boto3

    ses = ses_client or boto3.client("ses", region_name=settings_obj.aws_region)
    sns = sns_client or boto3.client("sns", region_name=settings_obj.aws_region)

    checks: list[CheckResult] = []
    checks.append(await _check_ses_credentials(ses, settings_obj))
    checks.append(await _check_ses_identity_verified(ses, settings_obj))
    checks.append(await _check_sns_attributes(sns, settings_obj))
    checks.append(await _check_sns_sandbox(sns, settings_obj))

    overall = _aggregate(checks)
    return NotificationsHealth(overall=overall, checks=checks, timestamp=_now_iso())


# ---- Individual probes ----------------------------------------------------


async def _check_ses_credentials(client, settings_obj) -> CheckResult:
    """Verify credentials by calling ``get_send_quota`` (free, read-only)."""
    try:
        quota = await asyncio.to_thread(client.get_send_quota)
    except Exception as exc:  # noqa: BLE001 — caught for the health report
        return _ses_error("ses.credentials", exc)

    used_pct = (
        (quota.get("SentLast24Hours", 0) / quota["Max24HourSend"] * 100)
        if quota.get("Max24HourSend")
        else 0
    )
    return CheckResult(
        name="ses.credentials",
        status="ok",
        details={
            "region": settings_obj.aws_region,
            "max_24h_send": quota.get("Max24HourSend"),
            "sent_last_24h": quota.get("SentLast24Hours"),
            "send_quota_used_pct": round(used_pct, 2),
            "max_send_rate": quota.get("MaxSendRate"),
        },
    )


async def _check_ses_identity_verified(client, settings_obj) -> CheckResult:
    """Verify that ``SES_FROM_EMAIL`` is a verified SES identity."""
    if not settings_obj.ses_from_email:
        return CheckResult(
            name="ses.from_email",
            status="error",
            error="SES_FROM_EMAIL is not configured.",
        )
    identity = settings_obj.ses_from_email
    try:
        result = await asyncio.to_thread(
            client.get_identity_verification_attributes,
            Identities=[identity],
        )
    except Exception as exc:  # noqa: BLE001
        return _ses_error("ses.from_email", exc, identity=identity)

    attrs = (result.get("VerificationAttributes") or {}).get(identity, {})
    verified = attrs.get("VerificationStatus") == "Success"
    return CheckResult(
        name="ses.from_email",
        status="ok" if verified else "error",
        details={
            "from_email": identity,
            "verification_status": attrs.get("VerificationStatus", "NotFound"),
            "from_email_verified": verified,
        },
        error=None if verified else (
            f"SES identity {identity!r} is NOT verified. Verify it at "
            f"AWS Console → SES → Verified identities."
        ),
    )


async def _check_sns_attributes(client, settings_obj) -> CheckResult:
    """Read SNS account-level SMS attributes (sender id default, spend limit)."""
    try:
        result = await asyncio.to_thread(client.get_sms_attributes)
    except Exception as exc:  # noqa: BLE001
        return _ses_error("sns.attributes", exc)

    attrs = result.get("attributes", {}) or {}
    spend_limit = attrs.get("MonthlySpendLimit")
    return CheckResult(
        name="sns.attributes",
        status="ok",
        details={
            "region": settings_obj.aws_region,
            "sender_id_default": attrs.get("DefaultSenderID"),
            "monthly_spend_limit_usd": float(spend_limit) if spend_limit else None,
            "default_sms_type": attrs.get("DefaultSMSType"),
            "configured_sender_id": settings_obj.sns_sender_id,
        },
    )


async def _check_sns_sandbox(client, settings_obj) -> CheckResult:
    """Determine whether the account is still in the SNS SMS sandbox."""
    try:
        status = await asyncio.to_thread(client.get_sms_sandbox_account_status)
    except Exception as exc:  # noqa: BLE001
        return _ses_error("sns.sandbox", exc)

    in_sandbox = bool(status.get("IsInSandbox"))
    return CheckResult(
        name="sns.sandbox",
        # In sandbox is a "warning" — the app starts fine, but only
        # verified destinations will receive SMS. Engineers reading the
        # boot log can decide whether to request production access.
        status="warning" if in_sandbox else "ok",
        details={"in_sandbox": in_sandbox},
        error=(
            "SNS is in SMS sandbox — only pre-verified phone numbers will "
            "receive SMS. Request production access at AWS Console → SNS → "
            "Mobile → Text messaging → Exit SMS sandbox."
        ) if in_sandbox else None,
    )


# ---- Helpers --------------------------------------------------------------


def _ses_error(name: str, exc: Exception, **extra) -> CheckResult:
    """Wrap any boto3 exception into a structured ``CheckResult``."""
    try:
        from botocore.exceptions import ClientError
        if isinstance(exc, ClientError):
            meta = extract_error_metadata(exc)
            return CheckResult(
                name=name,
                status="error",
                details={**extra, **meta},
                error=f"{meta['aws_error_code']}: {meta['aws_error_message']}",
            )
    except Exception:  # noqa: BLE001
        pass
    return CheckResult(
        name=name,
        status="error",
        details={**extra, "exception_type": type(exc).__name__},
        error=str(exc),
    )


def _aggregate(checks: list[CheckResult]) -> str:
    """Roll individual statuses up to an overall ``healthy/degraded/unhealthy``."""
    statuses = {c.status for c in checks}
    if "error" in statuses:
        return "unhealthy"
    if "warning" in statuses:
        return "degraded"
    return "healthy"


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


async def log_startup_validation(settings_obj) -> None:
    """Run the validators at boot and log a one-line summary plus per-check details.

    Failures are logged at WARNING (operational issues like sandbox /
    unverified identities) or ERROR (credential / authorization
    failures), but NEVER raise — the API must come up even when AWS is
    misconfigured.
    """
    try:
        report = await validate_notifications_config(settings_obj=settings_obj)
    except Exception:  # noqa: BLE001 — never crash startup
        _logger.exception("notifications.startup.validation_unexpected_failure")
        return

    _logger.info(
        "notifications.startup.validated",
        extra={"overall": report.overall, "timestamp": report.timestamp},
    )
    for check in report.checks:
        if check.status == "ok":
            _logger.info(
                f"notifications.startup.{check.name}",
                extra={"status": "ok", **check.details},
            )
        elif check.status == "warning":
            _logger.warning(
                f"notifications.startup.{check.name}",
                extra={
                    "status": "warning",
                    "diagnostic_hint": check.error,
                    **check.details,
                },
            )
        else:
            _logger.error(
                f"notifications.startup.{check.name}",
                extra={
                    "status": "error",
                    "diagnostic_hint": check.error,
                    **check.details,
                },
            )
