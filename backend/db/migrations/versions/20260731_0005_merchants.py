"""merchants + merchant_aliases; re-normalize historical merchants

Revision ID: 0005_merchants
Revises: 0004_seed_transfer_category
Create Date: 2026-07-31

Backfill: re-runs normalization over every transaction and overwrites
`merchant_normalized` AND the compat `merchant` column (PHASE_2.md §Extend
transactions — from Phase 2 on, `merchant` always holds the normalized name).
At migration time the alias and brand tables are empty (brand seeds load at
next boot), so strip+title-case IS the full engine — we import only the pure
`strippers` module, never DB-dependent service code. Prints a changed-row
count so a bulk rewrite mid-dogfooding is diagnosable.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.services.normalization.strippers import strip_location, title_case_if_shouty

revision: str = "0005_merchants"
down_revision: Union[str, None] = "0004_seed_transfer_category"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "merchants",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("canonical_name", sa.String(), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=False),
        sa.Column("default_category_id", sa.String(), nullable=True),
        sa.Column("logo_url", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source IN ('seed','user','learned')", name=op.f("ck_merchants_source")
        ),
        sa.ForeignKeyConstraint(
            ["default_category_id"],
            ["categories.id"],
            name=op.f("fk_merchants_default_category_id_categories"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_merchants")),
    )

    op.create_table(
        "merchant_aliases",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("raw_pattern", sa.String(), nullable=False),
        sa.Column("match_type", sa.String(), nullable=False),
        sa.Column("merchant_id", sa.String(), nullable=False),
        sa.Column("applied_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "match_type IN ('contains','exact','regex')",
            name=op.f("ck_merchant_aliases_match_type"),
        ),
        sa.ForeignKeyConstraint(
            ["merchant_id"],
            ["merchants.id"],
            name=op.f("fk_merchant_aliases_merchant_id_merchants"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_merchant_aliases")),
    )

    # Backfill: strip-normalize every historical row.
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, merchant, merchant_raw, merchant_normalized FROM transactions")
    ).fetchall()
    changed = 0
    for row_id, merchant, merchant_raw, merchant_normalized in rows:
        raw = merchant_raw or merchant or ""
        normalized = title_case_if_shouty(strip_location(raw)) if raw else merchant
        if normalized != merchant_normalized or normalized != merchant:
            bind.execute(
                sa.text(
                    "UPDATE transactions SET merchant_normalized = :n, merchant = :n "
                    "WHERE id = :id"
                ),
                {"n": normalized, "id": row_id},
            )
            changed += 1
    print(f"0005_merchants: re-normalized {changed} of {len(rows)} transaction rows")


def downgrade() -> None:
    # merchant/merchant_normalized rewrites are NOT reverted (original values
    # survive in merchant_raw).
    op.drop_table("merchant_aliases")
    op.drop_table("merchants")
