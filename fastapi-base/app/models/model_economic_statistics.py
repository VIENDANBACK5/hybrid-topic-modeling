from sqlalchemy import Column, String, Float, Text, Integer, Index
from app.models.model_base import BareBaseModel


class EconomicStatistics(BareBaseModel):
    """
    Model for economic statistics data extracted from important posts
    """
    __tablename__ = "economic_statistics"

    # Location information
    dvhc = Column(String(255), nullable=False, comment="Đơn vị hành chính (xã/phường)")
    
    # Reference to source post
    source_post_id = Column(Integer, nullable=True, comment="ID của bài viết nguồn")
    source_url = Column(String(500), nullable=True, comment="URL của bài viết nguồn")
    
    # Time period
    period = Column(String(100), nullable=True, comment="Thời kỳ (năm, quý, tháng)")
    year = Column(Integer, nullable=True, comment="Năm")
    
    # Economic indicators
    total_production_value = Column(Float, nullable=True, comment="Tổng giá trị sản xuất (tỷ đồng)")
    growth_rate = Column(Float, nullable=True, comment="Tốc độ tăng trưởng (%)")
    total_budget_revenue = Column(Float, nullable=True, comment="Tổng thu ngân sách nhà nước (tỷ đồng)")
    budget_collection_efficiency = Column(Float, nullable=True, comment="Hiệu suất thu ngân sách (%)")
    
    # Additional context
    notes = Column(Text, nullable=True, comment="Ghi chú bổ sung")
    extraction_metadata = Column(Text, nullable=True, comment="Metadata từ quá trình trích xuất")
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_economic_dvhc', 'dvhc'),
        Index('idx_economic_year', 'year'),
        Index('idx_economic_source', 'source_post_id'),
    )

    def __repr__(self):
        return f"<EconomicStatistics(dvhc={self.dvhc}, year={self.year}, production={self.total_production_value})>"
