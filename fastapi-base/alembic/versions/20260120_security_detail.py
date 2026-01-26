"""add_security_detail

Revision ID: 20260120_security_detail
Revises: 20260120_par_sipas
Create Date: 2026-01-20 04:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260120_security_detail'
down_revision: Union[str, None] = '20260120_par_sipas'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create security_detail table to replace public_order and crime_prevention."""
    # Create new security_detail table
    op.create_table(
        'security_detail',
        sa.Column('drug_cases', sa.Integer(), nullable=True, comment='Số vụ vi phạm ma túy'),
        sa.Column('drug_offenders', sa.Integer(), nullable=True, comment='Số người vi phạm ma túy'),
        sa.Column('crime_reduction_rate', sa.Float(), nullable=True, comment='Tỷ lệ giảm tội phạm (%)'),
        # Mixin columns
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('economic_indicator_id', sa.Integer(), nullable=True),
        sa.Column('province', sa.String(length=100), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('quarter', sa.Integer(), nullable=True),
        sa.Column('month', sa.Integer(), nullable=True),
        sa.Column('rank_national', sa.Integer(), nullable=True),
        sa.Column('rank_regional', sa.Integer(), nullable=True),
        sa.Column('yoy_change', sa.Float(), nullable=True),
        sa.Column('data_status', sa.String(length=20), nullable=False),
        sa.Column('data_source', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_security_detail_province', 'security_detail', ['province'])
    op.create_index('ix_security_detail_year', 'security_detail', ['year'])


def downgrade() -> None:
    """Drop security_detail table."""
    op.drop_index('ix_security_detail_year', table_name='security_detail')
    op.drop_index('ix_security_detail_province', table_name='security_detail')
    op.drop_table('security_detail')
