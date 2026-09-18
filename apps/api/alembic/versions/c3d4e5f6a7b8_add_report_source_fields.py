"""add report source fields

Revision ID: c3d4e5f6a7b8
Revises: b1c2d3e4f5a6
Create Date: 2026-09-18 23:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add source metadata used by report ingestion and PDF generation."""
    op.add_column(
        "reports",
        sa.Column("source_type", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "reports",
        sa.Column("source_ref", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Remove report source metadata."""
    op.drop_column("reports", "source_ref")
    op.drop_column("reports", "source_type")
