"""merge_important_posts_and_security

Revision ID: ba934abe4742
Revises: 20260120_important_posts, 20260120_security_detail
Create Date: 2026-01-20 10:16:17.840288

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ba934abe4742'
down_revision: Union[str, None] = ('20260120_important_posts', '20260120_security_detail')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
