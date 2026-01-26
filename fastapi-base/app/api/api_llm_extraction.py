from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import Dict
import sys
import os
import importlib
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


def import_extraction_module(module_name: str):
    """Helper to import extraction modules dynamically"""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)
    
    # Use importlib for more robust dynamic importing
    import importlib
    try:
        module = importlib.import_module(f"call_llm.{module_name}")
        return module.main
    except Exception as e:
        logger.error(f"Failed to import call_llm.{module_name}: {e}")
        raise


# ============================================
# LĨNH VỰC 1: XÂY DỰNG ĐẢNG (type_newspaper='politics')
# ============================================

@router.post("/extract-politics", status_code=202)
async def trigger_politics_extraction(background_tasks: BackgroundTasks) -> Dict:
    """Async extraction cho Lĩnh vực: Xây dựng Đảng"""
    try:
        extract_main = import_extraction_module("extract_xay_dung_dang")
        background_tasks.add_task(extract_main)
        
        return {
            "status": "accepted",
            "message": "LLM extraction đã được khởi chạy ở background",
            "field": "Xây dựng Đảng",
            "type_newspaper": "politics",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-politics/sync", status_code=200)
def run_politics_extraction_sync() -> Dict:
    """Sync extraction cho Lĩnh vực: Xây dựng Đảng"""
    try:
        extract_main = import_extraction_module("extract_xay_dung_dang")
        result = extract_main()
        
        return {
            "status": "completed",
            "field": "Xây dựng Đảng",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# LĨNH VỰC 2: Y TẾ (type_newspaper='medical')
# ============================================

@router.post("/extract-medical", status_code=202)
async def trigger_medical_extraction(background_tasks: BackgroundTasks) -> Dict:
    """Async extraction cho Lĩnh vực: Y tế"""
    try:
        extract_main = import_extraction_module("extract_medical")
        background_tasks.add_task(extract_main)
        
        return {
            "status": "accepted",
            "message": "LLM extraction đã được khởi chạy ở background",
            "field": "Y tế",
            "type_newspaper": "medical",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-medical/sync", status_code=200)
def run_medical_extraction_sync() -> Dict:
    """Sync extraction cho Lĩnh vực: Y tế"""
    try:
        extract_main = import_extraction_module("extract_medical")
        result = extract_main()
        
        return {
            "status": "completed",
            "field": "Y tế",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# LĨNH VỰC 3: GIÁO DỤC (type_newspaper='education')
# ============================================

@router.post("/extract-education", status_code=202)
async def trigger_education_extraction(background_tasks: BackgroundTasks) -> Dict:
    """Async extraction cho Lĩnh vực: Giáo dục"""
    try:
        extract_main = import_extraction_module("extract_education")
        background_tasks.add_task(extract_main)
        
        return {
            "status": "accepted",
            "message": "LLM extraction đã được khởi chạy ở background",
            "field": "Giáo dục",
            "type_newspaper": "education",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-education/sync", status_code=200)
def run_education_extraction_sync() -> Dict:
    """Sync extraction cho Lĩnh vực: Giáo dục"""
    try:
        extract_main = import_extraction_module("extract_education")
        result = extract_main()
        
        return {
            "status": "completed",
            "field": "Giáo dục",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# LĨNH VỰC 4: AN NINH (type_newspaper='security')
# ============================================

@router.post("/extract-security", status_code=202)
async def trigger_security_extraction(background_tasks: BackgroundTasks) -> Dict:
    """Async extraction cho Lĩnh vực: An ninh - Trật tự"""
    try:
        extract_main = import_extraction_module("extract_security")
        background_tasks.add_task(extract_main)
        
        return {
            "status": "accepted",
            "message": "LLM extraction đã được khởi chạy ở background",
            "field": "An ninh - Trật tự",
            "type_newspaper": "security",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-security/sync", status_code=200)
def run_security_extraction_sync() -> Dict:
    """Sync extraction cho Lĩnh vực: An ninh - Trật tự"""
    try:
        extract_main = import_extraction_module("extract_security")
        result = extract_main()
        
        return {
            "status": "completed",
            "field": "An ninh - Trật tự",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# LĨNH VỰC 5: VĂN HÓA - XÃ HỘI (type_newspaper='society')
# ============================================

@router.post("/extract-society", status_code=202)
async def trigger_society_extraction(background_tasks: BackgroundTasks) -> Dict:
    """Async extraction cho Lĩnh vực: Văn hóa - Xã hội"""
    try:
        extract_main = import_extraction_module("extract_society")
        background_tasks.add_task(extract_main)
        
        return {
            "status": "accepted",
            "message": "LLM extraction đã được khởi chạy ở background",
            "field": "Văn hóa - Xã hội",
            "type_newspaper": "society",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-society/sync", status_code=200)
def run_society_extraction_sync() -> Dict:
    """Sync extraction cho Lĩnh vực: Văn hóa - Xã hội"""
    try:
        extract_main = import_extraction_module("extract_society")
        result = extract_main()
        
        return {
            "status": "completed",
            "field": "Văn hóa - Xã hội",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# LĨNH VỰC 6: GIAO THÔNG (type_newspaper='transportation')
# ============================================

@router.post("/extract-transportation", status_code=202)
async def trigger_transportation_extraction(background_tasks: BackgroundTasks) -> Dict:
    """Async extraction cho Lĩnh vực: Giao thông"""
    try:
        extract_main = import_extraction_module("extract_transportation")
        background_tasks.add_task(extract_main)
        
        return {
            "status": "accepted",
            "message": "LLM extraction đã được khởi chạy ở background",
            "field": "Giao thông",
            "type_newspaper": "transportation",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-transportation/sync", status_code=200)
def run_transportation_extraction_sync() -> Dict:
    """Sync extraction cho Lĩnh vực: Giao thông"""
    try:
        extract_main = import_extraction_module("extract_transportation")
        result = extract_main()
        
        return {
            "status": "completed",
            "field": "Giao thông",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# LĨNH VỰC 7: THỐNG KÊ KINH TẾ - CHÍNH TRỊ (2 bảng: economic_statistics, political_statistics)
# ============================================

@router.post("/extract-statistics", status_code=202)
async def trigger_statistics_extraction(background_tasks: BackgroundTasks) -> Dict:
    """Async extraction cho Thống kê Kinh tế & Chính trị"""
    try:
        extract_main = import_extraction_module("extract_statistics")
        background_tasks.add_task(extract_main)
        
        return {
            "status": "accepted",
            "message": "LLM extraction đã được khởi chạy ở background",
            "field": "Thống kê Kinh tế & Chính trị",
            "tables": ["economic_statistics", "political_statistics"],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-statistics/sync", status_code=200)
def run_statistics_extraction_sync() -> Dict:
    """Sync extraction cho Thống kê Kinh tế & Chính trị"""
    try:
        extract_main = import_extraction_module("extract_statistics")
        result = extract_main()
        
        return {
            "status": "completed",
            "field": "Thống kê Kinh tế & Chính trị",
            "tables": ["economic_statistics", "political_statistics"],
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# LĨNH VỰC 8: KINH TẾ SỐ (digital_economy_detail)
# ============================================

@router.post("/extract-digital-economy", status_code=202)
async def trigger_digital_economy_extraction(background_tasks: BackgroundTasks) -> Dict:
    """Async extraction cho Kinh tế số"""
    try:
        extract_main = import_extraction_module("extract_digital_economy")
        background_tasks.add_task(extract_main)
        
        return {
            "status": "accepted",
            "message": "LLM extraction đã được khởi chạy ở background",
            "field": "Kinh tế số",
            "table": "digital_economy_detail",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-digital-economy/sync", status_code=200)
def run_digital_economy_extraction_sync() -> Dict:
    """Sync extraction cho Kinh tế số"""
    try:
        extract_main = import_extraction_module("extract_digital_economy")
        result = extract_main()
        
        return {
            "status": "completed",
            "field": "Kinh tế số",
            "table": "digital_economy_detail",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# LĨNH VỰC 9: THU HÚT FDI (fdi_detail)
# ============================================

@router.post("/extract-fdi", status_code=202)
async def trigger_fdi_extraction(background_tasks: BackgroundTasks) -> Dict:
    """Async extraction cho Thu hút FDI"""
    try:
        extract_main = import_extraction_module("extract_fdi")
        background_tasks.add_task(extract_main)
        
        return {
            "status": "accepted",
            "message": "LLM extraction đã được khởi chạy ở background",
            "field": "Thu hút FDI",
            "table": "fdi_detail",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-fdi/sync", status_code=200)
def run_fdi_extraction_sync() -> Dict:
    """Sync extraction cho Thu hút FDI"""
    try:
        extract_main = import_extraction_module("extract_fdi")
        result = extract_main()
        
        return {
            "status": "completed",
            "field": "Thu hút FDI",
            "table": "fdi_detail",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# LĨNH VỰC 10: CHUYỂN ĐỔI SỐ (digital_transformation_detail)
# ============================================

@router.post("/extract-digital-transformation", status_code=202)
async def trigger_digital_transformation_extraction(background_tasks: BackgroundTasks) -> Dict:
    """Async extraction cho Chuyển đổi số"""
    try:
        extract_main = import_extraction_module("extract_digital_transformation")
        background_tasks.add_task(extract_main)
        
        return {
            "status": "accepted",
            "message": "LLM extraction đã được khởi chạy ở background",
            "field": "Chuyển đổi số",
            "table": "digital_transformation_detail",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-digital-transformation/sync", status_code=200)
def run_digital_transformation_extraction_sync() -> Dict:
    """Sync extraction cho Chuyển đổi số"""
    try:
        extract_main = import_extraction_module("extract_digital_transformation")
        result = extract_main()
        
        return {
            "status": "completed",
            "field": "Chuyển đổi số",
            "table": "digital_transformation_detail",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# LĨNH VỰC 11: CHỈ SỐ SẢN XUẤT CÔNG NGHIỆP (pii_detail)
# ============================================

@router.post("/extract-pii", status_code=202)
async def trigger_pii_extraction(background_tasks: BackgroundTasks) -> Dict:
    """Async extraction cho Chỉ số Sản xuất Công nghiệp (PII)"""
    try:
        extract_main = import_extraction_module("extract_pii")
        background_tasks.add_task(extract_main)
        
        return {
            "status": "accepted",
            "message": "LLM extraction đã được khởi chạy ở background",
            "field": "Chỉ số Sản xuất Công nghiệp (PII)",
            "table": "pii_detail",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-pii/sync", status_code=200)
def run_pii_extraction_sync() -> Dict:
    """Sync extraction cho Chỉ số Sản xuất Công nghiệp (PII)"""
    try:
        extract_main = import_extraction_module("extract_pii")
        result = extract_main()
        
        return {
            "status": "completed",
            "field": "Chỉ số Sản xuất Công nghiệp (PII)",
            "table": "pii_detail",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
