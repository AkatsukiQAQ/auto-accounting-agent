"""accounts table — Phase 2 ledger base

Revision ID: 0002_accounts
Revises: 0001_initial
Create Date: 2026-07-31

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_accounts"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("balance_cents", sa.BigInteger(), nullable=False),
        sa.Column("opening_balance_cents", sa.BigInteger(), nullable=False),
        sa.Column("institution", sa.String(), nullable=True),
        sa.Column("color", sa.String(), nullable=True),
        sa.Column("archived", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "kind IN ('checking','savings','credit','cash','investment','other')",
            name=op.f("ck_accounts_kind"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_accounts")),
    )


def downgrade() -> None:
    op.drop_table("accounts")
