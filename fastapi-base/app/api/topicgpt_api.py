"""
TopicGPT API - Endpoints de tan dung kha nang TopicGPT
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.topic.topicgpt_enhancer import get_enhancer
from app.services.topic.topicgpt_service import get_topicgpt_service
from typing import Dict
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/topicgpt", tags=["TopicGPT"])


@router.get("/status")
def get_status() -> Dict:
    """
    Kiem tra trang thai TopicGPT service
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
    Enhance 12 custom topics voi TopicGPT
    
    Actions:
    - Generate descriptions cho topics thieu description
    - Su dung sample articles de tao descriptions chat luong cao
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
