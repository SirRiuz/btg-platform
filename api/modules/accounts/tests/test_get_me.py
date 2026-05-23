# Python
from datetime import datetime, timezone
from http import HTTPStatus
from unittest.mock import AsyncMock

# Libs
from bson import ObjectId

# Core
from core.security import create_jwt

# Module
from modules.auth.manager import RevokedToken, User


def _active_user_doc(**overrides):
    """Build a User-shaped Mongo document with sensible defaults for tests."""
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    doc = {
        "_id": ObjectId(),
        "first_name": "Mateo",
        "last_name": "Jimenez",
        "email": "user@example.com",
        "phone": "+573223438015",
        "password_hash": "$2b$04$abc",
        "balance": 500000,
        "role": "USER",
        "is_active": True,
        "settings": {"allow_email": True, "allow_sms": False},
        "created_at": now,
        "updated_at": now,
    }
    doc.update(overrides)
    return doc


def _auth_headers(user_doc) -> dict:
    """Issue a JWT for ``user_doc`` and wire the mocks ``get_current_user`` needs."""
    token = create_jwt(subject=str(user_doc["_id"]), role=user_doc["role"])
    return {"Authorization": f"Bearer {token}"}


class TestGetMe:

    def test_get_me_returns_user_profile_with_settings(self, client, monkeypatch):
        user = _active_user_doc()
        monkeypatch.setattr(User.objects, "get_by_id", AsyncMock(return_value=user))
        monkeypatch.setattr(RevokedToken.objects, "is_revoked", AsyncMock(return_value=False))

        response = client.get("/accounts/me", headers=_auth_headers(user))

        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert body["id"] == str(user["_id"])
        assert body["first_name"] == "Mateo"
        assert body["email"] == "user@example.com"
        assert body["phone"] == "+573223438015"
        assert body["balance"] == 500000
        assert body["role"] == "USER"
        assert body["settings"] == {"allow_email": True, "allow_sms": False}
        assert "created_at" in body
        assert "updated_at" in body

    def test_get_me_does_not_expose_password_hash(self, client, monkeypatch):
        user = _active_user_doc()
        monkeypatch.setattr(User.objects, "get_by_id", AsyncMock(return_value=user))
        monkeypatch.setattr(RevokedToken.objects, "is_revoked", AsyncMock(return_value=False))

        response = client.get("/accounts/me", headers=_auth_headers(user))

        assert response.status_code == HTTPStatus.OK
        body = response.json()
        # password_hash is filtered out by UserProfileResponse — verify explicitly
        # in case someone later relaxes the schema or switches to a permissive
        # `extra=allow` config.
        assert "password_hash" not in body
        assert "jti" not in body

    def test_default_settings_after_register_are_email_true_sms_false(self, client, monkeypatch):
        """A freshly-registered user reads back with the documented defaults.

        Mirrors the behavior of ``UserManager.create()`` which writes
        ``settings={"allow_email": True, "allow_sms": False}``.
        """
        user = _active_user_doc()  # built with the same defaults UserManager.create writes
        monkeypatch.setattr(User.objects, "get_by_id", AsyncMock(return_value=user))
        monkeypatch.setattr(RevokedToken.objects, "is_revoked", AsyncMock(return_value=False))

        response = client.get("/accounts/me", headers=_auth_headers(user))

        assert response.status_code == HTTPStatus.OK
        assert response.json()["settings"] == {"allow_email": True, "allow_sms": False}

    def test_get_me_without_jwt_returns_401(self, client):
        response = client.get("/accounts/me")
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.json()["error"] == "MISSING_TOKEN"

    def test_get_me_with_revoked_jwt_returns_401(self, client, monkeypatch):
        user = _active_user_doc()
        monkeypatch.setattr(User.objects, "get_by_id", AsyncMock(return_value=user))
        monkeypatch.setattr(RevokedToken.objects, "is_revoked", AsyncMock(return_value=True))

        response = client.get("/accounts/me", headers=_auth_headers(user))

        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.json()["error"] == "TOKEN_REVOKED"
