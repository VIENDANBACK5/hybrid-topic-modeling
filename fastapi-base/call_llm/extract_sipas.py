#!/usr/bin/env python3
"""
LLM Extract: SIPAS (Satisfaction Index of Public Administrative Services)

Source: articles table  
Target: sipas_detail

Extracts public service satisfaction metrics
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

logger = setup_logger('sipas')
TABLE_NAME = 'sipas_detail'


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
        logger.info(f"Found {len(articles)} articles")
        return articles
    except Exception as e:
        logger.error(f"Error: {e}")
        return []


def extract_sipas(content: str, url: str, province: str) -> Optional[Dict]:
    """Extract SIPAS data"""
    prompt = f"""Phân tích văn bản và trích xuất chỉ số Hài lòng dịch vụ hành chính (SIPAS).

Schema:
{{
  "year": null,
  "quarter": null,
  "sipas_score": null,
  "ranking": null,
  "service_quality_score": null,
  "staff_attitude_score": null,
  "procedure_efficiency_score": null
}}

Giải thích:
- year: Năm
- quarter: Quý (1-4)
- sipas_score: Điểm SIPAS tổng (0-100)
- ranking: Xếp hạng
- service_quality_score: Điểm chất lượng dịch vụ
- staff_attitude_score: Điểm thái độ cán bộ
- procedure_efficiency_score: Điểm hiệu quả thủ tục

Quy tắc:
1. CHỈ extract về {province}
2. Không về {province} → {{"no_data": true}}

Văn bản:
\"\"\"{content[:3000]}\"\"\"

JSON only."""

    result = call_llm(prompt, title="SIPAS Extractor")
    if not result:
        return None
    
    data = parse_llm_json(result, logger)
    if not data:
        return None
    
    data["province"] = province
    data["data_source"] = url
    data["document_type"] = "external"
    return data


def main():
    validate_api_key()
    log_extraction_start(logger, "extract_sipas.py", "SIPAS", BATCH_SIZE)
    
    articles = get_articles_from_api(limit=BATCH_SIZE)
    if not articles:
        return {"status": "no_data", "processed": 0, "extracted": 0}
    
    total_extracted = 0
    for i, article in enumerate(articles, 1):
        try:
            content = article.get("content", "")
            url = article.get("url", "")
            province = article.get("province", "Hưng Yên")
            
            data = extract_sipas(content, url, province)
            if data and save_to_detail_table(data, TABLE_NAME, logger):
                total_extracted += 1
            time.sleep(DELAY_BETWEEN_CALLS)
        except Exception as e:
            logger.error(f"Error: {e}")
    
    log_extraction_summary(logger, len(articles), total_extracted, "SIPAS")
    return {"status": "success", "processed": len(articles), "extracted": total_extracted}


if __name__ == "__main__":
    main()
