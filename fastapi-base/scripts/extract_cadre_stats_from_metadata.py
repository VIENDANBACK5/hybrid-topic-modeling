"""
Extract cadre statistics from articles.raw_metadata.statistics
Thay vì dùng LLM/Regex, lấy trực tiếp từ metadata đã parse sẵn
"""
import re
import json
from sqlalchemy import create_engine, text
from datetime import datetime

# Database connection
DB_URL = "postgresql://postgres:postgres@localhost:5555/DBHuYe"
engine = create_engine(DB_URL)


def parse_number(text: str) -> int:
    """
    Parse number from Vietnamese text
    "6.485 biên chế" -> 6485
    "hơn 2.000" -> 2000
    """
    # Remove all non-digit except dot and comma
    text = text.lower()
    # Extract first number
    match = re.search(r'(\d+[.,]?\d*)', text)
    if match:
        num_str = match.group(1).replace('.', '').replace(',', '')
        try:
            return int(num_str)
        except:
            pass
    return None


def extract_cadre_stats(statistics: list) -> dict:
    """
    Extract cadre statistics from metadata.statistics list
    
    Input example:
    [
      "6.485 biên chế",
      "2.016 biên chế cho các sở, ban, ngành",
      "4.469 biên chế cho UBND các xã, phường",
      "240 lao động hợp đồng"
    ]
    
    Output:
    {
      "total_authorized": 6485,
      "provincial_level": 2016,
      "commune_level": 4469,
      "contract_workers": 240
    }
    """
    result = {
        "total_authorized": None,
        "provincial_level": None,
        "commune_level": None,
        "contract_workers": None
    }
    
    for stat in statistics:
        stat_lower = stat.lower()
        
        # Total: "6.485 biên chế" (standalone)
        if 'biên chế' in stat_lower and 'sở' not in stat_lower and 'xã' not in stat_lower and 'phường' not in stat_lower:
            num = parse_number(stat)
            if num and num > 1000:  # Must be > 1000 to be total
                result["total_authorized"] = num
        
        # Provincial: "2.016 biên chế cho các sở, ban, ngành" or "cấp tỉnh"
        if ('sở' in stat_lower or 'ban' in stat_lower or 'ngành' in stat_lower or 'cấp tỉnh' in stat_lower) and 'biên chế' in stat_lower:
            num = parse_number(stat)
            if num:
                result["provincial_level"] = num
        
        # Commune: "4.469 biên chế cho UBND các xã, phường" or "cấp xã"
        if ('xã' in stat_lower or 'phường' in stat_lower or 'cấp xã' in stat_lower) and 'biên chế' in stat_lower:
            num = parse_number(stat)
            if num:
                result["commune_level"] = num
        
        # Contract workers: "240 lao động hợp đồng"
        if 'hợp đồng' in stat_lower:
            num = parse_number(stat)
            if num:
                result["contract_workers"] = num
    
    return result


def extract_year_from_date(date_str: str) -> int:
    """
    Extract year from date string
    "Chủ nhật, ngày 14/09/2025 17:19 GMT+7" -> 2025
    "14/09/2025" -> 2025
    """
    match = re.search(r'(\d{4})', date_str)
    if match:
        return int(match.group(1))
    return datetime.now().year


def main():
    print("Extracting cadre statistics from articles.raw_metadata...\n")
    
    # Query articles with raw_metadata.statistics
    query = """
    SELECT 
        id,
        url,
        title,
        province,
        raw_metadata,
        category
    FROM articles
    WHERE 
        raw_metadata IS NOT NULL
        AND raw_metadata::jsonb ? 'statistics'
    ORDER BY id DESC
    LIMIT 100
    """
    
    with engine.connect() as conn:
        result = conn.execute(text(query))
        articles = result.fetchall()
        
        print(f"Found {len(articles)} articles with potential cadre statistics\n")
        
        inserted_count = 0
        skipped_count = 0
        
        for article in articles:
            article_id, url, title, province, raw_metadata, category = article
            
            # Parse metadata
            if isinstance(raw_metadata, str):
                metadata = json.loads(raw_metadata)
            else:
                metadata = raw_metadata
            
            statistics = metadata.get('statistics', [])
            if not statistics:
                continue
            
            # Extract cadre stats
            stats = extract_cadre_stats(statistics)
            
            # Check if we got at least 2 fields
            non_null_count = sum(1 for v in stats.values() if v is not None)
            if non_null_count < 2:
                skipped_count += 1
                continue
            
            # Extract year
            date_str = metadata.get('date', '')
            year = extract_year_from_date(date_str)
            
            # Get province
            if not province and 'hưng yên' in title.lower():
                province = 'Hưng Yên'
            
            print(f"Article {article_id}: {title[:60]}...")
            print(f"   Province: {province}, Year: {year}")
            print(f"   Stats: {stats}")
            
            # Insert to cadre_statistics_detail
            insert_query = """
            INSERT INTO cadre_statistics_detail (
                province, year, 
                total_authorized, provincial_level, commune_level, contract_workers,
                data_source, data_status, created_at, updated_at
            ) VALUES (
                :province, :year,
                :total_authorized, :provincial_level, :commune_level, :contract_workers,
                :data_source, 'official', NOW(), NOW()
            )
            ON CONFLICT DO NOTHING
            """
            
            try:
                conn.execute(text(insert_query), {
                    'province': province or 'Unknown',
                    'year': year,
                    'total_authorized': stats['total_authorized'],
                    'provincial_level': stats['provincial_level'],
                    'commune_level': stats['commune_level'],
                    'contract_workers': stats['contract_workers'],
                    'data_source': url[:255]
                })
                conn.commit()
                inserted_count += 1
                print(f"   Inserted to DB\n")
            except Exception as e:
                print(f"   ✗ Error: {e}\n")
                conn.rollback()
        
        print(f"\n📈 Summary:")
        print(f"   Total articles: {len(articles)}")
        print(f"   Inserted: {inserted_count}")
        print(f"   Skipped: {skipped_count}")


if __name__ == '__main__':
    main()
