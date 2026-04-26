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
    previews = data["previewTransactions"]
    assert len(previews) == 1
    p0 = previews[0]
    assert p0["merchant"] == "Steam"
    assert p0["currency"] == "JPY"
    assert p0["amountCents"] == -72500  # -round(725.0 * 100)
    assert p0["categoryId"] == "entertain"  # regex-matched
    assert p0["source"] == "photo"
    assert p0["raw"]["imageUrl"].startswith("/media/")
    assert len(data["confidences"]) == 1
    assert data["confidences"][0] > 0.9


def test_import_photo_multi_receipt_returns_all(
    client: TestClient, fake_llm: FakePipelineLLM
) -> None:
    """Three-receipt screenshot → three preview drafts in one response."""
    _configure_key(client)
    receipts = [
        ParsedReceipt(
            raw_text="STARBUCKS ¥725",
            currency="JPY",
            amount=725.0,
            date="2026-04-23",
            time="10:00",
            merchant="Steam",  # regex-matched entertain
        ),
        ParsedReceipt(
            raw_text="UBER EATS ¥2035",
            currency="JPY",
            amount=2035.0,
            date="2026-04-23",
            time=None,
            merchant="Uber Eats",  # regex-matched food
        ),
        ParsedReceipt(
            raw_text="UNKNOWN SHOP ¥500",
            currency="JPY",
            amount=500.0,
            date=None,  # missing date drags parse_c down
            time=None,
            merchant="Unknown Shop",  # regex miss → LLM
        ),
    ]
    fake_llm.responses.update(
        {
            OCR_Results: OCR_Results(
                ocr_results=[OCR_Receipt(raw_text=r.raw_text) for r in receipts]
            ),
            ParsedOcrResult: ParsedOcrResult(parsed_ocr_results=receipts),
            ClassificationResult: ClassificationResult(
                classification_results=[
                    # idx 2 is the unmatched-by-regex one; we provide an LLM verdict.
                    ReceiptClassification(
                        idx=2, category="other", sub_category=None,
                        matched=False, keyword=None,
                    )
                ]
            ),
        }
    )

    r = client.post(
        "/api/import/photo",
        files={"image": ("r.png", VALID_PNG_BYTES, "image/png")},
    )
    assert r.status_code == 200
    data = r.json()["data"]

    previews = data["previewTransactions"]
    assert len(previews) == 3
    assert [p["merchant"] for p in previews] == ["Steam", "Uber Eats", "Unknown Shop"]
    assert [p["categoryId"] for p in previews] == ["entertain", "food", "other"]
    assert [p["amountCents"] for p in previews] == [-72500, -203500, -50000]

    confidences = data["confidences"]
    assert len(confidences) == 3
    # First two have full parse + regex match → high; third has no date + LLM-fallback → lower.
    assert confidences[0] > 0.9
    assert confidences[1] > 0.9
    assert confidences[2] < 0.7

    # OCR text concatenates all receipts.
    assert "STARBUCKS" in data["ocrText"] and "UBER" in data["ocrText"] and "UNKNOWN" in data["ocrText"]


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
    data = r.json()["data"]
    assert data["previewTransactions"][0]["categoryId"] == "other"
    # classify_c = 0.4 (unmatched fallback) → overall < 0.9
    assert data["confidences"][0] < 0.8


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
    previews = data["previewTransactions"]
    assert len(previews) == 1  # one placeholder draft
    assert previews[0]["merchant"] == "Unknown"
    assert previews[0]["amountCents"] == 0
    assert previews[0]["categoryId"] == "other"
    assert data["confidences"] == [0.0]


def test_e2e_import_then_commit(client: TestClient, fake_llm: FakePipelineLLM) -> None:
    _configure_key(client)
    fake_llm.responses.update(_mk_llm_responses(merchant="Steam", amount=100.0, date="2026-04-20"))

    # 1. Upload photo → get drafts (single receipt in this fixture).
    r = client.post(
        "/api/import/photo",
        files={"image": ("r.png", VALID_PNG_BYTES, "image/png")},
    )
    assert r.status_code == 200
    preview = r.json()["data"]["previewTransactions"][0]

    # 2. POST draft to create the transaction
    r2 = client.post("/api/transactions", json=preview)
    assert r2.status_code == 201
    created_id = r2.json()["data"]["id"]

    # 3. GET list should include it
    r3 = client.get("/api/transactions")
    ids = [t["id"] for t in r3.json()["data"]]
    assert created_id in ids
