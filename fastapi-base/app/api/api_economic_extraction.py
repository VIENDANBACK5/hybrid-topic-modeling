"""
API Endpoints for Universal Economic Data Extraction
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
import re

from app.core.database import get_db
from app.services.universal_economic_extractor import (
    ArticleCrawler,
    IndicatorClassifier,
    UniversalEconomicExtractor
)

router = APIRouter(prefix="/api/economic", tags=["Economic Data Extraction"])


def extract_period_from_title(title: str, default_year: int) -> tuple:
    """
    Extract year, month, quarter from article title
    
    Returns:
        (year, month, quarter) tuple
    
    Examples:
        "tháng 11 và 11 tháng năm 2025" -> (2025, 11, None)  # monthly report
        "Quý I/2025" -> (2025, None, 1)
        "năm 2024" -> (2024, None, None)  # annual
    """
    title_lower = title.lower()
    
    # Extract year from title (prioritize this over default)
    year_match = re.search(r'năm\s+(20\d{2})', title_lower)
    if year_match:
        year = int(year_match.group(1))
    else:
        year = default_year
    
    
    month_match = re.search(r'tháng\s+(\d+|một|hai|ba|bốn|năm|sáu|bảy|tám|chín|mười|mười một|mười hai)', title_lower)
    if month_match:
        month_str = month_match.group(1)
        month_map = {
            'một': 1, 'hai': 2, 'ba': 3, 'bốn': 4, 'năm': 5, 'sáu': 6,
            'bảy': 7, 'tám': 8, 'chín': 9, 'mười': 10, 'mười một': 11, 'mười hai': 12
        }
        month = month_map.get(month_str, None)
        if month is None:
            try:
                month = int(month_str)
            except:
                month = None
        if month:
            return (year, month, None)
    
    
    quarter_match = re.search(r'quý\s*([IVX]+|[1-4])', title_lower, re.IGNORECASE)
    if quarter_match:
        quarter_str = quarter_match.group(1).upper()
        quarter_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4}
        quarter = quarter_map.get(quarter_str, None)
        if quarter is None:
            try:
                quarter = int(quarter_str)
            except:
                quarter = None
        
        if quarter:
            return (year, None, quarter)
    
    # Default: annual (no month/quarter)
    return (year, None, None)


class BulkExtractionRequest(BaseModel):
    """Request for bulk extraction"""
    max_pages: int = Field(3, description="Số trang tối đa để crawl")
    year: int = Field(2025, description="Năm của dữ liệu")
    indicator_types: Optional[List[str]] = Field(
        None,
        description="Chỉ extract các chỉ số này (None = tất cả)"
    )


class BulkExtractionResponse(BaseModel):
    """Response for bulk extraction"""
    total_articles: int
    processed: int
    results: list  # Changed from dict to list


@router.post("/extract-all", response_model=BulkExtractionResponse)
def extract_all_economic_data(
    request: BulkExtractionRequest,
    db: Session = Depends(get_db)
):
    """
    Crawl và extract tất cả dữ liệu kinh tế từ thongkehungyen.nso.gov.vn
    
    **Quy trình:**
    1. Crawl danh sách bài viết từ trang chủ
    2. Với mỗi bài viết:
       - Fetch nội dung đầy đủ
       - Phân loại thuộc chỉ số nào (GRDP, IIP, Export, etc.)
       - Extract dữ liệu
       - Save vào bảng tương ứng
    
    **Ví dụ:**
    ```json
    {
      "max_pages": 3,
      "year": 2025,
      "indicator_types": ["grdp", "iip", "export"]
    }
    ```
    """
    # Step 1: Crawl articles
    crawler = ArticleCrawler()
    articles = crawler.get_article_list(max_pages=request.max_pages)
    
    if not articles:
        raise HTTPException(
            status_code=404,
            detail="No articles found"
        )
    
    # Step 2: Process each article
    extractor = UniversalEconomicExtractor(db)
    results = []
    processed = 0
    
    for article in articles:
        try:
            # Get full content
            content = crawler.get_article_content(article['url'])
            
            if not content:
                continue
            
            # Classify article
            full_text = f"{article['title']} {article['summary']} {content}"
            indicator_types = IndicatorClassifier.classify(full_text)
            
            # Filter by requested types
            if request.indicator_types:
                indicator_types = [
                    t for t in indicator_types
                    if t in request.indicator_types
                ]
            
            if not indicator_types:
                continue
            
            # Extract period (year, month, quarter) from title
            year, month, quarter = extract_period_from_title(article['title'], request.year)
            
            # Extract and save
            result = extractor.extract_and_save(
                text=content,
                indicator_types=indicator_types,
                source_url=article['url'],
                year=year,
                month=month,
                quarter=quarter
            )
            
            results.append({
                'article': article,
                'indicators': indicator_types,
                'extraction': result
            })
            
            processed += 1
            
        except Exception as e:
            results.append({
                'article': article,
                'error': str(e)
            })
            continue
    
    return {
        'total_articles': len(articles),
        'processed': processed,
        'results': results
    }


@router.post("/extract-single")
def extract_single_article(
    url: str,
    year: int = 2025,
    use_llm: bool = True,
    db: Session = Depends(get_db)
):
    """
    Extract dữ liệu từ một bài viết cụ thể
    
    **Ví dụ:**
    ```
    POST /api/economic/extract-single?url=https://thongkehungyen.nso.gov.vn/...&year=2025&use_llm=true
    ```
    
    **Parameters:**
    - url: URL của bài viết
    - year: Năm của dữ liệu (default: 2025)
    - use_llm: Sử dụng LLM để phân tích chính xác hơn (default: true)
    """
    # Get content
    crawler = ArticleCrawler()
    content = crawler.get_article_content(url)
    
    if not content:
        raise HTTPException(
            status_code=404,
            detail=f"Could not fetch content from {url}"
        )
    
    # Classify
    indicator_types = IndicatorClassifier.classify(content)
    
    if not indicator_types:
        return {
            'url': url,
            'message': 'No economic indicators detected',
            'content_preview': content[:500]
        }
    
    # Extract with LLM support
    extractor = UniversalEconomicExtractor(db, use_llm=use_llm)
    results = extractor.extract_and_save(
        text=content,
        indicator_types=indicator_types,
        source_url=url,
        year=year
    )
    
    return {
        'url': url,
        'year': year,
        'use_llm': use_llm,
        'detected_indicators': indicator_types,
        'extraction_results': results,
        'content_length': len(content)
    }


@router.get("/test-classifier")
def test_classifier(text: str):
    """
    Test phân loại text thuộc chỉ số nào
    
    **Ví dụ:**
    ```
    GET /api/economic/test-classifier?text=GRDP 9 tháng đạt 114.792 tỷ đồng
    ```
    """
    indicator_types = IndicatorClassifier.classify(text)
    
    return {
        'text': text,
        'detected_indicators': indicator_types,
        'all_patterns': IndicatorClassifier.PATTERNS
    }
