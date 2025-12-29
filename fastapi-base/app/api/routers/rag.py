from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.model_article import Article
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class SearchRequest(BaseModel):
    """Đơn giản - chỉ cần query"""
    query: str
    limit: int = 5
    source_filter: Optional[str] = None  # Filter theo nguồn cụ thể


class QARequest(BaseModel):
    """Hỏi đáp với LLM"""
    question: str
    top_k: int = 5
    use_llm: bool = True
    source_filter: Optional[str] = None


@router.post("/search")
async def semantic_search(request: SearchRequest, db: Session = Depends(get_db)):
    """
    Tìm kiếm semantic trên tài liệu (OPTIMIZED)
    
    Không cần LLM - chỉ tìm articles giống nhất với query
    
    Example:
        {"query": "kinh tế Hưng Yên", "limit": 5}
    """
    try:
        from app.core.models import rag_service
        
        if not rag_service:
            raise HTTPException(status_code=503, detail="RAG service not available")
        
        # Get articles from DB with keyword filtering (OPTIMIZATION)
        query_lower = request.query.lower()
        keywords = query_lower.split()[:3]  # Top 3 keywords
        
        # Build SQL filter
        articles_query = db.query(Article)
        
        if request.source_filter:
            articles_query = articles_query.filter(Article.url.contains(request.source_filter))
        
        # Keyword filter (speeds up from 4021 → ~200 articles)
        if keywords:
            from sqlalchemy import or_
            filters = []
            for kw in keywords:
                filters.append(Article.content.ilike(f"%{kw}%"))
                filters.append(Article.title.ilike(f"%{kw}%"))
            articles_query = articles_query.filter(or_(*filters))
        
        # Limit to 200 articles max
        articles = articles_query.limit(200).all()
        
        if not articles:
            return {
                "results": [],
                "total": 0,
                "query": request.query
            }
        
        # Convert to dicts
        articles_data = [
            {
                "id": a.id,
                "title": a.title,
                "content": a.content or a.raw_content,
                "url": a.url,
                "created_at": str(a.created_at) if a.created_at else None
            }
            for a in articles
        ]
        
        # Search with RAG
        results = rag_service.search_similar_articles(
            query=request.query,
            articles=articles_data,
            top_k=request.limit
        )
        
        return {
            "results": results,
            "total": len(results),
            "query": request.query,
            "searched_articles": len(articles_data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RAG search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/qa")
async def question_answering(request: QARequest, db: Session = Depends(get_db)):
    """
    Hỏi đáp với RAG + LLM (OPTIMIZED)
    
    Flow:
    1. Tìm articles liên quan (semantic search)
    2. Dùng GPT để generate answer từ context
    3. Trả về answer + sources
    
    Example:
        {"question": "Tình hình kinh tế Hưng Yên như thế nào?", "use_llm": true}
        {"question": "Các dự án đầu tư mới", "use_llm": false}  // Chỉ search
    """
    try:
        from app.core.models import rag_service
        
        if not rag_service:
            raise HTTPException(status_code=503, detail="RAG service not available")
        
        # Get articles from DB with keyword filtering
        query_lower = request.question.lower()
        keywords = query_lower.split()[:3]
        
        articles_query = db.query(Article)
        
        if request.source_filter:
            articles_query = articles_query.filter(Article.url.contains(request.source_filter))
        
        if keywords:
            from sqlalchemy import or_
            filters = []
            for kw in keywords:
                filters.append(Article.content.ilike(f"%{kw}%"))
                filters.append(Article.title.ilike(f"%{kw}%"))
            articles_query = articles_query.filter(or_(*filters))
        
        articles = articles_query.limit(200).all()
        
        if not articles:
            return {
                "answer": "Không tìm thấy tài liệu liên quan.",
                "sources": [],
                "question": request.question
            }
        
        # Convert to dicts
        articles_data = [
            {
                "id": a.id,
                "title": a.title,
                "content": a.content or a.raw_content,
                "url": a.url,
                "created_at": str(a.created_at) if a.created_at else None
            }
            for a in articles
        ]
        
        # Q&A with RAG
        result = rag_service.qa(
            question=request.question,
            articles=articles_data,
            top_k=request.top_k,
            use_llm=request.use_llm
        )
        
        return {
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
            "question": request.question,
            "searched_articles": len(articles_data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RAG Q&A error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_rag_status():
    """Check RAG service status"""
    try:
        from app.core.models import rag_service
        
        if not rag_service:
            return {
                "status": "unavailable",
                "message": "RAG service not initialized"
            }
        
        return {
            "status": "ready",
            "embedding_model": "keepitreal/vietnamese-sbert" if rag_service.embedding_model else None,
            "cache_size": len(rag_service.embedding_cache) if hasattr(rag_service, 'embedding_cache') else 0
        }
    except Exception as e:
        logger.error(f"RAG status error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }
