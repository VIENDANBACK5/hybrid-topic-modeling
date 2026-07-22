#!/usr/bin/env python3
"""
LLM Extract: TVET Employment Statistics

TVET = Technical and Vocational Education and Training

Source: important_posts (type_newspaper='education')
Target: tvet_employment_detail

Extracts:
- TVET graduation rates
- Employment rates after vocational training
- Skills certification data
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
logger = setup_logger('tvet_employment')
TABLE_NAME = 'tvet_employment_detail'


def extract_tvet_employment(content: str, url: str, province: str) -> Optional[Dict]:
    """Extract TVET employment statistics"""
    prompt = f"""Phân tích văn bản sau và trả về JSON theo đúng cấu trúc.
Chỉ sử dụng thông tin có trong văn bản, không suy diễn.

Schema:
{{
  "year": null,
  "quarter": null,
  "month": null,
  "total_graduates": null,
  "employed_graduates": null,
  "employment_rate": null,
  "skilled_employment_rate": null,
  "average_salary": null,
  "certification_rate": null,
  "training_completion_rate": null
}}

Giải thích các trường:
- year (integer): Năm của số liệu
- quarter (integer 1-4): Quý (nếu có)
- month (integer 1-12): Tháng (nếu có)
- total_graduates (integer): Tổng số học sinh tốt nghiệp đào tạo nghề
- employed_graduates (integer): Số người có việc làm sau tốt nghiệp
- employment_rate (float): Tỷ lệ có việc làm (%, 0-100)
- skilled_employment_rate (float): Tỷ lệ có việc làm đúng ngành (%, 0-100)
- average_salary (float): Mức lương trung bình (triệu đồng/tháng)
- certification_rate (float): Tỷ lệ có chứng chỉ nghề (%, 0-100)
- training_completion_rate (float): Tỷ lệ hoàn thành khóa đào tạo (%, 0-100)

QUY TẮC QUAN TRỌNG:
1. CHỈ extract nếu văn bản RÕ RÀNG nói về Hưng Yên (hoặc các trung tâm dạy nghề/trường CĐ nghề ở Hưng Yên)
2. Nếu văn bản nói về toàn quốc, tỉnh khác → trả về: {{"no_data": true}}
3. CHỈ trích xuất số liệu CÓ TRONG văn bản về Hưng Yên
4. Linh hoạt với các thuật ngữ:
   - "Dạy nghề", "đào tạo nghề", "nghề nghiệp", "TVET"
   - "Trung cấp", "cao đẳng nghề", "dạy nghề"
   - "Tốt nghiệp", "hoàn thành khóa học"
   - "Có việc làm", "tìm được việc", "đã có việc"
   - "Lương", "thu nhập", "mức thu nhập"
5. Tỷ lệ % chuyển sang số thập phân (85% → 85.0)
6. Lương: chuyển về triệu đồng (5 triệu đồng → 5.0)
7. Nếu trường không có: để null

Tỉnh/Thành cần validate: {province}

Văn bản:
\"\"\"
{content[:3000]}
\"\"\"

Chỉ trả về JSON, không thêm giải thích."""

    result = call_llm(prompt, title="TVET Employment Extractor")
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
    data = extract_tvet_employment(content, url, province)
    if not data:
        logger.info("ℹ️  No TVET employment data found")
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
        "extract_tvet_employment.py",
        "TVET EMPLOYMENT STATISTICS",
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
    log_extraction_summary(logger, len(articles), total_extracted, "TVET Employment")
    
    return {
        "status": "success",
        "processed": len(articles),
        "extracted": total_extracted
    }


if __name__ == "__main__":
    main()
