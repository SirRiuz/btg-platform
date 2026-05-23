# Python
from typing import Annotated

# FastApi
import fastapi
from fastapi import Depends, status

# Constants
from constants.accounts import AccountMessages

# Module
from modules.accounts.manager import Account
from modules.accounts.manager.account import _profile_from_doc
from modules.accounts.schemas import (
    EmailNotificationsUpdateRequest,
    NotificationSettingsResponse,
    SmsNotificationsUpdateRequest,
    UserProfileResponse,
)
from modules.auth.dependencies import get_current_user


router = fastapi.APIRouter(prefix="/accounts", tags=["accounts"])


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    response_model=UserProfileResponse,
    summary="Return the authenticated user's full profile",
)
async def me(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> UserProfileResponse:
    """Return the public profile of the caller, including notification settings.

    The user document has already been read from Mongo by
    :func:`get_current_user` (which decoded the JWT, checked the
    blacklist and confirmed the account is active), so this handler
    simply projects it into :class:`UserProfileResponse`. Doing the
    projection in code — rather than relying on Pydantic to ignore extra
    fields — guarantees that ``password_hash`` and other internal fields
    can never leak via this endpoint, even if the response model is
    later switched to ``model_config = ConfigDict(extra='allow')``.
    """
    return _profile_from_doc(current_user)


@router.put(
    "/me/settings/email-notifications",
    status_code=status.HTTP_200_OK,
    response_model=NotificationSettingsResponse,
    summary="Enable or disable email notifications for the authenticated user",
)
async def update_email_notifications(
    payload: EmailNotificationsUpdateRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> NotificationSettingsResponse:
    """Toggle ``settings.allow_email`` for the caller.

    The endpoint is idempotent — sending the same ``enabled`` value twice
    is indistinguishable from sending it once, which is why we use PUT
    instead of POST. The body is intentionally a single boolean so the
    same route covers enable and disable; the alternative
    (``/activate-email-notifications`` and ``/deactivate-...``) doubles
    the surface for no extra expressiveness.

    Users can only modify their own settings: the ``user_id`` always
    comes from the JWT-derived ``current_user``, never from the URL or
    body — there is no path on this endpoint to act on another account.
    """
    settings = await Account.objects.update_email_notifications(
        user_id=str(current_user["_id"]),
        enabled=payload.enabled,
    )
    return NotificationSettingsResponse(
        settings=settings,
        message=AccountMessages.SETTINGS_UPDATED,
    )


@router.put(
    "/me/settings/sms-notifications",
    status_code=status.HTTP_200_OK,
    response_model=NotificationSettingsResponse,
    summary="Enable or disable SMS notifications for the authenticated user",
)
async def update_sms_notifications(
    payload: SmsNotificationsUpdateRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> NotificationSettingsResponse:
    """Mirror of :func:`update_email_notifications` for the SMS channel.

    Same idempotency, same self-only semantics, same single-boolean body.
    The two endpoints are intentionally separate (rather than a generic
    ``PUT /me/settings``) so the API surfaces each channel as an
    independent toggle — easier for clients to render and easier to
    instrument per-channel adoption analytics.
    """
    settings = await Account.objects.update_sms_notifications(
        user_id=str(current_user["_id"]),
        enabled=payload.enabled,
    )
    return NotificationSettingsResponse(
        settings=settings,
        message=AccountMessages.SETTINGS_UPDATED,
    )
