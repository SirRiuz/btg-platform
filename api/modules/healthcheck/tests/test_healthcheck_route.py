# Python
from http import HTTPStatus
from unittest.mock import AsyncMock

# Libs
import pytest


@pytest.fixture
def client(monkeypatch):
    """Same plumbing as the other modules' conftests: stub Mongo lifecycle
    so the TestClient lifespan does not crash, and stub the route's DB
    probe so it returns "ok" without a real Mongo.
    """
    from fastapi.testclient import TestClient
    import integrations.mongo.client as mongo_client
    from modules.healthcheck.manager import Healthcheck

    monkeypatch.setattr(mongo_client, "connect_to_mongo", AsyncMock())
    monkeypatch.setattr(mongo_client, "close_mongo_connection", AsyncMock())
    monkeypatch.setattr(
        Healthcheck.objects, "check_db_conection", AsyncMock(return_value=True)
    )

    from main import app

    with TestClient(app) as test_client:
        yield test_client


class TestHealthcheckRoute:

    def test_healthcheck_route_status_code(self, client):
        response = client.get("/healthcheck")
        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"status": "ok", "db": "ok"}
