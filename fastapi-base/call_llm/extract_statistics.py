#!/usr/bin/env python3
"""
LLM Extract cho: THỐNG KÊ KINH TẾ - CHÍNH TRỊ

THUẦN LLM - Không dùng Regex

Nguồn dữ liệu:
  - Bảng: important_posts
  - Filter: Tất cả posts có số liệu kinh tế/chính trị
  
Bảng đích (2 bảng):
  1. economic_statistics       - Thống kê kinh tế (GDP, thu nhập, đầu tư, xuất khẩu...)
  2. political_statistics      - Thống kê chính trị (đảng viên, tổ chức đảng, hoạt động chính trị...)
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
        logging.FileHandler('call_llm/statistics_extraction.log'),
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


# ============== DB SAVE FUNCTIONS ==============
def save_to_economic_statistics(db, data: Dict) -> bool:
    """Save to economic_statistics"""
    try:
        # Build period string from year/quarter/month
        period_parts = []
        if data.get('year'):
            period_parts.append(f"Năm {data['year']}")
        if data.get('quarter'):
            period_parts.append(f"Quý {data['quarter']}")
        if data.get('month'):
            period_parts.append(f"Tháng {data['month']}")
        data['period'] = ", ".join(period_parts) if period_parts else None
        
        insert_query = text("""
            INSERT INTO economic_statistics (
                dvhc, source_post_id, source_url, period, year,
                total_production_value, growth_rate,
                total_budget_revenue, budget_collection_efficiency,
                notes, extraction_metadata
            ) VALUES (
                :dvhc, :source_post_id, :source_url, :period, :year,
                :total_production_value, :growth_rate,
                :total_budget_revenue, :budget_collection_efficiency,
                :notes, :extraction_metadata
            )
        """)
        db.execute(insert_query, data)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi save economic_statistics: {e}")
        db.rollback()
        return False


def save_to_political_statistics(db, data: Dict) -> bool:
    """Save to political_statistics"""
    try:
        # Build period string from year/quarter/month
        period_parts = []
        if data.get('year'):
            period_parts.append(f"Năm {data['year']}")
        if data.get('quarter'):
            period_parts.append(f"Quý {data['quarter']}")
        if data.get('month'):
            period_parts.append(f"Tháng {data['month']}")
        data['period'] = ", ".join(period_parts) if period_parts else None
        
        insert_query = text("""
            INSERT INTO political_statistics (
                dvhc, source_post_id, source_url, period, year,
                party_organization_count, party_member_count,
                party_size_description, new_party_members, party_cells_count,
                notes, extraction_metadata
            ) VALUES (
                :dvhc, :source_post_id, :source_url, :period, :year,
                :party_organization_count, :party_member_count,
                :party_size_description, :new_party_members, :party_cells_count,
                :notes, :extraction_metadata
            )
        """)
        db.execute(insert_query, data)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi save political_statistics: {e}")
        db.rollback()
        return False


def call_llm(prompt: str, max_retries: int = 3) -> Optional[str]:
    """Call OpenRouter LLM API"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": API_BASE_URL,
        "X-Title": "Statistics Data Extractor"
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
    """Lấy important_posts CHỈ từ xã Thư Vũ và phường Trà Lý"""
    try:
        db = SessionLocal()
        query = text("""
            SELECT id, title, content, url, dvhc as province, published_date, type_newspaper
            FROM important_posts
            WHERE dvhc IN ('Thư Vũ', 'Trà Lý')
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
        logger.info(f"Lấy được {len(posts)} posts từ DB")
        return posts
    except Exception as e:
        logger.error(f"Lỗi khi lấy posts từ DB: {e}")
        return []


def extract_economic_statistics(content: str, url: str, post_id: int, province: str) -> Optional[Dict]:
    """Extract thống kê kinh tế CHỈ cho xã Thư Vũ và phường Trà Lý"""
    prompt = f"""Phân tích văn bản và trích xuất các chỉ số KINH TẾ.

Trả về JSON với cấu trúc:
{{
  "location": null,
  "year": null,
  "quarter": null,
  "month": null,
  "total_production_value": null,
  "growth_rate": null,
  "total_budget_revenue": null,
  "budget_collection_efficiency": null,
  "notes": null
}}

Giải thích các trường:
- location (string): Tên xã/phường ("xã Thư Vũ" hoặc "phường Trà Lý")
- year (integer): Năm
- quarter (integer): Quý (1-4)
- month (integer): Tháng (1-12)
- total_production_value (float): Tổng giá trị sản xuất/GDP (tỷ đồng)
- growth_rate (float): Tốc độ tăng trưởng (%)
- total_budget_revenue (float): Tổng thu ngân sách (tỷ đồng)
- budget_collection_efficiency (float): % thực hiện so kế hoạch thu ngân sách
- notes (string): Các chỉ số khác

QUY TẮC:
1. Văn bản này ĐÃ ĐƯỢC LỌC - chỉ thuộc về Thư Vũ hoặc Trà Lý
2. LINH HOẠT: Extract BẤT KỲ chỉ số KINH TẾ nào (không cần đầy đủ tất cả fields)
3. Các chỉ số thường gặp cần extract:
   - Giá trị sản xuất/GDP/tổng giá trị sản xuất → total_production_value
   - Tăng trưởng/phát triển (%) → growth_rate
   - Thu ngân sách/thu nội địa/thu NSNN → total_budget_revenue
   - % thực hiện/vượt kế hoạch thu → budget_collection_efficiency
   - FDI, xuất khẩu, đầu tư, thu nhập BQ, GRDP → notes
4. Nhận diện địa điểm:
   - Nếu thấy "Thư Vũ" (có thể là "xã Thư Vũ", "đảng bộ xã Thư Vũ", "Thư Vũ đạt"...) → location="xã Thư Vũ"
   - Nếu thấy "Trà Lý" (có thể là "phường Trà Lý", "Đảng bộ phường Trà Lý", "Trà Lý hoàn thành"...) → location="phường Trà Lý"
5. ⏰ Thời gian:
   - "Quý I/II/III/IV" → quarter=1/2/3/4
   - "6 tháng"/"nửa đầu năm" → quarter=2
   - "9 tháng" → quarter=3
   - "Năm 2024"/"năm học 2024-2025" → year=2024
6. CHỈ trả về {{"no_data": true}} nếu văn bản HOÀN TOÀN KHÔNG có chỉ số kinh tế

Văn bản:
\"\"\"
{content[:3500]}
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
        
        # Determine dvhc based on location
        location = data.get("location", "")
        if "Thư Vũ" in location:
            data["dvhc"] = "Thư Vũ"
        elif "Trà Lý" in location:
            data["dvhc"] = "Trà Lý"
        else:
            logger.warning(f"Unknown location in economic: {location}")
            return None
        
        data.pop("location", None)  # Remove location field
        data["source_post_id"] = post_id
        # Only save real URLs (not fallback strings)
        data["source_url"] = url if url and url.startswith("http") else None
        data["extraction_metadata"] = None
        return data
        
    except Exception as e:
        logger.error(f"Lỗi extract economic_statistics: {e}")
        return None


def extract_political_statistics(content: str, url: str, post_id: int, province: str) -> Optional[Dict]:
    """Extract thống kê chính trị CHỈ cho xã Thư Vũ và phường Trà Lý"""
    prompt = f"""Phân tích văn bản và trích xuất các chỉ số CHÍNH TRỊ - ĐẢNG.

Trả về JSON với cấu trúc:
{{
  "location": null,
  "year": null,
  "quarter": null,
  "month": null,
  "party_organization_count": null,
  "party_member_count": null,
  "party_size_description": null,
  "new_party_members": null,
  "party_cells_count": null,
  "notes": null
}}

Giải thích các trường:
- location (string): Tên xã/phường ("xã Thư Vũ" hoặc "phường Trà Lý")
- year (integer): Năm
- quarter (integer): Quý (1-4)
- month (integer): Tháng (1-12)
- party_organization_count (integer): Số tổ chức đảng
- party_member_count (integer): Tổng số đảng viên
- party_size_description (string): Mô tả quy mô (VD: "Đảng bộ 2.200 đảng viên")
- new_party_members (integer): Số đảng viên mới kết nạp
- party_cells_count (integer): Số chi bộ/chi bộ cơ sở
- notes (string): Hoạt động chính trị, cuộc họp, bầu cử, danh hiệu...

QUY TẮC:
1. Văn bản này ĐÃ ĐƯỢC LỌC - chỉ thuộc về Thư Vũ hoặc Trà Lý
2. LINH HOẠT: Extract BẤT KỲ chỉ số CHÍNH TRỊ/ĐẢNG nào (không cần đầy đủ)
3. Các chỉ số thường gặp:
   - Số tổ chức đảng/đảng bộ → party_organization_count
   - Số đảng viên/tổng số ĐV → party_member_count
   - "Đảng bộ X đảng viên"/quy mô → party_size_description
   - Kết nạp đảng viên mới → new_party_members
   - Số chi bộ/chi bộ cơ sở → party_cells_count
   - Các danh hiệu ("trong sạch vững mạnh", "hoàn thành xuất sắc"), cuộc họp, nghị quyết → notes
4. Nhận diện địa điểm:
   - Thấy "Thư Vũ" (bất kỳ dạng nào) → location="xã Thư Vũ"
   - Thấy "Trà Lý" (bất kỳ dạng nào) → location="phường Trà Lý"
5. ⏰ Thời gian:
   - "Quý I/II/III/IV" → quarter=1/2/3/4
   - "6 tháng"/"nửa đầu năm" → quarter=2
   - "9 tháng" → quarter=3
   - "Năm 2024" → year=2024
6. CHỈ trả về {{"no_data": true}} nếu văn bản HOÀN TOÀN KHÔNG có thông tin chính trị/đảng

Văn bản:
\"\"\"
{content[:3500]}
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
        
        # Determine dvhc based on location
        location = data.get("location", "")
        if "Thư Vũ" in location:
            data["dvhc"] = "Thư Vũ"
        elif "Trà Lý" in location:
            data["dvhc"] = "Trà Lý"
        else:
            logger.warning(f"Unknown location in political: {location}")
            return None
        
        data.pop("location", None)  # Remove location field
        data["source_post_id"] = post_id
        # Only save real URLs (not fallback strings)
        data["source_url"] = url if url and url.startswith("http") else None
        data["extraction_metadata"] = None
        return data
        
    except Exception as e:
        logger.error(f"Lỗi extract political_statistics: {e}")
        return None


def process_post(post: Dict, db) -> Dict[str, int]:
    """Xử lý 1 post - Extract 2 loại thống kê"""
    post_id = post.get("id")
    content = post.get("content", "")
    title = post.get("title", "")
    province = post.get("province", "Hưng Yên")
    url = post.get("url") or None  # Only real URL or None
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Post ID: {post_id}")
    logger.info(f"Title: {title[:100]}")
    
    results = {
        "economic": 0,
        "political": 0
    }
    
    # 1. Economic Statistics
    econ = extract_economic_statistics(content, url, post_id, province)
    if econ:
        if save_to_economic_statistics(db, econ):
            logger.info(f"Saved to economic_statistics")
            results["economic"] = 1
        else:
            logger.error(f"Failed to save economic_statistics")
    
    time.sleep(DELAY_BETWEEN_CALLS)
    
    # 2. Political Statistics
    pol = extract_political_statistics(content, url, post_id, province)
    if pol:
        if save_to_political_statistics(db, pol):
            logger.info(f"Saved to political_statistics")
            results["political"] = 1
        else:
            logger.error(f"Failed to save political_statistics")
    
    time.sleep(DELAY_BETWEEN_CALLS)
    return results


def main():
    """Main function"""
    logger.info("="*80)
    logger.info("BẮT ĐẦU LLM EXTRACTION - THỐNG KÊ KINH TẾ - CHÍNH TRỊ")
    logger.info(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80)
    
    db = SessionLocal()
    try:
        posts = get_posts_from_db(limit=BATCH_SIZE)
        
        if not posts:
            return {
                "status": "no_data",
                "message": "Không có posts nào",
                "processed": 0
            }
        
        total_extracted = {
            "economic": 0,
            "political": 0
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
        logger.info(f"Economic Statistics: {total_extracted['economic']}")
        logger.info(f"Political Statistics: {total_extracted['political']}")
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
