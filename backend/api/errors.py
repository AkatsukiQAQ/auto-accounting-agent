"""HTTP exception handlers — translates service-layer errors to `{error:{...}}`."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.services.errors import (
    ApiKeyNotConfiguredError,
    ConflictError,
    NotFoundError,
    ServiceError,
    ValidationError,
)
from backend.services.pipeline import PipelineLLMError

logger = logging.getLogger(__name__)


def _error_body(code: str, message: str, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"error": {"code": code, "message": message, "meta": meta or {}}}
    return body


def _from_service(exc: ServiceError, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=_error_body(exc.code, exc.message, exc.meta),
    )


def register(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def _not_found(_req: Request, exc: NotFoundError) -> JSONResponse:
        return _from_service(exc, status.HTTP_404_NOT_FOUND)

    @app.exception_handler(ValidationError)
    async def _validation(_req: Request, exc: ValidationError) -> JSONResponse:
        return _from_service(exc, status.HTTP_400_BAD_REQUEST)

    @app.exception_handler(ConflictError)
    async def _conflict(_req: Request, exc: ConflictError) -> JSONResponse:
        # Covers CategoryInUseError + SystemCategoryError (both subclass ConflictError).
        return _from_service(exc, status.HTTP_409_CONFLICT)

    @app.exception_handler(ApiKeyNotConfiguredError)
    async def _api_key(_req: Request, exc: ApiKeyNotConfiguredError) -> JSONResponse:
        return _from_service(exc, status.HTTP_400_BAD_REQUEST)

    @app.exception_handler(PipelineLLMError)
    async def _pipeline_llm(_req: Request, exc: PipelineLLMError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=_error_body("pipeline_llm_error", str(exc)),
        )

    @app.exception_handler(RequestValidationError)
    async def _req_validation(_req: Request, exc: RequestValidationError) -> JSONResponse:
        # Pydantic 2 shape: [{loc, msg, type, input, url}, ...]
        field_errors = [
            {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]}
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_error_body(
                "validation_error",
                "request body failed validation",
                {"fieldErrors": field_errors},
            ),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_req: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body("internal_error", "internal server error"),
        )
