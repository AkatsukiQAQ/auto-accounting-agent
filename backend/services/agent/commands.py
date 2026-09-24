"""Strict command grammar. All UI money uses hundredths, including JPY."""
import re
import shlex
from decimal import Decimal
from backend.services.errors import ValidationError
from backend.services.budget.mutations import money


def amount(text, currency):
    if not re.fullmatch(r'(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d{1,2})?', text):
        raise ValidationError('Amount must be a non-negative number, with at most two decimal places')
    value = Decimal(text.replace(',', ''))
    if currency in ('JPY', 'KRW') and value != value.to_integral_value():
        raise ValidationError(f'{currency} requires whole currency units')
    result = int(value * 100)
    money(result)
    return result


def parse(text, currency):
    try:
        parts = shlex.split(text.strip())
    except ValueError as exc:
        raise ValidationError('Unclosed command quote') from exc
    if not parts or not parts[0].startswith('/'):
        return None
    command, *args = parts
    if command == '/help' and not args:
        return {'command': 'help'}
    if command == '/plan' and args == ['next-week']:
        return {'command': 'plan', 'period': 'next-week'}
    if command == '/undo' and not args:
        return {'command': 'undo'}
    if command == '/summary' and len(args) <= 1 and (not args or args[0] in ('week', 'month')):
        return {'command': 'summary', 'period': args[0] if args else 'month'}
    if command == '/spend' and len(args) == 2:
        cents = amount(args[0], currency)
        if not cents:
            raise ValidationError('Expense must be positive')
        return {'command': 'spend', 'amount_cents': cents, 'category': args[1]}
    if command == '/income' and args:
        cents = amount(args[0], currency)
        if not cents:
            raise ValidationError('Income must be positive')
        return {'command': 'income', 'amount_cents': cents, 'note': ' '.join(args[1:]) or None}
    if command in ('/budget', '/set-spent') and len(args) in (2, 3):
        period = args[2] if len(args) == 3 else 'month'
        allowed = ('week', 'month', 'next-week', 'next-month') if command == '/budget' else ('week', 'month')
        if period in allowed:
            return {'command': command[1:], 'category': args[0], 'amount_cents': amount(args[1], currency), 'period': period}
    raise ValidationError('Invalid command. Use /help, /plan next-week, /spend amount category, /income amount [note], /budget category amount [week|month|next-week|next-month], /set-spent category amount [week|month], /summary [week|month], or /undo. Quote multi-word categories.')
