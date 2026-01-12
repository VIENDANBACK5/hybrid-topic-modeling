"""
GRDP Detail Model - Chi tiết chỉ số GRDP theo tỉnh/thành
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.model_base import BareBaseModel


class GRDPDetail(BareBaseModel):
    """
    Bảng chi tiết GRDP theo tỉnh/thành
    Lưu trữ thông tin chi tiết về GRDP, tăng trưởng, cơ cấu ngành, xếp hạng
    """
    __tablename__ = "grdp_detail"
    
    # Foreign key (optional - có thể link với bảng economic_indicators)
    economic_indicator_id = Column(
        Integer, 
        ForeignKey('economic_indicators.id', ondelete='SET NULL'), 
        nullable=True, 
        index=True,
        comment='Liên kết với bảng economic_indicators'
    )
    
    # === 1. NHÓM ĐỊNH DANH & THỜI GIAN ===
    province = Column(
        String(100), 
        nullable=False, 
        index=True,
        comment='Tên tỉnh/thành phố (VD: Hưng Yên)'
    )
    
    year = Column(
        Integer, 
        nullable=False, 
        index=True,
        comment='Năm thống kê (VD: 2025)'
    )
    
    quarter = Column(
        Integer, 
        nullable=True, 
        index=True,
        comment='Quý (1-4), NULL = dữ liệu cả năm'
    )
    
    # === 2. NHÓM GIÁ TRỊ KINH TẾ ===
    grdp_current_price = Column(
        Float, 
        nullable=True,
        comment='Tổng sản phẩm trên địa bàn theo giá hiện hành (tỷ VNĐ)'
    )
    
    grdp_per_capita = Column(
        Float, 
        nullable=True,
        comment='GRDP bình quân đầu người (triệu VNĐ/người)'
    )
    
    # === 3. NHÓM TĂNG TRƯỞNG ===
    growth_rate = Column(
        Float, 
        nullable=True,
        comment='Tốc độ tăng trưởng GRDP so với cùng kỳ năm trước (%)'
    )
    
    # === 4. NHÓM CƠ CẤU NGÀNH KINH TẾ ===
    agriculture_sector_pct = Column(
        Float, 
        nullable=True,
        comment='Tỷ trọng ngành Nông - Lâm - Thủy sản (%)'
    )
    
    industry_sector_pct = Column(
        Float, 
        nullable=True,
        comment='Tỷ trọng ngành Công nghiệp - Xây dựng (%)'
    )
    
    service_sector_pct = Column(
        Float, 
        nullable=True,
        comment='Tỷ trọng ngành Dịch vụ (%)'
    )
    
    # === 5. NHÓM SO SÁNH & XẾP HẠNG ===
    rank_national = Column(
        Integer, 
        nullable=True,
        comment='Xếp hạng GRDP so với các tỉnh/thành cả nước'
    )
    
    # === 6. NHÓM DỰ BÁO ===
    forecast_year_end = Column(
        Float, 
        nullable=True,
        comment='Dự báo GRDP cả năm (tỷ VNĐ) - chỉ áp dụng cho dữ liệu quý'
    )
    
    # === 7. NHÓM TRẠNG THÁI & NGUỒN DỮ LIỆU ===
    data_status = Column(
        String(20), 
        nullable=False, 
        server_default='official',
        index=True,
        comment='Trạng thái dữ liệu: official (chính thức) / estimated (ước tính) / forecast (dự báo)'
    )
    
    data_source = Column(
        String(255), 
        nullable=True,
        comment='Nguồn dữ liệu (VD: Cục Thống kê Hưng Yên, GSO)'
    )
    
    last_updated = Column(
        DateTime, 
        server_default=func.now(),
        comment='Thời điểm cập nhật dữ liệu gần nhất'
    )
    
    # Timestamp fields
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationship
    economic_indicator = relationship(
        "EconomicIndicator", 
        foreign_keys=[economic_indicator_id],
        backref="grdp_details"
    )
    
    def __repr__(self):
        quarter_str = f"Q{self.quarter}" if self.quarter else "Cả năm"
        return f"<GRDPDetail {self.province} - {quarter_str}/{self.year}: {self.grdp_current_price}T VNĐ>"
    
    @property
    def period_label(self):
        """Tạo nhãn thời gian đẹp"""
        if self.quarter:
            return f"Quý {self.quarter}/{self.year}"
        return f"Năm {self.year}"
    
    @property
    def is_complete_sector_structure(self):
        """Kiểm tra cơ cấu 3 ngành có đầy đủ không"""
        if all([
            self.agriculture_sector_pct is not None,
            self.industry_sector_pct is not None,
            self.service_sector_pct is not None
        ]):
            total = self.agriculture_sector_pct + self.industry_sector_pct + self.service_sector_pct
            return abs(total - 100.0) < 0.1  # Cho phép sai số 0.1%
        return False
