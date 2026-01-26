#!/usr/bin/env python3
"""
LLM Extract cho Lĩnh vực: Y TẾ

THUẦN LLM - Không dùng Regex

Nguồn dữ liệu:
  - Bảng: important_posts
  - Filter: type_newspaper = 'medical'
  - Số lượng: ~37 posts

Bảng đích (3 bảng):
  1. health_statistics_detail      - Thống kê cơ sở y tế/bác sĩ/giường bệnh
  2. health_insurance_detail       - Bảo hiểm y tế
  3. preventive_health_detail      - Y tế dự phòng/tiêm chủng
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Import SessionLocal
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.database import SessionLocal

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('call_llm/medical_extraction.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:7777")
LLM_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "20"))
DELAY_BETWEEN_CALLS = float(os.getenv("DELAY_BETWEEN_CALLS", "1"))


# ============== DB SAVE FUNCTIONS ==============
def save_to_health_statistics(db, data: Dict) -> bool:
    """Save to health_statistics_detail"""
    try:
        insert_query = text("""
            INSERT INTO health_statistics_detail (
                province, year, quarter, month,
                hospitals, health_stations, clinics,
                doctors_per_10k_pop, nurses_per_10k_pop, beds_per_10k_pop,
                traditional_medicine_facilities,
                data_status, data_source
            ) VALUES (
                :province, :year, :quarter, :month,
                :hospitals, :health_stations, :clinics,
                :doctors_per_10k_pop, :nurses_per_10k_pop, :beds_per_10k_pop,
                :traditional_medicine_facilities,
                :data_status, :data_source
            )
        """)
        db.execute(insert_query, data)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi save health_statistics: {e}")
        db.rollback()
        return False


def save_to_health_insurance(db, data: Dict) -> bool:
    """Save to health_insurance_detail"""
    try:
        insert_query = text("""
            INSERT INTO health_insurance_detail (
                province, year, quarter, month,
                coverage_rate, total_insured, total_population,
                children_coverage_rate, elderly_coverage_rate,
                poor_coverage_rate, near_poor_coverage_rate,
                data_status, data_source
            ) VALUES (
                :province, :year, :quarter, :month,
                :coverage_rate, :total_insured, :total_population,
                :children_coverage_rate, :elderly_coverage_rate,
                :poor_coverage_rate, :near_poor_coverage_rate,
                :data_status, :data_source
            )
        """)
        db.execute(insert_query, data)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi save health_insurance: {e}")
        db.rollback()
        return False


def save_to_preventive_health(db, data: Dict) -> bool:
    """Save to preventive_health_detail"""
    try:
        insert_query = text("""
            INSERT INTO preventive_health_detail (
                province, year, quarter, month,
                vaccination_coverage_rate, vaccination_doses,
                health_screening_count, disease_cases,
                infectious_disease_cases, epidemic_outbreaks,
                data_status, data_source
            ) VALUES (
                :province, :year, :quarter, :month,
                :vaccination_coverage_rate, :vaccination_doses,
                :health_screening_count, :disease_cases,
                :infectious_disease_cases, :epidemic_outbreaks,
                :data_status, :data_source
            )
        """)
        db.execute(insert_query, data)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi save preventive_health: {e}")
        db.rollback()
        return False


def call_llm(prompt: str, max_retries: int = 3) -> Optional[str]:
    """Call OpenRouter LLM API"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": API_BASE_URL,
        "X-Title": "Medical Data Extractor"
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
    return None


def get_posts_from_db(limit: int = 100) -> List[Dict]:
    """Lấy important_posts có type_newspaper = 'medical'"""
    try:
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/DBHuYe")
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        query = text("""
            SELECT id, title, content, url, dvhc, published_date
            FROM important_posts
            WHERE type_newspaper = 'medical'
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
                "province": row[3] or "Unknown",
                "published_date": row[4]
            })
        
        session.close()
        logger.info(f"Tìm thấy {len(posts)} posts (type_newspaper=medical)")
        return posts
        
    except Exception as e:
        logger.error(f"Lỗi khi lấy posts từ DB: {e}")
        return []


def extract_health_statistics(content: str, url: str, province: str) -> Optional[Dict]:
    """Extract thống kê y tế → health_statistics_detail"""
    prompt = f"""Phân tích văn bản sau và trả về JSON theo đúng cấu trúc.
Chỉ sử dụng thông tin có trong văn bản, không suy diễn.

Schema:
{{
  "year": null,
  "quarter": null,
  "month": null,
  "bhyt_coverage_rate": null,
  "total_insured": null,
  "voluntary_insured": null,
  "natural_population_growth_rate": null,
  "elderly_health_checkup_rate": null,
  "sex_ratio_at_birth": null
}}

Giải thích các trường:
- year (integer): Năm của báo cáo
- quarter (integer 1-4): Quý (nếu có)
- month (integer 1-12): Tháng (nếu có)
- bhyt_coverage_rate (float): Tỷ lệ bao phủ BHYT (%, 0-100)
- total_insured (integer): Tổng số người tham gia BHYT
- voluntary_insured (integer): Số người tham gia BHYT tự nguyện
- natural_population_growth_rate (float): Tỷ lệ tăng trưởng dân số tự nhiên (%)
- elderly_health_checkup_rate (float): Tỷ lệ khám sức khỏe người cao tuổi (%, 0-100)
- sex_ratio_at_birth (float): Tỷ lệ giới tính khi sinh (số bé trai/100 bé gái)

Quy tắc:
1. ⚠️ QUAN TRỌNG: CHỈ extract nếu văn bản RÕ RÀNG nói về Hưng Yên (hoặc huyện/thành phố thuộc Hưng Yên)
2. Nếu văn bản nói về toàn quốc, tỉnh khác, hoặc không rõ địa phương → trả về: {{"no_data": true}}
3. CHỈ trích xuất số liệu CÓ TRONG văn bản về Hưng Yên
4. Nếu văn bản KHÔNG đề cập thống kê y tế của Hưng Yên, trả về: {{"no_data": true}}
5. Tỷ lệ % chuyển sang số thập phân (95.5% → 95.5)
6. Thời gian:
   - "Quý I" → quarter=1, "Quý II" → quarter=2, "Quý III" → quarter=3, "Quý IV" → quarter=4
   - "6 tháng đầu năm" / "nửa đầu năm" → quarter=2 (Quý 1+2)
   - "9 tháng đầu năm" → quarter=3 (Quý 1+2+3)
   - "Năm 2024" → year=2024, quarter=null, month=null
7. Nếu trường không có: để null

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
            return None
        
        data["province"] = province
        data["data_source"] = f"Post {post_id}"
        data["data_status"] = "extracted"
        return data
        
    except Exception as e:
        logger.error(f"Lỗi extract health_statistics: {e}")
        return None


def extract_health_insurance(content: str, url: str, province: str) -> Optional[Dict]:
    """Extract bảo hiểm y tế → health_insurance_detail"""
    prompt = f"""Phân tích văn bản sau và trả về JSON theo đúng cấu trúc.
Chỉ sử dụng thông tin có trong văn bản, không suy diễn.

Schema:
{{
  "year": null,
  "quarter": null,
  "month": null,
  "bhyt_coverage_rate": null,
  "total_insured": null,
  "voluntary_insured": null,
  "mandatory_insured": null,
  "poor_near_poor_coverage": null,
  "children_coverage": null,
  "elderly_coverage": null,
  "claims_amount_billion": null
}}

Giải thích các trường:
- year (integer): Năm
- quarter (integer): Quý
- month (integer): Tháng
- bhyt_coverage_rate (float): Tỷ lệ bao phủ BHYT (%, 0-100)
- total_insured (integer): Tổng số người tham gia
- voluntary_insured (integer): Số người tham gia tự nguyện
- mandatory_insured (integer): Số người tham gia bắt buộc
- poor_near_poor_coverage (float): Tỷ lệ bao phủ hộ nghèo/cận nghèo (%)
- children_coverage (float): Tỷ lệ bao phủ trẻ em (%)
- elderly_coverage (float): Tỷ lệ bao phủ người cao tuổi (%)
- claims_amount_billion (float): Số tiền chi trả BHYT (tỷ đồng)

Quy tắc:
1. ⚠️ QUAN TRỌNG: CHỈ extract nếu văn bản RÕ RÀNG nói về Hưng Yên (hoặc huyện/thành phố thuộc Hưng Yên)
2. Nếu văn bản nói về toàn quốc, tỉnh khác, hoặc không rõ địa phương → trả về: {{"no_data": true}}
3. CHỈ trích xuất số liệu CÓ TRONG văn bản về Hưng Yên
4. Nếu văn bản KHÔNG đề cập BHYT của Hưng Yên, trả về: {{"no_data": true}}
5. Thời gian:
   - "Quý I" → quarter=1, "Quý II" → quarter=2, "Quý III" → quarter=3, "Quý IV" → quarter=4
   - "6 tháng đầu năm" / "nửa đầu năm" → quarter=2 (Quý 1+2)
   - "9 tháng đầu năm" → quarter=3 (Quý 1+2+3)
   - "Năm 2024" → year=2024, quarter=null, month=null
6. Nếu trường không có: để null

Tỉnh/Thành cần validate: {province}

Văn bản:
\"\"\"
{content[:3000]}
\"\"\"

Chỉ trả về JSON."""

    try:
        result = call_llm(prompt)
        if not result:
            return None
        
        json_start = result.find("{")
        json_end = result.rfind("}") + 1
        if json_start == -1:
            return None
        
        data = json.loads(result[json_start:json_end])
        
        if data.get("no_data"):
            return None
        
        data["province"] = province
        data["data_source"] = url
        data["data_status"] = "extracted"
        return data
        
    except Exception as e:
        logger.error(f"Lỗi extract health_insurance: {e}")
        return None


def extract_preventive_health(content: str, url: str, province: str) -> Optional[Dict]:
    """Extract y tế dự phòng → preventive_health_detail"""
    prompt = f"""Phân tích văn bản sau và trả về JSON theo đúng cấu trúc.
Chỉ sử dụng thông tin có trong văn bản, không suy diễn.

Schema:
{{
  "year": null,
  "quarter": null,
  "month": null,
  "preventive_health_score": null,
  "vaccination_coverage": null,
  "health_screening_rate": null,
  "disease_surveillance_score": null,
  "epidemic_response_score": null,
  "preventive_facilities": null,
  "health_education_programs": null,
  "clean_water_access_rate": null,
  "sanitation_access_rate": null
}}

Giải thích các trường:
- year (integer): Năm
- quarter (integer): Quý
- month (integer): Tháng
- preventive_health_score (float): Điểm y tế dự phòng (0-100)
- vaccination_coverage (float): Tỷ lệ tiêm chủng (%, 0-100)
- health_screening_rate (float): Tỷ lệ khám sức khỏe định kỳ (%)
- disease_surveillance_score (float): Điểm giám sát dịch bệnh (0-100)
- epidemic_response_score (float): Điểm ứng phó dịch bệnh (0-100)
- preventive_facilities (integer): Số cơ sở y tế dự phòng
- health_education_programs (integer): Số chương trình giáo dục sức khỏe
- clean_water_access_rate (float): Tỷ lệ tiếp cận nước sạch (%)
- sanitation_access_rate (float): Tỷ lệ vệ sinh môi trường (%)

Quy tắc:
1. ⚠️ QUAN TRỌNG: CHỈ extract nếu văn bản RÕ RÀNG nói về Hưng Yên (hoặc huyện/thành phố thuộc Hưng Yên)
2. Nếu văn bản nói về toàn quốc, tỉnh khác, hoặc không rõ địa phương → trả về: {{"no_data": true}}
3. CHỈ trích xuất số liệu CÓ TRONG văn bản về Hưng Yên
4. Nếu văn bản KHÔNG đề cập y tế dự phòng/tiêm chủng của Hưng Yên, trả về: {{"no_data": true}}
5. Thời gian:
   - "Quý I" → quarter=1, "Quý II" → quarter=2, "Quý III" → quarter=3, "Quý IV" → quarter=4
   - "6 tháng đầu năm" / "nửa đầu năm" → quarter=2 (Quý 1+2)
   - "9 tháng đầu năm" → quarter=3 (Quý 1+2+3)
   - "Năm 2024" → year=2024, quarter=null, month=null
6. Nếu trường không có: để null

Tỉnh/Thành cần validate: {province}

Văn bản:
\"\"\"
{content[:3000]}
\"\"\"

Chỉ trả về JSON."""

    try:
        result = call_llm(prompt)
        if not result:
            return None
        
        json_start = result.find("{")
        json_end = result.rfind("}") + 1
        if json_start == -1:
            return None
        
        data = json.loads(result[json_start:json_end])
        
        if data.get("no_data"):
            return None
        
        data["province"] = province
        data["data_source"] = url
        data["data_status"] = "extracted"
        return data
        
    except Exception as e:
        logger.error(f"Lỗi extract preventive_health: {e}")
        return None


def process_post(post: Dict, db) -> Dict[str, int]:
    """Xử lý 1 post - Extract 3 loại thống kê y tế"""
    post_id = post.get("id")
    content = post.get("content", "")
    title = post.get("title", "")
    province = post.get("province", "Unknown")
    url = post.get("url", f"Post {post_id}")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Post ID: {post_id}")
    logger.info(f"Title: {title[:100]}")
    logger.info(f"Province: {province}")
    
    results = {
        "health_statistics": 0,
        "health_insurance": 0,
        "preventive_health": 0
    }
    
    # 1. Health Statistics
    health_stats = extract_health_statistics(content, url, province)
    if health_stats:
        if save_to_health_statistics(db, health_stats):
            logger.info(f"Saved to health_statistics_detail")
            results["health_statistics"] = 1
        else:
            logger.error(f"Failed to save health_statistics")
    
    time.sleep(DELAY_BETWEEN_CALLS)
    
    # 2. Health Insurance
    health_insurance = extract_health_insurance(content, url, province)
    if health_insurance:
        if save_to_health_insurance(db, health_insurance):
            logger.info(f"Saved to health_insurance_detail")
            results["health_insurance"] = 1
        else:
            logger.error(f"Failed to save health_insurance")
    
    time.sleep(DELAY_BETWEEN_CALLS)
    
    # 3. Preventive Health
    preventive_health = extract_preventive_health(content, url, province)
    if preventive_health:
        if save_to_preventive_health(db, preventive_health):
            logger.info(f"Saved to preventive_health_detail")
            results["preventive_health"] = 1
        else:
            logger.error(f"Failed to save preventive_health")
    
    time.sleep(DELAY_BETWEEN_CALLS)
    return results


def main():
    """Main function"""
    logger.info("="*80)
    logger.info("BẮT ĐẦU LLM EXTRACTION - LĨNH VỰC: Y TẾ")
    logger.info(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"LLM Model: {LLM_MODEL}")
    logger.info("="*80)
    
    db = SessionLocal()
    try:
        posts = get_posts_from_db(limit=BATCH_SIZE)
        
        if not posts:
            return {
                "status": "no_data",
                "message": "Không có posts nào (type_newspaper=medical)",
                "processed": 0
            }
        
        total_extracted = {
            "health_statistics": 0,
            "health_insurance": 0,
            "preventive_health": 0
        }
        
        for i, post in enumerate(posts, 1):
            logger.info(f"\nProgress: {i}/{len(posts)}")
            try:
                results = process_post(post, db)
                for key in total_extracted:
                    total_extracted[key] += results.get(key, 0)
            except Exception as e:
                logger.error(f"Lỗi: {e}")
        
        logger.info("\n" + "="*80)
        logger.info(f"Đã xử lý: {len(posts)} posts")
        logger.info(f"Health Statistics: {total_extracted['health_statistics']}")
        logger.info(f"Health Insurance: {total_extracted['health_insurance']}")
        logger.info(f"Preventive Health: {total_extracted['preventive_health']}")
        logger.info(f"Tổng: {sum(total_extracted.values())} records")
        logger.info("="*80)
        
        return {
            "status": "success",
            "processed": len(posts),
            "extracted": total_extracted,
            "total_records": sum(total_extracted.values())
        }
    finally:
        db.close()


if __name__ == "__main__":
    main()
