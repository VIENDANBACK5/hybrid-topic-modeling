"""add statistics tables for economic and political data

Revision ID: 20260120_statistics
Revises: a3013e4aba96
Create Date: 2026-01-20 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260120_statistics'
down_revision: Union[str, None] = 'a3013e4aba96'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create economic_statistics and political_statistics tables."""
    
    # Create economic_statistics table
    op.create_table(
        'economic_statistics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.Float(), nullable=True),
        sa.Column('updated_at', sa.Float(), nullable=True),
        sa.Column('dvhc', sa.String(length=255), nullable=False, comment='Đơn vị hành chính (xã/phường)'),
        sa.Column('source_post_id', sa.Integer(), nullable=True, comment='ID của bài viết nguồn'),
        sa.Column('source_url', sa.String(length=500), nullable=True, comment='URL của bài viết nguồn'),
        sa.Column('period', sa.String(length=100), nullable=True, comment='Thời kỳ (năm, quý, tháng)'),
        sa.Column('year', sa.Integer(), nullable=True, comment='Năm'),
        sa.Column('total_production_value', sa.Float(), nullable=True, comment='Tổng giá trị sản xuất (tỷ đồng)'),
        sa.Column('growth_rate', sa.Float(), nullable=True, comment='Tốc độ tăng trưởng (%)'),
        sa.Column('total_budget_revenue', sa.Float(), nullable=True, comment='Tổng thu ngân sách nhà nước (tỷ đồng)'),
        sa.Column('budget_collection_efficiency', sa.Float(), nullable=True, comment='Hiệu suất thu ngân sách (%)'),
        sa.Column('notes', sa.Text(), nullable=True, comment='Ghi chú bổ sung'),
        sa.Column('extraction_metadata', sa.Text(), nullable=True, comment='Metadata từ quá trình trích xuất'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_economic_dvhc', 'economic_statistics', ['dvhc'])
    op.create_index('idx_economic_year', 'economic_statistics', ['year'])
    op.create_index('idx_economic_source', 'economic_statistics', ['source_post_id'])

    # Create political_statistics table
    op.create_table(
        'political_statistics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.Float(), nullable=True),
        sa.Column('updated_at', sa.Float(), nullable=True),
        sa.Column('dvhc', sa.String(length=255), nullable=False, comment='Đơn vị hành chính (xã/phường)'),
        sa.Column('source_post_id', sa.Integer(), nullable=True, comment='ID của bài viết nguồn'),
        sa.Column('source_url', sa.String(length=500), nullable=True, comment='URL của bài viết nguồn'),
        sa.Column('period', sa.String(length=100), nullable=True, comment='Thời kỳ (năm, quý, tháng)'),
        sa.Column('year', sa.Integer(), nullable=True, comment='Năm'),
        sa.Column('party_organization_count', sa.Integer(), nullable=True, comment='Số tổ chức Đảng'),
        sa.Column('party_member_count', sa.Integer(), nullable=True, comment='Số lượng Đảng viên'),
        sa.Column('party_size_description', sa.Text(), nullable=True, comment='Mô tả quy mô Đảng bộ'),
        sa.Column('new_party_members', sa.Integer(), nullable=True, comment='Số Đảng viên mới kết nạp'),
        sa.Column('party_cells_count', sa.Integer(), nullable=True, comment='Số chi bộ'),
        sa.Column('notes', sa.Text(), nullable=True, comment='Ghi chú bổ sung'),
        sa.Column('extraction_metadata', sa.Text(), nullable=True, comment='Metadata từ quá trình trích xuất'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_political_dvhc', 'political_statistics', ['dvhc'])
    op.create_index('idx_political_year', 'political_statistics', ['year'])
    op.create_index('idx_political_source', 'political_statistics', ['source_post_id'])


def downgrade() -> None:
    """Drop economic_statistics and political_statistics tables."""
    op.drop_index('idx_political_source', table_name='political_statistics')
    op.drop_index('idx_political_year', table_name='political_statistics')
    op.drop_index('idx_political_dvhc', table_name='political_statistics')
    op.drop_table('political_statistics')
    
    op.drop_index('idx_economic_source', table_name='economic_statistics')
    op.drop_index('idx_economic_year', table_name='economic_statistics')
    op.drop_index('idx_economic_dvhc', table_name='economic_statistics')
    op.drop_table('economic_statistics')
