"""GRDP Detail Model - Timeseries Format"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, UniqueConstraint, Index
from sqlalchemy.sql import func
from app.models.model_base import Base


class GRDPDetail(Base):
    """GRDP Timeseries - Time + Actual + Forecast + Change"""
    __tablename__ = "grdp_detail"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Time
    province = Column(String, nullable=False)
    period_type = Column(String, nullable=False, default='year')
    year = Column(Integer, nullable=False)
    quarter = Column(Integer, nullable=True)
    
    # Values
    actual_value = Column(Numeric)
    forecast_value = Column(Numeric)
    
    # Changes
    change_yoy = Column(Numeric)
    change_qoq = Column(Numeric)
    change_prev_period = Column(Numeric)
    
    # Metadata
    data_status = Column(String, default='estimated')
    data_source = Column(String)
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('province', 'year', 'quarter', name='unique_period'),
        Index('idx_grdp_province_year', 'province', 'year'),
    )
    
    @property
    def period_label(self) -> str:
        if self.quarter:
            return f"Q{self.quarter}/{self.year}"
        return str(self.year)
