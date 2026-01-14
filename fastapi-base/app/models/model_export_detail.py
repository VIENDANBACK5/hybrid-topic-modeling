"""Export Value Detail Model"""
from sqlalchemy import Column, String, Numeric, UniqueConstraint, Index
from app.models.model_economic_base import EconomicIndicatorBase


class ExportDetail(EconomicIndicatorBase):
    """
    Kim ngạch xuất khẩu (Export Value)
    Measures total export value in USD or VND
    """
    __tablename__ = "export_detail"
    
    # Additional fields for export
    export_usd = Column(Numeric, comment='Export value in million USD')
    export_vnd = Column(Numeric, comment='Export value in billion VND')
    top_products = Column(String, comment='Top export products (JSON array)')
    top_markets = Column(String, comment='Top export markets (JSON array)')
    
    __table_args__ = (
        UniqueConstraint('province', 'year', 'quarter', 'month', name='unique_export_period'),
        Index('idx_export_province_year', 'province', 'year', 'quarter', 'month'),
    )
