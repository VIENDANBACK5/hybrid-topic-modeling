"""add_par_sipas_new_fields

Revision ID: 20260120_par_sipas
Revises: 20260120_health_stats
Create Date: 2026-01-20 03:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260120_par_sipas'
down_revision: Union[str, None] = '20260120_health_stats'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add new fields to PAR Index and SIPAS tables."""
    # Add fields to par_index_detail
    op.add_column('par_index_detail', sa.Column('onestop_processing_rate', sa.Float(), nullable=True, comment='Tỷ lệ giải quyết đúng hạn (%)'))
    op.add_column('par_index_detail', sa.Column('simplified_procedures_count', sa.Integer(), nullable=True, comment='Số thủ tục được đơn giản hóa'))
    
    # Add field to sipas_detail
    op.add_column('sipas_detail', sa.Column('satisfaction_rate', sa.Float(), nullable=True, comment='Tỷ lệ hài lòng (%)'))


def downgrade() -> None:
    """Remove fields from PAR Index and SIPAS tables."""
    # Remove fields from sipas_detail
    op.drop_column('sipas_detail', 'satisfaction_rate')
    
    # Remove fields from par_index_detail
    op.drop_column('par_index_detail', 'simplified_procedures_count')
    op.drop_column('par_index_detail', 'onestop_processing_rate')
