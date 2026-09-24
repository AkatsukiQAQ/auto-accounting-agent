from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from backend.db.session import build_engine


def test_forward_migration_preserves_records(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config("alembic.ini")
    command.upgrade(config, "0005_merchants")
    engine = build_engine(url)
    with engine.begin() as conn:
        account = conn.scalar(text("SELECT id FROM accounts LIMIT 1"))
        conn.execute(text("INSERT INTO categories (id,label,color_bg,color_dot,keywords,auto_assign,sort_order) VALUES ('food','Food','#ffffff','#000000','[]',1,0)"))
        conn.execute(text("INSERT INTO transactions (id,occurred_at,merchant,amount_cents,currency,category_id,source,account_id,type,note) VALUES ('legacy','2026-01-10','Original shop',-12300,'JPY','food','photo',:account,'normal','Keep me')"), {"account":account})
    command.upgrade(config, "head")
    with engine.begin() as conn:
        row = conn.execute(text("SELECT merchant, amount_cents, source, note, granularity FROM transactions WHERE id='legacy'")).one()
        assert tuple(row) == ("Original shop", -12300, "photo", "Keep me", "transaction")
        assert conn.execute(text("PRAGMA foreign_key_check")).all() == []
        assert {"budget_plans", "budget_items"}.issubset(inspect(conn).get_table_names())
        assert next(c for c in inspect(conn).get_columns('transactions') if c['name'] == 'merchant')['nullable']
    command.downgrade(config, "0005_merchants")
    command.upgrade(config, "head")
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT amount_cents FROM transactions WHERE id='legacy'")) == -12300
    engine.dispose()


def test_fresh_migrated_database_boots(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from backend.api.config import AppConfig
    from backend.api.main import create_app
    url = f"sqlite:///{(tmp_path / 'fresh.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    command.upgrade(Config("alembic.ini"), "head")
    app = create_app(AppConfig(database_url=url, image_storage_dir=tmp_path / 'images'))
    with TestClient(app) as client:
        categories = client.get('/api/categories').json()['data']
        assert 'food' in {c['id'] for c in categories}
        assert client.get('/api/budget-plans').json()['data'] == []
