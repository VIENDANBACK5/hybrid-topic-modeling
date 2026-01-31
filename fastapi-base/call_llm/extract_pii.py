#!/usr/bin/env python3
"""
LLM Extract cho: CHỈ SỐ SẢN XUẤT CÔNG NGHIỆP CẤP TỈNH (PII - Provincial Industrial Index)

THUẦN LLM - Không dùng Regex

Nguồn dữ liệu:
  - Bảng: important_posts
  - Filter: Posts có thông tin về sản xuất công nghiệp, IIP
  
Bảng đích:
  - pii_detail - Các chỉ số về sản xuất công nghiệp, IIP, các ngành công nghiệp
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
        logging.FileHandler('call_llm/pii_extraction.log'),
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
        "X-Title": "PII Data Extractor"
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


def save_to_pii(db, data: Dict) -> bool:
    """Save to pii_detail"""
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
            'pii_overall', 'pii_growth_rate', 'industrial_output_value',
            'mining_index', 'mining_output', 'mining_growth',
            'manufacturing_index', 'manufacturing_output', 'manufacturing_growth',
            'electricity_index', 'electricity_output', 'electricity_growth',
            'water_waste_index', 'water_waste_output', 'water_waste_growth',
            'food_processing_index', 'food_processing_output',
            'textile_index', 'textile_output',
            'leather_footwear_index', 'leather_footwear_output',
            'wood_products_index', 'wood_products_output',
            'chemical_index', 'chemical_output',
            'rubber_plastic_index', 'rubber_plastic_output',
            'metal_index', 'metal_output',
            'electronics_index', 'electronics_output',
            'electrical_equipment_index', 'electrical_equipment_output',
            'vehicle_index', 'vehicle_output',
            'state_owned_pii', 'private_pii', 'fdi_pii',
            'state_owned_output', 'private_output', 'fdi_output',
            'manufacturing_share', 'hightech_industry_share', 'supporting_industry_share',
            'labor_productivity', 'capacity_utilization', 'output_per_enterprise',
            'steel_production', 'cement_production', 'fertilizer_production', 'electricity_production',
            'industrial_enterprises', 'large_enterprises', 'sme_industrial',
            'industrial_workers', 'skilled_workers', 'average_wage_industrial',
            'notes', 'data_source', 'extraction_metadata'
        ]
        for field in required_fields:
            if field not in data:
                data[field] = None
        
        insert_query = text("""
            INSERT INTO pii_detail (
                province, source_post_id, source_url, period, year, quarter, month,
                pii_overall, pii_growth_rate, industrial_output_value,
                mining_index, mining_output, mining_growth,
                manufacturing_index, manufacturing_output, manufacturing_growth,
                electricity_index, electricity_output, electricity_growth,
                water_waste_index, water_waste_output, water_waste_growth,
                food_processing_index, food_processing_output,
                textile_index, textile_output,
                leather_footwear_index, leather_footwear_output,
                wood_products_index, wood_products_output,
                chemical_index, chemical_output,
                rubber_plastic_index, rubber_plastic_output,
                metal_index, metal_output,
                electronics_index, electronics_output,
                electrical_equipment_index, electrical_equipment_output,
                vehicle_index, vehicle_output,
                state_owned_pii, private_pii, fdi_pii,
                state_owned_output, private_output, fdi_output,
                manufacturing_share, hightech_industry_share, supporting_industry_share,
                labor_productivity, capacity_utilization, output_per_enterprise,
                steel_production, cement_production, fertilizer_production, electricity_production,
                industrial_enterprises, large_enterprises, sme_industrial,
                industrial_workers, skilled_workers, average_wage_industrial,
                notes, data_source, extraction_metadata
            ) VALUES (
                :province, :source_post_id, :source_url, :period, :year, :quarter, :month,
                :pii_overall, :pii_growth_rate, :industrial_output_value,
                :mining_index, :mining_output, :mining_growth,
                :manufacturing_index, :manufacturing_output, :manufacturing_growth,
                :electricity_index, :electricity_output, :electricity_growth,
                :water_waste_index, :water_waste_output, :water_waste_growth,
                :food_processing_index, :food_processing_output,
                :textile_index, :textile_output,
                :leather_footwear_index, :leather_footwear_output,
                :wood_products_index, :wood_products_output,
                :chemical_index, :chemical_output,
                :rubber_plastic_index, :rubber_plastic_output,
                :metal_index, :metal_output,
                :electronics_index, :electronics_output,
                :electrical_equipment_index, :electrical_equipment_output,
                :vehicle_index, :vehicle_output,
                :state_owned_pii, :private_pii, :fdi_pii,
                :state_owned_output, :private_output, :fdi_output,
                :manufacturing_share, :hightech_industry_share, :supporting_industry_share,
                :labor_productivity, :capacity_utilization, :output_per_enterprise,
                :steel_production, :cement_production, :fertilizer_production, :electricity_production,
                :industrial_enterprises, :large_enterprises, :sme_industrial,
                :industrial_workers, :skilled_workers, :average_wage_industrial,
                :notes, :data_source, :extraction_metadata
            )
        """)
        db.execute(insert_query, data)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi save pii_detail: {e}")
        db.rollback()
        return False


def get_posts_from_db(limit: int = 100) -> List[Dict]:
    """Lấy important_posts có nội dung về sản xuất công nghiệp"""
    try:
        db = SessionLocal()
        query = text("""
            SELECT id, title, content, url, dvhc as province, published_date, type_newspaper, document_type FROM important_posts
            WHERE type_newspaper = 'economy'
               AND (document_type IS NULL OR document_type != 'internal')
               AND (
                content ILIKE '%sản xuất công nghiệp%' OR
                content ILIKE '%công nghiệp%' OR
                content ILIKE '%chế biến chế tạo%' OR
                content ILIKE '%iip%' OR
                content ILIKE '%khu công nghiệp%' OR
                content ILIKE '%doanh nghiệp công nghiệp%' OR
                content ILIKE '%giá trị sản xuất%' OR
                content ILIKE '%sản lượng%' OR
                content ILIKE '%năng suất lao động%' OR
                content ILIKE '%công suất%'
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
        logger.info(f"Lấy được {len(posts)} posts về sản xuất công nghiệp từ DB")
        return posts
    except Exception as e:
        logger.error(f"Lỗi khi lấy posts từ DB: {e}")
        return []


def extract_pii_data(content: str, url: str, post_id: int, province: str) -> Optional[Dict]:
    """Extract chỉ số sản xuất công nghiệp từ văn bản"""
    prompt = f"""Phân tích văn bản và trích xuất các chỉ số SẢN XUẤT CÔNG NGHIỆP (PII/IIP).

Trả về JSON với cấu trúc (có thể bỏ trống nhiều field):
{{
  "location": null,
  "year": null,
  "quarter": null,
  "month": null,
  "pii_overall": null,
  "pii_growth_rate": null,
  "industrial_output_value": null,
  "mining_index": null,
  "mining_output": null,
  "mining_growth": null,
  "manufacturing_index": null,
  "manufacturing_output": null,
  "manufacturing_growth": null,
  "electricity_index": null,
  "electricity_output": null,
  "electricity_growth": null,
  "water_waste_index": null,
  "water_waste_output": null,
  "water_waste_growth": null,
  "food_processing_index": null,
  "food_processing_output": null,
  "textile_index": null,
  "textile_output": null,
  "leather_footwear_index": null,
  "leather_footwear_output": null,
  "wood_products_index": null,
  "wood_products_output": null,
  "chemical_index": null,
  "chemical_output": null,
  "rubber_plastic_index": null,
  "rubber_plastic_output": null,
  "metal_index": null,
  "metal_output": null,
  "electronics_index": null,
  "electronics_output": null,
  "electrical_equipment_index": null,
  "electrical_equipment_output": null,
  "vehicle_index": null,
  "vehicle_output": null,
  "state_owned_pii": null,
  "private_pii": null,
  "fdi_pii": null,
  "state_owned_output": null,
  "private_output": null,
  "fdi_output": null,
  "manufacturing_share": null,
  "hightech_industry_share": null,
  "supporting_industry_share": null,
  "labor_productivity": null,
  "capacity_utilization": null,
  "output_per_enterprise": null,
  "steel_production": null,
  "cement_production": null,
  "fertilizer_production": null,
  "electricity_production": null,
  "industrial_enterprises": null,
  "large_enterprises": null,
  "sme_industrial": null,
  "industrial_workers": null,
  "skilled_workers": null,
  "average_wage_industrial": null,
  "notes": null
}}

Giải thích các trường (KHÔNG CẦN ĐẦY ĐỦ - chỉ extract khi có trong văn bản):
- location (string): Tên địa phương
- year/quarter/month (int): Thời gian
- pii_overall (float): Chỉ số IIP tổng hợp (Index, base=100)
- pii_growth_rate (float): Tốc độ tăng trưởng IIP (%)
- industrial_output_value (float): Giá trị sản xuất công nghiệp (tỷ VNĐ)
- mining_* : Chỉ số và sản lượng khai khoáng
- manufacturing_* : Chỉ số và sản lượng công nghiệp chế biến
- electricity_* : Chỉ số và sản lượng điện, khí đốt, nước
- water_waste_* : Chỉ số cấp nước, xử lý rác
- food_processing_* : Chế biến thực phẩm
- textile_* : Dệt may
- leather_footwear_* : Da giày
- wood_products_* : Gỗ và sản phẩm gỗ
- chemical_* : Hóa chất
- rubber_plastic_* : Cao su và plastic
- metal_* : Kim loại
- electronics_* : Điện tử, máy tính
- electrical_equipment_* : Thiết bị điện
- vehicle_* : Phương tiện vận tải
- state_owned_* : Khu vực nhà nước
- private_* : Khu vực tư nhân
- fdi_* : Khu vực FDI
- manufacturing_share (float): Tỷ trọng chế biến chế tạo (%)
- hightech_industry_share (float): Tỷ trọng công nghiệp công nghệ cao (%)
- supporting_industry_share (float): Tỷ trọng công nghiệp hỗ trợ (%)
- labor_productivity (float): Năng suất lao động (triệu VNĐ/người)
- capacity_utilization (float): Tỷ lệ sử dụng công suất (%)
- output_per_enterprise (float): Sản lượng bình quân/DN (tỷ VNĐ)
- steel_production (float): Sản lượng thép (nghìn tấn)
- cement_production (float): Sản lượng xi măng (nghìn tấn)
- fertilizer_production (float): Sản lượng phân bón (nghìn tấn)
- electricity_production (float): Sản lượng điện (triệu kWh)
- industrial_enterprises (int): Số doanh nghiệp công nghiệp
- large_enterprises (int): Số DN công nghiệp lớn
- sme_industrial (int): Số DN công nghiệp vừa và nhỏ
- industrial_workers (int): Số lao động trong công nghiệp
- skilled_workers (int): Số lao động có tay nghề
- average_wage_industrial (float): Lương bình quân công nghiệp (triệu VNĐ)
- notes (string): Thông tin bổ sung

QUY TẮC:
1. LINH HOẠT: Extract BẤT KỲ chỉ số CÔNG NGHIỆP nào (không cần đầy đủ tất cả fields)
2. Các từ khóa cần chú ý:
   - Sản xuất công nghiệp, giá trị sản xuất, chỉ số IIP
   - Tăng trưởng công nghiệp, tốc độ tăng trưởng
   - Các ngành: khai khoáng, chế biến chế tạo, điện, dệt may, da giày, gỗ, hóa chất, điện tử, ô tô...
   - Khu vực: nhà nước, tư nhân, FDI
   - Doanh nghiệp công nghiệp, lao động công nghiệp
   - Năng suất lao động, công suất
   - Sản lượng: thép, xi măng, phân bón, điện
3. 📈 Chỉ số IIP:
   - Chỉ số IIP thường có base=100
   - Tăng trưởng thường tính so với cùng kỳ năm trước (%)
4. Nhận diện địa điểm: Trích xuất tên tỉnh/thành/huyện/xã từ văn bản
5. ⏰ Thời gian:
   - "Quý I/II/III/IV" → quarter=1/2/3/4
   - "6 tháng đầu năm" → quarter=2
   - "9 tháng" → quarter=3
   - "Năm 2024" → year=2024
6. CHỈ trả về {{"no_data": true}} nếu văn bản HOÀN TOÀN KHÔNG có chỉ số công nghiệp

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
        logger.error(f"Lỗi extract PII: {e}")
        return None


def process_post(post: Dict, db) -> int:
    """Xử lý 1 post - Extract PII"""
    post_id = post.get("id")
    content = post.get("content", "")
    title = post.get("title", "")
    province = post.get("province", "Hưng Yên")
    url = post.get("url") or None
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Post ID: {post_id}")
    logger.info(f"Title: {title[:100]}")
    
    data = extract_pii_data(content, url, post_id, province)
    if data:
        data["document_type"] = document_type
        if save_to_pii(db, data):
            logger.info(f"Saved to pii_detail")
            return 1
        else:
            logger.error(f"Failed to save pii_detail")
    
    return 0


def main():
    """Main function"""
    logger.info("="*80)
    logger.info("BẮT ĐẦU LLM EXTRACTION - CHỈ SỐ SẢN XUẤT CÔNG NGHIỆP (PII)")
    logger.info(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80)
    
    db = SessionLocal()
    try:
        posts = get_posts_from_db(limit=BATCH_SIZE)
        
        if not posts:
            return {
                "status": "no_data",
                "message": "Không có posts về sản xuất công nghiệp",
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
