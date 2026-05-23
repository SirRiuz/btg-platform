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
from modules.funds.manager import Fund
from modules.funds.schemas import Categoria, FundResponseDTO, PerfilRiesgo


def _active_user_doc(role: str = "USER", **overrides):
    """Build a User-shaped Mongo document with sensible defaults for tests."""
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    doc = {
        "_id": ObjectId(),
        "email": "user@example.com",
        "role": role,
        "is_active": True,
        "settings": {"allow_email": True, "allow_sms": False},
        "created_at": now,
        "updated_at": now,
    }
    doc.update(overrides)
    return doc


def _auth_headers(user_doc) -> dict:
    """Issue a JWT for ``user_doc`` and return the Bearer headers."""
    token = create_jwt(subject=str(user_doc["_id"]), role=user_doc["role"])
    return {"Authorization": f"Bearer {token}"}


def _wire_authn(monkeypatch, user_doc) -> None:
    """Stub the auth pipeline so ``get_current_user`` returns ``user_doc``."""
    monkeypatch.setattr(User.objects, "get_by_id", AsyncMock(return_value=user_doc))
    monkeypatch.setattr(RevokedToken.objects, "is_revoked", AsyncMock(return_value=False))


def _fund_dto(**overrides) -> FundResponseDTO:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    base = {
        "id": 1,
        "nombre": "FPV_BTG_PACTUAL_RECAUDADORA",
        "monto_minimo": 75_000,
        "categoria": Categoria.FPV,
        "descripcion": None,
        "perfil_riesgo": PerfilRiesgo.BAJO,
        "activo": True,
        "created_at": now,
        "updated_at": now,
    }
    base.update(overrides)
    return FundResponseDTO(**base)


class TestListFunds:

    def test_list_funds_returns_only_active(self, client, monkeypatch):
        """The route delegates to ``list_active_funds`` — the manager is
        responsible for filtering ``activo=True``. We verify the contract
        here by asserting the route calls the right method (and trusts it
        with the active-only invariant)."""
        user = _active_user_doc()
        _wire_authn(monkeypatch, user)
        list_mock = AsyncMock(return_value=([_fund_dto()], 1))
        monkeypatch.setattr(Fund.objects, "list_active_funds", list_mock)

        response = client.get("/funds", headers=_auth_headers(user))

        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert body["total"] == 1
        assert len(body["items"]) == 1
        assert body["items"][0]["activo"] is True
        # The route MUST go through list_active_funds (not a raw find).
        list_mock.assert_awaited_once()

    def test_list_funds_with_pagination(self, client, monkeypatch):
        user = _active_user_doc()
        _wire_authn(monkeypatch, user)
        items = [_fund_dto(id=i, nombre=f"FUND_{i}") for i in range(3, 6)]
        list_mock = AsyncMock(return_value=(items, 10))
        monkeypatch.setattr(Fund.objects, "list_active_funds", list_mock)

        response = client.get(
            "/funds?skip=2&limit=3", headers=_auth_headers(user)
        )

        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert body["skip"] == 2
        assert body["limit"] == 3
        assert body["total"] == 10
        assert [item["id"] for item in body["items"]] == [3, 4, 5]
        list_mock.assert_awaited_once_with(filters={}, skip=2, limit=3)

    def test_list_funds_filter_by_categoria(self, client, monkeypatch):
        user = _active_user_doc()
        _wire_authn(monkeypatch, user)
        list_mock = AsyncMock(return_value=([_fund_dto(categoria=Categoria.FIC)], 1))
        monkeypatch.setattr(Fund.objects, "list_active_funds", list_mock)

        response = client.get("/funds?categoria=FIC", headers=_auth_headers(user))

        assert response.status_code == HTTPStatus.OK
        list_mock.assert_awaited_once_with(filters={"categoria": "FIC"}, skip=0, limit=20)

    def test_list_funds_filter_by_perfil_riesgo(self, client, monkeypatch):
        user = _active_user_doc()
        _wire_authn(monkeypatch, user)
        list_mock = AsyncMock(return_value=([_fund_dto(perfil_riesgo=PerfilRiesgo.ALTO)], 1))
        monkeypatch.setattr(Fund.objects, "list_active_funds", list_mock)

        response = client.get(
            "/funds?perfil_riesgo=ALTO", headers=_auth_headers(user)
        )

        assert response.status_code == HTTPStatus.OK
        list_mock.assert_awaited_once_with(
            filters={"perfil_riesgo": "ALTO"}, skip=0, limit=20
        )

    def test_list_funds_without_jwt_returns_401(self, client):
        response = client.get("/funds")
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.json()["error"] == "MISSING_TOKEN"

    def test_list_funds_invalid_limit_returns_422(self, client, monkeypatch):
        """``limit`` is capped at 100 — Pydantic should reject 101."""
        user = _active_user_doc()
        _wire_authn(monkeypatch, user)

        response = client.get("/funds?limit=500", headers=_auth_headers(user))

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
