"""
OpenAI Service for Economic Indicators
Dùng OpenAI để tìm kiếm và fill các trường dữ liệu kinh tế bị thiếu
"""
import os
import logging
from typing import Dict, Any, Optional
import json

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


def call_openai_for_economic_data(
    indicator_name: str,
    period_label: str,
    province: Optional[str] = None,
    existing_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Gọi OpenAI để lấy dữ liệu kinh tế thiếu
    
    Args:
        indicator_name: Tên chỉ số cần tìm (GRDP, IIP, CPI, etc.)
        period_label: Nhãn thời gian (Tháng 12/2025, Quý 4/2025)
        province: Tỉnh/thành (optional)
        existing_data: Dữ liệu đã có (để context)
    
    Returns:
        Dict với dữ liệu tìm được
    """
    if not OPENAI_API_KEY:
        logger.warning("⚠️ OPENAI_API_KEY not found, returning empty result")
        return {}
    
    try:
        from openai import OpenAI
        
        # Check if using OpenRouter (sk-or-v1-...)
        if OPENAI_API_KEY.startswith("sk-or-v1-"):
            client = OpenAI(
                api_key=OPENAI_API_KEY,
                base_url="https://openrouter.ai/api/v1"
            )
            model = "openai/gpt-4o-mini"  # OpenRouter format
        else:
            client = OpenAI(api_key=OPENAI_API_KEY)
            model = "gpt-4o-mini"  # Standard OpenAI format
        
        # Build context
        location = province or "Việt Nam"
        context_str = ""
        if existing_data:
            context_str = f"\n\nDữ liệu có sẵn: {json.dumps(existing_data, ensure_ascii=False, indent=2)}"
        
        # Build prompt - simplified and more specific
        prompt = f"""Bạn là chuyên gia kinh tế Việt Nam. Dựa trên xu hướng kinh tế gần đây, hãy ước tính các chỉ số kinh tế cho:

Thời gian: {period_label}
Địa phương: {location}{context_str}

Lưu ý: 
- Nếu không có dữ liệu chính xác, hãy ước tính hợp lý dựa trên xu hướng
- GDP Việt Nam 2024: 7.09%, mục tiêu 2025-2026: 8%
- IIP thường tăng 8-12% 
- CPI/lạm phát: 3-4%
- Xuất khẩu tháng: 3000-3500 triệu USD
- FDI giải ngân tháng: 1500-2000 triệu USD
- Thu ngân sách tháng: 50000-60000 tỷ VNĐ

Trả về JSON với ước tính (điền số thực tế, không để null):
{{
  "iip_growth_rate": <ước tính % tăng IIP>,
  "cpi_growth_rate": <ước tính % lạm phát>,
  "export_value": <ước tính xuất khẩu triệu USD>,
  "fdi_disbursed": <ước tính FDI triệu USD>,
  "state_budget_revenue": <ước tính thu ngân sách tỷ VNĐ>,
  "notes": "Dữ liệu ước tính dựa trên xu hướng"
}}

CHỈ trả về JSON, không giải thích."""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Bạn là chuyên gia kinh tế Việt Nam, chỉ trả về dữ liệu dạng JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        content = response.choices[0].message.content.strip()
        
        # Extract JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        result = json.loads(content)
        
        logger.info(f"✅ OpenAI returned data for {indicator_name} {period_label}")
        return result
        
    except Exception as e:
        logger.error(f"❌ OpenAI API error: {e}")
        return {}


def fill_missing_fields(
    indicator_data: Dict[str, Any],
    use_openai: bool = True
) -> Dict[str, Any]:
    """
    Fill các trường NULL trong indicator data bằng OpenAI
    
    Args:
        indicator_data: Dict với dữ liệu indicator hiện tại
        use_openai: Có dùng OpenAI không
    
    Returns:
        Dict với dữ liệu đã được fill
    """
    if not use_openai or not OPENAI_API_KEY:
        return indicator_data
    
    # Check which fields are missing
    important_fields = [
        "grdp_growth_rate", "iip_growth_rate", "cpi_growth_rate",
        "export_value", "fdi_disbursed", "state_budget_revenue"
    ]
    
    missing_fields = [
        field for field in important_fields 
        if indicator_data.get(field) is None
    ]
    
    if not missing_fields:
        logger.info("✅ All important fields are filled")
        return indicator_data
    
    logger.info(f"🔍 Missing fields: {missing_fields}, calling OpenAI...")
    
    # Call OpenAI
    period_label = indicator_data.get("period_label", "Unknown period")
    province = indicator_data.get("province")
    
    # Get existing non-null data for context
    existing_data = {
        k: v for k, v in indicator_data.items() 
        if v is not None and k not in ["id", "created_at", "updated_at"]
    }
    
    openai_result = call_openai_for_economic_data(
        indicator_name="economic_indicators",
        period_label=period_label,
        province=province,
        existing_data=existing_data
    )
    
    # Merge results
    for field in missing_fields:
        if field in openai_result and openai_result[field] is not None:
            indicator_data[field] = openai_result[field]
            logger.info(f"  ✅ Filled {field}: {openai_result[field]}")
    
    # Add metadata
    if openai_result:
        if not indicator_data.get("notes"):
            indicator_data["notes"] = "Một số dữ liệu được bổ sung bởi OpenAI"
        indicator_data["is_estimated"] = 1
    
    return indicator_data


def generate_summary(indicator_data: Dict[str, Any]) -> Optional[str]:
    """
    Tự động tạo tóm tắt (summary) cho economic indicator bằng OpenAI
    
    Args:
        indicator_data: Dict với dữ liệu indicator
    
    Returns:
        Tóm tắt ngắn (2-4 câu) hoặc None nếu lỗi
    """
    if not OPENAI_API_KEY:
        logger.warning("⚠️ OPENAI_API_KEY not found, cannot generate summary")
        return None
    
    try:
        from openai import OpenAI
        
        # Setup client
        if OPENAI_API_KEY.startswith("sk-or-v1-"):
            client = OpenAI(
                api_key=OPENAI_API_KEY,
                base_url="https://openrouter.ai/api/v1"
            )
            model = "openai/gpt-4o-mini"
        else:
            client = OpenAI(api_key=OPENAI_API_KEY)
            model = "gpt-4o-mini"
        
        # Extract key info
        location = indicator_data.get("province") or "Việt Nam"
        period = indicator_data.get("period_label", "")
        grdp = indicator_data.get("grdp_growth_rate")
        iip = indicator_data.get("iip_growth_rate")
        retail = indicator_data.get("retail_services_growth")
        export_val = indicator_data.get("export_value")
        fdi = indicator_data.get("fdi_disbursed")
        investment = indicator_data.get("total_investment")
        budget = indicator_data.get("state_budget_revenue")
        sbr_growth = indicator_data.get("sbr_growth_rate")
        cpi = indicator_data.get("cpi_growth_rate")
        
        # Build data summary for prompt
        data_points = []
        if grdp: data_points.append(f"GRDP tăng {grdp}%")
        if iip: data_points.append(f"IIP tăng {iip}%")
        if retail: data_points.append(f"Bán lẻ & dịch vụ tăng {retail}%")
        if export_val: data_points.append(f"Xuất khẩu {export_val:.1f} triệu USD")
        if fdi: data_points.append(f"FDI giải ngân {fdi:.1f} triệu USD")
        if investment: data_points.append(f"Đầu tư {investment:.0f} tỷ VNĐ")
        if budget: data_points.append(f"Thu ngân sách {budget:.0f} tỷ VNĐ")
        if sbr_growth: data_points.append(f"Thu NS tăng {sbr_growth}%")
        if cpi: data_points.append(f"CPI tăng {cpi}%")
        
        data_str = ", ".join(data_points) if data_points else "Chưa có đầy đủ số liệu"
        
        prompt = f"""Viết tóm tắt ngắn (2-3 câu, tối đa 250 từ) về tình hình kinh tế dựa trên các chỉ số sau:

Địa phương: {location}
Thời gian: {period}
Các chỉ số: {data_str}

Yêu cầu:
- Câu 1: Đánh giá tổng quan tình hình kinh tế và tốc độ tăng trưởng chính
- Câu 2: Nêu các điểm nhấn (ngành/lĩnh vực động lực, chỉ số nổi bật)
- Câu 3 (nếu cần): Triển vọng hoặc kết luận ngắn

Viết giọng điệu chuyên nghiệp, súc tích. CHỈ trả về đoạn tóm tắt, không thêm tiêu đề hay giải thích."""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Bạn là chuyên gia kinh tế Việt Nam, viết tóm tắt súc tích và chuyên nghiệp."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        summary = response.choices[0].message.content.strip()
        logger.info(f"✅ Generated summary for {location} {period}: {len(summary)} chars")
        return summary
        
    except Exception as e:
        logger.error(f"❌ Failed to generate summary: {e}")
        return None


def generate_indicator_analysis(
    indicator_data: Dict[str, Any],
    indicator_type: str
) -> Optional[str]:
    """
    Tạo phân tích chi tiết cho từng nhóm chỉ số kinh tế
    
    Args:
        indicator_data: Dict với dữ liệu indicator và detailed_data
        indicator_type: Loại chỉ số - grdp, iip, agricultural, retail_services, 
                       export_import, investment, budget, labor
    
    Returns:
        Phân tích chi tiết (3-5 câu) hoặc None nếu lỗi
    """
    if not OPENAI_API_KEY:
        logger.warning("⚠️ OPENAI_API_KEY not found, cannot generate analysis")
        return None
    
    try:
        from openai import OpenAI
        
        # Setup client
        if OPENAI_API_KEY.startswith("sk-or-v1-"):
            client = OpenAI(
                api_key=OPENAI_API_KEY,
                base_url="https://openrouter.ai/api/v1"
            )
            model = "openai/gpt-4o-mini"
        else:
            client = OpenAI(api_key=OPENAI_API_KEY)
            model = "gpt-4o-mini"
        
        # Extract basic info
        location = indicator_data.get("province") or "Việt Nam"
        period = indicator_data.get("period_label", "")
        detailed_data = indicator_data.get("detailed_data", {})
        source_url = indicator_data.get("source_article_url", "")
        
        # Build prompt based on indicator type
        prompts = {
            "grdp": f"""Phân tích GRDP (Tổng sản phẩm trên địa bàn) của {location} trong {period}.

Thông tin có sẵn: {json.dumps(detailed_data, ensure_ascii=False) if detailed_data else "Chưa có số liệu chi tiết"}

Yêu cầu:
- Nhận xét về giá trị GRDP và tốc độ tăng trưởng (nếu có số liệu)
- So sánh với cùng kỳ năm trước hoặc trung bình vùng
- Phân tích các ngành đóng góp chính (nông nghiệp, công nghiệp, dịch vụ)
- Đánh giá xu hướng và triển vọng

Viết 3-4 câu, chuyên nghiệp, dựa trên thực tế. CHỈ trả về phân tích.""",

            "iip": f"""Phân tích Chỉ số sản xuất công nghiệp (IIP) của {location} trong {period}.

Thông tin: {json.dumps(detailed_data, ensure_ascii=False) if detailed_data else "Chưa có số liệu chi tiết"}

Yêu cầu:
- Nhận xét về chỉ số IIP và tốc độ tăng/giảm
- Phân tích các ngành công nghiệp chủ lực (chế biến, chế tạo, điện, xây dựng)
- So sánh với cùng kỳ năm trước
- Đánh giá xu hướng sản xuất công nghiệp

Viết 3-4 câu. CHỈ trả về phân tích.""",

            "agricultural": f"""Phân tích sản xuất nông nghiệp của {location} trong {period}.

Thông tin: {json.dumps(detailed_data, ensure_ascii=False) if detailed_data else "Chưa có số liệu chi tiết"}

Yêu cầu:
- Chỉ số sản xuất nông nghiệp và tốc độ tăng trưởng
- Các sản phẩm nông nghiệp chủ lực (lúa, rau, thủy sản, chăn nuôi)
- Tình hình thời tiết, mùa vụ ảnh hưởng
- Giá trị sản xuất và triển vọng

Viết 3-4 câu. CHỈ trả về phân tích.""",

            "retail_services": f"""Phân tích Tổng mức bán lẻ hàng hóa & dịch vụ tiêu dùng của {location} trong {period}.

Thông tin: {json.dumps(detailed_data, ensure_ascii=False) if detailed_data else "Chưa có số liệu chi tiết"}

Yêu cầu:
- Tổng mức bán lẻ & dịch vụ và tốc độ tăng trưởng
- Phân tích các nhóm hàng chủ yếu (thực phẩm, hàng tiêu dùng, dịch vụ)
- Xu hướng tiêu dùng của người dân
- Đánh giá sức mua và triển vọng

Viết 3-4 câu. CHỈ trả về phân tích.""",

            "export_import": f"""Phân tích Xuất nhập khẩu của {location} trong {period}.

Thông tin: {json.dumps(detailed_data, ensure_ascii=False) if detailed_data else "Chưa có số liệu chi tiết"}

Yêu cầu:
- Kim ngạch xuất khẩu, nhập khẩu và tốc độ tăng trưởng
- Các mặt hàng xuất khẩu chủ lực
- Cân đối thương mại (thặng dư/thâm hụt)
- Thị trường xuất khẩu chính và triển vọng

Viết 3-4 câu. CHỈ trả về phân tích.""",

            "investment": f"""Phân tích Thu hút đầu tư của {location} trong {period}.

Thông tin: {json.dumps(detailed_data, ensure_ascii=False) if detailed_data else "Chưa có số liệu chi tiết"}

Yêu cầu:
- FDI đăng ký mới và FDI giải ngân
- Đầu tư trong nước (công, tư)
- Tổng vốn đầu tư và tốc độ tăng trưởng
- Các dự án/lĩnh vực thu hút đầu tư chính
- Đánh giá môi trường đầu tư

Viết 3-4 câu. CHỈ trả về phân tích.""",

            "budget": f"""Phân tích Thu ngân sách nhà nước của {location} trong {period}.

Thông tin: {json.dumps(detailed_data, ensure_ascii=False) if detailed_data else "Chưa có số liệu chi tiết"}

Yêu cầu:
- Tổng thu ngân sách và tốc độ tăng trưởng
- Thu từ thuế và thu ngoài thuế
- So sánh với cùng kỳ và kế hoạch
- Đánh giá hiệu quả thu ngân sách

Viết 3-4 câu. CHỈ trả về phân tích.""",

            "labor": f"""Phân tích Thị trường lao động của {location} trong {period}.

Thông tin: {json.dumps(detailed_data, ensure_ascii=False) if detailed_data else "Chưa có số liệu chi tiết"}

Yêu cầu:
- Lực lượng lao động và tỷ lệ thất nghiệp
- Việc làm mới được tạo ra
- Cơ cấu lao động theo ngành
- Chất lượng nguồn nhân lực và triển vọng

Viết 3-4 câu. CHỈ trả về phân tích."""
        }
        
        prompt = prompts.get(indicator_type)
        if not prompt:
            logger.warning(f"⚠️ Unknown indicator type: {indicator_type}")
            return None
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Bạn là chuyên gia kinh tế Việt Nam, phân tích chuyên sâu các chỉ số kinh tế."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=400
        )
        
        analysis = response.choices[0].message.content.strip()
        logger.info(f"✅ Generated {indicator_type} analysis for {location} {period}: {len(analysis)} chars")
        return analysis
        
    except Exception as e:
        logger.error(f"❌ Failed to generate {indicator_type} analysis: {e}")
        return None


def generate_all_analyses(indicator_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Tạo phân tích cho tất cả các nhóm chỉ số
    
    Args:
        indicator_data: Dict với dữ liệu indicator
    
    Returns:
        Dict với key là tên trường analysis và value là nội dung phân tích
    """
    analyses = {}
    
    indicator_types = [
        "grdp", "iip", "agricultural", "retail_services",
        "export_import", "investment", "budget", "labor"
    ]
    
    for ind_type in indicator_types:
        analysis = generate_indicator_analysis(indicator_data, ind_type)
        if analysis:
            analyses[f"{ind_type}_analysis"] = analysis
    
    return analyses
