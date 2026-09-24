"""Persistent chat and structured agent action audit."""
from alembic import op
import sqlalchemy as sa
revision = '0008_agent_core'
down_revision = '0007_category_icons'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('chat_sessions', sa.Column('id', sa.String(), primary_key=True),
                    sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.create_table('chat_messages', sa.Column('id', sa.String(), primary_key=True),
        sa.Column('session_id', sa.String(), sa.ForeignKey('chat_sessions.id'), nullable=False),
        sa.Column('role', sa.String(), nullable=False), sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.create_index('ix_chat_messages_session_id', 'chat_messages', ['session_id'])
    op.create_table('agent_actions', sa.Column('id', sa.String(), primary_key=True),
        sa.Column('session_id', sa.String(), sa.ForeignKey('chat_sessions.id'), nullable=False),
        sa.Column('action_type', sa.String(), nullable=False), sa.Column('payload_json', sa.Text(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('executed_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint("status IN ('proposed','confirmed','executed','cancelled','failed')", name='action_status'))
    op.create_index('ix_agent_actions_session_id', 'agent_actions', ['session_id'])


def downgrade():
    op.drop_table('agent_actions')
    op.drop_table('chat_messages')
    op.drop_table('chat_sessions')
