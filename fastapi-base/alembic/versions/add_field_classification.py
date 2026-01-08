"""Add field classification tables

Revision ID: add_field_classification
Revises: add_trend_tables
Create Date: 2026-01-07

Tables:
- fields: Lưu các lĩnh vực phân loại
- article_field_classifications: Phân loại bài viết theo lĩnh vực
- field_statistics: Thống kê số lượng bài viết theo lĩnh vực
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision = 'add_field_classification'
down_revision = 'add_trend_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Create field classification tables"""
    
    # ========== FIELDS TABLE ==========
    op.create_table(
        'fields',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.Float(), nullable=False),
        sa.Column('updated_at', sa.Float(), nullable=False),
        
        sa.Column('name', sa.String(256), unique=True, nullable=False, index=True),
        sa.Column('description', sa.Text()),
        sa.Column('keywords', JSON),
        sa.Column('order_index', sa.Integer(), default=0),
    )
    
    # ========== ARTICLE FIELD CLASSIFICATIONS TABLE ==========
    op.create_table(
        'article_field_classifications',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.Float(), nullable=False),
        sa.Column('updated_at', sa.Float(), nullable=False),
        
        sa.Column('article_id', sa.Integer(), nullable=False, index=True),
        sa.Column('field_id', sa.Integer(), nullable=False, index=True),
        sa.Column('confidence_score', sa.Float(), default=1.0),
        sa.Column('matched_keywords', JSON),
        sa.Column('classification_method', sa.String(50), default='keyword'),
        
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['field_id'], ['fields.id'], ondelete='CASCADE'),
    )
    
    # ========== FIELD STATISTICS TABLE ==========
    op.create_table(
        'field_statistics',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.Float(), nullable=False),
        sa.Column('updated_at', sa.Float(), nullable=False),
        
        sa.Column('field_id', sa.Integer(), nullable=False, index=True),
        sa.Column('field_name', sa.String(256), nullable=False),
        
        # Thống kê số lượng
        sa.Column('total_articles', sa.Integer(), default=0),
        sa.Column('articles_today', sa.Integer(), default=0),
        sa.Column('articles_this_week', sa.Integer(), default=0),
        sa.Column('articles_this_month', sa.Integer(), default=0),
        
        # Thống kê engagement
        sa.Column('avg_likes', sa.Float(), default=0),
        sa.Column('avg_shares', sa.Float(), default=0),
        sa.Column('avg_comments', sa.Float(), default=0),
        sa.Column('total_engagement', sa.Integer(), default=0),
        
        # Thống kê theo nguồn
        sa.Column('source_distribution', JSON),
        sa.Column('province_distribution', JSON),
        
        sa.Column('stats_date', sa.Float()),
        
        sa.ForeignKeyConstraint(['field_id'], ['fields.id'], ondelete='CASCADE'),
    )
    
    # Create indexes
    op.create_index('idx_article_field_article', 'article_field_classifications', ['article_id'])
    op.create_index('idx_article_field_field', 'article_field_classifications', ['field_id'])
    op.create_index('idx_field_stats_field', 'field_statistics', ['field_id'])
    op.create_index('idx_field_stats_date', 'field_statistics', ['stats_date'])


def downgrade():
    """Drop field classification tables"""
    op.drop_index('idx_field_stats_date', 'field_statistics')
    op.drop_index('idx_field_stats_field', 'field_statistics')
    op.drop_index('idx_article_field_field', 'article_field_classifications')
    op.drop_index('idx_article_field_article', 'article_field_classifications')
    
    op.drop_table('field_statistics')
    op.drop_table('article_field_classifications')
    op.drop_table('fields')
