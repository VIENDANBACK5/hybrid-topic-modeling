#!/usr/bin/env python3
"""
LLM Extract cho Lĩnh vực: AN NINH - TRẬT TỰ - AN TOÀN XÃ HỘI

THUẦN LLM - Không dùng Regex

Nguồn dữ liệu:
  - Bảng: important_posts
  - Filter: type_newspaper = 'security'
  - Số lượng: ~36 posts

Bảng đích (4 bảng):
  1. security_detail               - An ninh chung/tội phạm
  2. crime_prevention_detail       - Phòng chống tội phạm
  3. traffic_safety_detail         - An toàn giao thông
  4. public_order_detail           - Trật tự công cộng
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
        logging.FileHandler('call_llm/security_extraction.log'),
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
def save_to_security_detail(db, data: Dict) -> bool:
    """Save to security_detail"""
    try:
        insert_query = text("""
            INSERT INTO security_detail (
                province, year, quarter, month,
                security_score, crime_cases, crime_rate_per_100k_pop,
                arrests, conviction_rate, recidivism_rate,
                data_status, data_source
            ) VALUES (
                :province, :year, :quarter, :month,
                :security_score, :crime_cases, :crime_rate_per_100k_pop,
                :arrests, :conviction_rate, :recidivism_rate,
                :data_status, :data_source
            )
        """)
        db.execute(insert_query, data)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi save security_detail: {e}")
        db.rollback()
        return False


def save_to_crime_prevention_detail(db, data: Dict) -> bool:
    """Save to crime_prevention_detail"""
    try:
        insert_query = text("""
            INSERT INTO crime_prevention_detail (
                province, year, quarter, month,
                prevented_cases, security_patrols, community_programs,
                cameras_installed, hotspots_monitored,
                data_status, data_source
            ) VALUES (
                :province, :year, :quarter, :month,
                :prevented_cases, :security_patrols, :community_programs,
                :cameras_installed, :hotspots_monitored,
                :data_status, :data_source
            )
        """)
        db.execute(insert_query, data)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi save crime_prevention_detail: {e}")
        db.rollback()
        return False


def save_to_traffic_safety_detail_sec(db, data: Dict) -> bool:
    """Save to traffic_safety_detail (from security)"""
    try:
        insert_query = text("""
            INSERT INTO traffic_safety_detail (
                province, year, quarter, month,
                traffic_safety_score, accidents_total, fatalities, injuries,
                accidents_per_100k_vehicles, fatalities_per_100k_pop,
                drunk_driving_cases, helmet_compliance_rate, accident_reduction_rate,
                data_status, data_source
            ) VALUES (
                :province, :year, :quarter, :month,
                :traffic_safety_score, :accidents_total, :fatalities, :injuries,
                :accidents_per_100k_vehicles, :fatalities_per_100k_pop,
                :drunk_driving_cases, :helmet_compliance_rate, :accident_reduction_rate,
                :data_status, :data_source
            )
        """)
        db.execute(insert_query, data)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi save traffic_safety_detail: {e}")
        db.rollback()
        return False


def save_to_public_order_detail(db, data: Dict) -> bool:
    """Save to public_order_detail"""
    try:
        insert_query = text("""
            INSERT INTO public_order_detail (
                province, year, quarter, month,
                public_order_score, violations, enforcement_actions,
                disputes_resolved, mediation_success_rate,
                data_status, data_source
            ) VALUES (
                :province, :year, :quarter, :month,
                :public_order_score, :violations, :enforcement_actions,
                :disputes_resolved, :mediation_success_rate,
                :data_status, :data_source
            )
        """)
        db.execute(insert_query, data)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi save public_order_detail: {e}")
        db.rollback()
        return False


def call_llm(prompt: str, max_retries: int = 3) -> Optional[str]:
    """Call OpenRouter LLM API"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": API_BASE_URL,
        "X-Title": "Security Data Extractor"
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
    """Lấy important_posts có type_newspaper = 'security'"""
    try:
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/DBHuYe")
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        query = text("""
            SELECT id, title, content, url, dvhc, published_date
            FROM important_posts
            WHERE type_newspaper = 'security'
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
        logger.info(f"Tìm thấy {len(posts)} posts (type_newspaper=security)")
        return posts
        
    except Exception as e:
        logger.error(f"Lỗi khi lấy posts từ DB: {e}")
        return []


def extract_security_detail(content: str, post_id: int, province: str) -> Optional[Dict]:
    """Extract an ninh ma túy → security_detail"""
    prompt = f"""Phân tích văn bản sau và trả về JSON theo đúng cấu trúc.
Chỉ sử dụng thông tin có trong văn bản, không suy diễn.

Schema:
{{
  "year": null,
  "quarter": null,
  "month": null,
  "drug_cases": null,
  "drug_offenders": null,
  "crime_reduction_rate": null
}}

Giải thích các trường:
- year (integer): Năm
- quarter (integer): Quý
- month (integer): Tháng
- drug_cases (integer): Số vụ án ma túy
- drug_offenders (integer): Số đối tượng phạm tội ma túy
- crime_reduction_rate (float): Tỷ lệ giảm tội phạm (%, 0-100)

Quy tắc:
1. QUAN TRỌNG: CHỈ extract nếu văn bản RÕ RÀNG nói về Hưng Yên (hoặc huyện/thành phố thuộc Hưng Yên)
2. Nếu văn bản nói về toàn quốc, tỉnh khác, hoặc không rõ địa phương → trả về: {{"no_data": true}}
3. CHỈ trích xuất số liệu CÓ TRONG văn bản về Hưng Yên
4. Nếu văn bản KHÔNG đề cập ma túy/tội phạm của Hưng Yên, trả về: {{"no_data": true}}
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
        logger.error(f"Lỗi extract security_detail: {e}")
        return None


def extract_crime_prevention(content: str, post_id: int, province: str) -> Optional[Dict]:
    """Extract phòng chống tội phạm → crime_prevention_detail"""
    prompt = f"""Phân tích văn bản sau và trả về JSON theo đúng cấu trúc.
Chỉ sử dụng thông tin có trong văn bản, không suy diễn.

Schema:
{{
  "year": null,
  "quarter": null,
  "month": null,
  "crime_reduction_rate": null,
  "case_clearance_rate": null,
  "total_cases": null,
  "solved_cases": null,
  "prevention_programs": null,
  "community_watch_groups": null,
  "drug_crime_reduction": null,
  "effectiveness_score": null
}}

Giải thích các trường:
- year (integer): Năm
- quarter (integer): Quý
- month (integer): Tháng
- crime_reduction_rate (float): Tỷ lệ giảm tội phạm (%, 0-100)
- case_clearance_rate (float): Tỷ lệ phá án (%, 0-100)
- total_cases (integer): Tổng số vụ án
- solved_cases (integer): Số vụ đã phá
- prevention_programs (integer): Số chương trình phòng chống tội phạm
- community_watch_groups (integer): Số tổ bảo vệ dân phố/tự quản
- drug_crime_reduction (float): Tỷ lệ giảm tội phạm ma túy (%)
- effectiveness_score (float): Điểm hiệu quả phòng chống (0-100)

Quy tắc:
1. QUAN TRỌNG: CHỈ extract nếu văn bản RÕ RÀNG nói về Hưng Yên (hoặc huyện/thành phố thuộc Hưng Yên)
2. Nếu văn bản nói về toàn quốc, tỉnh khác, hoặc không rõ địa phương → trả về: {{"no_data": true}}
3. CHỈ trích xuất số liệu CÓ TRONG văn bản về Hưng Yên
4. Nếu văn bản KHÔNG đề cập phòng chống tội phạm của Hưng Yên, trả về: {{"no_data": true}}
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
        logger.error(f"Lỗi extract crime_prevention: {e}")
        return None


def extract_traffic_safety(content: str, post_id: int, province: str) -> Optional[Dict]:
    """Extract an toàn giao thông → traffic_safety_detail"""
    prompt = f"""Phân tích văn bản sau và trả về JSON theo đúng cấu trúc.
Chỉ sử dụng thông tin có trong văn bản, không suy diễn.

Schema:
{{
  "year": null,
  "quarter": null,
  "month": null,
  "traffic_safety_score": null,
  "accidents_total": null,
  "fatalities": null,
  "injuries": null,
  "accidents_per_100k_vehicles": null,
  "fatalities_per_100k_pop": null,
  "drunk_driving_cases": null
}}

Giải thích các trường:
- year (integer): Năm
- quarter (integer): Quý
- month (integer): Tháng
- traffic_safety_score (float): Điểm an toàn giao thông (0-100)
- accidents_total (integer): Tổng số vụ tai nạn giao thông
- fatalities (integer): Số người chết
- injuries (integer): Số người bị thương
- accidents_per_100k_vehicles (float): Số vụ/100k phương tiện
- fatalities_per_100k_pop (float): Số người chết/100k dân
- drunk_driving_cases (integer): Số vụ lái xe say rượu

Quy tắc:
1. QUAN TRỌNG: CHỈ extract nếu văn bản RÕ RÀNG nói về Hưng Yên (hoặc huyện/thành phố thuộc Hưng Yên)
2. Nếu văn bản nói về toàn quốc, tỉnh khác, hoặc không rõ địa phương → trả về: {{"no_data": true}}
3. CHỈ trích xuất số liệu CÓ TRONG văn bản về Hưng Yên
4. Nếu văn bản KHÔNG đề cập tai nạn giao thông của Hưng Yên, trả về: {{"no_data": true}}
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
        logger.error(f"Lỗi extract traffic_safety: {e}")
        return None


def extract_public_order(content: str, post_id: int, province: str) -> Optional[Dict]:
    """Extract trật tự công cộng → public_order_detail"""
    prompt = f"""Phân tích văn bản sau và trả về JSON theo đúng cấu trúc.
Chỉ sử dụng thông tin có trong văn bản, không suy diễn.

Schema:
{{
  "year": null,
  "quarter": null,
  "month": null,
  "public_order_score": null,
  "safety_perception_score": null,
  "crime_rate_per_100k": null,
  "violent_crime_rate": null,
  "property_crime_rate": null,
  "police_per_capita": null,
  "response_time_minutes": null
}}

Giải thích các trường:
- year (integer): Năm
- quarter (integer): Quý
- month (integer): Tháng
- public_order_score (float): Điểm trật tự công cộng (0-100)
- safety_perception_score (float): Điểm cảm nhận an toàn (0-100)
- crime_rate_per_100k (float): Tỷ lệ tội phạm/100k dân
- violent_crime_rate (float): Tỷ lệ tội phạm bạo lực/100k dân
- property_crime_rate (float): Tỷ lệ tội phạm tài sản/100k dân
- police_per_capita (float): Số cảnh sát/1000 dân
- response_time_minutes (float): Thời gian phản ứng trung bình (phút)

Quy tắc:
1. QUAN TRỌNG: CHỈ extract nếu văn bản RÕ RÀNG nói về Hưng Yên (hoặc huyện/thành phố thuộc Hưng Yên)
2. Nếu văn bản nói về toàn quốc, tỉnh khác, hoặc không rõ địa phương → trả về: {{"no_data": true}}
3. CHỈ trích xuất số liệu CÓ TRONG văn bản về Hưng Yên
4. Nếu văn bản KHÔNG đề cập trật tự công cộng của Hưng Yên, trả về: {{"no_data": true}}
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
        logger.error(f"Lỗi extract public_order: {e}")
        return None


def process_post(post: Dict, db) -> Dict[str, int]:
    """Xử lý 1 post - Extract 4 loại thống kê an ninh"""
    post_id = post.get("id")
    content = post.get("content", "")
    title = post.get("title", "")
    province = post.get("province", "Unknown")
    url = post.get("url", f"Post {post_id}")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Post ID: {post_id}")
    logger.info(f"Title: {title[:100]}")
    
    results = {
        "security": 0,
        "crime_prevention": 0,
        "traffic_safety": 0,
        "public_order": 0
    }
    
    # 1. Security (ma túy)
    security = extract_security_detail(content, url, province)
    if security:
        if save_to_security_detail(db, security):
            logger.info(f"Saved to security_detail")
            results["security"] = 1
        else:
            logger.error(f"Failed to save security_detail")
    
    time.sleep(DELAY_BETWEEN_CALLS)
    
    # 2. Crime Prevention
    crime_prev = extract_crime_prevention(content, url, province)
    if crime_prev:
        if save_to_crime_prevention_detail(db, crime_prev):
            logger.info(f"Saved to crime_prevention_detail")
            results["crime_prevention"] = 1
        else:
            logger.error(f"Failed to save crime_prevention_detail")
    
    time.sleep(DELAY_BETWEEN_CALLS)
    
    # 3. Traffic Safety
    traffic = extract_traffic_safety(content, url, province)
    if traffic:
        if save_to_traffic_safety_detail_sec(db, traffic):
            logger.info(f"Saved to traffic_safety_detail")
            results["traffic_safety"] = 1
        else:
            logger.error(f"Failed to save traffic_safety_detail")
    
    time.sleep(DELAY_BETWEEN_CALLS)
    
    # 4. Public Order
    public_ord = extract_public_order(content, url, province)
    if public_ord:
        if save_to_public_order_detail(db, public_ord):
            logger.info(f"Saved to public_order_detail")
            results["public_order"] = 1
        else:
            logger.error(f"Failed to save public_order_detail")
    
    time.sleep(DELAY_BETWEEN_CALLS)
    return results


def main():
    """Main function"""
    logger.info("="*80)
    logger.info("BẮT ĐẦU LLM EXTRACTION - LĨNH VỰC: AN NINH - TRẬT TỰ")
    logger.info(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80)
    
    db = SessionLocal()
    try:
        posts = get_posts_from_db(limit=BATCH_SIZE)
        
        if not posts:
            return {
                "status": "no_data",
                "message": "Không có posts nào (type_newspaper=security)",
                "processed": 0
            }
        
        total_extracted = {
            "security": 0,
            "crime_prevention": 0,
            "traffic_safety": 0,
            "public_order": 0
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
        logger.info(f"Security Detail: {total_extracted['security']}")
        logger.info(f"Crime Prevention: {total_extracted['crime_prevention']}")
        logger.info(f"Traffic Safety: {total_extracted['traffic_safety']}")
        logger.info(f"Public Order: {total_extracted['public_order']}")
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
