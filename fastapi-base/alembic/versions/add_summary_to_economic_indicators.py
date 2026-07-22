"""add summary field to economic indicators

Revision ID: add_summary_economic_ind
Revises: add_economic_indicators
Create Date: 2026-01-09 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_summary_economic_ind'
down_revision: Union[str, None] = 'add_economic_indicators'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add summary column to economic_indicators table"""
    op.add_column('economic_indicators', 
                  sa.Column('summary', sa.Text(), nullable=True,
                           comment='Tóm tắt ngắn về tình hình kinh tế kỳ này'))


def downgrade() -> None:
    """Remove summary column from economic_indicators table"""
    op.drop_column('economic_indicators', 'summary')
