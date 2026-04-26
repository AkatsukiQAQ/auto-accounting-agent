from __future__ import annotations

from dataclasses import dataclass

from backend.core.schemas import ClassificationResult, OCR_Results, ParsedOcrResult


@dataclass
class PipelineResult:
    """Aggregate output of one ImportPipeline.run invocation.

    Every stage's raw output is preserved so the API layer (or future pipeline-
    visualization UI) can expose intermediates without re-running the pipeline.
    """

    ocr: OCR_Results
    parsed: ParsedOcrResult
    classified: ClassificationResult
    elapsed_ms: int
    llm_model: str
