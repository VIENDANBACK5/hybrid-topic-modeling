"""
Smart Crawl API Endpoints - Add to crawl.py
Các endpoint mới với LLM integration
"""

# ==================== SMART CRAWL ENDPOINTS ====================

class SmartCrawlRequest(BaseModel):
    """
    Smart Crawl Request với LLM options
    """
    url: str
    mode: str = "smart"  # "smart", "smart-full"
    
    # LLM Options
    enable_llm: bool = True
    llm_features: Optional[List[str]] = None  # ['category', 'summary', 'keywords']
    semantic_dedupe: Optional[bool] = None  # Auto-decide if None
    cost_limit: Optional[float] = None  # Daily budget in USD
    
    # Traditional crawl params
    follow_links: bool = True
    max_pages: int = 100
    custom_params: Optional[Dict] = None


class SmartCrawlResponse(BaseModel):
    status: str
    processed: int
    saved_to_db: int = 0
    db_duplicates: int = 0
    documents: List[Dict] = []
    
    # Pipeline info
    pipeline_info: Dict
    
    # Cost tracking
    cost_info: Optional[Dict] = None


@router.post("/smart", response_model=SmartCrawlResponse)
async def smart_crawl(request: SmartCrawlRequest, db: Session = Depends(get_db)):
    """
    🤖 SMART CRAWL API - Với LLM Enhancement
    
    Features:
    - Tự động categorize nội dung
    - Generate summaries cho bài dài
    - Extract keywords và tags
    - Semantic deduplication (detect paraphrases)
    - Cost-aware operations
    
    Examples:
        # Basic smart crawl
        {"url": "https://vnexpress.net", "mode": "smart"}
        
        # With specific features
        {
            "url": "https://dantri.com.vn",
            "enable_llm": true,
            "llm_features": ["category", "summary"],
            "cost_limit": 5.0
        }
        
        # Disable LLM (same as traditional)
        {"url": "https://example.com", "enable_llm": false}
    """
    try:
        logger.info(f"🤖 Smart crawl: {request.url}")
        
        # Set budget if specified
        if request.cost_limit:
            smart_crawler_pipeline.set_daily_budget(request.cost_limit)
        
        # Configure features
        if request.llm_features:
            smart_crawler_pipeline.configure_llm_features(request.llm_features)
        
        # Build crawl params
        crawl_params = dict(request.custom_params) if request.custom_params else {}
        crawl_params.update({
            "follow_links": request.follow_links,
            "max_pages": request.max_pages
        })
        
        # Run smart pipeline
        result = await smart_crawler_pipeline.run(
            source_type="web",
            source=request.url,
            clean=True,
            dedupe=True,
            enrich=request.enable_llm,
            semantic_dedupe=request.semantic_dedupe,
            **crawl_params
        )
        
        # Save to database (same as traditional crawl)
        saved_to_db = 0
        db_duplicates = 0
        documents = result.get("documents", [])
        
        try:
            from app.models.model_source import Source
            from datetime import datetime
            from urllib.parse import urlparse
            
            domain = urlparse(request.url).netloc if request.url else "unknown"
            
            # Get or create source
            source_record = db.query(Source).filter(Source.url == request.url).first()
            if not source_record:
                source_record = Source(
                    name=domain,
                    url=request.url,
                    type="news",
                    domain=domain,
                    is_active=True
                )
                db.add(source_record)
                db.flush()
            
            # Update source
            source_record.last_crawled_at = datetime.utcnow()
            source_record.last_article_count = len(documents)
            
            # Save articles
            for doc in documents:
                url = doc.get("source_id") or doc.get("url") or doc.get("source")
                if not url or url in ["web", "rss", "file", "api"]:
                    continue
                
                # Check duplicate
                existing = db.query(Article).filter(Article.url == url).first()
                if existing:
                    db_duplicates += 1
                    continue
                
                meta = doc.get("metadata", {})
                
                # Create article with LLM metadata
                article = Article(
                    url=url,
                    source_type="web",
                    source=request.url,
                    domain=domain,
                    title=meta.get("title"),
                    content=doc.get("cleaned_content") or doc.get("content"),
                    summary=doc.get("llm_summary") or meta.get("description"),
                    category=doc.get("llm_category") or meta.get("category"),
                    author=meta.get("author"),
                    published_date=meta.get("published_time"),
                    tags=doc.get("llm_tags") or meta.get("tags"),
                    images=meta.get("images"),
                    videos=meta.get("videos"),
                    is_cleaned=True,
                    is_deduped=True,
                    word_count=len(doc.get("content", "").split()) if doc.get("content") else 0,
                    raw_metadata={
                        **meta,
                        "llm_enriched": doc.get("llm_enriched", False),
                        "llm_category_confidence": doc.get("llm_category_confidence"),
                        "llm_keywords": doc.get("llm_keywords")
                    }
                )
                db.add(article)
                saved_to_db += 1
            
            # Update source total
            source_record.total_articles = db.query(Article).filter(Article.source == request.url).count()
            
            db.commit()
            logger.info(f"✅ Saved {saved_to_db} articles, {db_duplicates} duplicates")
        
        except Exception as e:
            db.rollback()
            logger.error(f"DB error: {e}")
        
        # Return response with pipeline info and cost tracking
        return {
            "status": result.get("status"),
            "processed": result.get("processed"),
            "saved_to_db": saved_to_db,
            "db_duplicates": db_duplicates,
            "documents": documents if request.mode == "smart-full" else [],
            "pipeline_info": result.get("pipeline_info", {}),
            "cost_info": result.get("pipeline_info", {}).get("cost_tracking")
        }
    
    except Exception as e:
        logger.error(f"Smart crawl error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== COST MANAGEMENT ENDPOINTS ====================

@router.get("/cost/report")
async def get_cost_report():
    """
    📊 Get cost usage report
    
    Returns:
        Daily usage, remaining budget, operations breakdown
    """
    try:
        from app.services.crawler.cost_optimizer import get_cost_optimizer
        cost_optimizer = get_cost_optimizer()
        report = cost_optimizer.get_usage_report()
        return report
    except Exception as e:
        logger.error(f"Error getting cost report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cost/set-budget")
async def set_daily_budget(budget: float):
    """
    💰 Set daily budget for LLM operations
    
    Args:
        budget: Daily budget in USD
    
    Example:
        POST /api/crawl/cost/set-budget?budget=10.0
    """
    try:
        smart_crawler_pipeline.set_daily_budget(budget)
        return {
            "status": "success",
            "daily_budget": budget,
            "message": f"Daily budget set to ${budget}"
        }
    except Exception as e:
        logger.error(f"Error setting budget: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cost/estimate")
async def estimate_cost(operation: str, count: int = 1):
    """
    🔮 Estimate cost for operation
    
    Args:
        operation: Operation type (categorize, summarize, extract_keywords, etc.)
        count: Number of operations
    
    Example:
        POST /api/crawl/cost/estimate?operation=categorize&count=100
    """
    try:
        from app.services.crawler.cost_optimizer import get_cost_optimizer
        cost_optimizer = get_cost_optimizer()
        estimate = cost_optimizer.estimate_cost(operation, count)
        return estimate
    except Exception as e:
        logger.error(f"Error estimating cost: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== PIPELINE MANAGEMENT ENDPOINTS ====================

@router.get("/pipeline/stats")
async def get_pipeline_stats():
    """
    📈 Get pipeline statistics
    
    Returns:
        Pipeline configuration, LLM status, cost tracking
    """
    try:
        stats = smart_crawler_pipeline.get_pipeline_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting pipeline stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pipeline/configure")
async def configure_pipeline(
    enable_llm: bool = True,
    llm_features: List[str] = None,
    cost_aware: bool = True
):
    """
    ⚙️ Configure pipeline settings
    
    Args:
        enable_llm: Enable/disable LLM features
        llm_features: List of features to enable
        cost_aware: Enable cost optimization
    
    Example:
        POST /api/crawl/pipeline/configure
        {
            "enable_llm": true,
            "llm_features": ["category", "summary"],
            "cost_aware": true
        }
    """
    try:
        global smart_crawler_pipeline
        
        # Recreate pipeline with new settings
        smart_crawler_pipeline = get_smart_crawler_pipeline(
            enable_llm=enable_llm,
            llm_features=llm_features or [],
            cost_aware=cost_aware
        )
        
        return {
            "status": "success",
            "configuration": {
                "enable_llm": enable_llm,
                "llm_features": llm_features or [],
                "cost_aware": cost_aware
            }
        }
    except Exception as e:
        logger.error(f"Error configuring pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== DEDUPLICATION ENDPOINTS ====================

@router.post("/dedupe/find")
async def find_duplicates(
    source: Optional[str] = None,
    semantic: bool = False,
    db: Session = Depends(get_db)
):
    """
    🔍 Find duplicate documents
    
    Args:
        source: Source URL (optional, checks all if not provided)
        semantic: Use semantic deduplication (LLM-powered)
    
    Returns:
        Duplicate groups and statistics
    """
    try:
        from app.services.etl.hybrid_dedupe import get_hybrid_deduplicator
        
        # Get documents from DB
        query = db.query(Article)
        if source:
            query = query.filter(Article.source == source)
        
        articles = query.limit(1000).all()  # Limit for performance
        
        # Convert to document format
        documents = [
            {
                "content": article.content,
                "metadata": {"url": article.url, "title": article.title}
            }
            for article in articles
        ]
        
        # Find duplicates
        deduplicator = get_hybrid_deduplicator()
        duplicates_info = deduplicator.find_duplicates(documents, return_groups=True)
        
        return duplicates_info
    
    except Exception as e:
        logger.error(f"Error finding duplicates: {e}")
        raise HTTPException(status_code=500, detail=str(e))
