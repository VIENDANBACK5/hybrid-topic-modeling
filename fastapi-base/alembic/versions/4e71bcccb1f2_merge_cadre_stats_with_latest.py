"""merge cadre stats with latest

Revision ID: 4e71bcccb1f2
Revises: 20260119_add_cadre_stats, e1079e7777e8
Create Date: 2026-01-19 11:22:37.674869

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e71bcccb1f2'
down_revision: Union[str, None] = ('20260119_add_cadre_stats', 'e1079e7777e8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
