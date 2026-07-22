"""
Script để import dữ liệu từ API nguồn vào bảng important_posts
Sử dụng: python import_important_posts.py --type medical --page 1 --page_size 100
"""
import requests
import argparse
import json
from typing import List, Dict, Any
from datetime import datetime


def fetch_posts_from_api(
    base_url: str,
    type_newspaper: str,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "id",
    order: str = "desc"
) -> Dict[str, Any]:
    """
    Lấy dữ liệu từ API nguồn
    
    Args:
        base_url: URL cơ bản của API
        type_newspaper: Loại báo (medical, economic, ...)
        page: Số trang
        page_size: Số bài viết mỗi trang
        sort_by: Sắp xếp theo field
        order: Thứ tự sắp xếp
        
    Returns:
        Dict chứa response từ API
    """
    url = f"{base_url}/api/v1/posts-v2/by-type-newspaper/{type_newspaper}"
    params = {
        "sort_by": sort_by,
        "order": order,
        "page_size": page_size,
        "page": page
    }
    
    print(f"📡 Fetching from: {url}")
    print(f"   Params: {params}")
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    return response.json()


def transform_post_to_important_post(post: Dict[str, Any]) -> Dict[str, Any]:
    """
    Chuyển đổi dữ liệu từ API nguồn sang format của ImportantPost
    
    Args:
        post: Dữ liệu bài viết từ API nguồn
        
    Returns:
        Dict theo format ImportantPostCreate
    """
    meta_data = post.get("meta_data", {})
    
    return {
        "url": post.get("url"),
        "title": post.get("title"),
        "content": post.get("content"),
        "data_type": post.get("data_type", "newspaper"),
        "type_newspaper": meta_data.get("type_newspaper"),
        
        # Original source metadata
        "original_id": post.get("id"),
        "original_created_at": post.get("created_at"),
        "original_updated_at": post.get("updated_at"),
        
        # Full metadata
        "meta_data": meta_data,
        
        # Extracted fields
        "author": meta_data.get("author"),
        "published_date": meta_data.get("date"),
        "dvhc": meta_data.get("dvhc"),
        "statistics": meta_data.get("statistics", []),
        "organizations": meta_data.get("organizations", []),
        
        # Default values
        "is_featured": 1,
        "importance_score": None,
        "tags": [],
        "categories": []
    }


def import_posts_to_db(
    api_url: str,
    posts: List[Dict[str, Any]],
    skip_duplicates: bool = True
) -> Dict[str, Any]:
    """
    Import bài viết vào database thông qua API
    
    Args:
        api_url: URL của API important-posts
        posts: Danh sách bài viết cần import
        skip_duplicates: Bỏ qua các URL đã tồn tại
        
    Returns:
        Dict chứa kết quả import
    """
    url = f"{api_url}/api/important-posts/bulk/import"
    params = {"skip_duplicates": skip_duplicates}
    
    print(f"📤 Importing {len(posts)} posts to: {url}")
    
    try:
        response = requests.post(url, json=posts, params=params, timeout=300)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        print(f"Response text: {response.text[:1000]}")
        raise
    except Exception as e:
        print(f"Request Error: {e}")
        raise

from dotenv import load_dotenv
import os
load_dotenv()

def main():
    parser = argparse.ArgumentParser(
        description="Import dữ liệu từ API nguồn vào bảng important_posts"
    )
    parser.add_argument(
        "--source-url",
        default=os.getenv("EXTERNAL_API_BASE_URL"),
        help="URL của API nguồn"
    )
    parser.add_argument(
        "--target-url",
        default=os.getenv("LOCAL_API_BASE_URL"),
        help="URL của API target (important-posts)"
    )
    parser.add_argument(
        "--type",
        default="medical",
        help="Loại báo cần import (medical, economic, ...)"
    )
    parser.add_argument(
        "--page",
        type=int,
        default=1,
        help="Số trang bắt đầu"
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=10,
        help="Số bài viết mỗi trang"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Số trang tối đa cần import (None = tất cả)"
    )
    parser.add_argument(
        "--skip-duplicates",
        action="store_true",
        default=True,
        help="Bỏ qua các URL đã tồn tại"
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("IMPORT IMPORTANT POSTS")
    print("=" * 80)
    print(f"Source: {args.source_url}")
    print(f"Target: {args.target_url}")
    print(f"Type: {args.type}")
    print(f"Page size: {args.page_size}")
    print(f"Skip duplicates: {args.skip_duplicates}")
    print("=" * 80)
    
    total_created = 0
    total_skipped = 0
    total_errors = 0
    current_page = args.page
    
    while True:
        try:
            # Fetch posts from source API
            print(f"\n📖 Page {current_page}...")
            response = fetch_posts_from_api(
                base_url=args.source_url,
                type_newspaper=args.type,
                page=current_page,
                page_size=args.page_size
            )
            
            # Check if we got data
            data = response.get("data", [])
            if not data:
                print("No more data to import")
                break
            
            print(f"   Found {len(data)} posts")
            
            # Transform posts
            transformed_posts = [transform_post_to_important_post(post) for post in data]
            
            # Import to database
            result = import_posts_to_db(
                api_url=args.target_url,
                posts=transformed_posts,
                skip_duplicates=args.skip_duplicates
            )
            
            # Update counters
            total_created += result.get("created", 0)
            total_skipped += result.get("skipped", 0)
            total_errors += result.get("errors", 0)
            
            print(f"   Created: {result.get('created', 0)}")
            print(f"   Skipped: {result.get('skipped', 0)}")
            print(f"   Errors: {result.get('errors', 0)}")
            
            # Check if we should continue
            if args.max_pages and current_page >= args.page + args.max_pages - 1:
                print(f"\n🛑 Reached max pages limit: {args.max_pages}")
                break
            
            # Check if this was the last page
            metadata = response.get("metadata", {})
            total_items = metadata.get("total", 0)
            total_pages = (total_items + args.page_size - 1) // args.page_size
            
            if current_page >= total_pages:
                print(f"\nReached last page: {current_page}/{total_pages}")
                break
            
            current_page += 1
            
        except requests.exceptions.RequestException as e:
            print(f"\nError fetching data: {e}")
            break
        except Exception as e:
            print(f"\nUnexpected error: {e}")
            break
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total created: {total_created}")
    print(f"Total skipped: {total_skipped}")
    print(f"Total errors: {total_errors}")
    print(f"Total pages processed: {current_page - args.page + 1}")
    print("=" * 80)


if __name__ == "__main__":
    main()
