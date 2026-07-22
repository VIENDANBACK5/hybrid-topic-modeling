"""Add important_posts table - Lưu trữ các bài viết báo chí đặc biệt quan trọng

Revision ID: 20260120_important_posts
Revises: 20260120_health_stats
Create Date: 2026-01-20 17:09:23.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260120_important_posts'
down_revision = '20260120_health_stats'
branch_labels = None
depends_on = None


def upgrade():
    """Create important_posts table"""
    op.create_table(
        'important_posts',
        
        # Primary key and timestamps
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('created_at', sa.Float(), nullable=True),
        sa.Column('updated_at', sa.Float(), nullable=True),
        
        # Core content
        sa.Column('url', sa.String(length=2048), nullable=False, comment='URL bài viết gốc'),
        sa.Column('title', sa.String(length=1024), nullable=False, comment='Tiêu đề bài viết'),
        sa.Column('content', sa.Text(), nullable=False, comment='Nội dung đầy đủ bài viết'),
        
        # Classification
        sa.Column('data_type', sa.String(length=50), nullable=False, server_default='newspaper', 
                  comment='Loại dữ liệu: newspaper, social, etc.'),
        sa.Column('type_newspaper', sa.String(length=100), nullable=True, 
                  comment='Phân loại báo: medical, economic, social, etc.'),
        
        # Original source metadata
        sa.Column('original_id', sa.Integer(), nullable=True, comment='ID từ hệ thống nguồn'),
        sa.Column('original_created_at', sa.Float(), nullable=True, comment='Thời gian tạo từ hệ thống nguồn'),
        sa.Column('original_updated_at', sa.Float(), nullable=True, comment='Thời gian cập nhật từ hệ thống nguồn'),
        
        # Metadata (JSON)
        sa.Column('meta_data', postgresql.JSON(astext_type=sa.Text()), nullable=True,
                  comment='Metadata từ nguồn bao gồm: date, statistics, organizations, author'),
        
        # Extracted fields for faster queries
        sa.Column('author', sa.String(length=512), nullable=True, comment='Tác giả bài viết'),
        sa.Column('published_date', sa.String(length=100), nullable=True, 
                  comment='Ngày xuất bản (format từ nguồn)'),
        
        # Denormalized arrays for search
        sa.Column('statistics', postgresql.JSON(astext_type=sa.Text()), nullable=True,
                  comment='Danh sách các số liệu thống kê trong bài'),
        sa.Column('organizations', postgresql.JSON(astext_type=sa.Text()), nullable=True,
                  comment='Danh sách tổ chức được nhắc đến'),
        
        # Featured flags
        sa.Column('is_featured', sa.Integer(), nullable=True, server_default='1',
                  comment='Đánh dấu bài viết nổi bật (1=featured, 0=normal)'),
        sa.Column('importance_score', sa.Float(), nullable=True, 
                  comment='Điểm đánh giá mức độ quan trọng'),
        
        # Additional classification
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=True,
                  comment='Tags phân loại bổ sung'),
        sa.Column('categories', postgresql.JSON(astext_type=sa.Text()), nullable=True,
                  comment='Các danh mục liên quan'),
        
        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('url', name='uq_important_posts_url')
    )
    
    # Create indexes
    op.create_index('ix_important_posts_url', 'important_posts', ['url'])
    op.create_index('ix_important_posts_data_type', 'important_posts', ['data_type'])
    op.create_index('ix_important_posts_type_newspaper', 'important_posts', ['type_newspaper'])
    op.create_index('ix_important_posts_is_featured', 'important_posts', ['is_featured'])
    
    # Composite indexes
    op.create_index('idx_data_type_newspaper', 'important_posts', ['data_type', 'type_newspaper'])
    op.create_index('idx_featured_type', 'important_posts', ['is_featured', 'type_newspaper'])
    op.create_index('idx_importance', 'important_posts', ['importance_score'])


def downgrade():
    """Drop important_posts table"""
    op.drop_index('idx_importance', table_name='important_posts')
    op.drop_index('idx_featured_type', table_name='important_posts')
    op.drop_index('idx_data_type_newspaper', table_name='important_posts')
    op.drop_index('ix_important_posts_is_featured', table_name='important_posts')
    op.drop_index('ix_important_posts_type_newspaper', table_name='important_posts')
    op.drop_index('ix_important_posts_data_type', table_name='important_posts')
    op.drop_index('ix_important_posts_url', table_name='important_posts')
    op.drop_table('important_posts')
