"""add_field_sentiments_table

Revision ID: 63bc2c0fcb48
Revises: 7984bf821c50
Create Date: 2026-01-08 10:48:05.126468

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '63bc2c0fcb48'
down_revision: Union[str, None] = '7984bf821c50'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - only create field_sentiments table"""
    op.create_table('field_sentiments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.Float(), nullable=False),
        sa.Column('updated_at', sa.Float(), nullable=False),
        sa.Column('field_id', sa.Integer(), nullable=False),
        sa.Column('field_name', sa.String(length=256), nullable=False),
        sa.Column('period_type', sa.String(length=20), nullable=False),
        sa.Column('period_date', sa.Date(), nullable=False),
        sa.Column('period_start', sa.Float(), nullable=False),
        sa.Column('period_end', sa.Float(), nullable=False),
        sa.Column('total_articles', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('analyzed_articles', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('sentiment_positive', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('sentiment_negative', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('sentiment_neutral', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('positive_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('negative_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('neutral_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('avg_sentiment_score', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('sentiment_distribution', sa.JSON(), nullable=True),
        sa.Column('top_positive_articles', sa.JSON(), nullable=True),
        sa.Column('top_negative_articles', sa.JSON(), nullable=True),
        sa.Column('emotions', sa.JSON(), nullable=True),
        sa.Column('positive_keywords', sa.JSON(), nullable=True),
        sa.Column('negative_keywords', sa.JSON(), nullable=True),
        sa.Column('sentiment_trend', sa.String(length=20), nullable=True),
        sa.Column('trend_description', sa.Text(), nullable=True),
        sa.Column('analysis_method', sa.String(length=50), nullable=True, server_default='llm'),
        sa.Column('model_used', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['field_id'], ['fields.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_field_sentiments_field_id'), 'field_sentiments', ['field_id'], unique=False)
    op.create_index(op.f('ix_field_sentiments_period_date'), 'field_sentiments', ['period_date'], unique=False)
    op.create_index(op.f('ix_field_sentiments_period_type'), 'field_sentiments', ['period_type'], unique=False)


def downgrade() -> None:
    """Downgrade schema"""
    op.drop_index(op.f('ix_field_sentiments_period_type'), table_name='field_sentiments')
    op.drop_index(op.f('ix_field_sentiments_period_date'), table_name='field_sentiments')
    op.drop_index(op.f('ix_field_sentiments_field_id'), table_name='field_sentiments')
    op.drop_table('field_sentiments')
