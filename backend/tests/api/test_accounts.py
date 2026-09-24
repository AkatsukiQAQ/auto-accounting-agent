from __future__ import annotations

from fastapi.testclient import TestClient

CASH_ID = "acc_cash_default"

TXN_BODY = {
    "occurredAt": "2026-07-01T12:00:00Z",
    "merchant": "Lawson",
    "amountCents": -500,
    "currency": "JPY",
    "categoryId": "food",
    "source": "manual",
}


def _create_account(client: TestClient, **overrides: object) -> dict:
    body = {"name": "BoA", "kind": "checking", "currency": "USD", "openingBalanceCents": 10_000}
    body.update(overrides)
    r = client.post("/api/accounts", json=body)
    assert r.status_code == 201, r.text
    return r.json()["data"]


def test_list_includes_default_cash(client: TestClient) -> None:
    r = client.get("/api/accounts")
    assert r.status_code == 200
    accounts = r.json()["data"]
    assert [a["id"] for a in accounts] == [CASH_ID]
    assert accounts[0]["name"] == "Cash"
    assert accounts[0]["kind"] == "cash"


def test_create_account_roundtrip_camel_case(client: TestClient) -> None:
    acc = _create_account(client)
    assert acc["id"].startswith("acc_")
    assert acc["balanceCents"] == 10_000
    assert acc["openingBalanceCents"] == 10_000
    assert acc["archived"] is False


def test_create_account_bad_kind_400(client: TestClient) -> None:
    r = client.post(
        "/api/accounts", json={"name": "X", "kind": "crypto", "currency": "USD"}
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "validation_error"


def test_patch_archive_then_writes_rejected(client: TestClient) -> None:
    acc = _create_account(client)
    r = client.patch(f"/api/accounts/{acc['id']}", json={"archived": True})
    assert r.status_code == 200
    assert r.json()["data"]["archived"] is True

    r = client.post("/api/transactions", json={**TXN_BODY, "accountId": acc["id"]})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "account_archived"


def test_delete_referenced_account_409(client: TestClient) -> None:
    acc = _create_account(client, currency="JPY")
    r = client.post("/api/transactions", json={**TXN_BODY, "accountId": acc["id"]})
    assert r.status_code == 201

    r = client.delete(f"/api/accounts/{acc['id']}")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "account_in_use"


def test_delete_default_cash_409(client: TestClient) -> None:
    r = client.delete(f"/api/accounts/{CASH_ID}")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "cannot_delete_default_account"


def test_reconcile_creates_adjustment_and_second_call_noops(client: TestClient) -> None:
    acc = _create_account(client, currency="JPY", openingBalanceCents=0)
    client.post("/api/transactions", json={**TXN_BODY, "accountId": acc["id"]})

    r = client.post(f"/api/accounts/{acc['id']}/reconcile", json={"actualBalanceCents": -300})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["account"]["balanceCents"] == -300
    assert data["adjustment"]["amountCents"] == 200
    assert data["adjustment"]["accountId"] == acc["id"]

    r = client.post(f"/api/accounts/{acc['id']}/reconcile", json={"actualBalanceCents": -300})
    assert r.status_code == 200
    assert r.json()["data"]["adjustment"] is None


def test_recompute_balance_endpoint(client: TestClient) -> None:
    acc = _create_account(client, currency="JPY", openingBalanceCents=1_000)
    client.post("/api/transactions", json={**TXN_BODY, "accountId": acc["id"]})
    r = client.post(f"/api/accounts/{acc['id']}/recompute-balance")
    assert r.status_code == 200
    assert r.json()["data"]["balanceCents"] == 500


# ─────────────── FE1-compat + ledger wiring through /api/transactions ───────────────


def test_post_transaction_without_account_lands_on_cash(client: TestClient) -> None:
    """Phase-1 clients don't send accountId — the write must not break and the
    default Cash balance must move."""
    r = client.post("/api/transactions", json=TXN_BODY)
    assert r.status_code == 201, r.text
    data = r.json()["data"]
    assert data["accountId"] == CASH_ID
    assert data["type"] == "normal"

    r = client.get(f"/api/accounts/{CASH_ID}")
    assert r.json()["data"]["balanceCents"] == -500


def test_post_transaction_transfer_type_400_use_transfers_endpoint(client: TestClient) -> None:
    r = client.post("/api/transactions", json={**TXN_BODY, "type": "transfer_out"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "use_transfers_endpoint"


def test_patch_transaction_account_moves_balances(client: TestClient) -> None:
    acc = _create_account(client, currency="JPY", openingBalanceCents=0)
    created = client.post("/api/transactions", json=TXN_BODY).json()["data"]

    r = client.patch(f"/api/transactions/{created['id']}", json={"accountId": acc["id"]})
    assert r.status_code == 200
    assert client.get(f"/api/accounts/{CASH_ID}").json()["data"]["balanceCents"] == 0
    assert client.get(f"/api/accounts/{acc['id']}").json()["data"]["balanceCents"] == -500


def test_delete_transaction_reverses_balance(client: TestClient) -> None:
    created = client.post("/api/transactions", json=TXN_BODY).json()["data"]
    client.delete(f"/api/transactions/{created['id']}")
    assert client.get(f"/api/accounts/{CASH_ID}").json()["data"]["balanceCents"] == 0


def test_list_transactions_filters_by_account_and_type(client: TestClient) -> None:
    acc = _create_account(client, currency="JPY")
    client.post("/api/transactions", json=TXN_BODY)  # cash
    client.post("/api/transactions", json={**TXN_BODY, "accountId": acc["id"], "merchant": "7-Eleven"})

    r = client.get(f"/api/transactions?account={acc['id']}")
    rows = r.json()["data"]
    assert [t["merchant"] for t in rows] == ["7-Eleven"]

    r = client.get("/api/transactions?type=normal")
    assert len(r.json()["data"]) == 2

    r = client.get("/api/transactions?type=transfer_out,transfer_in")
    assert r.json()["data"] == []
