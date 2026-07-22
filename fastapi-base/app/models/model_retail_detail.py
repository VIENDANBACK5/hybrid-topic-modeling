"""Retail Sales and Services Detail Model"""
from sqlalchemy import Column, Numeric, UniqueConstraint, Index
from app.models.model_economic_base import EconomicIndicatorBase


class RetailServicesDetail(EconomicIndicatorBase):
    """
    Tổng mức bán lẻ hàng hóa và doanh thu dịch vụ tiêu dùng
    Total Retail Sales of Goods and Consumer Service Revenue
    """
    __tablename__ = "retail_services_detail"
    
    # Additional fields specific to retail
    retail_value = Column(Numeric, comment='Retail sales value only (billion VND)')
    services_value = Column(Numeric, comment='Services revenue only (billion VND)')
    
    __table_args__ = (
        UniqueConstraint('province', 'year', 'quarter', 'month', 'data_source', name='unique_retail_period'),
        Index('idx_retail_province_year', 'province', 'year'),
    )
