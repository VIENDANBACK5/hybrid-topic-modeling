"""add crawl history

Revision ID: add_crawl_history
Revises: add_articles
Create Date: 2025-11-28 17:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_crawl_history'
down_revision = 'add_articles'
branch_labels = None
depends_on = None


def upgrade():
    # Create crawl_history table
    op.create_table(
        'crawl_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(length=2048), nullable=False),
        sa.Column('domain', sa.String(length=256), nullable=False),
        sa.Column('category', sa.String(length=256), nullable=True),
        sa.Column('url_pattern', sa.String(length=512), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('discovered_at', sa.DateTime(), nullable=False),
        sa.Column('last_crawled_at', sa.DateTime(), nullable=True),
        sa.Column('last_checked_at', sa.DateTime(), nullable=True),
        sa.Column('crawl_count', sa.Integer(), nullable=True),
        sa.Column('has_article', sa.Boolean(), nullable=True),
        sa.Column('article_id', sa.Integer(), nullable=True),
        sa.Column('is_listing', sa.Boolean(), nullable=True),
        sa.Column('child_links_count', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.String(length=1024), nullable=True),
        sa.Column('page_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('crawl_params', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_crawl_history_url', 'crawl_history', ['url'], unique=True)
    op.create_index('ix_crawl_history_domain', 'crawl_history', ['domain'], unique=False)
    op.create_index('ix_crawl_history_category', 'crawl_history', ['category'], unique=False)
    op.create_index('ix_crawl_history_status', 'crawl_history', ['status'], unique=False)
    op.create_index('ix_crawl_history_last_checked', 'crawl_history', ['last_checked_at'], unique=False)
    
    # Index for finding articles needing crawl
    op.create_index('ix_crawl_history_pending', 'crawl_history', ['status', 'domain'], unique=False)


def downgrade():
    op.drop_index('ix_crawl_history_pending', table_name='crawl_history')
    op.drop_index('ix_crawl_history_last_checked', table_name='crawl_history')
    op.drop_index('ix_crawl_history_status', table_name='crawl_history')
    op.drop_index('ix_crawl_history_category', table_name='crawl_history')
    op.drop_index('ix_crawl_history_domain', table_name='crawl_history')
    op.drop_index('ix_crawl_history_url', table_name='crawl_history')
    op.drop_table('crawl_history')
