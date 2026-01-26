#!/usr/bin/env python3
"""
LLM Extract cho Lĩnh vực: VĂN HÓA - XÃ HỘI

THUẦN LLM - Không dùng Regex

Nguồn dữ liệu:
  - Bảng: important_posts
  - Filter: type_newspaper = 'society'
  - Số lượng: ~5 posts

Bảng đích (4 bảng):
  1. culture_lifestyle_stats_detail - Văn hóa/lối sống/phong trào
  2. cultural_infrastructure_detail - Cơ sở văn hóa/di tích
  3. culture_sport_access_detail    - Thể thao/thể dục thể thao
  4. social_security_coverage_detail - Bảo trợ xã hội/chính sách xã hội
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
        logging.FileHandler('call_llm/society_extraction.log'),
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
def save_to_culture_lifestyle_stats(db, data: Dict) -> bool:
    """Save to culture_lifestyle_stats_detail"""
    try:
        insert_query = text("""
            INSERT INTO culture_lifestyle_stats_detail (
                province, year, quarter, month,
                cultural_events, participants, festivals_held,
                traditional_craft_villages, cultural_clubs,
                lifestyle_improvement_programs,
                data_status, data_source
            ) VALUES (
                :province, :year, :quarter, :month,
                :cultural_events, :participants, :festivals_held,
                :traditional_craft_villages, :cultural_clubs,
                :lifestyle_improvement_programs,
                :data_status, :data_source
            )
        """)
        db.execute(insert_query, data)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi save culture_lifestyle_stats: {e}")
        db.rollback()
        return False


def save_to_cultural_infrastructure(db, data: Dict) -> bool:
    """Save to cultural_infrastructure_detail"""
    try:
        insert_query = text("""
            INSERT INTO cultural_infrastructure_detail (
                province, year, quarter, month,
                cultural_houses, libraries, museums,
                historical_sites, art_performance_venues,
                sports_facilities,
                data_status, data_source
            ) VALUES (
                :province, :year, :quarter, :month,
                :cultural_houses, :libraries, :museums,
                :historical_sites, :art_performance_venues,
                :sports_facilities,
                :data_status, :data_source
            )
        """)
        db.execute(insert_query, data)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi save cultural_infrastructure: {e}")
        db.rollback()
        return False


def save_to_culture_sport_access(db, data: Dict) -> bool:
    """Save to culture_sport_access_detail"""
    try:
        insert_query = text("""
            INSERT INTO culture_sport_access_detail (
                province, year, quarter, month,
                sports_participants, sports_competitions,
                athletes_trained, sports_clubs,
                physical_activity_rate, youth_sports_programs,
                data_status, data_source
            ) VALUES (
                :province, :year, :quarter, :month,
                :sports_participants, :sports_competitions,
                :athletes_trained, :sports_clubs,
                :physical_activity_rate, :youth_sports_programs,
                :data_status, :data_source
            )
        """)
        db.execute(insert_query, data)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi save culture_sport_access: {e}")
        db.rollback()
        return False


def save_to_social_security_coverage(db, data: Dict) -> bool:
    """Save to social_security_coverage_detail"""
    try:
        insert_query = text("""
            INSERT INTO social_security_coverage_detail (
                province, year, quarter, month,
                social_assistance_beneficiaries, poor_households_supported,
                disability_support_cases, elderly_care_recipients,
                child_welfare_cases, social_protection_coverage_rate,
                data_status, data_source
            ) VALUES (
                :province, :year, :quarter, :month,
                :social_assistance_beneficiaries, :poor_households_supported,
                :disability_support_cases, :elderly_care_recipients,
                :child_welfare_cases, :social_protection_coverage_rate,
                :data_status, :data_source
            )
        """)
        db.execute(insert_query, data)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi save social_security_coverage: {e}")
        db.rollback()
        return False


def call_llm(prompt: str, max_retries: int = 3) -> Optional[str]:
    """Call OpenRouter LLM API"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": API_BASE_URL,
        "X-Title": "Society Data Extractor"
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
    """Lấy important_posts có type_newspaper = 'society'"""
    try:
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/DBHuYe")
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        query = text("""
            SELECT id, title, content, url, dvhc, published_date
            FROM important_posts
            WHERE type_newspaper = 'society'
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
        logger.info(f"Tìm thấy {len(posts)} posts (type_newspaper=society)")
        return posts
        
    except Exception as e:
        logger.error(f"Lỗi khi lấy posts từ DB: {e}")
        return []


def extract_culture_lifestyle_stats(content: str, post_id: int, province: str) -> Optional[Dict]:
    """Extract văn hóa lối sống → culture_lifestyle_stats_detail"""
    prompt = f"""Phân tích văn bản sau và trả về JSON theo đúng cấu trúc.
Chỉ sử dụng thông tin có trong văn bản, không suy diễn.

Schema:
{{
  "year": null,
  "quarter": null,
  "month": null,
  "total_heritage_sites": null,
  "tourist_visitors": null,
  "tourism_revenue_billion": null,
  "natural_population_growth_rate": null,
  "elderly_health_checkup_rate": null,
  "sex_ratio_at_birth": null
}}

Giải thích các trường:
- year (integer): Năm
- quarter (integer): Quý
- month (integer): Tháng
- total_heritage_sites (integer): Tổng số di tích lịch sử/văn hóa
- tourist_visitors (float): Số lượt khách du lịch (triệu người)
- tourism_revenue_billion (float): Doanh thu du lịch (tỷ đồng)
- natural_population_growth_rate (float): Tỷ lệ tăng trưởng dân số tự nhiên (%)
- elderly_health_checkup_rate (float): Tỷ lệ khám sức khỏe người cao tuổi (%, 0-100)
- sex_ratio_at_birth (float): Tỷ lệ giới tính khi sinh (nam/100 nữ)

Quy tắc:
1. ⚠️ QUAN TRỌNG: CHỈ extract nếu văn bản RÕ RÀNG nói về Hưng Yên (hoặc huyện/thành phố thuộc Hưng Yên)
2. Nếu văn bản nói về toàn quốc, tỉnh khác, hoặc không rõ địa phương → trả về: {{"no_data": true}}
3. CHỈ trích xuất số liệu CÓ TRONG văn bản về Hưng Yên
4. Nếu văn bản KHÔNG đề cập văn hóa/du lịch của Hưng Yên, trả về: {{"no_data": true}}
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
        data["data_source"] = f"Post {post_id}"
        data["data_status"] = "extracted"
        return data
        
    except Exception as e:
        logger.error(f"Lỗi extract culture_lifestyle: {e}")
        return None


def extract_cultural_infrastructure(content: str, post_id: int, province: str) -> Optional[Dict]:
    """Extract cơ sở văn hóa → cultural_infrastructure_detail"""
    prompt = f"""Phân tích văn bản sau và trả về JSON theo đúng cấu trúc.
Chỉ sử dụng thông tin có trong văn bản, không suy diễn.

Schema:
{{
  "year": null,
  "quarter": null,
  "month": null,
  "total_facilities": null,
  "libraries": null,
  "museums": null,
  "theaters": null,
  "cultural_houses": null,
  "heritage_sites": null,
  "quality_score": null,
  "utilization_rate": null
}}

Giải thích các trường:
- year (integer): Năm
- quarter (integer): Quý
- month (integer): Tháng
- total_facilities (integer): Tổng số cơ sở văn hóa
- libraries (integer): Số thư viện
- museums (integer): Số bảo tàng
- theaters (integer): Số nhà hát/rạp chiếu phim
- cultural_houses (integer): Số nhà văn hóa cộng đồng
- heritage_sites (integer): Số di tích
- quality_score (float): Điểm chất lượng cơ sở (0-100)
- utilization_rate (float): Tỷ lệ sử dụng/hoạt động (%, 0-100)

Quy tắc:
1. ⚠️ QUAN TRỌNG: CHỈ extract nếu văn bản RÕ RÀNG nói về Hưng Yên (hoặc huyện/thành phố thuộc Hưng Yên)
2. Nếu văn bản nói về toàn quốc, tỉnh khác, hoặc không rõ địa phương → trả về: {{"no_data": true}}
3. CHỈ trích xuất số liệu CÓ TRONG văn bản về Hưng Yên
4. Nếu văn bản KHÔNG đề cập cơ sở văn hóa của Hưng Yên, trả về: {{"no_data": true}}
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
        data["data_source"] = f"Post {post_id}"
        data["data_status"] = "extracted"
        return data
        
    except Exception as e:
        logger.error(f"Lỗi extract cultural_infrastructure: {e}")
        return None


def extract_culture_sport_access(content: str, post_id: int, province: str) -> Optional[Dict]:
    """Extract thể thao/thể dục → culture_sport_access_detail"""
    prompt = f"""Phân tích văn bản sau và trả về JSON theo đúng cấu trúc.
Chỉ sử dụng thông tin có trong văn bản, không suy diễn.

Schema:
{{
  "year": null,
  "quarter": null,
  "month": null,
  "acss_score": null,
  "cultural_facilities_per_capita": null,
  "sport_facilities_per_capita": null,
  "participation_rate": null,
  "access_distance_km": null,
  "affordability_score": null
}}

Giải thích các trường:
- year (integer): Năm
- quarter (integer): Quý
- month (integer): Tháng
- acss_score (float): Điểm tiếp cận văn hóa thể thao (0-100)
- cultural_facilities_per_capita (float): Số cơ sở văn hóa/1000 dân
- sport_facilities_per_capita (float): Số cơ sở thể thao/1000 dân
- participation_rate (float): Tỷ lệ tham gia hoạt động văn hóa/thể thao (%, 0-100)
- access_distance_km (float): Khoảng cách trung bình đến cơ sở (km)
- affordability_score (float): Điểm khả năng chi trả (0-100)

Quy tắc:
1. ⚠️ QUAN TRỌNG: CHỈ extract nếu văn bản RÕ RÀNG nói về Hưng Yên (hoặc huyện/thành phố thuộc Hưng Yên)
2. Nếu văn bản nói về toàn quốc, tỉnh khác, hoặc không rõ địa phương → trả về: {{"no_data": true}}
3. CHỈ trích xuất số liệu CÓ TRONG văn bản về Hưng Yên
4. Nếu văn bản KHÔNG đề cập thể thao/hoạt động văn hóa của Hưng Yên, trả về: {{"no_data": true}}
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
        data["data_source"] = f"Post {post_id}"
        data["data_status"] = "extracted"
        return data
        
    except Exception as e:
        logger.error(f"Lỗi extract culture_sport_access: {e}")
        return None


def extract_social_security_coverage(content: str, post_id: int, province: str) -> Optional[Dict]:
    """Extract bảo trợ xã hội → social_security_coverage_detail"""
    prompt = f"""Phân tích văn bản sau và trả về JSON theo đúng cấu trúc.
Chỉ sử dụng thông tin có trong văn bản, không suy diễn.

Schema:
{{
  "year": null,
  "quarter": null,
  "month": null,
  "coverage_rate": null,
  "health_insurance_coverage": null,
  "social_insurance_coverage": null,
  "unemployment_insurance_coverage": null,
  "pension_coverage": null,
  "beneficiaries_count": null,
  "vulnerable_group_coverage": null
}}

Giải thích các trường:
- year (integer): Năm
- quarter (integer): Quý
- month (integer): Tháng
- coverage_rate (float): Tỷ lệ bao phủ an sinh xã hội tổng (%, 0-100)
- health_insurance_coverage (float): Tỷ lệ bao phủ BHYT (%, 0-100)
- social_insurance_coverage (float): Tỷ lệ bao phủ BHXH (%, 0-100)
- unemployment_insurance_coverage (float): Tỷ lệ bao phủ bảo hiểm thất nghiệp (%, 0-100)
- pension_coverage (float): Tỷ lệ bao phủ trợ cấp hưu trí (%, 0-100)
- beneficiaries_count (integer): Số người thưởng hưởng chính sách an sinh
- vulnerable_group_coverage (float): Tỷ lệ bao phủ nhóm dễ tổn thương (%, 0-100)

Quy tắc:
1. ⚠️ QUAN TRỌNG: CHỈ extract nếu văn bản RÕ RÀNG nói về Hưng Yên (hoặc huyện/thành phố thuộc Hưng Yên)
2. Nếu văn bản nói về toàn quốc, tỉnh khác, hoặc không rõ địa phương → trả về: {{"no_data": true}}
3. CHỈ trích xuất số liệu CÓ TRONG văn bản về Hưng Yên
4. Nếu văn bản KHÔNG đề cập bảo trợ xã hội/hộ nghèo của Hưng Yên, trả về: {{"no_data": true}}
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
        data["data_source"] = f"Post {post_id}"
        data["data_status"] = "extracted"
        return data
        
    except Exception as e:
        logger.error(f"Lỗi extract social_security: {e}")
        return None


def process_post(post: Dict, db) -> Dict[str, int]:
    """Xử lý 1 post - Extract 4 loại thống kê văn hóa xã hội"""
    post_id = post.get("id")
    content = post.get("content", "")
    title = post.get("title", "")
    province = post.get("province", "Unknown")
    url = post.get("url", f"Post {post_id}")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Post ID: {post_id}")
    logger.info(f"Title: {title[:100]}")
    
    results = {
        "culture_lifestyle": 0,
        "cultural_infrastructure": 0,
        "culture_sport_access": 0,
        "social_security": 0
    }
    
    # 1. Culture Lifestyle Stats
    culture_life = extract_culture_lifestyle_stats(content, url, province)
    if culture_life:
        if save_to_culture_lifestyle_stats(db, culture_life):
            logger.info(f"Saved to culture_lifestyle_stats_detail")
            results["culture_lifestyle"] = 1
        else:
            logger.error(f"Failed to save culture_lifestyle_stats")
    
    time.sleep(DELAY_BETWEEN_CALLS)
    
    # 2. Cultural Infrastructure
    culture_infra = extract_cultural_infrastructure(content, url, province)
    if culture_infra:
        if save_to_cultural_infrastructure(db, culture_infra):
            logger.info(f"Saved to cultural_infrastructure_detail")
            results["cultural_infrastructure"] = 1
        else:
            logger.error(f"Failed to save cultural_infrastructure")
    
    time.sleep(DELAY_BETWEEN_CALLS)
    
    # 3. Culture Sport Access
    sport_access = extract_culture_sport_access(content, url, province)
    if sport_access:
        if save_to_culture_sport_access(db, sport_access):
            logger.info(f"Saved to culture_sport_access_detail")
            results["culture_sport_access"] = 1
        else:
            logger.error(f"Failed to save culture_sport_access")
    
    time.sleep(DELAY_BETWEEN_CALLS)
    
    # 4. Social Security Coverage
    social_sec = extract_social_security_coverage(content, url, province)
    if social_sec:
        if save_to_social_security_coverage(db, social_sec):
            logger.info(f"Saved to social_security_coverage_detail")
            results["social_security"] = 1
        else:
            logger.error(f"Failed to save social_security_coverage")
    
    time.sleep(DELAY_BETWEEN_CALLS)
    return results


def main():
    """Main function"""
    logger.info("="*80)
    logger.info("BẮT ĐẦU LLM EXTRACTION - LĨNH VỰC: VĂN HÓA - XÃ HỘI")
    logger.info(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80)
    
    db = SessionLocal()
    try:
        posts = get_posts_from_db(limit=BATCH_SIZE)
        
        if not posts:
            return {
                "status": "no_data",
                "message": "Không có posts nào (type_newspaper=society)",
                "processed": 0
            }
        
        total_extracted = {
            "culture_lifestyle": 0,
            "cultural_infrastructure": 0,
            "culture_sport_access": 0,
            "social_security": 0
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
        logger.info(f"Culture Lifestyle: {total_extracted['culture_lifestyle']}")
        logger.info(f"Cultural Infrastructure: {total_extracted['cultural_infrastructure']}")
        logger.info(f"Culture Sport Access: {total_extracted['culture_sport_access']}")
        logger.info(f"Social Security: {total_extracted['social_security']}")
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
