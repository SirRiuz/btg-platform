# Python
from http import HTTPStatus
from unittest.mock import AsyncMock

# Libs
from bson import ObjectId

# Core
from core.security import create_jwt

# Module
from modules.auth.manager import RevokedToken, User


def _active_user():
    return {
        "_id": ObjectId(),
        "email": "ana@example.com",
        "role": "USER",
        "is_active": True,
    }


class TestLogout:

    def test_logout_revokes_token(self, client, monkeypatch):
        user = _active_user()
        monkeypatch.setattr(User.objects, "get_by_id", AsyncMock(return_value=user))
        monkeypatch.setattr(RevokedToken.objects, "is_revoked", AsyncMock(return_value=False))
        add_mock = AsyncMock()
        monkeypatch.setattr(RevokedToken.objects, "add", add_mock)

        token = create_jwt(subject=str(user["_id"]), role="USER")
        response = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == HTTPStatus.OK
        assert response.json()["message"] == "Session closed successfully"
        add_mock.assert_awaited_once()

    def test_revoked_token_cannot_be_used(self, client, monkeypatch):
        user = _active_user()
        monkeypatch.setattr(User.objects, "get_by_id", AsyncMock(return_value=user))
        monkeypatch.setattr(RevokedToken.objects, "is_revoked", AsyncMock(return_value=True))

        token = create_jwt(subject=str(user["_id"]), role="USER")
        response = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.json()["error"] == "TOKEN_REVOKED"

    def test_logout_without_token_returns_401(self, client):
        response = client.post("/auth/logout")
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.json()["error"] == "MISSING_TOKEN"

    def test_logout_with_invalid_token_returns_401(self, client):
        response = client.post("/auth/logout", headers={"Authorization": "Bearer not.a.jwt"})
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.json()["error"] == "INVALID_TOKEN"
