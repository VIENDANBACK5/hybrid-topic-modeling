#!/usr/bin/env python3
"""
Simple test: Lấy 1 FB post và xử lý hoàn chỉnh
"""
import sys
sys.path.insert(0, '/app')

from app.core.database import SessionLocal
from app.models.model_article import Article
from datetime import datetime
import json

# Load processed file
with open('data/processed/processed_20260104_132848.json', 'r') as f:
    records = json.load(f)

print(f"\n📊 Total processed records: {len(records)}")

if records:
    print("\n✅ Sample record structure:")
    sample = records[0]
    print(f"   Keys: {list(sample.keys())}")
    print(f"   Content length: {len(sample.get('content', ''))}")
    print(f"   URL: {sample.get('url', 'N/A')}")
    
    # Try to insert
    db = SessionLocal()
    try:
        print("\n📥 Attempting to insert...")
        
        article = Article(
            url=sample.get('url'),
            title=sample.get('title', ''),
            content=sample.get('content_cleaned') or sample.get('content', ''),
            source_type=sample.get('source_type', 'facebook'),
            domain=sample.get('domain'),
            published_at=datetime.fromisoformat(sample['published_at']) if sample.get('published_at') else None,
        )
        
        db.add(article)
        db.commit()
        
        print(f"✅ Successfully inserted article ID: {article.id}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()
