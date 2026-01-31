#!/usr/bin/env python3
"""
LLM Extract cho: CHUYỂN ĐỔI SỐ (Digital Transformation)

THUẦN LLM - Không dùng Regex

Nguồn dữ liệu:
  - Bảng: important_posts
  - Filter: Posts có thông tin về chuyển đổi số, chính quyền điện tử
  
Bảng đích:
  - digital_transformation_detail - Các chỉ số về chuyển đổi số, e-government, hạ tầng số
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
        logging.FileHandler('call_llm/digital_transformation_extraction.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:7777")
LLM_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "50"))
DELAY_BETWEEN_CALLS = float(os.getenv("DELAY_BETWEEN_CALLS", "1"))


def call_llm(prompt: str, max_retries: int = 3) -> Optional[str]:
    """Call OpenRouter LLM API"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": API_BASE_URL,
        "X-Title": "Digital Transformation Data Extractor"
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


def save_to_digital_transformation(db, data: Dict) -> bool:
    """Save to digital_transformation_detail"""
    try:
        # Build period string
        period_parts = []
        if data.get('year'):
            period_parts.append(f"Năm {data['year']}")
        if data.get('quarter'):
            period_parts.append(f"Quý {data['quarter']}")
        if data.get('month'):
            period_parts.append(f"Tháng {data['month']}")
        data['period'] = ", ".join(period_parts) if period_parts else None
        
        # Ensure all fields exist in data dict with None default
        required_fields = [
            'province', 'source_post_id', 'source_url', 'period', 'year', 'quarter', 'month',
            'dx_index', 'dx_readiness_index', 'dx_maturity_level', 'dx_ranking',
            'egov_index', 'online_public_services', 'level3_services', 'level4_services',
            'online_service_usage_rate',
            'government_portals', 'integrated_databases', 'shared_databases', 'data_sharing_rate',
            'cloud_adoption_rate', 'data_centers', 'broadband_coverage', 'fiber_optic_coverage', 'fiveg_coverage',
            'ai_projects', 'iot_devices', 'blockchain_projects', 'smart_city_projects',
            'dx_enterprises', 'dx_adoption_rate', 'digital_platform_usage',
            'dx_training_programs', 'digital_skills_workforce',
            'notes', 'data_source', 'extraction_metadata'
        ]
        for field in required_fields:
            if field not in data:
                data[field] = None
        
        insert_query = text("""
            INSERT INTO digital_transformation_detail (
                province, source_post_id, source_url, period, year, quarter, month,
                dx_index, dx_readiness_index, dx_maturity_level, dx_ranking,
                egov_index, online_public_services, level3_services, level4_services, 
                online_service_usage_rate,
                government_portals, integrated_databases, shared_databases, data_sharing_rate,
                cloud_adoption_rate, data_centers, broadband_coverage, fiber_optic_coverage, fiveg_coverage,
                sme_dx_adoption, large_company_dx_adoption, companies_using_cloud, 
                companies_using_ai, companies_using_iot, companies_using_big_data,
                digital_literacy_rate, digital_skills_workforce, digital_training_programs, 
                people_trained_digital,
                ai_projects, iot_projects, blockchain_projects, smart_city_projects,
                smart_agriculture_area, agricultural_iot_adoption, agricultural_digital_platforms,
                telemedicine_facilities, electronic_health_records_rate, health_digital_platforms,
                notes, data_source, extraction_metadata
            ) VALUES (
                :province, :source_post_id, :source_url, :period, :year, :quarter, :month,
                :dx_index, :dx_readiness_index, :dx_maturity_level, :dx_ranking,
                :egov_index, :online_public_services, :level3_services, :level4_services, 
                :online_service_usage_rate,
                :government_portals, :integrated_databases, :shared_databases, :data_sharing_rate,
                :cloud_adoption_rate, :data_centers, :broadband_coverage, :fiber_optic_coverage, :fiveg_coverage,
                :sme_dx_adoption, :large_company_dx_adoption, :companies_using_cloud, 
                :companies_using_ai, :companies_using_iot, :companies_using_big_data,
                :digital_literacy_rate, :digital_skills_workforce, :digital_training_programs, 
                :people_trained_digital,
                :ai_projects, :iot_projects, :blockchain_projects, :smart_city_projects,
                :smart_agriculture_area, :agricultural_iot_adoption, :agricultural_digital_platforms,
                :telemedicine_facilities, :electronic_health_records_rate, :health_digital_platforms,
                :notes, :data_source, :extraction_metadata
            )
        """)
        db.execute(insert_query, data)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi save digital_transformation_detail: {e}")
        db.rollback()
        return False


def get_posts_from_db(limit: int = 100) -> List[Dict]:
    """Lấy important_posts có nội dung về chuyển đổi số"""
    try:
        db = SessionLocal()
        query = text("""
            SELECT id, title, content, url, dvhc as province, published_date, type_newspaper, document_type FROM important_posts
            WHERE type_newspaper = 'economy'
               AND (document_type IS NULL OR document_type != 'internal')
               AND (
                content ILIKE '%chuyển đổi số%' OR
                content ILIKE '%cds%' OR
                content ILIKE '%digital transformation%' OR
                content ILIKE '%chính quyền điện tử%' OR
                content ILIKE '%chính quyền số%' OR
                content ILIKE '%e-government%' OR
                content ILIKE '%dịch vụ công trực tuyến%' OR
                content ILIKE '%cổng thông tin điện tử%' OR
                content ILIKE '%hạ tầng số%' OR
                content ILIKE '%cloud%' OR
                content ILIKE '%điện toán đám mây%' OR
                content ILIKE '%smart city%' OR
                content ILIKE '%thành phố thông minh%'
            )
            ORDER BY id DESC
            LIMIT :limit
        """)
        
        result = db.execute(query, {"limit": limit})
        posts = []
        for row in result:
            posts.append({
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "url": row[3],
                "province": row[4],
                "published_date": row[5],
                "type_newspaper": row[6]
            })
        
        db.close()
        logger.info(f"Lấy được {len(posts)} posts về chuyển đổi số từ DB")
        return posts
    except Exception as e:
        logger.error(f"Lỗi khi lấy posts từ DB: {e}")
        return []


def extract_digital_transformation_data(content: str, url: str, post_id: int, province: str) -> Optional[Dict]:
    """Extract chỉ số chuyển đổi số từ văn bản"""
    prompt = f"""Phân tích văn bản và trích xuất các chỉ số CHUYỂN ĐỔI SỐ.

Trả về JSON với cấu trúc:
{{
  "location": null,
  "year": null,
  "quarter": null,
  "month": null,
  "dx_index": null,
  "dx_readiness_index": null,
  "dx_maturity_level": null,
  "dx_ranking": null,
  "egov_index": null,
  "online_public_services": null,
  "level3_services": null,
  "level4_services": null,
  "online_service_usage_rate": null,
  "government_portals": null,
  "integrated_databases": null,
  "shared_databases": null,
  "data_sharing_rate": null,
  "cloud_adoption_rate": null,
  "data_centers": null,
  "broadband_coverage": null,
  "fiber_optic_coverage": null,
  "fiveg_coverage": null,
  "sme_dx_adoption": null,
  "large_company_dx_adoption": null,
  "companies_using_cloud": null,
  "companies_using_ai": null,
  "companies_using_iot": null,
  "companies_using_big_data": null,
  "digital_literacy_rate": null,
  "digital_skills_workforce": null,
  "digital_training_programs": null,
  "people_trained_digital": null,
  "ai_projects": null,
  "iot_projects": null,
  "blockchain_projects": null,
  "smart_city_projects": null,
  "smart_agriculture_area": null,
  "agricultural_iot_adoption": null,
  "agricultural_digital_platforms": null,
  "telemedicine_facilities": null,
  "electronic_health_records_rate": null,
  "health_digital_platforms": null,
  "notes": null
}}

Giải thích các trường:
- location (string): Tên địa phương (tỉnh/thành/huyện/xã)
- year/quarter/month (int): Thời gian
- dx_index (float): Chỉ số chuyển đổi số tổng hợp (0-100)
- dx_readiness_index (float): Chỉ số sẵn sàng chuyển đổi số (0-100)
- dx_maturity_level (string): Mức độ trưởng thành CĐS (basic/intermediate/advanced/leading)
- dx_ranking (int): Xếp hạng CĐS toàn quốc
- egov_index (float): Chỉ số chính quyền điện tử (0-100)
- online_public_services (int): Số dịch vụ công trực tuyến
- level3_services (int): Số dịch vụ công mức độ 3
- level4_services (int): Số dịch vụ công mức độ 4
- online_service_usage_rate (float): Tỷ lệ sử dụng dịch vụ công trực tuyến (%)
- government_portals (int): Số cổng thông tin điện tử
- integrated_databases (int): Số cơ sở dữ liệu được tích hợp
- shared_databases (int): Số CSDL dùng chung
- data_sharing_rate (float): Tỷ lệ chia sẻ dữ liệu liên thông (%)
- cloud_adoption_rate (float): Tỷ lệ sử dụng điện toán đám mây (%)
- data_centers (int): Số trung tâm dữ liệu
- broadband_coverage (float): Tỷ lệ phủ sóng băng thông rộng (%)
- fiber_optic_coverage (float): Tỷ lệ phủ sóng cáp quang (%)
- fiveg_coverage (float): Tỷ lệ phủ sóng 5G (%)
- sme_dx_adoption (float): Tỷ lệ SME thực hiện CĐS (%)
- large_company_dx_adoption (float): Tỷ lệ DN lớn thực hiện CĐS (%)
- companies_using_cloud (int): Số DN sử dụng cloud
- companies_using_ai (int): Số DN ứng dụng AI
- companies_using_iot (int): Số DN ứng dụng IoT
- companies_using_big_data (int): Số DN sử dụng Big Data
- digital_literacy_rate (float): Tỷ lệ biết chữ số (%)
- digital_skills_workforce (float): Tỷ lệ lao động có kỹ năng số (%)
- digital_training_programs (int): Số chương trình đào tạo kỹ năng số
- people_trained_digital (int): Số người được đào tạo CĐS
- ai_projects (int): Số dự án AI triển khai
- iot_projects (int): Số dự án IoT triển khai
- blockchain_projects (int): Số dự án Blockchain
- smart_city_projects (int): Số dự án thành phố thông minh
- smart_agriculture_area (float): Diện tích nông nghiệp thông minh (ha)
- agricultural_iot_adoption (float): Tỷ lệ ứng dụng IoT nông nghiệp (%)
- agricultural_digital_platforms (int): Số nền tảng số nông nghiệp
- telemedicine_facilities (int): Số cơ sở y tế khám chữa bệnh từ xa
- electronic_health_records_rate (float): Tỷ lệ bệnh án điện tử (%)
- health_digital_platforms (int): Số nền tảng số y tế
- notes (string): Thông tin bổ sung

QUY TẮC:
1. LINH HOẠT: Extract BẤT KỲ chỉ số CHUYỂN ĐỔI SỐ nào (không cần đầy đủ tất cả fields)
2. Các từ khóa cần chú ý:
   - Chuyển đổi số, CDS, Digital Transformation, DX
   - Chính quyền điện tử, chính quyền số, e-government
   - Dịch vụ công trực tuyến, mức độ 3, mức độ 4
   - Cổng thông tin điện tử, CSDL dùng chung, chia sẻ dữ liệu
   - Cloud, điện toán đám mây, trung tâm dữ liệu
   - Băng thông rộng, cáp quang, 4G, 5G
   - Smart city, thành phố thông minh
   - AI, IoT, Blockchain, Big Data
   - Nông nghiệp thông minh, y tế từ xa, bệnh án điện tử
   - Kỹ năng số, đào tạo số
3. 📈 Chỉ số và xếp hạng:
   - Chỉ số CĐS thường là số từ 0-100
   - Xếp hạng toàn quốc (VD: "xếp thứ 5/63 tỉnh")
   - Mức độ trưởng thành: basic, intermediate, advanced, leading
4. Nhận diện địa điểm: Trích xuất tên tỉnh/thành/huyện/xã từ văn bản
5. ⏰ Thời gian:
   - "Quý I/II/III/IV" → quarter=1/2/3/4
   - "6 tháng đầu năm" → quarter=2
   - "9 tháng" → quarter=3
   - "Năm 2024" → year=2024
6. CHỈ trả về {{"no_data": true}} nếu văn bản HOÀN TOÀN KHÔNG có chỉ số chuyển đổi số

Văn bản:
\"\"\"
{content[:4000]}
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
        
        # Set province from location or use default
        location = data.pop("location", None)
        if location:
            data["province"] = location
        else:
            data["province"] = province
        
        data["source_post_id"] = post_id
        data["source_url"] = url if url and url.startswith("http") else None
        data["data_source"] = "LLM Extraction"
        data["extraction_metadata"] = json.dumps({"model": LLM_MODEL, "timestamp": datetime.now().isoformat()})
        
        return data
        
    except Exception as e:
        logger.error(f"Lỗi extract digital_transformation: {e}")
        return None


def process_post(post: Dict, db) -> int:
    """Xử lý 1 post - Extract chuyển đổi số"""
    post_id = post.get("id")
    content = post.get("content", "")
    title = post.get("title", "")
    province = post.get("province", "Hưng Yên")
    url = post.get("url") or None
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Post ID: {post_id}")
    logger.info(f"Title: {title[:100]}")
    
    data = extract_digital_transformation_data(content, url, post_id, province)
    if data:
        data["document_type"] = document_type
        if save_to_digital_transformation(db, data):
            logger.info(f"Saved to digital_transformation_detail")
            return 1
        else:
            logger.error(f"Failed to save digital_transformation_detail")
    
    return 0


def main():
    """Main function"""
    logger.info("="*80)
    logger.info("BẮT ĐẦU LLM EXTRACTION - CHUYỂN ĐỔI SỐ")
    logger.info(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80)
    
    db = SessionLocal()
    try:
        posts = get_posts_from_db(limit=BATCH_SIZE)
        
        if not posts:
            return {
                "status": "no_data",
                "message": "Không có posts về chuyển đổi số",
                "processed": 0
            }
        
        total_extracted = 0
        
        for i, post in enumerate(posts, 1):
            logger.info(f"\nProgress: {i}/{len(posts)}")
            try:
                total_extracted += process_post(post, db)
                time.sleep(DELAY_BETWEEN_CALLS)
            except Exception as e:
                logger.error(f"Lỗi: {e}")
        
        logger.info("\n" + "="*80)
        logger.info(f"Đã xử lý: {len(posts)} posts")
        logger.info(f"Extracted: {total_extracted} records")
        logger.info("="*80)
        
        return {
            "status": "success",
            "processed": len(posts),
            "extracted": total_extracted
        }
    finally:
        db.close()


if __name__ == "__main__":
    main()
