"""
Universal Economic Data Extractor v2.0 - Production Architecture

Kiến trúc CHUẨN:
- LLM CHỈ làm classification (YES/NO) - KHÔNG extract số
- Số liệu = REGEX ONLY từ văn bản gốc
- Strict validation với Pydantic schema

Pipeline:
    Text → Normalize → Section Detect → Indicator Classify (LLM) → Value Extract (Regex) → Validate → DB
"""
import re
import logging
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
import requests
from bs4 import BeautifulSoup

# LLM imports - dùng cho classification ONLY
try:
    from langchain_openai import ChatOpenAI
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

from app.models.model_iip_detail import IIPDetail
from app.models.model_agri_detail import AgriProductionDetail
from app.models.model_retail_detail import RetailServicesDetail
from app.models.model_export_detail import ExportDetail
from app.models.model_investment_detail import InvestmentDetail
from app.models.model_budget_detail import BudgetRevenueDetail
from app.models.model_cpi_detail import CPIDetail
from app.models.model_grdp_detail import GRDPDetail

logger = logging.getLogger(__name__)


# =============================================================================
# STEP 1: PYDANTIC SCHEMAS - Strict Validation
# =============================================================================

class ExtractedIndicator(BaseModel):
    """Schema cho một chỉ số kinh tế đã extract"""
    indicator_type: str
    province: str = "Hưng Yên"
    year: int
    quarter: Optional[int] = None
    period_type: str = "quarter"
    actual_value: Optional[float] = None
    change_yoy: Optional[float] = None
    source_text: str = ""  # Đoạn text gốc chứa giá trị
    data_source: str = ""
    data_status: str = "official"
    
    @field_validator('change_yoy')
    @classmethod
    def validate_yoy(cls, v):
        if v is not None and abs(v) > 100:
            raise ValueError(f"YoY growth {v}% không hợp lý (>100%)")
        return v
    
    @field_validator('quarter')
    @classmethod
    def validate_quarter(cls, v):
        if v is not None and v not in [1, 2, 3, 4]:
            raise ValueError(f"Quarter {v} không hợp lệ")
        return v


class ValueRangeValidator:
    """Validate value ranges cho từng loại chỉ số"""
    
    # (min, max, unit, description)
    RANGES = {
        'grdp': (40000, 250000, 'tỷ VND', 'Tổng sản phẩm địa bàn'),
        'iip': (None, None, 'index', 'Chỉ số sản xuất công nghiệp'),
        'agri': (2000, 25000, 'tỷ VND', 'Sản xuất nông nghiệp'),
        'retail': (2000, 150000, 'tỷ VND', 'Bán lẻ hàng hóa dịch vụ'),  # Monthly: 2k+, Quarterly: 5k-40k, Annual: 100k+
        'export': (50, 1000, 'triệu USD', 'Kim ngạch xuất khẩu'),
        'investment': (1000, 100000, 'tỷ VND', 'Vốn đầu tư'),  # Expanded for VND values
        'budget': (1000, 85480, 'tỷ VND', 'Thu ngân sách'),  # Monthly: 1k+, Quarterly: 5k+, Annual: 40k+
        'cpi': (95, 120, 'index', 'Chỉ số giá tiêu dùng')
    }
    
    # Anti-patterns: từ khóa báo hiệu đây KHÔNG phải số liệu chính
    ANTI_PATTERNS = {
        'agri': ['tạ/ha', 'tấn', 'năng suất', 'sản lượng', 'diện tích', 'ha'],
        'retail': ['xăng dầu', 'lưu trú', 'ăn uống', 'tháng Một', 'tháng Hai', 'tháng Ba'],
        'budget': ['thu từ', 'khu vực', 'nội địa', 'thuế môn bài', 'thu đất'],
        'investment': ['của doanh nghiệp', 'khu vực', 'từ FDI'],
        'iip': ['chế biến', 'khai khoáng', 'điện', 'ngành', 'phân ngành'],
        'export': ['vốn', 'tín dụng', 'dư nợ', 'cho vay'],
    }
    
    @classmethod
    def has_anti_pattern(cls, indicator_type: str, text: str) -> bool:
        """
        Check if text contains anti-patterns (signals this is NOT the main indicator)
        Returns True if anti-pattern found (should skip this value)
        """
        if indicator_type not in cls.ANTI_PATTERNS:
            return False
        
        text_lower = text.lower()
        for anti in cls.ANTI_PATTERNS[indicator_type]:
            if anti.lower() in text_lower:
                return True
        return False
    
    @classmethod
    def validate(cls, indicator_type: str, value: float, is_annual: bool = False) -> Tuple[bool, str]:
        """
        Validate giá trị có nằm trong khoảng hợp lý không
        
        Args:
            indicator_type: Loại chỉ số
            value: Giá trị cần validate
            is_annual: True nếu là dữ liệu năm (sẽ nhân 4 cho quarterly ranges)
        
        Returns:
            (is_valid, error_message)
        """
        if indicator_type not in cls.RANGES:
            return True, ""
        
        min_val, max_val, unit, desc = cls.RANGES[indicator_type]
        
        if min_val is None or max_val is None:
            return True, ""
        
        # Nếu là dữ liệu năm, mở rộng range (x4 cho quarterly indicators)
        if is_annual and indicator_type not in ['cpi', 'grdp']:
            max_val = max_val * 4
        
        if not (min_val <= value <= max_val):
            return False, (
                f"{indicator_type.upper()} = {value:,.0f} {unit} "
                f"ngoài khoảng hợp lý ({min_val:,.0f} - {max_val:,.0f} {unit})"
            )
        
        return True, ""


# =============================================================================
# STEP 2: TEXT NORMALIZER - Clean text, giữ nguyên số
# =============================================================================

class TextNormalizer:
    """Chuẩn hóa văn bản, KHÔNG thay đổi số liệu"""
    
    @staticmethod
    def normalize(text: str) -> str:
        """
        Normalize text nhưng GIỮ NGUYÊN số liệu
        
        - Loại bỏ nbsp, multiple spaces
        - KHÔNG dịch
        - KHÔNG paraphrase
        """
        if not text:
            return ""
        
        # Replace non-breaking space
        text = text.replace('\xa0', ' ')
        
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Remove zero-width characters
        text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)
        
        return text.strip()
    
    @staticmethod
    def extract_sentences_with_numbers(text: str) -> List[str]:
        """
        Trích xuất các câu có chứa số liệu
        Giúp focus vào phần quan trọng
        """
        # Split into sentences
        sentences = re.split(r'[.!?]\s+', text)
        
        # Filter sentences containing numbers
        number_pattern = r'\d+[.,]?\d*\s*(?:tỷ|triệu|nghìn|%|USD|VND)'
        
        return [s for s in sentences if re.search(number_pattern, s, re.IGNORECASE)]


# =============================================================================
# STEP 3: SECTION DETECTOR - Detect structure bằng regex
# =============================================================================

class SectionDetector:
    """Detect sections trong báo cáo kinh tế bằng REGEX"""
    
    # Patterns cho section headers
    SECTION_PATTERNS = [
        r'\n\d+\.?\s+[A-ZÀ-ỴĐ][a-zà-ỵđ\s]+',  # "1. Tăng trưởng kinh tế"
        r'\n[IVX]+\.?\s+[A-ZÀ-ỴĐ][a-zà-ỵđ\s]+',  # "I. Nông nghiệp"
        r'\n[a-z]\)\s+[A-ZÀ-ỴĐ][a-zà-ỵđ\s]+',  # "a) Công nghiệp"
    ]
    
    @classmethod
    def detect_sections(cls, text: str) -> List[Dict[str, Any]]:
        """
        Detect các sections trong văn bản
        
        Returns:
            List of {'title': str, 'start': int, 'end': int, 'content': str}
        """
        sections = []
        
        for pattern in cls.SECTION_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                sections.append({
                    'title': match.group().strip(),
                    'start': match.start(),
                    'match': match.group()
                })
        
        # Sort by position
        sections.sort(key=lambda x: x['start'])
        
        # Extract content between sections
        for i, section in enumerate(sections):
            start = section['start']
            end = sections[i + 1]['start'] if i + 1 < len(sections) else len(text)
            section['content'] = text[start:end]
            section['end'] = end
        
        return sections


# =============================================================================
# STEP 4: INDICATOR DICTIONARY - Keywords cho từng chỉ số
# =============================================================================

class IndicatorDictionary:
    """Dictionary-based indicator detection - KHÔNG dùng LLM"""
    
    KEYWORDS = {
        'grdp': [
            'grdp', 'tổng sản phẩm trên địa bàn', 'tổng sản phẩm địa bàn',
            'gdp', 'quy mô kinh tế', 'tăng trưởng kinh tế',
            'giá hiện hành', 'giá so sánh'
        ],
        'iip': [
            'iip', 'chỉ số sản xuất công nghiệp', 'sản xuất công nghiệp',
            'công nghiệp chế biến', 'chế biến chế tạo', 
            'giá trị sản xuất công nghiệp'
        ],
        'agri': [
            'nông nghiệp', 'sản xuất nông nghiệp', 'nông lâm nghiệp',
            'nông lâm thủy sản', 'trồng trọt', 'chăn nuôi',
            'giá trị sản xuất nông nghiệp'
        ],
        'retail': [
            'bán lẻ', 'tổng mức bán lẻ', 'dịch vụ tiêu dùng',
            'bán lẻ hàng hóa', 'doanh thu dịch vụ',
            'thương mại dịch vụ'
        ],
        'export': [
            'kim ngạch xuất khẩu', 'tổng kim ngạch xuất khẩu', 
            'hàng hóa xuất khẩu', 'giá trị xuất khẩu hàng hóa',
            'kim ngạch hàng hóa xuất khẩu'
        ],
        'investment': [
            'đầu tư', 'fdi', 'vốn đầu tư', 'thu hút đầu tư',
            'đầu tư nước ngoài', 'vốn đăng ký', 'ddi',
            'tổng vốn đầu tư', 'vốn đầu tư phát triển'
        ],
        'budget': [
            'ngân sách', 'thu ngân sách', 'thu thuế',
            'thu nội địa', 'ngân sách nhà nước',
            'tổng thu ngân sách'
        ],
        'cpi': [
            'cpi', 'chỉ số giá', 'chỉ số giá tiêu dùng',
            'lạm phát', 'giá tiêu dùng bình quân'
        ]
    }
    
    @classmethod
    def detect_candidates(cls, text: str) -> Dict[str, List[str]]:
        """
        Detect các chỉ số candidate trong text
        
        Returns:
            {indicator_type: [matched_keywords]}
        """
        text_lower = text.lower()
        candidates = {}
        
        for indicator_type, keywords in cls.KEYWORDS.items():
            matched = [kw for kw in keywords if kw in text_lower]
            if matched:
                candidates[indicator_type] = matched
        
        return candidates
    
    @classmethod
    def find_keyword_context(cls, text: str, indicator_type: str, context_chars: int = 800, 
                           year: Optional[int] = None) -> List[str]:
        """
        Tìm context (đoạn văn) xung quanh keyword
        ƯU TIÊN đoạn chứa CẢ keyword VÀ số liệu
        
        STRATEGY:
        1. Tìm keyword position trong text
        2. Lấy 800 chars TRƯỚC và SAU keyword
        3. Ưu tiên: priority keywords -> year match -> nhiều số liệu
        
        Args:
            year: Year to filter (ưu tiên context có "năm {year}" hoặc "cả năm")
        
        Returns:
            List of context strings containing the keyword
        """
        keywords = cls.KEYWORDS.get(indicator_type, [])
        if not keywords:
            return [text[:1000]]
        
        priority_keywords = {
            'iip': ['(IIP)', 'Chỉ số sản xuất công nghiệp (IIP)'],
            'retail': ['Tổng mức bán lẻ', 'tổng mức bán lẻ', 'năm 20', 'cả năm', 'Quý'],
            'investment': ['Tổng vốn đầu tư', 'tổng vốn đầu tư'],
            'budget': ['Thu ngân sách nhà nước', 'Tổng thu ngân sách', 'thu ngân sách nhà nước'],
            'agri': ['giá trị sản xuất nông nghiệp', 'nông, lâm nghiệp và thủy sản', 'Giá trị sản xuất'],
            'export': ['Kim ngạch xuất khẩu', 'Tổng kim ngạch xuất khẩu', 'kim ngạch hàng hóa xuất khẩu'],
        }
        
        detail_antipatterns = {
            'budget': [
                'thu từ khu vực',
                'thu nội địa',
                'thu thuế môn bài',
                'thu từ doanh nghiệp',
                'các khoản thu về đất',
            ],
            'retail': [
                'doanh thu dịch vụ lưu trú',
                'doanh thu bán lẻ hàng hóa',
                'dịch vụ lưu trú, ăn uống',
                'doanh thu bán lẻ xăng dầu',
                'vốn đầu tư',
                'vốn ngân sách',
            ],
            'investment': [
                'vốn đầu tư của',
                'dự án',
            ],
            'agri': [
                'ống dẫn', 'thép', 'sắt', 'máy giặt', 'nitơrat',
                'chăn nuôi', 'trồng trọt', 'lâm nghiệp', 'thủy sản',
                'chế biến', 'cây công nghiệp', 'rau màu',
            ],
            'export': [
                'vốn', 'tín dụng', 'dư nợ', 'cho vay',
                'nông nghiệp, nông thôn', 'doanh nghiệp nhỏ',
                'công nghiệp hỗ trợ', 'ứng dụng công nghệ cao',
            ],
        }
        
        contexts = []
        
        for keyword in keywords:
            for match in re.finditer(re.escape(keyword), text, re.IGNORECASE):
                start = max(0, match.start() - context_chars)
                end = min(len(text), match.end() + context_chars)
                context = text[start:end]
                
                value_count = len(re.findall(r'\d+[.,]?\d*\s*(?:tỷ|triệu|%|nghìn)', context))
                
                has_priority = False
                if indicator_type in priority_keywords:
                    has_priority = any(
                        pk.lower() in context.lower() 
                        for pk in priority_keywords[indicator_type]
                    )
                
                has_year_match = False
                if year:
                    year_patterns = [f'năm {year}', 'cả năm', f'Năm {year}', 'Quý']
                    has_year_match = any(p in context for p in year_patterns)
                
                has_month_antipattern = False
                if indicator_type in ['retail', 'budget'] and year:
                    month_patterns = [f'tháng {m}' for m in ['Một', 'Hai', 'Ba', 'Tư', 'Năm', 'Sáu', 
                                                             'Bảy', 'Tám', 'Chín', 'Mười', 'Mười Một', 'Mười Hai']]
                    has_month_antipattern = any(p in context for p in month_patterns)
                
                has_detail_antipattern = False
                if indicator_type in detail_antipatterns:
                    has_detail_antipattern = any(
                        anti.lower() in context.lower()
                        for anti in detail_antipatterns[indicator_type]
                    )
                
                contexts.append({
                    'text': context,
                    'value_count': value_count,
                    'position': match.start(),
                    'has_priority': has_priority,
                    'has_year_match': has_year_match,
                    'has_month_antipattern': has_month_antipattern,
                    'has_detail_antipattern': has_detail_antipattern,
                })
        
        contexts.sort(key=lambda x: (
            -x['has_priority'],
            -x['has_year_match'],
            x['has_detail_antipattern'],
            x['has_month_antipattern'],
            -x['value_count'],
            x['position']
        ))
        
        unique_contexts = []
        seen_positions = set()
        
        for ctx_dict in contexts:
            pos = ctx_dict['position']
            if any(abs(pos - seen_pos) < 400 for seen_pos in seen_positions):
                continue
            
            unique_contexts.append(ctx_dict['text'][:1200])
            seen_positions.add(pos)
            
            if len(unique_contexts) >= 2:
                break
        
        return unique_contexts if unique_contexts else [text[:1000]]


# =============================================================================
# STEP 5: LLM CLASSIFIER
# =============================================================================

class LLMClassifier:
    """
    LLM CHỈ dùng để CONFIRM indicator type
    KHÔNG extract số liệu
    
    Input: "Câu này có phải đang mô tả chỉ tiêu GRDP không?"
    Output: {"confirm": true/false, "confidence": 0.95}
    """
    
    def __init__(self):
        self.llm = None
        if LLM_AVAILABLE:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.llm = ChatOpenAI(
                    model="openai/gpt-4o-mini",
                    temperature=0,
                    openai_api_key=api_key,
                    base_url="https://openrouter.ai/api/v1"
                )
                logger.info("LLM Classifier initialized (classification only)")
    
    def confirm_indicator(self, context_text: str, indicator_type: str) -> Dict[str, Any]:
        """
        Confirm xem context có đang mô tả indicator này không
        
        Args:
            context_text: Đoạn văn bản chứa keyword
            indicator_type: Loại chỉ số cần confirm
        
        Returns:
            {"confirm": bool, "confidence": float, "reasoning": str}
        """
        if not self.llm:
            return {"confirm": True, "confidence": 0.7, "reasoning": "LLM not available, using keyword match"}
        
        indicator_names = {
            'grdp': 'GRDP (Tổng sản phẩm trên địa bàn)',
            'iip': 'IIP (Chỉ số sản xuất công nghiệp)',
            'agri': 'Sản xuất nông nghiệp',
            'retail': 'Bán lẻ hàng hóa và dịch vụ',
            'export': 'Kim ngạch xuất khẩu',
            'investment': 'Vốn đầu tư (FDI/DDI)',
            'budget': 'Thu ngân sách nhà nước',
            'cpi': 'CPI (Chỉ số giá tiêu dùng)'
        }
        
        indicator_name = indicator_names.get(indicator_type, indicator_type)
        
        prompt = f"""Phân loại chỉ tiêu kinh tế.

ĐOẠN VĂN BẢN:
"{context_text}"

CÂU HỎI:
Đoạn văn bản trên có đang mô tả số liệu về "{indicator_name}" không?

CHÚ Ý:
- CHỈ trả lời về việc văn bản CÓ ĐỀ CẬP đến chỉ tiêu này hay không
- KHÔNG quan tâm đến giá trị số liệu cụ thể

Trả về JSON (CHỈ JSON, không text khác):
{{"confirm": true hoặc false, "confidence": 0.0-1.0, "reasoning": "lý do ngắn gọn"}}
"""
        
        try:
            result = self.llm.invoke(prompt)
            content = result.content.strip()
            
            # Parse JSON response
            json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    "confirm": data.get("confirm", False),
                    "confidence": data.get("confidence", 0.5),
                    "reasoning": data.get("reasoning", "")
                }
        except Exception as e:
            logger.warning(f"LLM classification error: {e}")
        
        return {"confirm": True, "confidence": 0.5, "reasoning": "LLM error, fallback to True"}


# =============================================================================
# STEP 6: VALUE EXTRACTOR
# =============================================================================

class ValueExtractor:
    """
    Extract số liệu bằng REGEX
    
    QUAN TRỌNG: LLM TUYỆT ĐỐI KHÔNG extract số
    Mọi số liệu phải lấy từ văn bản gốc bằng regex
    """
    
    # Patterns cho giá trị (tỷ VND)
    VALUE_PATTERNS_VND = [
        # "40.000 tỷ đồng" -> 40000
        (r'(\d{1,3})[.,](\d{3})\s*tỷ\s*(?:đồng)?', lambda m: float(m.group(1) + m.group(2))),
        
        # "đạt 40.000 tỷ" -> 40000  
        (r'đạt\s+(\d{1,3})[.,](\d{3})\s*tỷ', lambda m: float(m.group(1) + m.group(2))),
        
        # "ước đạt 40,5 nghìn tỷ" -> 40500
        (r'(\d+)[.,](\d+)\s*nghìn\s*tỷ', lambda m: float(m.group(1) + m.group(2)) * 1000),
        
        # "129.305 tỷ đồng" -> 129305
        (r'(\d{1,3})[.,](\d{3})\s*tỷ', lambda m: float(m.group(1) + m.group(2))),
        
        # "4.786,5 tỷ" -> 4786.5
        (r'(\d{1,3})[.,](\d{3})[.,](\d+)\s*tỷ', lambda m: float(f"{m.group(1)}{m.group(2)}.{m.group(3)}")),
    ]
    
    # Patterns cho growth rate (%)
    GROWTH_PATTERNS = [
        # "tăng 7,70%" -> 7.70
        (r'tăng\s+(\d+)[.,](\d+)\s*%', lambda m: float(f"{m.group(1)}.{m.group(2)}")),
        
        # "tăng 10%" -> 10.0
        (r'tăng\s+(\d+)\s*%', lambda m: float(m.group(1))),
        
        # "giảm 4,46%" -> -4.46
        (r'giảm\s+(\d+)[.,](\d+)\s*%', lambda m: -float(f"{m.group(1)}.{m.group(2)}")),
        
        # "giảm 5%" -> -5.0
        (r'giảm\s+(\d+)\s*%', lambda m: -float(m.group(1))),
        
        # "tăng trưởng đạt 8,5%" -> 8.5
        (r'tăng\s*trưởng.*?(\d+)[.,](\d+)\s*%', lambda m: float(f"{m.group(1)}.{m.group(2)}")),
    ]
    
    # Patterns cho USD
    VALUE_PATTERNS_USD = [
        # "150 triệu USD" -> 150
        (r'(\d+)[.,]?(\d*)\s*triệu\s*(?:USD|usd|đô la)', 
         lambda m: float(f"{m.group(1)}.{m.group(2) or '0'}")),
        
        # "1,5 tỷ USD" -> 1500
        (r'(\d+)[.,](\d+)\s*tỷ\s*(?:USD|usd)', 
         lambda m: float(f"{m.group(1)}{m.group(2)}") * 1000),
    ]
    
    # Patterns cho CPI (index)
    CPI_PATTERNS = [
        # "CPI bình quân tăng 6,33%" -> tăng 6.33% so với năm trước
        (r'(?:CPI|chỉ số giá).*?(?:bình quân)?.*?tăng\s+(\d+)[.,](\d+)\s*%', 
         lambda m: 100 + float(f"{m.group(1)}.{m.group(2)}")),  # Convert to index
        
        # "CPI đạt 106,33" -> 106.33
        (r'(?:CPI|chỉ số giá).*?đạt\s+(\d+)[.,](\d+)', 
         lambda m: float(f"{m.group(1)}.{m.group(2)}")),
    ]
    
    @classmethod
    def extract_value_vnd(cls, text: str) -> Tuple[Optional[float], str]:
        """
        Extract giá trị tỷ VND từ text
        
        Returns:
            (value, source_text)
        """
        for pattern, converter in cls.VALUE_PATTERNS_VND:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = converter(match)
                    source_text = match.group(0)
                    return value, source_text
                except:
                    continue
        return None, ""
    
    @classmethod
    def extract_growth(cls, text: str) -> Tuple[Optional[float], str]:
        """
        Extract growth rate từ text
        
        Returns:
            (growth_rate, source_text)
        """
        for pattern, converter in cls.GROWTH_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = converter(match)
                    source_text = match.group(0)
                    return value, source_text
                except:
                    continue
        return None, ""
    
    @classmethod
    def extract_value_usd(cls, text: str) -> Tuple[Optional[float], str]:
        """Extract giá trị triệu USD từ text"""
        for pattern, converter in cls.VALUE_PATTERNS_USD:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = converter(match)
                    source_text = match.group(0)
                    return value, source_text
                except:
                    continue
        return None, ""
    
    @classmethod
    def extract_cpi(cls, text: str) -> Tuple[Optional[float], str]:
        """Extract CPI index từ text"""
        for pattern, converter in cls.CPI_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = converter(match)
                    source_text = match.group(0)
                    return value, source_text
                except:
                    continue
        return None, ""
    
    @classmethod
    def extract_qoq_growth(cls, text: str) -> Tuple[Optional[float], str]:
        """Extract quarter-over-quarter growth rate từ text"""
        patterns = [
            (r'tăng\s+(\d+)[.,](\d+)\s*%\s*so với quý trước', lambda m: float(f"{m.group(1)}.{m.group(2)}")),
            (r'tăng\s+(\d+)\s*%\s*so với quý trước', lambda m: float(m.group(1))),
            (r'giảm\s+(\d+)[.,](\d+)\s*%\s*so với quý trước', lambda m: -float(f"{m.group(1)}.{m.group(2)}")),
            (r'giảm\s+(\d+)\s*%\s*so với quý trước', lambda m: -float(m.group(1))),
            (r'tăng\s+(\d+)[.,](\d+)\s*%\s*so với quý liền kề', lambda m: float(f"{m.group(1)}.{m.group(2)}")),
            (r'giảm\s+(\d+)[.,](\d+)\s*%\s*so với quý liền kề', lambda m: -float(f"{m.group(1)}.{m.group(2)}")),
        ]
        
        for pattern, converter in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = converter(match)
                    source_text = match.group(0)
                    return value, source_text
                except:
                    continue
        return None, ""
    
    @classmethod
    def extract_mom_growth(cls, text: str) -> Tuple[Optional[float], str]:
        """Extract month-over-month growth rate từ text"""
        patterns = [
            (r'tăng\s+(\d+)[.,](\d+)\s*%\s*so với tháng trước', lambda m: float(f"{m.group(1)}.{m.group(2)}")),
            (r'tăng\s+(\d+)\s*%\s*so với tháng trước', lambda m: float(m.group(1))),
            (r'giảm\s+(\d+)[.,](\d+)\s*%\s*so với tháng trước', lambda m: -float(f"{m.group(1)}.{m.group(2)}")),
            (r'giảm\s+(\d+)\s*%\s*so với tháng trước', lambda m: -float(m.group(1))),
            (r'tăng\s+(\d+)[.,](\d+)\s*%\s*so với tháng liền kề', lambda m: float(f"{m.group(1)}.{m.group(2)}")),
            (r'giảm\s+(\d+)[.,](\d+)\s*%\s*so với tháng liền kề', lambda m: -float(f"{m.group(1)}.{m.group(2)}")),
        ]
        
        for pattern, converter in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = converter(match)
                    source_text = match.group(0)
                    return value, source_text
                except:
                    continue
        return None, ""
    
    @classmethod
    def extract_forecast(cls, text: str) -> Tuple[Optional[float], str]:
        """Extract forecast value từ text - chỉ match khi rõ ràng là forecast/kế hoạch"""
        patterns = [
            # Chỉ match forecast/plan rõ ràng, KHÔNG match "ước đạt" (actual estimate)
            (r'(?:dự báo|dự kiến|kế hoạch)(?!.*(?:đạt|thực hiện)).*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
            (r'mục tiêu.*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
            (r'chỉ tiêu.*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
            # Match "năm sau" or future years
            (r'năm (?:sau|\d{4}).*?(?:dự báo|dự kiến|kế hoạch).*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
        ]
        
        for pattern, ptype in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    if ptype == 'value_split':
                        parts = [match.group(1), match.group(2)]
                        if match.lastindex >= 3 and match.group(3):
                            parts.append(match.group(3))
                        value = float(''.join(parts))
                        
                        # Double-check: không phải actual value (có "ước đạt", "thực hiện")
                        full_context = match.group(0)
                        if re.search(r'(?:ước đạt|thực hiện|đã đạt|đạt được)', full_context, re.IGNORECASE):
                            continue  # Skip nếu là actual value
                        
                        return value, match.group(0)
                except:
                    continue
        return None, ""
    
    # =========================================================================
    # SPECIFIC EXTRACTORS cho từng indicator type
    # =========================================================================
    
    @classmethod
    def extract_retail_breakdown(cls, text: str) -> Dict[str, Optional[float]]:
        """
        Extract retail_value và services_value từ text
        Returns: {'retail_value': float, 'services_value': float}
        """
        result = {'retail_value': None, 'services_value': None}
        
        # Pattern cho bán lẻ hàng hóa
        retail_patterns = [
            r'bán lẻ hàng hóa.*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ',
            r'doanh thu bán lẻ.*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ',
        ]
        
        for pattern in retail_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                parts = [match.group(1), match.group(2)]
                if match.lastindex >= 3 and match.group(3):
                    parts.append(match.group(3))
                result['retail_value'] = float(''.join(parts))
                break
        
        # Pattern cho dịch vụ
        services_patterns = [
            r'doanh thu dịch vụ(?!.*lưu trú).*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ',
            r'dịch vụ tiêu dùng.*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ',
        ]
        
        for pattern in services_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                parts = [match.group(1), match.group(2)]
                if match.lastindex >= 3 and match.group(3):
                    parts.append(match.group(3))
                result['services_value'] = float(''.join(parts))
                break
        
        return result
    
    @classmethod
    def extract_export_details(cls, text: str) -> Dict[str, Any]:
        """
        Extract export_usd, export_vnd, top_products, top_markets
        Returns: {'export_usd': float, 'export_vnd': float, 'top_products': str, 'top_markets': str}
        """
        result = {
            'export_usd': None,
            'export_vnd': None,
            'top_products': None,
            'top_markets': None
        }
        
        # Extract USD value
        usd_patterns = [
            r'kim ngạch xuất khẩu.*?(\d+[.,]\d+)\s*triệu\s*USD',
            r'xuất khẩu.*?đạt.*?(\d+[.,]\d+)\s*triệu\s*USD',
        ]
        for pattern in usd_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['export_usd'] = float(match.group(1).replace(',', '.'))
                break
        
        # Extract top products (common Vietnamese export products)
        product_keywords = [
            'may mặc', 'dệt may', 'giày dép', 'da giày', 
            'điện tử', 'linh kiện điện tử', 'thiết bị điện tử',
            'gỗ', 'đồ gỗ', 'nội thất',
            'thủy sản', 'tôm', 'cá',
            'rau quả', 'hoa quả',
            'cà phê', 'cao su', 'gạo',
            'xe máy', 'ô tô', 'phụ tùng'
        ]
        
        found_products = []
        for keyword in product_keywords:
            if keyword in text.lower():
                found_products.append(keyword)
        
        if found_products:
            result['top_products'] = ', '.join(found_products[:5])  # Top 5
        
        # Extract top markets (common Vietnamese export markets)
        market_keywords = [
            'Trung Quốc', 'Mỹ', 'Hoa Kỳ', 'Nhật Bản', 'Hàn Quốc',
            'EU', 'Châu Âu', 'ASEAN', 'Đông Nam Á',
            'Đài Loan', 'Hồng Kông', 'Singapore', 'Thái Lan'
        ]
        
        found_markets = []
        for keyword in market_keywords:
            if keyword in text:
                found_markets.append(keyword)
        
        if found_markets:
            result['top_markets'] = ', '.join(found_markets[:5])  # Top 5
        
        return result
    
    @classmethod
    def extract_investment_details(cls, text: str) -> Dict[str, Any]:
        """
        Extract FDI và DDI details
        Returns: {
            'fdi_registered': float (triệu USD),
            'fdi_disbursed': float (triệu USD),
            'fdi_projects_new': int,
            'fdi_projects_expanded': int,
            'ddi_value': float (tỷ VND),
            'public_investment': float (tỷ VND)
        }
        """
        result = {
            'fdi_registered': None,
            'fdi_disbursed': None,
            'fdi_projects_new': None,
            'fdi_projects_expanded': None,
            'ddi_value': None,
            'public_investment': None
        }
        
        # FDI registered (vốn đăng ký)
        fdi_reg_patterns = [
            r'vốn đăng ký.*?FDI.*?(\d+[.,]\d+)\s*triệu\s*USD',
            r'FDI.*?đăng ký.*?(\d+[.,]\d+)\s*triệu\s*USD',
            r'vốn FDI đăng ký.*?(\d+[.,]\d+)\s*triệu\s*USD',
        ]
        for pattern in fdi_reg_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['fdi_registered'] = float(match.group(1).replace(',', '.'))
                break
        
        # FDI disbursed (vốn giải ngân)
        fdi_dis_patterns = [
            r'vốn giải ngân.*?(\d+[.,]\d+)\s*triệu\s*USD',
            r'FDI.*?giải ngân.*?(\d+[.,]\d+)\s*triệu\s*USD',
            r'vốn thực hiện.*?FDI.*?(\d+[.,]\d+)\s*triệu\s*USD',
        ]
        for pattern in fdi_dis_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['fdi_disbursed'] = float(match.group(1).replace(',', '.'))
                break
        
        # FDI projects
        new_project_patterns = [
            r'(\d+)\s*dự án mới',
            r'cấp mới.*?(\d+)\s*dự án',
        ]
        for pattern in new_project_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['fdi_projects_new'] = int(match.group(1))
                break
        
        expanded_project_patterns = [
            r'(\d+)\s*dự án điều chỉnh',
            r'điều chỉnh.*?(\d+)\s*dự án',
        ]
        for pattern in expanded_project_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['fdi_projects_expanded'] = int(match.group(1))
                break
        
        # DDI (domestic direct investment)
        ddi_patterns = [
            r'DDI.*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ',
            r'đầu tư trong nước.*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ',
        ]
        for pattern in ddi_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                parts = [match.group(1), match.group(2)]
                if match.lastindex >= 3 and match.group(3):
                    parts.append(match.group(3))
                result['ddi_value'] = float(''.join(parts))
                break
        
        # Public investment - thêm nhiều alternative patterns
        public_patterns = [
            r'vốn ngân sách[^.;]{0,50}(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ',
            r'đầu tư công[^.;]{0,50}(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ',
            r'vốn đầu tư công[^.;]{0,50}(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ',
            r'vốn nhà nước[^.;]{0,50}(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ',
            r'trong đó[^.;]*vốn ngân sách[^.;]{0,50}(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ',
            r'trong đó[^.;]*đầu tư công[^.;]{0,50}(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ',
            # Format: số trước keyword
            r'(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ[^.;]{0,30}(?:vốn ngân sách|đầu tư công)',
        ]
        for pattern in public_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                parts = [match.group(1), match.group(2)]
                if match.lastindex >= 3 and match.group(3):
                    parts.append(match.group(3))
                result['public_investment'] = float(''.join(parts))
                break
        
        return result
    
    @classmethod
    def extract_budget_details(cls, text: str) -> Dict[str, Any]:
        """
        Extract budget revenue breakdown
        Returns: {
            'tax_revenue': float (tỷ VND),
            'non_tax_revenue': float (tỷ VND),
            'land_revenue': float (tỷ VND),
            'budget_target': float (tỷ VND),
            'execution_rate': float (%)
        }
        """
        result = {
            'tax_revenue': None,
            'non_tax_revenue': None,
            'land_revenue': None,
            'budget_target': None,
            'execution_rate': None
        }
        
        # Tax revenue (thu nội địa, thu thuế)
        tax_patterns = [
            r'thu nội địa[^.;]{0,50}?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ',
            r'trong đó[^.;]*thu nội địa[^.;]{0,50}?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ',
            r'thu thuế[^.;]{0,50}?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ',
            r'thu từ thuế[^.;]{0,50}?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ',
        ]
        for pattern in tax_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                parts = [match.group(1), match.group(2)]
                if match.lastindex >= 3 and match.group(3):
                    parts.append(match.group(3))
                result['tax_revenue'] = float(''.join(parts))
                break
        
        # Land revenue
        land_patterns = [
            r'thu từ đất.*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ',
            r'các khoản thu về đất.*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ',
        ]
        for pattern in land_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                parts = [match.group(1), match.group(2)]
                if match.lastindex >= 3 and match.group(3):
                    parts.append(match.group(3))
                result['land_revenue'] = float(''.join(parts))
                break
        
        # Budget target
        target_patterns = [
            r'dự toán.*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ',
            r'kế hoạch.*?ngân sách.*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ',
        ]
        for pattern in target_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                parts = [match.group(1), match.group(2)]
                if match.lastindex >= 3 and match.group(3):
                    parts.append(match.group(3))
                result['budget_target'] = float(''.join(parts))
                break
        
        # Execution rate
        exec_patterns = [
            r'đạt.*?(\d+[.,]\d+)\s*%.*?(?:dự toán|kế hoạch)',
            r'(\d+[.,]\d+)\s*%.*?dự toán',
        ]
        for pattern in exec_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['execution_rate'] = float(match.group(1).replace(',', '.'))
                break
        
        return result
    
    @classmethod
    def extract_cpi_details(cls, text: str) -> Dict[str, Any]:
        """
        Extract CPI component indices
        Returns: {
            'cpi_food': float (index),
            'cpi_housing': float (index),
            'cpi_transport': float (index),
            'cpi_education': float (index),
            'cpi_healthcare': float (index),
            'core_cpi': float (index),
            'inflation_rate': float (%)
        }
        """
        result = {
            'cpi_food': None,
            'cpi_housing': None,
            'cpi_transport': None,
            'cpi_education': None,
            'cpi_healthcare': None,
            'core_cpi': None,
            'inflation_rate': None
        }
        
        # Food CPI
        food_patterns = [
            r'(?:nhóm|chỉ số).*?lương thực.*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%',
            r'hàng ăn.*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%',
        ]
        for pattern in food_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                change = float(match.group(1).replace(',', '.'))
                if 'giảm' in match.group(0).lower():
                    change = -change
                result['cpi_food'] = 100 + change
                break
        
        # Housing CPI
        housing_patterns = [
            r'nhà ở.*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%',
            r'thuê nhà.*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%',
        ]
        for pattern in housing_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                change = float(match.group(1).replace(',', '.'))
                if 'giảm' in match.group(0).lower():
                    change = -change
                result['cpi_housing'] = 100 + change
                break
        
        # Transport CPI
        transport_patterns = [
            r'giao thông.*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%',
            r'vận chuyển.*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%',
        ]
        for pattern in transport_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                change = float(match.group(1).replace(',', '.'))
                if 'giảm' in match.group(0).lower():
                    change = -change
                result['cpi_transport'] = 100 + change
                break
        
        # Education CPI
        education_patterns = [
            r'giáo dục.*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%',
        ]
        for pattern in education_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                change = float(match.group(1).replace(',', '.'))
                if 'giảm' in match.group(0).lower():
                    change = -change
                result['cpi_education'] = 100 + change
                break
        
        # Healthcare CPI
        healthcare_patterns = [
            r'y tế.*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%',
            r'dược phẩm.*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%',
        ]
        for pattern in healthcare_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                change = float(match.group(1).replace(',', '.'))
                if 'giảm' in match.group(0).lower():
                    change = -change
                result['cpi_healthcare'] = 100 + change
                break
        
        # Core CPI
        core_patterns = [
            r'CPI cơ bản.*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%',
            r'lạm phát cơ bản.*?(\d+[.,]\d+)\s*%',
        ]
        for pattern in core_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                change = float(match.group(1).replace(',', '.'))
                if 'giảm' in match.group(0).lower():
                    change = -change
                result['core_cpi'] = 100 + change
                break
        
        # Inflation rate (same as change_yoy usually)
        inflation_patterns = [
            r'lạm phát.*?(\d+[.,]\d+)\s*%',
            r'tỷ lệ lạm phát.*?(\d+[.,]\d+)\s*%',
        ]
        for pattern in inflation_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['inflation_rate'] = float(match.group(1).replace(',', '.'))
                break
        
        return result
    
    @classmethod
    def extract_quarter(cls, text: str) -> Optional[int]:
        """Extract quarter từ text"""
        patterns = [
            (r'quý\s*I(?![IV])|quý\s*1\b', 1),
            (r'quý\s*II(?![IV])|quý\s*2\b', 2),
            (r'quý\s*III|quý\s*3\b', 3),
            (r'quý\s*IV|quý\s*4\b', 4),
        ]
        
        # Tìm tất cả quarters, lấy cái cuối cùng
        found = []
        for pattern, q in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                found.append((match.start(), q))
        
        if found:
            found.sort(key=lambda x: x[0])
            return found[-1][1]
        
        return None
    
    @classmethod
    def extract_for_indicator(cls, text: str, indicator_type: str, 
                             year: Optional[int] = None, month: Optional[int] = None, 
                             quarter: Optional[int] = None) -> Dict[str, Any]:
        """
        Extract tất cả values cho một indicator type cụ thể
        SỬ DỤNG PATTERNS CỤ THỂ cho từng loại chỉ số
        
        Returns:
            {
                'actual_value': float,
                'forecast_value': float,
                'change_yoy': float,
                'change_qoq': float,
                'change_mom': float,
                'change_prev_period': float,
                'source_texts': {'value': str, 'growth': str, 'qoq': str, 'mom': str, 'forecast': str},
                'quarter': int
            }
        """
        result = {
            'actual_value': None,
            'forecast_value': None,
            'change_yoy': None,
            'change_qoq': None,
            'change_mom': None,
            'change_prev_period': None,
            'source_texts': {},
            'quarter': quarter or None  # Use provided quarter or extract from text
        }
        
        # Extract quarter from text if not provided
        if result['quarter'] is None:
            result['quarter'] = cls.extract_quarter(text)
        
        # INDICATOR-SPECIFIC PATTERNS
        if indicator_type == 'iip':
            patterns = [
                # IIP là CHỈ SỐ (index), KHÔNG có giá trị tỷ đồng
                # Chỉ extract % tăng trưởng (growth)
                # GROWTH PATTERNS - avoid sub-sectors
                (r'\(IIP\)\s*(?!.*(?:chế biến|khai khoáng|điện)).*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%', 'growth'),
                (r'IIP(?!.*(?:ngành|phân ngành|khu vực))\s*(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%', 'growth'),
                (r'Chỉ số sản xuất công nghiệp\s*\(IIP\)(?!.*(?:chế biến|khai khoáng))\s*(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%', 'growth'),
                
                
                (r'(?:năm|cả năm).*?IIP.*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%', 'growth'),
                (r'IIP.*?(?:năm|cả năm).*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%', 'growth'),
                (r'chỉ số sản xuất công nghiệp.*?(?:năm \d{4}|cả năm).*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%', 'growth'),
                
                
                (r'[Qq]uý [IVX1-4].*?IIP.*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%', 'growth'),
                (r'IIP.*?[Qq]uý [IVX1-4].*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%', 'growth'),
                (r'(?:3|6|9) tháng đầu năm.*?IIP.*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%', 'growth'),
                
                
                (r'tháng \d+.*?IIP.*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%', 'growth'),
                (r'IIP.*?tháng [^,]+.*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%', 'growth'),
                
                
                (r'IIP.*?(?:đạt|ước đạt|thực hiện).*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%', 'growth'),
                (r'chỉ số.*?công nghiệp.*?(?:tăng trưởng|tăng)\s+(\d+[.,]\d+)\s*%', 'growth'),
                
                
                (r'chỉ số sản xuất công nghiệp.*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%', 'growth'),
            ]
            
        elif indicator_type == 'retail':
            patterns = [
                # Priority: avoid month breakdown and specific sectors
                (r'(?:năm \d{4}|cả năm|Năm \d{4})(?!.*tháng (?:Một|Hai|Ba|Tư|Năm|Sáu|Bảy|Tám|Chín|Mười)).*?[Tt]ổng mức bán lẻ(?!.*(?:xăng dầu|lưu trú|ăn uống)).*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
                (r'[Tt]ổng mức bán lẻ(?!.*(?:xăng|lưu trú)).*?(?:năm \d{4}|cả năm|Năm \d{4})(?!.*tháng (?:Một|Hai)).*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
                (r'[Tt]ổng mức bán lẻ hàng hóa và doanh thu dịch vụ(?!.*(?:lưu trú|xăng)).*?năm \d{4}.*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
                (r'năm \d{4}.*?[Tt]ổng mức bán lẻ hàng hóa, dịch vụ(?!.*tháng).*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
                
                
                (r'[Qq]uý [IVX1-4].*?[Tt]ổng mức bán lẻ.*?(\d{1,2})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
                (r'[Tt]ổng mức bán lẻ.*?[Qq]uý [IVX1-4].*?(\d{1,2})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
                (r'(?:3|6|9) tháng đầu năm.*?[Tt]ổng mức bán lẻ.*?(\d{1,2})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
                (r'[Tt]ổng mức bán lẻ.*?(?:3|6|9) tháng.*?(\d{1,2})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
                
                
                (r'[Tt]ổng mức bán lẻ.*?(?:đạt|ước đạt|đạt được).*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
                (r'(?:đạt|ước đạt).*?[Tt]ổng mức bán lẻ.*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
                (r'[Tt]ổng mức bán lẻ hàng hóa, dịch vụ.*?(?:đạt|ước).*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
                
                
                (r'[Tt]ổng mức bán lẻ hàng hóa và doanh thu dịch vụ(?!.*tháng Một|tháng Hai|tháng Ba).*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
                (r'[Tt]ổng mức bán lẻ hàng hoá, dịch vụ tiêu dùng.*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
                
                
                (r'[Tt]ổng mức bán lẻ(?!.*tháng (?:Một|Hai|Ba|Tư|Năm|Sáu|Bảy|Tám|Chín|Mười)).*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
                
                
                # Growth patterns - thêm variations
                (r'[Tt]ổng mức bán lẻ[^.;]*(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%', 'growth'),
                (r'[Bb]án lẻ hàng hóa[^.;]*(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%', 'growth'),
                (r'[Tt]ổng mức bán lẻ.*?tăng trưởng.*?(\d+[.,]\d+)\s*%', 'growth'),
                (r'(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%[^.;]*[Tt]ổng mức bán lẻ', 'growth'),
            ]
            
        elif indicator_type == 'budget':
            patterns = [
                # Priority: Tổng thu or Thu trên địa bàn, avoid specific revenue sources
                (r'[Tt]hu ngân sách trên địa bàn(?!.*(?:thu từ|khu vực|nội địa))[^.;]{0,50}(?:đạt|ước đạt)[^.;]{0,30}(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
                (r'[Tt]ổng thu ngân sách(?!.*(?:thu từ|thu thuế môn bài))[^.;]{0,50}(?:đạt|ước)[^.;]{0,30}(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
                (r'[Tt]hu ngân sách nhà nước(?!.*(?:thu từ|thu nội))[^.;]{0,50}(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
                (r'[Tt]hu ngân sách(?!.*(?:thu từ khu vực|thu nội địa|thu thuế môn))[^.;]{0,50}(?:đạt|ước đạt|thực hiện)[^.;]{0,30}(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
                
                # Alternative: số đứng trước
                (r'(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ[^.;]{0,40}thu ngân sách(?!.*thu nội địa)', 'value_split'),
                
                
                (r'(?:năm|cả năm)[^.;]{0,40}[Tt]hu ngân sách[^.;]{0,30}(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
                (r'[Qq]uý [IVX1-4].*?thu ngân sách.*?(\d{1,2})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
                (r'(?:3|6|9) tháng.*?thu ngân sách.*?(\d{1,2})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
                
                
                (r'(?:đạt|ước đạt).*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ.*?thu ngân sách', 'value_split'),
                (r'(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ.*?thu ngân sách(?!.*thu thuế môn bài)', 'value_split'),
                
                
                (r'[Tt]hu ngân sách.*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%', 'growth'),
                (r'(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%.*?thu ngân sách', 'growth'),
                (r'[Tt]hu ngân sách.*?tăng trưởng.*?(\d+[.,]\d+)\s*%', 'growth'),
            ]
            
        elif indicator_type == 'cpi':
            patterns = [
                # Pattern chính: CPI + tăng X% -> index = 100 + X
                (r'(?:CPI|chỉ số giá tiêu dùng|chỉ số giá).*?tăng\s+(\d+)[,.](\d+)\s*%', 'cpi_growth_split'),
                (r'(?:CPI|chỉ số giá).*?bình quân.*?tăng\s+(\d+)[,.](\d+)\s*%', 'cpi_growth_split'),
                # Pattern phụ: CPI đạt 106.33 -> index = 106.33
                (r'(?:CPI|chỉ số giá).*?đạt\s+(\d+)[,.](\d+)', 'cpi_value_split'),
            ]
            
        elif indicator_type == 'agri':
            patterns = [
                # AGRI trong báo cáo tổng hợp thường chỉ có % tăng trưởng
                # Value patterns chỉ match khi có keyword "giá trị" rõ ràng
                (r'[Gg]iá trị sản xuất nông nghiệp(?!.*(?:tạ/ha|tấn))[^.;]+(\d{1,3})[.,](\d{3})\s*tỷ\s*(?:đồng|VND)?', 'value_split'),
                (r'[Nn]ông, lâm nghiệp và thủy sản[^.;]+giá trị(?!.*(?:tạ|tấn|ha))[^.;]+(\d{1,3})[.,](\d{3})\s*tỷ', 'value_split'),
                (r'[Ss]ản xuất nông nghiệp[^.;]+giá trị[^.;]+(\d{1,3})[.,](\d{3})\s*tỷ\s*(?:đồng|VND)', 'value_split'),
                
                # Growth patterns - avoid năng suất, sản lượng, diện tích
                (r'[Gg]iá trị sản xuất nông nghiệp(?!.*(?:năng suất|sản lượng|diện tích)).*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%', 'growth'),
                (r'[Nn]ông, lâm nghiệp và thủy sản(?!.*(?:diện tích|sản lượng|năng suất|tạ|tấn)).*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%', 'growth'),
                (r'[Nn]ông nghiệp.*?tăng trưởng(?!.*(?:diện tích|năng suất)).*?(\d+[.,]\d+)\s*%', 'growth'),
                
                
                (r'(?:năm|cả năm).*?nông nghiệp.*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%', 'growth'),
                (r'[Qq]uý [IVX1-4].*?nông.*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%', 'growth'),
            ]
            
        elif indicator_type == 'investment':
            patterns = [
                # Priority: Tổng vốn đầu tư toàn xã hội or phát triển toàn xã hội
                (r'[Tt]ổng vốn đầu tư (?:phát triển )?toàn xã hội(?!.*FDI).*?(?:đạt|ước đạt|ước).*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
                (r'[Tt]ổng vốn đầu tư phát triển(?!.*FDI).*?(?:đạt|ước đạt|đạt được).*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
                (r'[Tt]ổng vốn đầu tư(?!.*(?:FDI|của|doanh nghiệp)).*?(?:đạt|ước).*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
                (r'(?:đạt|ước đạt).*?[Tt]ổng vốn đầu tư(?!.*FDI).*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ', 'value_split'),
                (r'[Vv]ốn đầu tư phát triển toàn xã hội.*?(\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?\s*tỷ\s*(?:đồng|VND)', 'value_split'),
                
                
                (r'(?:năm|cả năm).*?[Tt]ổng vốn đầu tư.*?(\d{1,3})[.,](\d{3})\s*tỷ', 'value_split'),
                (r'[Qq]uý [IVX1-4].*?vốn đầu tư.*?(\d{1,3})[.,](\d{3})\s*tỷ', 'value_split'),
                (r'(?:3|6|9) tháng.*?vốn đầu tư.*?(\d{1,3})[.,](\d{3})\s*tỷ', 'value_split'),
                
                
                (r'[Ff]DI.*?(?:đạt|ước).*?(\d+[.,]\d+)\s*(?:tỷ\s*USD|triệu\s*USD)', 'value_usd'),
                (r'[Vv]ốn đầu tư nước ngoài.*?(\d+[.,]\d+)\s*(?:tỷ|triệu)\s*(?:USD|đô)', 'value_usd'),
                (r'[Vv]ốn đăng ký.*?FDI.*?(\d+[.,]\d+)\s*triệu\s*USD', 'value_usd'),
                
                
                (r'[Tt]ổng vốn đầu tư.*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%', 'growth'),
                (r'[Vv]ốn đầu tư.*?tăng trưởng.*?(\d+[.,]\d+)\s*%', 'growth'),
                (r'(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%.*?vốn đầu tư', 'growth'),
            ]
            
        elif indicator_type == 'export':
            patterns = [
                
                (r'[Kk]im ngạch xuất khẩu.*?(?:đạt|ước đạt).*?(\d+[.,]\d+)\s*triệu\s*USD', 'value_usd'),
                (r'[Xx]uất khẩu.*?(?:đạt|ước).*?(\d+[.,]\d+)\s*triệu\s*(?:USD|đô)', 'value_usd'),
                (r'[Gg]iá trị xuất khẩu.*?(\d+[.,]\d+)\s*triệu\s*USD', 'value_usd'),
                (r'[Tt]ổng kim ngạch.*?(\d+[.,]\d+)\s*triệu\s*USD', 'value_usd'),
                
                
                (r'(?:năm|cả năm).*?xuất khẩu.*?(\d+[.,]\d+)\s*triệu', 'value_usd'),
                (r'[Qq]uý [IVX1-4].*?xuất khẩu.*?(\d+[.,]\d+)\s*triệu', 'value_usd'),
                
                
                (r'[Xx]uất khẩu.*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%', 'growth'),
                (r'[Kk]im ngạch.*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%', 'growth'),
            ]
            
        elif indicator_type == 'grdp':
            patterns = [
                
                (r'GRDP.*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%', 'growth'),
                (r'[Tt]ổng sản phẩm.*?địa bàn.*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%', 'growth'),
                (r'[Tt]ăng trưởng.*?GRDP.*?(\d+[.,]\d+)\s*%', 'growth'),
                (r'GRDP.*?tăng trưởng.*?(\d+[.,]\d+)\s*%', 'growth'),
                
                
                (r'GRDP.*?(?:đạt|ước).*?(\d{1,3})[.,](\d{3})\s*tỷ', 'value_split'),
                (r'[Tt]ổng sản phẩm.*?(\d{1,3})[.,](\d{3})\s*tỷ', 'value_split'),
                (r'(?:đạt|ước đạt).*?GRDP.*?(\d{1,3})[.,](\d{3})\s*tỷ', 'value_split'),
                
                
                (r'(?:năm|cả năm).*?GRDP.*?(?:tăng|giảm)\s+(\d+[.,]\d+)\s*%', 'growth'),
            ]
        else:
            patterns = []
        
        # Apply patterns
        for idx, (pattern, ptype) in enumerate(patterns):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Check for anti-patterns before accepting the value
                matched_text = match.group(0)
                if ValueRangeValidator.has_anti_pattern(indicator_type, matched_text):
                    logger.debug(f"    Pattern {idx+1} SKIPPED (anti-pattern detected): {matched_text[:60]}")
                    continue
                
                logger.debug(f"    Pattern {idx+1} matched ({ptype}): {matched_text[:60]}")
                try:
                    if ptype == 'value_split':
                        # Giá trị: "129.305" -> 129305, "12.109" -> 12109, "29.951" -> 29951
                        # Pattern: (\d{1,3})[.,](\d{3})(?:[.,](\d{3}))?
                        # Group 1: first part (1-3 digits)
                        # Group 2: second part (3 digits)
                        # Group 3: optional third part (3 digits)
                        parts = [match.group(1), match.group(2)]
                        if match.lastindex >= 3 and match.group(3):
                            parts.append(match.group(3))
                        value = float(''.join(parts))
                        result['actual_value'] = value
                        result['source_texts']['value'] = match.group(0)
                    elif ptype == 'value':
                        value = float(match.group(1).replace(',', '.'))
                        result['actual_value'] = value
                        result['source_texts']['value'] = match.group(0)
                    elif ptype == 'value_usd':
                        value = float(match.group(1).replace(',', '.'))
                        result['actual_value'] = value
                        result['source_texts']['value'] = match.group(0)
                    elif ptype == 'growth':
                        # Check tăng/giảm
                        if 'giảm' in match.group(0).lower():
                            growth = -float(match.group(1).replace(',', '.'))
                        else:
                            growth = float(match.group(1).replace(',', '.'))
                        result['change_yoy'] = growth
                        result['source_texts']['growth'] = match.group(0)
                    elif ptype == 'cpi_growth':
                        # CPI: convert growth to index (100 + growth)
                        growth = float(match.group(1).replace(',', '.'))
                        result['actual_value'] = 100 + growth
                        result['change_yoy'] = growth
                        result['source_texts']['value'] = match.group(0)
                    elif ptype == 'cpi_growth_split':
                        # CPI: "tăng 6,33%" -> index = 106.33
                        growth = float(f"{match.group(1)}.{match.group(2)}")
                        result['actual_value'] = 100 + growth
                        result['change_yoy'] = growth
                        result['source_texts']['value'] = match.group(0)
                    elif ptype == 'cpi_value_split':
                        # CPI: "đạt 106,33" -> index = 106.33
                        value = float(f"{match.group(1)}.{match.group(2)}")
                        result['actual_value'] = value
                        result['source_texts']['value'] = match.group(0)
                except Exception as e:
                    logger.warning(f"Pattern parse error: {e}")
                    continue
        
        if not result['actual_value'] and not result['change_yoy']:
            if indicator_type == 'cpi':
                value, source = cls.extract_cpi(text)
                result['actual_value'] = value
                result['source_texts']['value'] = source
            elif indicator_type in ['export', 'investment']:
                value, source = cls.extract_value_usd(text)
                result['actual_value'] = value
                result['source_texts']['value'] = source
            elif indicator_type not in ['iip', 'agri']:
                # SKIP fallback extraction cho IIP (chỉ số không có giá trị tuyệt đối)
                # và AGRI (dễ match nhầm sang indicator khác)
                value, source = cls.extract_value_vnd(text)
                result['actual_value'] = value
                result['source_texts']['value'] = source
            
            # Extract growth
            if not result['change_yoy']:
                growth, source = cls.extract_growth(text)
                result['change_yoy'] = growth
                result['source_texts']['growth'] = source
        
        # Extract QoQ growth (quarter-over-quarter)
        if not result['change_qoq']:
            qoq_growth, source = cls.extract_qoq_growth(text)
            result['change_qoq'] = qoq_growth
            result['source_texts']['qoq'] = source
        
        # Extract MoM growth (month-over-month)
        if not result['change_mom']:
            mom_growth, source = cls.extract_mom_growth(text)
            result['change_mom'] = mom_growth
            result['source_texts']['mom'] = source
        
        # Extract forecast value
        # SKIP forecast cho IIP (chỉ số không có forecast) và AGRI (thường không có trong báo cáo tổng hợp)
        if not result['forecast_value'] and indicator_type not in ['iip', 'agri']:
            forecast, source = cls.extract_forecast(text)
            result['forecast_value'] = forecast
            result['source_texts']['forecast'] = source
        
        # Set change_prev_period: use MoM if available, else QoQ
        if result['change_mom'] is not None:
            result['change_prev_period'] = result['change_mom']
        elif result['change_qoq'] is not None:
            result['change_prev_period'] = result['change_qoq']
        
        # =====================================================================
        # EXTRACT SPECIFIC FIELDS for each indicator type
        # =====================================================================
        
        if indicator_type == 'retail':
            breakdown = cls.extract_retail_breakdown(text)
            result.update(breakdown)
        
        elif indicator_type == 'export':
            export_details = cls.extract_export_details(text)
            result.update(export_details)
        
        elif indicator_type == 'investment':
            investment_details = cls.extract_investment_details(text)
            result.update(investment_details)
        
        elif indicator_type == 'budget':
            budget_details = cls.extract_budget_details(text)
            result.update(budget_details)
        
        elif indicator_type == 'cpi':
            cpi_details = cls.extract_cpi_details(text)
            result.update(cpi_details)
        
        return result


# =============================================================================
# STEP 7: ARTICLE CRAWLER - Fetch content từ URL
# =============================================================================

class ArticleCrawler:
    """Crawl nội dung bài viết"""
    
    BASE_URL = "https://thongkehungyen.nso.gov.vn"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.session.verify = False
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    def get_article_list(self, max_pages: int = 5) -> List[Dict[str, str]]:
        """
        Lấy danh sách bài viết từ nhiều trang
        
        Returns:
            List of {title, url, date, summary}
        """
        # Use dict to deduplicate by URL, keeping longest title
        articles_dict = {}
        
        for page in range(1, max_pages + 1):
            url = f"{self.BASE_URL}/tinh-hinh-kinh-te-xa-hoi?page={page}"
            logger.info(f"Crawling page {page}: {url}")
            
            try:
                resp = self.session.get(url, timeout=60)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.content, 'html.parser')
                
                # Tìm các bài viết (adjust selector dựa vào cấu trúc thực tế)
                article_items = soup.select('.article-item, .news-item, .post-item')
                
                if not article_items:
                    article_items = soup.find_all('a', href=re.compile(r'/tinh-hinh'))
                
                logger.info(f"   Found {len(article_items)} potential items on page {page}")
                
                for item in article_items:
                    try:
                        if item.name == 'a':
                            link = item
                            title = item.get_text(strip=True)
                        else:
                            link = item.find('a')
                            title = link.get_text(strip=True) if link else ""
                        
                        if not link:
                            continue
                        
                        href = link.get('href', '')
                        if not href.startswith('http'):
                            href = self.BASE_URL + href
                        
                        # Skip pagination links by title
                        if title in ['<', '>', '<<', '>>', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10']:
                            continue
                        
                        # Deduplicate: keep longest title for each URL
                        if href in articles_dict:
                            if len(title) > len(articles_dict[href]['title']):
                                articles_dict[href]['title'] = title
                                logger.debug(f"   Updated article title: {title[:50]}... -> {href}")
                        else:
                            # Extract date if available
                            date_elem = item.find(class_=re.compile(r'date|time'))
                            date_str = date_elem.get_text(strip=True) if date_elem else ""
                            
                            # Extract summary if available
                            summary_elem = item.find(class_=re.compile(r'summary|description|excerpt'))
                            summary = summary_elem.get_text(strip=True) if summary_elem else ""
                            
                            articles_dict[href] = {
                                'title': title,
                                'url': href,
                                'date': date_str,
                                'summary': summary
                            }
                            logger.debug(f"   Found article: {title[:50] if title else '(no title)'}... -> {href}")
                        
                    except Exception as e:
                        logger.warning(f"   Error parsing article item: {e}")
                        continue
                
            except Exception as e:
                logger.error(f"Error crawling page {page}: {e}")
                continue
        
        # Filter out articles with short titles (likely pagination or invalid)
        articles = [
            art for art in articles_dict.values()
            if art['title'] and len(art['title']) >= 10
        ]
        
        logger.info(f"Total unique articles found: {len(articles)} (after dedup and filter)")
        return articles
    
    def get_article_content(self, url: str, retries: int = 2) -> Optional[str]:
        """Fetch và extract nội dung bài viết với retry logic"""
        for attempt in range(retries):
            try:
                resp = self.session.get(url, timeout=60)
                resp.raise_for_status()
                break
            except requests.exceptions.Timeout:
                if attempt < retries - 1:
                    logger.warning(f"Timeout attempt {attempt + 1}/{retries}, retrying...")
                    continue
                else:
                    logger.error(f"All {retries} attempts timed out for {url}")
                    return None
            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
                return None
        
        try:
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Remove navigation elements
            for element in soup.find_all(['nav', 'header', 'footer', 'aside']):
                element.decompose()
            for element in soup.find_all(class_=re.compile(r'menu|nav|header|footer|sidebar')):
                element.decompose()
            
            # Find main content
            content = None
            selectors = [
                ('div', re.compile(r'article-content|post-content|entry-content|main-content')),
                ('article', None),
                ('main', None),
            ]
            
            for tag, attrs in selectors:
                if attrs:
                    content = soup.find(tag, class_=attrs)
                else:
                    content = soup.find(tag)
                
                if content:
                    text = content.get_text(separator='\n', strip=True)
                    if len(text) > 200:
                        return TextNormalizer.normalize(text)
            
            paragraphs = soup.find_all('p')
            if paragraphs:
                text = '\n'.join(p.get_text(strip=True) for p in paragraphs)
                if len(text) > 200:
                    return TextNormalizer.normalize(text)
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None


# =============================================================================
# STEP 8: MAIN EXTRACTOR - Production Pipeline
# =============================================================================

class UniversalEconomicExtractor:
    """
    Production-grade Economic Data Extractor
    
    Pipeline:
        1. Fetch content (ArticleCrawler)
        2. Normalize text (TextNormalizer)
        3. Detect candidates (IndicatorDictionary)
        4. Confirm with LLM (LLMClassifier) - ONLY classification
        5. Extract values (ValueExtractor) - REGEX ONLY
        6. Validate (Pydantic + ValueRangeValidator)
        7. Save to DB
    """
    
    MODEL_MAP = {
        'grdp': GRDPDetail,
        'iip': IIPDetail,
        'agri': AgriProductionDetail,
        'retail': RetailServicesDetail,
        'export': ExportDetail,
        'investment': InvestmentDetail,
        'budget': BudgetRevenueDetail,
        'cpi': CPIDetail
    }
    
    def __init__(self, db: Session, use_llm: bool = True):
        self.db = db
        self.crawler = ArticleCrawler()
        self.classifier = LLMClassifier() if use_llm else None
        self.use_llm = use_llm
    
    def extract_and_save(
        self,
        text: str,
        indicator_types: List[str],
        source_url: str,
        year: int = 2025,
        month: Optional[int] = None,
        quarter: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Extract và save dữ liệu theo pipeline chuẩn
        
        Returns:
            {indicator_type: {success: bool, data: {...}, validation: {...}}}
        """
        results = {}
        
        # Step 1: Normalize text
        text = TextNormalizer.normalize(text)
        logger.info(f"Normalized text: {len(text)} chars")
        
        # Step 2: Detect candidates bằng dictionary
        candidates = IndicatorDictionary.detect_candidates(text)
        logger.info(f"Dictionary detected {len(candidates)} candidates: {list(candidates.keys())}")
        
        # Step 3: Process each requested indicator
        for indicator_type in indicator_types:
            try:
                # Skip if not in candidates (no keyword match)
                if indicator_type not in candidates:
                    logger.info(f"Skipping {indicator_type.upper()} - no keyword match")
                    results[indicator_type] = {
                        'success': False,
                        'skipped': True,
                        'reason': 'No keyword match in text'
                    }
                    continue
                
                # Skip GRDP temporarily
                if indicator_type == 'grdp':
                    logger.info(f"Skipping GRDP (preserving existing data)")
                    results[indicator_type] = {
                        'success': False,
                        'skipped': True,
                        'reason': 'Skipped to preserve existing data'
                    }
                    continue
                
                logger.info(f"Processing {indicator_type.upper()}...")
                
                contexts = IndicatorDictionary.find_keyword_context(text, indicator_type, year=year)
                if not contexts:
                    results[indicator_type] = {
                        'success': False,
                        'error': 'No context found for keywords'
                    }
                    continue
                
                best_context = contexts[0]
                
                if indicator_type in ['budget', 'retail']:
                    # Try to find clean section after summary keyword
                    summary_keywords = {
                        'budget': ['thu ngân sách nhà nước', 'Tổng thu ngân sách'],
                        'retail': ['Tổng mức bán lẻ hàng hóa']
                    }
                    
                    for summary_kw in summary_keywords.get(indicator_type, []):
                        match = re.search(re.escape(summary_kw), best_context, re.IGNORECASE)
                        if match:
                            start_pos = match.start()
                            clean_context = best_context[start_pos:start_pos + 500]
                            logger.debug(f"   Using clean context from '{summary_kw}': {clean_context[:100]}")
                            best_context = clean_context
                            break
                
                if self.classifier and self.use_llm:
                    confirmation = self.classifier.confirm_indicator(best_context, indicator_type)
                    logger.info(f"   LLM confirm: {confirmation['confirm']} (conf: {confirmation['confidence']:.2f})")
                    
                    if not confirmation['confirm'] and confirmation['confidence'] > 0.8:
                        logger.info(f"   LLM rejected {indicator_type.upper()}: {confirmation['reasoning']}")
                        results[indicator_type] = {
                            'success': False,
                            'rejected_by_llm': True,
                            'reason': confirmation['reasoning']
                        }
                        continue
                else:
                    confirmation = {'confirm': True, 'confidence': 0.7}
                
                # Step 6: Extract values using REGEX ONLY
                logger.debug(f"   Best context (first 200 chars): {best_context[:200]}")
                
                extracted = ValueExtractor.extract_for_indicator(
                    text=best_context,
                    indicator_type=indicator_type,
                    year=year,
                    month=month,
                    quarter=quarter
                )
                logger.info(f"   Regex extracted: value={extracted['actual_value']}, yoy={extracted['change_yoy']}")
                
                if not extracted['actual_value'] and not extracted['change_yoy']:
                    # KHÔNG retry với full text cho IIP (chỉ số) và AGRI (dễ nhầm indicator khác)
                    if indicator_type not in ['iip', 'agri']:
                        logger.info(f"   Context empty, trying full text...")
                        extracted = ValueExtractor.extract_for_indicator(
                            text=text,
                            indicator_type=indicator_type,
                            year=year,
                            month=month,
                            quarter=quarter
                        )
                        logger.info(f"   Full text extracted: value={extracted['actual_value']}, yoy={extracted['change_yoy']}")
                    else:
                        logger.info(f"   Skip full text retry for {indicator_type} (growth-only indicator)")
                
                if not extracted['actual_value'] and not extracted['change_yoy']:
                    results[indicator_type] = {
                        'success': False,
                        'error': 'No numeric values found by regex'
                    }
                    continue
                
                # Step 7: Build data object
                extracted_quarter = extracted['quarter']
                # Use parameters from function if provided, otherwise use extracted
                final_month = month
                final_quarter = quarter if quarter else extracted_quarter
                
                if final_month:
                    period_type = 'month'
                elif final_quarter:
                    period_type = 'quarter'
                else:
                    period_type = 'year'
                
                # Base data (common for all indicators)
                data = {
                    'province': 'Hưng Yên',
                    'year': year,
                    'month': final_month,
                    'quarter': final_quarter,
                    'period_type': period_type,
                    'data_status': 'official',
                    'actual_value': extracted.get('actual_value'),
                    'forecast_value': extracted.get('forecast_value'),
                    'change_yoy': extracted.get('change_yoy'),
                    'change_qoq': extracted.get('change_qoq'),
                    'change_mom': extracted.get('change_mom'),
                    'change_prev_period': extracted.get('change_prev_period'),
                    'last_updated': self._calculate_timestamp(year, final_month, final_quarter),
                    'data_source': source_url
                }
                
                # Add indicator-specific fields
                if indicator_type == 'retail':
                    data['retail_value'] = extracted.get('retail_value')
                    data['services_value'] = extracted.get('services_value')
                
                elif indicator_type == 'export':
                    data['export_usd'] = extracted.get('export_usd')
                    data['export_vnd'] = extracted.get('export_vnd')
                    data['top_products'] = extracted.get('top_products')
                    data['top_markets'] = extracted.get('top_markets')
                
                elif indicator_type == 'investment':
                    data['fdi_registered'] = extracted.get('fdi_registered')
                    data['fdi_disbursed'] = extracted.get('fdi_disbursed')
                    data['fdi_projects_new'] = extracted.get('fdi_projects_new')
                    data['fdi_projects_expanded'] = extracted.get('fdi_projects_expanded')
                    data['ddi_value'] = extracted.get('ddi_value')
                    data['public_investment'] = extracted.get('public_investment')
                
                elif indicator_type == 'budget':
                    data['tax_revenue'] = extracted.get('tax_revenue')
                    data['non_tax_revenue'] = extracted.get('non_tax_revenue')
                    data['land_revenue'] = extracted.get('land_revenue')
                    data['budget_target'] = extracted.get('budget_target')
                    data['execution_rate'] = extracted.get('execution_rate')
                
                elif indicator_type == 'cpi':
                    data['cpi_food'] = extracted.get('cpi_food')
                    data['cpi_housing'] = extracted.get('cpi_housing')
                    data['cpi_transport'] = extracted.get('cpi_transport')
                    data['cpi_education'] = extracted.get('cpi_education')
                    data['cpi_healthcare'] = extracted.get('cpi_healthcare')
                    data['core_cpi'] = extracted.get('core_cpi')
                    data['inflation_rate'] = extracted.get('inflation_rate')
                
                # Add source text for audit
                source_texts = extracted.get('source_texts', {})
                
                # Step 8: Validate
                validation_errors = []
                
                # 8a: Value range validation
                if extracted['actual_value']:
                    is_annual = period_type == 'year'
                    is_valid, error_msg = ValueRangeValidator.validate(
                        indicator_type, 
                        extracted['actual_value'],
                        is_annual=is_annual
                    )
                    if not is_valid:
                        validation_errors.append(error_msg)
                
                # 8b: YoY validation
                if extracted['change_yoy'] and abs(extracted['change_yoy']) > 100:
                    validation_errors.append(f"YoY {extracted['change_yoy']}% không hợp lý")
                
                if validation_errors:
                    logger.warning(f"   Validation failed: {validation_errors}")
                    results[indicator_type] = {
                        'success': False,
                        'error': 'Validation failed',
                        'validation_errors': validation_errors,
                        'data': data,
                        'source_texts': source_texts
                    }
                    continue
                
                # Step 9: Save to database
                record = self._save_to_db(indicator_type, data, source_url)
                
                results[indicator_type] = {
                    'success': True,
                    'record': self._record_to_dict(record),
                    'data': data,
                    'source_texts': source_texts,
                    'llm_confirmation': confirmation
                }
                logger.info(f"   Saved {indicator_type.upper()} (id={record.id})")
                
            except Exception as e:
                logger.error(f"   Error processing {indicator_type}: {e}")
                results[indicator_type] = {
                    'success': False,
                    'error': str(e)
                }
        
        return results
    
    def _calculate_timestamp(self, year: int, month: Optional[int] = None, 
                            quarter: Optional[int] = None) -> datetime:
        """Calculate data timestamp (end of period)"""
        if month:
            # End of month
            if month == 12:
                return datetime(year, 12, 31)
            else:
                next_month = month + 1
                return datetime(year, next_month, 1) - timedelta(days=1)
        elif quarter == 1:
            return datetime(year, 3, 31)
        elif quarter == 2:
            return datetime(year, 6, 30)
        elif quarter == 3:
            return datetime(year, 9, 30)
        elif quarter == 4:
            return datetime(year, 12, 31)
        else:
            return datetime(year, 12, 31)
    
    def _save_to_db(self, indicator_type: str, data: Dict, source_url: str) -> Any:
        """Save data to appropriate table"""
        model_class = self.MODEL_MAP.get(indicator_type)
        if not model_class:
            raise ValueError(f"Unknown indicator type: {indicator_type}")
        
        data['data_source'] = source_url
        
        # Check for existing record (including data_source for uniqueness)
        query = self.db.query(model_class).filter(
            model_class.province == data['province'],
            model_class.year == data['year'],
            model_class.data_source == source_url
        )
        
        if data.get('quarter'):
            query = query.filter(model_class.quarter == data['quarter'])
        else:
            query = query.filter(model_class.quarter.is_(None))
        
        if data.get('month'):
            query = query.filter(model_class.month == data['month'])
        else:
            query = query.filter(model_class.month.is_(None))
        
        existing = query.first()
        
        if existing:
            # Update existing
            for key, value in data.items():
                if hasattr(existing, key) and value is not None:
                    setattr(existing, key, value)
            self.db.commit()
            self.db.refresh(existing)
            logger.info(f"   Updated existing record id={existing.id}")
            return existing
        else:
            # Create new
            record = model_class(**data)
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            logger.info(f"   Created new record id={record.id}")
            return record
    
    def _record_to_dict(self, record) -> Dict:
        """Convert SQLAlchemy record to dict"""
        return {c.name: getattr(record, c.name) for c in record.__table__.columns}


# =============================================================================
# STEP 9: LEGACY COMPATIBILITY - Wrapper for old API
# =============================================================================

class EconomicLLMExtractor:
    """
    DEPRECATED: Legacy wrapper for backward compatibility
    Use UniversalEconomicExtractor instead
    """
    
    def __init__(self):
        logger.warning("EconomicLLMExtractor is DEPRECATED. Use UniversalEconomicExtractor instead.")
        self.classifier = LLMClassifier()
        self.llm = self.classifier.llm
    
    def analyze_all_indicators(self, text: str, year: int) -> Dict[str, Any]:
        """Legacy method - now uses dictionary + regex"""
        candidates = IndicatorDictionary.detect_candidates(text)
        
        indicators = []
        for ind_type in candidates.keys():
            contexts = IndicatorDictionary.find_keyword_context(text, ind_type)
            if contexts:
                extracted = ValueExtractor.extract_for_indicator(contexts[0], ind_type)
                
                if extracted['actual_value'] or extracted['change_yoy']:
                    indicators.append({
                        'type': ind_type,
                        'confidence': 0.9,
                        'year': year,
                        'quarter': extracted['quarter'],
                        'actual_value': extracted['actual_value'],
                        'change_yoy': extracted['change_yoy'],
                        'source_text': extracted.get('source_texts', {}).get('value', '')
                    })
        
        return {'indicators': indicators}


# =============================================================================
# UTILITY CLASS - IndicatorClassifier (legacy)
# =============================================================================

class IndicatorClassifier:
    """Legacy classifier - use IndicatorDictionary instead"""
    
    PATTERNS = IndicatorDictionary.KEYWORDS
    
    @classmethod
    def classify(cls, text: str) -> List[str]:
        """Legacy method"""
        candidates = IndicatorDictionary.detect_candidates(text)
        return list(candidates.keys())
