#!/usr/bin/env python3
"""
Merge tất cả raw newspaper files thành 1 file duy nhất
"""

import json
from pathlib import Path
from datetime import datetime
from collections import Counter

def merge_raw_files():
    """Merge all newspaper raw files into one"""
    
    raw_dir = Path("data/raw/newspaper")
    
    # Get all files from today's fetch
    today = datetime.now().strftime("%Y%m%d")
    raw_files = sorted(raw_dir.glob(f"newspaper_{today}_*.json"))
    
    print(f"\n📂 Found {len(raw_files)} raw files to merge\n")
    
    all_records = []
    seen_urls = set()
    duplicates = 0
    
    type_counts = Counter()
    
    for file_path in raw_files:
        print(f"  Reading: {file_path.name}")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        records = data.get('records', [])
        
        for record in records:
            url = record.get('url')
            if url:
                if url in seen_urls:
                    duplicates += 1
                else:
                    seen_urls.add(url)
                    all_records.append(record)
                    
                    # Count by type
                    type_val = record.get('meta_data', {}).get('type_newspaper')
                    if type_val:
                        type_counts[type_val] += 1
    
    # Save merged file
    merged_file = raw_dir / f"newspaper_merged_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    output_data = {
        "data_type": "newspaper",
        "fetch_date": datetime.now().isoformat(),
        "source": "merged_from_multiple_fetches",
        "total_files_merged": len(raw_files),
        "total_records": len(all_records),
        "duplicates_removed": duplicates,
        "records": all_records
    }
    
    with open(merged_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    # Report
    print(f"\n{'='*60}")
    print(f"MERGE COMPLETE")
    print(f"{'='*60}")
    print(f"Files merged: {len(raw_files)}")
    print(f"Total records: {len(all_records)}")
    print(f"Duplicates removed: {duplicates}")
    print(f"\nOutput: {merged_file.name}")
    
    print(f"\nRecords by type:")
    for type_val, count in type_counts.most_common():
        print(f"  {type_val:20s}: {count:5d}")
    
    return str(merged_file)

if __name__ == "__main__":
    merge_raw_files()
