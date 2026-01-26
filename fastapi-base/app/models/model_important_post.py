from sqlalchemy import Column, Integer, String, Text, Float, JSON, Index
from app.models.model_base import BareBaseModel


class ImportantPost(BareBaseModel):
    """
    Model lưu trữ các bài viết báo chí đặc biệt quan trọng
    Dữ liệu từ API /posts-v2/by-type-newspaper/medical và các endpoint tương tự
    """
    __tablename__ = "important_posts"

    # Thông tin cơ bản
    url = Column(String(2048), unique=True, nullable=False, index=True, comment="URL bài viết gốc")
    title = Column(String(1024), nullable=False, comment="Tiêu đề bài viết")
    content = Column(Text, nullable=False, comment="Nội dung đầy đủ bài viết")
    
    # Phân loại
    data_type = Column(String(50), nullable=False, index=True, default="newspaper", comment="Loại dữ liệu: newspaper, social, etc.")
    type_newspaper = Column(String(100), index=True, comment="Phân loại báo: medical, economic, social, etc.")
    
    # Metadata từ nguồn gốc
    original_id = Column(Integer, comment="ID từ hệ thống nguồn")
    original_created_at = Column(Float, comment="Thời gian tạo từ hệ thống nguồn")
    original_updated_at = Column(Float, comment="Thời gian cập nhật từ hệ thống nguồn")
    
    # Thông tin mở rộng (JSON)
    meta_data = Column(JSON, comment="Metadata từ nguồn bao gồm: date, statistics, organizations, author")
    
    # Trích xuất từ metadata để query nhanh hơn
    author = Column(String(512), comment="Tác giả bài viết")
    published_date = Column(String(100), comment="Ngày xuất bản (format từ nguồn)")
    dvhc = Column(String(256), index=True, comment="Đơn vị hành chính (địa phương)")
    
    # Thống kê và tổ chức liên quan (denormalized cho tìm kiếm)
    statistics = Column(JSON, comment="Danh sách các số liệu thống kê trong bài")
    organizations = Column(JSON, comment="Danh sách tổ chức được nhắc đến")
    
    # Cờ đánh dấu quan trọng
    is_featured = Column(Integer, default=1, index=True, comment="Đánh dấu bài viết nổi bật (1=featured, 0=normal)")
    importance_score = Column(Float, comment="Điểm đánh giá mức độ quan trọng")
    
    # Tags và phân loại bổ sung
    tags = Column(JSON, comment="Tags phân loại bổ sung")
    categories = Column(JSON, comment="Các danh mục liên quan")
    
    # Index ghép để tìm kiếm hiệu quả
    __table_args__ = (
        Index('idx_data_type_newspaper', 'data_type', 'type_newspaper'),
        Index('idx_featured_type', 'is_featured', 'type_newspaper'),
        Index('idx_importance', 'importance_score'),
        Index('idx_dvhc_type', 'dvhc', 'type_newspaper'),
    )

    def __repr__(self):
        return f"<ImportantPost(id={self.id}, type={self.type_newspaper}, title='{self.title[:50]}...')>"
