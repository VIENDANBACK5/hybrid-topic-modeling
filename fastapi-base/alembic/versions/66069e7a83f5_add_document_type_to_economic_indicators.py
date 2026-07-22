"""add document_type to economic indicators

Revision ID: 66069e7a83f5
Revises: 20260130_doc_type_details
Create Date: 2026-01-31 04:24:43.861168

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '66069e7a83f5'
down_revision: Union[str, None] = '20260130_doc_type_details'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
