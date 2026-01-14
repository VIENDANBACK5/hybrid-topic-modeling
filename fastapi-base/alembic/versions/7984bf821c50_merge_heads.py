"""merge_heads

Revision ID: 7984bf821c50
Revises: add_field_summaries, cb98e40b61f7
Create Date: 2026-01-08 10:47:19.523062

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7984bf821c50'
down_revision: Union[str, None] = ('add_field_summaries', 'cb98e40b61f7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
