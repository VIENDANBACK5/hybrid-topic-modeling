"""
Extract economic and political statistics from important_posts using OpenRouter LLM API.
Focuses on: xã Thư Vũ and phường Trà Lý
"""
import os
import json
import argparse
import requests
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

# OpenRouter API Configuration
LLM_API_URL = os.getenv("LLM_API_URL", "https://openrouter.ai/api/v1/chat/completions")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
LLM_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", "")

TARGET_API_BASE = os.getenv("LOCAL_API_BASE_URL", "http://localhost:7777")
TARGET_LOCATIONS = ["xã Thư Vũ", "phường Trà Lý", "Thư Vũ", "Trà Lý"]


def call_llm(prompt: str) -> Optional[str]:
    """Call OpenRouter LLM API with proper headers."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LLM_API_KEY}",
        "HTTP-Referer": "https://pipeline.huye.vn",
        "X-Title": "Statistics Extraction"
    }
    
    try:
        response = requests.post(
            LLM_API_URL,
            headers=headers,
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": "Bạn là trợ lý trích xuất dữ liệu. Chỉ trả về JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 1000
            },
            timeout=60
        )
        
        if response.status_code != 200:
            print(f"  ✗ LLM API error {response.status_code}: {response.text[:150]}")
            return None
        
        result = response.json()
        content = result['choices'][0]['message']['content'].strip()
        
        # Extract JSON from markdown
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()
        
        return content
        
    except Exception as e:
        print(f"  ✗ LLM error: {e}")
        return None


def extract_economic_stats(post: Dict, location: str) -> Optional[Dict]:
    """Extract economic statistics using LLM."""
    content = post.get('content', '')[:3000]
    title = post.get('title', '')
    
    if not content:
        return None
    
    prompt = f"""Phân tích và trích xuất dữ liệu kinh tế cho "{location}":

TIÊU ĐỀ: {title}
NỘI DUNG: {content}

Trích xuất:
- Tổng giá trị sản xuất (tỷ đồng)
- Tốc độ tăng trưởng (%)
- Thu ngân sách (tỷ đồng)
- Hiệu suất thu NS (%)
- Năm

JSON format:
{{"found": true/false, "total_production_value": null, "growth_rate": null, "total_budget_revenue": null, "budget_collection_efficiency": null, "year": null, "period": null, "notes": null}}"""

    content_response = call_llm(prompt)
    if not content_response:
        return None
    
    try:
        data = json.loads(content_response)
        return data if data.get('found') else None
    except:
        return None


def extract_political_stats(post: Dict, location: str) -> Optional[Dict]:
    """Extract political statistics using LLM."""
    content = post.get('content', '')[:3000]
    title = post.get('title', '')
    
    if not content:
        return None
    
    prompt = f"""Phân tích và trích xuất thông tin Đảng bộ cho "{location}":

TIÊU ĐỀ: {title}
NỘI DUNG: {content}

Trích xuất:
- Số tổ chức Đảng
- Số Đảng viên
- Số chi bộ
- Năm

JSON format:
{{"found": true/false, "party_organization_count": null, "party_member_count": null, "party_size_description": null, "new_party_members": null, "party_cells_count": null, "year": null, "period": null, "notes": null}}"""

    content_response = call_llm(prompt)
    if not content_response:
        return None
    
    try:
        data = json.loads(content_response)
        return data if data.get('found') else None
    except:
        return None


def fetch_posts_for_locations(locations: List[str]) -> List[Dict]:
    """Fetch important posts mentioning target locations."""
    all_posts = []
    
    for loc in locations:
        try:
            response = requests.get(
                f"{TARGET_API_BASE}/api/important-posts/",
                params={'search': loc, 'limit': 100},
                timeout=30
            )
            
            if response.status_code == 200:
                posts = response.json().get('items', [])
                for post in posts:
                    post['detected_location'] = loc
                    all_posts.append(post)
        except Exception as e:
            print(f"Error fetching {loc}: {e}")
    
    # Deduplicate by ID
    seen = set()
    unique = []
    for p in all_posts:
        if p['id'] not in seen:
            seen.add(p['id'])
            unique.append(p)
    
    return unique


def save_economic_stats(stats: Dict, post_id: int, url: str, location: str) -> bool:
    """Save economic statistics via API."""
    payload = {
        "dvhc": location,
        "source_post_id": post_id,
        "source_url": url,
        **{k: v for k, v in stats.items() if k != 'found'},
        "extraction_metadata": json.dumps({"extracted_at": datetime.now().isoformat(), "model": LLM_MODEL})
    }
    
    try:
        response = requests.post(f"{TARGET_API_BASE}/api/statistics/economic", json=payload, timeout=30)
        return response.status_code in [200, 201]
    except:
        return False


def save_political_stats(stats: Dict, post_id: int, url: str, location: str) -> bool:
    """Save political statistics via API."""
    payload = {
        "dvhc": location,
        "source_post_id": post_id,
        "source_url": url,
        **{k: v for k, v in stats.items() if k != 'found'},
        "extraction_metadata": json.dumps({"extracted_at": datetime.now().isoformat(), "model": LLM_MODEL})
    }
    
    try:
        response = requests.post(f"{TARGET_API_BASE}/api/statistics/political", json=payload, timeout=30)
        return response.status_code in [200, 201]
    except:
        return False


def main():
    parser = argparse.ArgumentParser(description='Extract statistics using OpenRouter LLM')
    parser.add_argument('--type', choices=['economic', 'political', 'both'], default='both')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--limit', type=int, default=None)
    args = parser.parse_args()
    
    if not LLM_API_KEY:
        print("API KEY not set! Export OPENAI_API_KEY or OPENROUTER_API_KEY")
        print("   export OPENAI_API_KEY='sk-or-...'")
        return
    
    print("=" * 80)
    print("EXTRACTING STATISTICS WITH OPENROUTER")
    print("=" * 80)
    print(f"Model: {LLM_MODEL}")
    print(f"Type: {args.type}")
    print(f"Dry run: {args.dry_run}\n")
    
    posts = fetch_posts_for_locations(TARGET_LOCATIONS)
    print(f"Found {len(posts)} unique posts\n")
    
    if args.limit:
        posts = posts[:args.limit]
    
    eco_extracted = eco_saved = pol_extracted = pol_saved = 0
    
    for i, post in enumerate(posts, 1):
        print(f"[{i}/{len(posts)}] Post ID={post['id']} - {post['detected_location']}")
        print(f"  {post['title'][:70]}...")
        
        if args.type in ['economic', 'both']:
            print("  Extracting economic...")
            stats = extract_economic_stats(post, post['detected_location'])
            if stats:
                eco_extracted += 1
                print(f"  Economic: {stats}")
                if not args.dry_run and save_economic_stats(stats, post['id'], post['url'], post['detected_location']):
                    eco_saved += 1
        
        if args.type in ['political', 'both']:
            print("  🏛️  Extracting political...")
            stats = extract_political_stats(post, post['detected_location'])
            if stats:
                pol_extracted += 1
                print(f"  Political: {stats}")
                if not args.dry_run and save_political_stats(stats, post['id'], post['url'], post['detected_location']):
                    pol_saved += 1
        print()
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Posts processed: {len(posts)}")
    print(f"Economic extracted: {eco_extracted} | Saved: {eco_saved}")
    print(f"Political extracted: {pol_extracted} | Saved: {pol_saved}")


if __name__ == "__main__":
    main()
