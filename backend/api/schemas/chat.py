from typing import Literal

from pydantic import ConfigDict, Field, StrictInt, field_validator

from backend.api.schemas.base import CamelModel


class MessageInput(CamelModel):
    model_config = ConfigDict(extra='forbid')
    content: str = Field(min_length=1, max_length=8000)

    @field_validator('content')
    @classmethod
    def non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('Message cannot be blank')
        return value.strip()


class SessionUpdate(CamelModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=1, max_length=80)

    @field_validator('title')
    @classmethod
    def non_blank_title(cls, value: str) -> str:
        value = ' '.join(value.split())
        if not value:
            raise ValueError('Session title cannot be blank')
        return value


class Decision(CamelModel):
    model_config = ConfigDict(extra='forbid')
    decision: Literal['apply', 'cancel']


class PlanEditOperation(CamelModel):
    model_config = ConfigDict(extra='forbid')
    category_id: str
    proposed_limit_cents: StrictInt = Field(ge=0)
    reason: str = Field(min_length=1, max_length=500)
    allow_fixed_reduction: bool = False


class PlanProposalEdit(CamelModel):
    model_config = ConfigDict(extra='forbid')
    operations: list[PlanEditOperation] = Field(min_length=1, max_length=100)
    summary: str | None = Field(default=None, min_length=1, max_length=1000)
