"""Add optional category icon metadata and local custom-image references."""
import sqlalchemy as sa
from alembic import op

revision = "0007_category_icons"
down_revision = "0006_budget_core"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("categories") as batch:
        batch.add_column(sa.Column("icon", sa.String(length=16), nullable=True))
        batch.add_column(sa.Column("icon_image_url", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("categories") as batch:
        batch.drop_column("icon_image_url")
        batch.drop_column("icon")
