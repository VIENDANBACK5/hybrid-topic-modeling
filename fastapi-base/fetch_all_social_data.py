#!/usr/bin/env python3
"""
Fetch ALL social media data (Facebook, Threads, TikTok) và load vào articles table
"""

import requests
import json
from datetime import datetime
from pathlib import Path

EXTERNAL_API = "http://192.168.30.28:8000"
LOCAL_API = "http://localhost:7777"

def fetch_by_type(post_type, description):
    """Fetch all posts của 1 loại"""
    print(f"\n{'='*70}")
    print(f"📥 FETCHING {description.upper()} DATA")
    print(f"{'='*70}")
    
    page = 1
    page_size = 100
    all_posts = []
    
    while True:
        url = f"{EXTERNAL_API}/api/v1/posts/by-type/{post_type}?page={page}&page_size={page_size}"
        response = requests.get(url, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            break
            
        data = response.json()
        posts = data.get('data', [])
        
        if not posts:
            break
            
        all_posts.extend(posts)
        print(f"   Page {page}: {len(posts)} posts (total: {len(all_posts)})")
        
        # Check if last page
        metadata = data.get('metadata', {})
        if len(posts) < page_size or len(all_posts) >= metadata.get('total', 0):
            break
            
        page += 1
    
    print(f"\n✅ Fetched: {len(all_posts)} {description} posts")
    return all_posts

def main():
    print("\n" + "="*70)
    print("🎯 FETCH ALL SOCIAL MEDIA DATA")
    print("="*70)
    
    # Fetch all types
    all_data = {}
    
    # 1. Facebook
    fb_posts = fetch_by_type("facebook", "Facebook")
    all_data['facebook'] = fb_posts
    
    # 2. Threads
    threads_posts = fetch_by_type("threads", "Threads")
    all_data['threads'] = threads_posts
    
    # 3. TikTok
    tiktok_posts = fetch_by_type("tiktok", "TikTok")
    all_data['tiktok'] = tiktok_posts
    
    # Summary
    total = len(fb_posts) + len(threads_posts) + len(tiktok_posts)
    print(f"\n{'='*70}")
    print(f"📊 SUMMARY")
    print(f"{'='*70}")
    print(f"   Facebook: {len(fb_posts)} posts")
    print(f"   Threads:  {len(threads_posts)} posts")
    print(f"   TikTok:   {len(tiktok_posts)} posts")
    print(f"   ─────────────────────────────")
    print(f"   Total:    {total} posts")
    
    # Save raw backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_file = f"data/raw/all_social_raw_{timestamp}.json"
    
    Path(raw_file).parent.mkdir(parents=True, exist_ok=True)
    with open(raw_file, 'w', encoding='utf-8') as f:
        json.dump({
            'facebook': fb_posts,
            'threads': threads_posts,
            'tiktok': tiktok_posts,
            'total': total,
            'fetched_at': timestamp
        }, f, ensure_ascii=False, indent=2)
    
    file_size = Path(raw_file).stat().st_size / 1024
    print(f"\n💾 Raw backup: {raw_file} ({file_size:.1f} KB)")
    
    # Process all data
    print(f"\n{'='*70}")
    print(f"🔧 PROCESSING DATA")
    print(f"{'='*70}")
    
    process_url = f"{LOCAL_API}/api/data/process"
    response = requests.post(
        process_url,
        json={"raw_file": raw_file},
        headers={"Content-Type": "application/json"},
        timeout=300
    )
    
    if response.status_code == 200:
        result = response.json()
        stats = result.get('statistics', {})
        processed_file = result.get('processed_file', '')
        
        print(f"✅ Processed: {stats.get('processed', 0)}/{stats.get('total', 0)}")
        print(f"   Skipped: {stats.get('skipped', 0)} (content too short)")
        print(f"   Errors: {stats.get('errors', 0)}")
        print(f"   File: {processed_file}")
        
        # Load to DB
        print(f"\n{'='*70}")
        print(f"💾 LOADING TO DATABASE")
        print(f"{'='*70}")
        
        load_url = f"{LOCAL_API}/api/data/load-to-db"
        load_response = requests.post(
            load_url,
            json={
                "processed_file": processed_file,
                "update_existing": True
            },
            headers={"Content-Type": "application/json"},
            timeout=300
        )
        
        if load_response.status_code == 200:
            load_result = load_response.json()
            load_stats = load_result.get('result', {}).get('statistics', {})
            
            print(f"✅ Loaded to database!")
            print(f"   Inserted: {load_stats.get('inserted', 0)} records")
            print(f"   Updated: {load_stats.get('updated', 0)} records")
            print(f"   Skipped: {load_stats.get('skipped', 0)} (duplicates)")
            
            # Final summary
            print(f"\n{'='*70}")
            print(f"✅ COMPLETED!")
            print(f"{'='*70}")
            print(f"""
📊 FINAL SUMMARY:
   • Fetched: {total} posts (FB: {len(fb_posts)}, Threads: {len(threads_posts)}, TikTok: {len(tiktok_posts)})
   • Processed: {stats.get('processed', 0)} valid posts
   • Loaded to DB: {load_stats.get('inserted', 0)} new + {load_stats.get('updated', 0)} updated
   
📂 FILES:
   • Raw: {raw_file}
   • Processed: {processed_file}
   
🎯 Next: Train BERTopic với tất cả data
   curl -X POST http://localhost:7777/api/topics/train \\
     -H 'Content-Type: application/json' \\
     -d '{{"limit": null, "min_topic_size": 5, "use_vietnamese_tokenizer": true}}'
""")
        else:
            print(f"❌ Failed to load: {load_response.text}")
    else:
        print(f"❌ Processing failed: {response.text}")

if __name__ == "__main__":
    main()
