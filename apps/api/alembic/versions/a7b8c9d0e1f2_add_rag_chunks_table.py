"""add_rag_chunks_table

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-09-25 23:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure pgvector extension is present
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    op.create_table(
        'rag_chunks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('chunk_id', sa.String(length=64), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('report_id', sa.UUID(), nullable=True),
        sa.Column('report_section_id', sa.UUID(), nullable=True),
        sa.Column('source_id', sa.UUID(), nullable=True),
        sa.Column('document_type', sa.String(length=64), nullable=False, server_default='report_section'),
        sa.Column('source_type', sa.String(length=64), nullable=False, server_default='report'),
        sa.Column('access_level', sa.String(length=32), nullable=False, server_default='full_text'),
        sa.Column('source_title', sa.String(length=512), nullable=True),
        sa.Column('source_url', sa.String(length=2048), nullable=True),
        sa.Column('heading_hierarchy', sa.String(length=512), nullable=True),
        sa.Column('page_or_line_range', sa.String(length=100), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('redaction_applied', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('redaction_categories', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=1536), nullable=False),
        sa.Column('embedding_provider', sa.String(length=64), nullable=False),
        sa.Column('embedding_model', sa.String(length=128), nullable=False),
        sa.Column('embedding_dimension', sa.Integer(), nullable=False, server_default='1536'),
        sa.Column('chunking_strategy', sa.String(length=64), nullable=False, server_default='heading_aware'),
        sa.Column('chunking_version', sa.String(length=32), nullable=False, server_default='v1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['report_section_id'], ['report_sections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rag_chunks_chunk_id'), 'rag_chunks', ['chunk_id'], unique=True)
    op.create_index(op.f('ix_rag_chunks_project_id'), 'rag_chunks', ['project_id'], unique=False)
    op.create_index(op.f('ix_rag_chunks_report_id'), 'rag_chunks', ['report_id'], unique=False)
    op.create_index(op.f('ix_rag_chunks_report_section_id'), 'rag_chunks', ['report_section_id'], unique=False)
    op.create_index(op.f('ix_rag_chunks_source_id'), 'rag_chunks', ['source_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_rag_chunks_source_id'), table_name='rag_chunks')
    op.drop_index(op.f('ix_rag_chunks_report_section_id'), table_name='rag_chunks')
    op.drop_index(op.f('ix_rag_chunks_report_id'), table_name='rag_chunks')
    op.drop_index(op.f('ix_rag_chunks_project_id'), table_name='rag_chunks')
    op.drop_index(op.f('ix_rag_chunks_chunk_id'), table_name='rag_chunks')
    op.drop_table('rag_chunks')
