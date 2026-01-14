"""restructure economic indicators to analysis format

Revision ID: restructure_economic_ind
Revises: add_source_article_fields
Create Date: 2026-01-09

"""
from alembic import op
import sqlalchemy as sa

revision = 'restructure_economic_ind'
down_revision = 'add_source_article_fields'
branch_labels = None
depends_on = None

def upgrade():
    # Thêm các cột phân tích cho từng nhóm chỉ số (với kiểm tra tồn tại)
    from sqlalchemy import inspect
    from alembic import context
    
    connection = context.get_bind()
    inspector = inspect(connection)
    existing_columns = [col['name'] for col in inspector.get_columns('economic_indicators')]
    
    columns_to_add = [
        ('grdp_analysis', sa.Text()),
        ('iip_analysis', sa.Text()),
        ('agricultural_analysis', sa.Text()),
        ('retail_services_analysis', sa.Text()),
        ('export_import_analysis', sa.Text()),
        ('investment_analysis', sa.Text()),
        ('budget_analysis', sa.Text()),
        ('labor_analysis', sa.Text())
    ]
    
    for col_name, col_type in columns_to_add:
        if col_name not in existing_columns:
            op.add_column('economic_indicators', sa.Column(col_name, col_type, nullable=True))

def downgrade():
    op.drop_column('economic_indicators', 'labor_analysis')
    op.drop_column('economic_indicators', 'budget_analysis')
    op.drop_column('economic_indicators', 'investment_analysis')
    op.drop_column('economic_indicators', 'export_import_analysis')
    op.drop_column('economic_indicators', 'retail_services_analysis')
    op.drop_column('economic_indicators', 'agricultural_analysis')
    op.drop_column('economic_indicators', 'iip_analysis')
    op.drop_column('economic_indicators', 'grdp_analysis')
