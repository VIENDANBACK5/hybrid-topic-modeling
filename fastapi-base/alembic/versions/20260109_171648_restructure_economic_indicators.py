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
    # Thêm các cột phân tích cho từng nhóm chỉ số
    op.add_column('economic_indicators', sa.Column('grdp_analysis', sa.Text(), nullable=True))
    op.add_column('economic_indicators', sa.Column('iip_analysis', sa.Text(), nullable=True))
    op.add_column('economic_indicators', sa.Column('agricultural_analysis', sa.Text(), nullable=True))
    op.add_column('economic_indicators', sa.Column('retail_services_analysis', sa.Text(), nullable=True))
    op.add_column('economic_indicators', sa.Column('export_import_analysis', sa.Text(), nullable=True))
    op.add_column('economic_indicators', sa.Column('investment_analysis', sa.Text(), nullable=True))
    op.add_column('economic_indicators', sa.Column('budget_analysis', sa.Text(), nullable=True))
    op.add_column('economic_indicators', sa.Column('labor_analysis', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('economic_indicators', 'labor_analysis')
    op.drop_column('economic_indicators', 'budget_analysis')
    op.drop_column('economic_indicators', 'investment_analysis')
    op.drop_column('economic_indicators', 'export_import_analysis')
    op.drop_column('economic_indicators', 'retail_services_analysis')
    op.drop_column('economic_indicators', 'agricultural_analysis')
    op.drop_column('economic_indicators', 'iip_analysis')
    op.drop_column('economic_indicators', 'grdp_analysis')
