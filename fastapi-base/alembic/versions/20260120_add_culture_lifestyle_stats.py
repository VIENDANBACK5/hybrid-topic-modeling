"""Add culture_lifestyle_stats_detail table - Thống kê văn hóa và đời sống

Revision ID: 20260120_culture_lifestyle
Revises: 4e71bcccb1f2
Create Date: 2026-01-20

Bảng mới thay thế cho lĩnh vực Văn hóa:
- culture_lifestyle_stats_detail: Tổng hợp các chỉ số văn hóa và đời sống
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260120_culture_lifestyle'
down_revision: Union[str, None] = '4e71bcccb1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create culture_lifestyle_stats_detail table
    op.create_table(
        'culture_lifestyle_stats_detail',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('economic_indicator_id', sa.Integer(), nullable=True),
        
        # Thời gian
        sa.Column('province', sa.String(length=100), nullable=False, comment='Tên tỉnh/thành phố'),
        sa.Column('year', sa.Integer(), nullable=False, comment='Năm thống kê'),
        sa.Column('quarter', sa.Integer(), nullable=True, comment='Quý (1-4), NULL = cả năm'),
        sa.Column('month', sa.Integer(), nullable=True, comment='Tháng (1-12), NULL = cả năm/quý'),
        
        # Dữ liệu văn hóa và đời sống
        sa.Column('total_heritage_sites', sa.Integer(), nullable=True, comment='Tổng số di tích văn hóa'),
        sa.Column('tourist_visitors', sa.Float(), nullable=True, comment='Số lượt khách tham quan'),
        sa.Column('tourism_revenue_billion', sa.Float(), nullable=True, comment='Doanh thu du lịch (tỷ đồng)'),
        sa.Column('natural_population_growth_rate', sa.Float(), nullable=True, comment='Tốc độ tăng dân số tự nhiên (%)'),
        sa.Column('elderly_health_checkup_rate', sa.Float(), nullable=True, comment='Tỷ lệ người cao tuổi khám sức khỏe định kỳ (%)'),
        sa.Column('sex_ratio_at_birth', sa.Float(), nullable=True, comment='Tỷ số giới tính khi sinh'),
        
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
    op.create_index('ix_culture_lifestyle_stats_detail_province', 'culture_lifestyle_stats_detail', ['province'])
    op.create_index('ix_culture_lifestyle_stats_detail_year', 'culture_lifestyle_stats_detail', ['year'])
    op.create_index('ix_culture_lifestyle_stats_detail_quarter', 'culture_lifestyle_stats_detail', ['quarter'])
    op.create_index('ix_culture_lifestyle_stats_detail_economic_indicator_id', 'culture_lifestyle_stats_detail', ['economic_indicator_id'])


def downgrade() -> None:
    op.drop_index('ix_culture_lifestyle_stats_detail_economic_indicator_id', table_name='culture_lifestyle_stats_detail')
    op.drop_index('ix_culture_lifestyle_stats_detail_quarter', table_name='culture_lifestyle_stats_detail')
    op.drop_index('ix_culture_lifestyle_stats_detail_year', table_name='culture_lifestyle_stats_detail')
    op.drop_index('ix_culture_lifestyle_stats_detail_province', table_name='culture_lifestyle_stats_detail')
    op.drop_table('culture_lifestyle_stats_detail')
