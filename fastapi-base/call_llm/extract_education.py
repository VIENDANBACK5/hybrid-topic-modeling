#!/usr/bin/env python3
"""
LLM Extract cho Lĩnh vực: GIÁO DỤC & ĐÀO TẠO

THUẦN LLM - Không dùng Regex

Nguồn dữ liệu:
  - Bảng: important_posts
  - Filter: type_newspaper = 'education'
  - Số lượng: ~22 posts

Bảng đích (2 bảng):
  1. highschool_graduation_detail  - Tốt nghiệp THPT/tỷ lệ đỗ tốt nghiệp
  2. eqi_detail                    - Chỉ số chất lượng giáo dục (EQI)
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.database import SessionLocal

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('call_llm/education_extraction.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:7777")
LLM_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "20"))
DELAY_BETWEEN_CALLS = 2  # seconds


def save_to_highschool_graduation(db, data: Dict) -> bool:
    """Save to highschool_graduation_detail"""
    try:
        insert_query = text("""
            INSERT INTO highschool_graduation_detail (
                province, year, quarter, month,
                graduation_rate, total_candidates, passed_candidates,
                average_score, math_avg_score, literature_avg_score, english_avg_score,
                excellent_rate, fail_rate,
                data_status, data_source
            ) VALUES (
                :province, :year, :quarter, :month,
                :graduation_rate, :total_candidates, :passed_candidates,
                :average_score, :math_avg_score, :literature_avg_score, :english_avg_score,
                :excellent_rate, :fail_rate,
                :data_status, :data_source
            )
        """)
        db.execute(insert_query, data)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi save highschool_graduation: {e}")
        db.rollback()
        return False


def save_to_eqi_detail(db, data: Dict) -> bool:
    """Save to eqi_detail"""
    try:
        insert_query = text("""
            INSERT INTO eqi_detail (
                province, year, quarter, month,
                eqi_score, literacy_rate, school_enrollment_rate,
                primary_completion_rate, secondary_completion_rate,
                teacher_qualification_rate, student_teacher_ratio,
                learning_outcome_score, education_spending_per_student,
                data_status, data_source, notes
            ) VALUES (
                :province, :year, :quarter, :month,
                :eqi_score, :literacy_rate, :school_enrollment_rate,
                :primary_completion_rate, :secondary_completion_rate,
                :teacher_qualification_rate, :student_teacher_ratio,
                :learning_outcome_score, :education_spending_per_student,
                :data_status, :data_source, :notes
            )
        """)
        db.execute(insert_query, data)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi save eqi_detail: {e}")
        db.rollback()
        return False
DELAY_BETWEEN_CALLS = float(os.getenv("DELAY_BETWEEN_CALLS", "1"))


def call_llm(prompt: str, max_retries: int = 3) -> Optional[str]:
    """Call OpenRouter LLM API"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": API_BASE_URL,
        "X-Title": "Education Data Extractor"
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
    """Lấy important_posts có type_newspaper = 'education'"""
    try:
        session = SessionLocal()
        
        query = text("""
            SELECT id, title, content, url, dvhc, published_date
            FROM important_posts
            WHERE type_newspaper = 'education'
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
                "dvhc": row[4],
                "published_date": row[5]
            })
        
        session.close()
        logger.info(f"Tìm thấy {len(posts)} posts (type_newspaper=education)")
        return posts
        
    except Exception as e:
        logger.error(f"Lỗi khi lấy posts từ DB: {e}")
        return []


def extract_highschool_graduation(content: str, url: str, province: str) -> Optional[Dict]:
    """Extract tốt nghiệp THPT → highschool_graduation_detail"""
    prompt = f"""Phân tích văn bản sau và trả về JSON theo đúng cấu trúc.
Chỉ sử dụng thông tin có trong văn bản, không suy diễn.

Schema:
{{
  "year": null,
  "quarter": null,
  "month": null,
  "graduation_rate": null,
  "total_candidates": null,
  "passed_candidates": null,
  "average_score": null,
  "math_avg_score": null,
  "literature_avg_score": null,
  "english_avg_score": null,
  "excellent_rate": null,
  "fail_rate": null
}}

Giải thích các trường:
- year (integer): Năm thi tốt nghiệp
- quarter (integer): Quý
- month (integer): Tháng
- graduation_rate (float): Tỷ lệ tốt nghiệp (%, 0-100)
- total_candidates (integer): Tổng số thí sinh dự thi
- passed_candidates (integer): Số thí sinh đỗ tốt nghiệp
- average_score (float): Điểm trung bình chung (0-10)
- math_avg_score (float): Điểm trung bình môn Toán (0-10)
- literature_avg_score (float): Điểm trung bình môn Văn (0-10)
- english_avg_score (float): Điểm trung bình môn Anh (0-10)
- excellent_rate (float): Tỷ lệ học sinh xuất sắc (%, 0-100)
- fail_rate (float): Tỷ lệ không đạt (%, 0-100)

Quy tắc:
1. QUAN TRỌNG: CHỈ extract nếu văn bản RÕ RÀNG nói về Hưng Yên (hoặc huyện/thành phố thuộc Hưng Yên)
2. Nếu văn bản nói về toàn quốc, tỉnh khác, hoặc không rõ địa phương → trả về: {{"no_data": true}}
3. CHỈ trích xuất số liệu CÓ TRONG văn bản về Hưng Yên
4. Nếu văn bản KHÔNG đề cập tốt nghiệp THPT của Hưng Yên, trả về: {{"no_data": true}}
5. Tỷ lệ % chuyển sang số thập phân
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
        logger.error(f"Lỗi extract highschool_graduation: {e}")
        return None


def extract_eqi_detail(content: str, url: str, province: str) -> Optional[Dict]:
    """Extract chỉ số chất lượng giáo dục → eqi_detail"""
    prompt = f"""Phân tích văn bản sau và trích xuất các chỉ số về CHẤT LƯỢNG GIÁO DỤC.

Trả về JSON theo cấu trúc:
{{
  "year": null,
  "quarter": null,
  "month": null,
  "eqi_score": null,
  "literacy_rate": null,
  "school_enrollment_rate": null,
  "primary_completion_rate": null,
  "secondary_completion_rate": null,
  "teacher_qualification_rate": null,
  "student_teacher_ratio": null,
  "learning_outcome_score": null,
  "education_spending_per_student": null,
  "notes": null
}}

Giải thích các trường:
- year, quarter, month: Thời gian số liệu
- eqi_score: Điểm EQI hoặc điểm đánh giá chất lượng giáo dục tổng hợp (0-100)
- literacy_rate: Tỷ lệ biết chữ (%)
- school_enrollment_rate: Tỷ lệ nhập học/đi học (%)
- primary_completion_rate: Tỷ lệ hoàn thành tiểu học (%)
- secondary_completion_rate: Tỷ lệ hoàn thành THCS (%)
- teacher_qualification_rate: Tỷ lệ giáo viên đạt chuẩn/có bằng cấp phù hợp (%)
- student_teacher_ratio: Tỷ lệ học sinh/giáo viên (ví dụ: 25 HS/1 GV → ghi 25)
- learning_outcome_score: Điểm kết quả học tập/thành tích học tập (0-100)
- education_spending_per_student: Chi phí giáo dục/học sinh (triệu đồng/năm)
- notes: Ghi chú các chỉ số khác về chất lượng giáo dục (cơ sở vật chất, đạt chuẩn quốc gia, xếp loại trường...)

QUY TẮC QUAN TRỌNG:
1. CHỈ extract nếu văn bản nói về Hưng Yên (hoặc huyện/thành phố/trường học thuộc Hưng Yên)
2. Nếu toàn quốc/tỉnh khác → trả về: {{"no_data": true}}
3. ⭐ LINH HOẠT TỐI ĐA: 
   - Extract BẤT KỲ chỉ số nào về CHẤT LƯỢNG giáo dục (tỷ lệ, số lượng, %)
   - Nếu văn bản đề cập CÁC CHỈ SỐ về giáo dục Hưng Yên → BẮT BUỘC phải extract
   - Nếu không có field phù hợp → ghi chi tiết vào notes
4. Các chỉ số thường gặp (extract NẾU CÓ):
   - Tỷ lệ/số trường đạt chuẩn quốc gia → notes hoặc literacy_rate
   - Tỷ lệ học sinh tốt nghiệp/đỗ tốt nghiệp → secondary_completion_rate
   - Tỷ lệ GV đạt chuẩn/trên chuẩn → teacher_qualification_rate
   - Tỷ lệ phòng học kiên cố → notes
   - Thành tích học sinh giỏi → learning_outcome_score hoặc notes
   - Số học sinh/lớp, HS/GV → student_teacher_ratio
   - Tỷ lệ có việc làm sau tốt nghiệp → notes
   - Quy mô (số HS, số trường, số GV) → notes
5. Thời gian:
   - "Quý I/II/III/IV" → quarter=1/2/3/4
   - "6 tháng đầu năm" / "nửa đầu năm" → quarter=2
   - "9 tháng đầu năm" → quarter=3
   - "Năm 2024" / "năm học 2024-2025" → year=2024
6. CẤM trả về {{"no_data": true}} nếu văn bản CÓ BẤT KỲ CHỈ SỐ NÀO về chất lượng GD Hưng Yên

Văn bản:
\"\"\"
{content[:3500]}
\"\"\"

CHỈ trả về JSON, không giải thích."""

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
        logger.error(f"Lỗi extract eqi_detail: {e}")
        return None


def process_post(post: Dict, db) -> Dict[str, int]:
    """Xử lý 1 post - Extract 2 loại thống kê giáo dục"""
    post_id = post.get("id")
    content = post.get("content", "")
    title = post.get("title", "")
    province = post.get("province", "Unknown")
    url = post.get("url", f"Post {post_id}")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Post ID: {post_id}")
    logger.info(f"Title: {title[:100]}")
    
    results = {
        "highschool_graduation": 0,
        "eqi_detail": 0
    }
    
    # 1. Highschool Graduation
    hs_grad = extract_highschool_graduation(content, url, province)
    if hs_grad:
        if save_to_highschool_graduation(db, hs_grad):
            logger.info(f"Saved to highschool_graduation_detail")
            results["highschool_graduation"] = 1
        else:
            logger.error(f"Failed to save highschool_graduation")
    
    time.sleep(DELAY_BETWEEN_CALLS)
    
    # 2. EQI Detail
    eqi = extract_eqi_detail(content, url, province)
    if eqi:
        if save_to_eqi_detail(db, eqi):
            logger.info(f"Saved to eqi_detail")
            results["eqi_detail"] = 1
        else:
            logger.error(f"Failed to save eqi_detail")
    
    time.sleep(DELAY_BETWEEN_CALLS)
    return results


def main():
    """Main function"""
    logger.info("="*80)
    logger.info("BẮT ĐẦU LLM EXTRACTION - LĨNH VỰC: GIÁO DỤC")
    logger.info(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80)
    
    db = SessionLocal()
    try:
        posts = get_posts_from_db(limit=BATCH_SIZE)
        
        if not posts:
            return {
                "status": "no_data",
                "message": "Không có posts nào (type_newspaper=education)",
                "processed": 0
            }
        
        total_extracted = {
            "highschool_graduation": 0,
            "eqi_detail": 0
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
        logger.info(f"Highschool Graduation: {total_extracted['highschool_graduation']}")
        logger.info(f"EQI Detail: {total_extracted['eqi_detail']}")
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
