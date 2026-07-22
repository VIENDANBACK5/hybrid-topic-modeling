"""
API Endpoints for Social Indicator Extraction
9 Lĩnh vực × 3 Chỉ số = 27 bảng detail

Endpoints:
- POST /api/social-indicators/{field_key}/extract - Extract và fill data cho 1 lĩnh vực
- GET /api/social-indicators/{field_key}/summary - Lấy tổng quan data của lĩnh vực
- GET /api/social-indicators/fields - Danh sách tất cả lĩnh vực
- POST /api/social-indicators/extract-all - Extract tất cả lĩnh vực
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from app.core.database import get_db
from app.services.social_indicator_extractor import (
    FIELD_DEFINITIONS,
    CATEGORY_TO_FIELD,
    FIELD_TO_CATEGORIES,
    SocialIndicatorService
)

router = APIRouter(prefix="/api/social-indicators", tags=["Social Indicators Extraction"])


# =============================================================================
# SCHEMAS
# =============================================================================

class FieldInfo(BaseModel):
    """Info about a field"""
    key: str
    name: str
    indicators: List[Dict[str, str]]
    categories: List[str] = []  # Categories in articles that map to this field


class ExtractionRequest(BaseModel):
    """Request for extraction"""
    limit: int = Field(100, description="Max số bài viết để xử lý")
    year_filter: Optional[int] = Field(None, description="Lọc theo năm")
    province_filter: Optional[str] = Field(None, description="Lọc theo tỉnh/thành")
    use_category_filter: bool = Field(True, description="Lọc theo category của article (nhanh hơn nếu category đã được set)")
    use_llm: bool = Field(False, description="Sử dụng LLM (GPT) để extract indicators")


class ExtractionResponse(BaseModel):
    """Response for extraction"""
    field: str
    field_key: str
    articles_found: int
    articles_processed: int
    records_created: int
    indicators_filled: Dict[str, int]
    errors: List[str]
    duration_seconds: float


class FieldSummaryResponse(BaseModel):
    """Summary of field data"""
    field: str
    field_key: str
    indicators: Dict[str, Dict[str, Any]]


class IndicatorDataResponse(BaseModel):
    """Response with indicator data"""
    indicator_key: str
    indicator_name: str
    total_records: int
    data: List[Dict[str, Any]]


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/fields", response_model=List[FieldInfo])
def get_all_fields():
    """
    Lấy danh sách tất cả 9 lĩnh vực và các chỉ số
    
    Mỗi lĩnh vực bao gồm:
    - key: Mã lĩnh vực
    - name: Tên lĩnh vực
    - indicators: Danh sách 3 chỉ số
    - categories: Các giá trị category trong articles tương ứng với lĩnh vực này
    """
    fields = []
    for field_key, field_def in FIELD_DEFINITIONS.items():
        indicators = [
            {"key": ind_key, "name": ind_def["name"]}
            for ind_key, ind_def in field_def["indicators"].items()
        ]
        categories = FIELD_TO_CATEGORIES.get(field_key, [])
        fields.append(FieldInfo(
            key=field_key,
            name=field_def["name"],
            indicators=indicators,
            categories=categories
        ))
    return fields


@router.get("/fields/{field_key}", response_model=FieldInfo)
def get_field_info(field_key: str):
    """
    Lấy thông tin chi tiết của 1 lĩnh vực
    """
    field_def = FIELD_DEFINITIONS.get(field_key)
    if not field_def:
        raise HTTPException(status_code=404, detail=f"Field not found: {field_key}")
    
    indicators = [
        {"key": ind_key, "name": ind_def["name"]}
        for ind_key, ind_def in field_def["indicators"].items()
    ]
    categories = FIELD_TO_CATEGORIES.get(field_key, [])
    
    return FieldInfo(
        key=field_key,
        name=field_def["name"],
        indicators=indicators,
        categories=categories
    )


@router.post("/{field_key}/extract", response_model=ExtractionResponse)
def extract_field_data(
    field_key: str,
    request: ExtractionRequest,
    db: Session = Depends(get_db)
):
    """
    Trích xuất dữ liệu từ articles và fill vào các bảng của lĩnh vực
    
    - **field_key**: Key của lĩnh vực (vd: xay_dung_dang, van_hoa_the_thao, ...)
    - **limit**: Số bài viết tối đa để xử lý
    - **year_filter**: Lọc theo năm
    - **province_filter**: Lọc theo tỉnh/thành
    - **use_category_filter**: Nếu True, sẽ lọc theo category của article (nhanh hơn)
    
    SMART EXTRACTION:
    - Tự động dùng LLM (nếu có OpenAI API key) + Regex
    - LLM hiểu context phức tạp: "giảm 30%" vs "đạt 70%"
    - Regex làm backup: đảm bảo không bỏ sót
    - Merge kết quả: ưu tiên LLM > Regex
    
    CATEGORY TRONG ARTICLES (8 giá trị chuẩn):
    - medical/health → y_te (Y tế & Chăm sóc sức khỏe)
    - education → giao_duc (Giáo dục & Đào tạo)
    - security/police → an_ninh_trat_tu (An ninh, Trật tự)
    - politics → xay_dung_dang (Xây dựng Đảng)
    - social/culture → van_hoa_the_thao (Văn hóa, Thể thao)
    - environment → moi_truong (Môi trường)
    - welfare → an_sinh_xa_hoi (An sinh xã hội)
    - administration → hanh_chinh_cong (Hành chính công)
    - infrastructure/transport → ha_tang_giao_thong (Hạ tầng Giao thông)
    
    CATEGORY TRONG ARTICLES (8 giá trị chuẩn):
    - "medical" → y_te (Y tế & Chăm sóc sức khỏe)
    - "education" → giao_duc (Giáo dục & Đào tạo)
    - "transportation" → ha_tang_giao_thong (Hạ tầng & Giao thông)
    - "environment" → moi_truong (Môi trường & Biến đổi khí hậu)
    - "policy" → an_sinh_xa_hoi (An sinh xã hội & Chính sách)
    - "security" → an_ninh_trat_tu (An ninh, Trật tự & Quốc phòng)
    - "management" → hanh_chinh_cong (Hành chính công & Quản lý Nhà nước)
    - "politics" → xay_dung_dang (Xây dựng Đảng & Hệ thống chính trị)
    - "social" → van_hoa_the_thao (Văn hóa, Thể thao & Đời sống tinh thần)
    
    CHÚ Ý: 
    - Chỉ trích xuất số liệu có trong văn bản gốc (không bịa)
    - Nếu không tìm thấy số liệu, để NULL
    """
    # Convert dash to underscore (API uses dash, code uses underscore)
    field_key = field_key.replace('-', '_')
    
    if field_key not in FIELD_DEFINITIONS:
        raise HTTPException(status_code=404, detail=f"Field not found: {field_key}")
    
    start_time = datetime.now()
    
    service = SocialIndicatorService(db)
    result = service.process_field(
        field_key=field_key,
        limit=request.limit,
        year_filter=request.year_filter,
        province_filter=request.province_filter,
        use_category_filter=request.use_category_filter,
        use_llm=request.use_llm
    )
    
    duration = (datetime.now() - start_time).total_seconds()
    
    return ExtractionResponse(
        field=result.get("field", ""),
        field_key=result.get("field_key", field_key),
        articles_found=result.get("articles_found", 0),
        articles_processed=result.get("articles_processed", 0),
        records_created=result.get("records_created", 0),
        indicators_filled=result.get("indicators_filled", {}),
        errors=result.get("errors", []),
        duration_seconds=duration
    )


@router.get("/{field_key}/summary", response_model=FieldSummaryResponse)
def get_field_summary(
    field_key: str,
    db: Session = Depends(get_db)
):
    """
    Lấy tổng quan dữ liệu của 1 lĩnh vực
    
    Bao gồm:
    - Số lượng records trong mỗi bảng chỉ số
    - Năm/quý mới nhất có dữ liệu
    """
    # Convert dash to underscore
    field_key = field_key.replace('-', '_')
    
    if field_key not in FIELD_DEFINITIONS:
        raise HTTPException(status_code=404, detail=f"Field not found: {field_key}")
    
    service = SocialIndicatorService(db)
    result = service.get_field_summary(field_key)
    
    return FieldSummaryResponse(
        field=result.get("field", ""),
        field_key=result.get("field_key", field_key),
        indicators=result.get("indicators", {})
    )


@router.get("/{field_key}/{indicator_key}/data", response_model=IndicatorDataResponse)
def get_indicator_data(
    field_key: str,
    indicator_key: str,
    province: Optional[str] = Query(None, description="Lọc theo tỉnh/thành"),
    year: Optional[int] = Query(None, description="Lọc theo năm"),
    limit: int = Query(100, description="Số records tối đa"),
    db: Session = Depends(get_db)
):
    """
    Lấy dữ liệu của 1 chỉ số cụ thể
    """
    # Convert dash to underscore
    field_key = field_key.replace('-', '_')
    indicator_key = indicator_key.replace('-', '_')
    
    if field_key not in FIELD_DEFINITIONS:
        raise HTTPException(status_code=404, detail=f"Field not found: {field_key}")
    
    field_def = FIELD_DEFINITIONS[field_key]
    if indicator_key not in field_def["indicators"]:
        raise HTTPException(status_code=404, detail=f"Indicator not found: {indicator_key}")
    
    service = SocialIndicatorService(db)
    model_class = service.get_model_class(indicator_key)
    
    if not model_class:
        raise HTTPException(status_code=500, detail=f"Model not found for: {indicator_key}")
    
    query = db.query(model_class)
    
    if province:
        query = query.filter(model_class.province == province)
    if year:
        query = query.filter(model_class.year == year)
    
    records = query.order_by(
        model_class.year.desc(),
        model_class.quarter.desc().nullsfirst()
    ).limit(limit).all()
    
    # Convert to dict
    data = []
    for record in records:
        record_dict = {c.name: getattr(record, c.name) for c in record.__table__.columns}
        # Convert datetime to string
        for key, value in record_dict.items():
            if isinstance(value, datetime):
                record_dict[key] = value.isoformat()
        data.append(record_dict)
    
    return IndicatorDataResponse(
        indicator_key=indicator_key,
        indicator_name=field_def["indicators"][indicator_key]["name"],
        total_records=len(data),
        data=data
    )


@router.post("/extract-all")
def extract_all_fields(
    request: ExtractionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Trích xuất dữ liệu cho TẤT CẢ 9 lĩnh vực
    
    Chạy tuần tự qua từng lĩnh vực và tổng hợp kết quả
    """
    start_time = datetime.now()
    
    all_results = {
        "total_articles_found": 0,
        "total_articles_processed": 0,
        "total_records_created": 0,
        "by_field": {},
        "errors": []
    }
    
    service = SocialIndicatorService(db)
    
    for field_key in FIELD_DEFINITIONS.keys():
        try:
            result = service.process_field(
                field_key=field_key,
                limit=request.limit,
                year_filter=request.year_filter,
                province_filter=request.province_filter,
                use_category_filter=request.use_category_filter,
                use_llm=request.use_llm
            )
            
            all_results["total_articles_found"] += result.get("articles_found", 0)
            all_results["total_articles_processed"] += result.get("articles_processed", 0)
            all_results["total_records_created"] += result.get("records_created", 0)
            all_results["by_field"][field_key] = {
                "field_name": result.get("field", ""),
                "articles_processed": result.get("articles_processed", 0),
                "records_created": result.get("records_created", 0),
                "indicators_filled": result.get("indicators_filled", {}),
                "categories_used": result.get("categories_used", [])
            }
            all_results["errors"].extend(result.get("errors", []))
            
        except Exception as e:
            all_results["errors"].append(f"Field {field_key}: {str(e)}")
    
    duration = (datetime.now() - start_time).total_seconds()
    all_results["duration_seconds"] = duration
    
    return all_results


@router.get("/summary-all")
def get_all_fields_summary(db: Session = Depends(get_db)):
    """
    Lấy tổng quan dữ liệu của TẤT CẢ 9 lĩnh vực
    """
    service = SocialIndicatorService(db)
    
    summaries = {}
    total_records = 0
    
    for field_key in FIELD_DEFINITIONS.keys():
        summary = service.get_field_summary(field_key)
        summaries[field_key] = summary
        
        for ind_info in summary.get("indicators", {}).values():
            total_records += ind_info.get("total_records", 0)
    
    return {
        "total_fields": len(FIELD_DEFINITIONS),
        "total_indicators": sum(len(f["indicators"]) for f in FIELD_DEFINITIONS.values()),
        "total_records": total_records,
        "by_field": summaries
    }


# =============================================================================
# INDIVIDUAL FIELD SHORTCUTS (Optional convenience endpoints)
# =============================================================================

@router.post("/xay-dung-dang/extract", response_model=ExtractionResponse)
def extract_xay_dung_dang(request: ExtractionRequest, db: Session = Depends(get_db)):
    """Lĩnh vực 1: Xây dựng Đảng & Hệ thống chính trị"""
    return extract_field_data("xay_dung_dang", request, db)


@router.post("/van-hoa-the-thao/extract", response_model=ExtractionResponse)
def extract_van_hoa_the_thao(request: ExtractionRequest, db: Session = Depends(get_db)):
    """Lĩnh vực 2: Văn hóa, Thể thao & Đời sống tinh thần"""
    return extract_field_data("van_hoa_the_thao", request, db)


@router.post("/moi-truong/extract", response_model=ExtractionResponse)
def extract_moi_truong(request: ExtractionRequest, db: Session = Depends(get_db)):
    """Lĩnh vực 3: Môi trường & Biến đổi khí hậu"""
    return extract_field_data("moi_truong", request, db)


@router.post("/an-sinh-xa-hoi/extract", response_model=ExtractionResponse)
def extract_an_sinh_xa_hoi(request: ExtractionRequest, db: Session = Depends(get_db)):
    """Lĩnh vực 4: An sinh xã hội & Chính sách"""
    return extract_field_data("an_sinh_xa_hoi", request, db)


@router.post("/an-ninh-trat-tu/extract", response_model=ExtractionResponse)
def extract_an_ninh_trat_tu(request: ExtractionRequest, db: Session = Depends(get_db)):
    """Lĩnh vực 5: An ninh, Trật tự & Quốc phòng"""
    return extract_field_data("an_ninh_trat_tu", request, db)


@router.post("/hanh-chinh-cong/extract", response_model=ExtractionResponse)
def extract_hanh_chinh_cong(request: ExtractionRequest, db: Session = Depends(get_db)):
    """Lĩnh vực 6: Hành chính công & Quản lý Nhà nước"""
    return extract_field_data("hanh_chinh_cong", request, db)


@router.post("/y-te/extract", response_model=ExtractionResponse)
def extract_y_te(request: ExtractionRequest, db: Session = Depends(get_db)):
    """Lĩnh vực 7: Y tế & Chăm sóc sức khỏe"""
    return extract_field_data("y_te", request, db)


@router.post("/giao-duc/extract", response_model=ExtractionResponse)
def extract_giao_duc(request: ExtractionRequest, db: Session = Depends(get_db)):
    """Lĩnh vực 8: Giáo dục & Đào tạo"""
    return extract_field_data("giao_duc", request, db)


@router.post("/ha-tang-giao-thong/extract", response_model=ExtractionResponse)
def extract_ha_tang_giao_thong(request: ExtractionRequest, db: Session = Depends(get_db)):
    """Lĩnh vực 9: Hạ tầng & Giao thông"""
    return extract_field_data("ha_tang_giao_thong", request, db)


# =============================================================================
# CATEGORY MAPPING ENDPOINTS
# =============================================================================

@router.get("/category-mapping")
def get_category_mapping():
    """
    Lấy mapping giữa article.category và field_key
    
    Dùng để hiểu article có category nào sẽ được xử lý bởi endpoint nào
    """
    return {
        "category_to_field": CATEGORY_TO_FIELD,
        "field_to_categories": FIELD_TO_CATEGORIES,
        "description": "Khi article có category='medical', sẽ được xử lý bởi field 'y_te'"
    }


@router.get("/articles/category-stats")
def get_article_category_stats(db: Session = Depends(get_db)):
    """
    Thống kê số lượng articles theo category
    
    Để biết có bao nhiêu articles đã được gán category
    """
    from sqlalchemy import func
    from app.models.model_article import Article
    
    # Count articles by category
    stats = db.query(
        Article.category,
        func.count(Article.id).label('count')
    ).group_by(Article.category).all()
    
    result = {
        "total_articles": db.query(Article).count(),
        "articles_with_category": db.query(Article).filter(
            Article.category.isnot(None),
            Article.category != ''
        ).count(),
        "by_category": {
            cat if cat else "null": count 
            for cat, count in stats
        },
        "mapped_to_fields": {}
    }
    
    # Map categories to fields
    for cat, count in stats:
        if cat:
            field_key = CATEGORY_TO_FIELD.get(cat.lower())
            if field_key:
                if field_key not in result["mapped_to_fields"]:
                    result["mapped_to_fields"][field_key] = 0
                result["mapped_to_fields"][field_key] += count
    
    return result
