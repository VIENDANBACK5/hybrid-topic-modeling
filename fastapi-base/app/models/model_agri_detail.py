"""Agricultural Production Index Detail Model"""
from sqlalchemy import UniqueConstraint, Index
from app.models.model_economic_base import EconomicIndicatorBase


class AgriProductionDetail(EconomicIndicatorBase):
    """
    Chỉ số sản xuất nông nghiệp (Agricultural Production Index)
    Measures agricultural output and productivity
    """
    __tablename__ = "agri_production_detail"
    
    __table_args__ = (
        UniqueConstraint('province', 'year', 'quarter', 'month', 'data_source', name='unique_agri_period'),
        Index('idx_agri_province_year', 'province', 'year'),
    )
