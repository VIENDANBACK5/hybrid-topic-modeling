"""Create statistics tables for Superset

Revision ID: add_statistics_tables
Revises: add_sentiment_table
Create Date: 2025-12-30

Tables:
- trend_reports: Báo cáo xu hướng tuần/tháng
- hot_topics: Chủ đề hot/khủng hoảng
- keyword_stats: Thống kê từ khóa (WordCloud)
- topic_mention_stats: Thống kê đề cập theo chủ đề
- website_activity_stats: Thống kê website theo chủ đề
- social_activity_stats: Thống kê mạng xã hội
- daily_snapshots: Snapshot hàng ngày
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision = 'add_statistics_tables'
down_revision = 'add_sentiment_table'
branch_labels = None
depends_on = None


def upgrade():
    """Create all statistics tables"""
    
    # ========== TREND REPORTS ==========
    op.create_table(
        'trend_reports',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now()),
        
        sa.Column('period_type', sa.String(20), nullable=False),  # weekly, monthly
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('period_label', sa.String(50)),
        
        sa.Column('total_mentions', sa.Integer(), default=0),
        sa.Column('total_sources', sa.Integer(), default=0),
        sa.Column('total_topics', sa.Integer(), default=0),
        
        sa.Column('positive_count', sa.Integer(), default=0),
        sa.Column('negative_count', sa.Integer(), default=0),
        sa.Column('neutral_count', sa.Integer(), default=0),
        sa.Column('positive_ratio', sa.Float()),
        sa.Column('negative_ratio', sa.Float()),
        
        sa.Column('emotion_distribution', JSON),
        sa.Column('mention_change', sa.Float()),
        sa.Column('sentiment_change', sa.Float()),
        sa.Column('top_keywords', JSON),
        sa.Column('top_sources', JSON),
    )
    op.create_index('ix_trend_period_type', 'trend_reports', ['period_type'])
    op.create_index('ix_trend_period_start', 'trend_reports', ['period_start'])
    
    # ========== HOT TOPICS ==========
    op.create_table(
        'hot_topics',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now()),
        
        sa.Column('period_type', sa.String(20), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        
        sa.Column('topic_id', sa.Integer()),
        sa.Column('topic_name', sa.String(512)),
        sa.Column('topic_keywords', JSON),
        
        sa.Column('mention_count', sa.Integer(), default=0),
        sa.Column('mention_velocity', sa.Float()),
        sa.Column('engagement_score', sa.Float()),
        sa.Column('hot_score', sa.Float()),
        
        sa.Column('is_hot', sa.Boolean(), default=False),
        sa.Column('is_crisis', sa.Boolean(), default=False),
        sa.Column('is_trending_up', sa.Boolean(), default=False),
        sa.Column('is_trending_down', sa.Boolean(), default=False),
        
        sa.Column('positive_count', sa.Integer(), default=0),
        sa.Column('negative_count', sa.Integer(), default=0),
        sa.Column('neutral_count', sa.Integer(), default=0),
        sa.Column('crisis_score', sa.Float()),
        
        sa.Column('dominant_emotion', sa.String(30)),
        sa.Column('emotion_distribution', JSON),
        sa.Column('sample_titles', JSON),
        sa.Column('rank', sa.Integer()),
    )
    op.create_index('ix_hot_period_type', 'hot_topics', ['period_type'])
    op.create_index('ix_hot_period_start', 'hot_topics', ['period_start'])
    op.create_index('ix_hot_topic_id', 'hot_topics', ['topic_id'])
    op.create_index('ix_hot_is_hot', 'hot_topics', ['is_hot'])
    op.create_index('ix_hot_is_crisis', 'hot_topics', ['is_crisis'])
    op.create_index('ix_hot_score', 'hot_topics', ['hot_score'])
    
    # ========== KEYWORD STATS ==========
    op.create_table(
        'keyword_stats',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now()),
        
        sa.Column('period_type', sa.String(20), nullable=False),
        sa.Column('period_start', sa.Date()),
        sa.Column('period_end', sa.Date()),
        
        sa.Column('keyword', sa.String(256), nullable=False),
        sa.Column('keyword_normalized', sa.String(256)),
        
        sa.Column('mention_count', sa.Integer(), default=0),
        sa.Column('document_count', sa.Integer(), default=0),
        
        sa.Column('positive_count', sa.Integer(), default=0),
        sa.Column('negative_count', sa.Integer(), default=0),
        sa.Column('neutral_count', sa.Integer(), default=0),
        sa.Column('sentiment_score', sa.Float()),
        
        sa.Column('related_topics', JSON),
        sa.Column('top_sources', JSON),
        sa.Column('weight', sa.Float()),
    )
    op.create_index('ix_keyword_period_type', 'keyword_stats', ['period_type'])
    op.create_index('ix_keyword_period_start', 'keyword_stats', ['period_start'])
    op.create_index('ix_keyword_keyword', 'keyword_stats', ['keyword'])
    op.create_index('ix_keyword_count', 'keyword_stats', ['mention_count'])
    
    # ========== TOPIC MENTION STATS ==========
    op.create_table(
        'topic_mention_stats',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now()),
        
        sa.Column('period_type', sa.String(20), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date()),
        
        sa.Column('topic_id', sa.Integer()),
        sa.Column('topic_name', sa.String(512)),
        sa.Column('category', sa.String(256)),
        
        sa.Column('total_mentions', sa.Integer(), default=0),
        sa.Column('unique_sources', sa.Integer(), default=0),
        
        sa.Column('positive_mentions', sa.Integer(), default=0),
        sa.Column('negative_mentions', sa.Integer(), default=0),
        sa.Column('neutral_mentions', sa.Integer(), default=0),
        sa.Column('emotion_breakdown', JSON),
        
        sa.Column('sentiment_score', sa.Float()),
        sa.Column('engagement_score', sa.Float()),
        sa.Column('mention_change_pct', sa.Float()),
        sa.Column('sentiment_change', sa.Float()),
        
        sa.Column('rank_by_mention', sa.Integer()),
        sa.Column('rank_by_negative', sa.Integer()),
    )
    op.create_index('ix_topic_mention_period_type', 'topic_mention_stats', ['period_type'])
    op.create_index('ix_topic_mention_period_start', 'topic_mention_stats', ['period_start'])
    op.create_index('ix_topic_mention_topic_id', 'topic_mention_stats', ['topic_id'])
    op.create_index('ix_topic_mention_category', 'topic_mention_stats', ['category'])
    
    # ========== WEBSITE ACTIVITY STATS ==========
    op.create_table(
        'website_activity_stats',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now()),
        
        sa.Column('period_type', sa.String(20), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date()),
        
        sa.Column('domain', sa.String(256), nullable=False),
        sa.Column('website_name', sa.String(256)),
        sa.Column('website_type', sa.String(50)),
        
        sa.Column('topic_id', sa.Integer()),
        sa.Column('topic_name', sa.String(512)),
        sa.Column('category', sa.String(256)),
        
        sa.Column('article_count', sa.Integer(), default=0),
        sa.Column('total_mentions', sa.Integer(), default=0),
        
        sa.Column('positive_count', sa.Integer(), default=0),
        sa.Column('negative_count', sa.Integer(), default=0),
        sa.Column('neutral_count', sa.Integer(), default=0),
        sa.Column('avg_sentiment_score', sa.Float()),
        
        sa.Column('emotion_distribution', JSON),
        sa.Column('dominant_emotion', sa.String(30)),
        
        sa.Column('avg_articles_per_day', sa.Float()),
        sa.Column('peak_day', sa.Date()),
        
        sa.Column('rank_overall', sa.Integer()),
        sa.Column('rank_in_topic', sa.Integer()),
    )
    op.create_index('ix_website_period_type', 'website_activity_stats', ['period_type'])
    op.create_index('ix_website_period_start', 'website_activity_stats', ['period_start'])
    op.create_index('ix_website_domain', 'website_activity_stats', ['domain'])
    op.create_index('ix_website_topic_id', 'website_activity_stats', ['topic_id'])
    op.create_index('ix_website_type', 'website_activity_stats', ['website_type'])
    
    # ========== SOCIAL ACTIVITY STATS ==========
    op.create_table(
        'social_activity_stats',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now()),
        
        sa.Column('period_type', sa.String(20), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date()),
        
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('account_id', sa.String(256)),
        sa.Column('account_name', sa.String(256)),
        sa.Column('account_url', sa.String(1024)),
        
        sa.Column('topic_id', sa.Integer()),
        sa.Column('topic_name', sa.String(512)),
        sa.Column('category', sa.String(256)),
        
        sa.Column('post_count', sa.Integer(), default=0),
        sa.Column('total_mentions', sa.Integer(), default=0),
        
        sa.Column('total_likes', sa.Integer(), default=0),
        sa.Column('total_comments', sa.Integer(), default=0),
        sa.Column('total_shares', sa.Integer(), default=0),
        sa.Column('avg_engagement', sa.Float()),
        
        sa.Column('positive_count', sa.Integer(), default=0),
        sa.Column('negative_count', sa.Integer(), default=0),
        sa.Column('neutral_count', sa.Integer(), default=0),
        sa.Column('avg_sentiment_score', sa.Float()),
        
        sa.Column('emotion_distribution', JSON),
        sa.Column('dominant_emotion', sa.String(30)),
        
        sa.Column('estimated_reach', sa.Integer()),
        sa.Column('influence_score', sa.Float()),
        
        sa.Column('rank_in_platform', sa.Integer()),
        sa.Column('rank_in_topic', sa.Integer()),
        sa.Column('rank_overall', sa.Integer()),
    )
    op.create_index('ix_social_period_type', 'social_activity_stats', ['period_type'])
    op.create_index('ix_social_period_start', 'social_activity_stats', ['period_start'])
    op.create_index('ix_social_platform', 'social_activity_stats', ['platform'])
    op.create_index('ix_social_account', 'social_activity_stats', ['account_name'])
    op.create_index('ix_social_topic_id', 'social_activity_stats', ['topic_id'])
    
    # ========== DAILY SNAPSHOTS ==========
    op.create_table(
        'daily_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now()),
        
        sa.Column('snapshot_date', sa.Date(), nullable=False, unique=True),
        
        sa.Column('total_articles', sa.Integer(), default=0),
        sa.Column('total_sources', sa.Integer(), default=0),
        
        sa.Column('positive_count', sa.Integer(), default=0),
        sa.Column('negative_count', sa.Integer(), default=0),
        sa.Column('neutral_count', sa.Integer(), default=0),
        
        sa.Column('emotion_counts', JSON),
        sa.Column('top_topics', JSON),
        sa.Column('top_keywords', JSON),
        sa.Column('top_sources', JSON),
        
        sa.Column('crisis_topics', JSON),
        sa.Column('trending_up', JSON),
        sa.Column('trending_down', JSON),
    )
    op.create_index('ix_snapshot_date', 'daily_snapshots', ['snapshot_date'])


def downgrade():
    """Drop all statistics tables"""
    # Daily snapshots
    op.drop_index('ix_snapshot_date', table_name='daily_snapshots')
    op.drop_table('daily_snapshots')
    
    # Social activity
    op.drop_index('ix_social_topic_id', table_name='social_activity_stats')
    op.drop_index('ix_social_account', table_name='social_activity_stats')
    op.drop_index('ix_social_platform', table_name='social_activity_stats')
    op.drop_index('ix_social_period_start', table_name='social_activity_stats')
    op.drop_index('ix_social_period_type', table_name='social_activity_stats')
    op.drop_table('social_activity_stats')
    
    # Website activity
    op.drop_index('ix_website_type', table_name='website_activity_stats')
    op.drop_index('ix_website_topic_id', table_name='website_activity_stats')
    op.drop_index('ix_website_domain', table_name='website_activity_stats')
    op.drop_index('ix_website_period_start', table_name='website_activity_stats')
    op.drop_index('ix_website_period_type', table_name='website_activity_stats')
    op.drop_table('website_activity_stats')
    
    # Topic mention
    op.drop_index('ix_topic_mention_category', table_name='topic_mention_stats')
    op.drop_index('ix_topic_mention_topic_id', table_name='topic_mention_stats')
    op.drop_index('ix_topic_mention_period_start', table_name='topic_mention_stats')
    op.drop_index('ix_topic_mention_period_type', table_name='topic_mention_stats')
    op.drop_table('topic_mention_stats')
    
    # Keyword stats
    op.drop_index('ix_keyword_count', table_name='keyword_stats')
    op.drop_index('ix_keyword_keyword', table_name='keyword_stats')
    op.drop_index('ix_keyword_period_start', table_name='keyword_stats')
    op.drop_index('ix_keyword_period_type', table_name='keyword_stats')
    op.drop_table('keyword_stats')
    
    # Hot topics
    op.drop_index('ix_hot_score', table_name='hot_topics')
    op.drop_index('ix_hot_is_crisis', table_name='hot_topics')
    op.drop_index('ix_hot_is_hot', table_name='hot_topics')
    op.drop_index('ix_hot_topic_id', table_name='hot_topics')
    op.drop_index('ix_hot_period_start', table_name='hot_topics')
    op.drop_index('ix_hot_period_type', table_name='hot_topics')
    op.drop_table('hot_topics')
    
    # Trend reports
    op.drop_index('ix_trend_period_start', table_name='trend_reports')
    op.drop_index('ix_trend_period_type', table_name='trend_reports')
    op.drop_table('trend_reports')
