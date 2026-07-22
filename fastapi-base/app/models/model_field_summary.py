from sqlalchemy import Column, Integer, String, Text, Float, JSON, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.models.model_base import BareBaseModel


class FieldSummary(BareBaseModel):
    """Model lưu tóm tắt thông tin theo lĩnh vực"""
    __tablename__ = "field_summaries"

    # Quan hệ
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False, index=True)
    field_name = Column(String(256), nullable=False)  # Denormalized
    
    # Thời gian
    summary_period = Column(String(20), nullable=False, index=True)  # daily, weekly, monthly
    period_start = Column(Float, nullable=False)  # timestamp
    period_end = Column(Float, nullable=False)  # timestamp
    summary_date = Column(Date, nullable=False, index=True)  # Ngày tạo summary
    
    # Thống kê
    total_articles = Column(Integer, default=0)
    avg_engagement = Column(Float, default=0)
    top_sources = Column(JSON)  # {"vnexpress": 10, "tuoitre": 5, ...}
    
    # Tóm tắt nội dung
    key_topics = Column(JSON)  # ["Chủ đề 1", "Chủ đề 2", ...]
    summary_text = Column(Text)  # Tóm tắt chi tiết bằng LLM
    sentiment_overview = Column(JSON)  # {"positive": 10, "negative": 5, "neutral": 20}
    
    # Bài viết nổi bật
    top_articles = Column(JSON)  # [{"id": 1, "title": "...", "engagement": 100}, ...]
    trending_keywords = Column(JSON)  # ["từ khóa 1", "từ khóa 2", ...]
    
    # Metadata
    generation_method = Column(String(50), default="llm")  # llm, template
    model_used = Column(String(100))  # gpt-3.5-turbo, gpt-4, etc.
    
    # Quan hệ
    field = relationship("Field")
