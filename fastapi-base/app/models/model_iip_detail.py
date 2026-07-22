"""Industrial Production Index (IIP) Detail Model"""
from sqlalchemy import UniqueConstraint, Index
from app.models.model_economic_base import EconomicIndicatorBase


class IIPDetail(EconomicIndicatorBase):
    """
    Chỉ số sản xuất công nghiệp (Industrial Production Index)
    Measures manufacturing and industrial output growth
    """
    __tablename__ = "iip_detail"
    
    __table_args__ = (
        UniqueConstraint('province', 'year', 'quarter', 'month', 'data_source', name='unique_iip_period'),
        Index('idx_iip_province_year', 'province', 'year', 'quarter', 'month'),
    )
