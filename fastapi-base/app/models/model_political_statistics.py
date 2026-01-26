from sqlalchemy import Column, String, Integer, Text, Index
from app.models.model_base import BareBaseModel


class PoliticalStatistics(BareBaseModel):
    """
    Model for political and administrative statistics data extracted from important posts
    """
    __tablename__ = "political_statistics"

    # Location information
    dvhc = Column(String(255), nullable=False, comment="Đơn vị hành chính (xã/phường)")
    
    # Reference to source post
    source_post_id = Column(Integer, nullable=True, comment="ID của bài viết nguồn")
    source_url = Column(String(500), nullable=True, comment="URL của bài viết nguồn")
    
    # Time period
    period = Column(String(100), nullable=True, comment="Thời kỳ (năm, quý, tháng)")
    year = Column(Integer, nullable=True, comment="Năm")
    
    # Political indicators - Party organization
    party_organization_count = Column(Integer, nullable=True, comment="Số tổ chức Đảng")
    party_member_count = Column(Integer, nullable=True, comment="Số lượng Đảng viên")
    party_size_description = Column(Text, nullable=True, comment="Mô tả quy mô Đảng bộ")
    
    # Additional party statistics
    new_party_members = Column(Integer, nullable=True, comment="Số Đảng viên mới kết nạp")
    party_cells_count = Column(Integer, nullable=True, comment="Số chi bộ")
    
    # Additional context
    notes = Column(Text, nullable=True, comment="Ghi chú bổ sung")
    extraction_metadata = Column(Text, nullable=True, comment="Metadata từ quá trình trích xuất")
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_political_dvhc', 'dvhc'),
        Index('idx_political_year', 'year'),
        Index('idx_political_source', 'source_post_id'),
    )

    def __repr__(self):
        return f"<PoliticalStatistics(dvhc={self.dvhc}, year={self.year}, party_members={self.party_member_count})>"
