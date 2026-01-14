"""merge_grdp_heads

Revision ID: de3c11d7b74a
Revises: add_grdp_detail, simplify_grdp_001
Create Date: 2026-01-14 02:42:06.373855

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de3c11d7b74a'
down_revision: Union[str, None] = ('add_grdp_detail', 'simplify_grdp_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
