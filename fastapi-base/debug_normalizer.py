#!/usr/bin/env python3
"""
Debug normalizer - Find exact errors
"""
import sys
import json
sys.path.insert(0, '/app')

from app.services.etl.data_normalizer import DataNormalizer

# Load raw data
with open('data/raw/raw_facebook_20260104_202744.json', 'r') as f:
    raw_data = json.load(f)

posts = raw_data['data']
print(f"\n📊 Total posts: {len(posts)}\n")

normalizer = DataNormalizer()

success = 0
errors_by_type = {}
error_samples = []

for i, post in enumerate(posts[:50]):  # Test first 50
    normalized, errors, warnings = normalizer.normalize_document(post)
    
    if errors:
        error_type = errors[0]
        if error_type not in errors_by_type:
            errors_by_type[error_type] = 0
            if len(error_samples) < 5:
                error_samples.append({
                    'index': i,
                    'id': post.get('id'),
                    'error': error_type,
                    'has_content': bool(post.get('content')),
                    'has_message': bool(post.get('meta_data', {}).get('message')),
                    'url': post.get('url', '')[:60]
                })
        errors_by_type[error_type] += 1
    else:
        success += 1

print(f"✅ Success: {success}")
print(f"❌ Errors: {len(posts[:50]) - success}\n")

print("📋 Error types:")
for error_type, count in sorted(errors_by_type.items(), key=lambda x: -x[1]):
    print(f"   {count:3d}x {error_type}")

if error_samples:
    print("\n🔍 Error samples:")
    for sample in error_samples:
        print(f"\n   #{sample['index']} (ID: {sample['id']}):")
        print(f"      Error: {sample['error']}")
        print(f"      Has content: {sample['has_content']}")
        print(f"      Has message: {sample['has_message']}")
        print(f"      URL: {sample['url']}")
