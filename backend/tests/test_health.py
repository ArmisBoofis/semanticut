from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


def test_health_returns_200_when_database_ok():
    from app.main import app

    with patch("app.main.check_db_connection", new_callable=AsyncMock, return_value=True):
        with TestClient(app) as client:
            r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_when_database_down():
    from app.main import app

    with patch("app.main.check_db_connection", new_callable=AsyncMock, return_value=False):
        with TestClient(app) as client:
            r = client.get("/health")
    assert r.status_code == 503
    assert r.json()["status"] == "unavailable"
    assert r.json()["database"] == "error"
