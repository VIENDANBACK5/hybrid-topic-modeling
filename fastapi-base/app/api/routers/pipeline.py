from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import json
import logging

from app.services.crawler.pipeline import CrawlerPipeline
from app.services.topic.model import TopicModel

logger = logging.getLogger(__name__)
router = APIRouter()

# Lazy initialization - only load when first used
class LazyTopicModel:
    def __init__(self):
        self._instance = None
    
    def _ensure_loaded(self):
        if self._instance is None:
            self._instance = TopicModel()
        return self._instance
    
    def __getattr__(self, name):
        return getattr(self._ensure_loaded(), name)

crawler_pipeline = CrawlerPipeline()
topic_model = LazyTopicModel()


class SimpleAnalyzeRequest(BaseModel):
    """Đơn giản nhất - chỉ cần URL"""
    url: str
    max_pages: int = 50  # Số trang tối đa để crawl
    min_topic_size: int = 10  # Kích thước topic tối thiểu
    auto_topic_modeling: bool = True  # Tự động chạy topic modeling


class AnalyzeResponse(BaseModel):
    status: str
    url: str
    documents_crawled: int
    topics_found: int
    saved_file: Optional[str] = None
    model_path: Optional[str] = None
    summary: Dict


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_url(request: SimpleAnalyzeRequest):
    """
    API đơn giản nhất - chỉ cần URL, tự động:
    1. Crawl website
    2. Extract và clean text
    3. Topic modeling
    4. Trả về kết quả
    
    Usage:
    ```json
    {
        "url": "https://example.com",
        "max_pages": 50
    }
    ```
    """
    try:
        logger.info(f"🚀 Starting auto pipeline for: {request.url}")
        
        # Step 1: Crawl
        logger.info("📥 Step 1: Crawling...")
        crawl_result = await crawler_pipeline.run(
            source_type="web",
            source=request.url,
            clean=True,
            dedupe=True,
            follow_links=True,
            max_pages=request.max_pages
        )
        
        documents = crawl_result.get('documents', [])
        if not documents:
            return {
                "status": "no_data",
                "url": request.url,
                "documents_crawled": 0,
                "topics_found": 0,
                "saved_file": None,
                "model_path": None,
                "summary": {
                    "message": "Không tìm thấy dữ liệu để crawl"
                }
            }
        
        logger.info(f"✅ Crawled {len(documents)} documents")
        
        # Step 2: Extract text for topic modeling
        logger.info("📝 Step 2: Extracting text...")
        texts = []
        for doc in documents:
            # Extract text from various fields
            content = doc.get('content', '') or doc.get('cleaned_content', '') or doc.get('raw_content', '')
            
            # Get title from different possible locations
            metadata = doc.get('metadata', {})
            title = metadata.get('title', '') if isinstance(metadata, dict) else ''
            if not title:
                title = doc.get('title', '')
            
            # Combine title and content, handle None values
            if not isinstance(content, str):
                content = str(content) if content else ''
            if not isinstance(title, str):
                title = str(title) if title else ''
            
            text = f"{title} {content}".strip()
            if text and len(text) > 50:  # Minimum length filter
                texts.append(text[:3000])  # Limit length
        
        if len(texts) < 2:
            return {
                "status": "insufficient_data",
                "url": request.url,
                "documents_crawled": len(documents),
                "topics_found": 0,
                "saved_file": None,
                "model_path": None,
                "summary": {
                    "message": f"Chỉ có {len(texts)} documents, cần ít nhất 2 để phân tích topics"
                }
            }
        
        # Step 3: Save crawled data
        saved_path = None
        try:
            base_dir = Path("data/processed")
            base_dir.mkdir(parents=True, exist_ok=True)
            
            host = urlparse(request.url).netloc or "unknown"
            safe_host = host.replace(":", "_").replace("/", "_")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{safe_host}_{ts}.json"
            
            out_path = base_dir / filename
            payload = {
                "meta": {
                    "url": request.url,
                    "created_at": datetime.now().isoformat(),
                    "documents_count": len(documents),
                    "max_pages": request.max_pages
                },
                "documents": documents
            }
            with out_path.open("w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            saved_path = str(out_path)
            logger.info(f"💾 Saved to {saved_path}")
        except Exception as e:
            logger.error(f"Error saving file: {e}")
        
        # Step 4: Topic Modeling (if enabled)
        topics_found = 0
        model_path = None
        
        if request.auto_topic_modeling:
            logger.info("🧠 Step 3: Running topic modeling...")
            try:
                topic_model.min_topic_size = request.min_topic_size
                topics, probs = topic_model.fit(texts)
                
                topic_info = topic_model.get_topic_info()
                topics_found = len(topic_info.get('topics', []))
                
                # Save model
                model_name = f"auto_{safe_host}_{ts}"
                model_path = topic_model.save(model_name)
                logger.info(f"✅ Found {topics_found} topics, model saved to {model_path}")
            except Exception as e:
                logger.error(f"Error in topic modeling: {e}")
                topics_found = 0
        
        # Summary
        summary = {
            "crawl_status": crawl_result.get('status', 'unknown'),
            "documents_processed": len(documents),
            "texts_extracted": len(texts),
            "topics_analyzed": topics_found if request.auto_topic_modeling else 0,
            "auto_topic_modeling": request.auto_topic_modeling
        }
        
        return {
            "status": "success",
            "url": request.url,
            "documents_crawled": len(documents),
            "topics_found": topics_found,
            "saved_file": saved_path,
            "model_path": model_path,
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@router.get("/status")
async def get_pipeline_status():
    """Check pipeline status"""
    return {
        "status": "ready",
        "features": {
            "auto_crawl": True,
            "auto_topic_modeling": True,
            "auto_save": True
        },
        "usage": {
            "endpoint": "POST /api/pipeline/analyze",
            "required": ["url"],
            "optional": ["max_pages", "min_topic_size", "auto_topic_modeling"]
        }
    }

