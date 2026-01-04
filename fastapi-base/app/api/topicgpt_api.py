"""
TopicGPT API - Endpoints để tận dụng khả năng TopicGPT
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.topic.topicgpt_enhancer import get_enhancer
from app.services.topic.topicgpt_service import get_topicgpt_service
from pydantic import BaseModel
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/topicgpt", tags=["🎨 TopicGPT"])


@router.get("/status")
def get_status() -> Dict:
    """
    📊 Kiểm tra trạng thái TopicGPT service
    
    **Example:**
    ```bash
    curl http://localhost:7777/api/topicgpt/status
    ```
    """
    service = get_topicgpt_service()
    stats = service.get_stats()
    
    return {
        "status": "available" if stats["available"] else "unavailable",
        "details": stats,
        "message": "Ready to use" if stats["available"] else "OPENAI_API_KEY not configured"
    }


@router.post("/enhance/custom-topics")
def enhance_custom_topics(db: Session = Depends(get_db)) -> Dict:
    """
    🎨 Enhance 12 custom topics với TopicGPT
    
    **Actions:**
    - Generate descriptions cho topics thiếu description
    - Sử dụng sample articles để tạo descriptions chất lượng cao
    
    **Example:**
    ```bash
    curl -X POST http://localhost:7777/api/topicgpt/enhance/custom-topics
    ```
    """
    try:
        enhancer = get_enhancer(db)
        result = enhancer.enhance_custom_topics()
        
        if result["status"] == "success":
            return {
                "status": "success",
                "message": f"Enhanced {result['enhanced']}/{result['total']} topics",
                "result": result
            }
        else:
            return result
            
    except Exception as e:
        logger.error(f"Failed to enhance custom topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refine/discovered-topics")
def refine_discovered_topics(
    session_id: Optional[str] = None,
    merge_similar: bool = True,
    db: Session = Depends(get_db)
) -> Dict:
    """
    🔧 Refine discovered topics với TopicGPT
    
    **Actions:**
    - Phân tích và suggest merge các topics tương tự
    - Cải thiện topic labels
    - Categorize topics
    
    **Args:**
    - `session_id`: Training session ID (None = latest session)
    - `merge_similar`: Enable merge suggestions (default: True)
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:7777/api/topicgpt/refine/discovered-topics?merge_similar=true"
    ```
    """
    try:
        enhancer = get_enhancer(db)
        result = enhancer.refine_discovered_topics(
            session_id=session_id,
            merge_similar=merge_similar
        )
        
        if result["status"] == "success":
            return {
                "status": "success",
                "message": f"Analyzed {result['analyzed']} topics",
                "result": result
            }
        else:
            return result
            
    except Exception as e:
        logger.error(f"Failed to refine topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/categorize-articles")
def categorize_articles(
    limit: int = 100,
    uncategorized_only: bool = True,
    db: Session = Depends(get_db)
) -> Dict:
    """
    📑 Categorize articles using TopicGPT
    
    **Actions:**
    - Phân loại articles vào các danh mục chuẩn
    - Sử dụng LLM để hiểu ngữ cảnh và nội dung
    
    **Args:**
    - `limit`: Số articles tối đa (default: 100)
    - `uncategorized_only`: Chỉ categorize articles chưa có category (default: True)
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:7777/api/topicgpt/categorize-articles?limit=50"
    ```
    """
    try:
        enhancer = get_enhancer(db)
        result = enhancer.categorize_articles(
            limit=limit,
            uncategorized_only=uncategorized_only
        )
        
        if result["status"] == "success":
            return {
                "status": "success",
                "message": f"Categorized {result['categorized']}/{result['total']} articles",
                "result": result
            }
        else:
            return result
            
    except Exception as e:
        logger.error(f"Failed to categorize articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-summaries")
def generate_summaries(
    limit: int = 50,
    unsummarized_only: bool = True,
    db: Session = Depends(get_db)
) -> Dict:
    """
    📝 Generate summaries for articles
    
    **Actions:**
    - Tạo tóm tắt ngắn gọn cho articles
    - Sử dụng LLM để tạo summaries chất lượng cao
    
    **Args:**
    - `limit`: Số articles tối đa (default: 50)
    - `unsummarized_only`: Chỉ summarize articles chưa có summary (default: True)
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:7777/api/topicgpt/generate-summaries?limit=30"
    ```
    
    **Note:** API này tốn token, sử dụng cẩn thận với limit lớn.
    """
    try:
        enhancer = get_enhancer(db)
        result = enhancer.generate_summaries(
            limit=limit,
            unsummarized_only=unsummarized_only
        )
        
        if result["status"] == "success":
            return {
                "status": "success",
                "message": f"Generated summaries for {result['summarized']}/{result['total']} articles",
                "result": result
            }
        else:
            return result
            
    except Exception as e:
        logger.error(f"Failed to generate summaries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ContentAnalysisRequest(BaseModel):
    """Request for content analysis"""
    text: str
    max_keywords: int = 10


@router.post("/analyze-content")
def analyze_content(
    request: ContentAnalysisRequest
) -> Dict:
    """
    🔍 Analyze content with TopicGPT
    
    **Actions:**
    - Extract keywords and tags
    - Categorize content
    - Generate summary
    
    **Example:**
    ```bash
    curl -X POST http://localhost:7777/api/topicgpt/analyze-content \\
      -H "Content-Type: application/json" \\
      -d '{
        "text": "Hôm nay, UBND tỉnh Hưng Yên tổ chức họp báo...",
        "max_keywords": 10
      }'
    ```
    """
    try:
        service = get_topicgpt_service()
        
        if not service.is_available():
            raise HTTPException(
                status_code=503,
                detail="TopicGPT service not available (OPENAI_API_KEY not configured)"
            )
        
        # Extract keywords
        keywords_result = service.extract_keywords_and_tags(
            text=request.text,
            max_keywords=request.max_keywords
        )
        
        # Categorize
        category_result = service.categorize_content(text=request.text)
        
        # Generate summary
        summary = service.summarize_content(text=request.text, max_length=100)
        
        return {
            "status": "success",
            "analysis": {
                "keywords": keywords_result.get("keywords", []),
                "tags": keywords_result.get("tags", []),
                "category": category_result.get("category", "Unknown"),
                "category_confidence": category_result.get("confidence", 0.0),
                "summary": summary
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to analyze content: {e}")
        raise HTTPException(status_code=500, detail=str(e))
