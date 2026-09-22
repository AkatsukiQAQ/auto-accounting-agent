"""Pipeline stages — one class per stage, composed by `ImportPipeline`.

Each stage is a thin wrapper around `backend.core/` functions. The LLM is
injected via `StageContext`, which also carries the DB session (needed by
ClassifyStage to load the user-editable category set) and the per-request
`PipelineConfig`.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.classifier import _compile_regex_pattern, regex_classify_batch
from backend.core.currency import normalize_text
from backend.core.prompts import (
    render_classify_prompt,
    render_ocr_prompt,
    render_parser_prompt,
)
from backend.core.schemas import (
    Category as CoreCategory,
    ClassificationResult,
    OCR_Receipt,
    OCR_Results,
    ParsedOcrResult,
)
from backend.db.models import Category as DbCategory
from backend.services.normalization import NormalizationOutcome, normalize
from backend.services.pipeline.config import PipelineConfig
from backend.services.pipeline.llm import PipelineLLM


@dataclass
class StageContext:
    llm: PipelineLLM
    session: Session
    config: PipelineConfig


class OCRStage:
    """Image → OCR_Results. Passes the image path through to the LLM unchanged."""

    def run(self, ctx: StageContext, image_path: str) -> OCR_Results:
        prompt = render_ocr_prompt()
        return ctx.llm.complete_structured(prompt, OCR_Results, images=[image_path])


class ParseStage:
    """OCR_Results → ParsedOcrResult. Normalizes text, filters rejected currencies."""

    def run(self, ctx: StageContext, ocr: OCR_Results) -> ParsedOcrResult:
        accepted = ctx.config.accepted_currencies
        normalized_receipts = [
            OCR_Receipt(raw_text=normalize_text(r.raw_text)) for r in ocr.ocr_results
        ]
        prompt = render_parser_prompt(normalized_receipts, list(accepted))
        raw = ctx.llm.complete_structured(prompt, ParsedOcrResult)
        kept = [
            r
            for r in raw.parsed_ocr_results
            if r.currency is None or r.currency in accepted
        ]
        return ParsedOcrResult(parsed_ocr_results=kept)


@dataclass
class NormalizedParse:
    """NormalizeStage output: receipts with brand-level merchant names, plus the
    per-receipt outcomes (parallel list; None where a receipt had no merchant)."""

    parsed: ParsedOcrResult
    outcomes: list[NormalizationOutcome | None]


class NormalizeStage:
    """ParsedOcrResult → NormalizedParse. Runs between Parse and Classify so the
    classifier (and Phase-3 learned rules) see ONE identity per brand — the
    verbatim OCR string survives in PipelineResult.parsed / merchant_raw."""

    def run(self, ctx: StageContext, parsed: ParsedOcrResult) -> NormalizedParse:
        receipts = []
        outcomes: list[NormalizationOutcome | None] = []
        for receipt in parsed.parsed_ocr_results:
            if receipt.merchant:
                outcome = normalize(ctx.session, receipt.merchant, count_alias_hits=True)
                outcomes.append(outcome)
                receipts.append(receipt.model_copy(update={"merchant": outcome.normalized}))
            else:
                outcomes.append(None)
                receipts.append(receipt)
        return NormalizedParse(
            parsed=ParsedOcrResult(parsed_ocr_results=receipts), outcomes=outcomes
        )


class ClassifyStage:
    """ParsedOcrResult → ClassificationResult. Regex first, LLM fallback for the rest.

    Phase 1 simplification: DB categories are flat (no sub_categories column),
    so the subcategory LLM branch is wired as an assertion rather than a code
    path. Phase 2 restores it when sub_categories come back.
    """

    def run(self, ctx: StageContext, parsed: ParsedOcrResult) -> ClassificationResult:
        categories = _hydrate_categories_from_db(ctx.session)
        idx_merchants: list[tuple[int, str]] = [
            (i, r.merchant or "") for i, r in enumerate(parsed.parsed_ocr_results)
        ]
        buckets = regex_classify_batch(idx_merchants, categories)

        if buckets.needs_subcategory_llm:
            # Invariant: Phase 1 DB schema has no sub_categories, so this bucket
            # should never populate. If it does, someone added sub_categories
            # without wiring the subclassify prompt — fail loud.
            raise RuntimeError(
                "subcategory LLM fallback is not wired in Phase 1; "
                "Category DB rows should not declare sub_categories yet"
            )

        classifications = list(buckets.matched)
        pending = list(buckets.needs_top_category_llm)
        if pending:
            prompt = render_classify_prompt(categories, pending)
            llm_result = ctx.llm.complete_structured(prompt, ClassificationResult)
            classifications.extend(llm_result.classification_results)

        classifications.sort(key=lambda c: c.idx)
        return ClassificationResult(classification_results=classifications)


def _hydrate_categories_from_db(session: Session) -> list[CoreCategory]:
    """Materialize DB category rows as core.schemas.Category with compiled regex.

    `Category.name` intentionally carries the slug (e.g. "food"), not the human
    label ("Food"). The slug is what flows through classification results and
    becomes `categoryId` on transactions — keeping one string end-to-end avoids
    a mapping round-trip.

    Only `auto_assign=True` rows participate: system categories like `transfer`
    exist for ledger bookkeeping and must never be offered to the classifier.
    """
    rows = session.scalars(
        select(DbCategory)
        .where(DbCategory.auto_assign.is_(True))
        .order_by(DbCategory.sort_order)
    ).all()
    return [
        CoreCategory(
            name=row.id,
            keywords=list(row.keywords),
            sub_categories=None,
            regex=_compile_regex_pattern(list(row.keywords)),
        )
        for row in rows
    ]
