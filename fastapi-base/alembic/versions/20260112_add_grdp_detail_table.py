"""add grdp_detail table

Revision ID: add_grdp_detail
Revises: restructure_economic_ind
Create Date: 2026-01-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_grdp_detail'
down_revision: Union[str, None] = 'restructure_economic_ind'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create grdp_detail table"""
    
    op.create_table('grdp_detail',
        # Primary key
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        
        # Foreign key to economic_indicators (optional)
        sa.Column('economic_indicator_id', sa.Integer(), nullable=True),
        
        # 1. Nhóm định danh & thời gian
        sa.Column('province', sa.String(length=100), nullable=False, comment='Tên tỉnh/thành phố'),
        sa.Column('year', sa.Integer(), nullable=False, comment='Năm thống kê'),
        sa.Column('quarter', sa.Integer(), nullable=True, comment='Quý (1-4), NULL = cả năm'),
        
        # 2. Nhóm giá trị kinh tế
        sa.Column('grdp_current_price', sa.Float(), nullable=True, comment='GRDP theo giá hiện hành (tỷ VNĐ)'),
        sa.Column('grdp_per_capita', sa.Float(), nullable=True, comment='GRDP bình quân/người (triệu VNĐ)'),
        
        # 3. Nhóm tăng trưởng
        sa.Column('growth_rate', sa.Float(), nullable=True, comment='Tốc độ tăng trưởng so cùng kỳ (%)'),
        
        # 4. Nhóm cơ cấu ngành kinh tế
        sa.Column('agriculture_sector_pct', sa.Float(), nullable=True, comment='Tỷ trọng nông - lâm - thủy sản (%)'),
        sa.Column('industry_sector_pct', sa.Float(), nullable=True, comment='Tỷ trọng công nghiệp - xây dựng (%)'),
        sa.Column('service_sector_pct', sa.Float(), nullable=True, comment='Tỷ trọng dịch vụ (%)'),
        
        # 5. Nhóm so sánh & xếp hạng
        sa.Column('rank_national', sa.Integer(), nullable=True, comment='Xếp hạng so với cả nước'),
        
        # 6. Nhóm dự báo
        sa.Column('forecast_year_end', sa.Float(), nullable=True, comment='Dự báo GRDP cả năm (tỷ VNĐ)'),
        
        # 7. Nhóm trạng thái & nguồn dữ liệu
        sa.Column('data_status', sa.String(length=20), nullable=False, server_default='official', 
                  comment='Trạng thái: official/estimated/forecast'),
        sa.Column('data_source', sa.String(length=255), nullable=True, comment='Nguồn dữ liệu'),
        sa.Column('last_updated', sa.DateTime(), server_default=sa.func.now(), comment='Thời điểm cập nhật gần nhất'),
        
        # Timestamp fields
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        
        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL'),
    )
    
    # Create indexes for frequently queried columns
    op.create_index('ix_grdp_detail_province', 'grdp_detail', ['province'])
    op.create_index('ix_grdp_detail_year', 'grdp_detail', ['year'])
    op.create_index('ix_grdp_detail_quarter', 'grdp_detail', ['quarter'])
    op.create_index('ix_grdp_detail_economic_indicator_id', 'grdp_detail', ['economic_indicator_id'])
    op.create_index('ix_grdp_detail_data_status', 'grdp_detail', ['data_status'])
    
    # Create unique constraint to prevent duplicate records
    op.create_index('ix_grdp_detail_unique', 'grdp_detail', 
                    ['province', 'year', 'quarter', 'data_status'], 
                    unique=True,
                    postgresql_where=sa.text('quarter IS NOT NULL'))
    
    op.create_index('ix_grdp_detail_unique_yearly', 'grdp_detail', 
                    ['province', 'year', 'data_status'], 
                    unique=True,
                    postgresql_where=sa.text('quarter IS NULL'))


def downgrade() -> None:
    """Drop grdp_detail table"""
    
    # Drop indexes first
    op.drop_index('ix_grdp_detail_unique_yearly', 'grdp_detail')
    op.drop_index('ix_grdp_detail_unique', 'grdp_detail')
    op.drop_index('ix_grdp_detail_data_status', 'grdp_detail')
    op.drop_index('ix_grdp_detail_economic_indicator_id', 'grdp_detail')
    op.drop_index('ix_grdp_detail_quarter', 'grdp_detail')
    op.drop_index('ix_grdp_detail_year', 'grdp_detail')
    op.drop_index('ix_grdp_detail_province', 'grdp_detail')
    
    # Drop table
    op.drop_table('grdp_detail')
