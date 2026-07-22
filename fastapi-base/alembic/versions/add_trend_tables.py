"""Add trend analysis tables

Revision ID: add_trend_tables
Revises: add_statistics_tables
Create Date: 2025-12-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_trend_tables'
down_revision = '598f7648e8ea'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Bảng CẢNH BÁO XU HƯỚNG (spike, crisis, drop, viral)
    op.create_table('trend_alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alert_type', sa.String(50), nullable=False),  # spike, crisis, drop, viral
        sa.Column('alert_level', sa.String(20), nullable=False),  # low, medium, high, critical
        sa.Column('alert_status', sa.String(20), default='active'),  # active, acknowledged, resolved
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('topic_id', sa.Integer(), nullable=True),
        sa.Column('topic_name', sa.String(255), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('category_vi', sa.String(100), nullable=True),
        sa.Column('current_count', sa.Integer(), default=0),
        sa.Column('previous_count', sa.Integer(), default=0),
        sa.Column('change_percent', sa.Float(), default=0),
        sa.Column('negative_ratio', sa.Float(), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_trend_alerts_type', 'trend_alerts', ['alert_type'])
    op.create_index('ix_trend_alerts_level', 'trend_alerts', ['alert_level'])
    op.create_index('ix_trend_alerts_status', 'trend_alerts', ['alert_status'])
    op.create_index('ix_trend_alerts_detected', 'trend_alerts', ['detected_at'])
    op.create_index('ix_trend_alerts_topic', 'trend_alerts', ['topic_id'])

    # 2. Bảng THỐNG KÊ HASHTAG
    op.create_table('hashtag_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('period_type', sa.String(20), nullable=False),  # daily, weekly, monthly
        sa.Column('period_start', sa.Date(), nullable=True),
        sa.Column('period_end', sa.Date(), nullable=True),
        sa.Column('hashtag', sa.String(255), nullable=False),
        sa.Column('mention_count', sa.Integer(), default=0),
        sa.Column('previous_count', sa.Integer(), default=0),
        sa.Column('change_percent', sa.Float(), default=0),
        sa.Column('rank', sa.Integer(), nullable=True),
        sa.Column('is_trending', sa.Boolean(), default=False),
        sa.Column('is_new', sa.Boolean(), default=False),
        sa.Column('sentiment_score', sa.Float(), nullable=True),
        sa.Column('related_topics', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('related_categories', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('sample_urls', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_hashtag_stats_period', 'hashtag_stats', ['period_type'])
    op.create_index('ix_hashtag_stats_hashtag', 'hashtag_stats', ['hashtag'])
    op.create_index('ix_hashtag_stats_count', 'hashtag_stats', ['mention_count'])
    op.create_index('ix_hashtag_stats_trending', 'hashtag_stats', ['is_trending'])

    # 3. Bảng NỘI DUNG VIRAL / HOT
    op.create_table('viral_contents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('period_type', sa.String(20), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=True),
        sa.Column('period_end', sa.Date(), nullable=True),
        sa.Column('article_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('source_domain', sa.String(255), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('category_vi', sa.String(100), nullable=True),
        sa.Column('topic_id', sa.Integer(), nullable=True),
        sa.Column('topic_name', sa.String(255), nullable=True),
        sa.Column('emotion', sa.String(50), nullable=True),
        sa.Column('emotion_vi', sa.String(50), nullable=True),
        sa.Column('sentiment_score', sa.Float(), nullable=True),
        sa.Column('viral_score', sa.Float(), default=0),
        sa.Column('engagement_score', sa.Float(), default=0),
        sa.Column('rank', sa.Integer(), nullable=True),
        sa.Column('is_hot', sa.Boolean(), default=False),
        sa.Column('is_viral', sa.Boolean(), default=False),
        sa.Column('hashtags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('keywords', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_viral_contents_period', 'viral_contents', ['period_type'])
    op.create_index('ix_viral_contents_score', 'viral_contents', ['viral_score'])
    op.create_index('ix_viral_contents_hot', 'viral_contents', ['is_hot'])
    op.create_index('ix_viral_contents_article', 'viral_contents', ['article_id'])

    # 4. Bảng XU HƯỚNG THEO DANH MỤC
    op.create_table('category_trend_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('period_type', sa.String(20), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=True),
        sa.Column('period_end', sa.Date(), nullable=True),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('category_vi', sa.String(100), nullable=True),
        sa.Column('category_icon', sa.String(10), nullable=True),
        sa.Column('total_mentions', sa.Integer(), default=0),
        sa.Column('previous_mentions', sa.Integer(), default=0),
        sa.Column('change_percent', sa.Float(), default=0),
        sa.Column('positive_count', sa.Integer(), default=0),
        sa.Column('negative_count', sa.Integer(), default=0),
        sa.Column('neutral_count', sa.Integer(), default=0),
        sa.Column('sentiment_score', sa.Float(), nullable=True),
        sa.Column('dominant_emotion', sa.String(50), nullable=True),
        sa.Column('emotion_distribution', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_trending_up', sa.Boolean(), default=False),
        sa.Column('is_trending_down', sa.Boolean(), default=False),
        sa.Column('has_crisis', sa.Boolean(), default=False),
        sa.Column('top_topics', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('top_keywords', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('top_hashtags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('rank_by_mention', sa.Integer(), nullable=True),
        sa.Column('rank_by_change', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_category_trend_period', 'category_trend_stats', ['period_type'])
    op.create_index('ix_category_trend_category', 'category_trend_stats', ['category'])
    op.create_index('ix_category_trend_mentions', 'category_trend_stats', ['total_mentions'])
    op.create_index('ix_category_trend_crisis', 'category_trend_stats', ['has_crisis'])


def downgrade():
    op.drop_table('category_trend_stats')
    op.drop_table('viral_contents')
    op.drop_table('hashtag_stats')
    op.drop_table('trend_alerts')
