"""State Budget Revenue Detail Model"""
from sqlalchemy import Column, Numeric, UniqueConstraint, Index
from app.models.model_economic_base import EconomicIndicatorBase


class BudgetRevenueDetail(EconomicIndicatorBase):
    """
    Thu ngân sách nhà nước (State Budget Revenue - SBR)
    Total state budget revenue from all sources
    """
    __tablename__ = "budget_revenue_detail"
    
    # Revenue breakdown
    tax_revenue = Column(Numeric, comment='Tax revenue (billion VND)')
    non_tax_revenue = Column(Numeric, comment='Non-tax revenue (billion VND)')
    land_revenue = Column(Numeric, comment='Land and property revenue (billion VND)')
    
    # Budget execution rate
    budget_target = Column(Numeric, comment='Annual budget target (billion VND)')
    execution_rate = Column(Numeric, comment='Budget execution rate (%)')
    
    __table_args__ = (
        UniqueConstraint('province', 'year', 'quarter', 'month', 'data_source', name='unique_budget_period'),
        Index('idx_budget_province_year', 'province', 'year', 'quarter', 'month'),
    )
