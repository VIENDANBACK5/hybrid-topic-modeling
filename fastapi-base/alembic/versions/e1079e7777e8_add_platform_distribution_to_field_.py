"""add_platform_distribution_to_field_statistics

Revision ID: e1079e7777e8
Revises: add_27_indicator_details
Create Date: 2026-01-16 20:32:16.101350

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e1079e7777e8"
down_revision: Union[str, None] = "add_27_indicator_details"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add platform_distribution column to field_statistics
    op.add_column("field_statistics", 
        sa.Column("platform_distribution", sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove platform_distribution column
    op.drop_column("field_statistics", "platform_distribution")
