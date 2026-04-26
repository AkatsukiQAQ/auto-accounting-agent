from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_pydantic_validation_returns_400_with_field_errors(client: TestClient) -> None:
    # Missing required fields on POST /api/transactions.
    r = client.post("/api/transactions", json={"merchant": "X"})
    assert r.status_code == 400
    body = r.json()
    assert body["error"]["code"] == "validation_error"
    assert "fieldErrors" in body["error"]["meta"]
    assert isinstance(body["error"]["meta"]["fieldErrors"], list)
    assert len(body["error"]["meta"]["fieldErrors"]) > 0


def test_unhandled_exception_returns_500(app: FastAPI, client: TestClient) -> None:
    @app.get("/_boom")
    def boom():
        raise RuntimeError("intentional")

    r = client.get("/_boom")
    assert r.status_code == 500
    body = r.json()
    assert body["error"]["code"] == "internal_error"
    # No stack trace leaked
    assert "intentional" not in body["error"]["message"].lower()


def test_cors_preflight_allows_configured_origin(client: TestClient) -> None:
    r = client.options(
        "/api/health",
        headers={
            "Origin": "http://testserver",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://testserver"
