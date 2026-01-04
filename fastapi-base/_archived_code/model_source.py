from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, Text
from datetime import datetime
from app.models.model_base import BareBaseModel


class Source(BareBaseModel):
    """
    Model lưu các nguồn thu thập dữ liệu
    
    Phân loại:
    - news: Báo điện tử, cổng thông tin, websites ban ngành
    - social: Mạng xã hội (Facebook, Twitter, Instagram...)
    - forum: Diễn đàn, Fanpage, Group địa phương
    """
    
    __tablename__ = "sources"
    
    # Basic info
    name = Column(String(500), nullable=False)  # Tên nguồn
    url = Column(String(2048), unique=True, nullable=False, index=True)  # URL gốc
    type = Column(String(50), nullable=False, index=True)  # "news", "social", "forum"
    
    # Classification
    category = Column(String(100))  # Phân loại chi tiết: "bao_dien_tu", "facebook_page", "forum_local"...
    description = Column(Text)  # Mô tả nguồn
    
    # Metadata
    domain = Column(String(255), index=True)
    language = Column(String(10), default="vi")  # vi, en
    country = Column(String(10), default="VN")
    region = Column(String(100))  # Khu vực địa phương (nếu có)
    
    # Crawl config
    is_active = Column(Boolean, default=True)  # Đang active hay không
    crawl_frequency = Column(String(50))  # "daily", "weekly", "hourly"
    last_crawled_at = Column(DateTime)
    next_crawl_at = Column(DateTime)
    
    # Stats
    total_articles = Column(Integer, default=0)  # Tổng số bài đã crawl
    last_article_count = Column(Integer, default=0)  # Số bài crawl lần trước
    success_rate = Column(Integer, default=100)  # % thành công
    
    # Additional data
    contact_info = Column(JSON)  # Email, phone, address...
    tags = Column(JSON)  # Tags để search/filter
    crawl_params = Column(JSON)  # Custom params cho crawler
    extra_data = Column(JSON)  # Metadata khác
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Source {self.name} ({self.type})>"
