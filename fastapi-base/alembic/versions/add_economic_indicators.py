"""add economic indicators tables

Revision ID: add_economic_indicators
Revises: 63bc2c0fcb48
Create Date: 2026-01-09 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_economic_indicators'
down_revision: Union[str, None] = '63bc2c0fcb48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - create economic indicators tables"""
    
    # Create economic_indicators table
    op.create_table('economic_indicators',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        
        # Time information
        sa.Column('period_type', sa.String(length=20), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('period_label', sa.String(length=50), nullable=True),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('month', sa.Integer(), nullable=True),
        sa.Column('quarter', sa.Integer(), nullable=True),
        
        # Location
        sa.Column('province', sa.String(length=100), nullable=True),
        sa.Column('region', sa.String(length=100), nullable=True),
        
        # Economic indicators
        sa.Column('grdp', sa.Float(), nullable=True),
        sa.Column('grdp_growth_rate', sa.Float(), nullable=True),
        sa.Column('grdp_per_capita', sa.Float(), nullable=True),
        
        sa.Column('iip', sa.Float(), nullable=True),
        sa.Column('iip_growth_rate', sa.Float(), nullable=True),
        
        sa.Column('agricultural_production_index', sa.Float(), nullable=True),
        sa.Column('agricultural_growth_rate', sa.Float(), nullable=True),
        sa.Column('agricultural_output', sa.Float(), nullable=True),
        
        sa.Column('retail_services_total', sa.Float(), nullable=True),
        sa.Column('retail_services_growth', sa.Float(), nullable=True),
        sa.Column('retail_total', sa.Float(), nullable=True),
        sa.Column('services_total', sa.Float(), nullable=True),
        
        sa.Column('export_value', sa.Float(), nullable=True),
        sa.Column('export_growth_rate', sa.Float(), nullable=True),
        sa.Column('import_value', sa.Float(), nullable=True),
        sa.Column('trade_balance', sa.Float(), nullable=True),
        
        sa.Column('total_investment', sa.Float(), nullable=True),
        sa.Column('fdi_registered', sa.Float(), nullable=True),
        sa.Column('fdi_disbursed', sa.Float(), nullable=True),
        sa.Column('domestic_investment', sa.Float(), nullable=True),
        sa.Column('investment_growth_rate', sa.Float(), nullable=True),
        
        sa.Column('state_budget_revenue', sa.Float(), nullable=True),
        sa.Column('sbr_growth_rate', sa.Float(), nullable=True),
        sa.Column('tax_revenue', sa.Float(), nullable=True),
        sa.Column('non_tax_revenue', sa.Float(), nullable=True),
        
        sa.Column('cpi', sa.Float(), nullable=True),
        sa.Column('cpi_growth_rate', sa.Float(), nullable=True),
        sa.Column('core_inflation', sa.Float(), nullable=True),
        
        sa.Column('unemployment_rate', sa.Float(), nullable=True),
        sa.Column('labor_force', sa.Float(), nullable=True),
        
        sa.Column('detailed_data', sa.JSON(), nullable=True),
        
        sa.Column('data_source', sa.String(length=255), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        
        sa.Column('is_verified', sa.Integer(), server_default='0'),
        sa.Column('is_estimated', sa.Integer(), server_default='0'),
        
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_economic_indicators_period_type', 'economic_indicators', ['period_type'])
    op.create_index('ix_economic_indicators_period_start', 'economic_indicators', ['period_start'])
    op.create_index('ix_economic_indicators_year', 'economic_indicators', ['year'])
    op.create_index('ix_economic_indicators_month', 'economic_indicators', ['month'])
    op.create_index('ix_economic_indicators_quarter', 'economic_indicators', ['quarter'])
    op.create_index('ix_economic_indicators_province', 'economic_indicators', ['province'])
    
    # Create economic_indicators_gpt table
    op.create_table('economic_indicators_gpt',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        
        sa.Column('period_type', sa.String(length=20), nullable=False),
        sa.Column('period_label', sa.String(length=50), nullable=True),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('month', sa.Integer(), nullable=True),
        sa.Column('quarter', sa.Integer(), nullable=True),
        
        sa.Column('province', sa.String(length=100), nullable=True),
        
        sa.Column('indicator_name', sa.String(length=100), nullable=False),
        sa.Column('indicator_value', sa.Float(), nullable=True),
        sa.Column('indicator_unit', sa.String(length=50), nullable=True),
        
        sa.Column('gpt_response', sa.Text(), nullable=True),
        sa.Column('gpt_summary', sa.Text(), nullable=True),
        
        sa.Column('prompt_used', sa.Text(), nullable=True),
        sa.Column('model_used', sa.String(length=50), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for GPT table
    op.create_index('ix_economic_indicators_gpt_period_type', 'economic_indicators_gpt', ['period_type'])
    op.create_index('ix_economic_indicators_gpt_year', 'economic_indicators_gpt', ['year'])
    op.create_index('ix_economic_indicators_gpt_month', 'economic_indicators_gpt', ['month'])
    op.create_index('ix_economic_indicators_gpt_quarter', 'economic_indicators_gpt', ['quarter'])
    op.create_index('ix_economic_indicators_gpt_province', 'economic_indicators_gpt', ['province'])
    op.create_index('ix_economic_indicators_gpt_indicator_name', 'economic_indicators_gpt', ['indicator_name'])


def downgrade() -> None:
    """Downgrade schema - drop economic indicators tables"""
    op.drop_table('economic_indicators_gpt')
    op.drop_table('economic_indicators')
