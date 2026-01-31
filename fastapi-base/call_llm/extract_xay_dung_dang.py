#!/usr/bin/env python3
"""
LLM Extract cho Lĩnh vực: XÂY DỰNG ĐẢNG & HỆ THỐNG CHÍNH TRỊ

THUẦN LLM - Không dùng Regex

Nguồn dữ liệu:
  - Bảng: important_posts
  - Filter: type_newspaper = 'politics'
  - Số lượng: ~3 posts

Bảng đích (3 bảng):
  1. cadre_statistics_detail       - Thống kê số lượng cán bộ/biên chế
  2. party_discipline_detail       - Kỷ luật Đảng/vi phạm
  3. cadre_quality_detail          - Chất lượng cán bộ/đào tạo
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('call_llm/xay_dung_dang_extraction.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:7777")
LLM_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10"))
DELAY_BETWEEN_CALLS = float(os.getenv("DELAY_BETWEEN_CALLS", "2"))  # seconds

if not LLM_API_KEY:
    logger.error("Không tìm thấy API key")
    sys.exit(1)


def call_llm(prompt: str, max_retries: int = 3) -> Optional[str]:
    """Call OpenRouter LLM API"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": API_BASE_URL,
        "X-Title": "Xay Dung Dang Extractor"
    }
    
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 3000
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"LLM call attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                logger.error(f"LLM call failed after {max_retries} attempts")
                return None


def extract_cadre_statistics(content: str, url: str, province: str) -> Optional[Dict]:
    """Extract thống kê số lượng cán bộ"""
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

    try:
        result = call_llm(prompt)
        if not result:
            return None
        
        # Parse JSON
        json_start = result.find("{")
        json_end = result.rfind("}") + 1
        if json_start == -1 or json_end == 0:
            logger.warning(f"Không tìm thấy JSON trong response")
            return None
        
        data = json.loads(result[json_start:json_end])
        
        if data.get("no_data"):
            logger.info(f"ℹ️  Không có thông tin thống kê cán bộ")
            return None
        
        # Thêm metadata
        data["province"] = province
        data["data_source"] = url
        
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"Lỗi parse JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Lỗi extract cadre statistics cho article {url}: {e}")
        return None


def extract_party_discipline(content: str, url: str, province: str) -> Optional[Dict]:
    """Extract thống kê kỷ luật Đảng"""
    prompt = f"""Phân tích văn bản sau và trả về JSON theo đúng cấu trúc.
Chỉ sử dụng thông tin có trong văn bản, không suy diễn.

Schema:
{{
  "year": null,
  "quarter": null,
  "month": null,
  "dci_score": null,
  "discipline_violations": null,
  "warnings_issued": null,
  "dismissals": null,
  "compliance_rate": null,
  "regulation_adherence_score": null
}}

Giải thích các trường:
- year (integer): Năm của báo cáo
- quarter (integer 1-4): Quý (nếu có)
- month (integer 1-12): Tháng (nếu có)
- dci_score (float): Điểm chỉ số kỷ luật Đảng DCI (0-100)
- discipline_violations (integer): Số vụ vi phạm kỷ luật Đảng
- warnings_issued (integer): Số trường hợp bị cảnh cáo
- dismissals (integer): Số trường hợp bị khai trừ/cách chức
- compliance_rate (float): Tỷ lệ tuân thủ kỷ luật (%, 0-100)
- regulation_adherence_score (float): Điểm chấp hành nội quy (0-100)

Quy tắc:
1. QUAN TRỌNG: CHỈ extract nếu văn bản RÕ RÀNG nói về Hưng Yên (Đảng bộ tỉnh Hưng Yên hoặc các huyện/thành phố thuộc Hưng Yên)
2. Nếu văn bản nói về toàn quốc, đảng bộ tỉnh khác, hoặc không rõ địa phương → trả về: {{"no_data": true}}
3. CHỈ trích xuất số liệu CÓ TRONG văn bản về Hưng Yên
4. Nếu văn bản KHÔNG đề cập kỷ luật Đảng/vi phạm/khai trừ của Hưng Yên, trả về: {{"no_data": true}}
5. Tỷ lệ % chuyển sang số thập phân (98.5% → 98.5)
6. Nếu trường không có trong văn bản: để null

Tỉnh/Thành cần validate: {province}

Văn bản:
\"\"\"
{content[:3000]}
\"\"\"

Chỉ trả về JSON, không thêm giải thích."""

    try:
        result = call_llm(prompt)
        if not result:
            return None
        
        json_start = result.find("{")
        json_end = result.rfind("}") + 1
        if json_start == -1 or json_end == 0:
            return None
        
        data = json.loads(result[json_start:json_end])
        
        if data.get("no_data"):
            logger.info(f"ℹ️  URL {url} không có thông tin kỷ luật Đảng")
            return None
        
        data["province"] = province
        data["url"] = url
        data["data_source"] = f"URL {url}"
        
        return data
        
    except Exception as e:
        logger.error(f"Lỗi extract party discipline cho article {url}: {e}")
        return None


def extract_cadre_quality(content: str, url: str, province: str) -> Optional[Dict]:
    """Extract chất lượng cán bộ"""
    prompt = f"""Phân tích văn bản sau và trả về JSON theo đúng cấu trúc.
Chỉ sử dụng thông tin có trong văn bản, không suy diễn.

Schema:
{{
  "year": null,
  "quarter": null,
  "month": null,
  "total_cadres": null,
  "cadres_with_degree": null,
  "degree_rate": null,
  "training_completion_rate": null,
  "performance_score": null,
  "citizen_satisfaction": null,
  "policy_implementation_score": null
}}

Giải thích các trường:
- year (integer): Năm của báo cáo
- quarter (integer 1-4): Quý (nếu có)
- month (integer 1-12): Tháng (nếu có)
- total_cadres (integer): Tổng số cán bộ/công chức
- cadres_with_degree (integer): Số cán bộ có bằng cấp/trình độ đại học trở lên
- degree_rate (float): Tỷ lệ cán bộ có bằng cấp (%, 0-100)
- training_completion_rate (float): Tỷ lệ hoàn thành đào tạo/bồi dưỡng (%, 0-100)
- performance_score (float): Điểm đánh giá hiệu quả công tác (0-100)
- citizen_satisfaction (float): Mức độ hài lòng của người dân/doanh nghiệp (%, 0-100)
- policy_implementation_score (float): Điểm thực thi chính sách/nhiệm vụ (0-100)

Quy tắc:
1. QUAN TRỌNG: CHỈ extract nếu văn bản RÕ RÀNG nói về Hưng Yên (Đảng bộ tỉnh Hưng Yên hoặc các huyện/thành phố thuộc Hưng Yên)
2. Nếu văn bản nói về toàn quốc, đảng bộ tỉnh khác, hoặc không rõ địa phương → trả về: {{"no_data": true}}
3. CHỈ trích xuất số liệu CÓ TRONG văn bản về Hưng Yên
4. Nếu văn bản KHÔNG đề cập chất lượng cán bộ/đào tạo/trình độ của Hưng Yên, trả về: {{"no_data": true}}
5. Tỷ lệ % chuyển sang số thập phân (90.5% → 90.5)
6. Nếu trường không có trong văn bản: để null

Tỉnh/Thành cần validate: {province}

Văn bản:
\"\"\"
{content[:3000]}
\"\"\"

Chỉ trả về JSON, không thêm giải thích."""

    try:
        result = call_llm(prompt)
        if not result:
            return None
        
        json_start = result.find("{")
        json_end = result.rfind("}") + 1
        if json_start == -1 or json_end == 0:
            return None
        
        data = json.loads(result[json_start:json_end])
        
        if data.get("no_data"):
            logger.info(f"ℹ️  URL {url} không có thông tin chất lượng cán bộ")
            return None
        
        data["province"] = province
        data["url"] = url
        data["data_source"] = f"URL {url}"
        
        return data
        
    except Exception as e:
        logger.error(f"Lỗi extract cadre quality cho article {url}: {e}")
        return None


def save_to_detail_table(data: Dict, table_name: str) -> bool:
    """Lưu data vào bảng detail"""
    # Map url to economic_indicator_id if needed
    if "url" in data:
        data["economic_indicator_id"] = data.pop("url")
    
    endpoint = f"{API_BASE_URL}/api/indicators/{table_name}"
    
    try:
        response = requests.post(endpoint, json=data, timeout=30)
        
        if response.status_code in [200, 201]:
            logger.info(f"Đã lưu vào {table_name}")
            return True
        elif response.status_code == 409 or "duplicate" in response.text.lower():
            logger.info(f"ℹ️  {table_name} đã tồn tại (skip)")
            return True
        else:
            logger.error(f"Lỗi lưu {table_name}: {response.status_code} - {response.text[:200]}")
            return False
            
    except Exception as e:
        logger.error(f"Exception khi lưu {table_name}: {e}")
        return False


def get_politics_posts_from_db(limit: int = 100) -> List[Dict]:
    """Lấy important_posts có type_newspaper = 'politics' trực tiếp từ DB"""
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    import os
    
    try:
        # Get DB connection
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/DBHuYe")
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Query important_posts WITH document_type
        query = text("""
            SELECT id, title, content, url, dvhc, published_date, document_type
            FROM important_posts
            WHERE type_newspaper = 'politics'
              AND (document_type IS NULL OR document_type != 'internal')
            ORDER BY id DESC
            LIMIT :limit
        """)
        
        result = session.execute(query, {"limit": limit})
        posts = []
        
        for row in result:
            posts.append({
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "url": row[3],
                "province": row[4] or "Hưng Yên",
                "published_date": row[5],
                "document_type": row[6] or "external"
            })
        
        session.close()
        logger.info(f"Tìm thấy {len(posts)} posts từ important_posts (type_newspaper=politics)")
        return posts
        
    except Exception as e:
        logger.error(f"Lỗi khi lấy posts từ DB: {e}")
        return []


def get_politics_articles(limit: int = 100) -> List[Dict]:
    """Lấy articles về chính trị"""
    try:
        all_articles = []
        page = 1
        
        while len(all_articles) < limit:
            response = requests.get(
                f"{API_BASE_URL}/api/articles",
                params={
                    "page": page,
                    "page_size": min(100, limit - len(all_articles)),
                    "category": "politics"  # Filter by politics category
                },
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            articles = result.get("items", result.get("data", []))
            if not articles:
                break
                
            all_articles.extend(articles)
            
            if len(articles) < 100:  # No more pages
                break
            
            page += 1
        
        logger.info(f"Tìm thấy {len(all_articles)} articles về chính trị")
        return all_articles[:limit]
        
    except Exception as e:
        logger.error(f"Lỗi khi lấy articles: {e}")
        return []


def process_article(article: Dict) -> Dict[str, int]:
    """Xử lý 1 article và extract cả 3 loại thống kê"""
    url = article.get("id")
    content = article.get("content", "")
    title = article.get("title", "")
    province = article.get("province", "Hưng Yên")
    document_type = article.get("document_type", "external")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"URL ID: {url}")
    logger.info(f"Title: {title[:100]}")
    logger.info(f"Province: {province}")
    logger.info(f"Content length: {len(content)} chars")
    
    results = {
        "cadre_statistics": 0,
        "party_discipline": 0,
        "cadre_quality": 0
    }
    
    # 1. Extract cadre statistics
    logger.info("💼 Extracting cadre statistics...")
    cadre_stats = extract_cadre_statistics(content, url, province)
    if cadre_stats:
        cadre_stats["document_type"] = document_type
        if save_to_detail_table(cadre_stats, "cadre_statistics_detail"):
            results["cadre_statistics"] = 1
    time.sleep(DELAY_BETWEEN_CALLS)
    
    # 2. Extract party discipline
    logger.info("⚖️  Extracting party discipline...")
    party_disc = extract_party_discipline(content, url, province)
    if party_disc:
        party_disc["document_type"] = document_type
        if save_to_detail_table(party_disc, "party_discipline_detail"):
            results["party_discipline"] = 1
    time.sleep(DELAY_BETWEEN_CALLS)
    
    # 3. Extract cadre quality
    logger.info("⭐ Extracting cadre quality...")
    cadre_qual = extract_cadre_quality(content, url, province)
    if cadre_qual:
        cadre_qual["document_type"] = document_type
        if save_to_detail_table(cadre_qual, "cadre_quality_detail"):
            results["cadre_quality"] = 1
    time.sleep(DELAY_BETWEEN_CALLS)
    
    return results


def main():
    """Main function"""
    logger.info("="*80)
    logger.info("BẮT ĐẦU LLM EXTRACTION - LĨNH VỰC 1: XÂY DỰNG ĐẢNG")
    logger.info(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"LLM Model: {LLM_MODEL}")
    logger.info(f"📦 Batch size: {BATCH_SIZE}")
    logger.info("="*80)
    
    # Lấy posts từ important_posts (type_newspaper='politics')
    articles = get_politics_posts_from_db(limit=BATCH_SIZE)
    
    if not articles:
        logger.info("Không có articles nào cần xử lý")
        return {
            "status": "no_data",
            "message": "Không có posts nào trong important_posts với type_newspaper=politics",
            "processed": 0,
            "extracted": 0
        }
    
    # Process articles
    total_extracted = {
        "cadre_statistics": 0,
        "party_discipline": 0,
        "cadre_quality": 0
    }
    
    for i, article in enumerate(articles, 1):
        logger.info(f"\nProgress: {i}/{len(articles)}")
        
        try:
            results = process_article(article)
            
            for key, value in results.items():
                total_extracted[key] += value
                
        except Exception as e:
            logger.error(f"Lỗi khi xử lý article {article.get('id')}: {e}")
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("KẾT QUẢ EXTRACTION")
    logger.info("="*80)
    logger.info(f"Đã xử lý: {len(articles)} articles")
    logger.info(f"💼 Cadre Statistics extracted: {total_extracted['cadre_statistics']}")
    logger.info(f"⚖️  Party Discipline extracted: {total_extracted['party_discipline']}")
    logger.info(f"⭐ Cadre Quality extracted: {total_extracted['cadre_quality']}")
    logger.info(f"Tổng: {sum(total_extracted.values())} records")
    logger.info("="*80)
    
    # Return results
    return {
        "status": "success",
        "message": "LLM extraction hoàn thành",
        "processed": len(articles),
        "extracted": total_extracted,
        "total_records": sum(total_extracted.values())
    }


if __name__ == "__main__":
    main()
