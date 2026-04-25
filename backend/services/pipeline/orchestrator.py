from __future__ import annotations

import time

from backend.services.pipeline.result import PipelineResult
from backend.services.pipeline.stages import ClassifyStage, OCRStage, ParseStage, StageContext


class ImportPipeline:
    """Deterministic three-stage orchestrator. No agent, no LangGraph, no retries."""

    def __init__(
        self, ocr: OCRStage, parse: ParseStage, classify: ClassifyStage
    ) -> None:
        self.ocr = ocr
        self.parse = parse
        self.classify = classify

    def run(self, ctx: StageContext, image_path: str) -> PipelineResult:
        t0 = time.monotonic()
        ocr_result = self.ocr.run(ctx, image_path)
        parsed = self.parse.run(ctx, ocr_result)
        classified = self.classify.run(ctx, parsed)
        return PipelineResult(
            ocr=ocr_result,
            parsed=parsed,
            classified=classified,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
            llm_model=ctx.llm.model_name,
        )


def build_default_pipeline() -> ImportPipeline:
    """Construct an `ImportPipeline` with the three stock stages.

    No dependency injection beyond what stages already accept via `StageContext`
    at run-time. M4's `get_pipeline` FastAPI dependency wraps this for the HTTP
    request path.
    """
    return ImportPipeline(OCRStage(), ParseStage(), ClassifyStage())
