"""add_code_provenance_to_rag_chunks

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-09-25 23:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('rag_chunks', sa.Column('repo_identifier', sa.String(length=256), nullable=True))
    op.add_column('rag_chunks', sa.Column('commit_sha', sa.String(length=64), nullable=True))
    op.add_column('rag_chunks', sa.Column('relative_path', sa.String(length=1024), nullable=True))
    op.add_column('rag_chunks', sa.Column('symbol_name', sa.String(length=256), nullable=True))
    op.add_column('rag_chunks', sa.Column('symbol_type', sa.String(length=64), nullable=True))
    op.add_column('rag_chunks', sa.Column('start_line', sa.Integer(), nullable=True))
    op.add_column('rag_chunks', sa.Column('end_line', sa.Integer(), nullable=True))
    op.add_column('rag_chunks', sa.Column('is_ast', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('rag_chunks', sa.Column('chunk_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    op.create_index('ix_rag_chunks_repo_identifier', 'rag_chunks', ['repo_identifier'], unique=False)
    op.create_index('ix_rag_chunks_commit_sha', 'rag_chunks', ['commit_sha'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_rag_chunks_commit_sha', table_name='rag_chunks')
    op.drop_index('ix_rag_chunks_repo_identifier', table_name='rag_chunks')

    op.drop_column('rag_chunks', 'chunk_metadata')
    op.drop_column('rag_chunks', 'is_ast')
    op.drop_column('rag_chunks', 'end_line')
    op.drop_column('rag_chunks', 'start_line')
    op.drop_column('rag_chunks', 'symbol_type')
    op.drop_column('rag_chunks', 'symbol_name')
    op.drop_column('rag_chunks', 'relative_path')
    op.drop_column('rag_chunks', 'commit_sha')
    op.drop_column('rag_chunks', 'repo_identifier')
