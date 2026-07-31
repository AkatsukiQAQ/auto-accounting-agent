from __future__ import annotations

from fastapi.testclient import TestClient


def _account(client: TestClient, name: str, opening: int = 0) -> dict:
    r = client.post(
        "/api/accounts",
        json={"name": name, "kind": "checking", "currency": "JPY", "openingBalanceCents": opening},
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]


def _transfer(client: TestClient, from_id: str, to_id: str, cents: int = 3_000) -> dict:
    r = client.post(
        "/api/transfers",
        json={
            "fromAccountId": from_id,
            "toAccountId": to_id,
            "amountCents": cents,
            "occurredAt": "2026-07-01T12:00:00Z",
            "note": "monthly move",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]


def test_create_transfer_camel_case_pair(client: TestClient) -> None:
    a = _account(client, "Checking", opening=10_000)
    b = _account(client, "Savings")
    data = _transfer(client, a["id"], b["id"])

    assert data["transferGroupId"].startswith("xfr_")
    assert data["outTransaction"]["type"] == "transfer_out"
    assert data["outTransaction"]["amountCents"] == -3_000
    assert data["inTransaction"]["type"] == "transfer_in"
    assert data["inTransaction"]["transferGroupId"] == data["transferGroupId"]

    assert client.get(f"/api/accounts/{a['id']}").json()["data"]["balanceCents"] == 7_000
    assert client.get(f"/api/accounts/{b['id']}").json()["data"]["balanceCents"] == 3_000


def test_transfer_legs_excluded_from_normal_type_filter(client: TestClient) -> None:
    a = _account(client, "Checking", opening=10_000)
    b = _account(client, "Savings")
    _transfer(client, a["id"], b["id"])

    r = client.get("/api/transactions?type=normal")
    assert r.json()["data"] == []
    r = client.get("/api/transactions")
    assert len(r.json()["data"]) == 2


def test_patch_single_leg_via_generic_endpoint_400(client: TestClient) -> None:
    a = _account(client, "Checking", opening=10_000)
    b = _account(client, "Savings")
    data = _transfer(client, a["id"], b["id"])

    r = client.patch(
        f"/api/transactions/{data['outTransaction']['id']}", json={"amountCents": -999}
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "transfer_leg_edit_forbidden"


def test_generic_delete_of_one_leg_removes_both(client: TestClient) -> None:
    a = _account(client, "Checking", opening=10_000)
    b = _account(client, "Savings")
    data = _transfer(client, a["id"], b["id"])

    r = client.delete(f"/api/transactions/{data['inTransaction']['id']}")
    assert r.status_code == 200
    assert client.get("/api/transactions").json()["data"] == []
    assert client.get(f"/api/accounts/{a['id']}").json()["data"]["balanceCents"] == 10_000


def test_delete_transfer_group_endpoint(client: TestClient) -> None:
    a = _account(client, "Checking", opening=10_000)
    b = _account(client, "Savings")
    data = _transfer(client, a["id"], b["id"])

    r = client.delete(f"/api/transfers/{data['transferGroupId']}")
    assert r.status_code == 200
    assert client.get("/api/transactions").json()["data"] == []

    r = client.delete(f"/api/transfers/{data['transferGroupId']}")
    assert r.status_code == 404


def test_cross_currency_transfer_400(client: TestClient) -> None:
    a = _account(client, "Checking", opening=10_000)
    r = client.post(
        "/api/accounts",
        json={"name": "BoA", "kind": "checking", "currency": "USD"},
    )
    usd = r.json()["data"]
    r = client.post(
        "/api/transfers",
        json={
            "fromAccountId": a["id"],
            "toAccountId": usd["id"],
            "amountCents": 100,
            "occurredAt": "2026-07-01T12:00:00Z",
        },
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "validation_error"
