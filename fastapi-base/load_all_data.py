#!/usr/bin/env python3
"""
Load All Data with Proper Pagination
Fetches all 7692 posts from external API using page-based pagination
"""

import requests
import time
from typing import Dict, Any, List

# API Configuration
SOURCE_API = "http://192.168.30.28:8000"
POSTS_ENDPOINT = "/api/v1/posts"
TARGET_API = "http://localhost:7777"
INGEST_ENDPOINT = "/topic-service/ingest"

# Pagination settings (from external API metadata)
PAGE_SIZE = 10  # External API returns 10 items per page
TOTAL_POSTS = 7692
TOTAL_PAGES = (TOTAL_POSTS + PAGE_SIZE - 1) // PAGE_SIZE  # 770 pages

# Rate limiting
DELAY_BETWEEN_PAGES = 0.5  # seconds
BATCH_SIZE = 50  # Send to ingest every N pages


def fetch_page(page: int) -> Dict[str, Any]:
    """Fetch a single page from external API"""
    url = f"{SOURCE_API}{POSTS_ENDPOINT}"
    params = {"page": page, "page_size": PAGE_SIZE}
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching page {page}: {e}")
        return None


def transform_post(post: Dict[str, Any]) -> Dict[str, Any]:
    """Transform post from external API to ingest format"""
    return {
        "url": post.get("url", ""),
        "title": post.get("title", ""),
        "content": post.get("content", ""),
        "published_date": post.get("published_date"),
        "source": post.get("source", "unknown"),
        "author": post.get("author"),
        "category": post.get("category"),
        "tags": post.get("tags", []),
        "image_url": post.get("image_url"),
        "metadata": post.get("metadata", {})
    }


def send_to_ingest(documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Send batch of documents to ingest API"""
    url = f"{TARGET_API}{INGEST_ENDPOINT}"
    payload = {
        "documents": documents,
        "skip_duplicates": True,
        "analyze_sentiment": True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error sending to ingest: {e}")
        return {"saved": 0, "skipped": 0, "error": str(e)}


def main():
    """Main function to load all data"""
    print("=" * 60)
    print("📥 LOADING ALL DATA WITH PAGINATION")
    print("=" * 60)
    print(f"Source API: {SOURCE_API}")
    print(f"Total posts: {TOTAL_POSTS}")
    print(f"Total pages: {TOTAL_PAGES}")
    print(f"Page size: {PAGE_SIZE}")
    print("=" * 60)
    
    total_fetched = 0
    total_saved = 0
    total_skipped = 0
    batch_buffer = []
    
    start_time = time.time()
    
    for page in range(1, TOTAL_PAGES + 1):
        print(f"\n📄 Fetching page {page}/{TOTAL_PAGES}...", end=" ")
        
        # Fetch page
        response = fetch_page(page)
        if not response:
            print("⚠️  Failed, skipping...")
            continue
        
        # Extract posts
        posts = response.get("data", [])
        metadata = response.get("metadata", {})
        
        if not posts:
            print("⚠️  No posts found")
            continue
        
        print(f"✓ Got {len(posts)} posts")
        total_fetched += len(posts)
        
        # Transform posts
        transformed = []
        for post in posts:
            try:
                transformed.append(transform_post(post))
            except Exception as e:
                print(f"  ⚠️  Transform error: {e}")
        
        # Add to batch buffer
        batch_buffer.extend(transformed)
        
        # Send batch when buffer is full
        if len(batch_buffer) >= BATCH_SIZE:
            print(f"  💾 Sending batch of {len(batch_buffer)} documents...", end=" ")
            result = send_to_ingest(batch_buffer)
            saved = result.get("saved", 0)
            skipped = result.get("skipped", 0)
            total_saved += saved
            total_skipped += skipped
            print(f"✓ Saved: {saved}, Skipped: {skipped}")
            batch_buffer = []
        
        # Progress update
        if page % 10 == 0:
            elapsed = time.time() - start_time
            rate = total_fetched / elapsed if elapsed > 0 else 0
            remaining = TOTAL_PAGES - page
            eta = remaining / (page / elapsed) if page > 0 else 0
            print(f"\n📊 Progress: {page}/{TOTAL_PAGES} pages ({page/TOTAL_PAGES*100:.1f}%)")
            print(f"   Fetched: {total_fetched}, Saved: {total_saved}, Skipped: {total_skipped}")
            print(f"   Rate: {rate:.1f} posts/sec, ETA: {eta/60:.1f} minutes")
        
        # Rate limiting
        time.sleep(DELAY_BETWEEN_PAGES)
    
    # Send remaining documents
    if batch_buffer:
        print(f"\n💾 Sending final batch of {len(batch_buffer)} documents...", end=" ")
        result = send_to_ingest(batch_buffer)
        saved = result.get("saved", 0)
        skipped = result.get("skipped", 0)
        total_saved += saved
        total_skipped += skipped
        print(f"✓ Saved: {saved}, Skipped: {skipped}")
    
    # Final summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("✅ LOADING COMPLETED")
    print("=" * 60)
    print(f"Total fetched: {total_fetched}/{TOTAL_POSTS}")
    print(f"Total saved: {total_saved}")
    print(f"Total skipped: {total_skipped}")
    print(f"Time elapsed: {elapsed/60:.1f} minutes")
    print(f"Average rate: {total_fetched/elapsed:.1f} posts/sec")
    print("=" * 60)


if __name__ == "__main__":
    main()
