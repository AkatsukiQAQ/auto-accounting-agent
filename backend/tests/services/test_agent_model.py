from types import SimpleNamespace
import pytest
from backend.services.agent.model import OpenAIAgentModel
from backend.services.agent import model as model_module
from backend.services.agent.tools import READS, WRITES
from backend.services.errors import ValidationError


def fake_provider(monkeypatch, message):
    captured = {}
    def create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])
    monkeypatch.setattr(model_module, 'OpenAI', lambda **kwargs: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    return OpenAIAgentModel('unused-test-key', 'stub-model'), captured


def test_provider_exposes_typed_tools_without_pipeline_or_undo(monkeypatch):
    call = SimpleNamespace(id='tool-1', function=SimpleNamespace(name='get_current_plan', arguments='{"period_type":"month"}'))
    model, captured = fake_provider(monkeypatch, SimpleNamespace(tool_calls=[call], content=None))
    result = model.complete([{'role':'user','content':'How is my budget?'}])
    assert result == {'id':'tool-1','name':'get_current_plan','arguments':{'period_type':'month'}}
    names = {tool['function']['name'] for tool in captured['tools']}
    assert names == set(READS) | set(WRITES)
    assert 'undo' not in names and 'add_income' not in names
    assert captured['parallel_tool_calls'] is False
    assert captured['model'] == 'stub-model'
    for tool in captured['tools']:
        assert tool['function']['parameters']['additionalProperties'] is False


def test_provider_text_and_invalid_json(monkeypatch):
    model, _ = fake_provider(monkeypatch, SimpleNamespace(tool_calls=None, content='Within plan.'))
    assert model.complete([]) == {'content':'Within plan.'}
    call = SimpleNamespace(id='tool-1', function=SimpleNamespace(name='add_quick_expense', arguments='invalid'))
    model, _ = fake_provider(monkeypatch, SimpleNamespace(tool_calls=[call], content=None))
    with pytest.raises(ValidationError):
        model.complete([])
    model, _ = fake_provider(monkeypatch, SimpleNamespace(tool_calls=[call, call], content=None))
    with pytest.raises(ValidationError):
        model.complete([])
