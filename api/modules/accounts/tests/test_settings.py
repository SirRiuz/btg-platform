# Python
from datetime import datetime, timezone
from http import HTTPStatus
from unittest.mock import AsyncMock

# Libs
from bson import ObjectId

# Core
from core.security import create_jwt

# Module
from modules.accounts.manager import Account
from modules.accounts.schemas import NotificationSettingsDTO
from modules.auth.manager import RevokedToken, User


def _active_user_doc(**overrides):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    doc = {
        "_id": ObjectId(),
        "email": "user@example.com",
        "role": "USER",
        "is_active": True,
        "settings": {"allow_email": True, "allow_sms": False},
        "created_at": now,
        "updated_at": now,
    }
    doc.update(overrides)
    return doc


def _auth_headers(user_doc) -> dict:
    token = create_jwt(subject=str(user_doc["_id"]), role=user_doc["role"])
    return {"Authorization": f"Bearer {token}"}


def _wire_authn(monkeypatch, user_doc):
    """Stub the auth pipeline so ``get_current_user`` returns ``user_doc``."""
    monkeypatch.setattr(User.objects, "get_by_id", AsyncMock(return_value=user_doc))
    monkeypatch.setattr(RevokedToken.objects, "is_revoked", AsyncMock(return_value=False))


class TestUpdateEmailNotifications:

    def test_update_email_notifications_enables_correctly(self, client, monkeypatch):
        user = _active_user_doc(settings={"allow_email": False, "allow_sms": False})
        _wire_authn(monkeypatch, user)
        manager_mock = AsyncMock(return_value=NotificationSettingsDTO(allow_email=True, allow_sms=False))
        monkeypatch.setattr(Account.objects, "update_email_notifications", manager_mock)

        response = client.put(
            "/accounts/me/settings/email-notifications",
            json={"enabled": True},
            headers=_auth_headers(user),
        )

        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert body["settings"] == {"allow_email": True, "allow_sms": False}
        assert body["message"] == "Settings updated successfully"
        manager_mock.assert_awaited_once_with(user_id=str(user["_id"]), enabled=True)

    def test_update_email_notifications_disables_correctly(self, client, monkeypatch):
        user = _active_user_doc(settings={"allow_email": True, "allow_sms": True})
        _wire_authn(monkeypatch, user)
        monkeypatch.setattr(
            Account.objects,
            "update_email_notifications",
            AsyncMock(return_value=NotificationSettingsDTO(allow_email=False, allow_sms=True)),
        )

        response = client.put(
            "/accounts/me/settings/email-notifications",
            json={"enabled": False},
            headers=_auth_headers(user),
        )

        assert response.status_code == HTTPStatus.OK
        assert response.json()["settings"] == {"allow_email": False, "allow_sms": True}

    def test_invalid_body_returns_422(self, client, monkeypatch):
        user = _active_user_doc()
        _wire_authn(monkeypatch, user)

        response = client.put(
            "/accounts/me/settings/email-notifications",
            json={"enabled": "not-a-bool"},
            headers=_auth_headers(user),
        )

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert response.json()["error"] == "VALIDATION_ERROR"


class TestUpdateSmsNotifications:

    def test_update_sms_notifications_enables_correctly(self, client, monkeypatch):
        user = _active_user_doc(settings={"allow_email": True, "allow_sms": False})
        _wire_authn(monkeypatch, user)
        manager_mock = AsyncMock(return_value=NotificationSettingsDTO(allow_email=True, allow_sms=True))
        monkeypatch.setattr(Account.objects, "update_sms_notifications", manager_mock)

        response = client.put(
            "/accounts/me/settings/sms-notifications",
            json={"enabled": True},
            headers=_auth_headers(user),
        )

        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert body["settings"] == {"allow_email": True, "allow_sms": True}
        assert body["message"] == "Settings updated successfully"
        manager_mock.assert_awaited_once_with(user_id=str(user["_id"]), enabled=True)

    def test_update_sms_notifications_disables_correctly(self, client, monkeypatch):
        user = _active_user_doc(settings={"allow_email": True, "allow_sms": True})
        _wire_authn(monkeypatch, user)
        monkeypatch.setattr(
            Account.objects,
            "update_sms_notifications",
            AsyncMock(return_value=NotificationSettingsDTO(allow_email=True, allow_sms=False)),
        )

        response = client.put(
            "/accounts/me/settings/sms-notifications",
            json={"enabled": False},
            headers=_auth_headers(user),
        )

        assert response.status_code == HTTPStatus.OK
        assert response.json()["settings"] == {"allow_email": True, "allow_sms": False}


class TestIsolationAndAuthZ:

    def test_settings_are_independent_email_does_not_affect_sms(self, client, monkeypatch):
        """Toggling email leaves SMS untouched (and vice versa).

        Verified at the route layer: when the manager returns the updated
        settings, the response carries both channels and the unaffected
        one preserves its previous value.
        """
        user = _active_user_doc(settings={"allow_email": False, "allow_sms": True})
        _wire_authn(monkeypatch, user)
        # Manager returns the new full settings: email flipped, sms untouched.
        monkeypatch.setattr(
            Account.objects,
            "update_email_notifications",
            AsyncMock(return_value=NotificationSettingsDTO(allow_email=True, allow_sms=True)),
        )

        response = client.put(
            "/accounts/me/settings/email-notifications",
            json={"enabled": True},
            headers=_auth_headers(user),
        )

        assert response.status_code == HTTPStatus.OK
        assert response.json()["settings"]["allow_sms"] is True  # not touched by email toggle

    def test_user_cannot_modify_other_user_settings(self, client, monkeypatch):
        """The route always passes ``current_user["_id"]`` — not anything caller-controlled.

        The test forges an "attacker" JWT for user A, and asserts the
        manager is invoked with user A's id no matter what the body says.
        Since the endpoint has no path-param or body field for ``user_id``,
        this is structurally impossible to bypass; this test pins that
        property so a future refactor cannot accidentally expose it.
        """
        attacker = _active_user_doc()
        _wire_authn(monkeypatch, attacker)
        manager_mock = AsyncMock(return_value=NotificationSettingsDTO(allow_email=False, allow_sms=False))
        monkeypatch.setattr(Account.objects, "update_email_notifications", manager_mock)

        # Body includes a stray field that should be ignored — Pydantic strips
        # unknowns by default, and the route never forwards them anyway.
        response = client.put(
            "/accounts/me/settings/email-notifications",
            json={"enabled": False, "user_id": str(ObjectId())},
            headers=_auth_headers(attacker),
        )

        assert response.status_code == HTTPStatus.OK
        # Manager received the attacker's id (from the JWT), not the body's id.
        manager_mock.assert_awaited_once_with(user_id=str(attacker["_id"]), enabled=False)
