"""Base Economic Indicator Model - Reusable for all indicators"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, UniqueConstraint, Index
from sqlalchemy.sql import func
from app.models.model_base import Base


class EconomicIndicatorBase(Base):
    """Base class for all economic indicators - DO NOT USE DIRECTLY"""
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Time dimensions
    province = Column(String, nullable=False, default='Hưng Yên')
    period_type = Column(String, nullable=False, default='quarter')  # 'year', 'quarter', 'month'
    year = Column(Integer, nullable=False)
    quarter = Column(Integer, nullable=True)
    month = Column(Integer, nullable=True)
    
    # Core values
    actual_value = Column(Numeric, comment='Actual value')
    forecast_value = Column(Numeric, comment='Forecast value')
    
    # Growth rates
    change_yoy = Column(Numeric, comment='Year-over-year change %')
    change_qoq = Column(Numeric, comment='Quarter-over-quarter change %')
    change_mom = Column(Numeric, comment='Month-over-month change %')
    change_prev_period = Column(Numeric, comment='Previous period change %')
    
    # Metadata
    data_status = Column(String, default='estimated', comment='official, estimated, preliminary')
    data_source = Column(String, comment='Source URL or reference')
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    
    @property
    def period_label(self) -> str:
        """Generate human-readable period label"""
        if self.month:
            return f"{self.month:02d}/{self.year}"
        elif self.quarter:
            return f"Q{self.quarter}/{self.year}"
        return str(self.year)
