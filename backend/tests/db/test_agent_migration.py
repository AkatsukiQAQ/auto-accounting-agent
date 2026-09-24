from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from backend.db.session import build_engine


def test_agent_migration_forward_and_reverse(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'agent-migration.db').as_posix()}"
    monkeypatch.setenv('DATABASE_URL', url)
    config = Config('alembic.ini')
    command.upgrade(config, '0007_category_icons')
    engine = build_engine(url)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO budget_plans (id,period_type,starts_on,ends_on,currency,status,created_by) VALUES ('keep','month','2026-09-01','2026-09-30','JPY','active','user')"))
    command.upgrade(config, 'head')
    with engine.begin() as connection:
        assert {'chat_sessions','chat_messages','agent_actions'} <= set(inspect(connection).get_table_names())
        assert 'title' in {column['name'] for column in inspect(connection).get_columns('chat_sessions')}
        connection.execute(text("INSERT INTO chat_sessions (id,title) VALUES ('s','Planning')"))
        connection.execute(text("INSERT INTO agent_actions (id,session_id,action_type,payload_json,status) VALUES ('a','s','test','{}','cancelled')"))
        assert connection.scalar(text("SELECT currency FROM budget_plans WHERE id='keep'")) == 'JPY'
        assert connection.execute(text('PRAGMA foreign_key_check')).all() == []
    command.downgrade(config, '0007_category_icons')
    with engine.connect() as connection:
        assert 'agent_actions' not in inspect(connection).get_table_names()
        assert connection.scalar(text("SELECT currency FROM budget_plans WHERE id='keep'")) == 'JPY'
    command.upgrade(config, 'head')
    engine.dispose()
