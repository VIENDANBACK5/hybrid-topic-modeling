from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import Dict
import sys
import os
from datetime import datetime
import logging

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/extract-xay-dung-dang", status_code=202)
async def trigger_xay_dung_dang_extraction(background_tasks: BackgroundTasks) -> Dict:
    """
    Trigger LLM extraction cho Lĩnh vực 1: Xây dựng Đảng
    
    Trích xuất dữ liệu từ important_posts (type_newspaper='politics') vào 3 bảng:
    - cadre_statistics_detail
    - party_discipline_detail
    - cadre_quality_detail
    
    Returns:
        202 Accepted - Task được thêm vào background
    """
    try:
        # Import với absolute path từ project root
        import sys
        import os
        
        # Add fastapi-base directory to path
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        if base_dir not in sys.path:
            sys.path.insert(0, base_dir)
        
        from call_llm.extract_xay_dung_dang import main as extract_main
        
        # Add task to background
        background_tasks.add_task(extract_main)
        
        return {
            "status": "accepted",
            "message": "LLM extraction đã được khởi chạy ở background",
            "field": "Lĩnh vực 1 - Xây dựng Đảng",
            "tables": [
                "cadre_statistics_detail",
                "party_discipline_detail",
                "cadre_quality_detail"
            ],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error triggering extraction: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Không thể khởi chạy extraction: {str(e)}"
        )


@router.post("/extract-xay-dung-dang/sync", status_code=200)
def run_xay_dung_dang_extraction_sync() -> Dict:
    """
    Chạy LLM extraction ĐỒNG BỘ (synchronous) - Sẽ đợi kết quả
    
    CHÚ Ý: API này có thể mất vài phút để chạy xong
    Nên dùng endpoint /extract-xay-dung-dang (async) thay vì endpoint này
    
    Returns:
        200 OK với kết quả chi tiết
    """
    try:
        import sys
        import os
        
        # Add fastapi-base directory to path
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        if base_dir not in sys.path:
            sys.path.insert(0, base_dir)
        
        from call_llm.extract_xay_dung_dang import main as extract_main
        
        logger.info("Bắt đầu LLM extraction SYNC...")
        
        # Chạy trực tiếp (blocking)
        result = extract_main()
        
        return {
            "status": "completed",
            "message": "LLM extraction hoàn thành",
            "field": "Lĩnh vực 1 - Xây dựng Đảng",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in sync extraction: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi chạy extraction: {str(e)}"
        )
