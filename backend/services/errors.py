"""Service-layer exceptions.

These are framework-agnostic business errors. The API layer (M4) translates
them into HTTP responses via `backend/api/errors.py`. Core rule: services
raise these; routes catch these. Nothing else.
"""
from __future__ import annotations

from typing import Any


class ServiceError(Exception):
    """Base for all service-layer business errors. Carries an error code + optional metadata."""

    code: str = "service_error"

    def __init__(self, message: str, *, meta: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.meta = meta or {}


class NotFoundError(ServiceError):
    code = "not_found"


class ValidationError(ServiceError):
    code = "validation_error"


class ConflictError(ServiceError):
    code = "conflict"


class CategoryInUseError(ConflictError):
    code = "category_in_use"


class SystemCategoryError(ConflictError):
    code = "cannot_delete_system_category"
