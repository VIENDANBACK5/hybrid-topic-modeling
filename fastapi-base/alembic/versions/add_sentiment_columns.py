"""Create sentiment_analysis table - Multi-emotion

Revision ID: add_sentiment_table
Revises: 
Create Date: 2025-12-30

Supports 15 emotion types:
- Positive: vui_mừng, ủng_hộ, tin_tưởng, hài_lòng, tự_hào, hy_vọng
- Negative: phẫn_nộ, lo_ngại, thất_vọng, chỉ_trích, buồn_bã, sợ_hãi
- Neutral: trung_lập, hoài_nghi, ngạc_nhiên
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_sentiment_table'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create sentiment_analysis table với 15 sắc thái cảm xúc"""
    op.create_table(
        'sentiment_analysis',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now()),
        
        # Link to article
        sa.Column('article_id', sa.Integer(), sa.ForeignKey('articles.id'), nullable=False),
        
        # Source info (duplicate for fast query)
        sa.Column('source_url', sa.String(2048)),
        sa.Column('source_domain', sa.String(256)),
        sa.Column('title', sa.String(1024)),
        
        # === DETAILED EMOTION (15 types) ===
        sa.Column('emotion', sa.String(30), nullable=False),  # vui_mừng, phẫn_nộ, lo_ngại, etc.
        sa.Column('emotion_vi', sa.String(30)),  # Vui mừng, Phẫn nộ, Lo ngại, etc.
        sa.Column('emotion_icon', sa.String(10)),  # 😊, 😠, 😟, etc.
        
        # === GENERAL GROUP ===
        sa.Column('sentiment_group', sa.String(20), nullable=False),  # positive, negative, neutral
        sa.Column('sentiment_group_vi', sa.String(20)),  # Tích cực, Tiêu cực, Trung lập
        
        # Confidence
        sa.Column('confidence', sa.Float()),
        
        # All emotion scores (JSON)
        sa.Column('emotion_scores', sa.JSON()),  # {"vui_mừng": 0.3, "phẫn_nộ": 0.1, ...}
        
        # Metadata for dashboard
        sa.Column('category', sa.String(256)),
        sa.Column('topic_id', sa.Integer()),
        sa.Column('topic_name', sa.String(512)),
        
        # Time
        sa.Column('published_date', sa.DateTime()),
        sa.Column('analyzed_at', sa.DateTime(), server_default=sa.func.now()),
        
        # Content preview
        sa.Column('content_snippet', sa.Text()),
    )
    
    # Create indexes for Superset queries
    op.create_index('ix_sentiment_emotion', 'sentiment_analysis', ['emotion'])
    op.create_index('ix_sentiment_group', 'sentiment_analysis', ['sentiment_group'])
    op.create_index('ix_sentiment_domain', 'sentiment_analysis', ['source_domain'])
    op.create_index('ix_sentiment_category', 'sentiment_analysis', ['category'])
    op.create_index('ix_sentiment_topic_id', 'sentiment_analysis', ['topic_id'])
    op.create_index('ix_sentiment_published', 'sentiment_analysis', ['published_date'])
    op.create_index('ix_sentiment_article', 'sentiment_analysis', ['article_id'])


def downgrade():
    """Drop sentiment_analysis table"""
    op.drop_index('ix_sentiment_article', table_name='sentiment_analysis')
    op.drop_index('ix_sentiment_published', table_name='sentiment_analysis')
    op.drop_index('ix_sentiment_topic_id', table_name='sentiment_analysis')
    op.drop_index('ix_sentiment_category', table_name='sentiment_analysis')
    op.drop_index('ix_sentiment_domain', table_name='sentiment_analysis')
    op.drop_index('ix_sentiment_group', table_name='sentiment_analysis')
    op.drop_index('ix_sentiment_emotion', table_name='sentiment_analysis')
    op.drop_table('sentiment_analysis')
