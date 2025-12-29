from sqlalchemy import Column, Integer, String, Text, Float, Boolean, JSON
from app.models.model_base import BareBaseModel


class Article(BareBaseModel):
    """Model lưu các bài viết đã crawl"""
    __tablename__ = "articles"

    # Thông tin nguồn
    url = Column(String(2048), unique=True, nullable=False, index=True)
    source_type = Column(String(50), nullable=False)  # web, rss, file, api
    source = Column(String(512), nullable=False, index=True)  # URL gốc hoặc source name
    domain = Column(String(256), index=True)  # baohungyen.vn, vnexpress.net, etc.
    
    # Nội dung
    title = Column(String(1024))
    content = Column(Text)
    summary = Column(Text)
    author = Column(String(256))
    published_date = Column(Float)  # timestamp
    
    # Metadata
    category = Column(String(256), index=True)
    tags = Column(JSON)  # List[str]
    images = Column(JSON)  # List[str]
    videos = Column(JSON)  # List[str]
    
    # Xử lý
    is_cleaned = Column(Boolean, default=False)
    is_deduped = Column(Boolean, default=False)
    word_count = Column(Integer)
    
    # Topic modeling
    topic_id = Column(Integer, index=True, nullable=True)
    topic_name = Column(String(512), nullable=True)
    topic_probability = Column(Float, nullable=True)
    
    # Crawl metadata
    crawl_params = Column(JSON)  # params used for crawling
    raw_metadata = Column(JSON)  # original metadata from crawler
