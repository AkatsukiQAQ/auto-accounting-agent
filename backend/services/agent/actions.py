"""Structured proposals and atomic, idempotent confirmation."""
import json
from datetime import date, datetime, timezone
from uuid import uuid4
from sqlalchemy import select, update
from backend.db.models import AgentAction, BudgetItem, Transaction
from backend.services.errors import ConflictError, NotFoundError, ValidationError
from backend.services.budget import mutations as budget
from backend.services.budget.periods import period_bounds
from backend.services.budget.summary import profile_context
from backend.services.transactions import _validate_currency
from backend.services.ledger import apply
from . import tools
from . import planning


def action_out(row):
    return {'id': row.id, 'sessionId': row.session_id, 'actionType': row.action_type,
            'status': row.status, 'payload': json.loads(row.payload_json)}


def validate_proposal(session, name, args):
    if name == 'propose_next_week_budget':
        return planning.prepare(session, args)[0]
    a = tools.validate(name, args)
    if name not in tools.WRITES and name != 'add_income':
        raise ValidationError('Not a write tool')
    if hasattr(a, 'currency'):
        _validate_currency(a.currency)
        for field in ('amount_cents', 'limit_cents'):
            if hasattr(a, field) and a.currency in ('JPY', 'KRW') and getattr(a, field) % 100:
                raise ValidationError(f'{a.currency} requires whole currency units')
    if hasattr(a, 'category_id'):
        budget.validate_item(session, a.category_id, 0, .8, 'flexible')
    if getattr(a, 'plan_id', None):
        plan = budget.get_plan(session, a.plan_id)
        for field in ('amount_cents', 'total_cents'):
            if hasattr(a, field) and plan.currency in ('JPY', 'KRW') and getattr(a, field) % 100:
                raise ValidationError(f'{plan.currency} requires whole currency units')
    if name == 'set_budget_item_limit':
        start, _ = period_bounds(a.period_type, a.starts_on)
        if start != a.starts_on:
            raise ValidationError('Budget must start on the period boundary')
        if a.plan_id and (plan.currency != a.currency or plan.starts_on != start or plan.period_type != a.period_type):
            raise ValidationError('Plan period/currency mismatch')
    if name in ('add_quick_expense', 'add_income'):
        if not a.amount_cents or a.occurred_on > profile_context(session)[2]:
            raise ValidationError('Amount must be positive and date cannot be in the future')
    if name == 'set_category_spend_total' and plan.starts_on > profile_context(session)[2]:
        raise ValidationError('Cannot adjust a future period')
    if name == 'clone_budget_plan':
        plan = budget.get_plan(session, a.source_plan_id)
        start, end = period_bounds(plan.period_type, a.starts_on)
        if start != a.starts_on or budget.list_plans(session, period_type=plan.period_type, start=start, end=end, currency=plan.currency):
            raise ValidationError('Clone needs an empty destination period starting on its boundary')
    return a.model_dump(mode='json')


def target_state(session, name, args):
    """Only guard data that a proposal would overwrite or copy."""
    if name == 'propose_next_week_budget':
        return planning.before_state(session, args)
    if name == 'set_budget_item_limit':
        plans = budget.list_plans(session, period_type=args['period_type'],
            start=date.fromisoformat(args['starts_on']), end=date.fromisoformat(args['starts_on']),
            currency=args['currency'])
        plan = budget.get_plan(session, args['plan_id']) if args.get('plan_id') else (plans[0] if plans else None)
        item = next((i for i in plan.items if i.category_id == args['category_id']), None) if plan else None
        return {'plan_id': plan.id if plan else None, 'item_id': item.id if item else None,
                'limit_cents': item.limit_cents if item else None}
    if name in ('set_planned_income', 'set_savings_target'):
        field = 'planned_income_cents' if name == 'set_planned_income' else 'savings_target_cents'
        plan = budget.get_plan(session, args['plan_id'])
        return {'plan_id': plan.id, 'amount_cents': getattr(plan, field)}
    if name == 'clone_budget_plan':
        return tools.plan_json(budget.get_plan(session, args['source_plan_id']))
    return None


def propose(session, session_id, name, args, source='agent'):
    if name == 'propose_next_week_budget':
        previous = list(session.scalars(select(AgentAction).where(
            AgentAction.session_id == session_id,
            AgentAction.action_type == 'propose_next_week_budget',
            AgentAction.status == 'proposed',
        ).order_by(AgentAction.created_at.desc(), AgentAction.id.desc())))
        if previous:
            # Merge against the last canonical preview, not the model's memory.
            # A follow-up may mention only one changed category; every omitted
            # category and plan-level amount keeps the pending proposal's value.
            prior_preview = json.loads(previous[0].payload_json)['preview']
            requested = {item['category_id']: item for item in args.get('operations', [])}
            carried = []
            for item in prior_preview['operations']:
                carried.append(requested.pop(item['category_id'], {
                    'category_id': item['category_id'],
                    'proposed_limit_cents': item['proposed_limit_cents'],
                    'reason': item['reason'],
                    'allow_fixed_reduction': item['allow_fixed_reduction'],
                }))
            carried.extend(requested.values())
            args = dict(args, operations=carried)
            totals = prior_preview['totals']
            if args.get('planned_income_cents') is None:
                args['planned_income_cents'] = totals['planned_income_cents']
            if args.get('savings_target_cents') is None:
                args['savings_target_cents'] = totals['savings_target_cents']
        args, preview, before = planning.prepare(session, args)
        action_id = str(uuid4())
        # A conversational revision replaces the older pending plan. Keeping two
        # complete plans actionable would make "make Food lower" ambiguous at Apply.
        for prior in previous:
            prior_payload = json.loads(prior.payload_json)
            prior_payload['supersededBy'] = action_id
            prior.payload_json = json.dumps(prior_payload)
            prior.status = 'cancelled'
        row = AgentAction(id=action_id, session_id=session_id, action_type=name, status='proposed',
                          created_at=datetime.now(timezone.utc),
                          payload_json=json.dumps({'arguments': args, 'source': source,
                                                   'preview': preview, 'before': before}))
        session.add(row)
        session.flush()
        return row
    args = validate_proposal(session, name, args)
    preview = dict(args)
    before = target_state(session, name, args)
    if before is not None:
        preview['previous_cents'] = before.get('limit_cents', before.get('amount_cents'))
    if name == 'clone_budget_plan':
        preview['items'] = [{'category_id': item['category_id'], 'limit_cents': item['limit_cents']}
                            for item in before['items']]
        preview['planned_income_cents'] = before['planned_income_cents']
        preview['savings_target_cents'] = before['savings_target_cents']
    plan_id = args.get('plan_id') or args.get('source_plan_id')
    if plan_id:
        plan = budget.get_plan(session, plan_id)
        preview.update(currency=plan.currency, period_type=plan.period_type)
        preview.setdefault('starts_on', str(plan.starts_on))
        preview['ends_on'] = str(period_bounds(plan.period_type, date.fromisoformat(preview['starts_on']))[1])
    elif name == 'set_budget_item_limit':
        preview['ends_on'] = str(period_bounds(args['period_type'], date.fromisoformat(args['starts_on']))[1])
    row = AgentAction(id=str(uuid4()), session_id=session_id, action_type=name, status='proposed',
                      created_at=datetime.now(timezone.utc),
                      payload_json=json.dumps({'arguments': args, 'source': source, 'preview': preview, 'before': before}))
    session.add(row)
    session.flush()
    return row


def get_action(session, session_id, action_id):
    row = session.get(AgentAction, action_id)
    if row is None or row.session_id != session_id:
        raise NotFoundError('Action not found in this chat')
    return row


def edit_plan_proposal(session, session_id, action_id, patch):
    session.execute(update(AgentAction).where(
        AgentAction.id == action_id, AgentAction.session_id == session_id,
        AgentAction.status == 'proposed').values(status=AgentAction.status))
    row = get_action(session, session_id, action_id)
    session.refresh(row)
    if row.status != 'proposed':
        raise ConflictError(f'Action is already {row.status}')
    if row.action_type != 'propose_next_week_budget':
        raise ValidationError('Only a pending weekly plan proposal can be edited')
    payload = json.loads(row.payload_json)
    if planning.before_state(session, payload['arguments']) != payload['before']:
        raise ConflictError('Budget data changed after this proposal. Ask MITA for a fresh proposal before editing.')
    arguments = dict(payload['arguments'])
    arguments['operations'] = patch['operations']
    if patch.get('summary') is not None:
        arguments['summary'] = patch['summary']
    arguments, preview, before = planning.prepare(session, arguments)
    payload.update(arguments=arguments, preview=preview, before=before)
    row.payload_json = json.dumps(payload)
    session.flush()
    return row


def decide(session, session_id, action_id, decision):
    # The first statement takes the SQLite write lock, before any read. Domain
    # changes and status transition commit together; retries never reapply them.
    status = 'confirmed' if decision == 'apply' else 'cancelled'
    claimed = session.execute(update(AgentAction).where(AgentAction.id == action_id,
        AgentAction.session_id == session_id, AgentAction.status == 'proposed').values(status=status)).rowcount
    row = get_action(session, session_id, action_id)
    session.refresh(row)
    if not claimed:
        if (decision == 'apply' and row.status == 'executed') or (decision == 'cancel' and row.status == 'cancelled'):
            return row
        raise ConflictError(f'Action is already {row.status}')
    if decision == 'cancel':
        return row
    payload = json.loads(row.payload_json)
    try:
        with session.begin_nested():
            args = validate_proposal(session, row.action_type, payload['arguments'])
            if target_state(session, row.action_type, args) != payload['before']:
                raise ConflictError('Budget changed after this proposal. Ask MITA for a fresh proposal before applying.')
            result, inverse = tools.write(session, row.action_type, args, payload['source'])
        payload.update(result=result, undo=inverse)
        row.status = 'executed'
        row.executed_at = datetime.now(timezone.utc)
    except (ValidationError, NotFoundError, ConflictError) as exc:
        row.status = 'failed'
        payload['error'] = str(exc)
    row.payload_json = json.dumps(payload)
    session.flush()
    return row


def undo(session, session_id):
    # Serialize undo with confirmation and other undo requests.
    session.execute(update(AgentAction).where(AgentAction.session_id == session_id).values(status=AgentAction.status))
    rows = session.scalars(select(AgentAction).where(AgentAction.session_id == session_id,
        AgentAction.status == 'executed', AgentAction.action_type != 'undo').order_by(AgentAction.executed_at.desc(), AgentAction.created_at.desc(), AgentAction.id.desc()))
    row = next((r for r in rows if not json.loads(r.payload_json).get('undoneBy')), None)
    if row is None:
        raise ValidationError('Nothing to undo in this chat')
    payload = json.loads(row.payload_json)
    inverse = payload.get('undo')
    if not inverse:
        raise ValidationError('This action cannot be undone automatically; edit it in Plan instead')
    kind = inverse['kind']
    if kind == 'transaction':
        snapshot = inverse['snapshot']
        current = session.get(Transaction, snapshot['id'])
        if current is None or tools.fingerprint(current) != inverse['fingerprint']:
            raise ConflictError('Entry changed since this action; automatic undo is unsafe')
        apply.delete(session, current.id)
    elif kind == 'limit':
        item = session.get(BudgetItem, inverse['item_id'])
        if item is None or tools.fingerprint(item) != inverse['fingerprint']:
            raise ConflictError('Budget changed since this action; automatic undo is unsafe')
        if inverse['before'] is None:
            budget.delete_item(session, item.id)
        else:
            budget.update_item(session, item.id, limit_cents=inverse['before'])
    elif kind == 'plan_amount':
        plan = budget.get_plan(session, inverse['plan_id'])
        if getattr(plan, inverse['field']) != inverse['after']:
            raise ConflictError('Plan changed since this action; automatic undo is unsafe')
        budget.update_plan(session, plan.id, **{inverse['field']: inverse['before']})
    elif kind == 'budget_plan':
        planning.undo_proposal(session, inverse)
    audit = AgentAction(id=str(uuid4()), session_id=session_id, action_type='undo', status='executed',
        payload_json=json.dumps({'targetActionId': row.id, 'result': 'undone'}), executed_at=datetime.now(timezone.utc))
    session.add(audit)
    payload['undoneBy'] = audit.id
    row.payload_json = json.dumps(payload)
    session.flush()
    return audit

