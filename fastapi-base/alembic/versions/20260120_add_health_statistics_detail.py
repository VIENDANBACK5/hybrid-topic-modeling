"""Add health_statistics_detail table - Thống kê Y tế & Dân số

Revision ID: 20260120_health_stats
Revises: 20260120_culture_lifestyle
Create Date: 2026-01-20 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260120_health_stats'
down_revision = '20260120_culture_lifestyle'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'health_statistics_detail',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('economic_indicator_id', sa.Integer(), nullable=True),
        sa.Column('province', sa.String(length=100), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('quarter', sa.Integer(), nullable=True),
        sa.Column('month', sa.Integer(), nullable=True),
        
        # 6 data fields
        sa.Column('bhyt_coverage_rate', sa.Float(), nullable=True, comment='Tỷ lệ bao phủ BHYT (%)'),
        sa.Column('total_insured', sa.Integer(), nullable=True, comment='Số người tham gia BHYT'),
        sa.Column('voluntary_insured', sa.Integer(), nullable=True, comment='Số người tham gia BHYT tự nguyện'),
        sa.Column('natural_population_growth_rate', sa.Float(), nullable=True, comment='Tốc độ tăng dân số tự nhiên (%)'),
        sa.Column('elderly_health_checkup_rate', sa.Float(), nullable=True, comment='Tỷ lệ người cao tuổi khám sức khỏe định kỳ (%)'),
        sa.Column('sex_ratio_at_birth', sa.Float(), nullable=True, comment='Tỷ số giới tính khi sinh (nam/100 nữ)'),
        
        # Metadata fields
        sa.Column('rank_national', sa.Integer(), nullable=True),
        sa.Column('rank_regional', sa.Integer(), nullable=True),
        sa.Column('yoy_change', sa.Float(), nullable=True),
        sa.Column('data_status', sa.String(length=20), nullable=False, server_default='official'),
        sa.Column('data_source', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['economic_indicator_id'], ['economic_indicators.id'], ondelete='SET NULL')
    )
    
    # Create indexes
    op.create_index('ix_health_statistics_detail_province', 'health_statistics_detail', ['province'])
    op.create_index('ix_health_statistics_detail_year', 'health_statistics_detail', ['year'])
    op.create_index('ix_health_statistics_detail_quarter', 'health_statistics_detail', ['quarter'])
    op.create_index('ix_health_statistics_detail_economic_indicator_id', 'health_statistics_detail', ['economic_indicator_id'])


def downgrade():
    op.drop_index('ix_health_statistics_detail_economic_indicator_id', 'health_statistics_detail')
    op.drop_index('ix_health_statistics_detail_quarter', 'health_statistics_detail')
    op.drop_index('ix_health_statistics_detail_year', 'health_statistics_detail')
    op.drop_index('ix_health_statistics_detail_province', 'health_statistics_detail')
    op.drop_table('health_statistics_detail')
