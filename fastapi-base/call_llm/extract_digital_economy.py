#!/usr/bin/env python3
"""
LLM Extract cho: KINH TẾ SỐ (Digital Economy)

THUẦN LLM - Không dùng Regex

Nguồn dữ liệu:
  - Bảng: important_posts
  - Filter: Posts có thông tin về kinh tế số, thương mại điện tử, fintech, startup
  
Bảng đích:
  - digital_economy_detail - Các chỉ số về kinh tế số, TMĐT, thanh toán điện tử
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
        logging.FileHandler('call_llm/digital_economy_extraction.log'),
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
        "X-Title": "Digital Economy Data Extractor"
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


def save_to_digital_economy(db, data: Dict) -> bool:
    """Save to digital_economy_detail"""
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
            'digital_economy_gdp', 'digital_economy_gdp_share', 'digital_economy_growth_rate',
            'ecommerce_revenue', 'ecommerce_users', 'ecommerce_transactions', 'ecommerce_growth_rate',
            'digital_payment_volume', 'digital_payment_transactions', 'digital_wallet_users', 'cashless_payment_rate',
            'digital_companies', 'tech_startups', 'unicorn_companies', 'digital_companies_revenue',
            'fintech_revenue', 'edtech_revenue', 'healthtech_revenue', 'digital_content_revenue',
            'digital_exports', 'software_exports', 'digital_services_exports',
            'ict_investment', 'digital_infrastructure_investment',
            'notes', 'data_source', 'extraction_metadata'
        ]
        for field in required_fields:
            if field not in data:
                data[field] = None
        
        insert_query = text("""
            INSERT INTO digital_economy_detail (
                province, source_post_id, source_url, period, year, quarter, month,
                digital_economy_gdp, digital_economy_gdp_share, digital_economy_growth_rate,
                ecommerce_revenue, ecommerce_users, ecommerce_transactions, ecommerce_growth_rate,
                digital_payment_volume, digital_payment_transactions, digital_wallet_users, cashless_payment_rate,
                digital_companies, tech_startups, unicorn_companies, digital_companies_revenue,
                fintech_revenue, edtech_revenue, healthtech_revenue, digital_content_revenue,
                internet_penetration, broadband_subscribers, mobile_internet_users, average_internet_speed,
                digital_service_exports, software_exports, it_outsourcing_revenue,
                digital_workforce, it_graduates, digital_skills_training,
                digital_investment, venture_capital_digital,
                notes, data_source, extraction_metadata
            ) VALUES (
                :province, :source_post_id, :source_url, :period, :year, :quarter, :month,
                :digital_economy_gdp, :digital_economy_gdp_share, :digital_economy_growth_rate,
                :ecommerce_revenue, :ecommerce_users, :ecommerce_transactions, :ecommerce_growth_rate,
                :digital_payment_volume, :digital_payment_transactions, :digital_wallet_users, :cashless_payment_rate,
                :digital_companies, :tech_startups, :unicorn_companies, :digital_companies_revenue,
                :fintech_revenue, :edtech_revenue, :healthtech_revenue, :digital_content_revenue,
                :internet_penetration, :broadband_subscribers, :mobile_internet_users, :average_internet_speed,
                :digital_service_exports, :software_exports, :it_outsourcing_revenue,
                :digital_workforce, :it_graduates, :digital_skills_training,
                :digital_investment, :venture_capital_digital,
                :notes, :data_source, :extraction_metadata
            )
        """)
        db.execute(insert_query, data)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi save digital_economy_detail: {e}")
        db.rollback()
        return False


def get_posts_from_db(limit: int = 100) -> List[Dict]:
    """Lấy important_posts có nội dung về kinh tế số"""
    try:
        db = SessionLocal()
        query = text("""
            SELECT id, title, content, url, dvhc as province, published_date, type_newspaper
            FROM important_posts
            WHERE type_newspaper = 'economy'
               AND (
                content ILIKE '%kinh tế số%' OR
                content ILIKE '%thương mại điện tử%' OR
                content ILIKE '%tmđt%' OR
                content ILIKE '%e-commerce%' OR
                content ILIKE '%thanh toán điện tử%' OR
                content ILIKE '%fintech%' OR
                content ILIKE '%startup%' OR
                content ILIKE '%công nghệ số%' OR
                content ILIKE '%chuyển đổi số%' OR
                content ILIKE '%dịch vụ số%'
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
        logger.info(f"Lấy được {len(posts)} posts về kinh tế số từ DB")
        return posts
    except Exception as e:
        logger.error(f"Lỗi khi lấy posts từ DB: {e}")
        return []


def extract_digital_economy_data(content: str, url: str, post_id: int, province: str) -> Optional[Dict]:
    """Extract chỉ số kinh tế số từ văn bản"""
    prompt = f"""Phân tích văn bản và trích xuất các chỉ số KINH TẾ SỐ.

Trả về JSON với cấu trúc:
{{
  "location": null,
  "year": null,
  "quarter": null,
  "month": null,
  "digital_economy_gdp": null,
  "digital_economy_gdp_share": null,
  "digital_economy_growth_rate": null,
  "ecommerce_revenue": null,
  "ecommerce_users": null,
  "ecommerce_transactions": null,
  "ecommerce_growth_rate": null,
  "digital_payment_volume": null,
  "digital_payment_transactions": null,
  "digital_wallet_users": null,
  "cashless_payment_rate": null,
  "digital_companies": null,
  "tech_startups": null,
  "unicorn_companies": null,
  "digital_companies_revenue": null,
  "fintech_revenue": null,
  "edtech_revenue": null,
  "healthtech_revenue": null,
  "digital_content_revenue": null,
  "internet_penetration": null,
  "broadband_subscribers": null,
  "mobile_internet_users": null,
  "average_internet_speed": null,
  "digital_service_exports": null,
  "software_exports": null,
  "it_outsourcing_revenue": null,
  "digital_workforce": null,
  "it_graduates": null,
  "digital_skills_training": null,
  "digital_investment": null,
  "venture_capital_digital": null,
  "notes": null
}}

Giải thích các trường:
- location (string): Tên địa phương (tỉnh/thành/huyện/xã)
- year/quarter/month (int): Thời gian
- digital_economy_gdp (float): GDP từ kinh tế số (tỷ VNĐ)
- digital_economy_gdp_share (float): Tỷ trọng kinh tế số trong GDP (%)
- digital_economy_growth_rate (float): Tốc độ tăng trưởng kinh tế số (%)
- ecommerce_revenue (float): Doanh thu thương mại điện tử (tỷ VNĐ)
- ecommerce_users (int): Số người dùng TMĐT
- ecommerce_transactions (int): Số giao dịch TMĐT
- ecommerce_growth_rate (float): Tăng trưởng TMĐT (%)
- digital_payment_volume (float): Giá trị thanh toán điện tử (tỷ VNĐ)
- digital_payment_transactions (int): Số giao dịch thanh toán điện tử
- digital_wallet_users (int): Số người dùng ví điện tử
- cashless_payment_rate (float): Tỷ lệ thanh toán không dùng tiền mặt (%)
- digital_companies (int): Số doanh nghiệp công nghệ số
- tech_startups (int): Số startup công nghệ
- unicorn_companies (int): Số công ty kỳ lân
- digital_companies_revenue (float): Doanh thu DN số (tỷ VNĐ)
- fintech_revenue (float): Doanh thu Fintech (tỷ VNĐ)
- edtech_revenue (float): Doanh thu Edtech (tỷ VNĐ)
- healthtech_revenue (float): Doanh thu Healthtech (tỷ VNĐ)
- digital_content_revenue (float): Doanh thu nội dung số (tỷ VNĐ)
- internet_penetration (float): Tỷ lệ phủ sóng Internet (%)
- broadband_subscribers (int): Số thuê bao băng thông rộng
- mobile_internet_users (int): Số người dùng Internet di động
- average_internet_speed (float): Tốc độ Internet trung bình (Mbps)
- digital_service_exports (float): Xuất khẩu dịch vụ số (triệu USD)
- software_exports (float): Xuất khẩu phần mềm (triệu USD)
- it_outsourcing_revenue (float): Doanh thu gia công phần mềm (triệu USD)
- digital_workforce (int): Số lao động trong lĩnh vực số
- it_graduates (int): Số sinh viên tốt nghiệp IT/năm
- digital_skills_training (int): Số người được đào tạo kỹ năng số
- digital_investment (float): Đầu tư vào kinh tế số (tỷ VNĐ)
- venture_capital_digital (float): Vốn đầu tư mạo hiểm vào startup số (triệu USD)
- notes (string): Thông tin bổ sung

QUY TẮC:
1. LINH HOẠT: Extract BẤT KỲ chỉ số KINH TẾ SỐ nào (không cần đầy đủ tất cả fields)
2. Các từ khóa cần chú ý:
   - Kinh tế số, digital economy, GDP kinh tế số
   - Thương mại điện tử, TMĐT, e-commerce, mua sắm online
   - Thanh toán điện tử, ví điện tử, cashless, QR code
   - Fintech, Edtech, Healthtech
   - Startup công nghệ, công ty kỳ lân, unicorn
   - Internet, băng thông, 4G, 5G, cáp quang
   - Xuất khẩu phần mềm, IT outsourcing
3. Nhận diện địa điểm: Trích xuất tên tỉnh/thành/huyện/xã từ văn bản
4. ⏰ Thời gian:
   - "Quý I/II/III/IV" → quarter=1/2/3/4
   - "6 tháng đầu năm" → quarter=2
   - "9 tháng" → quarter=3
   - "Năm 2024" → year=2024
5. CHỈ trả về {{"no_data": true}} nếu văn bản HOÀN TOÀN KHÔNG có chỉ số kinh tế số

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
        logger.error(f"Lỗi extract digital_economy: {e}")
        return None


def process_post(post: Dict, db) -> int:
    """Xử lý 1 post - Extract kinh tế số"""
    post_id = post.get("id")
    content = post.get("content", "")
    title = post.get("title", "")
    province = post.get("province", "Hưng Yên")
    url = post.get("url") or None
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Post ID: {post_id}")
    logger.info(f"Title: {title[:100]}")
    
    data = extract_digital_economy_data(content, url, post_id, province)
    if data:
        if save_to_digital_economy(db, data):
            logger.info(f"Saved to digital_economy_detail")
            return 1
        else:
            logger.error(f"Failed to save digital_economy_detail")
    
    return 0


def main():
    """Main function"""
    logger.info("="*80)
    logger.info("BẮT ĐẦU LLM EXTRACTION - KINH TẾ SỐ")
    logger.info(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80)
    
    db = SessionLocal()
    try:
        posts = get_posts_from_db(limit=BATCH_SIZE)
        
        if not posts:
            return {
                "status": "no_data",
                "message": "Không có posts về kinh tế số",
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
