"""Add field summaries table

Revision ID: add_field_summaries
Revises: add_field_classification
Create Date: 2026-01-08

Table:
- field_summaries: Tóm tắt thông tin gần đây theo lĩnh vực
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision = 'add_field_summaries'
down_revision = 'add_field_classification'
branch_labels = None
depends_on = None


def upgrade():
    """Create field summaries table"""
    
    op.create_table(
        'field_summaries',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.Float(), nullable=False),
        sa.Column('updated_at', sa.Float(), nullable=False),
        
        sa.Column('field_id', sa.Integer(), nullable=False, index=True),
        sa.Column('field_name', sa.String(256), nullable=False),
        
        # Thời gian
        sa.Column('summary_period', sa.String(20), nullable=False, index=True),
        sa.Column('period_start', sa.Float(), nullable=False),
        sa.Column('period_end', sa.Float(), nullable=False),
        sa.Column('summary_date', sa.Date(), nullable=False, index=True),
        
        # Thống kê
        sa.Column('total_articles', sa.Integer(), default=0),
        sa.Column('avg_engagement', sa.Float(), default=0),
        sa.Column('top_sources', JSON),
        
        # Nội dung
        sa.Column('key_topics', JSON),
        sa.Column('summary_text', sa.Text()),
        sa.Column('sentiment_overview', JSON),
        
        # Bài viết nổi bật
        sa.Column('top_articles', JSON),
        sa.Column('trending_keywords', JSON),
        
        # Metadata
        sa.Column('generation_method', sa.String(50), default='llm'),
        sa.Column('model_used', sa.String(100)),
        
        sa.ForeignKeyConstraint(['field_id'], ['fields.id'], ondelete='CASCADE'),
    )
    
    # Create indexes
    op.create_index('idx_field_summaries_field', 'field_summaries', ['field_id'])
    op.create_index('idx_field_summaries_period', 'field_summaries', ['summary_period'])
    op.create_index('idx_field_summaries_date', 'field_summaries', ['summary_date'])
    op.create_index('idx_field_summaries_field_date', 'field_summaries', ['field_id', 'summary_date'])


def downgrade():
    """Drop field summaries table"""
    op.drop_index('idx_field_summaries_field_date', 'field_summaries')
    op.drop_index('idx_field_summaries_date', 'field_summaries')
    op.drop_index('idx_field_summaries_period', 'field_summaries')
    op.drop_index('idx_field_summaries_field', 'field_summaries')
    op.drop_table('field_summaries')
