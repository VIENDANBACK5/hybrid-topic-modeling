#!/usr/bin/env python3
"""
Fetch tất cả type_newspaper riêng biệt để đảm bảo lấy đủ 100%
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:7777"

# All known type_newspaper values
TYPE_NEWSPAPERS = [
    "education",
    "medical", 
    "transportation",
    "environment",
    "policy",
    "security",
    "management",
    "politics",
    "society",
    "economy"
]

def fetch_by_type(type_newspaper: str):
    """Fetch all records for a specific type_newspaper"""
    print(f"\n{'='*60}")
    print(f"📥 Fetching: {type_newspaper}")
    print(f"{'='*60}")
    
    url = f"{BASE_URL}/api/fetch/newspaper"
    payload = {
        "page_size": 500,
        "type_newspaper": type_newspaper,
        "max_pages": None  # Fetch all pages
    }
    
    try:
        response = requests.post(url, json=payload, timeout=300)
        response.raise_for_status()
        result = response.json()
        
        print(f"Status: {result.get('status')}")
        print(f"   Total fetched: {result.get('total_fetched')}")
        print(f"   Unique records: {result.get('unique_records')}")
        print(f"   Duplicates: {result.get('duplicates_in_api')}")
        print(f"   Pages: {result.get('pages_processed')}")
        print(f"   File: {result.get('raw_file')}")
        
        return {
            "type": type_newspaper,
            "success": True,
            "unique_records": result.get('unique_records'),
            "file": result.get('raw_file')
        }
        
    except Exception as e:
        print(f"Error: {e}")
        return {
            "type": type_newspaper,
            "success": False,
            "error": str(e)
        }

def main():
    print("\n" + "="*60)
    print("FETCH ALL TYPE_NEWSPAPER")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    for type_news in TYPE_NEWSPAPERS:
        result = fetch_by_type(type_news)
        results.append(result)
        
        # Sleep between requests to avoid overwhelming server
        if type_news != TYPE_NEWSPAPERS[-1]:
            print("\n⏳ Waiting 2 seconds...")
            time.sleep(2)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    total_records = 0
    successful = 0
    failed = 0
    
    for result in results:
        if result['success']:
            successful += 1
            total_records += result['unique_records']
            print(f"{result['type']:20s}: {result['unique_records']:5d} records")
        else:
            failed += 1
            print(f"{result['type']:20s}: FAILED - {result.get('error', 'Unknown error')}")
    
    print(f"\n{'='*60}")
    print(f"Total records fetched: {total_records}")
    print(f"Successful: {successful}/{len(TYPE_NEWSPAPERS)}")
    print(f"Failed: {failed}/{len(TYPE_NEWSPAPERS)}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return results

if __name__ == "__main__":
    main()
