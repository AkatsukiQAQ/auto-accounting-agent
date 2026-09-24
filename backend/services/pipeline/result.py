from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from backend.core.schemas import ClassificationResult, OCR_Results, ParsedOcrResult

if TYPE_CHECKING:
    from backend.services.pipeline.stages import NormalizedParse


@dataclass
class PipelineResult:
    """Aggregate output of one ImportPipeline.run invocation.

    Every stage's raw output is preserved so the API layer (or future pipeline-
    visualization UI) can expose intermediates without re-running the pipeline.
    `parsed` carries the verbatim OCR merchants; `normalized.parsed` is what
    classification saw (brand-level merchant names).
    """

    ocr: OCR_Results
    parsed: ParsedOcrResult
    normalized: "NormalizedParse"
    classified: ClassificationResult
    elapsed_ms: int
    llm_model: str
