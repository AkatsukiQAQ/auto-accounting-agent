"""LLM abstraction used by pipeline stages.

Only three things leave this module:
- `PipelineLLM` — the structural Protocol that stages depend on.
- `OpenAIPipelineLLM` — the production impl wrapping the stock `openai` SDK
  (explicitly *not* LangChain; Phase 1 drops that dependency at M6).
- `PipelineLLMError` — raised on any OpenAI client failure so the API layer
  can translate it into a 502 response uniformly.
"""
from __future__ import annotations

from typing import Any, Protocol, TypeVar

from openai import OpenAI
from pydantic import BaseModel

from backend.core.image_utils import image_to_data_url

T = TypeVar("T", bound=BaseModel)


class PipelineLLMError(Exception):
    """Raised when the underlying LLM call fails or returns no parsed content."""


class PipelineLLM(Protocol):
    @property
    def model_name(self) -> str: ...

    def complete_structured(
        self,
        prompt: str,
        schema: type[T],
        images: list[str] | None = None,
    ) -> T: ...


class OpenAIPipelineLLM:
    """Concrete `PipelineLLM` that calls `openai` >= 2.x directly.

    Uses `client.chat.completions.parse` for Pydantic-structured output. Image
    inputs (local file paths) are encoded as `data:` URLs on the fly — callers
    never need to know about base64. `temperature` is only forwarded when
    explicitly set at construction (GPT-5 family rejects custom temperatures).
    """

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "gpt-5-nano",
        temperature: float | None = None,
        client: OpenAI | None = None,
    ) -> None:
        self._client = client or OpenAI(api_key=api_key)
        self._model = model
        self._temperature = temperature

    @property
    def model_name(self) -> str:
        return self._model

    def complete_structured(
        self,
        prompt: str,
        schema: type[T],
        images: list[str] | None = None,
    ) -> T:
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for path in images or []:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": image_to_data_url(path)},
                }
            )

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": "user", "content": content}],
            "response_format": schema,
        }
        if self._temperature is not None:
            kwargs["temperature"] = self._temperature

        try:
            completion = self._client.chat.completions.parse(**kwargs)
        except Exception as exc:  # openai raises APIError / APIConnectionError / etc.
            raise PipelineLLMError(f"{schema.__name__} completion failed: {exc}") from exc

        parsed = completion.choices[0].message.parsed
        if parsed is None:
            refusal = getattr(completion.choices[0].message, "refusal", None)
            raise PipelineLLMError(
                f"{schema.__name__} completion returned no parsed content"
                + (f" (refusal: {refusal})" if refusal else "")
            )
        return parsed
