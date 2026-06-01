from fastapi.testclient import TestClient

from app.api.app import app


def test_health_ok():
    with TestClient(app) as client:
        resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
