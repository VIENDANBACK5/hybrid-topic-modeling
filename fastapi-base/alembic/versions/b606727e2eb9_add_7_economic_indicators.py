"""add_7_economic_indicators

Revision ID: b606727e2eb9
Revises: de3c11d7b74a
Create Date: 2026-01-14 02:42:14.059592

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b606727e2eb9'
down_revision: Union[str, None] = 'de3c11d7b74a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create 7 economic indicator tables."""
    
    # 1. IIP (Industrial Production Index)
    op.create_table(
        'iip_detail',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('province', sa.String(), nullable=False),
        sa.Column('period_type', sa.String(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('quarter', sa.Integer(), nullable=True),
        sa.Column('month', sa.Integer(), nullable=True),
        sa.Column('actual_value', sa.Numeric(), nullable=True),
        sa.Column('forecast_value', sa.Numeric(), nullable=True),
        sa.Column('change_yoy', sa.Numeric(), nullable=True),
        sa.Column('change_qoq', sa.Numeric(), nullable=True),
        sa.Column('change_mom', sa.Numeric(), nullable=True),
        sa.Column('change_prev_period', sa.Numeric(), nullable=True),
        sa.Column('data_status', sa.String(), nullable=True),
        sa.Column('data_source', sa.String(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('province', 'year', 'quarter', 'month', name='unique_iip_period')
    )
    op.create_index('idx_iip_province_year', 'iip_detail', ['province', 'year'])
    
    # 2. Agricultural Production Index
    op.create_table(
        'agri_production_detail',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('province', sa.String(), nullable=False),
        sa.Column('period_type', sa.String(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('quarter', sa.Integer(), nullable=True),
        sa.Column('month', sa.Integer(), nullable=True),
        sa.Column('actual_value', sa.Numeric(), nullable=True),
        sa.Column('forecast_value', sa.Numeric(), nullable=True),
        sa.Column('change_yoy', sa.Numeric(), nullable=True),
        sa.Column('change_qoq', sa.Numeric(), nullable=True),
        sa.Column('change_mom', sa.Numeric(), nullable=True),
        sa.Column('change_prev_period', sa.Numeric(), nullable=True),
        sa.Column('data_status', sa.String(), nullable=True),
        sa.Column('data_source', sa.String(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('province', 'year', 'quarter', 'month', name='unique_agri_period')
    )
    op.create_index('idx_agri_province_year', 'agri_production_detail', ['province', 'year'])
    
    # 3. Retail & Services
    op.create_table(
        'retail_services_detail',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('province', sa.String(), nullable=False),
        sa.Column('period_type', sa.String(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('quarter', sa.Integer(), nullable=True),
        sa.Column('month', sa.Integer(), nullable=True),
        sa.Column('actual_value', sa.Numeric(), nullable=True),
        sa.Column('forecast_value', sa.Numeric(), nullable=True),
        sa.Column('retail_value', sa.Numeric(), nullable=True),
        sa.Column('services_value', sa.Numeric(), nullable=True),
        sa.Column('change_yoy', sa.Numeric(), nullable=True),
        sa.Column('change_qoq', sa.Numeric(), nullable=True),
        sa.Column('change_mom', sa.Numeric(), nullable=True),
        sa.Column('change_prev_period', sa.Numeric(), nullable=True),
        sa.Column('data_status', sa.String(), nullable=True),
        sa.Column('data_source', sa.String(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('province', 'year', 'quarter', 'month', name='unique_retail_period')
    )
    op.create_index('idx_retail_province_year', 'retail_services_detail', ['province', 'year'])
    
    # 4. Export
    op.create_table(
        'export_detail',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('province', sa.String(), nullable=False),
        sa.Column('period_type', sa.String(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('quarter', sa.Integer(), nullable=True),
        sa.Column('month', sa.Integer(), nullable=True),
        sa.Column('actual_value', sa.Numeric(), nullable=True),
        sa.Column('forecast_value', sa.Numeric(), nullable=True),
        sa.Column('export_usd', sa.Numeric(), nullable=True),
        sa.Column('export_vnd', sa.Numeric(), nullable=True),
        sa.Column('top_products', sa.String(), nullable=True),
        sa.Column('top_markets', sa.String(), nullable=True),
        sa.Column('change_yoy', sa.Numeric(), nullable=True),
        sa.Column('change_qoq', sa.Numeric(), nullable=True),
        sa.Column('change_mom', sa.Numeric(), nullable=True),
        sa.Column('change_prev_period', sa.Numeric(), nullable=True),
        sa.Column('data_status', sa.String(), nullable=True),
        sa.Column('data_source', sa.String(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('province', 'year', 'quarter', 'month', name='unique_export_period')
    )
    op.create_index('idx_export_province_year', 'export_detail', ['province', 'year'])
    
    # 5. Investment (FDI + DDI)
    op.create_table(
        'investment_detail',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('province', sa.String(), nullable=False),
        sa.Column('period_type', sa.String(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('quarter', sa.Integer(), nullable=True),
        sa.Column('month', sa.Integer(), nullable=True),
        sa.Column('actual_value', sa.Numeric(), nullable=True),
        sa.Column('forecast_value', sa.Numeric(), nullable=True),
        sa.Column('fdi_registered', sa.Numeric(), nullable=True),
        sa.Column('fdi_disbursed', sa.Numeric(), nullable=True),
        sa.Column('fdi_projects_new', sa.Numeric(), nullable=True),
        sa.Column('fdi_projects_expanded', sa.Numeric(), nullable=True),
        sa.Column('ddi_value', sa.Numeric(), nullable=True),
        sa.Column('public_investment', sa.Numeric(), nullable=True),
        sa.Column('change_yoy', sa.Numeric(), nullable=True),
        sa.Column('change_qoq', sa.Numeric(), nullable=True),
        sa.Column('change_mom', sa.Numeric(), nullable=True),
        sa.Column('change_prev_period', sa.Numeric(), nullable=True),
        sa.Column('data_status', sa.String(), nullable=True),
        sa.Column('data_source', sa.String(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('province', 'year', 'quarter', 'month', name='unique_investment_period')
    )
    op.create_index('idx_investment_province_year', 'investment_detail', ['province', 'year'])
    
    # 6. Budget Revenue
    op.create_table(
        'budget_revenue_detail',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('province', sa.String(), nullable=False),
        sa.Column('period_type', sa.String(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('quarter', sa.Integer(), nullable=True),
        sa.Column('month', sa.Integer(), nullable=True),
        sa.Column('actual_value', sa.Numeric(), nullable=True),
        sa.Column('forecast_value', sa.Numeric(), nullable=True),
        sa.Column('tax_revenue', sa.Numeric(), nullable=True),
        sa.Column('non_tax_revenue', sa.Numeric(), nullable=True),
        sa.Column('land_revenue', sa.Numeric(), nullable=True),
        sa.Column('budget_target', sa.Numeric(), nullable=True),
        sa.Column('execution_rate', sa.Numeric(), nullable=True),
        sa.Column('change_yoy', sa.Numeric(), nullable=True),
        sa.Column('change_qoq', sa.Numeric(), nullable=True),
        sa.Column('change_mom', sa.Numeric(), nullable=True),
        sa.Column('change_prev_period', sa.Numeric(), nullable=True),
        sa.Column('data_status', sa.String(), nullable=True),
        sa.Column('data_source', sa.String(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('province', 'year', 'quarter', 'month', name='unique_budget_period')
    )
    op.create_index('idx_budget_province_year', 'budget_revenue_detail', ['province', 'year'])
    
    # 7. CPI (Consumer Price Index)
    op.create_table(
        'cpi_detail',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('province', sa.String(), nullable=False),
        sa.Column('period_type', sa.String(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('quarter', sa.Integer(), nullable=True),
        sa.Column('month', sa.Integer(), nullable=True),
        sa.Column('actual_value', sa.Numeric(), nullable=True),
        sa.Column('forecast_value', sa.Numeric(), nullable=True),
        sa.Column('cpi_food', sa.Numeric(), nullable=True),
        sa.Column('cpi_housing', sa.Numeric(), nullable=True),
        sa.Column('cpi_transport', sa.Numeric(), nullable=True),
        sa.Column('cpi_education', sa.Numeric(), nullable=True),
        sa.Column('cpi_healthcare', sa.Numeric(), nullable=True),
        sa.Column('core_cpi', sa.Numeric(), nullable=True),
        sa.Column('inflation_rate', sa.Numeric(), nullable=True),
        sa.Column('basket_weights', sa.String(), nullable=True),
        sa.Column('change_yoy', sa.Numeric(), nullable=True),
        sa.Column('change_qoq', sa.Numeric(), nullable=True),
        sa.Column('change_mom', sa.Numeric(), nullable=True),
        sa.Column('change_prev_period', sa.Numeric(), nullable=True),
        sa.Column('data_status', sa.String(), nullable=True),
        sa.Column('data_source', sa.String(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('province', 'year', 'quarter', 'month', name='unique_cpi_period')
    )
    op.create_index('idx_cpi_province_year', 'cpi_detail', ['province', 'year'])


def downgrade() -> None:
    """Drop 7 economic indicator tables."""
    op.drop_index('idx_cpi_province_year', table_name='cpi_detail')
    op.drop_table('cpi_detail')
    
    op.drop_index('idx_budget_province_year', table_name='budget_revenue_detail')
    op.drop_table('budget_revenue_detail')
    
    op.drop_index('idx_investment_province_year', table_name='investment_detail')
    op.drop_table('investment_detail')
    
    op.drop_index('idx_export_province_year', table_name='export_detail')
    op.drop_table('export_detail')
    
    op.drop_index('idx_retail_province_year', table_name='retail_services_detail')
    op.drop_table('retail_services_detail')
    
    op.drop_index('idx_agri_province_year', table_name='agri_production_detail')
    op.drop_table('agri_production_detail')
    
    op.drop_index('idx_iip_province_year', table_name='iip_detail')
    op.drop_table('iip_detail')
