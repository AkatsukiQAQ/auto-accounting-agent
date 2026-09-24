import pytest
from backend.services.agent.commands import parse, amount
from backend.services.errors import ValidationError

@pytest.mark.parametrize('text,command', [('/spend 1800 dining','spend'), ('/income 42 salary','income'),
    ('/budget dining 12,000 next-week','budget'), ('/set-spent "Eating Out" 0 week','set-spent'),
    ('/summary','summary'), ('/summary month','summary'), ('/plan next-week','plan'),
    ('/help','help'), ('/undo','undo')])
def test_commands(text, command):
    assert parse(text, 'JPY')['command'] == command

@pytest.mark.parametrize('text', ['/spend', '/spend -1 food', '/spend 0 food', '/spend 1.5 food',
    '/spend 1e4 food', '/spend NaN food', '/spend 1,23 food', '/spend 10 food extra',
    '/income 0', '/budget food 20 year', '/set-spent food 20 next-week', '/summary year',
    '/undo now', '/plan', '/plan next-month', '/help now', '/unknown', '/spend 5 "food',
    '/budget food 90071992547410 month'])
def test_bad_commands(text):
    with pytest.raises(ValidationError):
        parse(text, 'JPY')


def test_currency_units():
    assert amount('1800', 'JPY') == 180000
    assert amount('12.34', 'USD') == 1234
    assert parse('hello', 'JPY') is None
    with pytest.raises(ValidationError):
        amount('12.001', 'USD')
