"""HTTP endpoint that surfaces the notifications health check.

The endpoint runs the same probes as ``validate_notifications_config``
at startup, but on demand — useful for:

* Debugging a misconfigured deploy from Postman without redeploying.
* Liveness/readiness checks in a Kubernetes-style orchestrator that
  needs JSON output, not just an HTTP 200.

The route deliberately always returns HTTP 200 with a body that
describes the state: ``status: healthy | degraded | unhealthy``. A 5xx
status here would conflate "the API is down" with "AWS notifications
are misconfigured", and we want those two to be distinguishable.
"""

# Python
from typing import Annotated

# FastApi
import fastapi
from fastapi import Depends, status

# Core
from core.settings import settings

# Module
from modules.auth.dependencies import get_current_user
from modules.notifications.diagnostics import validate_notifications_config


router = fastapi.APIRouter(prefix="/health", tags=["health"])


@router.get(
    "/notifications",
    status_code=status.HTTP_200_OK,
    summary="Notifications subsystem health (SES + SNS probes)",
)
async def notifications_health(
    _: Annotated[dict, Depends(get_current_user)],
) -> dict:
    """Return a JSON snapshot of the notifications subsystem.

    The endpoint is authenticated (any JWT) — the probes call AWS and
    we don't want them to be publicly drainable. They're also cheap
    (single API call each); no aggressive caching is needed for the
    technical-test workload.
    """
    report = await validate_notifications_config(settings_obj=settings)
    return report.to_dict()
