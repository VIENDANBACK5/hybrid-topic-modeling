"""
Model lưu sentiment analysis chi tiết theo lĩnh vực
"""
from sqlalchemy import Column, Integer, String, Float, JSON, ForeignKey, Date, Text
from sqlalchemy.orm import relationship
from app.models.model_base import BareBaseModel


class FieldSentiment(BareBaseModel):
    """Model lưu phân tích sentiment theo lĩnh vực và thời gian"""
    __tablename__ = "field_sentiments"

    # Quan hệ
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False, index=True)
    field_name = Column(String(256), nullable=False)  # Denormalized for quick access
    
    # Thời gian
    period_type = Column(String(20), nullable=False, index=True)  # daily, weekly, monthly
    period_date = Column(Date, nullable=False, index=True)  # Ngày đại diện cho period
    period_start = Column(Float, nullable=False)  # timestamp
    period_end = Column(Float, nullable=False)  # timestamp
    
    # Tổng quan
    total_articles = Column(Integer, default=0)
    analyzed_articles = Column(Integer, default=0)  # Số bài đã phân tích sentiment
    
    # Sentiment scores (0-1)
    sentiment_positive = Column(Float, default=0.0)  # % positive
    sentiment_negative = Column(Float, default=0.0)  # % negative
    sentiment_neutral = Column(Float, default=0.0)   # % neutral
    
    # Counts
    positive_count = Column(Integer, default=0)
    negative_count = Column(Integer, default=0)
    neutral_count = Column(Integer, default=0)
    
    # Sentiment score trung bình (-1 to 1)
    avg_sentiment_score = Column(Float, default=0.0)
    
    # Chi tiết sentiment
    sentiment_distribution = Column(JSON)  # {"very_positive": 5, "positive": 10, ...}
    top_positive_articles = Column(JSON)  # [{"id": 1, "title": "...", "score": 0.9}, ...]
    top_negative_articles = Column(JSON)  # [{"id": 2, "title": "...", "score": -0.8}, ...]
    
    # Emotions (optional - nếu có phân tích chi tiết)
    emotions = Column(JSON)  # {"joy": 20, "anger": 5, "sadness": 3, ...}
    
    # Keywords theo sentiment
    positive_keywords = Column(JSON)  # ["phát triển", "thành công", ...]
    negative_keywords = Column(JSON)  # ["sự cố", "khó khăn", ...]
    
    # Trend
    sentiment_trend = Column(String(20))  # improving, declining, stable
    trend_description = Column(Text)  # Mô tả xu hướng
    
    # Metadata
    analysis_method = Column(String(50), default="llm")  # llm, rule_based, hybrid
    model_used = Column(String(100))  # Model name nếu dùng LLM
    
    # Quan hệ
    field = relationship("Field")
