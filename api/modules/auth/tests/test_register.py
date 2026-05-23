# Python
from http import HTTPStatus
from unittest.mock import AsyncMock

# Libs
from bson import ObjectId

# Constants
from constants.auth_exceptions import EmailAlreadyExistsError, PhoneAlreadyExistsError

# Module
from modules.auth.manager import User


VALID_PAYLOAD = {
    "first_name": "Mateo",
    "last_name": "Jimenez",
    "email": "User@Example.COM",
    "phone": "+57 3223438015",
    "password": "Password8.",
}


def _user_document(**overrides):
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
    }
    doc.update(overrides)
    return doc


class TestRegister:

    def test_register_success(self, client, monkeypatch):
        monkeypatch.setattr(User.objects, "create", AsyncMock(return_value=_user_document()))

        response = client.post("/auth/register", json=VALID_PAYLOAD)

        assert response.status_code == HTTPStatus.CREATED
        body = response.json()
        assert body["token_type"] == "bearer"
        assert body["access_token"]
        assert body["user"]["email"] == "user@example.com"
        assert body["user"]["phone"] == "+573223438015"
        assert body["user"]["balance"] == 500000
        assert body["user"]["role"] == "USER"

    def test_register_normalizes_local_phone_to_e164_colombia(self, client, monkeypatch):
        """Local Colombian numbers (no ``+``) are normalized to E.164.

        The validator uses ``phonenumbers`` with ``PHONE_DEFAULT_REGION='CO'``,
        so ``3223438015`` becomes ``+573223438015`` — the canonical form
        that AWS SNS requires and that downstream notifications use.
        """
        monkeypatch.setattr(
            User.objects, "create", AsyncMock(return_value=_user_document(phone="+573223438015"))
        )

        response = client.post("/auth/register", json={**VALID_PAYLOAD, "phone": "3223438015"})

        assert response.status_code == HTTPStatus.CREATED
        assert response.json()["user"]["phone"] == "+573223438015"

    def test_register_duplicate_email_returns_409(self, client, monkeypatch):
        monkeypatch.setattr(User.objects, "create", AsyncMock(side_effect=EmailAlreadyExistsError()))

        response = client.post("/auth/register", json=VALID_PAYLOAD)

        assert response.status_code == HTTPStatus.CONFLICT
        assert response.json()["error"] == "EMAIL_ALREADY_EXISTS"

    def test_register_duplicate_phone_returns_409(self, client, monkeypatch):
        monkeypatch.setattr(User.objects, "create", AsyncMock(side_effect=PhoneAlreadyExistsError()))

        response = client.post("/auth/register", json=VALID_PAYLOAD)

        assert response.status_code == HTTPStatus.CONFLICT
        assert response.json()["error"] == "PHONE_ALREADY_EXISTS"

    def test_register_invalid_email_format_returns_422(self, client):
        bad = {**VALID_PAYLOAD, "email": "not-an-email"}
        response = client.post("/auth/register", json=bad)
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert response.json()["error"] == "VALIDATION_ERROR"

    def test_register_weak_password_returns_422(self, client):
        bad = {**VALID_PAYLOAD, "password": "alllowercase"}
        response = client.post("/auth/register", json=bad)
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_register_invalid_phone_returns_422(self, client):
        # Letters in the phone are rejected even with the lenient validator.
        bad = {**VALID_PAYLOAD, "phone": "abc12345"}
        response = client.post("/auth/register", json=bad)
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
