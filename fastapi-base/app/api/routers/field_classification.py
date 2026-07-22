"""
API endpoints để quản lý lĩnh vực và phân loại bài viết
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.schemas.schema_field_classification import (
    FieldCreate,
    FieldUpdate,
    FieldResponse,
    ArticleFieldClassificationResponse,
    ClassificationRequest,
    ClassificationStatsResponse,
    FieldDistributionResponse,
    FieldDistributionItem,
    FieldStatisticsResponse,
    FieldSummaryResponse,
    CreateSummaryRequest
)
from app.models.model_field_classification import Field, ArticleFieldClassification, FieldStatistics
from app.models.model_field_summary import FieldSummary
from app.services.classification.field_classifier import FieldClassificationService
from app.services.classification.summary_service import FieldSummaryService
from datetime import datetime, date
import time

router = APIRouter(prefix="/fields", tags=["Field Classification"])


# ==================== FIELD MANAGEMENT ====================

@router.get("/", response_model=List[FieldResponse])
async def get_all_fields(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Lấy danh sách tất cả lĩnh vực"""
    fields = db.query(Field).order_by(Field.order_index).offset(skip).limit(limit).all()
    return fields


@router.get("/{field_id}", response_model=FieldResponse)
async def get_field(field_id: int, db: Session = Depends(get_db)):
    """Lấy thông tin một lĩnh vực"""
    field = db.query(Field).filter(Field.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    return field


@router.post("/", response_model=FieldResponse)
async def create_field(field: FieldCreate, db: Session = Depends(get_db)):
    """Tạo lĩnh vực mới"""
    # Kiểm tra tên đã tồn tại chưa
    existing = db.query(Field).filter(Field.name == field.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Field name already exists")
    
    db_field = Field(
        name=field.name,
        description=field.description,
        keywords=field.keywords,
        order_index=field.order_index,
        created_at=time.time(),
        updated_at=time.time()
    )
    db.add(db_field)
    db.commit()
    db.refresh(db_field)
    return db_field


@router.put("/{field_id}", response_model=FieldResponse)
async def update_field(
    field_id: int, 
    field_update: FieldUpdate, 
    db: Session = Depends(get_db)
):
    """Cập nhật thông tin lĩnh vực"""
    field = db.query(Field).filter(Field.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    
    # Update các trường
    if field_update.name is not None:
        # Kiểm tra tên mới có trùng không
        existing = db.query(Field).filter(
            Field.name == field_update.name,
            Field.id != field_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Field name already exists")
        field.name = field_update.name
    
    if field_update.description is not None:
        field.description = field_update.description
    
    if field_update.keywords is not None:
        field.keywords = field_update.keywords
    
    if field_update.order_index is not None:
        field.order_index = field_update.order_index
    
    field.updated_at = time.time()
    db.commit()
    db.refresh(field)
    return field


@router.delete("/{field_id}")
async def delete_field(field_id: int, db: Session = Depends(get_db)):
    """Xóa lĩnh vực"""
    field = db.query(Field).filter(Field.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    
    db.delete(field)
    db.commit()
    return {"message": "Field deleted successfully"}


# ==================== CLASSIFICATION ====================

@router.post("/classify", response_model=ClassificationStatsResponse)
async def classify_articles(
    request: ClassificationRequest,
    use_llm: bool = Query(True, description="Có sử dụng LLM cho bài không match keyword"),
    db: Session = Depends(get_db)
):
    """
    Phân loại bài viết vào các lĩnh vực
    - Nếu không truyền article_ids, sẽ phân loại tất cả bài viết chưa được phân loại
    - force_reclassify=True để phân loại lại các bài đã được phân loại
    - method: 
        + auto (mặc định): Dùng keyword trước, không match thì dùng LLM
        + keyword: Chỉ dùng keyword matching
        + llm: Chỉ dùng LLM (chậm hơn nhưng chính xác hơn)
    """
    service = FieldClassificationService(db, use_llm=use_llm)
    
    # Phân loại
    result = service.classify_articles_batch(
        article_ids=request.article_ids,
        force=request.force_reclassify,
        method=request.method
    )
    
    # Cập nhật thống kê
    service.update_field_statistics()
    
    # Tính tổng số bài viết
    from app.models.model_article import Article
    total_articles = db.query(Article).count()
    classified_articles = db.query(ArticleFieldClassification).count()
    
    return ClassificationStatsResponse(
        total_articles=total_articles,
        classified_articles=classified_articles,
        unclassified_articles=total_articles - classified_articles,
        field_distribution=result["field_distribution"],
        method_stats=result.get("method_stats"),
        classification_time=result["processing_time"]
    )


@router.get("/distribution/overview", response_model=FieldDistributionResponse)
async def get_field_distribution(db: Session = Depends(get_db)):
    """Lấy phân bố số lượng bài viết theo lĩnh vực"""
    service = FieldClassificationService(db)
    distribution = service.get_field_distribution()
    
    from app.models.model_article import Article
    total_articles = db.query(Article).count()
    
    items = [
        FieldDistributionItem(**item)
        for item in distribution
    ]
    
    return FieldDistributionResponse(
        total_articles=total_articles,
        fields=items,
        last_updated=time.time()
    )


@router.get("/article/{article_id}/classification", response_model=Optional[ArticleFieldClassificationResponse])
async def get_article_classification(article_id: int, db: Session = Depends(get_db)):
    """Lấy thông tin phân loại của một bài viết"""
    classification = db.query(ArticleFieldClassification).filter(
        ArticleFieldClassification.article_id == article_id
    ).first()
    
    if not classification:
        return None
    
    return classification


@router.post("/article/{article_id}/classify", response_model=Optional[ArticleFieldClassificationResponse])
async def classify_single_article(
    article_id: int,
    force: bool = Query(False, description="Phân loại lại nếu đã tồn tại"),
    method: str = Query("auto", description="Phương pháp: auto, keyword, llm"),
    use_llm: bool = Query(True, description="Cho phép sử dụng LLM"),
    db: Session = Depends(get_db)
):
    """Phân loại một bài viết cụ thể"""
    from app.models.model_article import Article
    
    # Kiểm tra bài viết có tồn tại không
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    service = FieldClassificationService(db, use_llm=use_llm)
    result = service.classify_article(article_id, force=force, method=method)
    
    if not result:
        raise HTTPException(
            status_code=400, 
            detail="Could not classify article. No matching field found."
        )
    
    return result


# ==================== STATISTICS ====================

@router.get("/statistics/all", response_model=List[FieldStatisticsResponse])
async def get_all_statistics(db: Session = Depends(get_db)):
    """Lấy thống kê của tất cả lĩnh vực"""
    service = FieldClassificationService(db)
    stats = service.get_all_statistics()
    return stats


@router.get("/statistics/{field_id}", response_model=FieldStatisticsResponse)
async def get_field_statistics(field_id: int, db: Session = Depends(get_db)):
    """Lấy thống kê của một lĩnh vực"""
    stats = db.query(FieldStatistics).filter(
        FieldStatistics.field_id == field_id
    ).first()
    
    if not stats:
        raise HTTPException(status_code=404, detail="Statistics not found for this field")
    
    return stats


@router.post("/statistics/update")
async def update_statistics(
    field_id: Optional[int] = Query(None, description="ID lĩnh vực cần update. Nếu None, update tất cả"),
    db: Session = Depends(get_db)
):
    """Cập nhật thống kê cho một hoặc tất cả lĩnh vực"""
    service = FieldClassificationService(db)
    service.update_field_statistics(field_id=field_id)
    
    return {"message": "Statistics updated successfully"}


# ==================== SEED DATA ====================

@router.post("/seed")
async def seed_fields(db: Session = Depends(get_db)):
    """Seed dữ liệu các lĩnh vực từ bảng phân loại"""
    
    fields_data = [
        {
            "name": "Kinh tế & Việc làm",
            "description": "Thủ tục đầu tư, doanh nghiệp, khu công nghiệp; Việc làm, thất nghiệp, thu nhập; Nông nghiệp - nông thôn (sản xuất, tiêu thu nông sản, thiên tai); Thương mại, giá cả, thị trường; Du lịch, dịch vụ; Ngân sách, tài chính gia phương",
            "keywords": ["kinh tế", "doanh nghiệp", "đầu tư", "khu công nghiệp", "việc làm", "thất nghiệp", "thu nhập", "nông nghiệp", "nông thôn", "nông sản", "thiên tai", "thương mại", "giá cả", "thị trường", "du lịch", "dịch vụ", "ngân sách", "tài chính"]
        },
        {
            "name": "Y tế & Chăm sóc sức khỏe",
            "description": "Chất lượng khám chữa bệnh; Bệnh viện, trạm y tế; Giá dịch vụ y tế, thẻ bảo hiểm y tế; Dịch bệnh, tiêm chủng, an toàn y tế",
            "keywords": ["bệnh viện", "bác sĩ", "bảo hiểm y tế", "viện phí", "dịch bệnh", "khám chữa bệnh", "trạm y tế", "giá dịch vụ y tế", "bảo hiểm y tế", "dịch bệnh", "tiêm chủng", "an toàn y tế"]
        },
        {
            "name": "Giáo dục & Đào tạo",
            "description": "Chất lượng trường lớp; Học phí, thu - chi giáo dục; Tuyển sinh, thi tú; Cơ hội tiếp cận giáo dục",
            "keywords": ["học phí", "trường học", "giáo viên", "thi cử", "tuyển sinh", "chất lượng trường lớp", "thu chi giáo dục", "cơ hội tiếp cận giáo dục"]
        },
        {
            "name": "Hạ tầng & Giao thông",
            "description": "Đường xá, cầu cống, kết xe; Điện, nước, vệ sinh công cộng; Dự án hạ tầng, chậm tiến độ",
            "keywords": ["đường xá", "kết xe", "mất điện", "nước sạch", "dự án", "cầu cống", "điện", "nước", "vệ sinh công cộng", "hạ tầng", "chậm tiến độ"]
        },
        {
            "name": "Môi trường & Biến đổi khí hậu",
            "description": "Rác thải, ô nhiễm (không khí, nước); Xử lý chất thải; Ngập lụt, hạn hán, thiên tai; Biến đổi khí hậu",
            "keywords": ["ô nhiễm", "rác thải", "ngập lụt", "môi trường sống", "xử lý chất thải", "ngập lụt", "hạn hán", "thiên tai", "biến đổi khí hậu"]
        },
        {
            "name": "An sinh xã hội & Chính sách",
            "description": "Giảm nghèo, hỗ trợ dân; Người có công, người cao tuổi; Bảo hiểm xã hội; Chính sách hỗ trợ dân sinh",
            "keywords": ["trợ cấp", "hỗ trợ", "người nghèo", "bảo hiểm xã hội", "giảm nghèo", "người có công", "người cao tuổi", "chính sách hỗ trợ dân sinh"]
        },
        {
            "name": "An ninh, Trật tự & Quốc phòng",
            "description": "An ninh trật tự; Tội phạm, tai nạn; Khiếu kiện động người; Quốc phòng",
            "keywords": ["mất trật tự", "trộm cắp", "tai nạn", "khiếu kiện", "an ninh trật tự", "tội phạm", "khiếu kiện động người", "quốc phòng"]
        },
        {
            "name": "Hành chính công & Quản lý Nhà nước",
            "description": "Thủ tục hành chính; Dịch vụ công; Cải cách hành chính (CCHC); Minh bạch, thái độ cán bộ",
            "keywords": ["thủ tục", "hành chính", "giấy tờ", "chậm trễ", "thái độ", "nhũng nhiễu", "dịch vụ công", "cải cách hành chính", "minh bạch"]
        },
        {
            "name": "Xây dựng Đảng & Hệ thống chính trị",
            "description": "Công tác cán bộ; Phòng chống tham nhũng; Hoạt động của Mặt trận, Đoàn thể",
            "keywords": ["cán bộ", "tham nhũng", "kỷ luật", "tổ chức đảng", "phòng chống tham nhũng", "hoạt động mặt trận", "đoàn thể"]
        },
        {
            "name": "Văn hóa, Thể thao & Đời sống tinh thần",
            "description": "Hoạt động văn hóa, lễ hội; Thể thao, vui chơi giải trí; Bảo tồn di sản",
            "keywords": ["lễ hội", "văn hóa", "thể thao", "vui chơi", "hoạt động văn hóa", "thể thao", "vui chơi giải trí", "bảo tồn di sản"]
        }
    ]
    
    created_count = 0
    for field_data in fields_data:
        existing = db.query(Field).filter(Field.name == field_data["name"]).first()
        if not existing:
            field = Field(
                name=field_data["name"],
                description=field_data["description"],
                keywords=field_data["keywords"],
                order_index=created_count + 1,
                created_at=time.time(),
                updated_at=time.time()
            )
            db.add(field)
            created_count += 1
    
    db.commit()
    
    return {
        "message": f"Seeded {created_count} fields successfully",
        "total_fields": db.query(Field).count()
    }


# ==================== FIELD SUMMARIES ====================

@router.post("/summaries/generate", response_model=List[FieldSummaryResponse])
async def generate_summaries(
    request: CreateSummaryRequest,
    db: Session = Depends(get_db)
):
    """
    Tạo tóm tắt thông tin gần đây cho lĩnh vực
    - Phân tích các bài viết trong kỳ (daily/weekly/monthly)
    - Tạo tóm tắt bằng LLM về xu hướng, chủ đề chính
    - Lấy top bài viết nổi bật, từ khóa trending
    """
    service = FieldSummaryService(db)
    
    if not service.is_llm_available():
        raise HTTPException(
            status_code=503,
            detail="LLM service not available. Please configure OPENAI_API_KEY"
        )
    
    # Parse target date
    target_date_obj = None
    if request.target_date:
        try:
            target_date_obj = datetime.strptime(request.target_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Generate summaries
    if request.field_ids:
        summaries = []
        for field_id in request.field_ids:
            summary = service.create_summary(
                field_id=field_id,
                period=request.period,
                target_date=target_date_obj,
                model=request.model
            )
            if summary:
                summaries.append(summary)
    else:
        summaries = service.create_summaries_for_all_fields(
            period=request.period,
            target_date=target_date_obj,
            model=request.model
        )
    
    return summaries


@router.get("/summaries/latest", response_model=List[FieldSummaryResponse])
async def get_latest_summaries(
    period: str = Query("daily", description="Kỳ: daily, weekly, monthly"),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Lấy các tóm tắt mới nhất"""
    service = FieldSummaryService(db)
    summaries = service.get_latest_summaries(period=period, limit=limit)
    return summaries


@router.get("/summaries/{field_id}", response_model=List[FieldSummaryResponse])
async def get_field_summaries(
    field_id: int,
    period: Optional[str] = Query(None, description="Kỳ: daily, weekly, monthly"),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Lấy tóm tắt của một lĩnh vực cụ thể"""
    # Check if field exists
    field = db.query(Field).filter(Field.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    
    service = FieldSummaryService(db)
    summaries = service.get_field_summaries(
        field_id=field_id,
        period=period,
        limit=limit
    )
    return summaries


@router.get("/summaries/detail/{summary_id}", response_model=FieldSummaryResponse)
async def get_summary_detail(summary_id: int, db: Session = Depends(get_db)):
    """Lấy chi tiết một tóm tắt"""
    summary = db.query(FieldSummary).filter(FieldSummary.id == summary_id).first()
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    return summary

