"""
Data Fetch API - Endpoints de lay data tu external API theo tung loai

Endpoints:
- POST /fetch/facebook - Lay data Facebook
- POST /fetch/tiktok - Lay data TikTok  
- POST /fetch/threads - Lay data Threads
- POST /fetch/newspaper - Lay data Newspaper
- GET /fetch/status - Xem trang thai fetch
- GET /fetch/files/{data_type} - List files da fetch
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
import logging
import requests
import json
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/fetch", tags=["Data Fetch"])

# Base URL for external API
EXTERNAL_API_BASE = "http://192.168.30.28:8000/api/v1/posts/by-type"

# Directory structure
RAW_DATA_DIR = Path("data/raw")


class FetchConfig(BaseModel):
    """Config chung cho fetch"""
    page_size: Optional[int] = Field(default=500, ge=1, le=500, description="Default 500 (max) for fastest fetch. Set lower to reduce memory.")
    max_pages: Optional[int] = Field(default=None, description="None = fetch all pages")
    sort_by: str = "id"
    order: str = "desc"


class FetchResult(BaseModel):
    """Ket qua fetch"""
    status: str
    data_type: str
    total_fetched: int
    unique_records: int
    duplicates_in_api: int
    pages_processed: int
    raw_file: str
    message: str


# ============================================
# FACEBOOK
# ============================================

@router.post("/facebook", response_model=FetchResult)
def fetch_facebook(
    config: FetchConfig = FetchConfig(),
    db: Session = Depends(get_db)
):
    """
    Fetch data Facebook tu external API
    
    Response format:
    - url: Link post
    - title: Tieu de
    - content: Noi dung
    - meta_data: {post_id, message, timestamp, comments_count, reactions_count, reshare_count, reactions, author, album_preview, ...}
    - data_type: "facebook"
    - created_at, updated_at
    
    Example:
    ```bash
    curl -X POST http://localhost:7777/api/fetch/facebook \\
      -H "Content-Type: application/json" \\
      -d '{"page_size": 100, "max_pages": 10}'
    ```
    """
    return _fetch_data_type("facebook", config)


# ============================================
# TIKTOK
# ============================================

@router.post("/tiktok", response_model=FetchResult)
def fetch_tiktok(
    config: FetchConfig = FetchConfig(),
    db: Session = Depends(get_db)
):
    """
    Fetch data TikTok tu external API
    
    Response format:
    - url: Link video
    - title: Tieu de video
    - content: Noi dung (giong title)
    - meta_data: {url_video, username, views, views_text, hashtags, thumbnail_url, badge}
    - data_type: "tiktok"
    - created_at, updated_at
    
    Example:
    ```bash
    curl -X POST http://localhost:7777/api/fetch/tiktok \\
      -H "Content-Type: application/json" \\
      -d '{"page_size": 100, "max_pages": 10}'
    ```
    """
    return _fetch_data_type("tiktok", config)


# ============================================
# THREADS
# ============================================

@router.post("/threads", response_model=FetchResult)
def fetch_threads(
    config: FetchConfig = FetchConfig(),
    db: Session = Depends(get_db)
):
    """
    Fetch data Threads tu external API
    
    Response format:
    - url: Link post
    - title: Noi dung post
    - content: Noi dung post
    - meta_data: {username, likes, replies, reposts, shares, time, datetime}
    - data_type: "threads"
    - created_at, updated_at
    
    Example:
    ```bash
    curl -X POST http://localhost:7777/api/fetch/threads \\
      -H "Content-Type: application/json" \\
      -d '{"page_size": 100, "max_pages": 10}'
    ```
    """
    return _fetch_data_type("threads", config)


# ============================================
# NEWSPAPER
# ============================================

@router.post("/newspaper", response_model=FetchResult)
def fetch_newspaper(
    config: FetchConfig = FetchConfig(),
    db: Session = Depends(get_db)
):
    """
    Fetch data Newspaper tu external API
    
    Response format:
    - url: Link bai bao
    - title: Tieu de
    - content: Noi dung
    - meta_data: {...}
    - data_type: "newspaper"
    - created_at, updated_at
    
    Example:
    ```bash
    curl -X POST http://localhost:7777/api/fetch/newspaper \\
      -H "Content-Type: application/json" \\
      -d '{"page_size": 100, "max_pages": null}'
    ```
    """
    return _fetch_data_type("newspaper", config)


# ============================================
# HELPER FUNCTIONS
# ============================================

def _fetch_data_type(data_type: str, config: FetchConfig) -> FetchResult:
    """
    Core function de fetch data theo type
    """
    logger.info(f"Starting fetch for {data_type}...")
    
    api_url = f"{EXTERNAL_API_BASE}/{data_type}"
    save_dir = RAW_DATA_DIR / data_type
    save_dir.mkdir(parents=True, exist_ok=True)
    
    # Use default page_size if None
    page_size = config.page_size or 500
    
    all_records = []
    seen_urls = set()
    duplicates = 0
    page = 1
    
    while True:
        if config.max_pages and page > config.max_pages:
            logger.info(f"Reached max pages: {config.max_pages}")
            break
        
        params = {
            "page": page,
            "page_size": page_size,
            "sort_by": config.sort_by,
            "order": config.order
        }
        
        logger.info(f"Fetching {data_type} page {page}...")
        
        try:
            response = requests.get(api_url, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()
            
            if not data.get("success"):
                logger.warning(f"API returned success=false: {data.get('message')}")
                break
            
            records = data.get("data", [])
            
            if not records:
                logger.info(f"No more records on page {page}")
                break
            
            # Track duplicates within API response
            for record in records:
                url = record.get("url")
                if url:
                    if url in seen_urls:
                        duplicates += 1
                    else:
                        seen_urls.add(url)
                        all_records.append(record)
            
            new_records = len(all_records) - len([r for r in all_records[:-len(records)] if r.get('url') in seen_urls])
            logger.info(f"Page {page}: {len(records)} total, {len(records) - duplicates + len(all_records) - new_records} new (cumulative: {len(all_records)} unique)")
            
            # Check if last page - only break if no records returned or less than page_size
            # Don't rely on total_pages from API as it may be wrong
            if len(records) < page_size:
                logger.info(f"Last page reached (got {len(records)} < {page_size})")
                break
            
            page += 1
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch page {page}: {e}")
            break
        except Exception as e:
            logger.error(f"Error processing page {page}: {e}")
            break
    
    # Save to file
    if all_records:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{data_type}_{timestamp}.json"
        filepath = save_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "data_type": data_type,
                "fetched_at": datetime.now().isoformat(),
                "total_records": len(all_records),
                "unique_urls": len(seen_urls),
                "pages_processed": page - 1 if page > 1 else page,
                "records": all_records
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(all_records)} {data_type} records to {filepath}")
        
        return FetchResult(
            status="success",
            data_type=data_type,
            total_fetched=len(all_records) + duplicates,
            unique_records=len(all_records),
            duplicates_in_api=duplicates,
            pages_processed=page - 1 if page > 1 else page,
            raw_file=str(filepath),
            message=f"Fetched {len(all_records)} unique {data_type} records"
        )
    else:
        return FetchResult(
            status="empty",
            data_type=data_type,
            total_fetched=0,
            unique_records=0,
            duplicates_in_api=0,
            pages_processed=page - 1 if page > 1 else 0,
            raw_file="",
            message=f"No {data_type} records found"
        )


# ============================================
# STATUS & FILES
# ============================================

@router.get("/status")
def get_fetch_status():
    """
    Xem tong quan cac file da fetch theo tung loai
    """
    status = {}
    
    for data_type in ["facebook", "tiktok", "threads", "newspaper"]:
        type_dir = RAW_DATA_DIR / data_type
        if type_dir.exists():
            files = list(type_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in files)
            
            # Get latest file info
            latest = None
            if files:
                latest_file = max(files, key=lambda f: f.stat().st_mtime)
                latest = {
                    "filename": latest_file.name,
                    "modified": datetime.fromtimestamp(latest_file.stat().st_mtime).isoformat(),
                    "size_mb": round(latest_file.stat().st_size / 1024 / 1024, 2)
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
        "raw_dir": str(RAW_DATA_DIR)
    }


@router.get("/files/{data_type}")
def list_files_by_type(data_type: str):
    """
    List cac file da fetch theo data_type
    
    Args:
    - data_type: facebook | tiktok | threads | newspaper
    """
    valid_types = ["facebook", "tiktok", "threads", "newspaper"]
    if data_type not in valid_types:
        raise HTTPException(400, f"Invalid data_type. Must be one of: {valid_types}")
    
    type_dir = RAW_DATA_DIR / data_type
    
    if not type_dir.exists():
        return {
            "status": "ok",
            "data_type": data_type,
            "count": 0,
            "files": []
        }
    
    files = []
    for f in sorted(type_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        stat = f.stat()
        
        # Try to read record count from file
        record_count = None
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
                record_count = data.get("total_records") or len(data.get("records", []))
        except:
            pass
        
        files.append({
            "filename": f.name,
            "path": str(f),
            "size_mb": round(stat.st_size / 1024 / 1024, 2),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "record_count": record_count
        })
    
    return {
        "status": "ok",
        "data_type": data_type,
        "count": len(files),
        "files": files[:50]  # Latest 50
    }


@router.post("/all")
def fetch_all_types(
    config: FetchConfig = FetchConfig(),
    db: Session = Depends(get_db)
):
    """
    Fetch tat ca cac data types
    
    Example:
    ```bash
    curl -X POST http://localhost:7777/api/fetch/all \\
      -H "Content-Type: application/json" \\
      -d '{"page_size": 100, "max_pages": 5}'
    ```
    """
    results = {}
    
    for data_type in ["facebook", "tiktok", "threads", "newspaper"]:
        try:
            result = _fetch_data_type(data_type, config)
            results[data_type] = {
                "status": result.status,
                "unique_records": result.unique_records,
                "duplicates": result.duplicates_in_api,
                "raw_file": result.raw_file
            }
        except Exception as e:
            logger.error(f"Failed to fetch {data_type}: {e}")
            results[data_type] = {
                "status": "error",
                "error": str(e)
            }
    
    total_records = sum(r.get("unique_records", 0) for r in results.values() if isinstance(r.get("unique_records"), int))
    
    return {
        "status": "success",
        "message": f"Fetched {total_records} total records across all types",
        "results": results
    }
