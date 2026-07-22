"""Add document_type column to important_posts

Revision ID: 20260130_add_document_type
Revises: 
Create Date: 2026-01-30

Thêm column document_type để phân biệt tài liệu internal/external
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '20260130_add_document_type'
down_revision = '20260122_4_economic_tables'  # Kế thừa từ revision trước
branch_labels = None
depends_on = None


def upgrade():
    # Add document_type column to important_posts
    op.add_column('important_posts', sa.Column(
        'document_type', 
        sa.String(50), 
        nullable=True,
        comment='Loại tài liệu: internal, external (null = newspaper/social)'
    ))
    
    # Create index for faster queries
    op.create_index(
        'idx_important_posts_document_type', 
        'important_posts', 
        ['document_type']
    )
    
    # Create composite index for data_type + document_type
    op.create_index(
        'idx_important_posts_data_document_type',
        'important_posts',
        ['data_type', 'document_type']
    )


def downgrade():
    op.drop_index('idx_important_posts_data_document_type', table_name='important_posts')
    op.drop_index('idx_important_posts_document_type', table_name='important_posts')
    op.drop_column('important_posts', 'document_type')
