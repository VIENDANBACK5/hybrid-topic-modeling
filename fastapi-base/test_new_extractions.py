#!/usr/bin/env python3
"""
Test script for the 4 new LLM extraction services
"""

import requests
import json
import time
from dotenv import load_dotenv
import os

load_dotenv()

BASE_URL = os.getenv("LOCAL_API_BASE_URL", "http://localhost:7777")

def test_endpoint(endpoint: str, field_name: str):
    """Test a single extraction endpoint"""
    print(f"\n{'='*70}")
    print(f"Testing: {field_name}")
    print(f"Endpoint: POST {endpoint}")
    print(f"{'='*70}")
    
    try:
        # Test async endpoint
        response = requests.post(f"{BASE_URL}{endpoint}")
        
        if response.status_code in [200, 202]:
            result = response.json()
            print(f"Status Code: {response.status_code}")
            print(f"Response:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Status Code: {response.status_code}")
            print(f"Error: {response.text}")
            
        time.sleep(1)
        
    except Exception as e:
        print(f"Error: {e}")


def test_sync_endpoint(endpoint: str, field_name: str):
    """Test a single sync extraction endpoint"""
    print(f"\n{'='*70}")
    print(f"Testing SYNC: {field_name}")
    print(f"Endpoint: POST {endpoint}")
    print(f"{'='*70}")
    
    try:
        # Test sync endpoint (may take longer)
        response = requests.post(f"{BASE_URL}{endpoint}", timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            print(f"Status Code: {response.status_code}")
            print(f"Response:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Status Code: {response.status_code}")
            print(f"Error: {response.text}")
            
    except requests.exceptions.Timeout:
        print(f"⏰ Request timed out (this is normal for sync endpoints with large data)")
    except Exception as e:
        print(f"Error: {e}")


def main():
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║          TEST 4 NEW LLM EXTRACTION ENDPOINTS                         ║
╚══════════════════════════════════════════════════════════════════════╝
    """)
    
    endpoints = [
        {
            "async": "/llm-extraction/extract-digital-economy",
            "sync": "/llm-extraction/extract-digital-economy/sync",
            "field": "Kinh tế số (Digital Economy)"
        },
        {
            "async": "/llm-extraction/extract-fdi",
            "sync": "/llm-extraction/extract-fdi/sync",
            "field": "Thu hút FDI"
        },
        {
            "async": "/llm-extraction/extract-digital-transformation",
            "sync": "/llm-extraction/extract-digital-transformation/sync",
            "field": "Chuyển đổi số (Digital Transformation)"
        },
        {
            "async": "/llm-extraction/extract-pii",
            "sync": "/llm-extraction/extract-pii/sync",
            "field": "Chỉ số Sản xuất Công nghiệp (PII)"
        }
    ]
    
    print("\nTesting ASYNC endpoints (trigger background tasks)...\n")
    for ep in endpoints:
        test_endpoint(ep["async"], ep["field"])
        time.sleep(2)
    
    print("\n\n" + "="*70)
    print("Note: Sync endpoints will actually run extraction (may take time)")
    print("Skip sync tests if you just want to verify endpoints are available")
    print("="*70)
    
    user_input = input("\nDo you want to test SYNC endpoints? (y/n): ")
    
    if user_input.lower() == 'y':
        print("\n🔄 Testing SYNC endpoints (runs full extraction)...\n")
        for ep in endpoints:
            test_sync_endpoint(ep["sync"], ep["field"])
            time.sleep(2)
    
    print(f"\n{'='*70}")
    print("Testing complete!")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
