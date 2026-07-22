"""add_bertopic_discovered_topics

Revision ID: add_bertopic_discovered
Revises: add_custom_topics
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_bertopic_discovered'
down_revision = 'add_custom_topics'
branch_labels = None
depends_on = None


def upgrade():
    # Create topic_training_sessions table
    op.create_table(
        'topic_training_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('model_type', sa.String(length=50), nullable=False),
        sa.Column('model_version', sa.String(length=50), nullable=True),
        sa.Column('min_topic_size', sa.Integer(), nullable=True),
        sa.Column('embedding_model', sa.String(length=255), nullable=True),
        sa.Column('use_vietnamese_tokenizer', sa.Boolean(), default=False),
        sa.Column('use_topicgpt', sa.Boolean(), default=False),
        sa.Column('num_documents', sa.Integer(), nullable=False, default=0),
        sa.Column('num_topics_found', sa.Integer(), nullable=True),
        sa.Column('num_outliers', sa.Integer(), nullable=True),
        sa.Column('training_duration_seconds', sa.Float(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('model_saved_path', sa.String(length=500), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('avg_coherence_score', sa.Float(), nullable=True),
        sa.Column('avg_diversity_score', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id')
    )
    op.create_index('idx_training_sessions_session_id', 'topic_training_sessions', ['session_id'])
    op.create_index('idx_training_sessions_status', 'topic_training_sessions', ['status'])
    op.create_index('idx_training_sessions_started_at', 'topic_training_sessions', ['started_at'])

    # Create bertopic_discovered_topics table
    op.create_table(
        'bertopic_discovered_topics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('training_session_id', sa.String(length=36), nullable=False),
        sa.Column('model_version', sa.String(length=50), nullable=True),
        sa.Column('topic_id', sa.Integer(), nullable=False),
        sa.Column('topic_label', sa.String(length=500), nullable=True),
        sa.Column('keywords', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('representative_docs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('document_count', sa.Integer(), default=0),
        sa.Column('coherence_score', sa.Float(), nullable=True),
        sa.Column('diversity_score', sa.Float(), nullable=True),
        sa.Column('natural_description', sa.Text(), nullable=True),
        sa.Column('is_outlier', sa.Boolean(), default=False),
        sa.Column('is_reviewed', sa.Boolean(), default=False),
        sa.Column('reviewed_by', sa.String(length=100), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('is_converted', sa.Boolean(), default=False),
        sa.Column('converted_custom_topic_id', sa.Integer(), nullable=True),
        sa.Column('converted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['training_session_id'], ['topic_training_sessions.session_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['converted_custom_topic_id'], ['custom_topics.id'], ondelete='SET NULL')
    )
    op.create_index('idx_bertopic_topics_session_id', 'bertopic_discovered_topics', ['training_session_id'])
    op.create_index('idx_bertopic_topics_topic_id', 'bertopic_discovered_topics', ['topic_id'])
    op.create_index('idx_bertopic_topics_is_outlier', 'bertopic_discovered_topics', ['is_outlier'])
    op.create_index('idx_bertopic_topics_is_reviewed', 'bertopic_discovered_topics', ['is_reviewed'])
    op.create_index('idx_bertopic_topics_is_converted', 'bertopic_discovered_topics', ['is_converted'])

    # Create article_bertopic_topics table
    op.create_table(
        'article_bertopic_topics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('bertopic_topic_id', sa.Integer(), nullable=False),
        sa.Column('probability', sa.Float(), nullable=False),
        sa.Column('training_session_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['bertopic_topic_id'], ['bertopic_discovered_topics.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['training_session_id'], ['topic_training_sessions.session_id'], ondelete='CASCADE')
    )
    op.create_index('idx_article_bertopic_article_id', 'article_bertopic_topics', ['article_id'])
    op.create_index('idx_article_bertopic_topic_id', 'article_bertopic_topics', ['bertopic_topic_id'])
    op.create_index('idx_article_bertopic_session_id', 'article_bertopic_topics', ['training_session_id'])
    op.create_index('idx_article_bertopic_probability', 'article_bertopic_topics', ['probability'])
    
    # Composite unique constraint to prevent duplicates
    op.create_unique_constraint(
        'uq_article_bertopic_session',
        'article_bertopic_topics',
        ['article_id', 'training_session_id']
    )


def downgrade():
    # Drop tables in reverse order (due to foreign keys)
    op.drop_table('article_bertopic_topics')
    op.drop_table('bertopic_discovered_topics')
    op.drop_table('topic_training_sessions')
