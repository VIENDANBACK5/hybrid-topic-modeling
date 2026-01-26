#!/usr/bin/env python3
"""
WORKFLOW ĐƠN GIẢN: Fetch FB data → Processed JSON → Train trực tiếp
Bỏ qua bước load vào DB - Chỉ lưu processed JSON cho modeling
"""
import requests
import json
from datetime import datetime
from pathlib import Path
import time

EXTERNAL_API = "http://192.168.30.28:8548"
DATA_TYPE = "facebook"
PAGE_SIZE = 100
LOCAL_API = "http://localhost:7777"

print("\n" + "="*70)
print("SIMPLE WORKFLOW: API → PROCESSED JSON → TRAINING")
print("="*70)

# ============================================
# STEP 1: FETCH ALL DATA
# ============================================
print("\n📥 STEP 1: Fetching Facebook data...")

all_posts = []
page = 1

while True:
    url = f"{EXTERNAL_API}/api/v1/posts/by-type/{DATA_TYPE}"
    params = {"page": page, "page_size": PAGE_SIZE, "sort_by": "id", "order": "desc"}
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        posts = data.get('data', [])
        
        if not posts:
            break
        
        all_posts.extend(posts)
        print(f"   Page {page}: {len(posts)} posts (total: {len(all_posts)})")
        
        metadata = data.get('metadata', {})
        if len(all_posts) >= metadata.get('total', 0) or len(posts) < PAGE_SIZE:
            break
        
        page += 1
        time.sleep(0.1)
    except Exception as e:
        print(f"   Error: {e}")
        break

print(f"\nFetched: {len(all_posts)} posts")

if len(all_posts) == 0:
    print("No data. Exiting.")
    exit(1)

# ============================================
# STEP 2: SAVE RAW (Optional - for backup)
# ============================================
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
raw_dir = Path("data/raw")
raw_dir.mkdir(parents=True, exist_ok=True)

raw_file = raw_dir / f"raw_facebook_{timestamp}.json"
raw_data = {
    "source": "external_api",
    "data_type": DATA_TYPE,
    "fetched_at": timestamp,
    "total_records": len(all_posts),
    "data": all_posts
}

with open(raw_file, 'w', encoding='utf-8') as f:
    json.dump(raw_data, f, ensure_ascii=False, indent=2)

print(f"\n💾 Raw backup: {raw_file} ({raw_file.stat().st_size / 1024:.1f} KB)")

# ============================================
# STEP 3: PROCESS DATA
# ============================================
print("\nSTEP 3: Processing data...")

process_url = f"{LOCAL_API}/api/data/process"
payload = {"raw_file": str(raw_file)}

try:
    response = requests.post(process_url, json=payload, timeout=300)
    response.raise_for_status()
    result = response.json()
    
    stats = result.get('result', {}).get('statistics', {})
    processed_file = result.get('result', {}).get('processed_file')
    
    print(f"Processed: {stats.get('processed', 0)}/{stats.get('total', 0)}")
    print(f"   Skipped: {stats.get('skipped', 0)} (content too short)")
    print(f"   Errors: {stats.get('errors', 0)}")
    print(f"   File: {processed_file}")
    
except Exception as e:
    print(f"Processing failed: {e}")
    exit(1)

# ============================================
# STEP 4: LOAD TO ARTICLES TABLE
# ============================================
print("\n💾 STEP 4: Loading processed data to articles table...")

load_url = f"{LOCAL_API}/api/data/load-to-db"
load_payload = {
    "processed_file": processed_file,
    "update_existing": True  # Force update để refresh tất cả records
}

try:
    print(f"   📤 Calling: POST {load_url}")
    response = requests.post(load_url, json=load_payload, timeout=120)
    response.raise_for_status()
    load_result = response.json()
    
    print(f"Loaded to database!")
    print(f"   Loaded: {load_result.get('result', {}).get('statistics', {}).get('inserted', 0)} records")
    print(f"   Updated: {load_result.get('result', {}).get('statistics', {}).get('updated', 0)}")
    print(f"   Skipped: {load_result.get('result', {}).get('statistics', {}).get('skipped', 0)}")
    
except Exception as e:
    print(f"Warning: Failed to load to DB: {e}")
    print(f"   You can load manually later:")
    print(f"   curl -X POST '{LOCAL_API}/api/data/load-to-db' \\")
    print(f"     -H 'Content-Type: application/json' \\")
    print(f"     -d '{{\"processed_file\": \"{processed_file}\", \"update_existing\": false}}'")

# ============================================
# STEP 5: TRAIN BERTOPIC
# ============================================
print("\nSTEP 5: Training BERTopic from database...")

train_url = f"{LOCAL_API}/api/topics/train"
payload = {
    "limit": None,  # Use all from articles table
    "min_topic_size": 10,
    "use_vietnamese_tokenizer": True,
    "enable_topicgpt": True
}

try:
    print(f"   📤 Calling: POST {train_url}")
    response = requests.post(train_url, json=payload, timeout=600)
    response.raise_for_status()
    result = response.json()
    
    print(f"Training completed!")
    print(f"   Topics discovered: {result.get('num_topics', 0)}")
    print(f"   Documents processed: {result.get('num_documents', 0)}")
    print(f"   Session ID: {result.get('session_id', 'N/A')}")
    
except Exception as e:
    print(f"Training failed: {e}")
    print(f"   You can train manually later:")
    print(f"   curl -X POST '{LOCAL_API}/api/topics/train' \\")
    print(f"     -H 'Content-Type: application/json' \\")
    print(f"     -d '{{\"limit\": null}}'")

# ============================================
# SUMMARY
# ============================================
print("\n" + "="*70)
print("COMPLETED!")
print("="*70)

print(f"""
SUMMARY:
   • Fetched: {len(all_posts)} Facebook posts
   • Processed: {stats.get('processed', 0)} valid posts
   • Loaded to DB: articles table
   • Training: BERTopic completed
   
📂 FILES CREATED:
   • Raw backup: {raw_file}
   • Processed: {processed_file}
   
WORKFLOW:
   External API → Process → Load to articles → Train
   
TIP: Processed data now in articles table for:
   - Dashboard analytics
   - Database queries
   - Future model training
""")
