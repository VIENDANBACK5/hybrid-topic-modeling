"""Consumer Price Index (CPI) Detail Model"""
from sqlalchemy import Column, Numeric, String, UniqueConstraint, Index
from app.models.model_economic_base import EconomicIndicatorBase


class CPIDetail(EconomicIndicatorBase):
    """
    Chỉ số giá tiêu dùng (Consumer Price Index - CPI)
    Measures inflation and price changes
    """
    __tablename__ = "cpi_detail"
    
    # CPI breakdown by category
    cpi_food = Column(Numeric, comment='Food and foodstuff CPI')
    cpi_housing = Column(Numeric, comment='Housing and construction materials CPI')
    cpi_transport = Column(Numeric, comment='Transport CPI')
    cpi_education = Column(Numeric, comment='Education CPI')
    cpi_healthcare = Column(Numeric, comment='Healthcare CPI')
    
    # Core CPI (excluding volatile items)
    core_cpi = Column(Numeric, comment='Core CPI (excludes food, energy)')
    
    # Additional metrics
    inflation_rate = Column(Numeric, comment='Inflation rate (%)')
    basket_weights = Column(String, comment='Category weights (JSON)')
    
    __table_args__ = (
        UniqueConstraint('province', 'year', 'quarter', 'month', 'data_source', name='unique_cpi_period'),
        Index('idx_cpi_province_year', 'province', 'year'),
    )
