"""Investment Attraction Detail Model"""
from sqlalchemy import Column, Numeric, UniqueConstraint, Index
from app.models.model_economic_base import EconomicIndicatorBase


class InvestmentDetail(EconomicIndicatorBase):
    """
    Thu hút đầu tư (Investment Attraction)
    Total investment including FDI, DDI, and public investment
    """
    __tablename__ = "investment_detail"
    
    # Breakdown by investment type
    fdi_registered = Column(Numeric, comment='FDI registered capital (million USD)')
    fdi_disbursed = Column(Numeric, comment='FDI disbursed capital (million USD)')
    ddi_value = Column(Numeric, comment='Domestic investment (billion VND)')
    public_investment = Column(Numeric, comment='Public investment (billion VND)')
    
    # Project counts
    fdi_projects_new = Column(Numeric, comment='Number of new FDI projects')
    fdi_projects_expanded = Column(Numeric, comment='Number of expanded FDI projects')
    
    __table_args__ = (
        UniqueConstraint('province', 'year', 'quarter', 'month', name='unique_investment_period'),
        Index('idx_investment_province_year', 'province', 'year'),
    )
