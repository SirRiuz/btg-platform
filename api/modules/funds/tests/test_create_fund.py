# Python
from datetime import datetime, timezone
from http import HTTPStatus
from unittest.mock import AsyncMock

# Libs
from bson import ObjectId

# Constants
from constants.funds_exceptions import FundAlreadyExistsError

# Core
from core.security import create_jwt

# Module
from modules.auth.manager import RevokedToken, User
from modules.funds.manager import Fund
from modules.funds.schemas import Categoria, FundResponseDTO, PerfilRiesgo


def _user_doc(role: str = "ADMIN", **overrides):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    doc = {
        "_id": ObjectId(),
        "email": "admin@example.com",
        "role": role,
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


def _wire_authn(monkeypatch, user_doc) -> None:
    monkeypatch.setattr(User.objects, "get_by_id", AsyncMock(return_value=user_doc))
    monkeypatch.setattr(RevokedToken.objects, "is_revoked", AsyncMock(return_value=False))


VALID_PAYLOAD = {
    "id": 99,
    "nombre": "FONDO_TEST_CREAR",
    "monto_minimo": 100_000,
    "categoria": "FPV",
    "descripcion": "Fondo nuevo para pruebas",
    "perfil_riesgo": "MODERADO",
}


def _created_dto() -> FundResponseDTO:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return FundResponseDTO(
        id=VALID_PAYLOAD["id"],
        nombre=VALID_PAYLOAD["nombre"],
        monto_minimo=VALID_PAYLOAD["monto_minimo"],
        categoria=Categoria.FPV,
        descripcion=VALID_PAYLOAD["descripcion"],
        perfil_riesgo=PerfilRiesgo.MODERADO,
        activo=True,
        created_at=now,
        updated_at=now,
    )


class TestCreateFund:

    def test_create_fund_success_as_admin(self, client, monkeypatch):
        admin = _user_doc(role="ADMIN")
        _wire_authn(monkeypatch, admin)
        create_mock = AsyncMock(return_value=_created_dto())
        monkeypatch.setattr(Fund.objects, "create_fund", create_mock)

        response = client.post(
            "/admin/funds", json=VALID_PAYLOAD, headers=_auth_headers(admin)
        )

        assert response.status_code == HTTPStatus.CREATED
        body = response.json()
        assert body["id"] == VALID_PAYLOAD["id"]
        assert body["nombre"] == VALID_PAYLOAD["nombre"]
        assert body["categoria"] == "FPV"
        assert body["activo"] is True
        create_mock.assert_awaited_once()

    def test_create_fund_as_regular_user_returns_403(self, client, monkeypatch):
        user = _user_doc(role="USER")
        _wire_authn(monkeypatch, user)
        create_mock = AsyncMock(return_value=_created_dto())
        monkeypatch.setattr(Fund.objects, "create_fund", create_mock)

        response = client.post(
            "/admin/funds", json=VALID_PAYLOAD, headers=_auth_headers(user)
        )

        assert response.status_code == HTTPStatus.FORBIDDEN
        assert response.json()["error"] == "INSUFFICIENT_ROLE"
        # The manager must not be touched when authorization fails.
        create_mock.assert_not_awaited()

    def test_create_fund_without_jwt_returns_401(self, client):
        response = client.post("/admin/funds", json=VALID_PAYLOAD)
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.json()["error"] == "MISSING_TOKEN"

    def test_create_fund_duplicate_id_returns_409(self, client, monkeypatch):
        admin = _user_doc(role="ADMIN")
        _wire_authn(monkeypatch, admin)
        monkeypatch.setattr(
            Fund.objects,
            "create_fund",
            AsyncMock(side_effect=FundAlreadyExistsError.from_id(VALID_PAYLOAD["id"])),
        )

        response = client.post(
            "/admin/funds", json=VALID_PAYLOAD, headers=_auth_headers(admin)
        )

        assert response.status_code == HTTPStatus.CONFLICT
        body = response.json()
        assert body["error"] == "FUND_ALREADY_EXISTS"
        assert str(VALID_PAYLOAD["id"]) in body["message"]

    def test_create_fund_duplicate_nombre_returns_409(self, client, monkeypatch):
        admin = _user_doc(role="ADMIN")
        _wire_authn(monkeypatch, admin)
        monkeypatch.setattr(
            Fund.objects,
            "create_fund",
            AsyncMock(
                side_effect=FundAlreadyExistsError.from_nombre(VALID_PAYLOAD["nombre"])
            ),
        )

        response = client.post(
            "/admin/funds", json=VALID_PAYLOAD, headers=_auth_headers(admin)
        )

        assert response.status_code == HTTPStatus.CONFLICT
        body = response.json()
        assert body["error"] == "FUND_ALREADY_EXISTS"
        assert VALID_PAYLOAD["nombre"] in body["message"]

    def test_create_fund_invalid_categoria_returns_422(self, client, monkeypatch):
        admin = _user_doc(role="ADMIN")
        _wire_authn(monkeypatch, admin)

        bad = {**VALID_PAYLOAD, "categoria": "XYZ"}
        response = client.post("/admin/funds", json=bad, headers=_auth_headers(admin))

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert response.json()["error"] == "VALIDATION_ERROR"

    def test_create_fund_negative_monto_minimo_returns_422(self, client, monkeypatch):
        admin = _user_doc(role="ADMIN")
        _wire_authn(monkeypatch, admin)

        bad = {**VALID_PAYLOAD, "monto_minimo": -1}
        response = client.post("/admin/funds", json=bad, headers=_auth_headers(admin))

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert response.json()["error"] == "VALIDATION_ERROR"

    def test_create_fund_zero_monto_minimo_returns_422(self, client, monkeypatch):
        """``monto_minimo`` must be strictly greater than 0 — pin the boundary."""
        admin = _user_doc(role="ADMIN")
        _wire_authn(monkeypatch, admin)

        bad = {**VALID_PAYLOAD, "monto_minimo": 0}
        response = client.post("/admin/funds", json=bad, headers=_auth_headers(admin))

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_create_fund_short_nombre_returns_422(self, client, monkeypatch):
        admin = _user_doc(role="ADMIN")
        _wire_authn(monkeypatch, admin)

        bad = {**VALID_PAYLOAD, "nombre": "ab"}  # < 3 chars
        response = client.post("/admin/funds", json=bad, headers=_auth_headers(admin))

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
