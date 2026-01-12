"""initial_schema

Revision ID: a27dff25ce0f
Revises: 
Create Date: 2026-01-12 10:22:22.258539

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a27dff25ce0f'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create sessions and turns tables."""
    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('session_id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('language', sa.String(10), nullable=False),
        sa.Column('mode', sa.String(20), nullable=False),
        sa.Column('total_turns', sa.Integer(), default=0),
        sa.Column('last_activity_at', sa.DateTime(), nullable=False),
    )
    # Create index on last_activity_at for cleanup queries
    op.create_index('idx_sessions_last_activity', 'sessions', ['last_activity_at'])

    # Create turns table
    op.create_table(
        'turns',
        sa.Column('turn_id', sa.String(36), primary_key=True),
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('transcript', sa.Text(), nullable=True),
        sa.Column('reply_text', sa.Text(), nullable=True),
        sa.Column('audio_path', sa.String(500), nullable=True),
        sa.Column('audio_duration_ms', sa.Integer(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('route', sa.String(50), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.session_id'], ondelete='CASCADE'),
    )
    # Create indexes for efficient queries
    op.create_index('idx_turns_session_id', 'turns', ['session_id'])
    op.create_index('idx_turns_timestamp', 'turns', ['timestamp'])


def downgrade() -> None:
    """Drop sessions and turns tables."""
    op.drop_index('idx_turns_timestamp', table_name='turns')
    op.drop_index('idx_turns_session_id', table_name='turns')
    op.drop_table('turns')

    op.drop_index('idx_sessions_last_activity', table_name='sessions')
    op.drop_table('sessions')
