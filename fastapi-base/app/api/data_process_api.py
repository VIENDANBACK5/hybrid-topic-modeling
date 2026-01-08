"""
Data Process API - Endpoints de xu ly raw data theo tung loai

Endpoints:
- POST /process/facebook - Xu ly raw Facebook data
- POST /process/tiktok - Xu ly raw TikTok data
- POST /process/threads - Xu ly raw Threads data
- POST /process/newspaper - Xu ly raw Newspaper data
- POST /process/load-to-db - Load processed data vao DB
- GET /process/status - Xem trang thai xu ly
- GET /process/files/{data_type} - List processed files
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.etl.processors import get_processor, get_supported_types
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
import logging
import json
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/process", tags=["Data Process"])

# Directory structure
RAW_DATA_DIR = Path("data/raw")
PROCESSED_DATA_DIR = Path("data/processed")


class ProcessConfig(BaseModel):
    """Config cho xu ly"""
    raw_file: Optional[str] = Field(None, description="Path to raw file (if not provided, use latest)")
    skip_duplicates: bool = Field(default=True, description="Skip duplicate URLs within file")


class ProcessResult(BaseModel):
    """Ket qua xu ly"""
    status: str
    data_type: str
    raw_file: str
    processed_file: str
    total_records: int
    processed_records: int
    failed_records: int
    message: str


class LoadConfig(BaseModel):
    """Config cho load to DB"""
    processed_file: str
    update_existing: bool = False
    analyze_sentiment: bool = True


# ============================================
# FACEBOOK
# ============================================

@router.post("/facebook", response_model=ProcessResult)
def process_facebook(
    config: ProcessConfig = ProcessConfig(),
    db: Session = Depends(get_db)
):
    """
    Xu ly raw Facebook data
    
    - Doc file tu data/raw/facebook/
    - Chuan hoa cac truong
    - Clean text
    - Luu vao data/processed/facebook/
    """
    return _process_data_type("facebook", config)


# ============================================
# TIKTOK
# ============================================

@router.post("/tiktok", response_model=ProcessResult)
def process_tiktok(
    config: ProcessConfig = ProcessConfig(),
    db: Session = Depends(get_db)
):
    """
    Xu ly raw TikTok data
    
    - Doc file tu data/raw/tiktok/
    - Chuan hoa cac truong (views, hashtags, ...)
    - Clean text
    - Luu vao data/processed/tiktok/
    """
    return _process_data_type("tiktok", config)


# ============================================
# THREADS
# ============================================

@router.post("/threads", response_model=ProcessResult)
def process_threads(
    config: ProcessConfig = ProcessConfig(),
    db: Session = Depends(get_db)
):
    """
    Xu ly raw Threads data
    
    - Doc file tu data/raw/threads/
    - Chuan hoa cac truong (likes, replies, ...)
    - Clean text
    - Luu vao data/processed/threads/
    """
    return _process_data_type("threads", config)


# ============================================
# NEWSPAPER
# ============================================

@router.post("/newspaper", response_model=ProcessResult)
def process_newspaper(
    config: ProcessConfig = ProcessConfig(),
    db: Session = Depends(get_db)
):
    """
    Xu ly raw Newspaper data
    
    - Doc file tu data/raw/newspaper/
    - Chuan hoa cac truong
    - Clean text
    - Luu vao data/processed/newspaper/
    """
    return _process_data_type("newspaper", config)


# ============================================
# HELPER FUNCTIONS
# ============================================

def _process_data_type(data_type: str, config: ProcessConfig) -> ProcessResult:
    """Core function de xu ly data theo type"""
    logger.info(f"Starting process for {data_type}...")
    
    raw_dir = RAW_DATA_DIR / data_type
    processed_dir = PROCESSED_DATA_DIR / data_type
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    # Find raw file
    if config.raw_file:
        raw_file = Path(config.raw_file)
    else:
        # Get latest raw file
        raw_files = list(raw_dir.glob("*.json"))
        if not raw_files:
            raise HTTPException(404, f"No raw files found for {data_type}")
        raw_file = max(raw_files, key=lambda f: f.stat().st_mtime)
    
    if not raw_file.exists():
        raise HTTPException(404, f"Raw file not found: {raw_file}")
    
    logger.info(f"Processing file: {raw_file}")
    
    # Load raw data
    try:
        with open(raw_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except Exception as e:
        raise HTTPException(400, f"Failed to load raw file: {e}")
    
    # Extract records
    if isinstance(raw_data, dict):
        records = raw_data.get('records', raw_data.get('data', []))
    elif isinstance(raw_data, list):
        records = raw_data
    else:
        raise HTTPException(400, "Invalid raw data format")
    
    if not records:
        return ProcessResult(
            status="empty",
            data_type=data_type,
            raw_file=str(raw_file),
            processed_file="",
            total_records=0,
            processed_records=0,
            failed_records=0,
            message="No records to process"
        )
    
    # Get processor and process
    processor = get_processor(data_type)
    processed_records, stats = processor.process_batch(records)
    
    # Save processed data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    processed_filename = f"{data_type}_processed_{timestamp}.json"
    processed_file = processed_dir / processed_filename
    
    with open(processed_file, 'w', encoding='utf-8') as f:
        json.dump({
            "data_type": data_type,
            "processed_at": datetime.now().isoformat(),
            "source_file": str(raw_file),
            "statistics": stats,
            "records": processed_records
        }, f, ensure_ascii=False, indent=2, default=str)
    
    logger.info(f"Saved {len(processed_records)} processed records to {processed_file}")
    
    return ProcessResult(
        status="success",
        data_type=data_type,
        raw_file=str(raw_file),
        processed_file=str(processed_file),
        total_records=stats['total'],
        processed_records=stats['success'],
        failed_records=stats['failed'],
        message=f"Processed {stats['success']}/{stats['total']} {data_type} records"
    )


# ============================================
# LOAD TO DATABASE
# ============================================

@router.post("/load-to-db")
def load_to_database(
    config: LoadConfig,
    db: Session = Depends(get_db)
):
    """
    Load processed data vao database
    
    - Doc file tu data/processed/{data_type}/
    - Insert/Update vao bang articles
    - Tu dong analyze sentiment neu bat
    
    Example:
    - Full path: "data/processed/facebook/facebook_processed_xxx.json"
    - Filename only: "facebook_processed_xxx.json" (auto detect in data/processed/)
    """
    from app.models.model_article import Article
    from app.services.sentiment import get_sentiment_analyzer
    from app.models import SentimentAnalysis
    
    # Handle both full path and filename only
    processed_file = Path(config.processed_file)
    
    if not processed_file.exists():
        # Try to find in processed directory
        if not processed_file.is_absolute():
            # Extract data_type from filename (e.g., "facebook_processed_xxx.json" -> "facebook")
            filename = processed_file.name
            data_type = None
            for dt in ["facebook", "tiktok", "threads", "newspaper"]:
                if filename.startswith(dt):
                    data_type = dt
                    break
            
            if data_type:
                processed_file = PROCESSED_DATA_DIR / data_type / filename
            else:
                # Search in all processed folders
                for dt in ["facebook", "tiktok", "threads", "newspaper"]:
                    candidate = PROCESSED_DATA_DIR / dt / filename
                    if candidate.exists():
                        processed_file = candidate
                        break
        
        if not processed_file.exists():
            raise HTTPException(404, f"Processed file not found: {config.processed_file}. Use full path like 'data/processed/facebook/facebook_processed_xxx.json' or just filename.")
    
    logger.info(f"Loading to DB: {processed_file}")
    
    # Load processed data
    with open(processed_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    records = data.get('records', [])
    data_type = data.get('data_type', 'unknown')
    
    if not records:
        return {"status": "empty", "message": "No records to load"}
    
    # Get existing URLs
    existing_urls = {a.url for a in db.query(Article.url).all()}
    
    # Initialize sentiment analyzer if needed
    analyzer = None
    if config.analyze_sentiment:
        try:
            analyzer = get_sentiment_analyzer()
        except Exception as e:
            logger.warning(f"Sentiment analyzer not available: {e}")
    
    stats = {
        'inserted': 0,
        'updated': 0,
        'skipped': 0,
        'sentiment_analyzed': 0,
        'errors': []
    }
    
    for record in records:
        try:
            url = record.get('url')
            if not url:
                stats['skipped'] += 1
                continue
            
            # Check existing
            if url in existing_urls:
                if not config.update_existing:
                    stats['skipped'] += 1
                    continue
                # Update existing
                article = db.query(Article).filter(Article.url == url).first()
                if article:
                    for key, value in record.items():
                        if hasattr(article, key) and value is not None:
                            setattr(article, key, value)
                    stats['updated'] += 1
            else:
                # Create new article
                article = Article(
                    url=record.get('url'),
                    source_type=record.get('source_type', 'api'),
                    source=record.get('source', record.get('url')),
                    domain=record.get('domain'),
                    title=record.get('title'),
                    content=record.get('content'),
                    summary=record.get('summary'),
                    author=record.get('account_name'),
                    published_date=record.get('published_date'),
                    category=record.get('category'),
                    tags=record.get('tags'),
                    images=record.get('images'),
                    videos=record.get('videos'),
                    likes_count=record.get('likes_count', 0),
                    shares_count=record.get('shares_count', 0),
                    comments_count=record.get('comments_count', 0),
                    views_count=record.get('views_count', 0),
                    reactions=record.get('reactions'),
                    social_platform=record.get('social_platform'),
                    account_id=record.get('account_id'),
                    account_name=record.get('account_name'),
                    account_url=record.get('account_url'),
                    post_id=record.get('post_id'),
                    post_type=record.get('post_type'),
                    is_cleaned=True,
                    word_count=record.get('word_count'),
                    raw_metadata=record.get('raw_metadata'),
                )
                db.add(article)
                db.flush()
                existing_urls.add(url)
                stats['inserted'] += 1
                
                # Analyze sentiment
                if analyzer and record.get('content'):
                    try:
                        result = analyzer.analyze(record['content'])
                        sentiment = SentimentAnalysis(
                            article_id=article.id,
                            source_url=url,
                            source_domain=record.get('domain'),
                            title=record.get('title'),
                            emotion=result.emotion,
                            emotion_vi=result.emotion_vi,
                            emotion_icon=result.icon,
                            sentiment_group=result.group,
                            sentiment_group_vi=result.group_vi,
                            confidence=result.confidence,
                            emotion_scores=result.all_scores,
                            category=record.get('category'),
                            published_date=record.get('published_datetime'),
                            content_snippet=record['content'][:200]
                        )
                        db.add(sentiment)
                        stats['sentiment_analyzed'] += 1
                    except Exception as e:
                        logger.warning(f"Sentiment analysis failed: {e}")
        
        except Exception as e:
            logger.error(f"Error loading record: {e}")
            stats['errors'].append(str(e)[:100])
            stats['skipped'] += 1
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to commit: {e}")
    
    return {
        "status": "success",
        "data_type": data_type,
        "processed_file": str(processed_file),
        "statistics": stats,
        "message": f"Inserted {stats['inserted']}, updated {stats['updated']}, skipped {stats['skipped']}"
    }


# ============================================
# STATUS & FILES
# ============================================

@router.get("/status")
def get_process_status():
    """
    Xem tong quan files da xu ly theo tung loai
    """
    status = {}
    
    for data_type in get_supported_types():
        processed_dir = PROCESSED_DATA_DIR / data_type
        if processed_dir.exists():
            files = list(processed_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in files)
            
            latest = None
            if files:
                latest_file = max(files, key=lambda f: f.stat().st_mtime)
                # Get record count
                try:
                    with open(latest_file, 'r') as fp:
                        data = json.load(fp)
                        record_count = len(data.get('records', []))
                except:
                    record_count = None
                
                latest = {
                    "filename": latest_file.name,
                    "modified": datetime.fromtimestamp(latest_file.stat().st_mtime).isoformat(),
                    "size_mb": round(latest_file.stat().st_size / 1024 / 1024, 2),
                    "record_count": record_count
                }
            
            status[data_type] = {
                "file_count": len(files),
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "latest": latest
            }
        else:
            status[data_type] = {
                "file_count": 0,
                "total_size_mb": 0,
                "latest": None
            }
    
    return {
        "status": "ok",
        "data_types": status,
        "processed_dir": str(PROCESSED_DATA_DIR)
    }


@router.get("/files/{data_type}")
def list_processed_files(data_type: str):
    """
    List cac file da xu ly theo data_type
    """
    valid_types = get_supported_types()
    if data_type not in valid_types:
        raise HTTPException(400, f"Invalid data_type. Must be one of: {valid_types}")
    
    processed_dir = PROCESSED_DATA_DIR / data_type
    
    if not processed_dir.exists():
        return {
            "status": "ok",
            "data_type": data_type,
            "count": 0,
            "files": []
        }
    
    files = []
    for f in sorted(processed_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        stat = f.stat()
        
        # Try to read statistics
        statistics = None
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
                statistics = data.get('statistics')
        except:
            pass
        
        files.append({
            "filename": f.name,
            "path": str(f),
            "size_mb": round(stat.st_size / 1024 / 1024, 2),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "statistics": statistics
        })
    
    return {
        "status": "ok",
        "data_type": data_type,
        "count": len(files),
        "files": files[:50]
    }


@router.post("/all")
def process_all_types(
    config: ProcessConfig = ProcessConfig(),
    db: Session = Depends(get_db)
):
    """
    Xu ly tat ca cac data types
    """
    results = {}
    
    for data_type in get_supported_types():
        try:
            # Check if raw files exist
            raw_dir = RAW_DATA_DIR / data_type
            if not raw_dir.exists() or not list(raw_dir.glob("*.json")):
                results[data_type] = {"status": "skipped", "message": "No raw files"}
                continue
            
            result = _process_data_type(data_type, config)
            results[data_type] = {
                "status": result.status,
                "processed": result.processed_records,
                "failed": result.failed_records,
                "processed_file": result.processed_file
            }
        except Exception as e:
            logger.error(f"Failed to process {data_type}: {e}")
            results[data_type] = {
                "status": "error",
                "error": str(e)
            }
    
    total_processed = sum(r.get("processed", 0) for r in results.values() if isinstance(r.get("processed"), int))
    
    return {
        "status": "success",
        "message": f"Processed {total_processed} total records",
        "results": results
    }
