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
    processed_file: Optional[str] = Field(None, description="Path to processed file. If None, will load all latest files")
    data_types: Optional[List[str]] = Field(None, description="Data types to load (facebook, tiktok, threads, newspaper). If None, load all")
    update_existing: bool = Field(default=False, description="Update existing records")
    analyze_sentiment: bool = Field(default=True, description="Run sentiment analysis")


# ============================================
# PROCESS ALL TYPES (Must be BEFORE dynamic route)
# ============================================

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


# ============================================
# LOAD TO DATABASE (Must be BEFORE dynamic route)
# ============================================

def _get_latest_processed_file(data_type: str) -> Optional[Path]:
    """Get the latest processed file for a data type"""
    processed_dir = PROCESSED_DATA_DIR / data_type
    if not processed_dir.exists():
        return None
    files = list(processed_dir.glob(f"{data_type}_processed_*.json"))
    if not files:
        return None
    return max(files, key=lambda f: f.stat().st_mtime)


def _load_single_file(processed_file: Path, config: LoadConfig, db: Session) -> dict:
    """Load a single processed file to database"""
    from app.models.model_article import Article
    from app.services.sentiment import get_sentiment_analyzer
    from app.models import SentimentAnalysis
    
    logger.info(f"Loading to DB: {processed_file}")
    
    # Load processed data
    with open(processed_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    records = data.get('records', [])
    data_type = data.get('data_type', 'unknown')
    
    if not records:
        return {"status": "empty", "data_type": data_type, "message": "No records to load", "inserted": 0, "updated": 0, "skipped": 0}
    
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
                # Truncate source to 512 chars to avoid DB error
                source_val = record.get('source', record.get('url', ''))
                if len(source_val) > 512:
                    source_val = source_val[:512]
                
                article = Article(
                    url=record.get('url'),
                    source_type=record.get('source_type', 'api'),
                    source=source_val,
                    domain=record.get('source_name') or record.get('domain'),  # Use source_name if available
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
    
    return {
        "status": "success",
        "data_type": data_type,
        "file": str(processed_file.name),
        "total_records": len(records),
        "inserted": stats['inserted'],
        "updated": stats['updated'],
        "skipped": stats['skipped'],
        "sentiment_analyzed": stats['sentiment_analyzed']
    }


def _load_all_latest(config: LoadConfig, db: Session) -> dict:
    """Load all latest processed files to database"""
    from fastapi import HTTPException
    
    # Determine which data types to load
    all_types = ["facebook", "tiktok", "threads", "newspaper"]
    data_types = config.data_types if config.data_types else all_types
    
    # Validate data types
    invalid_types = [dt for dt in data_types if dt not in all_types]
    if invalid_types:
        raise HTTPException(400, f"Invalid data types: {invalid_types}. Valid: {all_types}")
    
    results = {}
    total_inserted = 0
    total_updated = 0
    total_skipped = 0
    
    for data_type in data_types:
        latest_file = _get_latest_processed_file(data_type)
        if not latest_file:
            results[data_type] = {"status": "skipped", "message": "No processed files found"}
            continue
        
        try:
            result = _load_single_file(latest_file, config, db)
            results[data_type] = result
            total_inserted += result.get('inserted', 0)
            total_updated += result.get('updated', 0)
            total_skipped += result.get('skipped', 0)
        except Exception as e:
            logger.error(f"Failed to load {data_type}: {e}")
            results[data_type] = {"status": "error", "error": str(e)}
    
    # Commit all changes
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to commit: {e}")
    
    return {
        "status": "success",
        "mode": "load_all_latest",
        "data_types_loaded": data_types,
        "results": results,
        "summary": {
            "total_inserted": total_inserted,
            "total_updated": total_updated,
            "total_skipped": total_skipped
        },
        "message": f"Loaded {len(data_types)} data types: inserted {total_inserted}, updated {total_updated}, skipped {total_skipped}"
    }


@router.post("/load-to-db")
def load_to_database(
    config: LoadConfig = LoadConfig(),
    db: Session = Depends(get_db)
):
    """
    Load processed data vao database
    
    Modes:
    1. Load ALL latest files: POST with empty body or {"data_types": ["facebook", "newspaper"]}
    2. Load SPECIFIC file: POST with {"processed_file": "facebook_processed_xxx.json"}
    
    Examples:
    ```bash
    # Load all latest files from all data types
    curl -X POST http://localhost:7777/api/process/load-to-db
    
    # Load only facebook and newspaper latest files
    curl -X POST http://localhost:7777/api/process/load-to-db \\
      -H "Content-Type: application/json" \\
      -d '{"data_types": ["facebook", "newspaper"]}'
    
    # Load specific file
    curl -X POST http://localhost:7777/api/process/load-to-db \\
      -H "Content-Type: application/json" \\
      -d '{"processed_file": "facebook_processed_20260116_110117.json"}'
    ```
    """
    # MODE 1: Load ALL latest files
    if not config.processed_file:
        return _load_all_latest(config, db)
    
    # MODE 2: Load SPECIFIC file
    processed_file = Path(config.processed_file)
    
    if not processed_file.exists():
        if not processed_file.is_absolute():
            filename = processed_file.name
            data_type = None
            for dt in ["facebook", "tiktok", "threads", "newspaper"]:
                if filename.startswith(dt):
                    data_type = dt
                    break
            
            if data_type:
                processed_file = PROCESSED_DATA_DIR / data_type / filename
            else:
                for dt in ["facebook", "tiktok", "threads", "newspaper"]:
                    candidate = PROCESSED_DATA_DIR / dt / filename
                    if candidate.exists():
                        processed_file = candidate
                        break
        
        if not processed_file.exists():
            raise HTTPException(404, f"Processed file not found: {config.processed_file}")
    
    result = _load_single_file(processed_file, config, db)
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to commit: {e}")
    
    return {
        "status": "success",
        "mode": "load_single_file",
        "data_type": result.get('data_type'),
        "processed_file": str(processed_file),
        "statistics": result,
        "message": f"Inserted {result['inserted']}, updated {result['updated']}, skipped {result['skipped']}"
    }


# ============================================
# DYNAMIC PROCESS ENDPOINT (CONSOLIDATED)
# ============================================

@router.post("/{data_type}", response_model=ProcessResult)
def process_data(
    data_type: str,
    config: ProcessConfig = ProcessConfig(),
    db: Session = Depends(get_db)
):
    """
    Xu ly raw data (Consolidated endpoint for all data types)
    
    Supported data_type:
    - facebook: Process Facebook posts
    - tiktok: Process TikTok videos
    - threads: Process Threads posts
    - newspaper: Process news articles
    
    Steps:
    - Doc file tu data/raw/{data_type}/
    - Chuan hoa cac truong
    - Clean text
    - Luu vao data/processed/{data_type}/
    
    Example:
    ```bash
    curl -X POST http://localhost:7777/api/process/facebook \\
      -H "Content-Type: application/json" \\
      -d '{"raw_file": null, "skip_duplicates": true}'
    
    curl -X POST http://localhost:7777/api/process/newspaper \\
      -H "Content-Type: application/json" \\
      -d '{"skip_duplicates": true}'
    ```
    """
    # Validate data_type using processor registry
    if data_type not in get_supported_types():
        raise HTTPException(
            status_code=400,
            detail=f"Invalid data_type '{data_type}'. Supported types: {', '.join(get_supported_types())}"
        )
    
    return _process_data_type(data_type, config)


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


# ============================================
# DATABASE STATISTICS
# ============================================

@router.get("/db-stats")
def get_database_stats(db: Session = Depends(get_db)) -> Dict:
    """
    Xem so luong data trong cac bang
    """
    from app.models import (
        Article, 
        SentimentAnalysis,
        DailySnapshot,
        TrendReport,
        HotTopic,
        KeywordStats,
        TopicMentionStats,
        WebsiteActivityStats,
        SocialActivityStats,
        TrendAlert,
        HashtagStats,
        ViralContent,
        CategoryTrendStats
    )
    from app.models.model_custom_topic import CustomTopic, ArticleCustomTopic
    from app.models.model_bertopic_discovered import BertopicDiscoveredTopic, ArticleBertopicTopic, TopicTrainingSession
    
    stats = {}
    total = 0
    
    all_tables = {
        "articles": Article,
        "sentiment_analysis": SentimentAnalysis,
        "custom_topics": CustomTopic,
        "article_custom_topics": ArticleCustomTopic,
        "bertopic_discovered_topics": BertopicDiscoveredTopic,
        "article_bertopic_topics": ArticleBertopicTopic,
        "topic_training_sessions": TopicTrainingSession,
        "daily_snapshots": DailySnapshot,
        "trend_reports": TrendReport,
        "hot_topics": HotTopic,
        "keyword_stats": KeywordStats,
        "topic_mention_stats": TopicMentionStats,
        "website_activity_stats": WebsiteActivityStats,
        "social_activity_stats": SocialActivityStats,
        "trend_alerts": TrendAlert,
        "hashtag_stats": HashtagStats,
        "viral_content": ViralContent,
        "category_trend_stats": CategoryTrendStats,
    }
    
    for table_name, model in all_tables.items():
        try:
            count = db.query(model).count()
            stats[table_name] = count
            total += count
        except Exception as e:
            stats[table_name] = f"Error: {str(e)}"
    
    return {
        "status": "success",
        "tables": stats,
        "total_rows": total,
        "table_count": len([v for v in stats.values() if isinstance(v, int)])
    }
