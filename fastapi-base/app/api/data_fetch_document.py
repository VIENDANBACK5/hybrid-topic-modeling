"""
Data Fetch API - Documents (Internal/External)
Endpoints để lấy tài liệu từ external API

Endpoints:
- POST /api/fetch/document/internal - Fetch tài liệu nội bộ
- POST /api/fetch/document/external - Fetch tài liệu bên ngoài
- POST /api/fetch/document/all - Fetch tất cả documents
- GET /api/fetch/document/status - Xem trạng thái
- GET /api/fetch/document/files/{document_type} - List files đã fetch
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
from dotenv import load_dotenv
import os
load_dotenv()

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/fetch/document", tags=["Data Fetch - Document"])

# Base URL for external API (posts-v2)
EXTERNAL_API_BASE = os.getenv("EXTERNAL_API_BASE_URL") + "/api/v1/posts-v2/by-document-type"

# Directory structure
RAW_DATA_DIR = Path("data/raw/document")

# Valid document types
VALID_DOCUMENT_TYPES = ["internal", "external"]


class DocumentFetchConfig(BaseModel):
    """Config cho fetch documents"""
    page_size: Optional[int] = Field(default=500, ge=1, le=500, description="Default 500 (max) for fastest fetch.")
    max_pages: Optional[int] = Field(default=None, description="None = fetch all pages")
    sort_by: str = "id"
    order: str = "desc"


class DocumentFetchResult(BaseModel):
    """Kết quả fetch documents"""
    status: str
    document_type: str
    total_fetched: int
    unique_records: int
    duplicates_in_api: int
    pages_processed: int
    raw_file: str
    message: str


# ============================================
# FETCH ALL DOCUMENT TYPES
# ============================================

@router.post("/all")
def fetch_all_document_types(
    config: DocumentFetchConfig = DocumentFetchConfig(),
    db: Session = Depends(get_db)
):
    """
    Fetch tất cả các loại documents (internal + external)
    
    Example:
    ```bash
    curl -X POST http://localhost:7777/api/fetch/document/all \\
      -H "Content-Type: application/json" \\
      -d '{"page_size": 100, "max_pages": 5}'
    ```
    """
    results = {}
    
    for doc_type in VALID_DOCUMENT_TYPES:
        try:
            result = _fetch_document_data(doc_type, config)
            results[doc_type] = {
                "status": result.status,
                "unique_records": result.unique_records,
                "duplicates": result.duplicates_in_api,
                "raw_file": result.raw_file
            }
        except Exception as e:
            logger.error(f"Failed to fetch document/{doc_type}: {e}")
            results[doc_type] = {
                "status": "error",
                "error": str(e)
            }
    
    total_records = sum(r.get("unique_records", 0) for r in results.values() if isinstance(r.get("unique_records"), int))
    
    return {
        "status": "success",
        "message": f"Fetched {total_records} total documents across all types",
        "results": results
    }


# ============================================
# DYNAMIC FETCH ENDPOINT
# ============================================

@router.post("/{document_type}", response_model=DocumentFetchResult)
def fetch_document_data(
    document_type: str,
    config: DocumentFetchConfig = DocumentFetchConfig(),
    db: Session = Depends(get_db)
):
    """
    Fetch documents từ external API
    
    Supported document_type:
    - internal: Tài liệu nội bộ (PDF, Word, etc.)
    - external: Tài liệu bên ngoài
    
    Response format:
    - url: Path to document file
    - title: Document title
    - content: Extracted content/description
    - meta_data: {original_filename, file_size, content_type, upload_date, type_newspaper, description}
    - document_type: internal | external
    
    Example:
    ```bash
    curl -X POST http://localhost:7777/api/fetch/document/internal \\
      -H "Content-Type: application/json" \\
      -d '{"page_size": 100, "max_pages": 10}'
    
    curl -X POST http://localhost:7777/api/fetch/document/external \\
      -H "Content-Type: application/json" \\
      -d '{"page_size": 50}'
    ```
    """
    if document_type not in VALID_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document_type '{document_type}'. Supported types: {', '.join(VALID_DOCUMENT_TYPES)}"
        )
    
    return _fetch_document_data(document_type, config)


# ============================================
# HELPER FUNCTIONS
# ============================================

def _fetch_document_data(document_type: str, config: DocumentFetchConfig) -> DocumentFetchResult:
    """
    Core function để fetch document data
    """
    logger.info(f"Starting fetch for document/{document_type}...")
    
    api_url = f"{EXTERNAL_API_BASE}/{document_type}"
    
    save_dir = RAW_DATA_DIR / document_type
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
        
        logger.info(f"Fetching document/{document_type} page {page}...")
        
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
            
            # Track duplicates and transform records
            for record in records:
                url = record.get("url")
                if url:
                    if url in seen_urls:
                        duplicates += 1
                    else:
                        seen_urls.add(url)
                        
                        # Transform record for important_posts compatibility
                        transformed = {
                            "id": record.get("id"),
                            "url": url,
                            "title": record.get("title"),
                            "content": record.get("content"),
                            "data_type": "document",  # Key difference from social
                            "document_type": document_type,  # internal or external
                            "type_newspaper": record.get("meta_data", {}).get("type_newspaper"),
                            "meta_data": record.get("meta_data", {}),
                            "created_at": record.get("created_at"),
                            "updated_at": record.get("updated_at")
                        }
                        all_records.append(transformed)
            
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
        filename = f"{document_type}_{timestamp}.json"
        filepath = save_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "data_type": "document",
                "document_type": document_type,
                "source": "document",
                "fetched_at": datetime.now().isoformat(),
                "total_records": len(all_records),
                "unique_urls": len(seen_urls),
                "pages_processed": page - 1 if page > 1 else page,
                "records": all_records
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(all_records)} document/{document_type} records to {filepath}")
        
        return DocumentFetchResult(
            status="success",
            document_type=document_type,
            total_fetched=len(all_records) + duplicates,
            unique_records=len(all_records),
            duplicates_in_api=duplicates,
            pages_processed=page - 1 if page > 1 else page,
            raw_file=str(filepath),
            message=f"Fetched {len(all_records)} unique {document_type} documents"
        )
    else:
        return DocumentFetchResult(
            status="empty",
            document_type=document_type,
            total_fetched=0,
            unique_records=0,
            duplicates_in_api=0,
            pages_processed=page - 1 if page > 1 else 0,
            raw_file="",
            message=f"No {document_type} documents found"
        )


# ============================================
# STATUS AND FILE LISTING
# ============================================

@router.get("/status")
def get_document_fetch_status():
    """
    Xem trạng thái fetch documents
    
    Returns: Thống kê về số file và records của mỗi document type
    """
    status = {}
    
    for doc_type in VALID_DOCUMENT_TYPES:
        type_dir = RAW_DATA_DIR / doc_type
        
        if not type_dir.exists():
            status[doc_type] = {
                "files": 0,
                "latest": None
            }
            continue
        
        files = list(type_dir.glob("*.json"))
        if not files:
            status[doc_type] = {
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
        
        status[doc_type] = {
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
        "source": "document",
        "types": status
    }


@router.get("/files/{document_type}")
def list_document_files_by_type(document_type: str):
    """
    List các file đã fetch theo document_type
    
    Args:
    - document_type: internal | external
    """
    if document_type not in VALID_DOCUMENT_TYPES:
        raise HTTPException(400, f"Invalid document_type. Must be one of: {VALID_DOCUMENT_TYPES}")
    
    type_dir = RAW_DATA_DIR / document_type
    
    if not type_dir.exists():
        return {
            "status": "ok",
            "document_type": document_type,
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
        "document_type": document_type,
        "count": len(files),
        "files": files[:50]  # Latest 50
    }
