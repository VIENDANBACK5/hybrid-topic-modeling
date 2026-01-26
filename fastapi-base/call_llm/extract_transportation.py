#!/usr/bin/env python3
"""
Extract TRANSPORTATION data from important_posts
- transport_infrastructure_detail: Hạ tầng giao thông (đường, cầu, chất lượng)
- traffic_congestion_detail: Ùn tắc giao thông (chỉ số, tốc độ, điểm tắc)
- traffic_safety_detail: Tai nạn giao thông (tử vong, vi phạm)
"""

import os
import sys
import time
import json
import logging
from typing import Dict, List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from sqlalchemy import text
from openai import OpenAI

# Config
DELAY_BETWEEN_CALLS = 2  # seconds
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# OpenRouter API
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY")
)


def save_to_traffic_safety_detail(db, data: Dict) -> bool:
    """Save extracted data to traffic_safety_detail table"""
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

def call_llm(prompt: str, max_retries: int = 3) -> Optional[str]:
    """Call LLM with retry logic"""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="openai/gpt-4-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM error (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                return None

def extract_transport_infrastructure(content: str, post_id: int, province: str) -> Optional[Dict]:
    """Extract hạ tầng giao thông → transport_infrastructure_detail"""
    prompt = f"""Phân tích văn bản sau và trả về JSON theo đúng cấu trúc.
Chỉ sử dụng thông tin có trong văn bản, không suy diễn.

Schema:
{{
  "year": null,
  "quarter": null,
  "month": null,
  "infrastructure_score": null,
  "road_length_km": null,
  "paved_road_rate": null,
  "road_density_km_per_km2": null,
  "bridge_count": null,
  "public_transport_coverage": null,
  "road_quality_score": null,
  "maintenance_budget_billion": null
}}

Giải thích các trường:
- year (integer): Năm
- quarter (integer): Quý
- month (integer): Tháng
- infrastructure_score (float): Điểm hạ tầng giao thông (0-100)
- road_length_km (float): Tổng chiều dài đường (km)
- paved_road_rate (float): Tỷ lệ đường nhựa/bê tông hóa (%, 0-100)
- road_density_km_per_km2 (float): Mật độ đường/km² diện tích
- bridge_count (integer): Số cầu/cống
- public_transport_coverage (float): Tỷ lệ phủ sóng giao thông công cộng (%, 0-100)
- road_quality_score (float): Điểm chất lượng đường (0-100)
- maintenance_budget_billion (float): Ngân sách bảo trì (tỷ đồng)

Quy tắc:
1. QUAN TRỌNG: CHỈ extract nếu văn bản RÕ RÀNG nói về Hưng Yên (hoặc huyện/thành phố thuộc Hưng Yên)
2. Nếu văn bản nói về toàn quốc, tỉnh khác, hoặc không rõ địa phương → trả về: {{"no_data": true}}
3. CHỈ trích xuất số liệu CÓ TRONG văn bản về Hưng Yên
4. Nếu văn bản KHÔNG đề cập hạ tầng giao thông/đường/cầu của Hưng Yên, trả về: {{"no_data": true}}
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
        logger.error(f"Lỗi extract transport_infrastructure: {e}")
        return None


def extract_traffic_congestion(content: str, post_id: int, province: str) -> Optional[Dict]:
    """Extract ùn tắc giao thông → traffic_congestion_detail"""
    prompt = f"""Phân tích văn bản sau và trả về JSON theo đúng cấu trúc.
Chỉ sử dụng thông tin có trong văn bản, không suy diễn.

Schema:
{{
  "year": null,
  "quarter": null,
  "month": null,
  "congestion_index": null,
  "average_speed_kmh": null,
  "peak_hour_delay_minutes": null,
  "congestion_points": null,
  "traffic_flow_score": null,
  "public_transport_usage_rate": null,
  "vehicle_per_1000_pop": null,
  "smart_traffic_coverage": null
}}

Giải thích các trường:
- year (integer): Năm
- quarter (integer): Quý
- month (integer): Tháng
- congestion_index (float): Chỉ số ùn tắc (0-100, cao = tắc nhiều)
- average_speed_kmh (float): Tốc độ trung bình (km/h)
- peak_hour_delay_minutes (float): Thời gian chậm trễ giờ cao điểm (phút)
- congestion_points (integer): Số điểm ùn tắc thường xuyên
- traffic_flow_score (float): Điểm lưu lượng giao thông (0-100)
- public_transport_usage_rate (float): Tỷ lệ sử dụng phương tiện công cộng (%, 0-100)
- vehicle_per_1000_pop (float): Số phương tiện/1000 dân
- smart_traffic_coverage (float): Tỷ lệ phủ sóng giao thông thông minh (%, 0-100)

Quy tắc:
1. QUAN TRỌNG: CHỈ extract nếu văn bản RÕ RÀNG nói về Hưng Yên (hoặc huyện/thành phố thuộc Hưng Yên)
2. Nếu văn bản nói về toàn quốc, tỉnh khác, hoặc không rõ địa phương → trả về: {{"no_data": true}}
3. CHỈ trích xuất số liệu CÓ TRONG văn bản về Hưng Yên
4. Nếu văn bản KHÔNG đề cập ùn tắc/tốc độ/lưu lượng của Hưng Yên, trả về: {{"no_data": true}}
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
        logger.error(f"Lỗi extract traffic_congestion: {e}")
        return None


def extract_traffic_safety(content: str, url: str, province: str) -> Optional[Dict]:
    """Extract tai nạn giao thông → traffic_safety_detail"""
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
  "drunk_driving_cases": null,
  "helmet_compliance_rate": null,
  "accident_reduction_rate": null
}}

Giải thích các trường:
- year (integer): Năm
- quarter (integer): Quý
- month (integer): Tháng
- traffic_safety_score (float): Điểm an toàn giao thông (0-100)
- accidents_total (integer): Tổng số vụ tai nạn
- fatalities (integer): Số người chết
- injuries (integer): Số người bị thương
- accidents_per_100k_vehicles (float): Tai nạn/100k phương tiện
- fatalities_per_100k_pop (float): Tử vong/100k dân
- drunk_driving_cases (integer): Số ca vi phạm nồng độ cồn
- helmet_compliance_rate (float): Tỷ lệ đội mũ bảo hiểm (%, 0-100)
- accident_reduction_rate (float): Tỷ lệ giảm tai nạn so với kỳ trước (%, có thể âm)

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
        data["data_source"] = url
        data["data_status"] = "extracted"
        return data
        
    except Exception as e:
        logger.error(f"Lỗi extract traffic_safety: {e}")
        return None


def process_post(post: Dict, db) -> Dict[str, int]:
    """Xử lý 1 post - Extract 3 loại thống kê giao thông"""
    post_id = post.get("id")
    content = post.get("content", "")
    title = post.get("title", "")
    url = post.get("url", "")
    province = post.get("province") or "Hưng Yên"  # Default nếu không có dvhc
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Post ID: {post_id}")
    logger.info(f"Title: {title[:100]}")
    logger.info(f"Province: {province}")
    
    results = {
        # "transport_infrastructure": 0,
        # "traffic_congestion": 0,
        "traffic_safety": 0
    }
    
    # # 1. Transport Infrastructure
    # infra = extract_transport_infrastructure(content, post_id, province)
    # if infra:
    #     logger.info(f"Extracted transport_infrastructure_detail")
    #     results["transport_infrastructure"] = 1
    #     # TODO: Save to DB
    
    # time.sleep(DELAY_BETWEEN_CALLS)
    
    # # 2. Traffic Congestion
    # congestion = extract_traffic_congestion(content, post_id, province)
    # if congestion:
    #     logger.info(f"Extracted traffic_congestion_detail")
    #     results["traffic_congestion"] = 1
    #     # TODO: Save to DB
    
    # time.sleep(DELAY_BETWEEN_CALLS)
    
    # 3. Traffic Safety
    safety = extract_traffic_safety(content, url, province)
    if safety:
        if save_to_traffic_safety_detail(db, safety):
            logger.info(f"Saved to traffic_safety_detail")
            results["traffic_safety"] = 1
        else:
            logger.error(f"Failed to save traffic_safety_detail")
    
    time.sleep(DELAY_BETWEEN_CALLS)
    return results


def main():
    """Main execution"""
    logger.info("\n" + "="*80)
    logger.info("🚗 TRANSPORTATION EXTRACTION - important_posts")
    logger.info("="*80)
    
    db = SessionLocal()
    try:
        query = text("""
            SELECT id, title, content, url, dvhc as province 
            FROM important_posts 
            WHERE type_newspaper = 'transportation'
            ORDER BY id
        """)
        result = db.execute(query)
        posts = [dict(row._mapping) for row in result]
    except Exception as e:
        db.close()
        raise e
    
    logger.info(f"Tổng posts: {len(posts)}")
    
    if not posts:
        return {
            "status": "no_data",
            "message": "Không có posts nào (type_newspaper=transportation)",
            "processed": 0
        }
    
    total_extracted = {
        # "transport_infrastructure": 0,
        # "traffic_congestion": 0,
        "traffic_safety": 0
    }
    
    for i, post in enumerate(posts, 1):
        logger.info(f"\nProgress: {i}/{len(posts)}")
        try:
            results = process_post(post, db)
            for key in total_extracted:
                total_extracted[key] += results.get(key, 0)
        except Exception as e:
            logger.error(f"Lỗi: {e}")
    
    db.close()
    
    logger.info("\n" + "="*80)
    logger.info(f"Đã xử lý: {len(posts)} posts")
    # logger.info(f"Transport Infrastructure: {total_extracted['transport_infrastructure']}")
    # logger.info(f"Traffic Congestion: {total_extracted['traffic_congestion']}")
    logger.info(f"Traffic Safety: {total_extracted['traffic_safety']}")
    logger.info(f"Tổng: {sum(total_extracted.values())} records")
    logger.info("="*80)
    
    return {
        "status": "success",
        "processed": len(posts),
        "extracted": total_extracted,
        "total_records": sum(total_extracted.values())
    }


if __name__ == "__main__":
    main()
