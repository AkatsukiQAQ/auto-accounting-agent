"""seed the `transfer` system category

Revision ID: 0004_seed_transfer_category
Revises: 0003_transactions_extend
Create Date: 2026-07-31

The lifespan seeder (`ensure_system_categories`) also inserts this on boot for
create_all databases; this migration covers alembic-managed databases so the
transfer service can rely on the slug existing right after `upgrade head`.
Idempotent (INSERT OR IGNORE). Values mirror `backend/db/seeders/categories.py`
— neutral ink greys, auto_assign=False keeps it out of the classifier.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_seed_transfer_category"
down_revision: Union[str, None] = "0003_transactions_extend"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "INSERT OR IGNORE INTO categories "
            "(id, label, color_bg, color_dot, keywords, auto_assign, sort_order, created_at) "
            "VALUES ('transfer', 'Transfer', '#E5DED0', '#6B5E4E', '[]', 0, 100, :now)"
        ),
        {"now": datetime.now(timezone.utc).isoformat(sep=" ")},
    )


def downgrade() -> None:
    bind = op.get_bind()
    referenced = bind.execute(
        sa.text("SELECT COUNT(*) FROM transactions WHERE category_id = 'transfer'")
    ).scalar()
    if referenced:
        raise RuntimeError(
            f"cannot remove 'transfer' category: {referenced} transaction(s) reference it"
        )
    bind.execute(sa.text("DELETE FROM categories WHERE id = 'transfer'"))
