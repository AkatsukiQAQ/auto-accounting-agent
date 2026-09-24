"""Real-file SQLite concurrency tests (separate connections, no paid model)."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from sqlalchemy import select, func
from backend.db.base import Base
from backend.db.models import ChatSession, Transaction
from backend.db.session import build_engine, build_session_factory
from backend.db.seeders.categories import seed_categories, ensure_system_categories
from backend.db.seeders.accounts import ensure_default_cash_account
from backend.services.agent import actions


def test_simultaneous_confirmations_execute_once(tmp_path):
    engine = build_engine(f"sqlite:///{(tmp_path / 'concurrent.db').as_posix()}")
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    with factory() as session:
        seed_categories(session)
        ensure_system_categories(session)
        ensure_default_cash_account(session)
        session.add(ChatSession(id='chat'))
        session.flush()
        proposal = actions.propose(session, 'chat', 'add_quick_expense', {
            'category_id':'food','amount_cents':180000,'currency':'JPY','occurred_on':'2026-01-01'})
        action_id = proposal.id
        session.commit()
    barrier = Barrier(2)
    def confirm():
        with factory() as session:
            barrier.wait(timeout=5)
            result = actions.decide(session, 'chat', action_id, 'apply')
            session.commit()
            return actions.action_out(result)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first, second = list(pool.map(lambda _: confirm(), range(2)))
        assert first == second
        assert first['status'] == 'executed'
        with factory() as session:
            assert session.scalar(select(func.count()).select_from(Transaction)) == 1
            assert session.scalar(select(Transaction.amount_cents)) == -180000
    finally:
        engine.dispose()
