"""Simplify grdp_detail to timeseries format

Revision ID: simplify_grdp_001
Revises: 
Create Date: 2026-01-13
"""
from alembic import op
import sqlalchemy as sa

revision = 'simplify_grdp_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Drop old table
    op.execute("DROP TABLE IF EXISTS grdp_detail CASCADE")
    
    # Create new simplified table
    op.execute("""
        CREATE TABLE grdp_detail (
            id SERIAL PRIMARY KEY,
            province TEXT NOT NULL,
            period_type TEXT NOT NULL DEFAULT 'year',
            year INT NOT NULL,
            quarter INT,
            
            actual_value NUMERIC,
            forecast_value NUMERIC,
            
            change_yoy NUMERIC,
            change_qoq NUMERIC,
            change_prev_period NUMERIC,
            
            data_status TEXT DEFAULT 'estimated',
            data_source TEXT,
            last_updated TIMESTAMP DEFAULT NOW(),
            
            CONSTRAINT valid_period_type CHECK (period_type IN ('year', 'quarter')),
            CONSTRAINT valid_quarter CHECK (quarter IS NULL OR quarter BETWEEN 1 AND 4),
            CONSTRAINT valid_data_status CHECK (data_status IN ('official', 'estimated', 'forecast')),
            CONSTRAINT unique_period UNIQUE (province, year, quarter)
        )
    """)
    
    # Create index
    op.execute("CREATE INDEX idx_grdp_province_year ON grdp_detail(province, year)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS grdp_detail CASCADE")
