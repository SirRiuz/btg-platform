# Python
from datetime import datetime

# Libs
from pydantic import BaseModel, EmailStr

# Module
from modules.auth.schemas import UserRole


class NotificationSettingsDTO(BaseModel):
    """Reusable read model for a user's notification preferences.

    Returned by :meth:`AccountManager.get_notification_settings` and the
    settings-update endpoints. Kept deliberately small so other modules
    (notifications, funds, …) can consume it without inheriting any
    knowledge of the User document layout.
    """

    allow_email: bool
    allow_sms: bool


class UserProfileResponse(BaseModel):
    """Full public projection of a user — sensitive fields are filtered out.

    Used as the response model for ``GET /accounts/me``. ``password_hash``
    is impossible to leak here by construction: only the fields listed
    below are mapped, so adding a new sensitive column to the User
    document does not silently expose it via this endpoint.
    """

    id: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    balance: int
    role: UserRole
    settings: NotificationSettingsDTO
    created_at: datetime
    updated_at: datetime


class EmailNotificationsUpdateRequest(BaseModel):
    """Body of ``PUT /accounts/me/settings/email-notifications``.

    A single boolean lets the same endpoint enable and disable the channel,
    which is why PUT (idempotent) is appropriate over POST.
    """

    enabled: bool


class SmsNotificationsUpdateRequest(BaseModel):
    """Body of ``PUT /accounts/me/settings/sms-notifications`` — mirror of the email one."""

    enabled: bool


class NotificationSettingsResponse(BaseModel):
    """Response shape for the settings-update endpoints.

    Returns the **full** settings object (both channels) plus a confirmation
    message, so the caller does not need a follow-up read to render the new
    state of the toggle UI.
    """

    settings: NotificationSettingsDTO
    message: str
