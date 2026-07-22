#!/usr/bin/env python3
"""
Extract economic indicators from crawled JSON files
Load JSON → Extract indicators → Save to database

Usage:
    python scripts/extract_from_json.py --input data/crawled/all_articles_20260115_172701.json
"""
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_db
from app.services.universal_economic_extractor import UniversalEconomicExtractor, IndicatorClassifier
from app.api.api_economic_extraction import extract_period_from_title


def extract_from_json(json_file: str, year: int = 2024, indicator_types: list = None):
    """
    Extract economic data from crawled JSON file
    
    Args:
        json_file: Path to JSON file with articles
        year: Default year if not found in title
        indicator_types: List of indicators to extract (None = all)
    """
    print(f"\n{'='*80}")
    print(f"EXTRACTING ECONOMIC DATA FROM JSON")
    print(f"{'='*80}\n")
    print(f"Input file:      {json_file}")
    print(f"Default year:    {year}")
    print(f"Indicators:      {indicator_types or 'ALL'}")
    print()
    
    # Load JSON
    with open(json_file, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    print(f"Loaded {len(articles)} articles\n")
    
    # Get DB session
    db = next(get_db())
    extractor = UniversalEconomicExtractor(db)
    
    results = []
    processed = 0
    skipped = 0
    
    for i, article in enumerate(articles, 1):
        print(f"[{i}/{len(articles)}] Article {article['article_id']}: {article['title'][:60]}...")
        
        # Fetch full content (since JSON might have incomplete content)
        from app.services.universal_economic_extractor import ArticleCrawler
        crawler = ArticleCrawler()
        
        full_content = crawler.get_article_content(article['url'])
        
        if not full_content:
            print(f"   Could not fetch content, using cached content")
            full_content = article.get('content', '')
        
        if not full_content or len(full_content) < 100:
            print(f"   Content too short ({len(full_content)} chars), skipping")
            skipped += 1
            continue
        
        # Classify indicators
        full_text = f"{article['title']} {article.get('summary', '')} {full_content}"
        detected_indicators = IndicatorClassifier.classify(full_text)
        
        # Filter by requested types
        if indicator_types:
            detected_indicators = [
                ind for ind in detected_indicators
                if ind in indicator_types
            ]
        
        if not detected_indicators:
            print(f"   No relevant indicators detected, skipping")
            skipped += 1
            continue
        
        print(f"   Detected: {', '.join(detected_indicators)}")
        
        # Extract period from title
        period_year, month, quarter = extract_period_from_title(article['title'], year)
        print(f"   📅 Period: year={period_year}, month={month}, quarter={quarter}")
        
        # Extract and save
        try:
            result = extractor.extract_and_save(
                text=full_content,
                indicator_types=detected_indicators,
                source_url=article['url'],
                year=period_year,
                month=month,
                quarter=quarter
            )
            
            results.append({
                'article_id': article['article_id'],
                'title': article['title'],
                'url': article['url'],
                'indicators': result
            })
            
            processed += 1
            
            # Count extracted values
            total_extracted = sum(
                len(ind_result.get('values', []))
                for ind_result in result.values()
            )
            print(f"   Extracted {total_extracted} values\n")
            
        except Exception as e:
            print(f"   Error: {str(e)[:100]}\n")
            skipped += 1
            continue
    
    # Summary
    print(f"\n{'='*80}")
    print("EXTRACTION SUMMARY")
    print(f"{'='*80}")
    print(f"Total articles:      {len(articles)}")
    print(f"Processed:           {processed} ")
    print(f"Skipped:             {skipped} ")
    print(f"Success rate:        {processed/len(articles)*100:.1f}%")
    print(f"{'='*80}\n")
    
    # Save extraction report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = Path(json_file).parent / f"extraction_report_{timestamp}.json"
    
    report = {
        'extraction_date': timestamp,
        'input_file': json_file,
        'statistics': {
            'total_articles': len(articles),
            'processed': processed,
            'skipped': skipped,
            'success_rate': f"{processed/len(articles)*100:.1f}%"
        },
        'results': results
    }
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"Report saved to: {report_file}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Extract economic indicators from crawled JSON'
    )
    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='Path to JSON file with articles'
    )
    parser.add_argument(
        '--year',
        type=int,
        default=2024,
        help='Default year if not in title (default: 2024)'
    )
    parser.add_argument(
        '--indicators',
        nargs='+',
        choices=['iip', 'cpi', 'budget', 'retail', 'investment', 'agri', 'export', 'grdp'],
        help='Specific indicators to extract (default: all)'
    )
    
    args = parser.parse_args()
    
    if not Path(args.input).exists():
        print(f"Error: File not found: {args.input}")
        sys.exit(1)
    
    extract_from_json(
        json_file=args.input,
        year=args.year,
        indicator_types=args.indicators
    )


if __name__ == '__main__':
    main()
