from __future__ import annotations

from fastapi.testclient import TestClient


def test_first_get_returns_defaults(client: TestClient) -> None:
    r = client.get("/api/settings")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["profile"]["timezone"] == "Asia/Tokyo"
    assert data["profile"]["defaultCurrency"] == "JPY"
    assert data["appearance"]["theme"] == "light"
    assert data["apiKeys"] == {}


def test_patch_deep_merges(client: TestClient) -> None:
    r = client.patch("/api/settings", json={"profile": {"email": "me@x.com"}})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["profile"]["email"] == "me@x.com"
    # siblings preserved
    assert data["profile"]["timezone"] == "Asia/Tokyo"


def test_patch_api_keys_accumulates(client: TestClient) -> None:
    client.patch("/api/settings", json={"apiKeys": {"openai": "sk-1"}})
    r = client.patch("/api/settings", json={"apiKeys": {"anthropic": "sk-2"}})
    assert r.json()["data"]["apiKeys"] == {"openai": "sk-1", "anthropic": "sk-2"}


def test_patch_theme_replaces(client: TestClient) -> None:
    r = client.patch("/api/settings", json={"appearance": {"theme": "dark"}})
    assert r.json()["data"]["appearance"]["theme"] == "dark"
