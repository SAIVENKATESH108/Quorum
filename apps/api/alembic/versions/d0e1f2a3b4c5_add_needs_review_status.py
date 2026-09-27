"""add_needs_review_status

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-09-27 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd0e1f2a3b4c5'
down_revision: Union[str, Sequence[str], None] = 'c9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adding a value to an enum in PostgreSQL must be executed outside a transaction block
    with op.get_context().autocommit_block():
        op.execute(sa.text("ALTER TYPE reportstatus ADD VALUE IF NOT EXISTS 'needs_review'"))


def downgrade() -> None:
    pass
