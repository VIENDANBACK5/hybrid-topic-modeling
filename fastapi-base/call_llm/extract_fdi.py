#!/usr/bin/env python3
"""
LLM Extract cho: THU HÚT ĐẦU TƯ TRỰC TIẾP NƯỚC NGOÀI (FDI)

THUẦN LLM - Không dùng Regex

Nguồn dữ liệu:
  - Bảng: important_posts
  - Filter: Posts có thông tin về FDI, đầu tư nước ngoài
  
Bảng đích:
  - fdi_detail - Các chỉ số về vốn FDI, dự án, ngành nghề, quốc gia đầu tư
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
        logging.FileHandler('call_llm/fdi_extraction.log'),
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
        "X-Title": "FDI Data Extractor"
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


def save_to_fdi(db, data: Dict) -> bool:
    """Save to fdi_detail"""
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
            'registered_capital', 'new_projects_capital', 'additional_capital', 'capital_contribution',
            'disbursed_capital', 'disbursement_rate', 'accumulated_disbursement',
            'total_projects', 'new_projects', 'adjusted_projects', 'share_purchase_projects',
            'manufacturing_fdi', 'realestate_fdi', 'retail_fdi', 'construction_fdi',
            'technology_fdi', 'energy_fdi', 'agriculture_fdi',
            'japan_fdi', 'korea_fdi', 'singapore_fdi', 'china_fdi', 'taiwan_fdi', 'hongkong_fdi',
            'europe_fdi', 'us_fdi', 'other_countries_fdi',
            'fdi_export_value', 'fdi_import_value', 'fdi_trade_surplus', 'fdi_sector_employees',
            'fdi_gdp_contribution', 'fdi_revenue_to_budget', 'fdi_share_in_industry', 'fdi_share_in_exports',
            'notes', 'data_source', 'extraction_metadata'
        ]
        for field in required_fields:
            if field not in data:
                data[field] = None
        
        insert_query = text("""
            INSERT INTO fdi_detail (
                province, source_post_id, source_url, period, year, quarter, month,
                registered_capital, new_projects_capital, additional_capital, capital_contribution,
                disbursed_capital, disbursement_rate, accumulated_disbursement,
                total_projects, new_projects, adjusted_projects, share_purchase_projects,
                manufacturing_fdi, realestate_fdi, retail_fdi, construction_fdi, 
                technology_fdi, energy_fdi, agriculture_fdi,
                japan_fdi, korea_fdi, singapore_fdi, china_fdi, taiwan_fdi, 
                hongkong_fdi, thailand_fdi, usa_fdi, eu_fdi,
                wholly_owned_fdi, joint_venture_fdi, bcc_fdi,
                fdi_contribution_grdp, fdi_export_value, fdi_export_share, 
                fdi_employment, fdi_tax_revenue,
                industrial_zones, economic_zones, occupancy_rate,
                fortune500_investors, high_tech_projects,
                notes, data_source, extraction_metadata
            ) VALUES (
                :province, :source_post_id, :source_url, :period, :year, :quarter, :month,
                :registered_capital, :new_projects_capital, :additional_capital, :capital_contribution,
                :disbursed_capital, :disbursement_rate, :accumulated_disbursement,
                :total_projects, :new_projects, :adjusted_projects, :share_purchase_projects,
                :manufacturing_fdi, :realestate_fdi, :retail_fdi, :construction_fdi, 
                :technology_fdi, :energy_fdi, :agriculture_fdi,
                :japan_fdi, :korea_fdi, :singapore_fdi, :china_fdi, :taiwan_fdi, 
                :hongkong_fdi, :thailand_fdi, :usa_fdi, :eu_fdi,
                :wholly_owned_fdi, :joint_venture_fdi, :bcc_fdi,
                :fdi_contribution_grdp, :fdi_export_value, :fdi_export_share, 
                :fdi_employment, :fdi_tax_revenue,
                :industrial_zones, :economic_zones, :occupancy_rate,
                :fortune500_investors, :high_tech_projects,
                :notes, :data_source, :extraction_metadata
            )
        """)
        db.execute(insert_query, data)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi save fdi_detail: {e}")
        db.rollback()
        return False


def get_posts_from_db(limit: int = 100) -> List[Dict]:
    """Lấy important_posts có nội dung về FDI"""
    try:
        db = SessionLocal()
        query = text("""
            SELECT id, title, content, url, dvhc as province, published_date, type_newspaper, document_type FROM important_posts
            WHERE type_newspaper = 'economy'
               AND (document_type IS NULL OR document_type != 'internal')
               AND (
                content ILIKE '%fdi%' OR
                content ILIKE '%đầu tư nước ngoài%' OR
                content ILIKE '%đầu tư trực tiếp%' OR
                content ILIKE '%vốn nước ngoài%' OR
                content ILIKE '%dự án fdi%' OR
                content ILIKE '%khu công nghiệp%' OR
                content ILIKE '%khu kinh tế%' OR
                content ILIKE '%nhà đầu tư nước ngoài%' OR
                content ILIKE '%giải ngân%' OR
                content ILIKE '%cấp phép đầu tư%'
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
                "type_newspaper": row[6],
                "document_type": row[7]
            })
        
        db.close()
        logger.info(f"Lấy được {len(posts)} posts về FDI từ DB")
        return posts
    except Exception as e:
        logger.error(f"Lỗi khi lấy posts từ DB: {e}")
        return []


def extract_fdi_data(content: str, url: str, post_id: int, province: str) -> Optional[Dict]:
    """Extract chỉ số FDI từ văn bản"""
    prompt = f"""Phân tích văn bản và trích xuất các chỉ số THU HÚT FDI (Đầu tư Trực tiếp Nước ngoài).

Trả về JSON với cấu trúc:
{{
  "location": null,
  "year": null,
  "quarter": null,
  "month": null,
  "registered_capital": null,
  "new_projects_capital": null,
  "additional_capital": null,
  "capital_contribution": null,
  "disbursed_capital": null,
  "disbursement_rate": null,
  "accumulated_disbursement": null,
  "total_projects": null,
  "new_projects": null,
  "adjusted_projects": null,
  "share_purchase_projects": null,
  "manufacturing_fdi": null,
  "realestate_fdi": null,
  "retail_fdi": null,
  "construction_fdi": null,
  "technology_fdi": null,
  "energy_fdi": null,
  "agriculture_fdi": null,
  "japan_fdi": null,
  "korea_fdi": null,
  "singapore_fdi": null,
  "china_fdi": null,
  "taiwan_fdi": null,
  "hongkong_fdi": null,
  "thailand_fdi": null,
  "usa_fdi": null,
  "eu_fdi": null,
  "wholly_owned_fdi": null,
  "joint_venture_fdi": null,
  "bcc_fdi": null,
  "fdi_contribution_grdp": null,
  "fdi_export_value": null,
  "fdi_export_share": null,
  "fdi_employment": null,
  "fdi_tax_revenue": null,
  "industrial_zones": null,
  "economic_zones": null,
  "occupancy_rate": null,
  "fortune500_investors": null,
  "high_tech_projects": null,
  "notes": null
}}

Giải thích các trường:
- location (string): Tên địa phương (tỉnh/thành/huyện/xã)
- year/quarter/month (int): Thời gian
- registered_capital (float): Vốn FDI đăng ký (triệu USD)
- new_projects_capital (float): Vốn đăng ký dự án mới (triệu USD)
- additional_capital (float): Vốn đăng ký tăng thêm (triệu USD)
- capital_contribution (float): Vốn góp mua cổ phần (triệu USD)
- disbursed_capital (float): Vốn FDI giải ngân (triệu USD)
- disbursement_rate (float): Tỷ lệ giải ngân so với đăng ký (%)
- accumulated_disbursement (float): Vốn giải ngân lũy kế (triệu USD)
- total_projects (int): Tổng số dự án (mới + tăng vốn + góp vốn)
- new_projects (int): Số dự án đầu tư mới
- adjusted_projects (int): Số lượt dự án tăng vốn
- share_purchase_projects (int): Số lượt góp vốn mua cổ phần
- manufacturing_fdi (float): FDI vào sản xuất chế biến (triệu USD)
- realestate_fdi (float): FDI vào bất động sản (triệu USD)
- retail_fdi (float): FDI vào bán lẻ (triệu USD)
- construction_fdi (float): FDI vào xây dựng (triệu USD)
- technology_fdi (float): FDI vào CNTT (triệu USD)
- energy_fdi (float): FDI vào điện, khí đốt, nước (triệu USD)
- agriculture_fdi (float): FDI vào nông lâm ngư nghiệp (triệu USD)
- japan_fdi (float): FDI từ Nhật Bản (triệu USD)
- korea_fdi (float): FDI từ Hàn Quốc (triệu USD)
- singapore_fdi (float): FDI từ Singapore (triệu USD)
- china_fdi (float): FDI từ Trung Quốc (triệu USD)
- taiwan_fdi (float): FDI từ Đài Loan (triệu USD)
- hongkong_fdi (float): FDI từ Hồng Kông (triệu USD)
- thailand_fdi (float): FDI từ Thái Lan (triệu USD)
- usa_fdi (float): FDI từ Hoa Kỳ (triệu USD)
- eu_fdi (float): FDI từ EU (triệu USD)
- wholly_owned_fdi (float): FDI 100% vốn nước ngoài (triệu USD)
- joint_venture_fdi (float): FDI liên doanh (triệu USD)
- bcc_fdi (float): FDI hợp đồng hợp tác kinh doanh (triệu USD)
- fdi_contribution_grdp (float): Đóng góp FDI vào GRDP (%)
- fdi_export_value (float): Giá trị xuất khẩu từ FDI (triệu USD)
- fdi_export_share (float): Tỷ trọng xuất khẩu FDI/tổng XK (%)
- fdi_employment (int): Số lao động trong khu vực FDI (người)
- fdi_tax_revenue (float): Thu ngân sách từ FDI (tỷ VNĐ)
- industrial_zones (int): Số khu công nghiệp có FDI
- economic_zones (int): Số khu kinh tế có FDI
- occupancy_rate (float): Tỷ lệ lấp đầy KCN/KKT (%)
- fortune500_investors (int): Số nhà đầu tư Fortune 500
- high_tech_projects (int): Số dự án công nghệ cao
- notes (string): Thông tin bổ sung

QUY TẮC:
1. LINH HOẠT: Extract BẤT KỲ chỉ số FDI nào (không cần đầy đủ tất cả fields)
2. Các từ khóa cần chú ý:
   - Vốn FDI, vốn đăng ký, vốn giải ngân, vốn đầu tư nước ngoài
   - Dự án FDI, dự án mới, tăng vốn, góp vốn mua cổ phần
   - Nhà đầu tư: Nhật Bản, Hàn Quốc, Singapore, Trung Quốc, Đài Loan, etc.
   - Ngành: sản xuất, bất động sản, xây dựng, công nghệ, năng lượng
   - Khu công nghiệp, khu kinh tế, KCN, KKT
   - Xuất khẩu FDI, lao động FDI, thu ngân sách từ FDI
3. 💰 Đơn vị: 
   - Vốn FDI thường tính bằng triệu USD
   - Thu ngân sách tính bằng tỷ VNĐ
4. Nhận diện địa điểm: Trích xuất tên tỉnh/thành/huyện/xã từ văn bản
5. ⏰ Thời gian:
   - "Quý I/II/III/IV" → quarter=1/2/3/4
   - "6 tháng đầu năm" → quarter=2
   - "9 tháng" → quarter=3
   - "Năm 2024" → year=2024
6. CHỈ trả về {{"no_data": true}} nếu văn bản HOÀN TOÀN KHÔNG có chỉ số FDI

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
        logger.error(f"Lỗi extract FDI: {e}")
        return None


def process_post(post: Dict, db) -> int:
    """Xử lý 1 post - Extract FDI"""
    post_id = post.get("id")
    content = post.get("content", "")
    title = post.get("title", "")
    province = post.get("province", "Hưng Yên")
    url = post.get("url") or None
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Post ID: {post_id}")
    logger.info(f"Title: {title[:100]}")
    
    data = extract_fdi_data(content, url, post_id, province)
    if data:
        data["document_type"] = post.get("document_type")
        if save_to_fdi(db, data):
            logger.info(f"Saved to fdi_detail")
            return 1
        else:
            logger.error(f"Failed to save fdi_detail")
    
    return 0


def main():
    """Main function"""
    logger.info("="*80)
    logger.info("BẮT ĐẦU LLM EXTRACTION - THU HÚT FDI")
    logger.info(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80)
    
    db = SessionLocal()
    try:
        posts = get_posts_from_db(limit=BATCH_SIZE)
        
        if not posts:
            return {
                "status": "no_data",
                "message": "Không có posts về FDI",
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
