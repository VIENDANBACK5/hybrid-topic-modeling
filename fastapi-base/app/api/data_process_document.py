"""
Data Process API - Documents (Internal/External)
Endpoints xử lý raw data cho tài liệu

Endpoints:
- POST /api/process/document/{document_type} - Xử lý internal hoặc external
- POST /api/process/document/all - Xử lý tất cả documents
- POST /api/process/document/load-to-db - Load vào important_posts
- GET /api/process/document/status - Xem trạng thái
- GET /api/process/document/files/{document_type} - List files
- GET /api/process/document/db-stats - Thống kê DB
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.model_important_post import ImportantPost
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
import logging
import json
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/process/document", tags=["Data Process - Document"])

# Directory structure
RAW_DATA_DIR = Path("data/raw/document")
PROCESSED_DATA_DIR = Path("data/processed/document")

# Valid document types
VALID_DOCUMENT_TYPES = ["internal", "external"]


class DocumentProcessConfig(BaseModel):
    """Config cho xử lý documents"""
    raw_file: Optional[str] = Field(None, description="Path to raw file (if not provided, use latest)")
    skip_duplicates: bool = Field(default=True, description="Skip duplicate URLs within file")


class DocumentProcessResult(BaseModel):
    """Kết quả xử lý documents"""
    status: str
    document_type: str
    raw_file: str
    processed_file: str
    total_records: int
    processed_records: int
    failed_records: int
    message: str


class DocumentLoadConfig(BaseModel):
    """Config cho load documents to DB"""
    processed_file: Optional[str] = Field(None, description="Path to processed file. If None, will load all latest files")
    document_types: Optional[List[str]] = Field(None, description="Document types to load (internal, external). If None, load all")
    update_existing: bool = Field(default=False, description="Update existing records")


# ============================================
# PROCESS ALL DOCUMENT TYPES
# ============================================

@router.post("/all")
def process_all_document_types(
    config: DocumentProcessConfig = DocumentProcessConfig(),
    db: Session = Depends(get_db)
):
    """
    Xử lý tất cả các document types (internal + external)
    
    Example:
    ```bash
    curl -X POST http://localhost:7777/api/process/document/all
    ```
    """
    results = {}
    
    for doc_type in VALID_DOCUMENT_TYPES:
        try:
            raw_dir = RAW_DATA_DIR / doc_type
            if not raw_dir.exists() or not list(raw_dir.glob("*.json")):
                results[doc_type] = {"status": "skipped", "message": "No raw files"}
                continue
            
            result = _process_document_data(doc_type, config)
            results[doc_type] = {
                "status": result.status,
                "processed": result.processed_records,
                "failed": result.failed_records,
                "processed_file": result.processed_file
            }
        except Exception as e:
            logger.error(f"Failed to process document/{doc_type}: {e}")
            results[doc_type] = {
                "status": "error",
                "error": str(e)
            }
    
    total_processed = sum(r.get("processed", 0) for r in results.values() if isinstance(r.get("processed"), int))
    
    return {
        "status": "success",
        "message": f"Processed {total_processed} total documents",
        "results": results
    }


# ============================================
# LOAD TO DATABASE (important_posts)
# ============================================

def _get_latest_processed_file(document_type: str) -> Optional[Path]:
    """Get the latest processed file for a document type"""
    processed_dir = PROCESSED_DATA_DIR / document_type
    if not processed_dir.exists():
        return None
    files = list(processed_dir.glob(f"{document_type}_processed_*.json"))
    if not files:
        return None
    return max(files, key=lambda f: f.stat().st_mtime)


def _load_single_file(processed_file: Path, config: DocumentLoadConfig, db: Session) -> dict:
    """Load a single processed file to important_posts table"""
    logger.info(f"Loading documents to DB: {processed_file}")
    
    with open(processed_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    records = data.get('records', [])
    document_type = data.get('document_type', 'unknown')
    
    if not records:
        return {"status": "empty", "document_type": document_type, "message": "No records to load", "inserted": 0, "updated": 0, "skipped": 0}
    
    # Get existing URLs
    existing_urls = {p.url for p in db.query(ImportantPost.url).all()}
    
    stats = {
        'inserted': 0,
        'updated': 0,
        'skipped': 0,
        'errors': []
    }
    
    for record in records:
        try:
            url = record.get('url')
            if not url:
                stats['skipped'] += 1
                continue
            
            if url in existing_urls:
                if not config.update_existing:
                    stats['skipped'] += 1
                    continue
                # Update existing
                post = db.query(ImportantPost).filter(ImportantPost.url == url).first()
                if post:
                    meta_data = record.get('meta_data', {})
                    post.title = record.get('title') or post.title
                    post.content = record.get('content') or post.content
                    post.type_newspaper = record.get('type_newspaper') or meta_data.get('type_newspaper') or post.type_newspaper
                    post.meta_data = meta_data or post.meta_data
                    post.dvhc = meta_data.get('dvhc') or record.get('dvhc') or post.dvhc
                    post.original_id = record.get('id') or post.original_id
                    post.original_created_at = record.get('created_at') or post.original_created_at
                    post.original_updated_at = record.get('updated_at') or post.original_updated_at
                    post.published_date = meta_data.get('upload_date') or meta_data.get('published_date') or post.published_date
                    post.author = meta_data.get('author') or record.get('author') or post.author
                    post.document_type = document_type
                    # Các trường mở rộng
                    post.statistics = meta_data.get('statistics') or record.get('statistics') or post.statistics
                    post.organizations = meta_data.get('organizations') or record.get('organizations') or post.organizations
                    if record.get('is_featured') is not None:
                        post.is_featured = record.get('is_featured')
                    post.importance_score = meta_data.get('importance_score') or record.get('importance_score') or post.importance_score
                    post.tags = meta_data.get('tags') or record.get('tags') or post.tags
                    post.categories = meta_data.get('categories') or record.get('categories') or post.categories
                    stats['updated'] += 1
            else:
                # Create new important post
                meta_data = record.get('meta_data', {})
                
                post = ImportantPost(
                    url=url,
                    title=record.get('title'),
                    content=record.get('content'),
                    data_type='document',  # Always 'document' for this loader
                    document_type=document_type,  # internal or external
                    type_newspaper=record.get('type_newspaper') or meta_data.get('type_newspaper'),
                    meta_data=meta_data,
                    # Map từ raw data
                    original_id=record.get('id'),
                    original_created_at=record.get('created_at'),
                    original_updated_at=record.get('updated_at'),
                    published_date=meta_data.get('upload_date') or meta_data.get('published_date'),
                    author=meta_data.get('author') or record.get('author'),
                    dvhc=meta_data.get('dvhc') or record.get('dvhc'),
                    # Các trường mở rộng
                    statistics=meta_data.get('statistics') or record.get('statistics'),
                    organizations=meta_data.get('organizations') or record.get('organizations'),
                    is_featured=record.get('is_featured', 1),  # Default = 1 (featured)
                    importance_score=meta_data.get('importance_score') or record.get('importance_score'),
                    tags=meta_data.get('tags') or record.get('tags'),
                    categories=meta_data.get('categories') or record.get('categories'),
                )
                db.add(post)
                db.flush()
                existing_urls.add(url)
                stats['inserted'] += 1
        
        except Exception as e:
            logger.error(f"Error loading document record: {e}")
            stats['errors'].append(str(e)[:100])
            stats['skipped'] += 1
    
    return {
        "status": "success",
        "document_type": document_type,
        "file": str(processed_file.name),
        "total_records": len(records),
        "inserted": stats['inserted'],
        "updated": stats['updated'],
        "skipped": stats['skipped']
    }


def _load_all_latest(config: DocumentLoadConfig, db: Session) -> dict:
    """Load all latest processed files to database"""
    document_types = config.document_types if config.document_types else VALID_DOCUMENT_TYPES
    
    invalid_types = [dt for dt in document_types if dt not in VALID_DOCUMENT_TYPES]
    if invalid_types:
        raise HTTPException(400, f"Invalid document types: {invalid_types}. Valid: {VALID_DOCUMENT_TYPES}")
    
    results = {}
    total_inserted = 0
    total_updated = 0
    total_skipped = 0
    
    for doc_type in document_types:
        latest_file = _get_latest_processed_file(doc_type)
        if not latest_file:
            results[doc_type] = {"status": "skipped", "message": "No processed files found"}
            continue
        
        try:
            result = _load_single_file(latest_file, config, db)
            results[doc_type] = result
            total_inserted += result.get('inserted', 0)
            total_updated += result.get('updated', 0)
            total_skipped += result.get('skipped', 0)
        except Exception as e:
            logger.error(f"Failed to load document/{doc_type}: {e}")
            results[doc_type] = {"status": "error", "error": str(e)}
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to commit: {e}")
    
    return {
        "status": "success",
        "mode": "load_all_latest",
        "source": "document",
        "document_types_loaded": document_types,
        "results": results,
        "summary": {
            "total_inserted": total_inserted,
            "total_updated": total_updated,
            "total_skipped": total_skipped
        },
        "message": f"Loaded {len(document_types)} document types: inserted {total_inserted}, updated {total_updated}, skipped {total_skipped}"
    }


@router.post("/load-to-db")
def load_documents_to_database(
    config: DocumentLoadConfig = DocumentLoadConfig(),
    db: Session = Depends(get_db)
):
    """
    Load processed documents vào important_posts table
    
    Example:
    ```bash
    # Load all latest files
    curl -X POST http://localhost:7777/api/process/document/load-to-db
    
    # Load chỉ internal
    curl -X POST http://localhost:7777/api/process/document/load-to-db \\
      -H "Content-Type: application/json" \\
      -d '{"document_types": ["internal"]}'
    ```
    """
    if not config.processed_file:
        return _load_all_latest(config, db)
    
    processed_file = Path(config.processed_file)
    
    if not processed_file.exists():
        if not processed_file.is_absolute():
            filename = processed_file.name
            doc_type = None
            for dt in VALID_DOCUMENT_TYPES:
                if filename.startswith(dt):
                    doc_type = dt
                    break
            
            if doc_type:
                processed_file = PROCESSED_DATA_DIR / doc_type / filename
            else:
                for dt in VALID_DOCUMENT_TYPES:
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
        "source": "document",
        "document_type": result.get('document_type'),
        "processed_file": str(processed_file),
        "statistics": result,
        "message": f"Inserted {result['inserted']}, updated {result['updated']}, skipped {result['skipped']}"
    }


# ============================================
# DYNAMIC PROCESS ENDPOINT
# ============================================

@router.post("/{document_type}", response_model=DocumentProcessResult)
def process_document_data(
    document_type: str,
    config: DocumentProcessConfig = DocumentProcessConfig(),
    db: Session = Depends(get_db)
):
    """
    Xử lý raw document data
    
    Supported document_type:
    - internal: Tài liệu nội bộ (PDF, Word, etc.)
    - external: Tài liệu bên ngoài
    
    Example:
    ```bash
    curl -X POST http://localhost:7777/api/process/document/internal
    
    curl -X POST http://localhost:7777/api/process/document/external \\
      -H "Content-Type: application/json" \\
      -d '{"skip_duplicates": true}'
    ```
    """
    if document_type not in VALID_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document_type '{document_type}'. Supported types: {', '.join(VALID_DOCUMENT_TYPES)}"
        )
    
    return _process_document_data(document_type, config)


# ============================================
# HELPER FUNCTIONS
# ============================================

def _process_document_data(document_type: str, config: DocumentProcessConfig) -> DocumentProcessResult:
    """Core function để xử lý document data theo type"""
    logger.info(f"Starting process for document/{document_type}...")
    
    raw_dir = RAW_DATA_DIR / document_type
    processed_dir = PROCESSED_DATA_DIR / document_type
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    if config.raw_file:
        raw_file = Path(config.raw_file)
    else:
        raw_files = list(raw_dir.glob("*.json"))
        if not raw_files:
            raise HTTPException(404, f"No raw files found for document/{document_type}")
        raw_file = max(raw_files, key=lambda f: f.stat().st_mtime)
    
    if not raw_file.exists():
        raise HTTPException(404, f"Raw file not found: {raw_file}")
    
    logger.info(f"Processing file: {raw_file}")
    
    try:
        with open(raw_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except Exception as e:
        raise HTTPException(400, f"Failed to load raw file: {e}")
    
    if isinstance(raw_data, dict):
        records = raw_data.get('records', raw_data.get('data', []))
    elif isinstance(raw_data, list):
        records = raw_data
    else:
        raise HTTPException(400, "Invalid raw data format")
    
    if not records:
        return DocumentProcessResult(
            status="empty",
            document_type=document_type,
            raw_file=str(raw_file),
            processed_file="",
            total_records=0,
            processed_records=0,
            failed_records=0,
            message="No records to process"
        )
    
    # Process documents (simpler than social - mainly cleaning and validation)
    processed_records = []
    stats = {'total': len(records), 'success': 0, 'failed': 0, 'duplicates': 0}
    seen_urls = set()
    
    for record in records:
        try:
            url = record.get('url')
            if not url:
                stats['failed'] += 1
                continue
            
            if config.skip_duplicates and url in seen_urls:
                stats['duplicates'] += 1
                continue
            seen_urls.add(url)
            
            # Clean and validate
            meta_data = record.get('meta_data', {})
            processed = {
                'id': record.get('id'),  # original_id từ API
                'url': url,
                'title': (record.get('title') or '').strip(),
                'content': (record.get('content') or '').strip(),
                'data_type': 'document',
                'document_type': document_type,
                'type_newspaper': record.get('type_newspaper') or meta_data.get('type_newspaper'),
                'meta_data': meta_data,
                'created_at': record.get('created_at'),
                'updated_at': record.get('updated_at'),
                # Các trường mở rộng - lấy từ record hoặc meta_data
                'author': meta_data.get('author') or record.get('author'),
                'dvhc': meta_data.get('dvhc') or record.get('dvhc'),
                'statistics': meta_data.get('statistics') or record.get('statistics'),
                'organizations': meta_data.get('organizations') or record.get('organizations'),
                'is_featured': record.get('is_featured', 1),
                'importance_score': meta_data.get('importance_score') or record.get('importance_score'),
                'tags': meta_data.get('tags') or record.get('tags'),
                'categories': meta_data.get('categories') or record.get('categories'),
            }
            
            # Word count
            content = processed.get('content', '')
            processed['word_count'] = len(content.split()) if content else 0
            
            processed_records.append(processed)
            stats['success'] += 1
            
        except Exception as e:
            logger.error(f"Error processing document record: {e}")
            stats['failed'] += 1
    
    # Save processed data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    processed_filename = f"{document_type}_processed_{timestamp}.json"
    processed_file = processed_dir / processed_filename
    
    with open(processed_file, 'w', encoding='utf-8') as f:
        json.dump({
            "data_type": "document",
            "document_type": document_type,
            "source": "document",
            "processed_at": datetime.now().isoformat(),
            "source_file": str(raw_file),
            "statistics": stats,
            "records": processed_records
        }, f, ensure_ascii=False, indent=2, default=str)
    
    logger.info(f"Saved {len(processed_records)} processed documents to {processed_file}")
    
    return DocumentProcessResult(
        status="success",
        document_type=document_type,
        raw_file=str(raw_file),
        processed_file=str(processed_file),
        total_records=stats['total'],
        processed_records=stats['success'],
        failed_records=stats['failed'],
        message=f"Processed {stats['success']}/{stats['total']} {document_type} documents"
    )


# ============================================
# STATUS & FILES
# ============================================

@router.get("/status")
def get_document_process_status():
    """
    Xem tổng quan files đã xử lý cho documents
    """
    status = {}
    
    for doc_type in VALID_DOCUMENT_TYPES:
        processed_dir = PROCESSED_DATA_DIR / doc_type
        if processed_dir.exists():
            files = list(processed_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in files)
            
            latest = None
            if files:
                latest_file = max(files, key=lambda f: f.stat().st_mtime)
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
            
            status[doc_type] = {
                "file_count": len(files),
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "latest": latest
            }
        else:
            status[doc_type] = {
                "file_count": 0,
                "total_size_mb": 0,
                "latest": None
            }
    
    return {
        "status": "ok",
        "source": "document",
        "document_types": status,
        "processed_dir": str(PROCESSED_DATA_DIR)
    }


@router.get("/files/{document_type}")
def list_document_processed_files(document_type: str):
    """
    List các file đã xử lý theo document_type
    """
    if document_type not in VALID_DOCUMENT_TYPES:
        raise HTTPException(400, f"Invalid document_type. Must be one of: {VALID_DOCUMENT_TYPES}")
    
    processed_dir = PROCESSED_DATA_DIR / document_type
    
    if not processed_dir.exists():
        return {
            "status": "ok",
            "document_type": document_type,
            "count": 0,
            "files": []
        }
    
    files = []
    for f in sorted(processed_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        stat = f.stat()
        
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
        "document_type": document_type,
        "count": len(files),
        "files": files[:50]
    }


# ============================================
# DATABASE STATISTICS
# ============================================

@router.get("/db-stats")
def get_document_database_stats(db: Session = Depends(get_db)) -> Dict:
    """
    Xem số lượng documents trong important_posts
    """
    stats = {}
    
    # Count by document_type
    for doc_type in VALID_DOCUMENT_TYPES:
        try:
            count = db.query(ImportantPost).filter(
                ImportantPost.data_type == 'document',
                ImportantPost.document_type == doc_type
            ).count()
            stats[doc_type] = count
        except Exception as e:
            stats[doc_type] = f"Error: {str(e)}"
    
    # Total documents
    try:
        total_documents = db.query(ImportantPost).filter(
            ImportantPost.data_type == 'document'
        ).count()
    except:
        total_documents = 0
    
    # Total important_posts
    try:
        total_all = db.query(ImportantPost).count()
    except:
        total_all = 0
    
    return {
        "status": "success",
        "source": "document",
        "document_counts": stats,
        "total_documents": total_documents,
        "total_important_posts": total_all
    }
