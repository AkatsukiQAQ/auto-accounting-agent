from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class CamelModel(BaseModel):
    """Base for every request/response DTO.

    Inputs accept both snake_case (Python) and camelCase (HTTP);
    outputs serialize camelCase via `model_dump(by_alias=True)` or FastAPI's
    auto-serialization when the DTO is declared as `response_model`.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,  # lets `model_validate(orm_row)` work
    )


class Data(CamelModel, Generic[T]):
    """Successful response envelope: `{"data": T}`."""

    data: T


class ErrorBody(CamelModel):
    code: str
    message: str
    meta: dict[str, Any] = Field(default_factory=dict)


class Error(CamelModel):
    """Failure response envelope: `{"error": {"code", "message", "meta"}}`."""

    error: ErrorBody


class OkOut(CamelModel):
    """Trivial payload for endpoints that return only success (e.g. DELETE)."""

    ok: bool = True
