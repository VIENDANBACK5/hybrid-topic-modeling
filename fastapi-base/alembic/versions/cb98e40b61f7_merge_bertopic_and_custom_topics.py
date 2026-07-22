"""merge bertopic and custom topics

Revision ID: cb98e40b61f7
Revises: 520703b2107c, add_bertopic_discovered
Create Date: 2026-01-04 05:16:34.457350

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cb98e40b61f7'
down_revision: Union[str, None] = ('520703b2107c', 'add_bertopic_discovered')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
