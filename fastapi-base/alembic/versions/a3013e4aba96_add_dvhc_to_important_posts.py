"""add_dvhc_to_important_posts

Revision ID: a3013e4aba96
Revises: ba934abe4742
Create Date: 2026-01-20 10:20:21.710011

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3013e4aba96'
down_revision: Union[str, None] = 'ba934abe4742'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
