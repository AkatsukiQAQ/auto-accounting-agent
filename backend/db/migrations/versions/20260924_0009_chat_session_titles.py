"""Persist user-defined chat session titles."""
from alembic import op
import sqlalchemy as sa

revision = '0009_chat_session_titles'
down_revision = '0008_agent_core'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('chat_sessions', sa.Column('title', sa.String(length=80), nullable=True))


def downgrade():
    op.drop_column('chat_sessions', 'title')
