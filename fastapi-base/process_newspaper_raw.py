#!/usr/bin/env python3
"""
Script để process raw newspaper data: xử lý duplicate, làm sạch, load vào DB
"""
import requests
import json
import sys
from pathlib import Path

API_BASE_URL = "http://localhost:7777"


def process_raw_file(raw_file: str, update_existing: bool = False) -> dict:
    """
    Process raw file và load vào database
    """
    print(f"🔧 Processing raw file: {raw_file}")
    print(f"   Update existing: {update_existing}")
    print()
    
    # Step 1: Process raw data
    print("Step 1/2: Processing raw data...")
    process_url = f"{API_BASE_URL}/api/data/process"
    process_payload = {"raw_file": raw_file}
    
    response = requests.post(process_url, json=process_payload)
    response.raise_for_status()
    process_result = response.json()
    
    if process_result.get("status") != "success":
        print(f"❌ Process failed: {process_result.get('error')}")
        return process_result
    
    # Get statistics from result structure
    stats = process_result.get('result', {}).get('statistics', process_result.get('statistics', {}))
    print(f"✅ Processed: {stats}")
    
    processed_file = process_result.get('result', {}).get('processed_file', process_result.get('processed_file'))
    
    # Step 2: Load to database
    print(f"\nStep 2/2: Loading to database...")
    load_url = f"{API_BASE_URL}/api/data/load-to-db"
    load_payload = {
        "processed_file": processed_file,
        "update_existing": update_existing
    }
    
    response = requests.post(load_url, json=load_payload)
    response.raise_for_status()
    load_result = response.json()
    
    if load_result.get("status") != "success":
        print(f"❌ Load failed: {load_result.get('error')}")
        return load_result
    
    # Get statistics from result structure
    load_stats = load_result.get('result', {}).get('statistics', load_result.get('statistics', {}))
    print(f"✅ Loaded: {load_stats}")
    
    return {
        "status": "success",
        "process_result": process_result,
        "load_result": load_result
    }


def list_raw_files():
    """
    List các raw files có sẵn
    """
    raw_dir = Path("data/raw")
    files = sorted(raw_dir.glob("raw_newspaper_*.json"), reverse=True)
    
    print("📋 Available raw files:")
    for i, f in enumerate(files[:10], 1):
        size_mb = f.stat().st_size / 1024 / 1024
        print(f"{i}. {f.name} ({size_mb:.1f} MB)")
    
    return [str(f) for f in files]


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Process raw newspaper data")
    parser.add_argument(
        "--file",
        help="Path to raw file (nếu không có sẽ list files)"
    )
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Update existing records in database"
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Process latest raw file"
    )
    
    args = parser.parse_args()
    
    try:
        if args.latest:
            # Get latest file
            raw_dir = Path("data/raw")
            files = sorted(raw_dir.glob("raw_newspaper_*.json"), reverse=True)
            if not files:
                print("❌ No raw files found")
                sys.exit(1)
            raw_file = str(files[0])
            print(f"Using latest file: {raw_file}\n")
        elif args.file:
            raw_file = args.file
        else:
            # List files and exit
            list_raw_files()
            print("\nUsage:")
            print("  python process_newspaper_raw.py --latest")
            print("  python process_newspaper_raw.py --file data/raw/raw_newspaper_xxx.json")
            sys.exit(0)
        
        result = process_raw_file(raw_file, args.update_existing)
        
        if result['status'] == 'success':
            print("\n" + "="*60)
            print("✅ SUCCESS!")
            proc_stats = result['process_result'].get('result', {}).get('statistics', result['process_result'].get('statistics', {}))
            load_stats = result['load_result'].get('result', {}).get('statistics', result['load_result'].get('statistics', {}))
            print(f"Process: {proc_stats}")
            print(f"Load: {load_stats}")
            print("="*60)
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

