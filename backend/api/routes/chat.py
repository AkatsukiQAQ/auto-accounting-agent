import json
from uuid import uuid4
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from backend.api.deps import get_session
from backend.api.schemas.chat import Decision, MessageInput, PlanProposalEdit, SessionUpdate
from backend.db.models import AgentAction, ChatMessage, ChatSession
from backend.services.agent import actions, orchestrator
from backend.services.agent.model import OpenAIAgentModel
from backend.services.errors import ApiKeyNotConfiguredError, NotFoundError
from backend.services.settings import get_settings

router = APIRouter(prefix='/api/chat', tags=['chat'])

def model_factory(request, session):
    def build():
        override = getattr(request.app.state, 'agent_model', None)
        if override is not None:
            return override
        key = (get_settings(session).get('apiKeys') or {}).get('openai')
        if not key:
            raise ApiKeyNotConfiguredError('Configure the OpenAI key in Settings, or use deterministic slash commands.')
        return OpenAIAgentModel(key, request.app.state.config.agent_model)
    return build


@router.get('/sessions')
def sessions(session: Session = Depends(get_session)):
    first_user_message = (
        select(ChatMessage.content)
        .where(ChatMessage.session_id == ChatSession.id, ChatMessage.role == 'user')
        .order_by(ChatMessage.created_at, ChatMessage.id)
        .limit(1)
        .scalar_subquery()
    )
    rows = session.execute(
        select(ChatSession, first_user_message.label('title'))
        .order_by(ChatSession.created_at.desc(), ChatSession.id.desc())
        .limit(50)
    )
    return {'data': [{
        'id': row.id,
        'createdAt': row.created_at.isoformat(),
        'title': row.title or _session_title(title),
    } for row, title in rows]}


def _session_title(content: str | None) -> str:
    if not content:
        return 'New chat'
    compact = ' '.join(content.split())
    return compact if len(compact) <= 48 else f'{compact[:47]}…'


@router.post('/sessions', status_code=201)
def create(session: Session = Depends(get_session)):
    row = ChatSession(id=str(uuid4()))
    session.add(row)
    session.commit()
    return {'data': {'id': row.id}}


@router.patch('/sessions/{session_id}')
def rename(session_id: str, body: SessionUpdate, session: Session = Depends(get_session)):
    row = session.get(ChatSession, session_id)
    if row is None:
        raise NotFoundError('Chat session not found')
    row.title = body.title
    session.commit()
    return {'data': {'id': row.id, 'title': row.title, 'createdAt': row.created_at.isoformat()}}


@router.delete('/sessions/{session_id}', status_code=204)
def delete_session(session_id: str, session: Session = Depends(get_session)):
    row = session.get(ChatSession, session_id)
    if row is None:
        raise NotFoundError('Chat session not found')
    session.execute(delete(AgentAction).where(AgentAction.session_id == session_id))
    session.execute(delete(ChatMessage).where(ChatMessage.session_id == session_id))
    session.delete(row)
    session.commit()


@router.get('/sessions/{session_id}')
def get(session_id: str, session: Session = Depends(get_session)):
    return {'data': orchestrator.history(session, session_id)}


@router.post('/sessions/{session_id}/messages')
def send(session_id: str, body: MessageInput, request: Request, session: Session = Depends(get_session)):
    events = list(orchestrator.run(session, session_id, body.content, model_factory(request, session)))
    return {'data': events[-1]}


@router.post('/sessions/{session_id}/stream')
def stream(session_id: str, body: MessageInput, request: Request):
    # Own the session for the lifetime of the response iterator (including disconnect).
    def events():
        with request.app.state.session_factory() as session:
            try:
                for event in orchestrator.run(session, session_id, body.content, model_factory(request, session)):
                    yield json.dumps(event) + '\n'
            except Exception as exc:
                session.rollback()
                from backend.services.errors import ServiceError
                text = str(exc) if isinstance(exc, ServiceError) else 'Chat request failed. Please retry.'
                yield json.dumps({'type': 'error', 'message': text}) + '\n'
    return StreamingResponse(events(), media_type='application/x-ndjson', headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@router.post('/sessions/{session_id}/actions/{action_id}')
def decide(session_id: str, action_id: str, body: Decision, session: Session = Depends(get_session)):
    row = actions.decide(session, session_id, action_id, body.decision)
    session.commit()
    return {'data': actions.action_out(row)}


@router.patch('/sessions/{session_id}/actions/{action_id}')
def edit(session_id: str, action_id: str, body: PlanProposalEdit,
         session: Session = Depends(get_session)):
    row = actions.edit_plan_proposal(session, session_id, action_id,
                                     body.model_dump(mode='json', exclude_unset=True))
    session.commit()
    return {'data': actions.action_out(row)}
