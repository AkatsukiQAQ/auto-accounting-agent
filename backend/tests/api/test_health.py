from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_endpoint_returns_ok(client: TestClient) -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body == {"data": {"ok": True, "version": "0.1.0"}}


def test_health_uses_config_version(client: TestClient, app) -> None:
    app.state.config = app.state.config.model_copy(update={"version": "9.9.9"})
    r = client.get("/api/health")
    assert r.json()["data"]["version"] == "9.9.9"
