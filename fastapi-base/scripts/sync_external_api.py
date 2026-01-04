#!/usr/bin/env python3
"""
🔄 SYNC DATA TỪ API BÊN NGOÀI

Script để lấy data từ API bên ngoài (http://192.168.30.28:8000)
và tự động xử lý qua hệ thống Topic Service

Flow:
1. Kết nối tới API nguồn (192.168.30.28:8000)
2. Lấy danh sách articles/posts
3. Transform sang format chuẩn
4. Gọi API /ingest để xử lý tự động:
   - Normalize & validate
   - Phân tích sentiment (15 sắc thái)
   - Phân loại danh mục (12 categories)
   - Lưu DB + Cập nhật thống kê

Usage:
    python sync_external_api.py
    python sync_external_api.py --endpoint articles --limit 100
    python sync_external_api.py --batch-size 50 --interval 300
"""

import requests
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
import argparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# CONFIGURATION
# ============================================

# API nguồn (BE bên ngoài)
SOURCE_API_BASE = "http://192.168.30.28:8000"
SOURCE_API_ENDPOINTS = {
    "articles": "/api/articles",           # Có thể là /articles, /posts, /data
    "posts": "/api/posts",
    "news": "/api/news",
}

# API đích (Topic Service - hệ thống này)
TARGET_API_BASE = "http://localhost:7777"
TARGET_INGEST_ENDPOINT = f"{TARGET_API_BASE}/api/v1/topics/ingest"

# Sync config
DEFAULT_BATCH_SIZE = 20  # Gửi 20 documents/lần
DEFAULT_LIMIT = None     # None = lấy hết
DEFAULT_INTERVAL = 0     # 0 = không sleep giữa các batch


# ============================================
# HELPER FUNCTIONS
# ============================================

def fetch_from_source_api(
    endpoint: str,
    limit: Optional[int] = None,
    offset: int = 0,
    params: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Lấy data từ API nguồn
    
    Args:
        endpoint: Tên endpoint (articles, posts, news)
        limit: Số lượng tối đa
        offset: Offset cho pagination
        params: Query parameters thêm
    
    Returns:
        Response JSON từ API
    """
    url = f"{SOURCE_API_BASE}{SOURCE_API_ENDPOINTS.get(endpoint, endpoint)}"
    
    # Build query params
    query_params = params or {}
    if limit:
        query_params['limit'] = limit
    if offset:
        query_params['offset'] = offset
    
    logger.info(f"📡 Fetching from {url} (limit={limit}, offset={offset})")
    
    try:
        response = requests.get(url, params=query_params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Log kết quả
        if isinstance(data, dict):
            count = len(data.get('data', data.get('items', [])))
            total = data.get('total', count)
            logger.info(f"✅ Fetched {count}/{total} items")
        elif isinstance(data, list):
            logger.info(f"✅ Fetched {len(data)} items")
        
        return data
    
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Failed to fetch from {url}: {e}")
        raise


def transform_document(raw_doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform document từ API nguồn sang format chuẩn cho /ingest
    
    Điều chỉnh logic này dựa vào cấu trúc data thực tế của API nguồn
    
    Args:
        raw_doc: Document gốc từ API nguồn
    
    Returns:
        Document đã transform theo format IngestRequest
    """
    # Detect các field phổ biến
    content = (
        raw_doc.get('content') or 
        raw_doc.get('body') or 
        raw_doc.get('text') or 
        raw_doc.get('description') or
        ""
    )
    
    url = (
        raw_doc.get('url') or 
        raw_doc.get('link') or 
        raw_doc.get('source_url') or
        raw_doc.get('id', f"doc_{hash(str(raw_doc))}")
    )
    
    title = (
        raw_doc.get('title') or 
        raw_doc.get('headline') or
        content[:100] if content else "Untitled"
    )
    
    # Parse published date
    published = raw_doc.get('published_date') or raw_doc.get('created_at') or raw_doc.get('date')
    
    # Extract engagement data
    engagement = {}
    if 'likes' in raw_doc or 'likes_count' in raw_doc:
        engagement['likes'] = raw_doc.get('likes') or raw_doc.get('likes_count', 0)
    if 'shares' in raw_doc or 'shares_count' in raw_doc:
        engagement['shares'] = raw_doc.get('shares') or raw_doc.get('shares_count', 0)
    if 'comments' in raw_doc or 'comments_count' in raw_doc:
        engagement['comments'] = raw_doc.get('comments') or raw_doc.get('comments_count', 0)
    if 'views' in raw_doc or 'views_count' in raw_doc:
        engagement['views'] = raw_doc.get('views') or raw_doc.get('views_count', 0)
    if 'reactions' in raw_doc:
        engagement['reactions'] = raw_doc.get('reactions')
    
    # Extract social account
    social_account = {}
    if 'social_platform' in raw_doc or 'platform' in raw_doc:
        social_account['platform'] = raw_doc.get('social_platform') or raw_doc.get('platform')
    if 'account_name' in raw_doc:
        social_account['account_name'] = raw_doc.get('account_name')
    if 'account_id' in raw_doc:
        social_account['account_id'] = raw_doc.get('account_id')
    
    # Extract location
    location = {}
    if 'province' in raw_doc:
        location['province'] = raw_doc.get('province')
    if 'district' in raw_doc:
        location['district'] = raw_doc.get('district')
    if 'location' in raw_doc and isinstance(raw_doc['location'], dict):
        location = raw_doc['location']
    
    # Build metadata
    metadata = {
        "title": title,
        "published": published,
        "author": raw_doc.get('author'),
        "category": raw_doc.get('category'),
        "tags": raw_doc.get('tags'),
        "images": raw_doc.get('images'),
        "description": raw_doc.get('description'),
        "language": raw_doc.get('language', 'vi'),
    }
    
    # Add engagement if exists
    if engagement:
        metadata['engagement'] = engagement
    
    # Add social account if exists
    if social_account:
        metadata['social_account'] = social_account
    
    # Add location if exists
    if location:
        metadata['location'] = location
    
    # Add extra fields
    for key in ['post_id', 'post_type', 'location_text']:
        if key in raw_doc:
            metadata[key] = raw_doc[key]
    
    # Detect source type
    source_type = "web"  # Default
    if 'facebook.com' in url or social_account.get('platform') == 'facebook':
        source_type = "facebook"
    elif 'youtube.com' in url or social_account.get('platform') == 'youtube':
        source_type = "youtube"
    elif 'tiktok.com' in url or social_account.get('platform') == 'tiktok':
        source_type = "tiktok"
    elif raw_doc.get('source_type'):
        source_type = raw_doc['source_type']
    
    # Return transformed document
    return {
        "source": source_type,
        "source_id": url,
        "content": content,
        "metadata": metadata
    }


def send_to_ingest_api(
    documents: List[Dict[str, Any]],
    skip_duplicates: bool = True,
    analyze_sentiment: bool = True
) -> Dict[str, Any]:
    """
    Gửi documents tới API /ingest để xử lý
    
    Args:
        documents: Danh sách documents đã transform
        skip_duplicates: Bỏ qua duplicate URLs
        analyze_sentiment: Phân tích sentiment
    
    Returns:
        Response từ /ingest API
    """
    payload = {
        "documents": documents,
        "skip_duplicates": skip_duplicates,
        "analyze_sentiment": analyze_sentiment
    }
    
    logger.info(f"📤 Sending {len(documents)} documents to {TARGET_INGEST_ENDPOINT}")
    
    try:
        response = requests.post(
            TARGET_INGEST_ENDPOINT,
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        result = response.json()
        
        # Log kết quả
        logger.info(f"✅ Ingest result: "
                   f"saved={result.get('saved')}, "
                   f"skipped={result.get('skipped')}, "
                   f"sentiment={result.get('sentiment_analyzed')}")
        
        if result.get('stats_updated'):
            logger.info(f"📊 Stats updated: {result['stats_updated']}")
        if result.get('trends_updated'):
            logger.info(f"📈 Trends updated: {result['trends_updated']}")
        
        return result
    
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Failed to send to ingest API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response: {e.response.text}")
        raise


def sync_data(
    endpoint: str = "articles",
    limit: Optional[int] = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    interval: int = DEFAULT_INTERVAL,
    skip_duplicates: bool = True,
    analyze_sentiment: bool = True
):
    """
    Sync data từ API nguồn sang hệ thống Topic Service
    
    Args:
        endpoint: Endpoint để lấy data (articles, posts, news)
        limit: Số lượng tối đa (None = all)
        batch_size: Số documents gửi mỗi lần
        interval: Delay giữa các batch (seconds)
        skip_duplicates: Bỏ qua duplicates
        analyze_sentiment: Phân tích sentiment
    """
    logger.info(f"🚀 Starting sync from {SOURCE_API_BASE}")
    logger.info(f"   Endpoint: {endpoint}")
    logger.info(f"   Limit: {limit or 'ALL'}")
    logger.info(f"   Batch size: {batch_size}")
    logger.info(f"   Interval: {interval}s")
    
    total_fetched = 0
    total_saved = 0
    total_skipped = 0
    total_sentiment = 0
    offset = 0
    
    start_time = time.time()
    
    try:
        while True:
            # Tính limit cho request này
            fetch_limit = batch_size
            if limit:
                remaining = limit - total_fetched
                if remaining <= 0:
                    break
                fetch_limit = min(batch_size, remaining)
            
            # Fetch từ API nguồn
            try:
                data = fetch_from_source_api(
                    endpoint=endpoint,
                    limit=fetch_limit,
                    offset=offset
                )
            except Exception as e:
                logger.error(f"Failed to fetch: {e}")
                break
            
            # Extract documents từ response
            if isinstance(data, dict):
                raw_docs = data.get('data', data.get('items', data.get('results', [])))
                has_more = data.get('has_more', False)
                total = data.get('total', 0)
            elif isinstance(data, list):
                raw_docs = data
                has_more = len(raw_docs) == fetch_limit
                total = None
            else:
                logger.warning(f"Unexpected response format: {type(data)}")
                break
            
            # Kiểm tra có data không
            if not raw_docs:
                logger.info("✅ No more data to fetch")
                break
            
            # Transform documents
            logger.info(f"🔄 Transforming {len(raw_docs)} documents...")
            transformed_docs = []
            for raw_doc in raw_docs:
                try:
                    transformed = transform_document(raw_doc)
                    transformed_docs.append(transformed)
                except Exception as e:
                    logger.warning(f"Failed to transform document: {e}")
            
            if not transformed_docs:
                logger.warning("No valid documents after transformation")
                break
            
            # Gửi tới ingest API
            try:
                result = send_to_ingest_api(
                    documents=transformed_docs,
                    skip_duplicates=skip_duplicates,
                    analyze_sentiment=analyze_sentiment
                )
                
                # Cập nhật counters
                total_saved += result.get('saved', 0)
                total_skipped += result.get('skipped', 0)
                total_sentiment += result.get('sentiment_analyzed', 0)
                
            except Exception as e:
                logger.error(f"Failed to ingest batch: {e}")
                # Continue với batch tiếp theo
            
            # Update progress
            total_fetched += len(raw_docs)
            offset += len(raw_docs)
            
            logger.info(f"📊 Progress: fetched={total_fetched}, saved={total_saved}, "
                       f"skipped={total_skipped}, sentiment={total_sentiment}")
            
            # Check xem còn data không
            if not has_more or (limit and total_fetched >= limit):
                break
            
            # Sleep giữa các batch (nếu có)
            if interval > 0:
                logger.info(f"⏳ Sleeping {interval}s before next batch...")
                time.sleep(interval)
        
        # Summary
        elapsed = time.time() - start_time
        logger.info("=" * 60)
        logger.info(f"✅ SYNC COMPLETED")
        logger.info(f"   Total fetched: {total_fetched}")
        logger.info(f"   Total saved: {total_saved}")
        logger.info(f"   Total skipped: {total_skipped}")
        logger.info(f"   Sentiment analyzed: {total_sentiment}")
        logger.info(f"   Time elapsed: {elapsed:.2f}s")
        logger.info(f"   Rate: {total_fetched/elapsed:.2f} docs/s")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.info("\n⚠️  Sync interrupted by user")
    except Exception as e:
        logger.error(f"❌ Sync failed: {e}", exc_info=True)


# ============================================
# CLI
# ============================================

def main():
    parser = argparse.ArgumentParser(
        description="Sync data từ API bên ngoài vào Topic Service"
    )
    
    parser.add_argument(
        "--endpoint",
        default="articles",
        help="Endpoint để lấy data (articles, posts, news)"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Số lượng documents tối đa (None = all)"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Số documents gửi mỗi lần (default: {DEFAULT_BATCH_SIZE})"
    )
    
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL,
        help=f"Delay giữa các batch (seconds, default: {DEFAULT_INTERVAL})"
    )
    
    parser.add_argument(
        "--no-skip-duplicates",
        action="store_true",
        help="Không bỏ qua duplicates"
    )
    
    parser.add_argument(
        "--no-sentiment",
        action="store_true",
        help="Không phân tích sentiment"
    )
    
    parser.add_argument(
        "--source-api",
        default=SOURCE_API_BASE,
        help=f"Base URL của API nguồn (default: {SOURCE_API_BASE})"
    )
    
    parser.add_argument(
        "--target-api",
        default=TARGET_API_BASE,
        help=f"Base URL của Topic Service (default: {TARGET_API_BASE})"
    )
    
    args = parser.parse_args()
    
    # Update global config
    global SOURCE_API_BASE, TARGET_API_BASE, TARGET_INGEST_ENDPOINT
    SOURCE_API_BASE = args.source_api
    TARGET_API_BASE = args.target_api
    TARGET_INGEST_ENDPOINT = f"{TARGET_API_BASE}/api/v1/topics/ingest"
    
    # Run sync
    sync_data(
        endpoint=args.endpoint,
        limit=args.limit,
        batch_size=args.batch_size,
        interval=args.interval,
        skip_duplicates=not args.no_skip_duplicates,
        analyze_sentiment=not args.no_sentiment
    )


if __name__ == "__main__":
    main()
