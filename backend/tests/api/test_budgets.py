def test_budget_vertical_slice(client):
    body = {"periodType":"month", "startsOn":"2026-01-01", "currency":"JPY", "plannedIncomeCents":30000000}
    res = client.post('/api/budget-plans', json=body)
    assert res.status_code == 201, res.text
    p = res.json()['data']
    assert p['endsOn'] == '2026-01-31'
    assert client.post('/api/budget-plans', json=body).status_code == 409
    item = client.post(f"/api/budget-plans/{p['id']}/items", json={"categoryId":"food","limitCents":200000}).json()['data']
    quick = client.post('/api/transactions/quick', json={"categoryId":"food","amountCents":120000,"currency":"JPY","occurredOn":"2026-01-10"})
    assert quick.status_code == 201, quick.text
    assert quick.json()['data']['merchant'] is None
    assert quick.json()['data']['granularity'] == 'quick'
    adjustment = client.post('/api/budget-spend/set-total', json={"planId":p['id'],"categoryId":"food","totalCents":85000})
    assert adjustment.status_code == 200, adjustment.text
    assert adjustment.json()['data']['amountCents'] == 35000
    summary = client.get(f"/api/budget-plans/{p['id']}/summary").json()['data']
    assert summary['actualSpendCents'] == 85000
    assert summary['plannedSpendCents'] == 200000
    assert client.get('/api/budget-summary/current?periodType=month&onDate=2026-01-10').json()['data']['planId'] == p['id']
    clone = client.post(f"/api/budget-plans/{p['id']}/clone", json={"startsOn":"2026-02-01"})
    assert clone.status_code == 201, clone.text
    assert len(clone.json()['data']['items']) == 1
    assert client.patch(f"/api/budget-items/{item['id']}", json={"kind":"fixed","warningRatio":0.9}).status_code == 200
    assert client.patch(f"/api/budget-plans/{p['id']}", json={"plannedIncomeCents":None}).status_code == 200
    assert client.delete(f"/api/budget-items/{item['id']}").status_code == 200
    assert client.delete(f"/api/budget-plans/{p['id']}").status_code == 200
    assert client.get(f"/api/budget-plans/{p['id']}").status_code == 404
    assert client.get('/api/transactions').status_code == 200


def test_budget_validation(client):
    assert client.get('/api/budget-summary/current?periodType=year').status_code == 400
    assert client.get('/api/budget-summary/current?onDate=2099-01-01').json()['data'] is None
    for amount in [-1, 1.5, True]:
        res = client.post('/api/budget-plans', json={"periodType":"month","startsOn":"2026-01-01","currency":"JPY","plannedIncomeCents":amount})
        assert res.status_code == 400, res.text


def test_current_summary_respects_requested_as_of_date(client):
    p = client.post('/api/budget-plans', json={"periodType":"month", "startsOn":"2026-01-01", "currency":"JPY"}).json()['data']
    transaction = client.post('/api/transactions', json={"occurredAt":"2026-01-20T12:00:00Z", "merchant":"Shop", "amountCents":-100,
        "currency":"JPY", "categoryId":"food", "source":"manual"})
    assert transaction.status_code == 201
    summary = client.get('/api/budget-summary/current?periodType=month&onDate=2026-01-10').json()['data']
    assert summary['planId'] == p['id']
    assert summary['actualSpendCents'] == 0


def test_receipt_import_contributes_to_budget(client, fake_llm):
    from backend.tests.api.test_imports import _mk_llm_responses
    from backend.tests.api.conftest import VALID_PNG_BYTES
    fake_llm.responses.update(_mk_llm_responses())
    p = client.post('/api/budget-plans', json={"periodType":"month", "startsOn":"2026-04-01", "currency":"JPY"}).json()['data']
    preview = client.post('/api/import/photo', files={'image': ('receipt.png', VALID_PNG_BYTES, 'image/png')})
    assert preview.status_code == 200, preview.text
    draft = preview.json()['data']['previewTransactions'][0]
    assert client.post('/api/transactions', json=draft).status_code == 201
    summary = client.get(f"/api/budget-plans/{p['id']}/summary").json()['data']
    assert summary['actualSpendCents'] == 72500


def test_offset_transaction_boundary(client):
    p = client.post('/api/budget-plans', json={"periodType":"month", "startsOn":"2026-01-01", "currency":"JPY"}).json()['data']
    response = client.post('/api/transactions', json={"occurredAt":"2026-01-31T23:59:00+09:00", "merchant":"Shop", "amountCents":-100,
        "currency":"JPY", "categoryId":"food", "source":"manual"})
    assert response.status_code == 201
    assert response.json()['data']['occurredAt'] == '2026-01-31T14:59:00Z'
    assert client.get(f"/api/budget-plans/{p['id']}/summary").json()['data']['actualSpendCents'] == 100
