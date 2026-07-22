#!/usr/bin/env python3
"""
LLM Extract: Highschool Graduation Statistics

Source: important_posts (type_newspaper='education')
Target: highschool_graduation_detail

Extracts:
- Graduation rates
- Student performance metrics
- Subject scores
"""

import sys
import os
from typing import Dict, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base_extractor import (
    setup_logger,
    call_llm,
    parse_llm_json,
    get_posts_from_db,
    save_to_detail_table,
    log_extraction_start,
    log_article_info,
    log_extraction_summary,
    validate_api_key,
    BATCH_SIZE,
    DELAY_BETWEEN_CALLS
)

import time

# Setup
logger = setup_logger('highschool_graduation')
TABLE_NAME = 'highschool_graduation_detail'


def extract_highschool_graduation(content: str, url: str, province: str) -> Optional[Dict]:
    """Extract highschool graduation statistics"""
    prompt = f"""Phân tích văn bản sau và trả về JSON theo đúng cấu trúc.
Chỉ sử dụng thông tin có trong văn bản, không suy diễn.

Schema:
{{
  "year": null,
  "quarter": null,
  "month": null,
  "graduation_rate": null,
  "total_candidates": null,
  "passed_candidates": null,
  "average_score": null,
  "math_avg_score": null,
  "literature_avg_score": null,
  "english_avg_score": null,
  "excellent_rate": null,
  "fail_rate": null
}}

Giải thích các trường:
- year (integer): Năm thi tốt nghiệp
- quarter (integer 1-4): Quý (nếu có)
- month (integer 1-12): Tháng (nếu có)
- graduation_rate (float): Tỷ lệ tốt nghiệp (%, 0-100)
- total_candidates (integer): Tổng số thí sinh dự thi
- passed_candidates (integer): Số thí sinh đỗ tốt nghiệp
- average_score (float): Điểm trung bình chung (0-10)
- math_avg_score (float): Điểm trung bình môn Toán (0-10)
- literature_avg_score (float): Điểm trung bình môn Văn (0-10)
- english_avg_score (float): Điểm trung bình môn Anh (0-10)
- excellent_rate (float): Tỷ lệ học sinh xuất sắc (%, 0-100)
- fail_rate (float): Tỷ lệ không đạt (%, 0-100)

Quy tắc:
1. QUAN TRỌNG: CHỈ extract nếu văn bản RÕ RÀNG nói về Hưng Yên (hoặc huyện/thành phố thuộc Hưng Yên)
2. Nếu văn bản nói về toàn quốc, tỉnh khác, hoặc không rõ địa phương → trả về: {{"no_data": true}}
3. CHỈ trích xuất số liệu CÓ TRONG văn bản về Hưng Yên
4. Nếu văn bản KHÔNG đề cập tốt nghiệp THPT của Hưng Yên, trả về: {{"no_data": true}}
5. Tỷ lệ % chuyển sang số thập phân (95.5% → 95.5)
6. Nếu trường không có trong văn bản: để null

Tỉnh/Thành cần validate: {province}

Văn bản:
\"\"\"
{content[:3000]}
\"\"\"

Chỉ trả về JSON, không thêm giải thích."""

    result = call_llm(prompt, title="Highschool Graduation Extractor")
    if not result:
        return None
    
    data = parse_llm_json(result, logger)
    if not data:
        return None
    
    # Add metadata
    data["province"] = province
    data["data_source"] = url
    
    return data


def process_article(article: Dict) -> bool:
    """Process one article and extract data"""
    url = article.get("id")
    content = article.get("content", "")
    province = article.get("province", "Hưng Yên")
    document_type = article.get("document_type", "external")
    
    # Extract data
    data = extract_highschool_graduation(content, url, province)
    if not data:
        logger.info("ℹ️  No highschool graduation data found")
        return False
    
    # Add document_type
    data["document_type"] = document_type
    
    # Save to database
    success = save_to_detail_table(data, TABLE_NAME, logger)
    return success


def main():
    """Main extraction function"""
    validate_api_key()
    
    log_extraction_start(
        logger,
        "extract_highschool_graduation.py",
        "HIGHSCHOOL GRADUATION STATISTICS",
        BATCH_SIZE
    )
    
    # Fetch posts
    articles = get_posts_from_db("education", limit=BATCH_SIZE, logger=logger)
    
    if not articles:
        logger.info("No articles found")
        return {
            "status": "no_data",
            "processed": 0,
            "extracted": 0
        }
    
    # Process articles
    total_extracted = 0
    for i, article in enumerate(articles, 1):
        log_article_info(logger, article, i, len(articles))
        
        try:
            if process_article(article):
                total_extracted += 1
            time.sleep(DELAY_BETWEEN_CALLS)
        except Exception as e:
            logger.error(f"Error processing article {article.get('id')}: {e}")
    
    # Summary
    log_extraction_summary(logger, len(articles), total_extracted, "Highschool Graduation")
    
    return {
        "status": "success",
        "processed": len(articles),
        "extracted": total_extracted
    }


if __name__ == "__main__":
    main()
