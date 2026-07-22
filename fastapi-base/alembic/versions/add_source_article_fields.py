"""add source article fields to economic indicators

Revision ID: add_source_article_fields
Revises: add_summary_economic_ind
Create Date: 2026-01-09 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_source_article_fields'
down_revision: Union[str, None] = 'add_summary_economic_ind'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add source article fields to economic_indicators table"""
    # Add columns for linking to source articles
    op.add_column('economic_indicators', 
                  sa.Column('source_article_id', sa.Integer(), nullable=True))
    op.add_column('economic_indicators', 
                  sa.Column('source_article_url', sa.String(length=2048), nullable=True))
    op.add_column('economic_indicators', 
                  sa.Column('source_article_domain', sa.String(length=256), nullable=True))
    
    # Create foreign key constraint
    op.create_foreign_key(
        'fk_economic_indicators_source_article',
        'economic_indicators', 'articles',
        ['source_article_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Create index for faster lookups
    op.create_index('ix_economic_indicators_source_article_id', 
                    'economic_indicators', ['source_article_id'])


def downgrade() -> None:
    """Remove source article fields from economic_indicators table"""
    op.drop_index('ix_economic_indicators_source_article_id', 
                  table_name='economic_indicators')
    op.drop_constraint('fk_economic_indicators_source_article', 
                       'economic_indicators', type_='foreignkey')
    op.drop_column('economic_indicators', 'source_article_domain')
    op.drop_column('economic_indicators', 'source_article_url')
    op.drop_column('economic_indicators', 'source_article_id')
