"""V2 Budget Core; preserve existing transaction data and metadata."""
import sqlalchemy as sa
from alembic import op

revision = "0006_budget_core"
down_revision = "0005_merchants"
branch_labels = None
depends_on = None


def timestamps():
    return [sa.Column(name, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
            for name in ("created_at", "updated_at")]


def upgrade():
    op.create_table(
        "budget_plans",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("period_type", sa.String(), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("planned_income_cents", sa.BigInteger()),
        sa.Column("savings_target_cents", sa.BigInteger()),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("note", sa.Text()),
        sa.Column("created_by", sa.String(), nullable=False, server_default="user"),
        *timestamps(),
        sa.UniqueConstraint("period_type", "starts_on", "currency"),
        sa.CheckConstraint("period_type IN ('week','month')", name="period_type"),
        sa.CheckConstraint("status IN ('draft','active','closed')", name="status"),
        sa.CheckConstraint("created_by IN ('user','agent','template')", name="created_by"),
        sa.CheckConstraint("ends_on >= starts_on", name="dates"),
        sa.CheckConstraint("planned_income_cents >= 0", name="income"),
        sa.CheckConstraint("savings_target_cents >= 0", name="savings"),
    )
    op.create_table(
        "budget_items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("plan_id", sa.String(), sa.ForeignKey("budget_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", sa.String(), sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("limit_cents", sa.BigInteger(), nullable=False),
        sa.Column("warning_ratio", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("kind", sa.String(), nullable=False, server_default="flexible"),
        sa.Column("note", sa.Text()),
        *timestamps(),
        sa.UniqueConstraint("plan_id", "category_id"),
        sa.CheckConstraint("limit_cents >= 0", name="limit"),
        sa.CheckConstraint("warning_ratio > 0 AND warning_ratio <= 1", name="warning_ratio"),
        sa.CheckConstraint("kind IN ('fixed','flexible','discretionary')", name="kind"),
    )
    with op.batch_alter_table("transactions") as batch:
        batch.alter_column("merchant", existing_type=sa.String(), nullable=True)
        batch.add_column(sa.Column("granularity", sa.String(), nullable=False, server_default="transaction"))


def downgrade():
    # Do not invent merchant names or destroy merchant-less entries on rollback.
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM transactions WHERE merchant IS NULL")):
        raise RuntimeError("Remove merchant-less V2 entries before downgrading Budget Core")
    with op.batch_alter_table("transactions") as batch:
        batch.drop_column("granularity")
        batch.alter_column("merchant", existing_type=sa.String(), nullable=False)
    op.drop_table("budget_items")
    op.drop_table("budget_plans")
