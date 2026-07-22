"""add_sources_table

Revision ID: 061547e4fa95
Revises: add_crawl_history
Create Date: 2025-12-05 03:17:09.927411

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '061547e4fa95'
down_revision: Union[str, None] = 'add_crawl_history'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Only create sources table."""
    # Create sources table
    op.create_table('sources',
    sa.Column('name', sa.String(length=500), nullable=False),
    sa.Column('url', sa.String(length=2048), nullable=False),
    sa.Column('type', sa.String(length=50), nullable=False),
    sa.Column('category', sa.String(length=100), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('domain', sa.String(length=255), nullable=True),
    sa.Column('language', sa.String(length=10), nullable=True),
    sa.Column('country', sa.String(length=10), nullable=True),
    sa.Column('region', sa.String(length=100), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('crawl_frequency', sa.String(length=50), nullable=True),
    sa.Column('last_crawled_at', sa.DateTime(), nullable=True),
    sa.Column('next_crawl_at', sa.DateTime(), nullable=True),
    sa.Column('total_articles', sa.Integer(), nullable=True),
    sa.Column('last_article_count', sa.Integer(), nullable=True),
    sa.Column('success_rate', sa.Integer(), nullable=True),
    sa.Column('contact_info', sa.JSON(), nullable=True),
    sa.Column('tags', sa.JSON(), nullable=True),
    sa.Column('crawl_params', sa.JSON(), nullable=True),
    sa.Column('extra_data', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sources_domain'), 'sources', ['domain'], unique=False)
    op.create_index(op.f('ix_sources_type'), 'sources', ['type'], unique=False)
    op.create_index(op.f('ix_sources_url'), 'sources', ['url'], unique=True)


def downgrade() -> None:
    """Downgrade schema - Drop sources table."""
    op.drop_index(op.f('ix_sources_url'), table_name='sources')
    op.drop_index(op.f('ix_sources_type'), table_name='sources')
    op.drop_index(op.f('ix_sources_domain'), table_name='sources')
    op.drop_table('sources')
