# Python
from http import HTTPStatus
from unittest.mock import AsyncMock

# Libs
from bson import ObjectId

# Core
from core.security import hash_password

# Module
from modules.auth.manager import User


class TestLogin:

    def test_login_success_returns_token(self, client, monkeypatch):
        user_doc = {
            "_id": ObjectId(),
            "email": "ana@example.com",
            "password_hash": hash_password("Password123"),
            "role": "USER",
            "is_active": True,
        }
        monkeypatch.setattr(User.objects, "get_by_email", AsyncMock(return_value=user_doc))

        response = client.post("/auth/login", json={"email": "ana@example.com", "password": "Password123"})

        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert body["token_type"] == "bearer"
        assert body["access_token"]

    def test_login_wrong_password_returns_401(self, client, monkeypatch):
        user_doc = {
            "_id": ObjectId(),
            "email": "ana@example.com",
            "password_hash": hash_password("Password123"),
            "role": "USER",
            "is_active": True,
        }
        monkeypatch.setattr(User.objects, "get_by_email", AsyncMock(return_value=user_doc))

        response = client.post("/auth/login", json={"email": "ana@example.com", "password": "WrongPass1"})

        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.json()["message"] == "Invalid credentials"

    def test_login_nonexistent_user_returns_401_same_message(self, client, monkeypatch):
        monkeypatch.setattr(User.objects, "get_by_email", AsyncMock(return_value=None))

        response = client.post("/auth/login", json={"email": "nobody@example.com", "password": "Password123"})

        assert response.status_code == HTTPStatus.UNAUTHORIZED
        # Identical message to wrong-password — no user enumeration.
        assert response.json()["message"] == "Invalid credentials"

    def test_login_inactive_user_returns_403(self, client, monkeypatch):
        user_doc = {
            "_id": ObjectId(),
            "email": "ana@example.com",
            "password_hash": hash_password("Password123"),
            "role": "USER",
            "is_active": False,
        }
        monkeypatch.setattr(User.objects, "get_by_email", AsyncMock(return_value=user_doc))

        response = client.post("/auth/login", json={"email": "ana@example.com", "password": "Password123"})

        assert response.status_code == HTTPStatus.FORBIDDEN
        assert response.json()["error"] == "INACTIVE_USER"
