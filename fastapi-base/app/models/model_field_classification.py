from sqlalchemy import Column, Integer, String, Text, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.models.model_base import BareBaseModel


class Field(BareBaseModel):
    """Model lưu các lĩnh vực phân loại"""
    __tablename__ = "fields"

    # Thông tin lĩnh vực
    name = Column(String(256), unique=True, nullable=False, index=True)  # Tên lĩnh vực
    description = Column(Text)  # Mô tả chi tiết
    keywords = Column(JSON)  # Danh sách từ khóa để phân loại
    order_index = Column(Integer, default=0)  # Thứ tự hiển thị
    
    # Quan hệ
    article_classifications = relationship("ArticleFieldClassification", back_populates="field")


class ArticleFieldClassification(BareBaseModel):
    """Model lưu phân loại bài viết theo lĩnh vực"""
    __tablename__ = "article_field_classifications"

    # Quan hệ với bài viết và lĩnh vực
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False, index=True)
    
    # Thông tin phân loại
    confidence_score = Column(Float, default=1.0)  # Độ tin cậy của phân loại (0-1)
    matched_keywords = Column(JSON)  # Các từ khóa matched trong bài viết
    classification_method = Column(String(50), default="keyword")  # keyword, ml, manual
    
    # Quan hệ
    field = relationship("Field", back_populates="article_classifications")


class FieldStatistics(BareBaseModel):
    """Model lưu thống kê số lượng bài viết theo lĩnh vực"""
    __tablename__ = "field_statistics"

    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False, index=True)
    field_name = Column(String(256), nullable=False)  # Denormalized để query nhanh
    
    # Thống kê số lượng
    total_articles = Column(Integer, default=0)
    articles_today = Column(Integer, default=0)
    articles_this_week = Column(Integer, default=0)
    articles_this_month = Column(Integer, default=0)
    
    # Thống kê engagement
    avg_likes = Column(Float, default=0)
    avg_shares = Column(Float, default=0)
    avg_comments = Column(Float, default=0)
    total_engagement = Column(Integer, default=0)
    
    # Thống kê theo nguồn
    source_distribution = Column(JSON)  # {"vnexpress": 100, "tuoitre": 50, ...}
    platform_distribution = Column(JSON)  # {"facebook": 150, "tiktok": 80, "threads": 30, ...}
    province_distribution = Column(JSON)  # {"Hà Nội": 80, "TP HCM": 60, ...}
    
    # Timestamp để biết lần update cuối
    stats_date = Column(Float)  # timestamp của ngày thống kê
    
    # Quan hệ
    field = relationship("Field")
