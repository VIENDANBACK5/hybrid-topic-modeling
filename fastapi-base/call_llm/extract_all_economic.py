#!/usr/bin/env python3
"""
LLM Extract TẤT CẢ CHỈ SỐ KINH TẾ - FILL 4 BẢNG CÙNG LÚC

Extract và lưu vào 4 bảng:
  1. digital_economy_detail - Kinh tế số
  2. fdi_detail - Thu hút FDI
  3. digital_transformation_detail - Chuyển đổi số
  4. pii_detail - Chỉ số sản xuất công nghiệp

Nguồn: important_posts với type_newspaper='economy'
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
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
        logging.FileHandler('call_llm/all_economic_extraction.log'),
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

if not LLM_API_KEY:
    logger.error("Không tìm thấy OPENROUTER_API_KEY hoặc OPENAI_API_KEY")
    sys.exit(1)

# Keywords cho từng loại (data từ Google search về Hưng Yên)
KEYWORDS = {
    'digital_economy': ['kinh tế số', 'thương mại điện tử', 'fintech', 'startup', 'doanh nghiệp số', 'nền kinh tế số'],
    'fdi': ['fdi', 'đầu tư trực tiếp', 'vốn đầu tư nước ngoài', 'dự án fdi', 'thu hút đầu tư', 'thu hút fdi'],
    'digital_transformation': ['chuyển đổi số', 'chính quyền điện tử', 'dịch vụ công', 'chỉ số dx', 'dx index', 'egov'],
    'pii': ['pii', 'sản xuất công nghiệp', 'chỉ số iip', 'iip', 'công nghiệp', 'chế biến chế tạo', 'sản lượng']
}


def call_llm(prompt: str, max_retries: int = 3) -> Optional[str]:
    """Call OpenRouter LLM API"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": API_BASE_URL,
        "X-Title": "Economic Data Extractor"
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


def classify_post(content: str, title: str) -> List[str]:
    """Phân loại post thuộc loại nào (có thể nhiều loại)"""
    text = (title + " " + content).lower()
    categories = []
    
    for category, keywords in KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            categories.append(category)
    
    return categories


def save_to_digital_economy(db, data: Dict) -> bool:
    """Save to digital_economy_detail"""
    try:
        # Build period_type
        if data.get('month'):
            data['period_type'] = 'month'
        elif data.get('quarter'):
            data['period_type'] = 'quarter'
        else:
            data['period_type'] = 'year'
        
        # Only use fields that exist in migration schema
        required_fields = [
            'province', 'period_type', 'year', 'quarter', 'month',
            'digital_economy_gdp', 'digital_economy_gdp_share', 'digital_economy_growth_rate',
            'ecommerce_revenue', 'ecommerce_users', 'ecommerce_transactions',
            'digital_payment_volume', 'digital_payment_transactions', 'digital_wallet_users', 'cashless_payment_rate',
            'digital_companies', 'tech_startups',
            'fintech_revenue',
            'internet_penetration',
            'digital_service_exports',
            'digital_workforce',
            'data_source'
        ]
        for field in required_fields:
            if field not in data:
                data[field] = None
        
        insert_query = text("""
            INSERT INTO digital_economy_detail (
                province, period_type, year, quarter, month,
                digital_economy_gdp, digital_economy_gdp_share, digital_economy_growth_rate,
                ecommerce_revenue, ecommerce_users, ecommerce_transactions,
                digital_payment_volume, digital_payment_transactions, digital_wallet_users, cashless_payment_rate,
                digital_companies, tech_startups,
                fintech_revenue,
                internet_penetration,
                digital_service_exports,
                digital_workforce,
                data_source
            ) VALUES (
                :province, :period_type, :year, :quarter, :month,
                :digital_economy_gdp, :digital_economy_gdp_share, :digital_economy_growth_rate,
                :ecommerce_revenue, :ecommerce_users, :ecommerce_transactions,
                :digital_payment_volume, :digital_payment_transactions, :digital_wallet_users, :cashless_payment_rate,
                :digital_companies, :tech_startups,
                :fintech_revenue,
                :internet_penetration,
                :digital_service_exports,
                :digital_workforce,
                :data_source
            )
        """)
        db.execute(insert_query, data)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi save digital_economy: {e}")
        db.rollback()
        return False


def save_to_fdi(db, data: Dict) -> bool:
    """Save to fdi_detail"""
    try:
        # Build period_type
        if data.get('month'):
            data['period_type'] = 'month'
        elif data.get('quarter'):
            data['period_type'] = 'quarter'
        else:
            data['period_type'] = 'year'
        
        # Match migration schema EXACTLY (lines 94-110)
        required_fields = [
            'province', 'period_type', 'year', 'quarter', 'month',
            'registered_capital', 'new_projects_capital', 'additional_capital',
            'disbursed_capital', 'disbursement_rate',
            'total_projects', 'new_projects', 'adjusted_projects',
            'manufacturing_fdi', 'realestate_fdi', 'technology_fdi',
            'japan_fdi', 'korea_fdi', 'singapore_fdi',
            'fdi_contribution_grdp', 'fdi_export_value', 'fdi_employment',
            'data_source'
        ]
        for field in required_fields:
            if field not in data:
                data[field] = None
        
        insert_query = text("""
            INSERT INTO fdi_detail (
                province, period_type, year, quarter, month,
                registered_capital, new_projects_capital, additional_capital,
                disbursed_capital, disbursement_rate,
                total_projects, new_projects, adjusted_projects,
                manufacturing_fdi, realestate_fdi, technology_fdi,
                japan_fdi, korea_fdi, singapore_fdi,
                fdi_contribution_grdp, fdi_export_value, fdi_employment,
                data_source
            ) VALUES (
                :province, :period_type, :year, :quarter, :month,
                :registered_capital, :new_projects_capital, :additional_capital,
                :disbursed_capital, :disbursement_rate,
                :total_projects, :new_projects, :adjusted_projects,
                :manufacturing_fdi, :realestate_fdi, :technology_fdi,
                :japan_fdi, :korea_fdi, :singapore_fdi,
                :fdi_contribution_grdp, :fdi_export_value, :fdi_employment,
                :data_source
            )
        """)
        db.execute(insert_query, data)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi save fdi: {e}")
        db.rollback()
        return False


def save_to_digital_transformation(db, data: Dict) -> bool:
    """Save to digital_transformation_detail"""
    try:
        # Build period_type
        if data.get('month'):
            data['period_type'] = 'month'
        elif data.get('quarter'):
            data['period_type'] = 'quarter'
        else:
            data['period_type'] = 'year'
        
        # Match migration schema EXACTLY (lines 142-159)
        required_fields = [
            'province', 'period_type', 'year', 'quarter', 'month',
            'dx_index', 'dx_readiness_index', 'egov_index',
            'online_public_services', 'level3_services', 'level4_services', 'online_service_usage_rate',
            'cloud_adoption_rate', 'broadband_coverage', 'fiveg_coverage',
            'sme_dx_adoption', 'companies_using_ai', 'companies_using_iot',
            'digital_literacy_rate',
            'ai_projects', 'iot_projects',
            'dx_investment', 'productivity_increase_from_dx',
            'data_source'
        ]
        for field in required_fields:
            if field not in data:
                data[field] = None
        
        insert_query = text("""
            INSERT INTO digital_transformation_detail (
                province, period_type, year, quarter, month,
                dx_index, dx_readiness_index, egov_index,
                online_public_services, level3_services, level4_services, online_service_usage_rate,
                cloud_adoption_rate, broadband_coverage, fiveg_coverage,
                sme_dx_adoption, companies_using_ai, companies_using_iot,
                digital_literacy_rate,
                ai_projects, iot_projects,
                dx_investment, productivity_increase_from_dx,
                data_source
            ) VALUES (
                :province, :period_type, :year, :quarter, :month,
                :dx_index, :dx_readiness_index, :egov_index,
                :online_public_services, :level3_services, :level4_services, :online_service_usage_rate,
                :cloud_adoption_rate, :broadband_coverage, :fiveg_coverage,
                :sme_dx_adoption, :companies_using_ai, :companies_using_iot,
                :digital_literacy_rate,
                :ai_projects, :iot_projects,
                :dx_investment, :productivity_increase_from_dx,
                :data_source
            )
        """)
        db.execute(insert_query, data)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi save digital_transformation: {e}")
        db.rollback()
        return False


def save_to_pii(db, data: Dict) -> bool:
    """Save to pii_detail"""
    try:
        # Build period_type
        if data.get('month'):
            data['period_type'] = 'month'
        elif data.get('quarter'):
            data['period_type'] = 'quarter'
        else:
            data['period_type'] = 'year'
        
        # Match migration schema EXACTLY (lines 191-208)
        required_fields = [
            'province', 'period_type', 'year', 'quarter', 'month',
            'pii_overall', 'pii_growth_rate', 'industrial_output_value',
            'mining_index', 'manufacturing_index', 'electricity_index',
            'food_processing_index', 'textile_index', 'electronics_index',
            'state_owned_pii', 'private_pii', 'fdi_pii',
            'manufacturing_share', 'hightech_industry_share',
            'labor_productivity', 'capacity_utilization',
            'industrial_enterprises', 'industrial_workers',
            'data_source'
        ]
        for field in required_fields:
            if field not in data:
                data[field] = None
        
        insert_query = text("""
            INSERT INTO pii_detail (
                province, period_type, year, quarter, month,
                pii_overall, pii_growth_rate, industrial_output_value,
                mining_index, manufacturing_index, electricity_index,
                food_processing_index, textile_index, electronics_index,
                state_owned_pii, private_pii, fdi_pii,
                manufacturing_share, hightech_industry_share,
                labor_productivity, capacity_utilization,
                industrial_enterprises, industrial_workers,
                data_source
            ) VALUES (
                :province, :period_type, :year, :quarter, :month,
                :pii_overall, :pii_growth_rate, :industrial_output_value,
                :mining_index, :manufacturing_index, :electricity_index,
                :food_processing_index, :textile_index, :electronics_index,
                :state_owned_pii, :private_pii, :fdi_pii,
                :manufacturing_share, :hightech_industry_share,
                :labor_productivity, :capacity_utilization,
                :industrial_enterprises, :industrial_workers,
                :data_source
            )
        """)
        db.execute(insert_query, data)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Lỗi save pii: {e}")
        db.rollback()
        return False


def extract_digital_economy(post: Dict, db) -> int:
    """Extract digital economy data"""
    prompt = f"""
Bạn là chuyên gia phân tích dữ liệu. NHIỆM VỤ: Trích xuất CHỈ SỐ KINH TẾ SỐ từ bài viết.

TIÊU ĐỀ: {post['title']}
NỘI DUNG: {post['content'][:3000]}

⚠️ QUY TẮC BẮT BUỘC:
1. CHỈ trích xuất số liệu ĐƯỢC NÊU RÕ RÀNG trong bài
2. TUYỆT ĐỐI KHÔNG tự suy luận, ước tính, hoặc sinh ra số liệu
3. Nếu bài KHÔNG có số liệu cụ thể về kinh tế số → trả {{"skip": true}}
4. Nếu thiếu thông tin → để null, KHÔNG đoán

Các trường cần extract (CHỈ khi có trong bài):
- year, quarter, month: Kỳ báo cáo (BẮT BUỘC phải có rõ ràng)
- digital_economy_gdp_share: % kinh tế số/GRDP (VD: "chiếm 20%")
- digital_economy_growth_rate: Tăng trưởng % (VD: "tăng 15%")
- ecommerce_revenue: Doanh thu TMĐT tỷ VNĐ (VD: "25.000 tỷ đồng")
- digital_companies: Số DN công nghệ số (VD: "500 doanh nghiệp")

VÍ DỤ ĐÚNG:
Bài: "Năm 2025, kinh tế số chiếm 20% GRDP, tăng 500 DN"
→ {{"year": 2025, "digital_economy_gdp_share": 20, "digital_companies": 500}}

VÍ DỤ SAI:
Bài: "Hưng Yên phát triển kinh tế số" (không có số liệu)
→ {{"skip": true}}

Trả về JSON (CHỈ JSON):
"""
    
    try:
        llm_response = call_llm(prompt)
        if not llm_response:
            return 0
        
        # Parse JSON
        json_start = llm_response.find('{')
        json_end = llm_response.rfind('}') + 1
        if json_start == -1 or json_end == 0:
            return 0
        
        data = json.loads(llm_response[json_start:json_end])
        
        if data.get('skip'):
            return 0
        
        # Add metadata (bỏ source_post_id và source_url vì DB không có cột này)
        data['province'] = post.get('province') or 'Hưng Yên'
        data['data_source'] = post.get('url') or 'LLM Extraction'
        
        if save_to_digital_economy(db, data):
            logger.info(f"Digital Economy: {data.get('year')} - {data.get('digital_economy_gdp_share')}%")
            return 1
        return 0
        
    except Exception as e:
        logger.error(f"Extract digital_economy error: {e}")
        return 0


def extract_fdi(post: Dict, db) -> int:
    """Extract FDI data"""
    prompt = f"""
Bạn là chuyên gia phân tích dữ liệu. NHIỆM VỤ: Trích xuất CHỈ SỐ FDI từ bài viết.

TIÊU ĐỀ: {post['title']}
NỘI DUNG: {post['content'][:3000]}

⚠️ QUY TẮC NGHIÊM NGẶT - KHÔNG ĐƯỢC VI PHẠM:
1. CHỈ extract số ĐƯỢC VIẾT RÕ RÀNG trong bài (VD: "1.600 triệu USD", "26 dự án")
2. TUYỆT ĐỐI KHÔNG ước tính, suy luận, hoặc tự sinh số
3. Nếu bài KHÔNG CÓ số liệu FDI cụ thể → {{"skip": true}}
4. Nếu thiếu field → để null

Các trường extract (CHỈ khi BÀI NÓI RÕ):
- year, quarter: Kỳ báo cáo (BẮT BUỘC)
- registered_capital: Vốn đăng ký (triệu USD)
- disbursed_capital: Vốn giải ngân (triệu USD) 
- total_projects: Tổng dự án (số nguyên)
- new_projects: Dự án mới (số nguyên)
- japan_fdi, korea_fdi, singapore_fdi: Vốn từ quốc gia (triệu USD)
- manufacturing_fdi: FDI sản xuất (triệu USD)

VÍ DỤ ĐÚNG:
Bài: "2025 thu hút 1.612,81 triệu USD FDI, 26 dự án mới"
→ {{"year": 2025, "registered_capital": 1612.81, "new_projects": 26}}

VÍ DỤ SAI - KHÔNG LÀM:
Bài: "FDI tăng mạnh" (không có số) → {{"skip": true}}

Trả về JSON:
"""
    
    try:
        llm_response = call_llm(prompt)
        if not llm_response:
            return 0
        
        json_start = llm_response.find('{')
        json_end = llm_response.rfind('}') + 1
        if json_start == -1 or json_end == 0:
            return 0
        
        data = json.loads(llm_response[json_start:json_end])
        
        if data.get('skip'):
            return 0
        
        # Add metadata (bỏ source_post_id và source_url vì DB không có cột này)
        data['province'] = post.get('province') or 'Hưng Yên'
        data['data_source'] = post.get('url') or 'LLM Extraction'
        
        if save_to_fdi(db, data):
            logger.info(f"FDI: {data.get('year')} - {data.get('registered_capital')} triệu USD")
            return 1
        return 0
        
    except Exception as e:
        logger.error(f"Extract FDI error: {e}")
        return 0


def extract_digital_transformation(post: Dict, db) -> int:
    """Extract digital transformation data"""
    prompt = f"""
Bạn là chuyên gia phân tích dữ liệu. NHIỆM VỤ: Extract CHỈ SỐ CHUYỂN ĐỔI SỐ.

TIÊU ĐỀ: {post['title']}
NỘI DUNG: {post['content'][:3000]}

⚠️ QUY TẮC NGHIÊM NGẶT:
1. CHỈ extract số ĐƯỢC VIẾT TRONG BÀI (VD: "chỉ số 58.41", "125 dịch vụ")
2. KHÔNG tự tính toán, suy luận, hoặc ước đoán
3. Nếu bài KHÔNG CÓ số liệu CĐS → {{"skip": true}}
4. Thiếu field → null

Các trường extract (CHỈ khi BÀI GHI RÕ):
- year: Năm (BẮT BUỘC)
- dx_index: Chỉ số CĐS (0-100 điểm)
- egov_index: Chỉ số chính quyền điện tử (0-100)
- level3_services, level4_services: Số dịch vụ công (số nguyên)
- online_service_usage_rate: Tỷ lệ sử dụng (%)
- sme_dx_adoption: Tỷ lệ SME CĐS (%)
- ai_projects, iot_projects: Số dự án (số nguyên)

VÍ DỤ ĐÚNG:
Bài: "2025, chỉ số CĐS đạt 58.41 điểm, 125 dịch vụ mức 4"
→ {{"year": 2025, "dx_index": 58.41, "level4_services": 125}}

VÍ DỤ SAI:
Bài: "Hưng Yên đẩy mạnh CĐS" (không có số) → {{"skip": true}}

Trả về JSON:
"""
    
    try:
        llm_response = call_llm(prompt)
        if not llm_response:
            return 0
        
        json_start = llm_response.find('{')
        json_end = llm_response.rfind('}') + 1
        if json_start == -1 or json_end == 0:
            return 0
        
        data = json.loads(llm_response[json_start:json_end])
        
        if data.get('skip'):
            return 0
        
        # Add metadata (bỏ source_post_id và source_url vì DB không có cột này)
        data['province'] = post.get('province') or 'Hưng Yên'
        data['data_source'] = post.get('url') or 'LLM Extraction'
        
        if save_to_digital_transformation(db, data):
            logger.info(f"DX: {data.get('year')} - Index {data.get('dx_index')}")
            return 1
        return 0
        
    except Exception as e:
        logger.error(f"Extract DX error: {e}")
        return 0


def extract_pii(post: Dict, db) -> int:
    """Extract PII (Industrial Production Index) data"""
    prompt = f"""
Bạn là chuyên gia phân tích dữ liệu. NHIỆM VỤ: Extract CHỈ SỐ SẢN XUẤT CÔNG NGHIỆP (IIP/PII).

TIÊU ĐỀ: {post['title']}
NỘI DUNG: {post['content'][:3000]}

⚠️ QUY TẮC BẮT BUỘC:
1. CHỈ extract số ĐƯỢC GHI TRONG BÀI (VD: "tăng 11.51%", "chỉ số 120.5")
2. TUYỆT ĐỐI KHÔNG tự tính, ước lượng số liệu
3. Nếu bài KHÔNG CÓ số IIP/PII cụ thể → {{"skip": true}}
4. Thiếu số → null

Các trường extract (CHỈ khi BÀI VIẾT RÕ):
- year, quarter, month: Kỳ báo cáo (BẮT BUỘC có ít nhất year)
- pii_growth_rate: % tăng trưởng IIP (VD: "tăng 11.51%")
- pii_overall: Chỉ số IIP tổng (base 100)
- industrial_output_value: Giá trị sản xuất (tỷ VNĐ)
- manufacturing_index: Chỉ số chế biến (%)
- mining_index, electricity_index: Chỉ số ngành (%)

VÍ DỤ ĐÚNG:
Bài: "Quý 3/2025, IIP tăng 11.51% so cùng kỳ"
→ {{"year": 2025, "quarter": 3, "pii_growth_rate": 11.51}}

VÍ DỤ SAI:
Bài: "Công nghiệp phát triển tốt" (không có số) → {{"skip": true}}

Trả về JSON:
"""
    
    try:
        llm_response = call_llm(prompt)
        if not llm_response:
            return 0
        
        json_start = llm_response.find('{')
        json_end = llm_response.rfind('}') + 1
        if json_start == -1 or json_end == 0:
            return 0
        
        data = json.loads(llm_response[json_start:json_end])
        
        if data.get('skip'):
            return 0
        
        # Add metadata (bỏ source_post_id và source_url vì DB không có cột này)
        data['province'] = post.get('province') or 'Hưng Yên'
        data['data_source'] = post.get('url') or 'LLM Extraction'
        
        if save_to_pii(db, data):
            logger.info(f"PII: {data.get('year')} - Growth {data.get('pii_growth_rate')}%")
            return 1
        return 0
        
    except Exception as e:
        logger.error(f"Extract PII error: {e}")
        return 0


def get_posts_from_db(limit: int = 100) -> List[Dict]:
    """Lấy important_posts có type_newspaper = 'economy'"""
    try:
        db = SessionLocal()
        query = text("""
            SELECT id, title, content, url, dvhc as province, published_date
            FROM important_posts
            WHERE type_newspaper = 'economy'
            ORDER BY id DESC
            LIMIT :limit
        """)
        
        result = db.execute(query, {"limit": limit})
        posts = []
        for row in result:
            posts.append({
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'url': row[3],
                'province': row[4],
                'published_date': row[5]
            })
        
        db.close()
        logger.info(f"Lấy được {len(posts)} posts economy")
        return posts
    except Exception as e:
        logger.error(f"Lỗi lấy posts: {e}")
        return []


def process_post(post: Dict, db) -> Dict[str, int]:
    """Process 1 post - extract tất cả categories phù hợp"""
    logger.info(f"\nPost {post['id']}: {post['title'][:80]}...")
    
    # Classify post
    categories = classify_post(post['content'], post['title'])
    
    if not categories:
        logger.info(f"Không match category nào")
        return {'digital_economy': 0, 'fdi': 0, 'digital_transformation': 0, 'pii': 0}
    
    logger.info(f"Categories: {', '.join(categories)}")
    
    results = {
        'digital_economy': 0,
        'fdi': 0,
        'digital_transformation': 0,
        'pii': 0
    }
    
    # Extract theo từng category
    if 'digital_economy' in categories:
        results['digital_economy'] = extract_digital_economy(post, db)
        time.sleep(DELAY_BETWEEN_CALLS)
    
    if 'fdi' in categories:
        results['fdi'] = extract_fdi(post, db)
        time.sleep(DELAY_BETWEEN_CALLS)
    
    if 'digital_transformation' in categories:
        results['digital_transformation'] = extract_digital_transformation(post, db)
        time.sleep(DELAY_BETWEEN_CALLS)
    
    if 'pii' in categories:
        results['pii'] = extract_pii(post, db)
        time.sleep(DELAY_BETWEEN_CALLS)
    
    return results


def main():
    """Main function"""
    logger.info("="*80)
    logger.info("BẮT ĐẦU LLM EXTRACTION - TẤT CẢ CHỈ SỐ KINH TẾ (4 BẢNG)")
    logger.info(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80)
    
    db = SessionLocal()
    try:
        # CHỈ phân tích 22 posts mới nhất
        posts = get_posts_from_db(limit=22)
        
        if not posts:
            return {
                "status": "no_data",
                "message": "Không có posts economy",
                "processed": 0
            }
        
        stats = {
            'digital_economy': 0,
            'fdi': 0,
            'digital_transformation': 0,
            'pii': 0
        }
        
        for i, post in enumerate(posts, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Progress: {i}/{len(posts)}")
            try:
                results = process_post(post, db)
                for key in stats:
                    stats[key] += results[key]
            except Exception as e:
                logger.error(f"Lỗi process post {post['id']}: {e}")
        
        logger.info("\n" + "="*80)
        logger.info(f"Đã xử lý: {len(posts)} posts")
        logger.info(f"Extracted:")
        logger.info(f"   - Digital Economy: {stats['digital_economy']} records")
        logger.info(f"   - FDI: {stats['fdi']} records")
        logger.info(f"   - Digital Transformation: {stats['digital_transformation']} records")
        logger.info(f"   - PII: {stats['pii']} records")
        logger.info(f"   - TỔNG: {sum(stats.values())} records")
        logger.info("="*80)
        
        return {
            "status": "success",
            "processed": len(posts),
            "extracted": stats
        }
    finally:
        db.close()


if __name__ == "__main__":
    main()
