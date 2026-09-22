from __future__ import annotations

import time

from backend.services.pipeline.result import PipelineResult
from backend.services.pipeline.stages import (
    ClassifyStage,
    NormalizeStage,
    OCRStage,
    ParseStage,
    StageContext,
)


class ImportPipeline:
    """Deterministic four-stage orchestrator. No agent, no LangGraph, no retries."""

    def __init__(
        self,
        ocr: OCRStage,
        parse: ParseStage,
        normalize: NormalizeStage,
        classify: ClassifyStage,
    ) -> None:
        self.ocr = ocr
        self.parse = parse
        self.normalize = normalize
        self.classify = classify

    def run(self, ctx: StageContext, image_path: str) -> PipelineResult:
        t0 = time.monotonic()
        ocr_result = self.ocr.run(ctx, image_path)
        parsed = self.parse.run(ctx, ocr_result)
        normalized = self.normalize.run(ctx, parsed)
        classified = self.classify.run(ctx, normalized.parsed)
        return PipelineResult(
            ocr=ocr_result,
            parsed=parsed,
            normalized=normalized,
            classified=classified,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
            llm_model=ctx.llm.model_name,
        )


def build_default_pipeline() -> ImportPipeline:
    """Construct an `ImportPipeline` with the four stock stages.

    No dependency injection beyond what stages already accept via `StageContext`
    at run-time. The `get_pipeline` FastAPI dependency wraps this for the HTTP
    request path.
    """
    return ImportPipeline(OCRStage(), ParseStage(), NormalizeStage(), ClassifyStage())
