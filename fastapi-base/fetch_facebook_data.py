#!/usr/bin/env python3
"""
Fetch ALL Facebook data từ external API và process vào hệ thống
"""
import requests
import json
from datetime import datetime
from pathlib import Path
import time
from dotenv import load_dotenv
import os
load_dotenv()

# ============================================
# CONFIG
# ============================================
EXTERNAL_API = os.getenv("EXTERNAL_API_BASE_URL")
DATA_TYPE = "facebook"
PAGE_SIZE = 100  # Lấy 100 posts mỗi lần
LOCAL_API = os.getenv("LOCAL_API_BASE_URL")

# ============================================
# STEP 1: FETCH ALL FACEBOOK DATA
# ============================================
print("\n" + "="*70)
print("📥 STEP 1: FETCHING ALL FACEBOOK DATA FROM EXTERNAL API")
print("="*70)

all_posts = []
page = 1
total_fetched = 0

while True:
    print(f"\n📄 Fetching page {page}...")
    
    try:
        # Call external API
        url = f"{EXTERNAL_API}/api/v1/posts/by-type/{DATA_TYPE}"
        params = {
            "page": page,
            "page_size": PAGE_SIZE,
            "sort_by": "id",
            "order": "desc"
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Check if we got data (API returns 'data' not 'items')
        posts = data.get('data', [])
        if not posts:
            print(f"   ℹ️  No more data on page {page}")
            break
        
        all_posts.extend(posts)
        total_fetched += len(posts)
        
        print(f"   Got {len(posts)} posts (total: {total_fetched})")
        
        # Check if this is the last page
        metadata = data.get('metadata', {})
        total_records = metadata.get('total', 0)
        
        if total_fetched >= total_records:
            print(f"   ℹ️  Fetched all {total_records} records")
            break
        
        # If we got less than PAGE_SIZE, it's the last page
        if len(posts) < PAGE_SIZE:
            print(f"   ℹ️  Last page (got {len(posts)} < {PAGE_SIZE})")
            break
        
        page += 1
        time.sleep(0.1)  # Rate limiting
        
    except Exception as e:
        print(f"   Error on page {page}: {e}")
        break

print(f"\nTotal fetched: {total_fetched} Facebook posts")

if total_fetched == 0:
    print("No data fetched. Exiting.")
    exit(1)

# ============================================
# STEP 2: SAVE RAW DATA
# ============================================
print("\n" + "="*70)
print("💾 STEP 2: SAVING RAW DATA")
print("="*70)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
raw_dir = Path("data/raw")
raw_dir.mkdir(parents=True, exist_ok=True)

raw_file = raw_dir / f"raw_facebook_{timestamp}.json"

raw_data = {
    "source": "external_api",
    "api_url": f"{EXTERNAL_API}/api/v1/posts/by-type/{DATA_TYPE}",
    "data_type": DATA_TYPE,
    "fetched_at": timestamp,
    "total_records": len(all_posts),
    "data": all_posts
}

with open(raw_file, 'w', encoding='utf-8') as f:
    json.dump(raw_data, f, ensure_ascii=False, indent=2)

print(f"Saved to: {raw_file}")
print(f"   Size: {raw_file.stat().st_size / 1024:.2f} KB")

# ============================================
# STEP 3: PROCESS DATA
# ============================================
print("\n" + "="*70)
print("STEP 3: PROCESSING DATA")
print("="*70)

try:
    # Call local API to process
    process_url = f"{LOCAL_API}/api/data/process"
    payload = {
        "raw_file": str(raw_file),
        "validate": True
    }
    
    print(f"📤 Calling: POST {process_url}")
    response = requests.post(process_url, json=payload, timeout=300)
    response.raise_for_status()
    
    result = response.json()
    
    print(f"Processing completed!")
    print(f"   Valid records: {result.get('valid_count', 0)}")
    print(f"   Invalid records: {result.get('invalid_count', 0)}")
    print(f"   Processed file: {result.get('processed_file', 'N/A')}")
    
    processed_file = result.get('processed_file')
    
except Exception as e:
    print(f"Processing failed: {e}")
    print(f"   You can manually process later:")
    print(f"   curl -X POST '{LOCAL_API}/api/data/process' \\")
    print(f"     -H 'Content-Type: application/json' \\")
    print(f"     -d '{{\"raw_file\": \"{raw_file}\"}}'")
    processed_file = None

# ============================================
# STEP 4: LOAD TO DATABASE
# ============================================
if processed_file:
    print("\n" + "="*70)
    print("💽 STEP 4: LOADING TO DATABASE")
    print("="*70)
    
    try:
        load_url = f"{LOCAL_API}/api/data/load-to-db"
        payload = {
            "processed_file": processed_file,
            "update_existing": True
        }
        
        print(f"📤 Calling: POST {load_url}")
        response = requests.post(load_url, json=payload, timeout=300)
        response.raise_for_status()
        
        result = response.json()
        
        print(f"Loading completed!")
        print(f"   Inserted: {result.get('inserted', 0)}")
        print(f"   Updated: {result.get('updated', 0)}")
        print(f"   Skipped: {result.get('skipped', 0)}")
        
    except Exception as e:
        print(f"Loading failed: {e}")
        print(f"   You can manually load later:")
        print(f"   curl -X POST '{LOCAL_API}/api/data/load-to-db' \\")
        print(f"     -H 'Content-Type: application/json' \\")
        print(f"     -d '{{\"processed_file\": \"{processed_file}\"}}'")

# ============================================
# SUMMARY
# ============================================
print("\n" + "="*70)
print("COMPLETED!")
print("="*70)

print(f"""
SUMMARY:
   • Fetched: {total_fetched} Facebook posts
   • Raw file: {raw_file}
   • Processed file: {processed_file or 'N/A'}

NEXT STEPS:
   1. Run orchestrator pipeline to analyze:
      POST {LOCAL_API}/api/orchestrator/run-full-pipeline
   
   2. Or classify & sentiment only:
      POST {LOCAL_API}/api/orchestrator/quick-update

   3. Check database stats:
      GET {LOCAL_API}/api/v1/sync/db-stats

📚 DATA FLOW:
   External API → data/raw/ → data/processed/ → Database → Analysis
""")

print("="*70)
