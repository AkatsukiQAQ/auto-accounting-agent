"""Agent-only model adapter. No dependency on the receipt pipeline."""
import json
from typing import Protocol
from openai import OpenAI, OpenAIError
from backend.services.errors import ValidationError
from .tools import READS, WRITES


class AgentModel(Protocol):
    def complete(self, messages: list[dict]) -> dict: ...


class OpenAIAgentModel:
    def __init__(self, api_key, model):
        self.client = OpenAI(api_key=api_key, timeout=45, max_retries=1)
        self.model = model

    def complete(self, messages):
        definitions = [{'type': 'function', 'function': {'name': name,
            'description': ('Read deterministic finance data.' if name in READS else 'Propose a write. Execution requires a separate user Apply click.'),
            'parameters': schema.model_json_schema()}} for name, schema in {**READS, **WRITES}.items()]
        try:
            response = self.client.chat.completions.create(model=self.model, messages=messages,
                tools=definitions, parallel_tool_calls=False)
            msg = response.choices[0].message
            if msg.tool_calls:
                if len(msg.tool_calls) != 1:
                    raise ValidationError('Only one tool call per step is supported. Please narrow your request.')
                call = msg.tool_calls[0]
                return {'name': call.function.name, 'arguments': json.loads(call.function.arguments), 'id': call.id}
            return {'content': msg.content or 'No response. Please try again.'}
        except (OpenAIError, ValueError, IndexError) as exc:
            raise ValidationError('Agent model unavailable or returned an invalid response. Retry or use a slash command.') from exc
