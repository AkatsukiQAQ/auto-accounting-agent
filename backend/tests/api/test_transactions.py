from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

UTC = timezone.utc


def _mk_body(
    *,
    when: datetime | None = None,
    merchant: str = "M",
    amount_cents: int = -500,
    currency: str = "JPY",
    category_id: str = "food",
    source: str = "manual",
    note: str | None = None,
) -> dict:
    when = when or datetime(2026, 4, 23, 12, tzinfo=UTC)
    body = {
        "occurredAt": when.isoformat(),
        "merchant": merchant,
        "amountCents": amount_cents,
        "currency": currency,
        "categoryId": category_id,
        "source": source,
    }
    if note is not None:
        body["note"] = note
    return body


def test_create_returns_201_with_camelcase(client: TestClient) -> None:
    r = client.post("/api/transactions", json=_mk_body(merchant="Starbucks"))
    assert r.status_code == 201
    t = r.json()["data"]
    assert t["id"].startswith("txn_")
    assert t["merchant"] == "Starbucks"
    assert t["amountCents"] == -500
    assert t["categoryId"] == "food"
    assert "occurredAt" in t and "createdAt" in t


def test_create_bad_currency_returns_400(client: TestClient) -> None:
    r = client.post("/api/transactions", json=_mk_body(currency="usd"))
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "validation_error"


def test_create_unknown_category_returns_400(client: TestClient) -> None:
    r = client.post("/api/transactions", json=_mk_body(category_id="mystery"))
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "validation_error"


def test_list_empty(client: TestClient) -> None:
    r = client.get("/api/transactions")
    assert r.status_code == 200
    body = r.json()
    assert body == {"data": [], "nextCursor": None}


def test_list_returns_created(client: TestClient) -> None:
    for m in ("A", "B", "C"):
        client.post("/api/transactions", json=_mk_body(merchant=m))
    r = client.get("/api/transactions")
    assert r.status_code == 200
    assert len(r.json()["data"]) == 3


def test_list_filters_by_category(client: TestClient) -> None:
    client.post("/api/transactions", json=_mk_body(category_id="food", merchant="A"))
    client.post("/api/transactions", json=_mk_body(category_id="transport", merchant="B"))
    r = client.get("/api/transactions?category=transport")
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data) == 1
    assert data[0]["merchant"] == "B"


def test_list_filters_by_search(client: TestClient) -> None:
    client.post("/api/transactions", json=_mk_body(merchant="Starbucks Shibuya"))
    client.post("/api/transactions", json=_mk_body(merchant="Family Mart"))
    r = client.get("/api/transactions?q=starbucks")
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data) == 1 and "Starbucks" in data[0]["merchant"]


def test_list_filters_by_date_range(client: TestClient) -> None:
    client.post("/api/transactions", json=_mk_body(when=datetime(2026, 1, 1, tzinfo=UTC)))
    client.post("/api/transactions", json=_mk_body(when=datetime(2026, 3, 15, tzinfo=UTC)))
    client.post("/api/transactions", json=_mk_body(when=datetime(2026, 5, 1, tzinfo=UTC)))
    r = client.get("/api/transactions?from=2026-02-01T00:00:00%2B00:00&to=2026-04-30T00:00:00%2B00:00")
    assert r.status_code == 200
    assert len(r.json()["data"]) == 1


def test_list_cursor_paginates(client: TestClient) -> None:
    base = datetime(2026, 4, 23, 12, tzinfo=UTC)
    for i in range(5):
        client.post(
            "/api/transactions",
            json=_mk_body(when=base - timedelta(hours=i), merchant=f"m{i}"),
        )

    r1 = client.get("/api/transactions?limit=2")
    assert r1.status_code == 200
    body1 = r1.json()
    assert len(body1["data"]) == 2
    assert body1["nextCursor"]

    r2 = client.get(f"/api/transactions?limit=2&cursor={body1['nextCursor']}")
    body2 = r2.json()
    assert len(body2["data"]) == 2
    # no overlap
    assert {t["id"] for t in body1["data"]} & {t["id"] for t in body2["data"]} == set()


def test_get_by_id(client: TestClient) -> None:
    created = client.post("/api/transactions", json=_mk_body()).json()["data"]
    r = client.get(f"/api/transactions/{created['id']}")
    assert r.status_code == 200
    assert r.json()["data"]["id"] == created["id"]


def test_get_missing_returns_404(client: TestClient) -> None:
    r = client.get("/api/transactions/txn_nope")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_patch_updates_fields(client: TestClient) -> None:
    created = client.post("/api/transactions", json=_mk_body(merchant="Old")).json()["data"]
    r = client.patch(f"/api/transactions/{created['id']}", json={"merchant": "New", "note": "hi"})
    assert r.status_code == 200
    t = r.json()["data"]
    assert t["merchant"] == "New"
    assert t["note"] == "hi"


def test_patch_invalid_cursor_query_returns_400(client: TestClient) -> None:
    r = client.get("/api/transactions?cursor=%21%21%21not-base64")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "validation_error"


def test_delete_removes(client: TestClient) -> None:
    created = client.post("/api/transactions", json=_mk_body()).json()["data"]
    r = client.delete(f"/api/transactions/{created['id']}")
    assert r.status_code == 200
    assert client.get(f"/api/transactions/{created['id']}").status_code == 404
