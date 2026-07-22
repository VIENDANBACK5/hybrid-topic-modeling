#!/usr/bin/env python3
"""
LLM Extract: Cadre Statistics

Source: important_posts (type_newspaper='politics')
Target: cadre_statistics_detail

Extracts:
- Total authorized positions
- Provincial level staff
- Commune level staff  
- Contract workers
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
logger = setup_logger('cadre_statistics')
TABLE_NAME = 'cadre_statistics_detail'


def extract_cadre_statistics(content: str, url: str, province: str) -> Optional[Dict]:
    """Extract cadre statistics (staff/personnel data)"""
    prompt = f"""Phân tích văn bản sau và trả về JSON theo đúng cấu trúc.
Chỉ sử dụng thông tin có trong văn bản, không suy diễn.

Schema:
{{
  "year": null,
  "quarter": null,
  "month": null,
  "total_authorized": null,
  "provincial_level": null,
  "commune_level": null,
  "contract_workers": null
}}

Giải thích các trường:
- year (integer): Năm của báo cáo
- quarter (integer 1-4): Quý (nếu có)
- month (integer 1-12): Tháng (nếu có)
- total_authorized (integer): Tổng số biên chế được giao/tạm giao (người)
- provincial_level (integer): Số biên chế cấp tỉnh/sở ban ngành (người)
- commune_level (integer): Số biên chế cấp xã/phường/thị trấn (người)
- contract_workers (integer): Số lao động hợp đồng (người)

Quy tắc:
1. QUAN TRỌNG: CHỈ extract nếu văn bản RÕ RÀNG nói về Hưng Yên (Đảng bộ tỉnh Hưng Yên hoặc các huyện/thành phố thuộc Hưng Yên)
2. Nếu văn bản nói về toàn quốc, đảng bộ tỉnh khác, hoặc không rõ địa phương → trả về: {{"no_data": true}}
3. CHỈ trích xuất số liệu CÓ TRONG văn bản về Hưng Yên
4. Nếu văn bản KHÔNG đề cập thống kê cán bộ/biên chế của Hưng Yên, trả về: {{"no_data": true}}
5. Các số phải là INTEGER (làm tròn nếu cần)
6. Nếu trường không có trong văn bản: để null

Tỉnh/Thành cần validate: {province}

Văn bản:
\"\"\"
{content[:3000]}
\"\"\"

Chỉ trả về JSON, không thêm giải thích."""

    result = call_llm(prompt, title="Cadre Statistics Extractor")
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
    data = extract_cadre_statistics(content, url, province)
    if not data:
        logger.info("ℹ️  No cadre statistics data found")
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
        "extract_cadre_statistics.py",
        "CADRE STATISTICS (Biên chế & Cán bộ)",
        BATCH_SIZE
    )
    
    # Fetch posts from politics
    articles = get_posts_from_db("politics", limit=BATCH_SIZE, logger=logger)
    
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
    log_extraction_summary(logger, len(articles), total_extracted, "Cadre Statistics")
    
    return {
        "status": "success",
        "processed": len(articles),
        "extracted": total_extracted
    }


if __name__ == "__main__":
    main()
