"""merge_all_heads

Revision ID: 520703b2107c
Revises: add_engagement_social_location, hitl_tables_001, add_statistics_tables, add_trend_tables
Create Date: 2026-01-03 03:09:04.048565

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '520703b2107c'
down_revision: Union[str, None] = ('add_engagement_social_location', 'hitl_tables_001', 'add_statistics_tables', 'add_trend_tables')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
