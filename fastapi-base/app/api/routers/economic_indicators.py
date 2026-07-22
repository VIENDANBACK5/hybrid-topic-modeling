"""
Economic Indicators API Endpoints
API quản lý và truy vấn các chỉ số kinh tế
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.schemas.schema_economic_indicators import (
    EconomicIndicatorCreate,
    EconomicIndicatorUpdate,
    EconomicIndicatorResponse,
    EconomicIndicatorQuery,
    EconomicIndicatorGPTRequest,
    EconomicIndicatorGPTResponse,
    EconomicIndicatorSummary
)
from app.services.economic_indicator_service import EconomicIndicatorService
from app.services.openai_economic_service import (
    fill_missing_fields, 
    generate_summary,
    generate_all_analyses,
    generate_indicator_analysis
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/economic-indicators", tags=["Economic Indicators"])


# ============================================
# ECONOMIC INDICATORS CRUD
# ============================================

@router.post("/", response_model=EconomicIndicatorResponse, status_code=201)
async def create_indicator(
    indicator: EconomicIndicatorCreate,
    db: Session = Depends(get_db)
):
    """
     Tạo mới một chỉ số kinh tế
    
    **Ví dụ:**
    ```json
    {
      "period_type": "monthly",
      "period_start": "2025-01-01",
      "period_end": "2025-01-31",
      "period_label": "Tháng 1/2025",
      "year": 2025,
      "month": 1,
      "province": "Hà Nội",
      "grdp_growth_rate": 6.5,
      "iip_growth_rate": 8.2,
      "cpi_growth_rate": 3.1,
      "export_value": 1500.5,
      "fdi_disbursed": 1200.0,
      "state_budget_revenue": 45000.0,
      "data_source": "GSO"
    }
    ```
    """
    try:
        service = EconomicIndicatorService(db)
        result = service.create_indicator(indicator)
        return result
    except Exception as e:
        logger.error(f"Failed to create indicator: {e}")
        raise HTTPException(500, f"Failed to create indicator: {str(e)}")


@router.get("/{indicator_id}", response_model=EconomicIndicatorResponse)
async def get_indicator(
    indicator_id: int,
    db: Session = Depends(get_db)
):
    """
     Lấy thông tin một chỉ số kinh tế theo ID
    """
    service = EconomicIndicatorService(db)
    result = service.get_indicator(indicator_id)
    
    if not result:
        raise HTTPException(404, f"Indicator {indicator_id} not found")
    
    return result


@router.put("/{indicator_id}", response_model=EconomicIndicatorResponse)
async def update_indicator(
    indicator_id: int,
    indicator: EconomicIndicatorUpdate,
    db: Session = Depends(get_db)
):
    """
     Cập nhật một chỉ số kinh tế
    """
    try:
        service = EconomicIndicatorService(db)
        result = service.update_indicator(indicator_id, indicator)
        
        if not result:
            raise HTTPException(404, f"Indicator {indicator_id} not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update indicator: {e}")
        raise HTTPException(500, f"Failed to update indicator: {str(e)}")


@router.delete("/{indicator_id}")
async def delete_indicator(
    indicator_id: int,
    db: Session = Depends(get_db)
):
    """
     Xóa một chỉ số kinh tế
    """
    try:
        service = EconomicIndicatorService(db)
        result = service.delete_indicator(indicator_id)
        
        if not result:
            raise HTTPException(404, f"Indicator {indicator_id} not found")
        
        return {"message": f"Indicator {indicator_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete indicator: {e}")
        raise HTTPException(500, f"Failed to delete indicator: {str(e)}")


# ============================================
# QUERY & SEARCH
# ============================================

@router.get("/", response_model=dict)
async def query_indicators(
    period_type: Optional[str] = Query(None, description="Loại kỳ: monthly, quarterly, yearly"),
    year: Optional[int] = Query(None, description="Năm"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Tháng (1-12)"),
    quarter: Optional[int] = Query(None, ge=1, le=4, description="Quý (1-4)"),
    province: Optional[str] = Query(None, description="Tỉnh/thành phố"),
    region: Optional[str] = Query(None, description="Miền"),
    page: int = Query(1, ge=1, description="Trang"),
    page_size: int = Query(20, ge=1, le=100, description="Số items mỗi trang"),
    sort_by: str = Query("period_start", description="Sắp xếp theo trường"),
    order: str = Query("desc", description="Thứ tự: asc, desc"),
    db: Session = Depends(get_db)
):
    """
     Query các chỉ số kinh tế với filters và pagination
    
    **Filters:**
    - `period_type`: monthly, quarterly, yearly
    - `year`: Năm
    - `month`: Tháng (1-12)
    - `quarter`: Quý (1-4)
    - `province`: Tỉnh/thành phố
    - `region`: Miền (Bắc, Trung, Nam)
    
    **Pagination:**
    - `page`: Trang hiện tại
    - `page_size`: Số items mỗi trang
    
    **Sorting:**
    - `sort_by`: Trường để sort (period_start, grdp_growth_rate, cpi_growth_rate, etc.)
    - `order`: asc hoặc desc
    """
    try:
        query = EconomicIndicatorQuery(
            period_type=period_type,
            year=year,
            month=month,
            quarter=quarter,
            province=province,
            region=region,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            order=order
        )
        
        service = EconomicIndicatorService(db)
        result = service.query_indicators(query)
        
        return result
    except Exception as e:
        logger.error(f"Failed to query indicators: {e}")
        raise HTTPException(500, f"Failed to query indicators: {str(e)}")


@router.get("/latest/indicator", response_model=EconomicIndicatorResponse)
async def get_latest_indicator(
    period_type: Optional[str] = Query(None, description="Loại kỳ"),
    province: Optional[str] = Query(None, description="Tỉnh/thành phố"),
    db: Session = Depends(get_db)
):
    """
     Lấy chỉ số kinh tế mới nhất
    """
    service = EconomicIndicatorService(db)
    result = service.get_latest_indicator(period_type, province)
    
    if not result:
        raise HTTPException(404, "No indicator found")
    
    return result


# ============================================
# SUMMARY & STATISTICS
# ============================================

@router.get("/summary/period", response_model=EconomicIndicatorSummary)
async def get_period_summary(
    period_type: str = Query(..., description="Loại kỳ: monthly, quarterly, yearly"),
    year: int = Query(..., description="Năm"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Tháng (1-12)"),
    quarter: Optional[int] = Query(None, ge=1, le=4, description="Quý (1-4)"),
    province: Optional[str] = Query(None, description="Tỉnh/thành phố"),
    db: Session = Depends(get_db)
):
    """
     Lấy tóm tắt các chỉ số kinh tế cho một kỳ cụ thể
    
    **Ví dụ:**
    - Tháng: `?period_type=monthly&year=2025&month=1`
    - Quý: `?period_type=quarterly&year=2025&quarter=1`
    - Năm: `?period_type=yearly&year=2025`
    - Theo tỉnh: `?period_type=monthly&year=2025&month=1&province=Hà Nội`
    
    **Trả về:**
    - Số lượng chỉ số có sẵn
    - Danh sách chỉ số có sẵn và còn thiếu
    - Các chỉ số chính (key metrics)
    """
    try:
        service = EconomicIndicatorService(db)
        result = service.get_summary(
            period_type=period_type,
            year=year,
            month=month,
            quarter=quarter,
            province=province
        )
        return result
    except Exception as e:
        logger.error(f"Failed to get summary: {e}")
        raise HTTPException(500, f"Failed to get summary: {str(e)}")


# ============================================
# GPT INTEGRATION
# ============================================

@router.post("/gpt/ask", response_model=EconomicIndicatorGPTResponse)
async def ask_gpt_for_indicator(
    request: EconomicIndicatorGPTRequest,
    db: Session = Depends(get_db)
):
    """
     Hỏi GPT để lấy dữ liệu chỉ số kinh tế khi không có trong DB
    
    **Ví dụ:**
    ```json
    {
      "indicator_name": "grdp_growth_rate",
      "period_type": "monthly",
      "year": 2025,
      "month": 1,
      "province": "Hà Nội",
      "additional_context": "Latest economic growth data"
    }
    ```
    
    **Note:** Hiện tại chưa tích hợp GPT API thực tế, trả về placeholder data
    """
    try:
        service = EconomicIndicatorService(db)
        result = service.ask_gpt_for_indicator(request)
        return result
    except Exception as e:
        logger.error(f"Failed to ask GPT: {e}")
        raise HTTPException(500, f"Failed to ask GPT: {str(e)}")


# ============================================
# BATCH IMPORT
# ============================================

@router.post("/batch/import")
async def batch_import_indicators(
    indicators: List[dict],
    db: Session = Depends(get_db)
):
    """
     Import hàng loạt chỉ số kinh tế từ file hoặc API
    
    **Ví dụ:**
    ```json
    [
      {
        "period_type": "monthly",
        "period_start": "2025-01-01",
        "period_end": "2025-01-31",
        "year": 2025,
        "month": 1,
        "grdp_growth_rate": 6.5,
        "iip_growth_rate": 8.2
      },
      ...
    ]
    ```
    
    **Trả về:**
    - Số lượng records được tạo mới
    - Số lượng records được cập nhật
    - Danh sách lỗi (nếu có)
    """
    try:
        service = EconomicIndicatorService(db)
        result = service.batch_import_indicators(indicators)
        return result
    except Exception as e:
        logger.error(f"Failed to batch import: {e}")
        raise HTTPException(500, f"Failed to batch import: {str(e)}")


# ============================================
# OPENAI FILL MISSING DATA
# ============================================

@router.post("/{indicator_id}/fill-missing")
async def fill_missing_data(
    indicator_id: int,
    db: Session = Depends(get_db)
):
    """
     Dùng OpenAI để fill các trường NULL trong indicator
    
    **Chức năng:**
    - Kiểm tra các trường quan trọng bị NULL
    - Gọi OpenAI để tìm kiếm dữ liệu
    - Cập nhật vào database
    
    **Ví dụ:**
    ```
    POST /api/v1/economic-indicators/5/fill-missing
    ```
    """
    try:
        service = EconomicIndicatorService(db)
        indicator = service.get_indicator(indicator_id)
        
        if not indicator:
            raise HTTPException(404, f"Indicator {indicator_id} not found")
        
        # Convert to dict
        indicator_dict = {
            "id": indicator.id,
            "period_label": indicator.period_label,
            "province": indicator.province,
            "grdp_growth_rate": indicator.grdp_growth_rate,
            "iip_growth_rate": indicator.iip_growth_rate,
            "cpi_growth_rate": indicator.cpi_growth_rate,
            "export_value": indicator.export_value,
            "fdi_disbursed": indicator.fdi_disbursed,
            "state_budget_revenue": indicator.state_budget_revenue,
            "notes": indicator.notes,
            "is_estimated": indicator.is_estimated
        }
        
        # Fill missing fields
        logger.info(f" Filling missing data for indicator {indicator_id}")
        filled_data = fill_missing_fields(indicator_dict, use_openai=True)
        
        # Update in database
        from app.schemas.schema_economic_indicators import EconomicIndicatorUpdate
        update_data = EconomicIndicatorUpdate(
            grdp_growth_rate=filled_data.get("grdp_growth_rate"),
            iip_growth_rate=filled_data.get("iip_growth_rate"),
            cpi_growth_rate=filled_data.get("cpi_growth_rate"),
            export_value=filled_data.get("export_value"),
            fdi_disbursed=filled_data.get("fdi_disbursed"),
            state_budget_revenue=filled_data.get("state_budget_revenue"),
            notes=filled_data.get("notes"),
            is_estimated=filled_data.get("is_estimated")
        )
        
        updated = service.update_indicator(indicator_id, update_data)
        
        return {
            "message": "Successfully filled missing data",
            "indicator_id": indicator_id,
            "updated_fields": [k for k, v in filled_data.items() if v != indicator_dict.get(k)],
            "data": updated
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fill missing data: {e}")
        raise HTTPException(500, f"Failed to fill missing data: {str(e)}")


@router.post("/batch/fill-missing")
async def batch_fill_missing_data(
    year: Optional[int] = Query(None, description="Chỉ fill cho năm cụ thể"),
    month: Optional[int] = Query(None, description="Chỉ fill cho tháng cụ thể"),
    limit: int = Query(10, ge=1, le=100, description="Số lượng records tối đa"),
    db: Session = Depends(get_db)
):
    """
     Fill missing data hàng loạt cho nhiều indicators
    
    **Chức năng:**
    - Tìm các indicators có trường NULL
    - Dùng OpenAI fill từng indicator
    - Trả về kết quả tổng hợp
    
    **Ví dụ:**
    ```
    POST /api/v1/economic-indicators/batch/fill-missing?year=2025&limit=5
    ```
    """
    try:
        from app.models.model_economic_indicators import EconomicIndicator
        from sqlalchemy import or_
        
        # Find indicators with missing important fields
        query = db.query(EconomicIndicator).filter(
            or_(
                EconomicIndicator.grdp_growth_rate.is_(None),
                EconomicIndicator.iip_growth_rate.is_(None),
                EconomicIndicator.cpi_growth_rate.is_(None),
                EconomicIndicator.export_value.is_(None),
                EconomicIndicator.fdi_disbursed.is_(None),
                EconomicIndicator.state_budget_revenue.is_(None)
            )
        )
        
        if year:
            query = query.filter(EconomicIndicator.year == year)
        if month:
            query = query.filter(EconomicIndicator.month == month)
        
        indicators = query.limit(limit).all()
        
        logger.info(f" Found {len(indicators)} indicators with missing data")
        
        results = []
        for indicator in indicators:
            try:
                indicator_dict = {
                    "id": indicator.id,
                    "period_label": indicator.period_label,
                    "province": indicator.province,
                    "grdp_growth_rate": indicator.grdp_growth_rate,
                    "iip_growth_rate": indicator.iip_growth_rate,
                    "cpi_growth_rate": indicator.cpi_growth_rate,
                    "export_value": indicator.export_value,
                    "fdi_disbursed": indicator.fdi_disbursed,
                    "state_budget_revenue": indicator.state_budget_revenue,
                }
                
                filled_data = fill_missing_fields(indicator_dict, use_openai=True)
                
                # Update
                for key, value in filled_data.items():
                    if key not in ["id"] and value is not None:
                        setattr(indicator, key, value)
                
                results.append({
                    "id": indicator.id,
                    "period_label": indicator.period_label,
                    "status": "updated"
                })
                
            except Exception as e:
                logger.error(f"Failed to fill indicator {indicator.id}: {e}")
                results.append({
                    "id": indicator.id,
                    "period_label": indicator.period_label,
                    "status": "failed",
                    "error": str(e)
                })
        
        db.commit()
        
        return {
            "total_processed": len(results),
            "successful": len([r for r in results if r["status"] == "updated"]),
            "failed": len([r for r in results if r["status"] == "failed"]),
            "results": results
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to batch fill: {e}")
        raise HTTPException(500, f"Failed to batch fill: {str(e)}")


# ============================================
# AUTO-GENERATE SUMMARY
# ============================================

@router.post("/generate-summaries", response_model=dict)
async def generate_summaries_for_indicators(
    indicator_ids: Optional[List[int]] = None,
    regenerate: bool = False,
    limit: int = Query(10, ge=1, le=100, description="Số lượng records tối đa"),
    db: Session = Depends(get_db)
):
    """
     Tự động tạo summary cho economic indicators bằng OpenAI
    
    **Tham số:**
    - `indicator_ids`: List các ID cụ thể cần gen summary. Nếu None = gen cho tất cả
    - `regenerate`: True = gen lại cả những record đã có summary. False = chỉ gen cho NULL
    - `limit`: Số lượng records tối đa xử lý
    
    **Ví dụ:**
    ```
    POST /api/v1/economic-indicators/generate-summaries?limit=5
    POST /api/v1/economic-indicators/generate-summaries?regenerate=true&limit=10
    
    Body (optional):
    {
      "indicator_ids": [1, 2, 3]
    }
    ```
    """
    try:
        from app.models.model_economic_indicators import EconomicIndicator
        
        # Build query
        query = db.query(EconomicIndicator)
        
        if indicator_ids:
            query = query.filter(EconomicIndicator.id.in_(indicator_ids))
        elif not regenerate:
            # Chỉ lấy những record chưa có summary
            query = query.filter(
                or_(
                    EconomicIndicator.summary.is_(None),
                    EconomicIndicator.summary == ''
                )
            )
        
        indicators = query.limit(limit).all()
        
        logger.info(f" Generating summaries for {len(indicators)} indicators")
        
        results = []
        for indicator in indicators:
            try:
                # Convert to dict
                indicator_dict = {
                    "id": indicator.id,
                    "period_label": indicator.period_label,
                    "province": indicator.province,
                    "grdp_growth_rate": indicator.grdp_growth_rate,
                    "iip_growth_rate": indicator.iip_growth_rate,
                    "retail_services_growth": indicator.retail_services_growth,
                    "export_value": indicator.export_value,
                    "fdi_disbursed": indicator.fdi_disbursed,
                    "total_investment": indicator.total_investment,
                    "state_budget_revenue": indicator.state_budget_revenue,
                    "sbr_growth_rate": indicator.sbr_growth_rate,
                    "cpi_growth_rate": indicator.cpi_growth_rate,
                }
                
                # Generate summary
                summary = generate_summary(indicator_dict)
                
                if summary:
                    indicator.summary = summary
                    results.append({
                        "id": indicator.id,
                        "period_label": indicator.period_label,
                        "province": indicator.province,
                        "status": "generated",
                        "summary_length": len(summary)
                    })
                    logger.info(f"   Generated summary for indicator {indicator.id}")
                else:
                    results.append({
                        "id": indicator.id,
                        "period_label": indicator.period_label,
                        "status": "failed",
                        "error": "No summary returned from OpenAI"
                    })
                
            except Exception as e:
                logger.error(f"Failed to generate summary for indicator {indicator.id}: {e}")
                results.append({
                    "id": indicator.id,
                    "period_label": indicator.period_label,
                    "status": "error",
                    "error": str(e)
                })
        
        db.commit()
        
        successful = len([r for r in results if r["status"] == "generated"])
        failed = len([r for r in results if r["status"] in ["failed", "error"]])
        
        return {
            "total_processed": len(results),
            "successful": successful,
            "failed": failed,
            "results": results
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to generate summaries: {e}")
        raise HTTPException(500, f"Failed to generate summaries: {str(e)}")


@router.post("/generate-analyses", response_model=dict)
async def generate_analyses_for_indicators(
    indicator_ids: Optional[List[int]] = None,
    regenerate: bool = False,
    limit: int = Query(10, ge=1, le=100, description="Số lượng records tối đa"),
    db: Session = Depends(get_db)
):
    """
     Tự động tạo phân tích chi tiết cho từng nhóm chỉ số bằng OpenAI
    
    **Tham số:**
    - `indicator_ids`: List các ID cụ thể. Nếu None = gen cho tất cả
    - `regenerate`: True = gen lại cả những record đã có. False = chỉ gen cho NULL
    - `limit`: Số lượng records tối đa xử lý
    
    **Ví dụ:**
    ```
    POST /api/v1/economic-indicators/generate-analyses?limit=5
    POST /api/v1/economic-indicators/generate-analyses?regenerate=true
    
    Body (optional):
    {"indicator_ids": [1, 2, 3]}
    ```
    """
    try:
        from app.models.model_economic_indicators import EconomicIndicator
        
        # Build query
        query = db.query(EconomicIndicator)
        
        if indicator_ids:
            query = query.filter(EconomicIndicator.id.in_(indicator_ids))
        
        indicators = query.limit(limit).all()
        
        logger.info(f" Generating analyses for {len(indicators)} indicators")
        
        results = []
        for indicator in indicators:
            try:
                # Convert to dict
                indicator_dict = {
                    "id": indicator.id,
                    "period_label": indicator.period_label,
                    "province": indicator.province,
                    "detailed_data": indicator.detailed_data or {},
                    "source_article_url": indicator.source_article_url,
                }
                
                # Generate all analyses
                analyses = generate_all_analyses(indicator_dict)
                
                if analyses:
                    # Update các trường analysis
                    if "grdp_analysis" in analyses:
                        indicator.grdp_analysis = analyses["grdp_analysis"]
                    if "iip_analysis" in analyses:
                        indicator.iip_analysis = analyses["iip_analysis"]
                    if "agricultural_analysis" in analyses:
                        indicator.agricultural_analysis = analyses["agricultural_analysis"]
                    if "retail_services_analysis" in analyses:
                        indicator.retail_services_analysis = analyses["retail_services_analysis"]
                    if "export_import_analysis" in analyses:
                        indicator.export_import_analysis = analyses["export_import_analysis"]
                    if "investment_analysis" in analyses:
                        indicator.investment_analysis = analyses["investment_analysis"]
                    if "budget_analysis" in analyses:
                        indicator.budget_analysis = analyses["budget_analysis"]
                    if "labor_analysis" in analyses:
                        indicator.labor_analysis = analyses["labor_analysis"]
                    
                    results.append({
                        "id": indicator.id,
                        "period_label": indicator.period_label,
                        "province": indicator.province,
                        "status": "generated",
                        "analyses_count": len(analyses)
                    })
                    logger.info(f"   Generated {len(analyses)} analyses for indicator {indicator.id}")
                else:
                    results.append({
                        "id": indicator.id,
                        "status": "failed",
                        "error": "No analyses returned"
                    })
                
            except Exception as e:
                logger.error(f"Failed to generate analyses for indicator {indicator.id}: {e}")
                results.append({
                    "id": indicator.id,
                    "status": "error",
                    "error": str(e)
                })
        
        db.commit()
        
        successful = len([r for r in results if r["status"] == "generated"])
        failed = len([r for r in results if r["status"] in ["failed", "error"]])
        
        return {
            "total_processed": len(results),
            "successful": successful,
            "failed": failed,
            "results": results
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to generate analyses: {e}")
        raise HTTPException(500, f"Failed to generate analyses: {str(e)}")
