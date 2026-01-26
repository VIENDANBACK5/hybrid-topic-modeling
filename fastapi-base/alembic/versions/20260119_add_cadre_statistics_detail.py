"""Add cadre_statistics_detail table - Thống kê số lượng cán bộ

Revision ID: 20260119_add_cadre_stats
Revises: add_27_indicator_details
Create Date: 2026-01-19

Bảng mới thay thế cho lĩnh vực Xây dựng Đảng:
- cadre_statistics_detail: Thống kê số lượng cán bộ (tổng số biên chế, cấp tỉnh, cấp xã, hợp đồng)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260119_add_cadre_stats'
down_revision: Union[str, None] = 'add_27_indicator_details'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create cadre_statistics_detail table
    op.create_table(
        'cadre_statistics_detail',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('economic_indicator_id', sa.Integer(), nullable=True),
        
        # Thời gian
        sa.Column('province', sa.String(length=100), nullable=False, comment='Tên tỉnh/thành phố'),
        sa.Column('year', sa.Integer(), nullable=False, comment='Năm thống kê'),
        sa.Column('quarter', sa.Integer(), nullable=True, comment='Quý (1-4), NULL = cả năm'),
        sa.Column('month', sa.Integer(), nullable=True, comment='Tháng (1-12), NULL = cả năm/quý'),
        
        # Dữ liệu thống kê cán bộ
        sa.Column('total_authorized', sa.Integer(), nullable=True, comment='Tổng số biên chế'),
        sa.Column('provincial_level', sa.Integer(), nullable=True, comment='Tổng số cấp tỉnh'),
        sa.Column('commune_level', sa.Integer(), nullable=True, comment='Tổng số cấp xã phường'),
        sa.Column('contract_workers', sa.Integer(), nullable=True, comment='Tổng số lao động hợp đồng'),
        
        # Metadata
        sa.Column('rank_national', sa.Integer(), nullable=True, comment='Xếp hạng so với cả nước'),
        sa.Column('rank_regional', sa.Integer(), nullable=True, comment='Xếp hạng trong vùng'),
        sa.Column('yoy_change', sa.Float(), nullable=True, comment='Thay đổi so với cùng kỳ năm trước (%)'),
        sa.Column('data_status', sa.String(length=20), nullable=False, server_default='official',
                  comment='Trạng thái: official/estimated/forecast'),
        sa.Column('data_source', sa.String(length=255), nullable=True, comment='Nguồn dữ liệu'),
        sa.Column('notes', sa.Text(), nullable=True, comment='Ghi chú'),
        sa.Column('last_updated', sa.DateTime(), server_default=sa.func.now(), comment='Thời điểm cập nhật'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    
    # Create indexes
    op.create_index('ix_cadre_statistics_detail_province', 'cadre_statistics_detail', ['province'])
    op.create_index('ix_cadre_statistics_detail_year', 'cadre_statistics_detail', ['year'])
    op.create_index('ix_cadre_statistics_detail_quarter', 'cadre_statistics_detail', ['quarter'])
    op.create_index('ix_cadre_statistics_detail_economic_indicator_id', 'cadre_statistics_detail', ['economic_indicator_id'])


def downgrade() -> None:
    op.drop_index('ix_cadre_statistics_detail_economic_indicator_id', table_name='cadre_statistics_detail')
    op.drop_index('ix_cadre_statistics_detail_quarter', table_name='cadre_statistics_detail')
    op.drop_index('ix_cadre_statistics_detail_year', table_name='cadre_statistics_detail')
    op.drop_index('ix_cadre_statistics_detail_province', table_name='cadre_statistics_detail')
    op.drop_table('cadre_statistics_detail')
