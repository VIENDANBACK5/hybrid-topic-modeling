"""Add articles table

Revision ID: add_articles
Revises: initial_
Create Date: 2025-11-29

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision = 'add_articles'
down_revision = 'initial'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'articles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.Float(), nullable=True),
        sa.Column('updated_at', sa.Float(), nullable=True),
        
        # Thông tin nguồn
        sa.Column('url', sa.String(length=2048), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('source', sa.String(length=512), nullable=False),
        sa.Column('domain', sa.String(length=256), nullable=True),
        
        # Nội dung
        sa.Column('title', sa.String(length=1024), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('author', sa.String(length=256), nullable=True),
        sa.Column('published_date', sa.Float(), nullable=True),
        
        # Metadata
        sa.Column('category', sa.String(length=256), nullable=True),
        sa.Column('tags', JSON, nullable=True),
        sa.Column('images', JSON, nullable=True),
        sa.Column('videos', JSON, nullable=True),
        
        # Xử lý
        sa.Column('is_cleaned', sa.Boolean(), default=False),
        sa.Column('is_deduped', sa.Boolean(), default=False),
        sa.Column('word_count', sa.Integer(), nullable=True),
        
        # Topic modeling
        sa.Column('topic_id', sa.Integer(), nullable=True),
        sa.Column('topic_name', sa.String(length=512), nullable=True),
        sa.Column('topic_probability', sa.Float(), nullable=True),
        
        # Crawl metadata
        sa.Column('crawl_params', JSON, nullable=True),
        sa.Column('raw_metadata', JSON, nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('url', name='uq_articles_url')
    )
    
    # Indexes
    op.create_index('ix_articles_url', 'articles', ['url'])
    op.create_index('ix_articles_source', 'articles', ['source'])
    op.create_index('ix_articles_domain', 'articles', ['domain'])
    op.create_index('ix_articles_category', 'articles', ['category'])
    op.create_index('ix_articles_topic_id', 'articles', ['topic_id'])


def downgrade():
    op.drop_index('ix_articles_topic_id', table_name='articles')
    op.drop_index('ix_articles_category', table_name='articles')
    op.drop_index('ix_articles_domain', table_name='articles')
    op.drop_index('ix_articles_source', table_name='articles')
    op.drop_index('ix_articles_url', table_name='articles')
    op.drop_table('articles')
