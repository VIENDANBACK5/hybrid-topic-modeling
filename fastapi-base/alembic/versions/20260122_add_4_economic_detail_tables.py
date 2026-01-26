"""Add 4 economic indicator detail tables

Revision ID: 20260122_add_4_economic_detail_tables
Revises: (latest)
Create Date: 2026-01-22

Tạo 4 bảng chi tiết cho chỉ số kinh tế:
1. digital_economy_detail - Kinh tế số
2. fdi_detail - Thu hút FDI
3. digital_transformation_detail - Chuyển đổi số  
4. pii_detail - Chỉ số sản xuất công nghiệp cấp tỉnh
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260122_4_economic_tables'
down_revision: Union[str, None] = '20260120_statistics'  # Link to current head
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create 4 economic indicator detail tables"""
    
    # ========================================
    # 1. DIGITAL ECONOMY DETAIL
    # ========================================
    op.create_table('digital_economy_detail',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('province', sa.String(), nullable=False, server_default='Hưng Yên'),
        sa.Column('period_type', sa.String(), nullable=False, server_default='quarter'),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('quarter', sa.Integer(), nullable=True),
        sa.Column('month', sa.Integer(), nullable=True),
        
        # Core values from base
        sa.Column('actual_value', sa.Numeric(), nullable=True, comment='Actual value'),
        sa.Column('forecast_value', sa.Numeric(), nullable=True, comment='Forecast value'),
        sa.Column('change_yoy', sa.Numeric(), nullable=True, comment='Year-over-year change %'),
        sa.Column('change_qoq', sa.Numeric(), nullable=True, comment='Quarter-over-quarter change %'),
        sa.Column('change_mom', sa.Numeric(), nullable=True, comment='Month-over-month change %'),
        sa.Column('change_prev_period', sa.Numeric(), nullable=True, comment='Previous period change %'),
        
        # Digital Economy fields
        sa.Column('digital_economy_gdp', sa.Numeric(), nullable=True, comment='GDP từ kinh tế số (tỷ VNĐ)'),
        sa.Column('digital_economy_gdp_share', sa.Numeric(), nullable=True, comment='Tỷ trọng kinh tế số trong GDP (%)'),
        sa.Column('digital_economy_growth_rate', sa.Numeric(), nullable=True, comment='Tốc độ tăng trưởng kinh tế số (%)'),
        sa.Column('ecommerce_revenue', sa.Numeric(), nullable=True, comment='Doanh thu thương mại điện tử (tỷ VNĐ)'),
        sa.Column('ecommerce_users', sa.Integer(), nullable=True, comment='Số lượng người dùng TMĐT (người)'),
        sa.Column('ecommerce_transactions', sa.Integer(), nullable=True, comment='Số lượng giao dịch TMĐT'),
        sa.Column('digital_payment_volume', sa.Numeric(), nullable=True, comment='Giá trị thanh toán điện tử (tỷ VNĐ)'),
        sa.Column('digital_payment_transactions', sa.Integer(), nullable=True, comment='Số lượng giao dịch thanh toán điện tử'),
        sa.Column('digital_wallet_users', sa.Integer(), nullable=True, comment='Số người dùng ví điện tử (người)'),
        sa.Column('cashless_payment_rate', sa.Numeric(), nullable=True, comment='Tỷ lệ thanh toán không dùng tiền mặt (%)'),
        sa.Column('digital_companies', sa.Integer(), nullable=True, comment='Số lượng doanh nghiệp công nghệ số'),
        sa.Column('tech_startups', sa.Integer(), nullable=True, comment='Số lượng startup công nghệ'),
        sa.Column('fintech_revenue', sa.Numeric(), nullable=True, comment='Doanh thu Fintech (tỷ VNĐ)'),
        sa.Column('internet_penetration', sa.Numeric(), nullable=True, comment='Tỷ lệ phủ sóng Internet (%)'),
        sa.Column('digital_workforce', sa.Integer(), nullable=True, comment='Số lao động trong lĩnh vực số (người)'),
        
        # Metadata
        sa.Column('data_status', sa.String(), server_default='estimated', comment='official, estimated, preliminary'),
        sa.Column('data_source', sa.String(), nullable=True, comment='Source URL or reference'),
        sa.Column('last_updated', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_digital_economy_province_year', 'digital_economy_detail', ['province', 'year'])
    op.create_index('idx_digital_economy_period', 'digital_economy_detail', ['year', 'quarter', 'month'])
    
    # ========================================
    # 2. FDI DETAIL
    # ========================================
    op.create_table('fdi_detail',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('province', sa.String(), nullable=False, server_default='Hưng Yên'),
        sa.Column('period_type', sa.String(), nullable=False, server_default='quarter'),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('quarter', sa.Integer(), nullable=True),
        sa.Column('month', sa.Integer(), nullable=True),
        
        # Core values from base
        sa.Column('actual_value', sa.Numeric(), nullable=True, comment='Actual value'),
        sa.Column('forecast_value', sa.Numeric(), nullable=True, comment='Forecast value'),
        sa.Column('change_yoy', sa.Numeric(), nullable=True, comment='Year-over-year change %'),
        sa.Column('change_qoq', sa.Numeric(), nullable=True, comment='Quarter-over-quarter change %'),
        sa.Column('change_mom', sa.Numeric(), nullable=True, comment='Month-over-month change %'),
        sa.Column('change_prev_period', sa.Numeric(), nullable=True, comment='Previous period change %'),
        
        # FDI fields
        sa.Column('registered_capital', sa.Numeric(), nullable=True, comment='Vốn FDI đăng ký (triệu USD)'),
        sa.Column('new_projects_capital', sa.Numeric(), nullable=True, comment='Vốn đăng ký dự án mới (triệu USD)'),
        sa.Column('additional_capital', sa.Numeric(), nullable=True, comment='Vốn đăng ký tăng thêm (triệu USD)'),
        sa.Column('disbursed_capital', sa.Numeric(), nullable=True, comment='Vốn FDI giải ngân (triệu USD)'),
        sa.Column('disbursement_rate', sa.Numeric(), nullable=True, comment='Tỷ lệ giải ngân so với đăng ký (%)'),
        sa.Column('total_projects', sa.Integer(), nullable=True, comment='Tổng số dự án (mới + tăng vốn + góp vốn)'),
        sa.Column('new_projects', sa.Integer(), nullable=True, comment='Số dự án đầu tư mới'),
        sa.Column('adjusted_projects', sa.Integer(), nullable=True, comment='Số lượt dự án tăng vốn'),
        sa.Column('manufacturing_fdi', sa.Numeric(), nullable=True, comment='FDI vào sản xuất chế biến (triệu USD)'),
        sa.Column('realestate_fdi', sa.Numeric(), nullable=True, comment='FDI vào bất động sản (triệu USD)'),
        sa.Column('technology_fdi', sa.Numeric(), nullable=True, comment='FDI vào công nghệ thông tin (triệu USD)'),
        sa.Column('japan_fdi', sa.Numeric(), nullable=True, comment='FDI từ Nhật Bản (triệu USD)'),
        sa.Column('korea_fdi', sa.Numeric(), nullable=True, comment='FDI từ Hàn Quốc (triệu USD)'),
        sa.Column('singapore_fdi', sa.Numeric(), nullable=True, comment='FDI từ Singapore (triệu USD)'),
        sa.Column('fdi_contribution_grdp', sa.Numeric(), nullable=True, comment='Đóng góp FDI vào GRDP (%)'),
        sa.Column('fdi_export_value', sa.Numeric(), nullable=True, comment='Giá trị xuất khẩu từ FDI (triệu USD)'),
        sa.Column('fdi_employment', sa.Integer(), nullable=True, comment='Số lao động trong khu vực FDI (người)'),
        
        # Metadata
        sa.Column('data_status', sa.String(), server_default='estimated', comment='official, estimated, preliminary'),
        sa.Column('data_source', sa.String(), nullable=True, comment='Source URL or reference'),
        sa.Column('last_updated', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_fdi_province_year', 'fdi_detail', ['province', 'year'])
    op.create_index('idx_fdi_period', 'fdi_detail', ['year', 'quarter', 'month'])
    
    # ========================================
    # 3. DIGITAL TRANSFORMATION DETAIL
    # ========================================
    op.create_table('digital_transformation_detail',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('province', sa.String(), nullable=False, server_default='Hưng Yên'),
        sa.Column('period_type', sa.String(), nullable=False, server_default='quarter'),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('quarter', sa.Integer(), nullable=True),
        sa.Column('month', sa.Integer(), nullable=True),
        
        # Core values from base
        sa.Column('actual_value', sa.Numeric(), nullable=True, comment='Actual value'),
        sa.Column('forecast_value', sa.Numeric(), nullable=True, comment='Forecast value'),
        sa.Column('change_yoy', sa.Numeric(), nullable=True, comment='Year-over-year change %'),
        sa.Column('change_qoq', sa.Numeric(), nullable=True, comment='Quarter-over-quarter change %'),
        sa.Column('change_mom', sa.Numeric(), nullable=True, comment='Month-over-month change %'),
        sa.Column('change_prev_period', sa.Numeric(), nullable=True, comment='Previous period change %'),
        
        # Digital Transformation fields
        sa.Column('dx_index', sa.Numeric(), nullable=True, comment='Chỉ số chuyển đổi số tổng hợp (0-100)'),
        sa.Column('dx_readiness_index', sa.Numeric(), nullable=True, comment='Chỉ số sẵn sàng chuyển đổi số (0-100)'),
        sa.Column('egov_index', sa.Numeric(), nullable=True, comment='Chỉ số chính quyền điện tử (0-100)'),
        sa.Column('online_public_services', sa.Integer(), nullable=True, comment='Số dịch vụ công trực tuyến'),
        sa.Column('level3_services', sa.Integer(), nullable=True, comment='Số dịch vụ công mức độ 3'),
        sa.Column('level4_services', sa.Integer(), nullable=True, comment='Số dịch vụ công mức độ 4'),
        sa.Column('online_service_usage_rate', sa.Numeric(), nullable=True, comment='Tỷ lệ sử dụng dịch vụ công trực tuyến (%)'),
        sa.Column('cloud_adoption_rate', sa.Numeric(), nullable=True, comment='Tỷ lệ sử dụng điện toán đám mây (%)'),
        sa.Column('broadband_coverage', sa.Numeric(), nullable=True, comment='Tỷ lệ phủ sóng băng thông rộng (%)'),
        sa.Column('fiveg_coverage', sa.Numeric(), nullable=True, comment='Tỷ lệ phủ sóng 5G (%)'),
        sa.Column('sme_dx_adoption', sa.Numeric(), nullable=True, comment='Tỷ lệ SME thực hiện CĐS (%)'),
        sa.Column('companies_using_ai', sa.Integer(), nullable=True, comment='Số DN ứng dụng AI'),
        sa.Column('companies_using_iot', sa.Integer(), nullable=True, comment='Số DN ứng dụng IoT'),
        sa.Column('digital_literacy_rate', sa.Numeric(), nullable=True, comment='Tỷ lệ biết chữ số (%)'),
        sa.Column('ai_projects', sa.Integer(), nullable=True, comment='Số dự án AI triển khai'),
        sa.Column('iot_projects', sa.Integer(), nullable=True, comment='Số dự án IoT triển khai'),
        sa.Column('dx_investment', sa.Numeric(), nullable=True, comment='Đầu tư cho CĐS (tỷ VNĐ)'),
        sa.Column('productivity_increase_from_dx', sa.Numeric(), nullable=True, comment='Tăng năng suất từ CĐS (%)'),
        
        # Metadata
        sa.Column('data_status', sa.String(), server_default='estimated', comment='official, estimated, preliminary'),
        sa.Column('data_source', sa.String(), nullable=True, comment='Source URL or reference'),
        sa.Column('last_updated', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_dx_province_year', 'digital_transformation_detail', ['province', 'year'])
    op.create_index('idx_dx_period', 'digital_transformation_detail', ['year', 'quarter', 'month'])
    
    # ========================================
    # 4. PII DETAIL (Provincial Industrial Index)
    # ========================================
    op.create_table('pii_detail',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('province', sa.String(), nullable=False, server_default='Hưng Yên'),
        sa.Column('period_type', sa.String(), nullable=False, server_default='quarter'),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('quarter', sa.Integer(), nullable=True),
        sa.Column('month', sa.Integer(), nullable=True),
        
        # Core values from base
        sa.Column('actual_value', sa.Numeric(), nullable=True, comment='Actual value'),
        sa.Column('forecast_value', sa.Numeric(), nullable=True, comment='Forecast value'),
        sa.Column('change_yoy', sa.Numeric(), nullable=True, comment='Year-over-year change %'),
        sa.Column('change_qoq', sa.Numeric(), nullable=True, comment='Quarter-over-quarter change %'),
        sa.Column('change_mom', sa.Numeric(), nullable=True, comment='Month-over-month change %'),
        sa.Column('change_prev_period', sa.Numeric(), nullable=True, comment='Previous period change %'),
        
        # PII fields
        sa.Column('pii_overall', sa.Numeric(), nullable=True, comment='Chỉ số IIP tổng hợp (Index, base=100)'),
        sa.Column('pii_growth_rate', sa.Numeric(), nullable=True, comment='Tốc độ tăng trưởng IIP (%)'),
        sa.Column('industrial_output_value', sa.Numeric(), nullable=True, comment='Giá trị sản xuất công nghiệp (tỷ VNĐ)'),
        sa.Column('mining_index', sa.Numeric(), nullable=True, comment='Chỉ số khai khoáng (Index)'),
        sa.Column('manufacturing_index', sa.Numeric(), nullable=True, comment='Chỉ số công nghiệp chế biến (Index)'),
        sa.Column('electricity_index', sa.Numeric(), nullable=True, comment='Chỉ số điện, khí đốt (Index)'),
        sa.Column('food_processing_index', sa.Numeric(), nullable=True, comment='Chỉ số chế biến thực phẩm (Index)'),
        sa.Column('textile_index', sa.Numeric(), nullable=True, comment='Chỉ số dệt may (Index)'),
        sa.Column('electronics_index', sa.Numeric(), nullable=True, comment='Chỉ số điện tử, máy tính (Index)'),
        sa.Column('state_owned_pii', sa.Numeric(), nullable=True, comment='IIP khu vực nhà nước (Index)'),
        sa.Column('private_pii', sa.Numeric(), nullable=True, comment='IIP khu vực tư nhân (Index)'),
        sa.Column('fdi_pii', sa.Numeric(), nullable=True, comment='IIP khu vực FDI (Index)'),
        sa.Column('manufacturing_share', sa.Numeric(), nullable=True, comment='Tỷ trọng chế biến chế tạo (%)'),
        sa.Column('hightech_industry_share', sa.Numeric(), nullable=True, comment='Tỷ trọng công nghiệp công nghệ cao (%)'),
        sa.Column('labor_productivity', sa.Numeric(), nullable=True, comment='Năng suất lao động (triệu VNĐ/người)'),
        sa.Column('capacity_utilization', sa.Numeric(), nullable=True, comment='Tỷ lệ sử dụng công suất (%)'),
        sa.Column('industrial_enterprises', sa.Integer(), nullable=True, comment='Số doanh nghiệp công nghiệp'),
        sa.Column('industrial_workers', sa.Integer(), nullable=True, comment='Số lao động trong công nghiệp (người)'),
        
        # Metadata
        sa.Column('data_status', sa.String(), server_default='estimated', comment='official, estimated, preliminary'),
        sa.Column('data_source', sa.String(), nullable=True, comment='Source URL or reference'),
        sa.Column('last_updated', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_pii_province_year', 'pii_detail', ['province', 'year'])
    op.create_index('idx_pii_period', 'pii_detail', ['year', 'quarter', 'month'])


def downgrade() -> None:
    """Drop all 4 indicator detail tables"""
    op.drop_index('idx_pii_period', 'pii_detail')
    op.drop_index('idx_pii_province_year', 'pii_detail')
    op.drop_table('pii_detail')
    
    op.drop_index('idx_dx_period', 'digital_transformation_detail')
    op.drop_index('idx_dx_province_year', 'digital_transformation_detail')
    op.drop_table('digital_transformation_detail')
    
    op.drop_index('idx_fdi_period', 'fdi_detail')
    op.drop_index('idx_fdi_province_year', 'fdi_detail')
    op.drop_table('fdi_detail')
    
    op.drop_index('idx_digital_economy_period', 'digital_economy_detail')
    op.drop_index('idx_digital_economy_province_year', 'digital_economy_detail')
    op.drop_table('digital_economy_detail')
