"""Add HITL review tables

Revision ID: hitl_tables_001
Revises: 598f7648e8ea
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'hitl_tables_001'
down_revision = '598f7648e8ea'
branch_labels = None
depends_on = None


def upgrade():
    # Create topic_reviews table
    op.create_table('topic_reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('topic_id', sa.Integer(), nullable=False),
        sa.Column('original_label', sa.String(500), nullable=True),
        sa.Column('suggested_label', sa.String(500), nullable=True),
        sa.Column('final_label', sa.String(500), nullable=True),
        sa.Column('keywords', sa.Text(), nullable=True),  # JSON string
        sa.Column('sample_docs', sa.Text(), nullable=True),  # JSON string
        sa.Column('status', sa.String(50), nullable=False, default='pending'),
        sa.Column('reviewer_notes', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_topic_reviews_topic_id', 'topic_reviews', ['topic_id'])
    op.create_index('ix_topic_reviews_status', 'topic_reviews', ['status'])

    # Create entity_reviews table
    op.create_table('entity_reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entity_text', sa.String(500), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('canonical_form', sa.String(500), nullable=True),
        sa.Column('source_doc_id', sa.String(100), nullable=True),
        sa.Column('context_snippet', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='pending'),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('reviewed_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_entity_reviews_entity_type', 'entity_reviews', ['entity_type'])
    op.create_index('ix_entity_reviews_status', 'entity_reviews', ['status'])

    # Create pipeline_runs table for tracking
    op.create_table('pipeline_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.String(100), nullable=False, unique=True),
        sa.Column('source_url', sa.String(1000), nullable=True),
        sa.Column('mode', sa.String(50), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='pending'),
        sa.Column('progress', sa.Integer(), default=0),
        sa.Column('documents_crawled', sa.Integer(), default=0),
        sa.Column('topics_trained', sa.Integer(), default=0),
        sa.Column('entities_extracted', sa.Integer(), default=0),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_pipeline_runs_task_id', 'pipeline_runs', ['task_id'])
    op.create_index('ix_pipeline_runs_status', 'pipeline_runs', ['status'])


def downgrade():
    op.drop_table('pipeline_runs')
    op.drop_table('entity_reviews')
    op.drop_table('topic_reviews')
