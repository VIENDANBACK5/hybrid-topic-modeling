#!/usr/bin/env python3
"""
DUAL-MODEL LLM Client - Kết hợp Gemini 2.5 Flash + GPT-4o-mini

Chiến lược:
- Gemini 2.5 Flash: Hiểu context, extract thông tin thô (context window lớn, nhanh)
- GPT-4o-mini: Xử lý structured output, validate & format JSON

Sử dụng cả 2 model qua OpenRouter API.
"""

import os
import json
import time
import logging
import requests
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Configuration
LLM_API_URL = os.getenv("LLM_API_URL", "https://openrouter.ai/api/v1/chat/completions")
LLM_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", "")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:7777")

# Model Configuration
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "google/gemini-2.5-flash-preview")  # Hiểu + Extract
GPT_MODEL = os.getenv("GPT_MODEL", "openai/gpt-4o-mini")  # Structured Output

# Feature flags
USE_DUAL_MODEL = os.getenv("USE_DUAL_MODEL", "true").lower() == "true"


def _call_openrouter(model: str, messages: list, temperature: float = 0.1, max_tokens: int = 3000) -> Optional[str]:
    """Internal function to call OpenRouter API"""
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": API_BASE_URL,
        "X-Title": "Dual Model Extractor"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    try:
        response = requests.post(LLM_API_URL, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"OpenRouter API error ({model}): {e}")
        return None


def call_gemini(prompt: str, max_retries: int = 3) -> Optional[str]:
    """
    Call Gemini 2.5 Flash - tốt cho:
    - Hiểu context dài (1M tokens)
    - Extract thông tin từ text
    - Phân tích nội dung tiếng Việt
    """
    messages = [{"role": "user", "content": prompt}]
    
    for attempt in range(max_retries):
        result = _call_openrouter(GEMINI_MODEL, messages, temperature=0.1)
        if result:
            return result
        logger.warning(f"Gemini attempt {attempt + 1}/{max_retries} failed")
        time.sleep(2 ** attempt)
    
    return None


def call_gpt(prompt: str, max_retries: int = 3) -> Optional[str]:
    """
    Call GPT-4o-mini - tốt cho:
    - Structured JSON output
    - Validate & format data
    - Instruction following
    """
    messages = [{"role": "user", "content": prompt}]
    
    for attempt in range(max_retries):
        result = _call_openrouter(GPT_MODEL, messages, temperature=0.1)
        if result:
            return result
        logger.warning(f"GPT attempt {attempt + 1}/{max_retries} failed")
        time.sleep(2 ** attempt)
    
    return None


def extract_with_dual_model(
    content: str,
    title: str,
    extraction_schema: Dict[str, Any],
    category: str = "general",
    province: str = "Hưng Yên",
    field_descriptions: Dict[str, str] = None
) -> Optional[Dict]:
    """
    DUAL-MODEL EXTRACTION PIPELINE
    
    Step 1: Gemini hiểu & extract thông tin thô
    Step 2: GPT validate & format JSON chuẩn
    
    Args:
        content: Nội dung bài viết
        title: Tiêu đề
        extraction_schema: Schema của dữ liệu cần extract
        category: Loại dữ liệu (economy, society, etc.)
        province: Tỉnh cần validate (mặc định Hưng Yên)
        field_descriptions: Dict mô tả từng field (optional)
    
    Returns:
        Dict với dữ liệu đã extract hoặc None
    """
    if not USE_DUAL_MODEL:
        # Fallback to single model (GPT)
        return _single_model_extract(content, title, extraction_schema, category, province, field_descriptions)
    
    # === STEP 1: Gemini hiểu & extract thô ===
    gemini_prompt = f"""Bạn là chuyên gia phân tích dữ liệu. Đọc kỹ bài viết và liệt kê TẤT CẢ các số liệu {category} được đề cập.

TIÊU ĐỀ: {title}
NỘI DUNG: {content[:8000]}

⚠️ QUY TẮC BẮT BUỘC:
1. CHỈ liệt kê số liệu ĐƯỢC NÊU RÕ RÀNG trong bài
2. TUYỆT ĐỐI KHÔNG tự suy luận, ước tính, hoặc sinh ra số liệu
3. ⚠️ QUAN TRỌNG: CHỈ extract nếu văn bản RÕ RÀNG nói về {province} (hoặc huyện/thành phố thuộc {province})
4. Nếu văn bản nói về toàn quốc, tỉnh khác, hoặc không rõ địa phương → trả lời: "KHÔNG PHẢI {province.upper()}"

Yêu cầu output:
1. Liệt kê TỪNG số liệu bạn tìm thấy (nguyên văn từ bài)
2. Ghi rõ: [Chỉ số gì] = [Giá trị] (Năm/Kỳ nào)
3. Nếu KHÔNG có số liệu cụ thể về {province}, trả lời: "KHÔNG CÓ SỐ LIỆU"

Trả lời đầy đủ:"""

    gemini_result = call_gemini(gemini_prompt)
    
    if not gemini_result:
        logger.warning("Gemini extraction failed, falling back to GPT only")
        return _single_model_extract(content, title, extraction_schema, category, province, field_descriptions)
    
    # Check if no data
    gemini_upper = gemini_result.upper()
    if "KHÔNG CÓ SỐ LIỆU" in gemini_upper or f"KHÔNG PHẢI {province.upper()}" in gemini_upper:
        logger.info(f"Gemini: No valid data for {province}")
        return None
    
    # === STEP 2: GPT format JSON chuẩn ===
    schema_str = json.dumps(extraction_schema, ensure_ascii=False, indent=2)
    
    # Build field descriptions if provided
    field_desc_text = ""
    if field_descriptions:
        field_desc_text = "\nGiải thích các trường:\n"
        for field, desc in field_descriptions.items():
            field_desc_text += f"- {field}: {desc}\n"
    
    gpt_prompt = f"""Dựa trên thông tin đã extract, format thành JSON chuẩn.

THÔNG TIN ĐÃ EXTRACT TỪ BÀI VIẾT (về {province}):
{gemini_result}

SCHEMA CẦN TUÂN THỦ:
{schema_str}
{field_desc_text}
QUY TẮC NGHIÊM NGẶT:
1. CHỈ sử dụng số liệu trong "THÔNG TIN ĐÃ EXTRACT" - KHÔNG tự sinh
2. year (integer): Năm của báo cáo - BẮT BUỘC phải có
3. Thời gian:
   - "Quý I" → quarter=1, "Quý II" → quarter=2, "Quý III" → quarter=3, "Quý IV" → quarter=4
   - "6 tháng đầu năm" / "nửa đầu năm" → quarter=2
   - "9 tháng đầu năm" → quarter=3
   - "Năm 2024" → year=2024, quarter=null, month=null
4. Tỷ lệ % chuyển sang số thập phân (95.5% → 95.5)
5. Nếu thiếu field → null
6. Nếu không có dữ liệu hợp lệ → {{"no_data": true}}

Trả về CHỈ JSON (không giải thích):"""

    gpt_result = call_gpt(gpt_prompt)
    
    if not gpt_result:
        logger.warning("GPT formatting failed")
        return None
    
    # Parse JSON
    try:
        json_start = gpt_result.find('{')
        json_end = gpt_result.rfind('}') + 1
        if json_start == -1 or json_end == 0:
            return None
        
        data = json.loads(gpt_result[json_start:json_end])
        
        if data.get('no_data') or data.get('skip'):
            return None
        
        # Add metadata
        data['province'] = province
        data['_extraction_method'] = 'dual_model'
        data['_gemini_model'] = GEMINI_MODEL
        data['_gpt_model'] = GPT_MODEL
        
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        return None


def _single_model_extract(
    content: str,
    title: str,
    extraction_schema: Dict[str, Any],
    category: str,
    province: str = "Hưng Yên",
    field_descriptions: Dict[str, str] = None
) -> Optional[Dict]:
    """Fallback: Single model extraction using GPT only"""
    schema_str = json.dumps(extraction_schema, ensure_ascii=False, indent=2)
    
    # Build field descriptions
    field_desc_text = ""
    if field_descriptions:
        field_desc_text = "\nGiải thích các trường:\n"
        for field, desc in field_descriptions.items():
            field_desc_text += f"- {field}: {desc}\n"
    
    prompt = f"""Phân tích văn bản sau và trả về JSON theo đúng cấu trúc.
Chỉ sử dụng thông tin có trong văn bản, không suy diễn.

TIÊU ĐỀ: {title}
NỘI DUNG: {content[:3000]}

SCHEMA:
{schema_str}
{field_desc_text}
QUY TẮC NGHIÊM NGẶT:
1. ⚠️ QUAN TRỌNG: CHỈ extract nếu văn bản RÕ RÀNG nói về {province} (hoặc huyện/thành phố thuộc {province})
2. Nếu văn bản nói về toàn quốc, tỉnh khác, hoặc không rõ địa phương → {{"no_data": true}}
3. CHỈ trích xuất số liệu CÓ TRONG văn bản về {province}
4. year (integer): Năm - BẮT BUỘC
5. Thời gian:
   - "Quý I" → quarter=1, "Quý II" → quarter=2, "Quý III" → quarter=3, "Quý IV" → quarter=4
   - "6 tháng đầu năm" → quarter=2
   - "9 tháng đầu năm" → quarter=3
6. Tỷ lệ % → số thập phân (95.5% → 95.5)
7. Nếu thiếu field → null
8. Không có số liệu → {{"no_data": true}}

Chỉ trả về JSON:"""
    
    result = call_gpt(prompt)
    
    if not result:
        return None
    
    try:
        json_start = result.find('{')
        json_end = result.rfind('}') + 1
        if json_start == -1 or json_end == 0:
            return None
        
        data = json.loads(result[json_start:json_end])
        
        if data.get('no_data') or data.get('skip'):
            return None
        
        data['province'] = province
        data['_extraction_method'] = 'single_model'
        data['_model'] = GPT_MODEL
        
        return data
        
    except json.JSONDecodeError:
        return None


# === COST CALCULATION ===
# Pricing từ OpenRouter (USD per 1M tokens) - Updated Jan 2025
PRICING = {
    "google/gemini-2.5-flash-preview": {"input": 0.15, "output": 0.60},
    "google/gemini-2.0-flash-001": {"input": 0.10, "output": 0.40},
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "openai/gpt-4o": {"input": 2.50, "output": 10.00},
    "openai/gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "qwen/qwen-2.5-72b-instruct": {"input": 0.35, "output": 0.40},
}


def estimate_cost(
    content_length: int,
    mode: str = "dual",
    num_articles: int = 1
) -> Dict[str, float]:
    """
    Ước tính chi phí extraction
    
    Args:
        content_length: Độ dài content (chars)
        mode: "dual" hoặc "single"
        num_articles: Số bài viết
    
    Returns:
        Dict với chi phí ước tính
    """
    # Ước tính tokens (1 token ≈ 4 chars tiếng Việt)
    input_tokens = content_length / 4
    output_tokens = 500  # Giả định output ~500 tokens
    
    gemini_price = PRICING.get(GEMINI_MODEL, {"input": 0.15, "output": 0.60})
    gpt_price = PRICING.get(GPT_MODEL, {"input": 0.15, "output": 0.60})
    
    if mode == "dual":
        # Gemini: đọc 8000 chars + output
        gemini_input = min(input_tokens, 2000)  # 8000 chars / 4
        gemini_output = 800  # Intermediate output
        
        # GPT: đọc Gemini output + schema
        gpt_input = gemini_output + 500  # Schema + gemini result
        gpt_output = output_tokens
        
        cost_gemini = (gemini_input * gemini_price["input"] + gemini_output * gemini_price["output"]) / 1_000_000
        cost_gpt = (gpt_input * gpt_price["input"] + gpt_output * gpt_price["output"]) / 1_000_000
        
        total = (cost_gemini + cost_gpt) * num_articles
        
        return {
            "mode": "dual",
            "per_article_usd": cost_gemini + cost_gpt,
            "total_usd": total,
            "total_vnd": total * 25000,
            "gemini_cost": cost_gemini,
            "gpt_cost": cost_gpt,
            "breakdown": f"Gemini: ${cost_gemini:.6f} + GPT: ${cost_gpt:.6f}"
        }
    else:
        # Single model: chỉ GPT
        gpt_input = min(input_tokens, 750)  # 3000 chars / 4
        gpt_output = output_tokens
        
        cost = (gpt_input * gpt_price["input"] + gpt_output * gpt_price["output"]) / 1_000_000
        total = cost * num_articles
        
        return {
            "mode": "single",
            "per_article_usd": cost,
            "total_usd": total,
            "total_vnd": total * 25000,
            "breakdown": f"GPT only: ${cost:.6f}"
        }


def compare_costs(content_length: int = 5000, num_articles: int = 100) -> str:
    """So sánh chi phí single vs dual model"""
    single = estimate_cost(content_length, "single", num_articles)
    dual = estimate_cost(content_length, "dual", num_articles)
    
    diff_pct = ((dual["total_usd"] - single["total_usd"]) / single["total_usd"]) * 100
    
    report = f"""
╔══════════════════════════════════════════════════════════════╗
║              SO SÁNH CHI PHÍ: SINGLE vs DUAL MODEL           ║
╠══════════════════════════════════════════════════════════════╣
║ Số bài viết: {num_articles:,} | Avg content: {content_length:,} chars                  ║
╠══════════════════════════════════════════════════════════════╣
║ SINGLE MODEL (GPT-4o-mini only)                              ║
║   - Per article: ${single['per_article_usd']:.6f}                              ║
║   - Total: ${single['total_usd']:.4f} ({single['total_vnd']:,.0f} VND)             ║
╠══════════════════════════════════════════════════════════════╣
║ DUAL MODEL (Gemini 2.5 Flash + GPT-4o-mini)                  ║
║   - Per article: ${dual['per_article_usd']:.6f}                              ║
║   - Total: ${dual['total_usd']:.4f} ({dual['total_vnd']:,.0f} VND)             ║
║   - {dual['breakdown']}                  ║
╠══════════════════════════════════════════════════════════════╣
║ CHÊNH LỆCH: Dual đắt hơn {diff_pct:.1f}%                              ║
║ Nhưng: Đọc được 8000 chars (vs 3000) + 2 bước verify          ║
╚══════════════════════════════════════════════════════════════╝
"""
    return report


# === CONVENIENCE FUNCTIONS ===

def call_llm(prompt: str, max_retries: int = 3) -> Optional[str]:
    """
    Default LLM call - uses GPT-4o-mini for backward compatibility
    Drop-in replacement for existing call_llm functions
    """
    return call_gpt(prompt, max_retries)


def get_available_models() -> Dict[str, str]:
    """Return configured models"""
    return {
        "gemini": GEMINI_MODEL,
        "gpt": GPT_MODEL,
        "dual_mode_enabled": USE_DUAL_MODEL
    }


# === TEST ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("DUAL-MODEL LLM CLIENT")
    print("=" * 60)
    print(f"Gemini Model: {GEMINI_MODEL}")
    print(f"GPT Model: {GPT_MODEL}")
    print(f"Dual Mode: {USE_DUAL_MODEL}")
    print(f"API Key: {'✓ Set' if LLM_API_KEY else '✗ Missing'}")
    print("=" * 60)
    
    # Hiển thị so sánh chi phí
    print(compare_costs(content_length=5000, num_articles=100))
    
    if LLM_API_KEY:
        # Test Gemini
        print("\nTesting Gemini...")
        gemini_test = call_gemini("Xin chào, bạn là model gì?")
        print(f"Gemini: {gemini_test[:100] if gemini_test else 'Failed'}...")
        
        # Test GPT
        print("\nTesting GPT...")
        gpt_test = call_gpt("Xin chào, bạn là model gì?")
        print(f"GPT: {gpt_test[:100] if gpt_test else 'Failed'}...")
    else:
        print("\n⚠️  API Key chưa được set. Export OPENROUTER_API_KEY để test.")
        print("   export OPENROUTER_API_KEY='sk-or-...'")

