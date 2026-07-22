"""Add document_type to 15 detail tables

Revision ID: 20260130_add_document_type_details
Revises: 20260130_add_document_type
Create Date: 2026-01-30

Add document_type column to 15 indicator detail tables to classify internal/external sources
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '20260130_doc_type_details'
down_revision = '20260130_add_document_type'
branch_labels = None
depends_on = None


# 15 bảng detail cần thêm column
DETAIL_TABLES = [
    # Kinh tế
    'grdp_detail',
    'iip_detail',
    'cpi_detail',
    'digital_transformation_detail',
    'pii_detail',
    'fdi_detail',
    # Xã hội
    'cadre_statistics_detail',
    'highschool_graduation_detail',
    'tvet_employment_detail',
    'health_statistics_detail',
    'culture_lifestyle_stats_detail',
    'security_detail',
    # Hành chính công
    'sipas_detail',
    'par_index_detail',
    # Môi trường
    'air_quality_detail',
]


def upgrade():
    """Add document_type column to 15 detail tables"""
    for table_name in DETAIL_TABLES:
        # Add column
        op.add_column(table_name, sa.Column(
            'document_type',
            sa.String(20),
            nullable=True,
            server_default='external',
            comment='Source document type: internal or external'
        ))
        
        # Create index for faster queries
        index_name = f'ix_{table_name}_document_type'
        op.create_index(index_name, table_name, ['document_type'])


def downgrade():
    """Remove document_type column from 15 detail tables"""
    for table_name in DETAIL_TABLES:
        # Drop index
        index_name = f'ix_{table_name}_document_type'
        op.drop_index(index_name, table_name=table_name)
        
        # Drop column
        op.drop_column(table_name, 'document_type')
