#!/usr/bin/env python3
"""
Hệ thống AI tự động đọc từng bài trong important_posts và extract statistics
Chạy tự động, không cần can thiệp thủ công
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_extract_statistics.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:7777")
LLM_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "10"))  # Số bài xử lý mỗi lần
DELAY_BETWEEN_CALLS = float(os.getenv("DELAY_BETWEEN_CALLS", "1"))  # seconds

if not LLM_API_KEY:
    logger.error("Không tìm thấy OPENROUTER_API_KEY hoặc OPENAI_API_KEY trong environment")
    sys.exit(1)


def call_llm(prompt: str, max_retries: int = 3) -> Optional[str]:
    """Call OpenRouter LLM API with retry logic"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:7777",
        "X-Title": "Economic Statistics Extractor"
    }
    
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.1,
        "max_tokens": 2000
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
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                logger.error(f"LLM call failed after {max_retries} attempts")
                return None


def get_unprocessed_posts() -> List[Dict]:
    """Lấy danh sách các bài chưa được xử lý"""
    try:
        # Lấy tất cả important_posts (dùng page và page_size)
        all_posts = []
        page = 1
        while True:
            response = requests.get(
                f"{API_BASE_URL}/api/important-posts",
                params={"page": page, "page_size": 100}
            )
            response.raise_for_status()
            result = response.json()
            
            # API trả về dict với key 'items' hoặc 'data'
            if isinstance(result, dict):
                posts = result.get("items", result.get("data", []))
                all_posts.extend(posts)
                
                # Check nếu hết data
                total = result.get("total", 0)
                if len(all_posts) >= total or len(posts) == 0:
                    break
            else:
                all_posts.extend(result)
                break
            
            page += 1
        
        # Lấy danh sách post_id đã được xử lý
        processed_economic = set()
        processed_political = set()
        
        # Check economic_statistics
        econ_response = requests.get(
            f"{API_BASE_URL}/api/statistics/economic",
            params={"page": 1, "page_size": 1000}
        )
        if econ_response.status_code == 200:
            econ_data = econ_response.json()
            econ_records = econ_data if isinstance(econ_data, list) else econ_data.get("items", econ_data.get("data", []))
            for record in econ_records:
                if record.get("source_post_id"):
                    processed_economic.add(record["source_post_id"])
        
        # Check political_statistics
        pol_response = requests.get(
            f"{API_BASE_URL}/api/statistics/political",
            params={"page": 1, "page_size": 1000}
        )
        if pol_response.status_code == 200:
            pol_data = pol_response.json()
            pol_records = pol_data if isinstance(pol_data, list) else pol_data.get("items", pol_data.get("data", []))
            for record in pol_records:
                if record.get("source_post_id"):
                    processed_political.add(record["source_post_id"])
        
        # Filter chỉ lấy bài Thư Vũ và Trà Lý chưa xử lý
        TARGET_LOCATIONS = ["Thư Vũ", "Trà Lý", "Thu Vu", "Tra Ly"]
        unprocessed = []
        for post in all_posts:
            post_id = post.get("id")
            dvhc = post.get("dvhc", "")
            
            # Kiểm tra có phải Thư Vũ hoặc Trà Lý không
            is_target_location = any(loc.lower() in str(dvhc).lower() for loc in TARGET_LOCATIONS)
            
            # Bài chưa xử lý = là địa phương mục tiêu VÀ (chưa có trong cả 2 bảng HOẶC đã xóa hết)
            if is_target_location:
                if post_id not in processed_economic and post_id not in processed_political:
                    unprocessed.append(post)
        
        logger.info(f"Tổng số bài: {len(all_posts)}, Đã xử lý: {len(processed_economic | processed_political)}, Thư Vũ/Trà Lý chưa xử lý: {len(unprocessed)}")
        return unprocessed
        
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách bài: {e}")
        return []


def extract_economic_data(content: str, dvhc: str, source_url: str, post_id: int) -> Optional[Dict]:
    """Extract economic statistics từ content"""
    prompt = f"""Phân tích văn bản sau và trích xuất thông tin kinh tế (nếu có):

Văn bản: {content[:3000]}

Địa phương: {dvhc}

Trích xuất các thông tin sau (nếu không có thì để null):
- year: Năm (integer)
- period: Giai đoạn/Kỳ (string, ví dụ: "Quý I", "6 tháng đầu năm", "5 năm 2020-2025")
- total_production_value: Tổng giá trị sản xuất (float, đơn vị tỷ đồng)
- growth_rate: Tốc độ tăng trưởng (float, ví dụ: 8.5 nghĩa là 8.5%)
- total_budget_revenue: Tổng thu ngân sách (float, đơn vị tỷ đồng)
- budget_collection_efficiency: Hiệu suất thu ngân sách (float, ví dụ: 120.5 nghĩa là 120.5%)

Trả về JSON format:
{{
    "year": 2025,
    "period": "6 tháng đầu năm",
    "total_production_value": 1500.5,
    "growth_rate": 8.5,
    "total_budget_revenue": 200.0,
    "budget_collection_efficiency": 120.5
}}

Nếu văn bản KHÔNG có thông tin kinh tế, trả về: {{"no_data": true}}
Chỉ trả về JSON, không giải thích thêm."""

    try:
        result = call_llm(prompt)
        if not result:
            return None
        
        # Parse JSON từ response
        json_start = result.find("{")
        json_end = result.rfind("}") + 1
        if json_start == -1 or json_end == 0:
            logger.warning(f"Không tìm thấy JSON trong response cho post {post_id}")
            return None
        
        data = json.loads(result[json_start:json_end])
        
        # Nếu không có dữ liệu kinh tế
        if data.get("no_data"):
            logger.info(f"ℹ️  Post {post_id} không có thông tin kinh tế")
            return None
        
        # Thêm metadata
        data["dvhc"] = dvhc if dvhc else "Unknown"
        data["source_post_id"] = post_id
        data["source_url"] = source_url
        
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"Lỗi parse JSON cho post {post_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Lỗi extract economic data cho post {post_id}: {e}")
        return None


def extract_political_data(content: str, dvhc: str, source_url: str, post_id: int) -> Optional[Dict]:
    """Extract political statistics từ content"""
    prompt = f"""Phân tích văn bản sau và trích xuất thông tin chính trị/Đảng (nếu có):

Văn bản: {content[:3000]}

Địa phương: {dvhc}

Trích xuất các thông tin sau (nếu không có thì để null):
- year: Năm (integer)
- period: Giai đoạn (string)
- party_organization_count: Số tổ chức Đảng (integer)
- party_member_count: Số Đảng viên (integer)
- party_size_description: Mô tả quy mô Đảng (string)
- new_party_members: Số Đảng viên mới (integer)
- party_cells_count: Số chi bộ (integer)

Trả về JSON format:
{{
    "year": 2025,
    "period": "Quý III",
    "party_organization_count": 50,
    "party_member_count": 1500,
    "party_size_description": "Đảng bộ có 50 tổ chức...",
    "new_party_members": 70,
    "party_cells_count": 95
}}

Nếu văn bản KHÔNG có thông tin chính trị/Đảng, trả về: {{"no_data": true}}
Chỉ trả về JSON, không giải thích thêm."""

    try:
        result = call_llm(prompt)
        if not result:
            return None
        
        # Parse JSON từ response
        json_start = result.find("{")
        json_end = result.rfind("}") + 1
        if json_start == -1 or json_end == 0:
            logger.warning(f"Không tìm thấy JSON trong response cho post {post_id}")
            return None
        
        data = json.loads(result[json_start:json_end])
        
        # Nếu không có dữ liệu chính trị
        if data.get("no_data"):
            logger.info(f"ℹ️  Post {post_id} không có thông tin chính trị")
            return None
        
        # Thêm metadata
        data["dvhc"] = dvhc if dvhc else "Unknown"
        data["source_post_id"] = post_id
        data["source_url"] = source_url
        
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"Lỗi parse JSON cho post {post_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Lỗi extract political data cho post {post_id}: {e}")
        return None


def save_to_database(data: Dict, data_type: str) -> bool:
    """Lưu data vào database qua API"""
    endpoint = f"{API_BASE_URL}/api/statistics/{data_type}"
    
    try:
        response = requests.post(endpoint, json=data)
        
        if response.status_code in [200, 201]:
            logger.info(f"Đã lưu {data_type} cho post {data.get('source_post_id')}")
            return True
        elif response.status_code == 409 or "duplicate" in response.text.lower():
            logger.info(f"ℹ️  {data_type} cho post {data.get('source_post_id')} đã tồn tại (skip)")
            return True
        else:
            logger.error(f"Lỗi lưu {data_type}: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Exception khi lưu {data_type}: {e}")
        return False


def process_post(post: Dict) -> Tuple[bool, bool]:
    """
    Xử lý 1 bài post
    Returns: (economic_extracted, political_extracted)
    """
    post_id = post.get("id")
    content = post.get("content", "")
    dvhc = post.get("dvhc", "")
    source_url = post.get("source_url", "")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Đang xử lý post ID: {post_id}")
    logger.info(f"ĐVHC: {dvhc}")
    logger.info(f"Content length: {len(content)} chars")
    
    economic_saved = False
    political_saved = False
    
    # Extract economic data
    logger.info("💰 Đang extract economic data...")
    economic_data = extract_economic_data(content, dvhc, source_url, post_id)
    if economic_data:
        economic_saved = save_to_database(economic_data, "economic")
        time.sleep(DELAY_BETWEEN_CALLS)
    
    # Extract political data
    logger.info("🏛️  Đang extract political data...")
    political_data = extract_political_data(content, dvhc, source_url, post_id)
    if political_data:
        political_saved = save_to_database(political_data, "political")
        time.sleep(DELAY_BETWEEN_CALLS)
    
    return economic_saved, political_saved


def main():
    """Main function - chạy auto extract"""
    logger.info("="*80)
    logger.info("BẮT ĐẦU AUTO EXTRACT STATISTICS")
    logger.info(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"LLM Model: {LLM_MODEL}")
    logger.info(f"📦 Batch size: {BATCH_SIZE}")
    logger.info("="*80)
    
    # Lấy danh sách bài chưa xử lý
    unprocessed_posts = get_unprocessed_posts()
    
    if not unprocessed_posts:
        logger.info("Không có bài nào cần xử lý. Tất cả đã được extract!")
        return
    
    # Process theo batch
    total_posts = len(unprocessed_posts)
    economic_count = 0
    political_count = 0
    error_count = 0
    
    for i, post in enumerate(unprocessed_posts[:BATCH_SIZE], 1):
        logger.info(f"\nProgress: {i}/{min(BATCH_SIZE, total_posts)}")
        
        try:
            economic_ok, political_ok = process_post(post)
            
            if economic_ok:
                economic_count += 1
            if political_ok:
                political_count += 1
            if not economic_ok and not political_ok:
                error_count += 1
                
        except Exception as e:
            logger.error(f"Lỗi khi xử lý post {post.get('id')}: {e}")
            error_count += 1
        
        # Delay giữa các bài
        if i < min(BATCH_SIZE, total_posts):
            time.sleep(DELAY_BETWEEN_CALLS)
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("KẾT QUẢ AUTO EXTRACT")
    logger.info("="*80)
    logger.info(f"Đã xử lý: {min(BATCH_SIZE, total_posts)} bài")
    logger.info(f"💰 Economic records extracted: {economic_count}")
    logger.info(f"🏛️  Political records extracted: {political_count}")
    logger.info(f"Errors: {error_count}")
    logger.info(f"📋 Còn lại chưa xử lý: {max(0, total_posts - BATCH_SIZE)} bài")
    logger.info("="*80)
    
    if total_posts > BATCH_SIZE:
        logger.info(f"\nTIP: Chạy lại script để xử lý tiếp {total_posts - BATCH_SIZE} bài còn lại")


if __name__ == "__main__":
    main()
