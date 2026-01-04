"""
Data Pipeline Service - Xử lý data từ external API → processed files → training
"""
import logging
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.services.etl.data_normalizer import DataNormalizer
from app.services.etl.text_cleaner import TextCleaner

logger = logging.getLogger(__name__)


class DataPipelineService:
    """Service quản lý toàn bộ data flow: API → Processed → Training"""
    
    def __init__(self, db: Session):
        self.db = db
        self.normalizer = DataNormalizer()
        self.cleaner = TextCleaner()
        
        # Data directories
        self.base_dir = Path("data")
        self.raw_dir = self.base_dir / "raw"
        self.processed_dir = self.base_dir / "processed"
        self.results_dir = self.base_dir / "results"
        
        # Create directories
        for dir_path in [self.raw_dir, self.processed_dir, self.results_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def fetch_and_save_raw_data(
        self,
        external_api_url: str,
        params: Optional[Dict] = None,
        save_filename: Optional[str] = None
    ) -> Dict:
        """
        Step 1: Fetch data từ external API và lưu raw
        
        Args:
            external_api_url: URL của external API
            params: Query parameters
            save_filename: Tên file để lưu (default: raw_YYYYMMDD_HHMMSS.json)
        
        Returns:
            Dict với file path và số records
        """
        logger.info("📥 Step 1: Fetching data from external API...")
        
        try:
            import requests
            
            # Fetch data
            response = requests.get(external_api_url, params=params, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            
            # Generate filename
            if not save_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_filename = f"raw_{timestamp}.json"
            
            # Save raw data
            raw_file = self.raw_dir / save_filename
            with open(raw_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # Get record count
            if isinstance(data, list):
                record_count = len(data)
            elif isinstance(data, dict):
                record_count = len(data.get('data', []))
            else:
                record_count = 0
            
            logger.info(f"   ✅ Saved {record_count} records to {raw_file}")
            
            return {
                "status": "success",
                "raw_file": str(raw_file),
                "record_count": record_count
            }
            
        except Exception as e:
            logger.error(f"   ❌ Failed to fetch data: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def sync_from_database_to_raw(
        self,
        limit: Optional[int] = None,
        save_filename: Optional[str] = None
    ) -> Dict:
        """
        Step 1b: Export data từ database sang raw file
        
        Args:
            limit: Số records tối đa
            save_filename: Tên file để lưu
        
        Returns:
            Dict với file path và số records
        """
        logger.info("📥 Step 1b: Exporting data from database to raw file...")
        
        try:
            # Query articles
            query = text("""
                SELECT 
                    id, title, content, url, source,
                    published_at, created_at, category
                FROM articles
                WHERE content IS NOT NULL
                ORDER BY created_at DESC
                LIMIT :limit
            """)
            
            rows = self.db.execute(query, {"limit": limit or 999999}).fetchall()
            
            if not rows:
                logger.warning("   No articles found in database")
                return {
                    "status": "error",
                    "message": "No articles found"
                }
            
            # Convert to dict
            articles = []
            for row in rows:
                articles.append({
                    "id": row[0],
                    "title": row[1],
                    "content": row[2],
                    "url": row[3],
                    "source": row[4],
                    "published_at": row[5].isoformat() if row[5] else None,
                    "created_at": row[6].isoformat() if row[6] else None,
                    "category": row[7]
                })
            
            # Generate filename
            if not save_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_filename = f"raw_from_db_{timestamp}.json"
            
            # Save raw data
            raw_file = self.raw_dir / save_filename
            with open(raw_file, 'w', encoding='utf-8') as f:
                json.dump(articles, f, ensure_ascii=False, indent=2)
            
            logger.info(f"   ✅ Exported {len(articles)} articles to {raw_file}")
            
            return {
                "status": "success",
                "raw_file": str(raw_file),
                "record_count": len(articles)
            }
            
        except Exception as e:
            logger.error(f"   ❌ Failed to export data: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def process_raw_data(
        self,
        raw_file: str,
        save_filename: Optional[str] = None
    ) -> Dict:
        """
        Step 2: Xử lý raw data → processed data
        
        Actions:
        - Normalize data structure
        - Clean text (remove HTML, special chars)
        - Extract metadata
        - Validate và filter
        
        Args:
            raw_file: Path to raw data file
            save_filename: Tên file processed (default: processed_YYYYMMDD_HHMMSS.json)
        
        Returns:
            Dict với processed file path và statistics
        """
        logger.info("🔧 Step 2: Processing raw data...")
        
        try:
            # Load raw data
            with open(raw_file, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            # Handle different formats
            if isinstance(raw_data, dict) and 'data' in raw_data:
                records = raw_data['data']
            elif isinstance(raw_data, list):
                records = raw_data
            else:
                records = [raw_data]
            
            logger.info(f"   Processing {len(records)} records...")
            
            # Process each record
            processed_records = []
            stats = {
                "total": len(records),
                "processed": 0,
                "skipped": 0,
                "errors": 0
            }
            
            for i, record in enumerate(records):
                try:
                    # Normalize structure
                    normalized, errors, warnings = self.normalizer.normalize_document(record)
                    
                    if errors:
                        stats["errors"] += 1
                        logger.debug(f"   Record {i}: {len(errors)} errors")
                        continue
                    
                    # Clean text
                    if normalized.get('content'):
                        cleaned_content = self.cleaner.clean(normalized['content'])
                        normalized['content_cleaned'] = cleaned_content
                        normalized['content_length'] = len(cleaned_content)
                    
                    if normalized.get('title'):
                        cleaned_title = self.cleaner.clean(normalized['title'])
                        normalized['title_cleaned'] = cleaned_title
                    
                    # Add processing metadata
                    normalized['processed_at'] = datetime.now().isoformat()
                    normalized['processing_warnings'] = warnings
                    
                    # Validate minimum requirements (giảm từ 50 xuống 20 chars để lấy nhiều posts hơn)
                    if not normalized.get('content_cleaned') or len(normalized['content_cleaned']) < 20:
                        stats["skipped"] += 1
                        continue
                    
                    processed_records.append(normalized)
                    stats["processed"] += 1
                    
                except Exception as e:
                    logger.debug(f"   Failed to process record {i}: {e}")
                    stats["errors"] += 1
            
            # Generate filename
            if not save_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_filename = f"processed_{timestamp}.json"
            
            # Save processed data
            processed_file = self.processed_dir / save_filename
            
            # Convert datetime objects to ISO strings for JSON serialization
            def convert_datetime(obj):
                """Convert datetime objects to ISO strings"""
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: convert_datetime(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_datetime(item) for item in obj]
                return obj
            
            processed_records_serializable = convert_datetime(processed_records)
            
            with open(processed_file, 'w', encoding='utf-8') as f:
                json.dump(processed_records_serializable, f, ensure_ascii=False, indent=2)
            
            logger.info(f"   ✅ Processed {stats['processed']}/{stats['total']} records")
            logger.info(f"   💾 Saved to {processed_file}")
            
            return {
                "status": "success",
                "processed_file": str(processed_file),
                "statistics": stats
            }
            
        except Exception as e:
            logger.error(f"   ❌ Failed to process data: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def load_processed_data_to_db(
        self,
        processed_file: str,
        update_existing: bool = False
    ) -> Dict:
        """
        Step 3: Load processed data vào database
        
        Args:
            processed_file: Path to processed file
            update_existing: Update nếu đã tồn tại (based on URL)
        
        Returns:
            Dict với statistics
        """
        logger.info("💾 Step 3: Loading processed data to database...")
        
        try:
            # Load processed data
            with open(processed_file, 'r', encoding='utf-8') as f:
                processed_data = json.load(f)
            
            logger.info(f"   Loading {len(processed_data)} records...")
            
            stats = {
                "total": len(processed_data),
                "inserted": 0,
                "updated": 0,
                "skipped": 0
            }
            
            for record in processed_data:
                try:
                    url = record.get('url')
                    
                    # Check if exists
                    if url:
                        existing = self.db.execute(
                            text("SELECT id FROM articles WHERE url = :url"),
                            {"url": url}
                        ).fetchone()
                        
                        if existing:
                            if update_existing:
                                # Update
                                update_query = text("""
                                    UPDATE articles
                                    SET title = :title,
                                        content = :content,
                                        category = :category,
                                        updated_at = NOW()
                                    WHERE url = :url
                                """)
                                self.db.execute(update_query, {
                                    "title": record.get('title_cleaned', record.get('title')),
                                    "content": record.get('content_cleaned', record.get('content')),
                                    "category": record.get('category'),
                                    "url": url
                                })
                                self.db.commit()  # Commit per record
                                stats["updated"] += 1
                            else:
                                stats["skipped"] += 1
                            continue
                    
                    # Insert new - với đầy đủ fields
                    metadata = record.get('metadata', {})
                    
                    # Convert datetime to Unix timestamp
                    def to_unix(dt_str):
                        if not dt_str:
                            return None
                        try:
                            from datetime import datetime
                            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                            return dt.timestamp()
                        except:
                            return None
                    
                    insert_query = text("""
                        INSERT INTO articles (
                            title, content, url, source, source_type, domain, category,
                            published_datetime, published_date, created_at, updated_at,
                            likes_count, shares_count, comments_count, reactions,
                            social_platform, account_name, account_id, post_id, post_type,
                            word_count, raw_metadata
                        )
                        VALUES (
                            :title, :content, :url, :source, :source_type, :domain, :category,
                            :published_datetime, :published_date, :created_at, :updated_at,
                            :likes_count, :shares_count, :comments_count, :reactions,
                            :social_platform, :account_name, :account_id, :post_id, :post_type,
                            :word_count, :raw_metadata
                        )
                    """)
                    
                    reactions = metadata.get('reactions', {})
                    
                    self.db.execute(insert_query, {
                        "title": record.get('title_cleaned', record.get('title')),
                        "content": record.get('content_cleaned', record.get('content')),
                        "url": url,
                        "source": record.get('source', 'external'),
                        "source_type": record.get('source_type', 'facebook'),
                        "domain": record.get('domain'),
                        "category": metadata.get('category'),
                        "published_datetime": record.get('published_at'),
                        "published_date": to_unix(record.get('published_at')),
                        "created_at": to_unix(record.get('created_at')),
                        "updated_at": to_unix(record.get('updated_at')),
                        "likes_count": reactions.get('like', 0),
                        "shares_count": metadata.get('shares_count', 0),
                        "comments_count": metadata.get('comments_count', 0),
                        "reactions": json.dumps(reactions) if reactions else None,
                        "social_platform": record.get('platform', 'facebook'),
                        "account_name": metadata.get('author_name'),
                        "account_id": metadata.get('author_id'),
                        "post_id": metadata.get('post_id'),
                        "post_type": metadata.get('post_type'),
                        "word_count": record.get('content_length'),
                        "raw_metadata": json.dumps(metadata)
                    })
                    self.db.commit()  # Commit per record
                    stats["inserted"] += 1
                    
                except Exception as e:
                    logger.error(f"   Failed to load record: {e}")
                    logger.error(f"   Record URL: {record.get('url')}")
                    self.db.rollback()  # Rollback chỉ record này
                    continue
            
            logger.info(f"   ✅ Inserted: {stats['inserted']}, Updated: {stats['updated']}, Skipped: {stats['skipped']}")
            
            return {
                "status": "success",
                "statistics": stats
            }
            
        except Exception as e:
            logger.error(f"   ❌ Failed to load data: {e}")
            self.db.rollback()
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_processed_data_for_training(
        self,
        processed_file: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Dict:
        """
        Step 4: Load processed data cho training
        
        Args:
            processed_file: Path to specific file (None = latest)
            limit: Số records tối đa
        
        Returns:
            Dict với documents và metadata
        """
        logger.info("📚 Loading processed data for training...")
        
        try:
            # Find file
            if not processed_file:
                # Get latest processed file
                processed_files = sorted(self.processed_dir.glob("processed_*.json"))
                if not processed_files:
                    return {
                        "status": "error",
                        "message": "No processed files found"
                    }
                processed_file = processed_files[-1]
            
            # Load data
            with open(processed_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Apply limit
            if limit:
                data = data[:limit]
            
            # Prepare documents
            documents = []
            metadata = []
            
            for record in data:
                # Combine title + content
                title = record.get('title_cleaned', record.get('title', ''))
                content = record.get('content_cleaned', record.get('content', ''))
                
                doc = f"{title}\n{content}"
                documents.append(doc)
                
                # Save metadata
                metadata.append({
                    "id": record.get('id'),
                    "title": title,
                    "url": record.get('url'),
                    "source": record.get('source_type'),
                    "category": record.get('category'),
                    "length": len(content)
                })
            
            logger.info(f"   ✅ Loaded {len(documents)} documents from {processed_file}")
            
            return {
                "status": "success",
                "documents": documents,
                "metadata": metadata,
                "source_file": str(processed_file)
            }
            
        except Exception as e:
            logger.error(f"   ❌ Failed to load training data: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


def get_data_pipeline(db: Session) -> DataPipelineService:
    """Get data pipeline instance"""
    return DataPipelineService(db)
