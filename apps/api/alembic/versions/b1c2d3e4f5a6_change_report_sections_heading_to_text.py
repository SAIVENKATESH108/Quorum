"""change report_sections heading to Text

Revision ID: b1c2d3e4f5a6
Revises: f32881a23e1a
Create Date: 2026-09-16 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "f32881a23e1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Change heading column from VARCHAR(255) to TEXT to support long AI-generated headings."""
    op.alter_column(
        "report_sections",
        "heading",
        existing_type=sa.String(255),
        type_=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Revert heading column from TEXT back to VARCHAR(255)."""
    op.alter_column(
        "report_sections",
        "heading",
        existing_type=sa.Text(),
        type_=sa.String(255),
        existing_nullable=False,
    )
