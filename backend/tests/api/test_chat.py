from datetime import timedelta
import json
import pytest
from sqlalchemy import select, func
from backend.db.models import Transaction, AgentAction, BudgetPlan, ChatMessage, ChatSession
from backend.services.agent import tools, actions
from backend.services.agent import planning
from backend.services.budget import mutations as budget
from backend.services.budget.periods import period_bounds
from backend.services.budget.summary import profile_context
from backend.services.errors import ValidationError


class StubModel:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []
    def complete(self, messages):
        self.calls.append(messages.copy())
        return self.responses.pop(0)


def chat(client):
    return client.post('/api/chat/sessions').json()['data']['id']


def test_session_history_uses_first_user_message_as_title(client):
    first = chat(client)
    second = chat(client)
    send(client, first, '/help')

    rows = client.get('/api/chat/sessions').json()['data']

    by_id = {row['id']: row for row in rows}
    assert by_id[first]['title'] == '/help'
    assert by_id[second]['title'] == 'New chat'


def test_session_can_be_renamed_and_deleted_with_its_chat_audit(client, db_session):
    sid = chat(client)
    assert send(client, sid, '/spend 1800 food').status_code == 200

    renamed = client.patch(f'/api/chat/sessions/{sid}', json={'title': '  September   review  '})
    assert renamed.status_code == 200
    assert renamed.json()['data']['title'] == 'September review'
    assert client.patch(f'/api/chat/sessions/{sid}', json={'title': '   '}).status_code == 400
    assert next(row for row in client.get('/api/chat/sessions').json()['data'] if row['id'] == sid)['title'] == 'September review'

    assert client.delete(f'/api/chat/sessions/{sid}').status_code == 204
    assert db_session.get(ChatSession, sid) is None
    assert db_session.scalar(select(func.count()).select_from(ChatMessage).where(ChatMessage.session_id == sid)) == 0
    assert db_session.scalar(select(func.count()).select_from(AgentAction).where(AgentAction.session_id == sid)) == 0
    assert db_session.scalar(select(func.count()).select_from(Transaction)) == 1


def send(client, sid, content):
    return client.post(f'/api/chat/sessions/{sid}/messages', json={'content': content})


def decide(client, sid, action, decision='apply'):
    return client.post(f'/api/chat/sessions/{sid}/actions/{action}', json={'decision': decision})


def current_plan(client, db_session):
    today = profile_context(db_session)[2]
    start, _ = period_bounds('month', today)
    return client.post('/api/budget-plans', json={'periodType':'month', 'startsOn':str(start), 'currency':'JPY'}).json()['data']


def test_natural_write_confirmation_exactly_once_and_dashboard(client, app, db_session, monkeypatch):
    plan = current_plan(client, db_session)
    today = profile_context(db_session)[2]
    app.state.agent_model = StubModel({'name':'add_quick_expense', 'arguments': {
        'category_id':'food','amount_cents':180000,'currency':'JPY','occurred_on':str(today)}})
    sid = chat(client)
    original = tools.write
    calls = []
    def tracked(*a, **kw):
        calls.append(a[1])
        return original(*a, **kw)
    monkeypatch.setattr(tools, 'write', tracked)
    response = send(client, sid, 'Add 1800 yen for food')
    assert response.status_code == 200, response.text
    action = response.json()['data']['action']
    assert action['status'] == 'proposed'
    assert calls == []
    assert db_session.scalar(select(func.count()).select_from(Transaction)) == 0
    for _ in range(2):
        result = decide(client, sid, action['id'])
        assert result.status_code == 200, result.text
        assert result.json()['data']['status'] == 'executed'
    assert calls == ['add_quick_expense']
    summary = client.get(f"/api/budget-plans/{plan['id']}/summary").json()['data']
    assert summary['actualSpendCents'] == 180000
    assert db_session.scalar(select(func.count()).select_from(Transaction)) == 1
    assert decide(client, sid, action['id'], 'cancel').status_code == 409
    assert client.get(f'/api/chat/sessions/{sid}').json()['data']['actions'][0]['status'] == 'executed'


def test_cancel_no_mutation_and_session_scope(client, app, db_session):
    plan = current_plan(client, db_session)
    app.state.agent_model = StubModel({'name':'set_planned_income', 'arguments': {'plan_id':plan['id'],'amount_cents':200000}})
    sid = chat(client)
    action = send(client, sid, 'Set income').json()['data']['action']
    other = chat(client)
    assert decide(client, other, action['id']).status_code == 404
    for _ in range(2):
        assert decide(client, sid, action['id'], 'cancel').json()['data']['status'] == 'cancelled'
    assert decide(client, sid, action['id']).status_code == 409
    assert client.get(f"/api/budget-plans/{plan['id']}").json()['data']['plannedIncomeCents'] is None


def test_completion_demo_and_read_loop(client, app, db_session):
    # The existing product permits user categories; do not silently map Dining to Food.
    created = client.post('/api/categories', json={'id':'dining','label':'Dining','colorBg':'#ffffff','colorDot':'#000000'})
    assert created.status_code == 201, created.text
    plan = current_plan(client, db_session)
    app.state.agent_model = StubModel({'name':'get_current_plan','arguments':{'period_type':'month'}},
        {'name':'get_plan_summary','arguments':{'plan_id':plan['id']}}, {'content':'Your recorded spending is within plan.'})
    sid = chat(client)
    response = send(client, sid, 'How am I doing this month?')
    assert response.status_code == 200, response.text
    assert len(app.state.agent_model.calls) == 3
    tool_data = json.loads(app.state.agent_model.calls[-1][-1]['content'])
    assert tool_data['actual_spend_cents'] == 0
    today = profile_context(db_session)[2]
    _, end = period_bounds('week', today)
    start = end + timedelta(days=1)
    app.state.agent_model = StubModel({'name':'set_budget_item_limit','arguments':{
        'category_id':'dining','limit_cents':1200000,'currency':'JPY','period_type':'week','starts_on':str(start)}})
    action = send(client, sid, "Set next week's dining budget to ¥12,000.").json()['data']['action']
    assert db_session.scalar(select(func.count()).select_from(BudgetPlan)) == 1
    applied = decide(client, sid, action['id']).json()['data']
    assert applied['status'] == 'executed', applied
    plans = client.get(f'/api/budget-plans?periodType=week&from={start}&to={start}&currency=JPY').json()['data']
    assert plans[0]['items'][0]['limitCents'] == 1200000
    assert client.get(f"/api/budget-plans/{plans[0]['id']}/summary").json()['data']['plannedSpendCents'] == 1200000
    before_calls = len(app.state.agent_model.calls)
    result = send(client, sid, '/spend 1800 dining')
    assert result.status_code == 200, result.text
    assert len(app.state.agent_model.calls) == before_calls
    assert result.json()['data']['action']['payload']['result']['source'] == 'slash'


def test_slash_income_set_total_and_undo(client, db_session):
    plan = current_plan(client, db_session)
    sid = chat(client)
    for text in ('/spend 1800 food', '/income 4000 salary', '/set-spent food 2500 month'):
        response = send(client, sid, text)
        assert response.status_code == 200, response.text
    def total():
        return client.get(f"/api/budget-plans/{plan['id']}/summary").json()['data']['actualSpendCents']
    assert total() == 250000
    assert send(client, sid, '/undo').status_code == 200
    assert total() == 180000
    assert send(client, sid, '/summary month').status_code == 200
    assert send(client, sid, '/undo').status_code == 200  # income
    assert total() == 180000
    assert send(client, sid, '/undo').status_code == 200  # expense
    assert total() == 0
    assert send(client, sid, '/undo').status_code == 400
    assert db_session.scalar(select(func.count()).select_from(AgentAction).where(AgentAction.action_type == 'undo')) == 3


def test_undo_refuses_later_manual_edits(client):
    sid = chat(client)
    action = send(client, sid, '/spend 1800 food').json()['data']['action']
    txn = action['payload']['result']['id']
    assert client.patch(f'/api/transactions/{txn}', json={'amountCents':-190000}).status_code == 200
    assert send(client, sid, '/undo').status_code == 409


@pytest.mark.parametrize('tool,args', [
    ('set_budget_item_limit', {'category_id':'missing','limit_cents':100,'currency':'JPY','period_type':'week','starts_on':'2026-09-28'}),
    ('add_quick_expense', {'category_id':'food','amount_cents':-1,'currency':'JPY','occurred_on':'2026-01-01'}),
    ('add_quick_expense', {'category_id':'food','amount_cents':True,'currency':'JPY','occurred_on':'2026-01-01'}),
    ('add_quick_expense', {'category_id':'food','amount_cents':101,'currency':'JPY','occurred_on':'2026-01-01'}),
    ('add_quick_expense', {'category_id':'food','amount_cents':100,'currency':'US','occurred_on':'2026-01-01'}),
    ('add_quick_expense', {'category_id':'income','amount_cents':100,'currency':'JPY','occurred_on':'2026-01-01'}),
])
def test_write_validation(client, app, db_session, tool, args):
    app.state.agent_model = StubModel({'name':tool,'arguments':args})
    response = send(client, chat(client), 'Please change it')
    assert response.status_code == 400, response.text
    assert db_session.scalar(select(func.count()).select_from(Transaction)) == 0
    assert db_session.scalar(select(func.count()).select_from(AgentAction)) == 0


def test_read_tools_currency_and_validation(client, db_session):
    sid = chat(client)
    assert send(client, sid, '/spend 1800 food').status_code == 200
    today = profile_context(db_session)[2]
    data = {'start':str(today), 'end':str(today), 'currency':'JPY'}
    result = tools.read(db_session, 'get_spending_breakdown', data)
    assert result['total_cents'] == 180000
    assert tools.read(db_session, 'get_spending_breakdown', {**data,'currency':'USD'})['total_cents'] == 0
    comparison = tools.read(db_session, 'compare_spending', {'period_a':data, 'period_b':data})
    assert comparison['difference_cents'] == 0
    assert tools.read(db_session, 'get_category_history', {'category_id':'food','periods':2})['periods'][0]['spent_cents'] == 180000
    assert len(tools.read(db_session, 'get_recent_entries', {'category_id':'food','limit':1})['entries']) == 1
    for name, args in [('get_recent_entries', {'limit':100}), ('get_category_history', {'category_id':'food','periods':0}),
        ('get_current_plan', {'period_type':'year'}), ('get_spending_breakdown', {**data,'end':'1900-01-01'}),
        ('compare_spending', {'period_a':data,'period_b':{**data,'currency':'USD'}})]:
        with pytest.raises(ValidationError):
            tools.read(db_session, name, args)


def test_stream_and_missing_key_slash_bypass(client):
    sid = chat(client)
    response = client.post(f'/api/chat/sessions/{sid}/stream', json={'content':'/spend 1800 food'})
    events = [json.loads(line) for line in response.text.splitlines()]
    assert events[-1]['type'] == 'done', events
    assert events[-1]['action']['status'] == 'executed'
    assert send(client, sid, '/spend broken food').status_code == 400
    assert send(client, sid, 'hello').status_code == 400
    error = client.post(f'/api/chat/sessions/{sid}/stream', json={'content':'/wat'}).text
    assert json.loads(error)['type'] == 'error'


def test_failed_confirmation_is_atomic(client, app, db_session):
    plan = current_plan(client, db_session)
    app.state.agent_model = StubModel({'name':'set_savings_target','arguments':{'plan_id':plan['id'],'amount_cents':100000}})
    sid = chat(client)
    action = send(client, sid, 'Set savings').json()['data']['action']
    client.delete(f"/api/budget-plans/{plan['id']}")
    result = decide(client, sid, action['id']).json()['data']
    assert result['status'] == 'failed'
    assert decide(client, sid, action['id']).status_code == 409


def test_stale_proposal_does_not_overwrite_manual_change(client, app, db_session):
    plan = current_plan(client, db_session)
    app.state.agent_model = StubModel({'name':'set_planned_income','arguments':{'plan_id':plan['id'],'amount_cents':200000}})
    sid = chat(client)
    action = send(client, sid, 'Set planned income').json()['data']['action']
    client.patch(f"/api/budget-plans/{plan['id']}", json={'plannedIncomeCents':300000})
    result = decide(client, sid, action['id']).json()['data']
    assert result['status'] == 'failed'
    assert 'changed' in result['payload']['error']
    assert client.get(f"/api/budget-plans/{plan['id']}").json()['data']['plannedIncomeCents'] == 300000


def test_all_budget_write_tools_and_supported_undo(client, app, db_session):
    plan = current_plan(client, db_session)
    sid = chat(client)
    for name, field in [('set_planned_income','plannedIncomeCents'), ('set_savings_target','savingsTargetCents')]:
        app.state.agent_model = StubModel({'name':name,'arguments':{'plan_id':plan['id'],'amount_cents':200000}})
        action = send(client, sid, 'Update plan').json()['data']['action']
        assert action['payload']['preview']['currency'] == 'JPY'
        assert decide(client, sid, action['id']).json()['data']['status'] == 'executed'
        assert client.get(f"/api/budget-plans/{plan['id']}").json()['data'][field] == 200000
        assert send(client, sid, '/undo').status_code == 200
        assert client.get(f"/api/budget-plans/{plan['id']}").json()['data'][field] is None
    assert send(client, sid, '/budget food 5000 month').json()['data']['action']['status'] == 'executed'
    assert send(client, sid, '/budget food 6000 month').json()['data']['action']['status'] == 'executed'
    assert send(client, sid, '/undo').status_code == 200
    assert client.get(f"/api/budget-plans/{plan['id']}").json()['data']['items'][0]['limitCents'] == 500000
    _, end = period_bounds('month', profile_context(db_session)[2])
    start = end + timedelta(days=1)
    app.state.agent_model = StubModel({'name':'clone_budget_plan','arguments':{'source_plan_id':plan['id'],'starts_on':str(start)}})
    proposal = send(client, sid, 'Copy this plan to next month').json()['data']['action']
    assert proposal['payload']['preview']['items'] == [{'category_id':'food','limit_cents':500000}]
    result = decide(client, sid, proposal['id']).json()['data']
    assert result['status'] == 'executed', result
    copied = result['payload']['result']
    assert copied['items'][0]['limit_cents'] == 500000
    assert client.get(f"/api/budget-plans/{copied['id']}/summary").json()['data']['actualSpendCents'] == 0
    assert send(client, sid, '/undo').status_code == 400  # new plans require manual Plan edits


def test_text_apply_cannot_confirm_and_model_cannot_call_undo(client, app, db_session):
    plan = current_plan(client, db_session)
    response = {'name':'set_planned_income','arguments':{'plan_id':plan['id'],'amount_cents':200000}}
    app.state.agent_model = StubModel(response, {'content':'Use the Apply button to confirm.'}, {'name':'undo','arguments':{}})
    sid = chat(client)
    action = send(client, sid, 'Set income').json()['data']['action']
    assert send(client, sid, 'Apply').status_code == 200
    assert client.get(f'/api/chat/sessions/{sid}').json()['data']['actions'][0]['status'] == 'proposed'
    assert send(client, sid, 'Undo').status_code == 400
    assert client.get(f"/api/budget-plans/{plan['id']}").json()['data']['plannedIncomeCents'] is None
    assert decide(client, sid, action['id']).json()['data']['status'] == 'executed'


def test_usd_minor_units_and_range_aliases(client, db_session):
    from backend.services.settings import update_settings
    update_settings(db_session, {'profile': {'defaultCurrency':'USD', 'timezone':'Asia/Tokyo'}})
    db_session.commit()
    sid = chat(client)
    result = send(client, sid, '/spend 12.34 food').json()['data']['action']
    assert result['payload']['result']['amount_cents'] == -1234
    assert result['payload']['result']['currency'] == 'USD'
    today = str(profile_context(db_session)[2])
    summary = tools.read(db_session, 'get_spending_breakdown', {'from':today,'to':today})
    assert summary['currency'] == 'USD'
    assert summary['total_cents'] == 1234


def test_undo_preserves_manual_merchant_edits(client):
    sid = chat(client)
    action = send(client, sid, '/spend 1800 food').json()['data']['action']
    txn = action['payload']['result']['id']
    client.patch(f'/api/transactions/{txn}', json={'merchant':'New merchant'})
    assert send(client, sid, '/undo').status_code == 409


def test_model_failure_does_not_hold_writer_lock_or_lose_user_message(client, app, session_factory):
    class FailingModel:
        def complete(self, messages):
            with session_factory() as independent:
                independent.add(ChatSession(id='independent-write'))
                independent.commit()
            raise ValidationError('Model unavailable')
    app.state.agent_model = FailingModel()
    sid = chat(client)
    assert send(client, sid, 'How is my budget?').status_code == 400
    history = client.get(f'/api/chat/sessions/{sid}').json()['data']
    assert history['messages'][0]['content'] == 'How is my budget?'
    assert history['actions'] == []


def test_blank_message_rejected_and_loop_is_bounded(client, app):
    sid = chat(client)
    assert send(client, sid, '   ').status_code == 400
    app.state.agent_model = StubModel(*[{'name':'get_current_plan','arguments':{'period_type':'month'}} for _ in range(8)])
    response = send(client, sid, 'Keep looking')
    assert response.status_code == 200
    assert len(app.state.agent_model.calls) == 8
    assert 'limit' in response.json()['data']['message']['content']


def make_weekly_baseline(db_session):
    today = profile_context(db_session)[2]
    start, end = period_bounds('week', today)
    plan = budget.create_plan(db_session, period_type='week', starts_on=start, currency='JPY',
                              planned_income_cents=10000000, savings_target_cents=2000000)
    budget.add_item(db_session, plan.id, category_id='rent', limit_cents=5000000, kind='fixed')
    budget.add_item(db_session, plan.id, category_id='food', limit_cents=2000000, kind='flexible')
    budget.add_item(db_session, plan.id, category_id='shopping', limit_cents=1000000, kind='discretionary')
    db_session.commit()
    return plan, end + timedelta(days=1)


def planner_stub(target_start, *, food=1500000, shopping=500000):
    return StubModel(
        {'name':'get_budget_planning_context','arguments':{'history_weeks':4}},
        {'name':'propose_next_week_budget','arguments':{
            'target_starts_on':str(target_start), 'summary':'Spend less on flexible categories next week.',
            'operations':[
                {'category_id':'food','proposed_limit_cents':food,'reason':'Keep groceries practical.'},
                {'category_id':'shopping','proposed_limit_cents':shopping,'reason':'Reduce discretionary purchases.'},
            ],
        }},
    )


def test_multi_category_plan_edit_apply_dashboard_and_undo(client, app, db_session):
    _, target_start = make_weekly_baseline(db_session)
    app.state.agent_model = planner_stub(target_start)
    sid = chat(client)
    response = send(client, sid, 'Help me make a stricter budget for next week.')
    assert response.status_code == 200, response.text
    action = response.json()['data']['action']
    assert action['actionType'] == 'propose_next_week_budget'
    assert action['status'] == 'proposed'
    assert db_session.scalar(select(func.count()).select_from(BudgetPlan)) == 1
    preview = action['payload']['preview']
    assert preview['totals']['proposed_planned_spend_cents'] == 7000000
    assert {item['category_id'] for item in preview['operations']} == {'rent','food','shopping'}

    edited = []
    for item in preview['operations']:
        edited.append({'categoryId':item['category_id'],
                       'proposedLimitCents':1200000 if item['category_id'] == 'food' else item['proposed_limit_cents'],
                       'reason':item['reason'], 'allowFixedReduction':item['allow_fixed_reduction']})
    result = client.patch(f"/api/chat/sessions/{sid}/actions/{action['id']}", json={'operations':edited})
    assert result.status_code == 200, result.text
    changed = result.json()['data']
    assert changed['payload']['preview']['totals']['proposed_planned_spend_cents'] == 6700000

    applied = decide(client, sid, action['id']).json()['data']
    assert applied['status'] == 'executed', applied
    plan_id = applied['payload']['result']['plan']['id']
    dashboard = client.get(f'/api/budget-plans/{plan_id}/summary').json()['data']
    assert dashboard['plannedSpendCents'] == 6700000
    assert len(dashboard['items']) == 3
    assert send(client, sid, '/undo').status_code == 200
    assert client.get(f'/api/budget-plans/{plan_id}').status_code == 404


def test_plan_cancel_and_stale_apply_do_not_mutate(client, app, db_session):
    _, target_start = make_weekly_baseline(db_session)
    sid = chat(client)
    app.state.agent_model = planner_stub(target_start)
    first = send(client, sid, 'Plan next week').json()['data']['action']
    assert decide(client, sid, first['id'], 'cancel').json()['data']['status'] == 'cancelled'
    assert db_session.scalar(select(func.count()).select_from(BudgetPlan)) == 1

    app.state.agent_model = planner_stub(target_start)
    second = send(client, sid, 'Plan next week again').json()['data']['action']
    previous = target_start - timedelta(days=14)
    budget.quick_expense(db_session, amount_cents=100000, category_id='food', currency='JPY', occurred_on=previous)
    db_session.commit()
    stale = decide(client, sid, second['id']).json()['data']
    assert stale['status'] == 'failed'
    assert 'changed' in stale['payload']['error']
    assert db_session.scalar(select(func.count()).select_from(BudgetPlan)) == 1


def test_plan_apply_is_atomic_on_child_failure(client, app, db_session, monkeypatch):
    _, target_start = make_weekly_baseline(db_session)
    app.state.agent_model = planner_stub(target_start)
    sid = chat(client)
    action = send(client, sid, 'Plan next week').json()['data']['action']
    original = tools.write
    def fail_after_first_change(session, name, args, source):
        if name != 'propose_next_week_budget':
            return original(session, name, args, source)
        target = budget.create_plan(session, period_type='week', starts_on=target_start, currency='JPY')
        budget.add_item(session, target.id, category_id='food', limit_cents=1)
        raise ValidationError('simulated child failure')
    monkeypatch.setattr(tools, 'write', fail_after_first_change)
    failed = decide(client, sid, action['id']).json()['data']
    assert failed['status'] == 'failed'
    assert budget.list_plans(db_session, period_type='week', start=target_start, end=target_start, currency='JPY') == []


def test_planner_requires_context_read_and_rejects_fixed_or_impossible_constraints(client, app, db_session):
    _, target_start = make_weekly_baseline(db_session)
    sid = chat(client)
    app.state.agent_model = StubModel({'name':'propose_next_week_budget','arguments':{
        'target_starts_on':str(target_start), 'summary':'No read',
        'operations':[{'category_id':'food','proposed_limit_cents':1000000,'reason':'Lower food'}]}})
    assert send(client, sid, 'Plan without reading').status_code == 400

    app.state.agent_model = StubModel(
        {'name':'get_budget_planning_context','arguments':{'history_weeks':4}},
        {'name':'propose_next_week_budget','arguments':{
            'target_starts_on':str(target_start), 'summary':'Reduce rent',
            'operations':[{'category_id':'rent','proposed_limit_cents':4000000,'reason':'Too high'}]}})
    assert send(client, sid, 'Reduce fixed rent').status_code == 400

    app.state.agent_model = StubModel(
        {'name':'get_budget_planning_context','arguments':{'history_weeks':4}},
        {'name':'propose_next_week_budget','arguments':{
            'target_starts_on':str(target_start), 'summary':'Impossible savings',
            'planned_income_cents':7000000, 'savings_target_cents':2000000,
            'operations':[{'category_id':'food','proposed_limit_cents':1500000,'reason':'Lower food'}]}})
    assert send(client, sid, 'Save more than possible').status_code == 400


def test_planner_explains_insufficient_history_without_proposal(client, app, db_session):
    _, _ = make_weekly_baseline(db_session)
    app.state.agent_model = StubModel(
        {'name':'get_budget_planning_context','arguments':{'history_weeks':4}},
        {'content':'I only have the current plan and no completed weekly history, so I need your preferred limits before proposing a stricter plan.'},
    )
    sid = chat(client)
    result = send(client, sid, 'Make next week stricter').json()['data']
    assert result['action'] is None
    assert 'no completed weekly history' in result['message']['content']


def test_help_is_deterministic_and_plan_command_uses_planner(client, app, db_session):
    _, target_start = make_weekly_baseline(db_session)
    sid = chat(client)
    app.state.agent_model = None
    help_result = send(client, sid, '/help').json()['data']
    assert help_result['action'] is None
    assert '/plan next-week' in help_result['message']['content']

    app.state.agent_model = planner_stub(target_start)
    planned = send(client, sid, '/plan next-week').json()['data']
    assert planned['action']['actionType'] == 'propose_next_week_budget'
    assert planned['action']['status'] == 'proposed'


def test_new_plan_proposal_supersedes_old_pending_plan(client, app, db_session):
    _, target_start = make_weekly_baseline(db_session)
    sid = chat(client)
    app.state.agent_model = planner_stub(target_start, food=1500000, shopping=500000)
    first = send(client, sid, 'Make next week stricter').json()['data']['action']

    # The revision intentionally mentions only Food. The service, rather than
    # the model, must carry Shopping ¥5,000 forward from the pending proposal.
    app.state.agent_model = StubModel(
        {'name':'get_budget_planning_context','arguments':{'history_weeks':4}},
        {'name':'propose_next_week_budget','arguments':{
            'target_starts_on':str(target_start), 'summary':'Lower Food and keep the rest.',
            'operations':[{'category_id':'food','proposed_limit_cents':1200000,'reason':'Lower food'}],
        }},
    )
    second = send(client, sid, 'Make Food 12,000 and keep the rest').json()['data']['action']
    restored = client.get(f'/api/chat/sessions/{sid}').json()['data']['actions']
    by_id = {action['id']: action for action in restored}
    assert by_id[first['id']]['status'] == 'cancelled'
    assert by_id[first['id']]['payload']['supersededBy'] == second['id']
    assert by_id[second['id']]['status'] == 'proposed'
    revised = {item['category_id']: item['proposed_limit_cents']
               for item in by_id[second['id']]['payload']['preview']['operations']}
    assert revised == {'rent':5000000, 'food':1200000, 'shopping':500000}
    assert db_session.scalar(select(func.count()).select_from(BudgetPlan)) == 1

    old_apply = decide(client, sid, first['id'])
    assert old_apply.status_code == 409
    applied = decide(client, sid, second['id']).json()['data']
    assert applied['status'] == 'executed'
    assert applied['payload']['preview']['totals']['proposed_planned_spend_cents'] == 6700000
