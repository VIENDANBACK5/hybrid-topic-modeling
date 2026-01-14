"""
Sentiment Analysis Model
Bảng lưu kết quả phân tích cảm xúc - dùng cho Superset dashboard
Hỗ trợ 15 sắc thái cảm xúc chi tiết
"""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.models.model_base import BareBaseModel


class SentimentAnalysis(BareBaseModel):
    """
    Bảng kết quả phân tích cảm xúc đa sắc thái
    Superset sẽ connect trực tiếp vào bảng này để vẽ dashboard
    
    15 sắc thái cảm xúc:
    - Tích cực: vui_mừng, ủng_hộ, tin_tưởng, hài_lòng, tự_hào, hy_vọng
    - Tiêu cực: phẫn_nộ, lo_ngại, thất_vọng, chỉ_trích, buồn_bã, sợ_hãi
    - Trung tính: trung_lập, hoài_nghi, ngạc_nhiên
    """
    __tablename__ = "sentiment_analysis"

    # Link tới article
    article_id = Column(Integer, ForeignKey('articles.id'), nullable=False, index=True)
    
    # Thông tin nguồn (duplicate để query nhanh, không cần join)
    source_url = Column(String(2048))
    source_domain = Column(String(256), index=True)
    title = Column(String(1024))
    
    # === SẮC THÁI CẢM XÚC CHI TIẾT ===
    # Emotion cụ thể: vui_mừng, phẫn_nộ, lo_ngại, etc.
    emotion = Column(String(30), nullable=False, index=True)
    emotion_vi = Column(String(30))  # Vui mừng, Phẫn nộ, Lo ngại, etc.
    emotion_icon = Column(String(10))  # , , , etc.
    
    # Group tổng quát: positive, negative, neutral
    sentiment_group = Column(String(20), nullable=False, index=True)
    sentiment_group_vi = Column(String(20))  # Tích cực, Tiêu cực, Trung lập
    
    # Độ tin cậy
    confidence = Column(Float)  # 0-1
    
    # Scores chi tiết cho tất cả emotions (JSON)
    emotion_scores = Column(JSON)  # {"vui_mừng": 0.3, "phẫn_nộ": 0.1, ...}
    
    # Metadata cho dashboard
    category = Column(String(256), index=True)  # Chủ đề/danh mục
    topic_id = Column(Integer, index=True)  # Topic từ topic modeling
    topic_name = Column(String(512))
    
    # Thời gian
    published_date = Column(DateTime, index=True)  # Ngày đăng bài
    analyzed_at = Column(DateTime, server_default=func.now())  # Ngày phân tích
    
    # Content snippet để preview
    content_snippet = Column(Text)  # 200 chars đầu
