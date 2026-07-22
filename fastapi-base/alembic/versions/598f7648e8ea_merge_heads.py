"""merge heads

Revision ID: 598f7648e8ea
Revises: 061547e4fa95, 78fa2a5f8720
Create Date: 2025-12-05 13:44:34.656741

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '598f7648e8ea'
down_revision: Union[str, None] = ('061547e4fa95', '78fa2a5f8720')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
