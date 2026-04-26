from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from backend.core.schemas import (
    ClassificationResult,
    OCR_Receipt,
    OCR_Results,
    ParsedOcrResult,
    ParsedReceipt,
    ReceiptClassification,
)
from backend.services.pipeline.config import PipelineConfig, load_default_pipeline_config
from backend.services.pipeline.orchestrator import ImportPipeline, build_default_pipeline
from backend.services.pipeline.stages import (
    ClassifyStage,
    OCRStage,
    ParseStage,
    _hydrate_categories_from_db,
)
from backend.tests.services.fakes import FakePipelineLLM


# ────────────────────────── config ──────────────────────────


def test_pipeline_config_loads_from_yaml() -> None:
    cfg = load_default_pipeline_config()
    assert "USD" in cfg.accepted_currencies
    assert "JPY" in cfg.accepted_currencies
    assert cfg.symbol_defaults.get("¥") == "CNY"
    assert cfg.symbol_defaults.get("$") == "USD"


# ────────────────────── orchestrator wiring ─────────────────


def test_build_default_pipeline_wires_three_stages() -> None:
    p = build_default_pipeline()
    assert isinstance(p, ImportPipeline)
    assert isinstance(p.ocr, OCRStage)
    assert isinstance(p.parse, ParseStage)
    assert isinstance(p.classify, ClassifyStage)


# ────────────────────── fake infrastructure ─────────────────


def test_fake_llm_raises_on_unexpected_schema() -> None:
    llm = FakePipelineLLM(responses={})
    with pytest.raises(AssertionError, match="unexpected schema"):
        llm.complete_structured("prompt", OCR_Results)


def test_fake_llm_records_prompt_and_images() -> None:
    ocr = OCR_Results(ocr_results=[OCR_Receipt(raw_text="hello")])
    llm = FakePipelineLLM(responses={OCR_Results: ocr})
    out = llm.complete_structured("the-prompt", OCR_Results, images=["/tmp/foo.jpg"])
    assert out is ocr
    assert len(llm.calls) == 1
    assert llm.calls[0].prompt == "the-prompt"
    assert llm.calls[0].images == ("/tmp/foo.jpg",)


# ────────────────────────── OCRStage ────────────────────────


def test_ocr_stage_forwards_image_path_to_llm(make_ctx) -> None:
    ocr = OCR_Results(ocr_results=[OCR_Receipt(raw_text="STARBUCKS ¥725")])
    llm = FakePipelineLLM(responses={OCR_Results: ocr})
    ctx = make_ctx(llm)

    result = OCRStage().run(ctx, "/absolute/path/receipt.jpg")

    assert result is ocr
    calls = llm.calls_for(OCR_Results)
    assert len(calls) == 1
    assert calls[0].images == ("/absolute/path/receipt.jpg",)


# ───────────────────────── ParseStage ───────────────────────


def _parsed(currency: str | None, merchant: str = "M") -> ParsedReceipt:
    return ParsedReceipt(
        raw_text="x", currency=currency, amount=100.0, date=None, time=None, merchant=merchant
    )


def test_parse_stage_drops_unaccepted_currencies(make_ctx) -> None:
    raw = ParsedOcrResult(
        parsed_ocr_results=[
            _parsed("USD", "a"),
            _parsed("GBP", "b"),  # GBP not in accepted {USD, JPY, EUR}
            _parsed("JPY", "c"),
        ]
    )
    llm = FakePipelineLLM(responses={ParsedOcrResult: raw})
    ctx = make_ctx(llm)

    out = ParseStage().run(ctx, OCR_Results(ocr_results=[OCR_Receipt(raw_text="")]))
    assert [r.currency for r in out.parsed_ocr_results] == ["USD", "JPY"]


def test_parse_stage_keeps_none_currency(make_ctx) -> None:
    raw = ParsedOcrResult(
        parsed_ocr_results=[_parsed(None, "undetected"), _parsed("USD", "known")]
    )
    llm = FakePipelineLLM(responses={ParsedOcrResult: raw})
    ctx = make_ctx(llm)

    out = ParseStage().run(ctx, OCR_Results(ocr_results=[OCR_Receipt(raw_text="")]))
    assert [r.currency for r in out.parsed_ocr_results] == [None, "USD"]


def test_parse_stage_prompt_contains_accepted_currency_list(make_ctx) -> None:
    raw = ParsedOcrResult(parsed_ocr_results=[])
    llm = FakePipelineLLM(responses={ParsedOcrResult: raw})
    ctx = make_ctx(llm)

    ParseStage().run(ctx, OCR_Results(ocr_results=[OCR_Receipt(raw_text="mixed  whitespace\r\n")]))

    [call] = llm.calls_for(ParsedOcrResult)
    assert "USD" in call.prompt and "JPY" in call.prompt and "EUR" in call.prompt
    # Normalized text collapses whitespace / CRLF — look for the cleaned form.
    assert "mixed whitespace" in call.prompt


# ──────────────────────── hydrate helper ────────────────────


def test_hydrate_categories_returns_seeded_rows_in_sort_order(session: Session) -> None:
    cats = _hydrate_categories_from_db(session)
    slugs = [c.name for c in cats]
    assert slugs == [
        "food",
        "transport",
        "shopping",
        "bills",
        "entertain",
        "health",
        "income",
        "rent",
        "other",
    ]


def test_hydrate_empty_keyword_slugs_have_none_regex(session: Session) -> None:
    cats = {c.name: c for c in _hydrate_categories_from_db(session)}
    # bills/income/rent seeded with no keywords → regex stays None.
    assert cats["bills"].regex is None
    assert cats["income"].regex is None
    assert cats["rent"].regex is None
    # food has many keywords → regex compiled.
    assert cats["food"].regex is not None


# ──────────────────────── ClassifyStage ─────────────────────


def test_classify_skips_llm_when_all_regex_match(make_ctx) -> None:
    parsed = ParsedOcrResult(
        parsed_ocr_results=[
            _parsed("JPY", "Steam"),  # entertain keyword
            _parsed("JPY", "セブンイレブン"),  # food keyword
        ]
    )
    # Intentionally no ClassificationResult fake — any call would raise.
    llm = FakePipelineLLM(responses={})
    ctx = make_ctx(llm)

    out = ClassifyStage().run(ctx, parsed)
    assert llm.calls_for(ClassificationResult) == []
    cats = [c.category for c in out.classification_results]
    assert "entertain" in cats and "food" in cats


def test_classify_calls_llm_only_for_unmatched(make_ctx) -> None:
    parsed = ParsedOcrResult(
        parsed_ocr_results=[
            _parsed("JPY", "Steam"),  # regex → entertain
            _parsed("USD", "Unknown Corp"),  # regex miss → LLM
        ]
    )
    llm_classification = ClassificationResult(
        classification_results=[
            ReceiptClassification(
                idx=1, category="other", sub_category=None, matched=False, keyword=None
            )
        ]
    )
    llm = FakePipelineLLM(responses={ClassificationResult: llm_classification})
    ctx = make_ctx(llm)

    out = ClassifyStage().run(ctx, parsed)

    calls = llm.calls_for(ClassificationResult)
    assert len(calls) == 1
    # The prompt only pends the regex-missed merchant, not the matched one.
    assert "Unknown Corp" in calls[0].prompt
    assert "Steam" not in calls[0].prompt


def test_classify_preserves_matched_false_without_rewriting(make_ctx) -> None:
    """Stage must return the LLM's verdict verbatim; 'other' fallback is the route layer's job."""
    parsed = ParsedOcrResult(parsed_ocr_results=[_parsed("USD", "Mystery")])
    llm_out = ClassificationResult(
        classification_results=[
            ReceiptClassification(
                idx=0, category="other", sub_category=None, matched=False, keyword=None
            )
        ]
    )
    llm = FakePipelineLLM(responses={ClassificationResult: llm_out})
    ctx = make_ctx(llm)

    out = ClassifyStage().run(ctx, parsed)
    assert out.classification_results[0].matched is False
    assert out.classification_results[0].category == "other"


def test_classify_sorts_results_by_idx(make_ctx) -> None:
    """Regex-matched items (idx 0) and LLM-matched items (idx 1, 2) must merge in order."""
    parsed = ParsedOcrResult(
        parsed_ocr_results=[
            _parsed("JPY", "Steam"),  # idx 0, regex
            _parsed("JPY", "UnknownA"),  # idx 1, LLM
            _parsed("JPY", "UnknownB"),  # idx 2, LLM
        ]
    )
    llm_out = ClassificationResult(
        classification_results=[
            ReceiptClassification(
                idx=2, category="other", sub_category=None, matched=False, keyword=None
            ),
            ReceiptClassification(
                idx=1, category="shopping", sub_category=None, matched=True, keyword="UnknownA"
            ),
        ]
    )
    llm = FakePipelineLLM(responses={ClassificationResult: llm_out})
    ctx = make_ctx(llm)

    out = ClassifyStage().run(ctx, parsed)
    assert [c.idx for c in out.classification_results] == [0, 1, 2]


# ─────────────────────────── end-to-end ─────────────────────


def test_pipeline_end_to_end_returns_complete_result(make_ctx) -> None:
    ocr = OCR_Results(ocr_results=[OCR_Receipt(raw_text="STARBUCKS ¥725")])
    parsed = ParsedOcrResult(
        parsed_ocr_results=[
            ParsedReceipt(
                raw_text="STARBUCKS ¥725",
                currency="JPY",
                amount=725.0,
                date=None,
                time=None,
                merchant="Steam",  # deliberately a regex match so no ClassificationResult needed
            )
        ]
    )
    llm = FakePipelineLLM(
        responses={OCR_Results: ocr, ParsedOcrResult: parsed}, model_name="fake-e2e"
    )
    ctx = make_ctx(llm)

    result = build_default_pipeline().run(ctx, "/fixtures/fake.jpg")

    assert result.ocr is ocr
    # ParseStage rebuilds the container after filtering — compare by value.
    assert result.parsed == parsed
    assert len(result.classified.classification_results) == 1
    assert result.classified.classification_results[0].category == "entertain"
    assert result.elapsed_ms >= 0
    assert result.llm_model == "fake-e2e"


def test_pipeline_call_order_is_ocr_then_parse_then_classify(make_ctx) -> None:
    llm = FakePipelineLLM(
        responses={
            OCR_Results: OCR_Results(ocr_results=[OCR_Receipt(raw_text="x")]),
            ParsedOcrResult: ParsedOcrResult(
                parsed_ocr_results=[_parsed("USD", "Steam")]
            ),
        }
    )
    ctx = make_ctx(llm)
    build_default_pipeline().run(ctx, "/fixtures/any.jpg")

    schemas_called = [c.schema for c in llm.calls]
    # Classify short-circuits (Steam regex-matches), so only OCR + Parse reach the LLM.
    assert schemas_called == [OCR_Results, ParsedOcrResult]
