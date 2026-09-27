"""add_guest_sessions_and_demo_flags

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-09-26 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, Sequence[str], None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add is_guest_demo column to projects and reports
    op.add_column(
        'projects',
        sa.Column('is_guest_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False)
    )
    op.create_index('ix_projects_is_guest_demo', 'projects', ['is_guest_demo'], unique=False)

    op.add_column(
        'reports',
        sa.Column('is_guest_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False)
    )
    op.create_index('ix_reports_is_guest_demo', 'reports', ['is_guest_demo'], unique=False)

    # 2. Create guest_sessions table
    op.create_table(
        'guest_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_type', sa.String(length=20), server_default='guest', nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_agent', sa.String(length=256), nullable=True),
        sa.CheckConstraint("session_type = 'guest'", name='chk_guest_session_type')
    )
    op.create_index('ix_guest_sessions_user_id', 'guest_sessions', ['user_id'], unique=False)
    op.create_index('ix_guest_sessions_expires_at', 'guest_sessions', ['expires_at'], unique=False)
    op.create_index('ix_guest_sessions_revoked_at', 'guest_sessions', ['revoked_at'], unique=False)
    op.create_index('ix_guest_sessions_lookup', 'guest_sessions', ['id', 'user_id', 'revoked_at', 'expires_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_guest_sessions_lookup', table_name='guest_sessions')
    op.drop_index('ix_guest_sessions_revoked_at', table_name='guest_sessions')
    op.drop_index('ix_guest_sessions_expires_at', table_name='guest_sessions')
    op.drop_index('ix_guest_sessions_user_id', table_name='guest_sessions')
    op.drop_table('guest_sessions')

    op.drop_index('ix_reports_is_guest_demo', table_name='reports')
    op.drop_column('reports', 'is_guest_demo')

    op.drop_index('ix_projects_is_guest_demo', table_name='projects')
    op.drop_column('projects', 'is_guest_demo')
