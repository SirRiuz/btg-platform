# Python
from datetime import datetime, timezone
from http import HTTPStatus
from unittest.mock import AsyncMock

# Libs
from bson import ObjectId

# Constants
from constants.funds_exceptions import FundAlreadyInactiveError, FundNotFoundError

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


def _deactivated_dto(fund_id: int, nombre: str) -> FundResponseDTO:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return FundResponseDTO(
        id=fund_id,
        nombre=nombre,
        monto_minimo=75_000,
        categoria=Categoria.FPV,
        descripcion=None,
        perfil_riesgo=PerfilRiesgo.BAJO,
        activo=False,
        created_at=now,
        updated_at=now,
    )


class TestDeleteFund:

    def test_delete_fund_success_marks_inactive(self, client, monkeypatch):
        admin = _user_doc(role="ADMIN")
        _wire_authn(monkeypatch, admin)
        soft_delete_mock = AsyncMock(
            return_value=_deactivated_dto(1, "FPV_BTG_PACTUAL_RECAUDADORA")
        )
        monkeypatch.setattr(Fund.objects, "soft_delete_fund", soft_delete_mock)

        response = client.delete("/admin/funds/1", headers=_auth_headers(admin))

        assert response.status_code == HTTPStatus.OK
        body = response.json()
        assert body["fund_id"] == 1
        assert "FPV_BTG_PACTUAL_RECAUDADORA" in body["message"]
        soft_delete_mock.assert_awaited_once_with(1)

    def test_delete_fund_as_regular_user_returns_403(self, client, monkeypatch):
        user = _user_doc(role="USER")
        _wire_authn(monkeypatch, user)
        soft_delete_mock = AsyncMock(return_value=_deactivated_dto(1, "X"))
        monkeypatch.setattr(Fund.objects, "soft_delete_fund", soft_delete_mock)

        response = client.delete("/admin/funds/1", headers=_auth_headers(user))

        assert response.status_code == HTTPStatus.FORBIDDEN
        assert response.json()["error"] == "INSUFFICIENT_ROLE"
        soft_delete_mock.assert_not_awaited()

    def test_delete_fund_without_jwt_returns_401(self, client):
        response = client.delete("/admin/funds/1")
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.json()["error"] == "MISSING_TOKEN"

    def test_delete_nonexistent_fund_returns_404(self, client, monkeypatch):
        admin = _user_doc(role="ADMIN")
        _wire_authn(monkeypatch, admin)
        monkeypatch.setattr(
            Fund.objects,
            "soft_delete_fund",
            AsyncMock(side_effect=FundNotFoundError(999)),
        )

        response = client.delete("/admin/funds/999", headers=_auth_headers(admin))

        assert response.status_code == HTTPStatus.NOT_FOUND
        body = response.json()
        assert body["error"] == "FUND_NOT_FOUND"
        assert "999" in body["message"]

    def test_delete_already_inactive_fund_returns_409(self, client, monkeypatch):
        admin = _user_doc(role="ADMIN")
        _wire_authn(monkeypatch, admin)
        monkeypatch.setattr(
            Fund.objects,
            "soft_delete_fund",
            AsyncMock(side_effect=FundAlreadyInactiveError()),
        )

        response = client.delete("/admin/funds/1", headers=_auth_headers(admin))

        assert response.status_code == HTTPStatus.CONFLICT
        assert response.json()["error"] == "FUND_ALREADY_INACTIVE"

    def test_deleted_fund_does_not_appear_in_list(self, client, monkeypatch):
        """End-to-end-ish: after a delete, the listing returns zero rows.

        The manager is stubbed at both ends — delete returns success, then
        the next listing returns an empty page. This pins the *route-level*
        contract that the catalog endpoint never surfaces inactive funds.
        """
        admin = _user_doc(role="ADMIN")
        _wire_authn(monkeypatch, admin)
        monkeypatch.setattr(
            Fund.objects,
            "soft_delete_fund",
            AsyncMock(return_value=_deactivated_dto(1, "FPV_BTG_PACTUAL_RECAUDADORA")),
        )
        monkeypatch.setattr(
            Fund.objects, "list_active_funds", AsyncMock(return_value=([], 0))
        )

        delete_response = client.delete(
            "/admin/funds/1", headers=_auth_headers(admin)
        )
        assert delete_response.status_code == HTTPStatus.OK

        list_response = client.get("/funds", headers=_auth_headers(admin))
        assert list_response.status_code == HTTPStatus.OK
        body = list_response.json()
        assert body["items"] == []
        assert body["total"] == 0
