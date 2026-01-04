"""add engagement social location fields

Revision ID: add_engagement_social_location
Revises: 
Create Date: 2026-01-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_engagement_social_location'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add engagement metrics to articles
    op.add_column('articles', sa.Column('likes_count', sa.Integer(), server_default='0'))
    op.add_column('articles', sa.Column('shares_count', sa.Integer(), server_default='0'))
    op.add_column('articles', sa.Column('comments_count', sa.Integer(), server_default='0'))
    op.add_column('articles', sa.Column('views_count', sa.Integer(), server_default='0'))
    op.add_column('articles', sa.Column('reactions', postgresql.JSON(), nullable=True))
    op.add_column('articles', sa.Column('engagement_rate', sa.Float(), nullable=True))
    
    # Add social account info
    op.add_column('articles', sa.Column('social_platform', sa.String(50), nullable=True))
    op.add_column('articles', sa.Column('account_id', sa.String(256), nullable=True))
    op.add_column('articles', sa.Column('account_name', sa.String(512), nullable=True))
    op.add_column('articles', sa.Column('account_url', sa.String(1024), nullable=True))
    op.add_column('articles', sa.Column('account_type', sa.String(50), nullable=True))
    op.add_column('articles', sa.Column('account_followers', sa.Integer(), nullable=True))
    
    # Add post metadata
    op.add_column('articles', sa.Column('post_id', sa.String(256), nullable=True))
    op.add_column('articles', sa.Column('post_type', sa.String(50), nullable=True))
    op.add_column('articles', sa.Column('post_language', sa.String(10), nullable=True))
    
    # Add location data
    op.add_column('articles', sa.Column('province', sa.String(100), nullable=True))
    op.add_column('articles', sa.Column('district', sa.String(100), nullable=True))
    op.add_column('articles', sa.Column('ward', sa.String(100), nullable=True))
    op.add_column('articles', sa.Column('location_text', sa.String(512), nullable=True))
    op.add_column('articles', sa.Column('coordinates', postgresql.JSON(), nullable=True))
    
    # Create indexes for new columns
    op.create_index('ix_articles_social_platform', 'articles', ['social_platform'])
    op.create_index('ix_articles_post_id', 'articles', ['post_id'])
    op.create_index('ix_articles_province', 'articles', ['province'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_articles_province')
    op.drop_index('ix_articles_post_id')
    op.drop_index('ix_articles_social_platform')
    
    # Drop columns
    op.drop_column('articles', 'coordinates')
    op.drop_column('articles', 'location_text')
    op.drop_column('articles', 'ward')
    op.drop_column('articles', 'district')
    op.drop_column('articles', 'province')
    
    op.drop_column('articles', 'post_language')
    op.drop_column('articles', 'post_type')
    op.drop_column('articles', 'post_id')
    
    op.drop_column('articles', 'account_followers')
    op.drop_column('articles', 'account_type')
    op.drop_column('articles', 'account_url')
    op.drop_column('articles', 'account_name')
    op.drop_column('articles', 'account_id')
    op.drop_column('articles', 'social_platform')
    
    op.drop_column('articles', 'engagement_rate')
    op.drop_column('articles', 'reactions')
    op.drop_column('articles', 'views_count')
    op.drop_column('articles', 'comments_count')
    op.drop_column('articles', 'shares_count')
    op.drop_column('articles', 'likes_count')
