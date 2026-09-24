"""Typed tool boundary; arithmetic and mutations remain in domain services."""
from datetime import date, timedelta, datetime, time, timezone
from typing import Annotated, Literal
import hashlib
import json
from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError as PydanticError
from sqlalchemy import select
from backend.db.models import Category, Transaction
from backend.api.schemas.budget import PlanOut, SummaryOut
from backend.services.budget import mutations as budget, summary
from backend.services.budget.periods import period_bounds, zone
from backend.services.ledger import apply
from backend.services.errors import ValidationError
from . import planning

Money = Annotated[StrictInt, Field(ge=0, le=9_007_199_254_740_991)]
Period = Literal['week', 'month']

class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', populate_by_name=True)

class Current(Input):
    period_type: Period = 'month'

class Plan(Input):
    plan_id: str

class Range(Input):
    start: date = Field(alias='from')
    end: date = Field(alias='to')
    currency: str | None = None

class Compare(Input):
    period_a: Range
    period_b: Range

class History(Input):
    category_id: str
    periods: int = Field(default=4, ge=1, le=24)
    period_type: Period = 'month'

class Recent(Input):
    category_id: str | None = None
    limit: int = Field(default=10, ge=1, le=50)

class Limit(Input):
    category_id: str
    limit_cents: Money
    currency: str
    period_type: Period
    starts_on: date
    plan_id: str | None = None

class PlanAmount(Plan):
    amount_cents: Money

class Expense(Input):
    category_id: str
    amount_cents: Money
    currency: str
    occurred_on: date
    note: str | None = None

class Total(Plan):
    category_id: str
    total_cents: Money
    note: str | None = None

class Clone(Input):
    source_plan_id: str
    starts_on: date

class Income(Input):
    amount_cents: Money
    currency: str
    occurred_on: date
    note: str | None = None


class SpendingResult(BaseModel):
    currency: str
    start: date
    end: date
    categories: dict[str, int]
    total_cents: int


class ComparisonResult(BaseModel):
    period_a: SpendingResult
    period_b: SpendingResult
    difference_cents: int


class HistoryPeriod(BaseModel):
    start: date
    end: date
    spent_cents: int


class HistoryResult(BaseModel):
    currency: str
    category_id: str
    periods: list[HistoryPeriod]


class EntryResult(BaseModel):
    id: str
    amount_cents: int
    category_id: str
    currency: str
    occurred_at: str
    note: str | None
    source: str
    granularity: str
    account_id: str


class RecentResult(BaseModel):
    currency: str
    entries: list[EntryResult]

READS = {'get_current_plan': Current, 'get_plan_summary': Plan, 'get_spending_breakdown': Range,
         'compare_spending': Compare, 'get_category_history': History, 'get_recent_entries': Recent,
         'get_budget_planning_context': planning.PlanningContextInput}
WRITES = {'set_budget_item_limit': Limit, 'set_planned_income': PlanAmount, 'set_savings_target': PlanAmount,
          'add_quick_expense': Expense, 'set_category_spend_total': Total, 'clone_budget_plan': Clone,
          'propose_next_week_budget': planning.PlanProposalInput}
SCHEMAS = {**READS, **WRITES, 'add_income': Income}
RESULTS = {'get_current_plan': PlanOut, 'get_plan_summary': SummaryOut,
           'get_spending_breakdown': SpendingResult, 'compare_spending': ComparisonResult,
           'get_category_history': HistoryResult, 'get_recent_entries': RecentResult}


def validate(name, args):
    if name not in SCHEMAS:
        raise ValidationError('Unknown agent tool')
    try:
        return SCHEMAS[name].model_validate(args)
    except PydanticError as exc:
        raise ValidationError(str(exc)) from exc


def category(session, name):
    rows = list(session.scalars(select(Category)))
    matches = [c for c in rows if name.casefold() in (c.id.casefold(), c.label.casefold())]
    if len(matches) != 1:
        raise ValidationError(f'Unknown or ambiguous category: {name}. Use its exact name or ID.')
    return matches[0].id


def plan_json(plan):
    return PlanOut.model_validate(plan).model_dump(mode='json') if plan else None


def read(session, name, args):
    if name == 'get_budget_planning_context':
        parsed = validate(name, args)
        return planning.get_context(session, parsed.history_weeks)
    result = _read(session, name, args)
    return RESULTS[name].model_validate(result).model_dump(mode='json') if result is not None else None


def _read(session, name, args):
    a = validate(name, args)
    tz, currency, today = summary.profile_context(session)
    if name == 'get_current_plan':
        return plan_json(summary.get_active_plan(session, a.period_type, today, currency))
    if name == 'get_plan_summary':
        return SummaryOut.model_validate(summary.get_plan_summary(session, a.plan_id)).model_dump(mode='json')
    if name == 'get_spending_breakdown':
        from backend.services.transactions import _validate_currency
        selected_currency = a.currency or currency
        _validate_currency(selected_currency)
        if a.end < a.start:
            raise ValidationError('Range end must be on or after start')
        values = summary.spend_by_category(session, a.start, a.end, selected_currency, tz)
        return {'currency': selected_currency, 'start': str(a.start), 'end': str(a.end), 'categories': values, 'total_cents': sum(values.values())}
    if name == 'compare_spending':
        if (a.period_a.currency or currency) != (a.period_b.currency or currency):
            raise ValidationError('Cannot compare different currencies')
        first = read(session, 'get_spending_breakdown', a.period_a.model_dump())
        second = read(session, 'get_spending_breakdown', a.period_b.model_dump())
        return {'period_a': first, 'period_b': second, 'difference_cents': first['total_cents'] - second['total_cents']}
    if name == 'get_category_history':
        category_id = category(session, a.category_id)
        rows = []
        on = today
        for _ in range(a.periods):
            start, end = period_bounds(a.period_type, on)
            rows.append({'start': str(start), 'end': str(end), 'spent_cents': summary.get_period_spend(session, category_id, start, min(end, today), currency, tz)})
            on = start - timedelta(days=1)
        return {'currency': currency, 'category_id': category_id, 'periods': rows}
    if name == 'get_recent_entries':
        stmt = select(Transaction).where(Transaction.currency == currency)
        if a.category_id:
            category_id = category(session, a.category_id)
            stmt = stmt.where(Transaction.category_id == category_id)
        rows = session.scalars(stmt.order_by(Transaction.occurred_at.desc(), Transaction.id).limit(a.limit))
        return {'currency': currency, 'entries': [transaction_json(r) for r in rows]}
    raise ValidationError('Not a read tool')


def transaction_json(row):
    return {k: (str(getattr(row, k)) if k == 'occurred_at' else getattr(row, k)) for k in
            ('id', 'amount_cents', 'category_id', 'currency', 'occurred_at', 'note', 'source', 'granularity', 'account_id')}


def fingerprint(row):
    """Detect later edits without copying non-action data into the audit log."""
    values = {column.name: getattr(row, column.name) for column in row.__table__.columns if column.name != 'updated_at'}
    return hashlib.sha256(json.dumps(values, default=str, sort_keys=True).encode()).hexdigest()


def write(session, name, args, source):
    """Returns structured result plus an optional conservative inverse."""
    if name == 'propose_next_week_budget':
        return planning.apply_proposal(session, args)
    a = validate(name, args)
    data = a.model_dump()
    if name == 'set_budget_item_limit':
        start, _ = period_bounds(a.period_type, a.starts_on)
        if start != a.starts_on:
            raise ValidationError('Budget must start on the period boundary')
        plans = budget.list_plans(session, period_type=a.period_type, start=start, end=start, currency=a.currency)
        plan = budget.get_plan(session, a.plan_id) if a.plan_id else (plans[0] if plans else None)
        if plan and (plan.currency != a.currency or plan.starts_on != start or plan.period_type != a.period_type):
            raise ValidationError('Plan period/currency mismatch')
        created = plan is None
        if created:
            plan = budget.create_plan(session, period_type=a.period_type, starts_on=start, currency=a.currency, created_by='agent')
        item = next((i for i in plan.items if i.category_id == a.category_id), None)
        before = item.limit_cents if item else None
        if item:
            budget.update_item(session, item.id, limit_cents=a.limit_cents)
        else:
            item = budget.add_item(session, plan.id, category_id=a.category_id, limit_cents=a.limit_cents)
        result = plan_json(plan)
        return result, {'kind': 'limit', 'item_id': item.id, 'before': before, 'after': a.limit_cents,
                        'fingerprint': fingerprint(item)} if not created else None
    if name in ('set_planned_income', 'set_savings_target'):
        field = 'planned_income_cents' if name == 'set_planned_income' else 'savings_target_cents'
        before = getattr(budget.get_plan(session, a.plan_id), field)
        result = budget.update_plan(session, a.plan_id, **{field: a.amount_cents})
        return plan_json(result), {'kind': 'plan_amount', 'plan_id': a.plan_id, 'field': field, 'before': before, 'after': a.amount_cents}
    if name == 'clone_budget_plan':
        return plan_json(budget.clone_plan(session, **data)), None
    if name == 'add_quick_expense':
        row = budget.quick_expense(session, **data)
        apply.update(session, row.id, source=source)
    elif name == 'set_category_spend_total':
        row = budget.set_category_spend_total(session, **data)
    elif name == 'add_income':
        tz, _, today = summary.profile_context(session)
        if not a.amount_cents or a.occurred_on > today:
            raise ValidationError('Income must be positive and cannot be in the future')
        when = datetime.combine(a.occurred_on, time(12), zone(tz)).astimezone(timezone.utc).replace(tzinfo=None)
        row = apply.create(session, amount_cents=a.amount_cents, currency=a.currency, occurred_at=when,
                           merchant=None, category_id='income', source=source, granularity='quick', note=a.note)
    else:
        raise ValidationError('Not a write tool')
    result = EntryResult.model_validate(transaction_json(row)).model_dump(mode='json') if row else None
    return result, {'kind': 'transaction', 'snapshot': result, 'fingerprint': fingerprint(row)} if row else None
