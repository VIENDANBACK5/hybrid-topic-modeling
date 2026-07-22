#!/usr/bin/env python3
"""
LLM Extract: PAR Index (Public Administration Reform Index)

Source: articles table
Target: par_index_detail

Extracts provincial administrative reform performance metrics
"""

import sys
import os
from typing import Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base_extractor import (
    setup_logger, call_llm, parse_llm_json, save_to_detail_table,
    log_extraction_start, log_article_info, log_extraction_summary,
    validate_api_key, BATCH_SIZE, DELAY_BETWEEN_CALLS, API_BASE_URL
)
import time
import requests

logger = setup_logger('par_index')
TABLE_NAME = 'par_index_detail'


def get_articles_from_api(limit: int = 100) -> list:
    """Fetch articles from API"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/articles",
            params={"page": 1, "page_size": limit},
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        articles = result.get("items", result.get("data", []))
        logger.info(f"Found {len(articles)} articles from API")
        return articles
    except Exception as e:
        logger.error(f"Error fetching articles: {e}")
        return []


def extract_par_index(content: str, url: str, province: str) -> Optional[Dict]:
    """Extract PAR Index data"""
    prompt = f"""Phân tích văn bản và trích xuất chỉ số Cải cách hành chính (PAR Index).

Schema:
{{
  "year": null,
  "quarter": null,
  "par_index_score": null,
  "ranking": null,
  "improved_procedures": null,
  "digital_services_rate": null,
  "citizen_satisfaction": null
}}

Giải thích:
- year: Năm
- quarter: Quý (1-4)
- par_index_score: Điểm PAR Index (0-100)
- ranking: Xếp hạng toàn quốc
- improved_procedures: Số thủ tục được cải thiện
- digital_services_rate: Tỷ lệ dịch vụ số (%)
- citizen_satisfaction: Mức độ hài lòng người dân (%)

Quy tắc:
1. CHỈ extract nếu về {province}
2. Nếu không về {province} → {{"no_data": true}}
3. Nếu không có dữ liệu PAR → {{"no_data": true}}

Văn bản:
\"\"\"{content[:3000]}\"\"\"

Chỉ trả về JSON."""

    result = call_llm(prompt, title="PAR Index Extractor")
    if not result:
        return None
    
    data = parse_llm_json(result, logger)
    if not data:
        return None
    
    data["province"] = province
    data["data_source"] = url
    data["document_type"] = "external"  # articles always external
    return data


def main():
    validate_api_key()
    log_extraction_start(logger, "extract_par_index.py", "PAR INDEX", BATCH_SIZE)
    
    articles = get_articles_from_api(limit=BATCH_SIZE)
    if not articles:
        return {"status": "no_data", "processed": 0, "extracted": 0}
    
    total_extracted = 0
    for i, article in enumerate(articles, 1):
        try:
            content = article.get("content", "")
            url = article.get("url", "")
            province = article.get("province", "Hưng Yên")
            
            data = extract_par_index(content, url, province)
            if data and save_to_detail_table(data, TABLE_NAME, logger):
                total_extracted += 1
            time.sleep(DELAY_BETWEEN_CALLS)
        except Exception as e:
            logger.error(f"Error: {e}")
    
    log_extraction_summary(logger, len(articles), total_extracted, "PAR Index")
    return {"status": "success", "processed": len(articles), "extracted": total_extracted}


if __name__ == "__main__":
    main()
