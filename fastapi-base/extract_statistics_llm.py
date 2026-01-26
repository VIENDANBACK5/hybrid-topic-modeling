"""
Script to extract economic and political statistics from important_posts using LLM.
Focuses on specific locations: xã Thư Vũ and phường Trà Lý
"""
import os
import json
import argparse
import requests
from typing import List, Dict, Optional
from datetime import datetime
import re


# LLM API configuration - OpenRouter
LLM_API_URL = os.getenv("LLM_API_URL", "https://openrouter.ai/api/v1/chat/completions")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen/qwen-2.5-72b-instruct")
LLM_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Target API configuration
TARGET_API_BASE = "http://localhost:7777"

# Target locations
TARGET_LOCATIONS = [
    "xã Thư Vũ",
    "phường Trà Lý",
    "xã thư vũ",
    "phường trà lý",
    "Thư Vũ",
    "Trà Lý"
]


def normalize_location(text: str) -> str:
    """Normalize location name for matching."""
    text = text.lower().strip()
    # Remove special prefixes
    for prefix in ["xã ", "phường ", "thị trấn ", "thành phố "]:
        text = text.replace(prefix, "")
    return text


def extract_economic_stats_with_llm(post: Dict, location: str) -> Optional[Dict]:
    """Use LLM to extract economic statistics from post content."""
    
    content = post.get('content', '')
    title = post.get('title', '')
    meta_data = post.get('meta_data', {})
    
    if not content:
        return None
    
    prompt = f"""Bạn là trợ lý AI chuyên trích xuất dữ liệu kinh tế từ văn bản tiếng Việt.

Hãy phân tích bài viết sau và trích xuất các chỉ số kinh tế cho địa phương "{location}":

TIÊU ĐỀ: {title}

NỘI DUNG: {content[:3000]}

Hãy trích xuất các thông tin sau nếu có trong văn bản (chỉ trả về nếu có dữ liệu cụ thể):
1. Tổng giá trị sản xuất (tỷ đồng)
2. Tốc độ tăng trưởng (%)
3. Tổng thu ngân sách nhà nước (tỷ đồng)
4. Hiệu suất thu ngân sách (%)
5. Năm/thời kỳ của dữ liệu
6. Ghi chú bổ sung

Trả về kết quả dưới dạng JSON với cấu trúc:
{{
    "found": true/false,
    "total_production_value": số hoặc null,
    "growth_rate": số hoặc null,
    "total_budget_revenue": số hoặc null,
    "budget_collection_efficiency": số hoặc null,
    "year": số hoặc null,
    "period": "chuỗi mô tả thời kỳ" hoặc null,
    "notes": "ghi chú" hoặc null
}}

CHỈ trả về JSON, không giải thích thêm."""

    try:
        response = requests.post(
            LLM_API_URL,
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": "Bạn là trợ lý trích xuất dữ liệu. Chỉ trả về JSON, không giải thích."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 1000
            },
            timeout=60
        )
        
        if response.status_code != 200:
            print(f"LLM API error: {response.status_code}")
            return None
        
        result = response.json()
        content = result['choices'][0]['message']['content'].strip()
        
        # Extract JSON from response (handle markdown code blocks)
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()
        
        data = json.loads(content)
        
        if data.get('found'):
            return data
        return None
        
    except Exception as e:
        print(f"Error extracting economic stats: {e}")
        return None


def extract_political_stats_with_llm(post: Dict, location: str) -> Optional[Dict]:
    """Use LLM to extract political statistics from post content."""
    
    content = post.get('content', '')
    title = post.get('title', '')
    
    if not content:
        return None
    
    prompt = f"""Bạn là trợ lý AI chuyên trích xuất dữ liệu chính trị từ văn bản tiếng Việt.

Hãy phân tích bài viết sau và trích xuất các thông tin về Đảng bộ cho địa phương "{location}":

TIÊU ĐỀ: {title}

NỘI DUNG: {content[:3000]}

Hãy trích xuất các thông tin sau nếu có trong văn bản:
1. Quy mô Đảng bộ (mô tả tổng quát)
2. Số tổ chức Đảng (chi bộ, đảng bộ cơ sở)
3. Số lượng Đảng viên
4. Số Đảng viên mới kết nạp
5. Số chi bộ
6. Năm/thời kỳ của dữ liệu
7. Ghi chú bổ sung

Trả về kết quả dưới dạng JSON với cấu trúc:
{{
    "found": true/false,
    "party_organization_count": số hoặc null,
    "party_member_count": số hoặc null,
    "party_size_description": "mô tả" hoặc null,
    "new_party_members": số hoặc null,
    "party_cells_count": số hoặc null,
    "year": số hoặc null,
    "period": "chuỗi mô tả thời kỳ" hoặc null,
    "notes": "ghi chú" hoặc null
}}

CHỈ trả về JSON, không giải thích thêm."""

    try:
        response = requests.post(
            LLM_API_URL,
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": "Bạn là trợ lý trích xuất dữ liệu. Chỉ trả về JSON, không giải thích."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 1000
            },
            timeout=60
        )
        
        if response.status_code != 200:
            print(f"LLM API error: {response.status_code}")
            return None
        
        result = response.json()
        content = result['choices'][0]['message']['content'].strip()
        
        # Extract JSON from response
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()
        
        data = json.loads(content)
        
        if data.get('found'):
            return data
        return None
        
    except Exception as e:
        print(f"Error extracting political stats: {e}")
        return None


def fetch_important_posts_for_locations(locations: List[str]) -> List[Dict]:
    """Fetch important posts that mention target locations."""
    
    all_posts = []
    
    for location in locations:
        try:
            # Use search endpoint with dvhc or content search
            params = {
                'search': location,
                'limit': 100
            }
            
            response = requests.get(
                f"{TARGET_API_BASE}/api/important-posts/",
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                posts = data.get('items', [])
                print(f"Found {len(posts)} posts for location: {location}")
                
                # Filter posts that actually mention the location
                for post in posts:
                    content = post.get('content', '').lower()
                    title = post.get('title', '').lower()
                    dvhc = post.get('dvhc', '')
                    
                    normalized_loc = normalize_location(location)
                    
                    if (normalized_loc in normalize_location(content) or 
                        normalized_loc in normalize_location(title) or
                        normalized_loc in normalize_location(dvhc)):
                        
                        # Add location info to post
                        post['detected_location'] = location
                        all_posts.append(post)
            else:
                print(f"Error fetching posts for {location}: {response.status_code}")
                
        except Exception as e:
            print(f"Error fetching posts for {location}: {e}")
    
    # Remove duplicates based on post ID
    seen_ids = set()
    unique_posts = []
    for post in all_posts:
        post_id = post.get('id')
        if post_id not in seen_ids:
            seen_ids.add(post_id)
            unique_posts.append(post)
    
    print(f"\nTotal unique posts found: {len(unique_posts)}")
    return unique_posts


def save_economic_statistics(stats: Dict, post_id: int, post_url: str, location: str) -> bool:
    """Save economic statistics to database via API."""
    
    payload = {
        "dvhc": location,
        "source_post_id": post_id,
        "source_url": post_url,
        "total_production_value": stats.get('total_production_value'),
        "growth_rate": stats.get('growth_rate'),
        "total_budget_revenue": stats.get('total_budget_revenue'),
        "budget_collection_efficiency": stats.get('budget_collection_efficiency'),
        "year": stats.get('year'),
        "period": stats.get('period'),
        "notes": stats.get('notes'),
        "extraction_metadata": json.dumps({
            "extracted_at": datetime.now().isoformat(),
            "llm_model": LLM_MODEL
        })
    }
    
    try:
        response = requests.post(
            f"{TARGET_API_BASE}/api/statistics/economic",
            json=payload,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            return True
        else:
            print(f"Error saving economic stats: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Error saving economic stats: {e}")
        return False


def save_political_statistics(stats: Dict, post_id: int, post_url: str, location: str) -> bool:
    """Save political statistics to database via API."""
    
    payload = {
        "dvhc": location,
        "source_post_id": post_id,
        "source_url": post_url,
        "party_organization_count": stats.get('party_organization_count'),
        "party_member_count": stats.get('party_member_count'),
        "party_size_description": stats.get('party_size_description'),
        "new_party_members": stats.get('new_party_members'),
        "party_cells_count": stats.get('party_cells_count'),
        "year": stats.get('year'),
        "period": stats.get('period'),
        "notes": stats.get('notes'),
        "extraction_metadata": json.dumps({
            "extracted_at": datetime.now().isoformat(),
            "llm_model": LLM_MODEL
        })
    }
    
    try:
        response = requests.post(
            f"{TARGET_API_BASE}/api/statistics/political",
            json=payload,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            return True
        else:
            print(f"Error saving political stats: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Error saving political stats: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Extract statistics from important posts using LLM')
    parser.add_argument('--type', choices=['economic', 'political', 'both'], default='both',
                        help='Type of statistics to extract')
    parser.add_argument('--dry-run', action='store_true',
                        help='Extract but do not save to database')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit number of posts to process')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("EXTRACTING STATISTICS FROM IMPORTANT POSTS")
    print("=" * 80)
    print(f"Target locations: {', '.join(TARGET_LOCATIONS)}")
    print(f"Extraction type: {args.type}")
    print(f"Dry run: {args.dry_run}")
    print()
    
    # Fetch posts
    posts = fetch_important_posts_for_locations(TARGET_LOCATIONS)
    
    if args.limit:
        posts = posts[:args.limit]
        print(f"Processing limited to {args.limit} posts")
    
    economic_extracted = 0
    political_extracted = 0
    economic_saved = 0
    political_saved = 0
    
    for i, post in enumerate(posts, 1):
        post_id = post.get('id')
        post_url = post.get('url', '')
        title = post.get('title', '')
        location = post.get('detected_location', 'Unknown')
        
        print(f"\n[{i}/{len(posts)}] Processing post ID={post_id}")
        print(f"  Location: {location}")
        print(f"  Title: {title[:80]}...")
        
        # Extract economic statistics
        if args.type in ['economic', 'both']:
            print("  Extracting economic data...")
            economic_stats = extract_economic_stats_with_llm(post, location)
            
            if economic_stats:
                economic_extracted += 1
                print(f"  Found economic data: {economic_stats}")
                
                if not args.dry_run:
                    if save_economic_statistics(economic_stats, post_id, post_url, location):
                        economic_saved += 1
                        print("  Saved to database")
                    else:
                        print("  ✗ Failed to save")
            else:
                print("  - No economic data found")
        
        # Extract political statistics
        if args.type in ['political', 'both']:
            print("  Extracting political data...")
            political_stats = extract_political_stats_with_llm(post, location)
            
            if political_stats:
                political_extracted += 1
                print(f"  Found political data: {political_stats}")
                
                if not args.dry_run:
                    if save_political_statistics(political_stats, post_id, post_url, location):
                        political_saved += 1
                        print("  Saved to database")
                    else:
                        print("  ✗ Failed to save")
            else:
                print("  - No political data found")
    
    print("\n" + "=" * 80)
    print("EXTRACTION SUMMARY")
    print("=" * 80)
    print(f"Total posts processed: {len(posts)}")
    print(f"Economic data extracted: {economic_extracted}")
    print(f"Political data extracted: {political_extracted}")
    
    if not args.dry_run:
        print(f"Economic data saved: {economic_saved}")
        print(f"Political data saved: {political_saved}")
    else:
        print("(Dry run mode - no data saved)")
    print()


if __name__ == "__main__":
    main()
