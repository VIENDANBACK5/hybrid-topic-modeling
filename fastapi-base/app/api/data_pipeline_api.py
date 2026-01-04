"""
Data Pipeline API - Endpoints để quản lý data flow
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.etl.data_pipeline import get_data_pipeline
from pydantic import BaseModel
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/data", tags=["📊 Data Pipeline"])


class ExternalAPIConfig(BaseModel):
    """Config for fetching from external API"""
    api_url: str
    params: Optional[Dict] = None
    save_filename: Optional[str] = None


@router.post("/fetch-external")
def fetch_from_external_api(
    config: ExternalAPIConfig,
    db: Session = Depends(get_db)
) -> Dict:
    """
    📥 Fetch data từ external API và lưu vào data/raw/
    
    **Example:**
    ```bash
    curl -X POST http://localhost:7777/api/data/fetch-external \\
      -H "Content-Type: application/json" \\
      -d '{
        "api_url": "http://192.168.30.28:8000/api/articles",
        "params": {"limit": 500}
      }'
    ```
    """
    try:
        pipeline = get_data_pipeline(db)
        result = pipeline.fetch_and_save_raw_data(
            external_api_url=config.api_url,
            params=config.params,
            save_filename=config.save_filename
        )
        
        if result["status"] == "success":
            return {
                "status": "success",
                "message": f"Fetched {result['record_count']} records",
                "result": result
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error"))
            
    except Exception as e:
        logger.error(f"Failed to fetch external data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export-db-to-raw")
def export_database_to_raw(
    limit: Optional[int] = None,
    save_filename: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Dict:
    """
    📦 Export data từ database ra data/raw/
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:7777/api/data/export-db-to-raw?limit=500"
    ```
    """
    try:
        pipeline = get_data_pipeline(db)
        result = pipeline.sync_from_database_to_raw(
            limit=limit,
            save_filename=save_filename
        )
        
        if result["status"] == "success":
            return {
                "status": "success",
                "message": f"Exported {result['record_count']} records",
                "result": result
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", result.get("message")))
            
    except Exception as e:
        logger.error(f"Failed to export data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ProcessDataConfig(BaseModel):
    """Config for processing data"""
    raw_file: str
    save_filename: Optional[str] = None


@router.post("/process")
def process_raw_data(
    config: ProcessDataConfig,
    db: Session = Depends(get_db)
) -> Dict:
    """
    🔧 Xử lý raw data → processed data
    
    **Actions:**
    - Normalize data structure
    - Clean text (remove HTML, special chars)
    - Validate và filter
    - Save to data/processed/
    
    **Example:**
    ```bash
    curl -X POST http://localhost:7777/api/data/process \\
      -H "Content-Type: application/json" \\
      -d '{
        "raw_file": "data/raw/raw_20260104_120000.json"
      }'
    ```
    """
    try:
        pipeline = get_data_pipeline(db)
        result = pipeline.process_raw_data(
            raw_file=config.raw_file,
            save_filename=config.save_filename
        )
        
        if result["status"] == "success":
            stats = result["statistics"]
            return {
                "status": "success",
                "message": f"Processed {stats['processed']}/{stats['total']} records",
                "result": result
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error"))
            
    except Exception as e:
        logger.error(f"Failed to process data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class LoadDataConfig(BaseModel):
    """Config for loading data to DB"""
    processed_file: str
    update_existing: bool = False


@router.post("/load-to-db")
def load_processed_to_database(
    config: LoadDataConfig,
    db: Session = Depends(get_db)
) -> Dict:
    """
    💾 Load processed data vào database
    
    **Example:**
    ```bash
    curl -X POST http://localhost:7777/api/data/load-to-db \\
      -H "Content-Type: application/json" \\
      -d '{
        "processed_file": "data/processed/processed_20260104_120000.json",
        "update_existing": false
      }'
    ```
    """
    try:
        pipeline = get_data_pipeline(db)
        result = pipeline.load_processed_data_to_db(
            processed_file=config.processed_file,
            update_existing=config.update_existing
        )
        
        if result["status"] == "success":
            stats = result["statistics"]
            return {
                "status": "success",
                "message": f"Loaded {stats['inserted']} new, updated {stats['updated']}, skipped {stats['skipped']}",
                "result": result
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error"))
            
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/full-etl")
def run_full_etl(
    external_api_url: Optional[str] = None,
    use_database: bool = True,
    limit: Optional[int] = None,
    db: Session = Depends(get_db)
) -> Dict:
    """
    🔄 Chạy FULL ETL pipeline
    
    **Workflow:**
    1. Fetch from external API hoặc export từ DB → data/raw/
    2. Process raw data → data/processed/
    3. Load processed data → database
    
    **Args:**
    - `external_api_url`: URL của external API (None = use database)
    - `use_database`: Export từ database (default: True)
    - `limit`: Giới hạn records
    
    **Example:**
    ```bash
    # ETL từ database
    curl -X POST "http://localhost:7777/api/data/full-etl?use_database=true&limit=500"
    
    # ETL từ external API
    curl -X POST "http://localhost:7777/api/data/full-etl?external_api_url=http://192.168.30.28:8000/api/articles"
    ```
    """
    try:
        pipeline = get_data_pipeline(db)
        results = {
            "steps": [],
            "status": "success"
        }
        
        # Step 1: Fetch/Export
        if external_api_url:
            logger.info("Running ETL with external API source...")
            fetch_result = pipeline.fetch_and_save_raw_data(external_api_url)
        elif use_database:
            logger.info("Running ETL with database source...")
            fetch_result = pipeline.sync_from_database_to_raw(limit=limit)
        else:
            raise HTTPException(
                status_code=400,
                detail="Must provide external_api_url or set use_database=true"
            )
        
        if fetch_result["status"] != "success":
            return {
                "status": "error",
                "step": "fetch",
                "error": fetch_result.get("error")
            }
        
        results["steps"].append({
            "name": "fetch",
            "status": "success",
            "file": fetch_result["raw_file"],
            "records": fetch_result["record_count"]
        })
        
        # Step 2: Process
        process_result = pipeline.process_raw_data(fetch_result["raw_file"])
        
        if process_result["status"] != "success":
            return {
                "status": "error",
                "step": "process",
                "error": process_result.get("error")
            }
        
        results["steps"].append({
            "name": "process",
            "status": "success",
            "file": process_result["processed_file"],
            "statistics": process_result["statistics"]
        })
        
        # Step 3: Load to DB
        load_result = pipeline.load_processed_data_to_db(
            process_result["processed_file"],
            update_existing=False
        )
        
        if load_result["status"] != "success":
            return {
                "status": "error",
                "step": "load",
                "error": load_result.get("error")
            }
        
        results["steps"].append({
            "name": "load",
            "status": "success",
            "statistics": load_result["statistics"]
        })
        
        return {
            "status": "success",
            "message": "Full ETL completed",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Failed to run full ETL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/raw")
def list_raw_files() -> Dict:
    """
    📋 List raw data files
    
    **Example:**
    ```bash
    curl http://localhost:7777/api/data/files/raw
    ```
    """
    try:
        from pathlib import Path
        import os
        
        raw_dir = Path("data/raw")
        files = []
        
        for file in sorted(raw_dir.glob("*.json"), reverse=True):
            stat = file.stat()
            files.append({
                "filename": file.name,
                "path": str(file),
                "size_mb": round(stat.st_size / 1024 / 1024, 2),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        return {
            "status": "success",
            "count": len(files),
            "files": files[:20]  # Latest 20
        }
        
    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/processed")
def list_processed_files() -> Dict:
    """
    📋 List processed data files
    
    **Example:**
    ```bash
    curl http://localhost:7777/api/data/files/processed
    ```
    """
    try:
        from pathlib import Path
        from datetime import datetime
        import os
        
        processed_dir = Path("data/processed")
        files = []
        
        for file in sorted(processed_dir.glob("*.json"), reverse=True):
            stat = file.stat()
            files.append({
                "filename": file.name,
                "path": str(file),
                "size_mb": round(stat.st_size / 1024 / 1024, 2),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        return {
            "status": "success",
            "count": len(files),
            "files": files[:20]  # Latest 20
        }
        
    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        raise HTTPException(status_code=500, detail=str(e))
