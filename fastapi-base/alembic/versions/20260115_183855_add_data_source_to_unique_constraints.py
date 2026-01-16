"""add_data_source_to_unique_constraints

Revision ID: 20260115_183855
Revises: b606727e2eb9
Create Date: 2026-01-15 18:38:55

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260115_183855'
down_revision = 'b606727e2eb9'
branch_labels = None
depends_on = None


def upgrade():
    """
    Drop old unique constraints and create new ones with data_source included.
    This allows multiple records for the same period from different sources.
    """
    
    # IIP Detail
    op.drop_constraint('unique_iip_period', 'iip_detail', type_='unique')
    op.create_unique_constraint(
        'unique_iip_period',
        'iip_detail',
        ['province', 'year', 'quarter', 'month', 'data_source']
    )
    
    # Agricultural Production Detail
    op.drop_constraint('unique_agri_period', 'agri_production_detail', type_='unique')
    op.create_unique_constraint(
        'unique_agri_period',
        'agri_production_detail',
        ['province', 'year', 'quarter', 'month', 'data_source']
    )
    
    # Retail Services Detail
    op.drop_constraint('unique_retail_period', 'retail_services_detail', type_='unique')
    op.create_unique_constraint(
        'unique_retail_period',
        'retail_services_detail',
        ['province', 'year', 'quarter', 'month', 'data_source']
    )
    
    # Export Detail
    op.drop_constraint('unique_export_period', 'export_detail', type_='unique')
    op.create_unique_constraint(
        'unique_export_period',
        'export_detail',
        ['province', 'year', 'quarter', 'month', 'data_source']
    )
    
    # Investment Detail
    op.drop_constraint('unique_investment_period', 'investment_detail', type_='unique')
    op.create_unique_constraint(
        'unique_investment_period',
        'investment_detail',
        ['province', 'year', 'quarter', 'month', 'data_source']
    )
    
    # Budget Revenue Detail
    op.drop_constraint('unique_budget_period', 'budget_revenue_detail', type_='unique')
    op.create_unique_constraint(
        'unique_budget_period',
        'budget_revenue_detail',
        ['province', 'year', 'quarter', 'month', 'data_source']
    )
    
    # CPI Detail
    op.drop_constraint('unique_cpi_period', 'cpi_detail', type_='unique')
    op.create_unique_constraint(
        'unique_cpi_period',
        'cpi_detail',
        ['province', 'year', 'quarter', 'month', 'data_source']
    )


def downgrade():
    """
    Revert to old unique constraints without data_source.
    """
    
    # IIP Detail
    op.drop_constraint('unique_iip_period', 'iip_detail', type_='unique')
    op.create_unique_constraint(
        'unique_iip_period',
        'iip_detail',
        ['province', 'year', 'quarter', 'month']
    )
    
    # Agricultural Production Detail
    op.drop_constraint('unique_agri_period', 'agri_production_detail', type_='unique')
    op.create_unique_constraint(
        'unique_agri_period',
        'agri_production_detail',
        ['province', 'year', 'quarter', 'month']
    )
    
    # Retail Services Detail
    op.drop_constraint('unique_retail_period', 'retail_services_detail', type_='unique')
    op.create_unique_constraint(
        'unique_retail_period',
        'retail_services_detail',
        ['province', 'year', 'quarter', 'month']
    )
    
    # Export Detail
    op.drop_constraint('unique_export_period', 'export_detail', type_='unique')
    op.create_unique_constraint(
        'unique_export_period',
        'export_detail',
        ['province', 'year', 'quarter', 'month']
    )
    
    # Investment Detail
    op.drop_constraint('unique_investment_period', 'investment_detail', type_='unique')
    op.create_unique_constraint(
        'unique_investment_period',
        'investment_detail',
        ['province', 'year', 'quarter', 'month']
    )
    
    # Budget Revenue Detail
    op.drop_constraint('unique_budget_period', 'budget_revenue_detail', type_='unique')
    op.create_unique_constraint(
        'unique_budget_period',
        'budget_revenue_detail',
        ['province', 'year', 'quarter', 'month']
    )
    
    # CPI Detail
    op.drop_constraint('unique_cpi_period', 'cpi_detail', type_='unique')
    op.create_unique_constraint(
        'unique_cpi_period',
        'cpi_detail',
        ['province', 'year', 'quarter', 'month']
    )
