"""
Data Fetch API - Social Media & News
Endpoints để lấy data từ external API cho social media và báo chí

Endpoints:
- POST /api/fetch/social/facebook - Fetch Facebook posts
- POST /api/fetch/social/tiktok - Fetch TikTok videos  
- POST /api/fetch/social/threads - Fetch Threads posts
- POST /api/fetch/social/newspaper - Fetch báo chí
- POST /api/fetch/social/all - Fetch tất cả
- GET /api/fetch/social/status - Xem trạng thái
- GET /api/fetch/social/files/{data_type} - List files đã fetch
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
router = APIRouter(prefix="/api/fetch/social", tags=["Data Fetch - Social"])

# Base URL for external API
EXTERNAL_API_BASE = "http://192.168.30.28:8548/api/v1/posts/by-type"

# Directory structure
RAW_DATA_DIR = Path("data/raw")

# Valid data types for social/news
VALID_SOCIAL_TYPES = ["facebook", "tiktok", "threads", "newspaper"]


class FetchConfig(BaseModel):
    """Config chung cho fetch"""
    page_size: Optional[int] = Field(default=500, ge=1, le=500, description="Default 500 (max) for fastest fetch. Set lower to reduce memory.")
    max_pages: Optional[int] = Field(default=None, description="None = fetch all pages")
    sort_by: str = "id"
    order: str = "desc"
    type_newspaper: Optional[str] = Field(default=None, description="Filter by type_newspaper (education, medical, etc.). None = fetch all types")


class FetchResult(BaseModel):
    """Kết quả fetch"""
    status: str
    data_type: str
    total_fetched: int
    unique_records: int
    duplicates_in_api: int
    pages_processed: int
    raw_file: str
    message: str


# ============================================
# FETCH ALL TYPES
# ============================================

@router.post("/all")
def fetch_all_social_types(
    config: FetchConfig = FetchConfig(),
    db: Session = Depends(get_db)
):
    """
    Fetch tất cả các loại social media và báo chí
    
    Example:
    ```bash
    curl -X POST http://localhost:7777/api/fetch/social/all \\
      -H "Content-Type: application/json" \\
      -d '{"page_size": 100, "max_pages": 5}'
    ```
    """
    results = {}
    
    for data_type in VALID_SOCIAL_TYPES:
        try:
            result = _fetch_social_data(data_type, config)
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
        "message": f"Fetched {total_records} total records across all social types",
        "results": results
    }


# ============================================
# DYNAMIC FETCH ENDPOINT
# ============================================

@router.post("/{data_type}", response_model=FetchResult)
def fetch_social_data(
    data_type: str,
    config: FetchConfig = FetchConfig(),
    db: Session = Depends(get_db)
):
    """
    Fetch data từ external API cho social media và báo chí
    
    Supported data_type:
    - facebook: Facebook posts
    - tiktok: TikTok videos
    - threads: Threads posts
    - newspaper: News articles
    
    Example:
    ```bash
    curl -X POST http://localhost:7777/api/fetch/social/facebook \\
      -H "Content-Type: application/json" \\
      -d '{"page_size": 100, "max_pages": 10}'
    
    curl -X POST http://localhost:7777/api/fetch/social/newspaper \\
      -H "Content-Type: application/json" \\
      -d '{"page_size": 100, "type_newspaper": "economy"}'
    ```
    """
    if data_type not in VALID_SOCIAL_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid data_type '{data_type}'. Supported types: {', '.join(VALID_SOCIAL_TYPES)}"
        )
    
    return _fetch_social_data(data_type, config)


# ============================================
# HELPER FUNCTIONS
# ============================================

def _fetch_social_data(data_type: str, config: FetchConfig) -> FetchResult:
    """
    Core function để fetch social/news data
    """
    logger.info(f"Starting fetch for social/{data_type}...")
    
    # Use specific endpoint if type_newspaper filter is specified
    if config.type_newspaper and data_type == "newspaper":
        api_url = f"http://192.168.30.28:8548/api/v1/posts/by-type-newspaper/{config.type_newspaper}"
        logger.info(f"Using targeted endpoint for type_newspaper={config.type_newspaper}")
    else:
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
            
            logger.info(f"Page {page}: {len(records)} records (cumulative: {len(all_records)} unique)")
            
            # Check if last page
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
                "source": "social",
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
# STATUS AND FILE LISTING
# ============================================

@router.get("/status")
def get_social_fetch_status():
    """
    Xem trạng thái fetch social media & news
    
    Returns: Thống kê về số file và records của mỗi data type
    """
    status = {}
    
    for data_type in VALID_SOCIAL_TYPES:
        type_dir = RAW_DATA_DIR / data_type
        
        if not type_dir.exists():
            status[data_type] = {
                "files": 0,
                "latest": None
            }
            continue
        
        files = list(type_dir.glob("*.json"))
        if not files:
            status[data_type] = {
                "files": 0,
                "latest": None
            }
            continue
        
        latest_file = max(files, key=lambda f: f.stat().st_mtime)
        stat = latest_file.stat()
        
        # Try to count records in latest file
        record_count = None
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                record_count = data.get("total_records") or len(data.get("records", []))
        except:
            pass
        
        status[data_type] = {
            "files": len(files),
            "latest": {
                "filename": latest_file.name,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "size_mb": round(stat.st_size / 1024 / 1024, 2),
                "records": record_count
            }
        }
    
    return {
        "status": "ok",
        "source": "social",
        "types": status
    }


@router.get("/files/{data_type}")
def list_social_files_by_type(data_type: str):
    """
    List các file đã fetch theo data_type
    
    Args:
    - data_type: facebook | tiktok | threads | newspaper
    """
    if data_type not in VALID_SOCIAL_TYPES:
        raise HTTPException(400, f"Invalid data_type. Must be one of: {VALID_SOCIAL_TYPES}")
    
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
