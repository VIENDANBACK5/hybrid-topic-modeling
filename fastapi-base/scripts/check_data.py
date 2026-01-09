"""
Script để kiểm tra dữ liệu hiện có trong database
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from sqlalchemy import create_engine, text

print("Checking database data...")
print(f"Database URL: {settings.DATABASE_URL[:50]}...")

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    # Check articles
    result = conn.execute(text('SELECT COUNT(*) as count FROM articles'))
    print(f"\n✅ Total articles: {result.scalar()}")
    
    # Check custom topics
    result = conn.execute(text('SELECT COUNT(*) as count FROM custom_topics'))
    print(f"✅ Total custom topics: {result.scalar()}")
    
    # Check fields
    result = conn.execute(text('SELECT COUNT(*) as count FROM fields'))
    print(f"✅ Total fields: {result.scalar()}")
    
    # Check if economic indicators table exists
    result = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'economic_indicators'"))
    if result.scalar() > 0:
        result = conn.execute(text('SELECT COUNT(*) as count FROM economic_indicators'))
        print(f"✅ Total economic indicators: {result.scalar()}")
    else:
        print("⚠️  Economic indicators table not found")
    
    # Sample articles with field classification
    print("\n📊 Sample articles by field:")
    result = conn.execute(text("""
        SELECT f.name, COUNT(DISTINCT afc.article_id) as count
        FROM fields f
        LEFT JOIN article_field_classifications afc ON f.id = afc.field_id
        GROUP BY f.name
        ORDER BY count DESC
        LIMIT 10
    """))
    for row in result:
        print(f"  - {row[0]}: {row[1]} articles")

print("\n✅ Done!")
