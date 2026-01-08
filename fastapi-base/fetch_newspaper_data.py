#!/usr/bin/env python3
"""
Script để fetch newspaper data từ external API
Sử dụng endpoint mới với tính năng phân trang và deduplication
"""
import requests
import json
import sys
from typing import Optional

# API Configuration
API_BASE_URL = "http://localhost:7777"
EXTERNAL_API_URL = "http://192.168.30.28:8000/api/v1/posts/by-type/newspaper"


def fetch_newspaper_raw_all(
    page_size: int = 100,
    max_pages: Optional[int] = None
) -> dict:
    """
    Fetch TẤT CẢ data (kể cả duplicate) - không filter gì cả
    """
    url = f"{API_BASE_URL}/api/data/fetch-newspaper-raw-all"
    
    payload = {
        "base_api_url": EXTERNAL_API_URL,
        "page_size": page_size,
        "max_pages": max_pages,
        "sort_by": "id",
        "order": "desc"
    }
    
    print("📰 Fetching ALL newspaper data (no deduplication)...")
    print(f"   API: {EXTERNAL_API_URL}")
    print(f"   Page size: {page_size}")
    print(f"   Max pages: {max_pages or 'unlimited'}")
    print()
    
    response = requests.post(url, json=payload)
    response.raise_for_status()
    
    return response.json()


def fetch_newspaper_only(
    page_size: int = 100,
    max_pages: Optional[int] = None
) -> dict:
    """
    Fetch và filter duplicate với DB, chỉ lưu data mới
    """
    url = f"{API_BASE_URL}/api/data/fetch-newspaper"
    
    payload = {
        "base_api_url": EXTERNAL_API_URL,
        "page_size": page_size,
        "max_pages": max_pages,
        "sort_by": "id",
        "order": "desc"
    }
    
    print("📰 Fetching newspaper data...")
    print(f"   API: {EXTERNAL_API_URL}")
    print(f"   Page size: {page_size}")
    print(f"   Max pages: {max_pages or 'unlimited'}")
    print()
    
    response = requests.post(url, json=payload)
    response.raise_for_status()
    
    return response.json()


def fetch_newspaper_full_etl(
    page_size: int = 100,
    max_pages: Optional[int] = None,
    update_existing: bool = False
) -> dict:
    """
    Fetch và chạy FULL ETL: Fetch → Process → Load to DB
    """
    url = f"{API_BASE_URL}/api/data/fetch-newspaper-full-etl"
    
    params = {"update_existing": update_existing}
    
    payload = {
        "base_api_url": EXTERNAL_API_URL,
        "page_size": page_size,
        "max_pages": max_pages,
        "sort_by": "id",
        "order": "desc"
    }
    
    print("🔄 Running FULL ETL for newspaper data...")
    print(f"   API: {EXTERNAL_API_URL}")
    print(f"   Page size: {page_size}")
    print(f"   Max pages: {max_pages or 'unlimited'}")
    print(f"   Update existing: {update_existing}")
    print()
    
    response = requests.post(url, json=payload, params=params)
    response.raise_for_status()
    
    return response.json()


def print_results(result: dict):
    """In kết quả"""
    print("\n" + "="*60)
    print(f"Status: {result['status']}")
    print(f"Message: {result.get('message', 'N/A')}")
    
    if 'statistics' in result:
        print("\n📊 Statistics:")
        stats = result['statistics']
        for key, value in stats.items():
            print(f"   {key}: {value}")
    
    if 'results' in result and 'steps' in result['results']:
        print("\n📋 Pipeline Steps:")
        for step in result['results']['steps']:
            print(f"   {step['name']}: {step['status']}")
            if 'statistics' in step:
                for key, value in step['statistics'].items():
                    print(f"      {key}: {value}")
    
    if 'raw_file' in result:
        print(f"\n💾 Raw file: {result['raw_file']}")
    
    print("="*60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch newspaper data from external API")
    parser.add_argument(
        "--mode",
        choices=["fetch-all", "fetch-only", "full-etl"],
        default="full-etl",
        help="Mode: fetch-all (lấy hết, không filter), fetch-only (chỉ fetch data mới), full-etl (fetch + process + load)"
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=100,
        help="Số records mỗi trang (default: 100)"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Giới hạn số trang (default: None = unlimited)"
    )
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Update existing records (chỉ cho full-etl mode)"
    )
    
    args = parser.parse_args()
    
    try:
        if args.mode == "fetch-all":
            result = fetch_newspaper_raw_all(
                page_size=args.page_size,
                max_pages=args.max_pages
            )
        elif args.mode == "fetch-only":
            result = fetch_newspaper_only(
                page_size=args.page_size,
                max_pages=args.max_pages
            )
        else:  # full-etl
            result = fetch_newspaper_full_etl(
                page_size=args.page_size,
                max_pages=args.max_pages,
                update_existing=args.update_existing
            )
        
        print_results(result)
        
        if result['status'] == 'success':
            sys.exit(0)
        else:
            sys.exit(1)
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
