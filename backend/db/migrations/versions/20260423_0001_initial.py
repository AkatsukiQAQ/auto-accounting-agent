"""initial schema — categories, transactions, user_settings

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-23

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("color_bg", sa.String(), nullable=False),
        sa.Column("color_dot", sa.String(), nullable=False),
        sa.Column("keywords", sa.JSON(), nullable=False),
        sa.Column("auto_assign", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categories")),
    )

    op.create_table(
        "transactions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("merchant", sa.String(), nullable=False),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("category_id", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("raw_image_url", sa.String(), nullable=True),
        sa.Column("raw_ocr_text", sa.Text(), nullable=True),
        sa.Column("raw_ocr_engine", sa.String(), nullable=True),
        sa.Column("raw_llm_model", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_transactions_category_id_categories"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transactions")),
    )
    op.create_index(
        op.f("ix_transactions_occurred_at"),
        "transactions",
        ["occurred_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_transactions_category_id"),
        "transactions",
        ["category_id"],
        unique=False,
    )

    op.create_table(
        "user_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_settings")),
    )


def downgrade() -> None:
    op.drop_table("user_settings")
    op.drop_index(op.f("ix_transactions_category_id"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_occurred_at"), table_name="transactions")
    op.drop_table("transactions")
    op.drop_table("categories")
