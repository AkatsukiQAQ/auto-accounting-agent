from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel


@dataclass
class _Call:
    schema: type[BaseModel]
    prompt: str
    images: tuple[str, ...]


@dataclass
class FakePipelineLLM:
    """Dict-of-responses stand-in for `PipelineLLM`.

    Keyed by Pydantic schema class → canned instance. Records every call so
    tests can assert on invocation order, image plumbing, or non-invocation
    (e.g. ClassifyStage skipping the LLM when all merchants regex-match).
    Raises on an unregistered schema so tests fail loud instead of silently
    returning a placeholder.
    """

    responses: dict[type[BaseModel], BaseModel]
    model_name: str = "fake-model"
    calls: list[_Call] = field(default_factory=list)

    def complete_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        images: list[str] | None = None,
    ) -> BaseModel:
        self.calls.append(_Call(schema=schema, prompt=prompt, images=tuple(images or ())))
        if schema not in self.responses:
            raise AssertionError(
                f"FakePipelineLLM got unexpected schema {schema.__name__}; "
                f"registered schemas: {[s.__name__ for s in self.responses]}"
            )
        return self.responses[schema]

    def calls_for(self, schema: type[BaseModel]) -> list[_Call]:
        return [c for c in self.calls if c.schema is schema]
