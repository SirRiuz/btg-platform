# Python
import os
from unittest.mock import AsyncMock

# Libs
import pytest

# Ensure env vars exist before importing `main` / `core.settings`.
os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DB_NAME", "soptest_test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-do-not-use-in-prod")
os.environ.setdefault("BCRYPT_ROUNDS", "4")


@pytest.fixture
def client(monkeypatch):
    """TestClient with Mongo connection + index creation mocked out.

    The accounts tests follow the same pattern as the auth tests: the
    FastAPI lifespan still runs, but every Mongo touchpoint is stubbed.
    Individual tests monkeypatch the relevant ``Account.objects`` /
    ``User.objects`` / ``RevokedToken.objects`` methods directly.
    """
    from fastapi.testclient import TestClient
    import integrations.mongo.client as mongo_client
    from modules.auth.manager import RevokedToken, User

    monkeypatch.setattr(mongo_client, "connect_to_mongo", AsyncMock())
    monkeypatch.setattr(mongo_client, "close_mongo_connection", AsyncMock())
    monkeypatch.setattr(User.objects, "ensure_indexes", AsyncMock())
    monkeypatch.setattr(RevokedToken.objects, "ensure_indexes", AsyncMock())

    from main import app

    with TestClient(app) as test_client:
        yield test_client
