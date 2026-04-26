from __future__ import annotations

from fastapi.testclient import TestClient


def test_list_returns_nine_seeded_in_sort_order(client: TestClient) -> None:
    r = client.get("/api/categories")
    assert r.status_code == 200
    data = r.json()["data"]
    assert [c["id"] for c in data] == [
        "food", "transport", "shopping", "bills",
        "entertain", "health", "income", "rent", "other",
    ]
    # camelCase serialization sanity
    assert "colorBg" in data[0] and "autoAssign" in data[0]


def test_get_by_id(client: TestClient) -> None:
    r = client.get("/api/categories/food")
    assert r.status_code == 200
    c = r.json()["data"]
    assert c["id"] == "food"
    assert c["label"] == "Food"


def test_get_missing_returns_404(client: TestClient) -> None:
    r = client.get("/api/categories/nope")
    assert r.status_code == 404
    body = r.json()
    assert body["error"]["code"] == "not_found"


def test_create_happy_path(client: TestClient) -> None:
    r = client.post(
        "/api/categories",
        json={
            "id": "coffee",
            "label": "Coffee",
            "colorBg": "#AABBCC",
            "colorDot": "#112233",
            "keywords": ["starbucks"],
        },
    )
    assert r.status_code == 201
    c = r.json()["data"]
    assert c["id"] == "coffee"
    assert c["keywords"] == ["starbucks"]


def test_create_bad_slug_returns_400(client: TestClient) -> None:
    r = client.post(
        "/api/categories",
        json={"id": "BadSlug!", "label": "x", "colorBg": "#000000", "colorDot": "#ffffff"},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "validation_error"


def test_patch_updates_label(client: TestClient) -> None:
    r = client.patch("/api/categories/food", json={"label": "Groceries"})
    assert r.status_code == 200
    assert r.json()["data"]["label"] == "Groceries"


def test_delete_system_category_returns_409(client: TestClient) -> None:
    r = client.delete("/api/categories/other")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "cannot_delete_system_category"


def test_delete_unused_category_returns_200(client: TestClient) -> None:
    r = client.delete("/api/categories/bills")
    assert r.status_code == 200
    assert r.json()["data"] == {"ok": True}
    # Subsequent GET is 404
    assert client.get("/api/categories/bills").status_code == 404


def test_delete_in_use_category_returns_409_with_count(client: TestClient) -> None:
    # Create a transaction referencing "food" first.
    r = client.post(
        "/api/transactions",
        json={
            "occurredAt": "2026-04-23T10:00:00+00:00",
            "merchant": "Starbucks",
            "amountCents": -500,
            "currency": "JPY",
            "categoryId": "food",
            "source": "manual",
        },
    )
    assert r.status_code == 201

    r = client.delete("/api/categories/food")
    assert r.status_code == 409
    body = r.json()
    assert body["error"]["code"] == "category_in_use"
    assert body["error"]["meta"]["transactionCount"] == 1
