"""extend transactions — account_id, type, transfer/recurring links, merchant split

Revision ID: 0003_transactions_extend
Revises: 0002_accounts
Create Date: 2026-07-31

Backfills a default `Cash` account (currency = profile defaultCurrency, JPY
fallback) and points every existing row at it, copies `merchant` into
`merchant_raw` / `merchant_normalized` (re-normalization happens in
0005_merchants), then tightens `account_id` to NOT NULL.

SQLite notes:
- New columns use native ADD COLUMN (nullable / constant default — no rebuild).
- The NOT NULL tighten + new FK/CHECK need one "move and copy" rebuild; we pass
  an explicit `copy_from` because SQLite reflection silently drops CHECK
  constraints, and alembic's env runs without `PRAGMA foreign_keys`, which is
  exactly what the copy needs.
- Timestamps are bound as Python-formatted strings matching SQLAlchemy's
  storage format, since `now()` doesn't exist on SQLite.

Downgrade is destructive: it drops the new columns but keeps the default Cash
account row (0002's downgrade removes the whole table) and cannot restore
which account each row belonged to.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_transactions_extend"
down_revision: Union[str, None] = "0002_accounts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CASH_ID = "acc_cash_default"

_TYPE_CHECK = "type IN ('normal','transfer_out','transfer_in','recurring')"


def _transactions_copy_from() -> sa.Table:
    """The table exactly as it exists AFTER the plain ADD COLUMNs below —
    including everything 0001 created, so the rebuild loses nothing."""
    metadata = sa.MetaData()
    return sa.Table(
        "transactions",
        metadata,
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("merchant", sa.String(), nullable=False),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("category_id", sa.String(), nullable=False, index=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("raw_image_url", sa.String(), nullable=True),
        sa.Column("raw_ocr_text", sa.Text(), nullable=True),
        sa.Column("raw_ocr_engine", sa.String(), nullable=True),
        sa.Column("raw_llm_model", sa.String(), nullable=True),
        sa.Column("account_id", sa.String(), nullable=True, index=True),
        sa.Column("type", sa.String(), server_default="normal", nullable=False),
        sa.Column("transfer_group_id", sa.String(), nullable=True, index=True),
        sa.Column("recurring_rule_id", sa.String(), nullable=True),
        sa.Column("merchant_raw", sa.Text(), nullable=True),
        sa.Column("merchant_normalized", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name="fk_transactions_category_id_categories",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_transactions"),
    )


def _now_str() -> str:
    # Matches SQLAlchemy's SQLite storage format for DateTime(timezone=True).
    return datetime.now(timezone.utc).isoformat(sep=" ")


def upgrade() -> None:
    # 1. Native ADD COLUMN — nullable or constant-default only, no rebuild.
    op.add_column("transactions", sa.Column("account_id", sa.String(), nullable=True))
    op.add_column(
        "transactions",
        sa.Column("type", sa.String(), server_default="normal", nullable=False),
    )
    op.add_column("transactions", sa.Column("transfer_group_id", sa.String(), nullable=True))
    op.add_column("transactions", sa.Column("recurring_rule_id", sa.String(), nullable=True))
    op.add_column("transactions", sa.Column("merchant_raw", sa.Text(), nullable=True))
    op.add_column("transactions", sa.Column("merchant_normalized", sa.Text(), nullable=True))

    # 2. Data backfill.
    bind = op.get_bind()

    default_currency = "JPY"
    settings_row = bind.execute(sa.text("SELECT data FROM user_settings LIMIT 1")).fetchone()
    if settings_row and settings_row[0]:
        raw = settings_row[0]
        data = raw if isinstance(raw, dict) else json.loads(raw)
        default_currency = (data.get("profile") or {}).get("defaultCurrency") or "JPY"

    bind.execute(
        sa.text(
            "INSERT OR IGNORE INTO accounts "
            "(id, name, kind, currency, balance_cents, opening_balance_cents,"
            " institution, color, archived, sort_order, created_at) "
            "VALUES (:id, 'Cash', 'cash', :ccy, 0, 0, NULL, NULL, 0, 0, :now)"
        ),
        {"id": CASH_ID, "ccy": default_currency, "now": _now_str()},
    )
    bind.execute(
        sa.text("UPDATE transactions SET account_id = :id WHERE account_id IS NULL"),
        {"id": CASH_ID},
    )
    bind.execute(sa.text("UPDATE transactions SET merchant_raw = merchant WHERE merchant_raw IS NULL"))
    bind.execute(
        sa.text(
            "UPDATE transactions SET merchant_normalized = merchant "
            "WHERE merchant_normalized IS NULL"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE accounts SET balance_cents = opening_balance_cents + COALESCE("
            "(SELECT SUM(amount_cents) FROM transactions"
            " WHERE transactions.account_id = accounts.id), 0) "
            "WHERE id = :id"
        ),
        {"id": CASH_ID},
    )

    # 3. One rebuild: NOT NULL tighten + account FK + type CHECK.
    with op.batch_alter_table("transactions", copy_from=_transactions_copy_from()) as batch_op:
        batch_op.alter_column("account_id", existing_type=sa.String(), nullable=False)
        batch_op.create_foreign_key(
            "fk_transactions_account_id_accounts", "accounts", ["account_id"], ["id"]
        )
        batch_op.create_check_constraint("ck_transactions_type", _TYPE_CHECK)

    # 4. The move-and-copy rebuild does NOT carry indexes over (verified on a
    # live-DB copy) — recreate 0001's two and add the two new ones.
    op.create_index(op.f("ix_transactions_occurred_at"), "transactions", ["occurred_at"], unique=False)
    op.create_index(op.f("ix_transactions_category_id"), "transactions", ["category_id"], unique=False)
    op.create_index(op.f("ix_transactions_account_id"), "transactions", ["account_id"], unique=False)
    op.create_index(
        op.f("ix_transactions_transfer_group_id"),
        "transactions",
        ["transfer_group_id"],
        unique=False,
    )


def downgrade() -> None:
    # Rebuild back to the Phase-1 shape (drops FK/CHECK and the six columns).
    with op.batch_alter_table("transactions", copy_from=_transactions_copy_from()) as batch_op:
        batch_op.drop_column("merchant_normalized")
        batch_op.drop_column("merchant_raw")
        batch_op.drop_column("recurring_rule_id")
        batch_op.drop_column("transfer_group_id")
        batch_op.drop_column("type")
        batch_op.drop_column("account_id")
