# Python
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock

# Libs
import pytest

# Ensure env vars exist before importing `main` / `core.settings`.
os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DB_NAME", "soptest_test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-do-not-use-in-prod")
os.environ.setdefault("BCRYPT_ROUNDS", "4")


@pytest.fixture(autouse=True)
def _force_fallback_atomic_session(monkeypatch):
    """Force the fallback (no-transaction) path for every unit test.

    Production / Atlas deploys use real transactions; the local docker
    cluster does not — and most tests run with mocked collections that
    are not part of a real cluster anyway. Pinning fallback mode here
    keeps tests fast and deterministic. The transaction-supporting path
    is exercised by integration tests against a real replica set (not
    in this suite).
    """
    import modules.subscriptions.manager.subscription as sub_mod
    import modules.subscriptions.manager.atomic as atomic_mod

    @asynccontextmanager
    async def _fallback_session():
        yield None

    monkeypatch.setattr(sub_mod, "atomic_session", _fallback_session)
    monkeypatch.setattr(atomic_mod, "atomic_session", _fallback_session)


@pytest.fixture
def client(monkeypatch):
    """TestClient with Mongo + index creation mocked out.

    Mirrors the conftest used by every other module. Each test
    monkeypatches the specific manager methods it cares about.
    """
    from fastapi.testclient import TestClient
    import integrations.mongo.client as mongo_client
    from modules.auth.manager import RevokedToken, User
    from modules.funds.manager import Fund
    from modules.subscriptions.manager import Subscription, Transaction

    monkeypatch.setattr(mongo_client, "connect_to_mongo", AsyncMock())
    monkeypatch.setattr(mongo_client, "close_mongo_connection", AsyncMock())
    monkeypatch.setattr(User.objects, "ensure_indexes", AsyncMock())
    monkeypatch.setattr(RevokedToken.objects, "ensure_indexes", AsyncMock())
    monkeypatch.setattr(Fund.objects, "ensure_indexes", AsyncMock())
    monkeypatch.setattr(Subscription.objects, "ensure_indexes", AsyncMock())
    monkeypatch.setattr(Transaction.objects, "ensure_indexes", AsyncMock())

    from main import app

    with TestClient(app) as test_client:
        yield test_client


# ---------- Shared fixture data ----------


def make_user_doc(role: str = "USER", balance: int = 500_000, **overrides) -> dict:
    """Build a User-shaped Mongo document for tests."""
    from bson import ObjectId

    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    doc = {
        "_id": ObjectId(),
        "first_name": "Mateo",
        "last_name": "Jimenez",
        "email": "user@example.com",
        "phone": "+573223438015",
        "password_hash": "$2b$04$abc",
        "balance": balance,
        "role": role,
        "is_active": True,
        "settings": {"allow_email": True, "allow_sms": False},
        "created_at": now,
        "updated_at": now,
    }
    doc.update(overrides)
    return doc


def auth_headers(user_doc) -> dict:
    """Issue a JWT for ``user_doc`` and return the Bearer headers."""
    from core.security import create_jwt

    token = create_jwt(subject=str(user_doc["_id"]), role=user_doc["role"])
    return {"Authorization": f"Bearer {token}"}


def wire_authn(monkeypatch, user_doc) -> None:
    """Stub the auth pipeline so ``get_current_user`` returns ``user_doc``."""
    from modules.auth.manager import RevokedToken, User

    monkeypatch.setattr(User.objects, "get_by_id", AsyncMock(return_value=user_doc))
    monkeypatch.setattr(RevokedToken.objects, "is_revoked", AsyncMock(return_value=False))
