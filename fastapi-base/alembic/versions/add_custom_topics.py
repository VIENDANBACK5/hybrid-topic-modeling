"""
Add custom topics tables

Revision ID: add_custom_topics
Create Date: 2026-01-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = 'add_custom_topics'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create custom_topics table
    op.create_table(
        'custom_topics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('keywords', JSONB, nullable=False),
        sa.Column('keywords_weight', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('example_docs', JSONB, nullable=True),
        sa.Column('example_weight', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('negative_keywords', JSONB, nullable=True),
        sa.Column('classification_method', sa.String(50), nullable=False, server_default='hybrid'),
        sa.Column('min_confidence', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('color', sa.String(7), nullable=False, server_default='#3B82F6'),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('article_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_classified_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('slug'),
        sa.ForeignKeyConstraint(['parent_id'], ['custom_topics.id'], ondelete='SET NULL')
    )
    
    # Indexes for custom_topics
    op.create_index('ix_custom_topics_name', 'custom_topics', ['name'])
    op.create_index('ix_custom_topics_slug', 'custom_topics', ['slug'])
    op.create_index('ix_custom_topics_is_active', 'custom_topics', ['is_active'])
    
    # Create article_custom_topics table
    op.create_table(
        'article_custom_topics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('topic_id', sa.Integer(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('method', sa.String(50), nullable=True),
        sa.Column('keyword_score', sa.Float(), nullable=True),
        sa.Column('embedding_score', sa.Float(), nullable=True),
        sa.Column('llm_score', sa.Float(), nullable=True),
        sa.Column('is_manual', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('manual_by', sa.String(100), nullable=True),
        sa.Column('classified_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['topic_id'], ['custom_topics.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('article_id', 'topic_id', name='uq_article_custom_topic')
    )
    
    # Indexes for article_custom_topics
    op.create_index('ix_article_custom_topics_article_id', 'article_custom_topics', ['article_id'])
    op.create_index('ix_article_custom_topics_topic_id', 'article_custom_topics', ['topic_id'])
    op.create_index('ix_article_custom_topics_confidence', 'article_custom_topics', ['confidence'])
    op.create_index('ix_article_custom_topics_classified_at', 'article_custom_topics', ['classified_at'])
    
    # Create topic_classification_logs table
    op.create_table(
        'topic_classification_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('topic_id', sa.Integer(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('method', sa.String(50), nullable=True),
        sa.Column('accepted', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('scores_detail', JSONB, nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('classified_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['topic_id'], ['custom_topics.id'], ondelete='CASCADE')
    )
    
    # Indexes for logs
    op.create_index('ix_topic_classification_logs_article_id', 'topic_classification_logs', ['article_id'])
    op.create_index('ix_topic_classification_logs_topic_id', 'topic_classification_logs', ['topic_id'])
    op.create_index('ix_topic_classification_logs_classified_at', 'topic_classification_logs', ['classified_at'])
    
    # Create topic_templates table
    op.create_table(
        'topic_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('topics_data', JSONB, nullable=False),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('ix_topic_templates_category', 'topic_templates', ['category'])


def downgrade():
    op.drop_table('topic_templates')
    op.drop_table('topic_classification_logs')
    op.drop_table('article_custom_topics')
    op.drop_table('custom_topics')
