"""
Economic Indicators Models - Các chỉ số kinh tế
Thống kê các chỉ số kinh tế theo tháng/quý/năm
"""
from sqlalchemy import Column, Integer, String, Float, Date, JSON, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy import DateTime
from sqlalchemy.orm import relationship
from app.models.model_base import BareBaseModel


class EconomicIndicator(BareBaseModel):
    """
    Chỉ số kinh tế - Economic Indicators
    Lưu trữ các chỉ số kinh tế theo thời gian
    """
    __tablename__ = "economic_indicators"
    
    # Thông tin thời gian
    period_type = Column(String(20), nullable=False, index=True)  # monthly, quarterly, yearly
    period_start = Column(Date, nullable=False, index=True)  # Ngày bắt đầu kỳ
    period_end = Column(Date, nullable=False)  # Ngày kết thúc kỳ
    period_label = Column(String(50))  # "Tháng 12/2025", "Quý 4/2025", "Năm 2025"
    year = Column(Integer, index=True)  # Năm
    month = Column(Integer, nullable=True, index=True)  # Tháng (1-12)
    quarter = Column(Integer, nullable=True, index=True)  # Quý (1-4)
    
    # Địa phương (nếu có)
    province = Column(String(100), nullable=True, index=True)  # Tỉnh/thành phố
    region = Column(String(100), nullable=True)  # Miền (Bắc, Trung, Nam)
    
    # Dữ liệu chi tiết (JSON)
    detailed_data = Column(JSON, nullable=True)  # Lưu dữ liệu chi tiết khác
    
    # Nguồn dữ liệu
    data_source = Column(String(255), nullable=True)  # Nguồn: GSO, MPI, GPT, etc.
    source_url = Column(Text, nullable=True)  # URL nguồn dữ liệu
    
    # Liên kết với bài viết nguồn
    source_article_id = Column(Integer, ForeignKey('articles.id', ondelete='SET NULL'), nullable=True, index=True)  # ID bài viết nguồn
    source_article_url = Column(String(2048), nullable=True)  # URL bài viết nguồn (backup)
    source_article_domain = Column(String(256), nullable=True)  # Domain nguồn (baohungyen.vn, vnexpress.net, etc.)
    
    # Relationship
    source_article = relationship("Article", foreign_keys=[source_article_id])
    
    # Ghi chú
    notes = Column(Text, nullable=True)  # Ghi chú thêm
    
    # === PHÂN TÍCH CHO TỪNG NHÓM CHỈ SỐ ===
    grdp_analysis = Column(Text, nullable=True)  # Nhận xét về GRDP
    iip_analysis = Column(Text, nullable=True)  # Nhận xét về IIP
    agricultural_analysis = Column(Text, nullable=True)  # Nhận xét về nông nghiệp
    retail_services_analysis = Column(Text, nullable=True)  # Nhận xét về bán lẻ & dịch vụ
    export_import_analysis = Column(Text, nullable=True)  # Nhận xét về xuất nhập khẩu
    investment_analysis = Column(Text, nullable=True)  # Nhận xét về đầu tư (FDI, trong nước)
    budget_analysis = Column(Text, nullable=True)  # Nhận xét về ngân sách
    labor_analysis = Column(Text, nullable=True)  # Nhận xét về lao động
    
    # Tóm tắt tổng quan
    summary = Column(Text, nullable=True)  # Tóm tắt tổng quan về tình hình kinh tế kỳ này
    
    # Trạng thái
    is_verified = Column(Integer, default=0)  # Đã xác minh: 0=No, 1=Yes
    is_estimated = Column(Integer, default=0)  # Ước tính: 0=No, 1=Yes
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class EconomicIndicatorGPT(BareBaseModel):
    """
    Chỉ số kinh tế từ GPT - Dữ liệu được GPT tạo ra khi không có trong DB
    """
    __tablename__ = "economic_indicators_gpt"
    
    # Thông tin thời gian
    period_type = Column(String(20), nullable=False, index=True)
    period_label = Column(String(50))
    year = Column(Integer, index=True)
    month = Column(Integer, nullable=True)
    quarter = Column(Integer, nullable=True)
    
    # Địa phương
    province = Column(String(100), nullable=True, index=True)
    
    # Chỉ số được yêu cầu
    indicator_name = Column(String(100), nullable=False, index=True)  # grdp, iip, cpi, etc.
    indicator_value = Column(Float, nullable=True)
    indicator_unit = Column(String(50), nullable=True)  # %, tỷ VNĐ, triệu USD, etc.
    
    # Nội dung từ GPT
    gpt_response = Column(Text, nullable=True)  # Response đầy đủ từ GPT
    gpt_summary = Column(Text, nullable=True)  # Tóm tắt
    
    # Metadata
    prompt_used = Column(Text, nullable=True)  # Prompt đã dùng
    model_used = Column(String(50), nullable=True)  # Model GPT đã dùng
    confidence_score = Column(Float, nullable=True)  # Độ tin cậy (0-1)
    
    created_at = Column(DateTime, server_default=func.now())
