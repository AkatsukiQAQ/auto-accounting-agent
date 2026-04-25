from __future__ import annotations

from fastapi.testclient import TestClient

from backend.core.schemas import (
    ClassificationResult,
    OCR_Receipt,
    OCR_Results,
    ParsedOcrResult,
    ParsedReceipt,
    ReceiptClassification,
)
from backend.tests.api.conftest import FAKE_PNG_BYTES, VALID_PNG_BYTES
from backend.tests.services.fakes import FakePipelineLLM


def _configure_key(client: TestClient, key: str = "sk-fake") -> None:
    r = client.patch("/api/settings", json={"apiKeys": {"openai": key}})
    assert r.status_code == 200


def _mk_llm_responses(
    *,
    ocr_text: str = "STARBUCKS ¥725",
    merchant: str = "Steam",  # regex-matches entertain → no LLM ClassificationResult call
    currency: str | None = "JPY",
    amount: float | None = 725.0,
    date: str | None = "2026-04-23",
) -> dict:
    return {
        OCR_Results: OCR_Results(ocr_results=[OCR_Receipt(raw_text=ocr_text)]),
        ParsedOcrResult: ParsedOcrResult(
            parsed_ocr_results=[
                ParsedReceipt(
                    raw_text=ocr_text,
                    currency=currency,
                    amount=amount,
                    date=date,
                    time=None,
                    merchant=merchant,
                )
            ]
        ),
    }


def test_import_photo_without_api_key_returns_400(client: TestClient, app) -> None:
    # Remove the fake_llm override so the real get_llm runs its "no key" guard.
    from backend.api.deps import get_llm

    app.dependency_overrides.pop(get_llm, None)

    # Default settings have apiKeys={} → get_llm should raise ApiKeyNotConfiguredError.
    r = client.post(
        "/api/import/photo",
        files={"image": ("receipt.png", VALID_PNG_BYTES, "image/png")},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "api_key_not_configured"


def test_import_photo_rejects_unsupported_image(client: TestClient, fake_llm: FakePipelineLLM) -> None:
    _configure_key(client)
    fake_llm.responses.update(_mk_llm_responses())
    r = client.post(
        "/api/import/photo",
        files={"image": ("fake.png", FAKE_PNG_BYTES, "image/png")},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "unsupported_image"


def test_import_photo_rejects_non_image_content_type(client: TestClient) -> None:
    _configure_key(client)
    r = client.post(
        "/api/import/photo",
        files={"image": ("receipt.txt", b"not an image", "text/plain")},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "unsupported_image"


def test_import_photo_happy_path_regex_match(
    client: TestClient, fake_llm: FakePipelineLLM
) -> None:
    _configure_key(client)
    fake_llm.responses.update(_mk_llm_responses(merchant="Steam"))

    r = client.post(
        "/api/import/photo",
        files={"image": ("r.png", VALID_PNG_BYTES, "image/png")},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    preview = data["previewTransaction"]
    assert preview["merchant"] == "Steam"
    assert preview["currency"] == "JPY"
    assert preview["amountCents"] == -72500  # -round(725.0 * 100)
    assert preview["categoryId"] == "entertain"  # regex-matched
    assert preview["source"] == "photo"
    assert preview["raw"]["imageUrl"].startswith("/media/")
    assert data["confidence"] > 0.9  # currency+amount+date + regex-match → close to 1.0


def test_import_photo_llm_fallback_category(
    client: TestClient, fake_llm: FakePipelineLLM
) -> None:
    _configure_key(client)
    # Unknown merchant → regex misses → LLM called with ClassificationResult schema.
    responses = _mk_llm_responses(merchant="Mysterious Corp")
    responses[ClassificationResult] = ClassificationResult(
        classification_results=[
            ReceiptClassification(
                idx=0, category="other", sub_category=None, matched=False, keyword=None
            )
        ]
    )
    fake_llm.responses.update(responses)

    r = client.post(
        "/api/import/photo",
        files={"image": ("r.png", VALID_PNG_BYTES, "image/png")},
    )
    assert r.status_code == 200
    preview = r.json()["data"]["previewTransaction"]
    assert preview["categoryId"] == "other"
    # classify_c = 0.4 (unmatched fallback) → overall < 0.9
    assert r.json()["data"]["confidence"] < 0.8


def test_import_photo_empty_ocr_returns_placeholder(
    client: TestClient, fake_llm: FakePipelineLLM
) -> None:
    _configure_key(client)
    fake_llm.responses.update(
        {
            OCR_Results: OCR_Results(ocr_results=[]),
            ParsedOcrResult: ParsedOcrResult(parsed_ocr_results=[]),
        }
    )
    r = client.post(
        "/api/import/photo",
        files={"image": ("r.png", VALID_PNG_BYTES, "image/png")},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["previewTransaction"]["merchant"] == "Unknown"
    assert data["previewTransaction"]["amountCents"] == 0
    assert data["previewTransaction"]["categoryId"] == "other"
    assert data["confidence"] == 0.0


def test_e2e_import_then_commit(client: TestClient, fake_llm: FakePipelineLLM) -> None:
    _configure_key(client)
    fake_llm.responses.update(_mk_llm_responses(merchant="Steam", amount=100.0, date="2026-04-20"))

    # 1. Upload photo → get draft
    r = client.post(
        "/api/import/photo",
        files={"image": ("r.png", VALID_PNG_BYTES, "image/png")},
    )
    assert r.status_code == 200
    preview = r.json()["data"]["previewTransaction"]

    # 2. POST draft to create the transaction
    r2 = client.post("/api/transactions", json=preview)
    assert r2.status_code == 201
    created_id = r2.json()["data"]["id"]

    # 3. GET list should include it
    r3 = client.get("/api/transactions")
    ids = [t["id"] for t in r3.json()["data"]]
    assert created_id in ids
