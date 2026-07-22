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
from datetime import datetime
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
        'iip': (1000, 15000, 'tỷ VND', 'Chỉ số sản xuất công nghiệp'),
        'agri': (2000, 25000, 'tỷ VND', 'Sản xuất nông nghiệp'),
        'retail': (10000, 150000, 'tỷ VND', 'Bán lẻ hàng hóa dịch vụ'),
        'export': (50, 1000, 'triệu USD', 'Kim ngạch xuất khẩu'),
        'investment': (50, 2000, 'triệu USD', 'Vốn đầu tư'),
        'budget': (2000, 50000, 'tỷ VND', 'Thu ngân sách'),
        'cpi': (95, 120, 'index', 'Chỉ số giá tiêu dùng')
    }
    
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
        
        # Nếu là dữ liệu năm, mở rộng range (x4 cho quarterly indicators)
        if is_annual and indicator_type not in ['cpi', 'grdp']:
            max_val = max_val * 4
        
        if not (min_val <= value <= max_val):
            return False, (
                f" {indicator_type.upper()} = {value:,.0f} {unit} "
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
            'xuất khẩu', 'kim ngạch xuất khẩu', 'hàng hóa xuất khẩu',
            'giá trị xuất khẩu', 'xuất khẩu đạt'
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
    def find_keyword_context(cls, text: str, indicator_type: str, context_chars: int = 300) -> List[str]:
        """
        Tìm context (đoạn văn) xung quanh keyword
        
        Returns:
            List of context strings containing the keyword
        """
        keywords = cls.KEYWORDS.get(indicator_type, [])
        contexts = []
        
        for keyword in keywords:
            for match in re.finditer(re.escape(keyword), text, re.IGNORECASE):
                start = max(0, match.start() - context_chars)
                end = min(len(text), match.end() + context_chars)
                context = text[start:end]
                contexts.append(context)
        
        return contexts


# =============================================================================
# STEP 5: LLM CLASSIFIER - CHỈ làm YES/NO classification
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
                    openai_api_key=api_key,
                    base_url="https://openrouter.ai/api/v1"
                )
                logger.info(" LLM Classifier initialized (classification only)")
    
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
"{context_text[:500]}"

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
# STEP 6: VALUE EXTRACTOR - REGEX ONLY, KHÔNG dùng LLM
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
    def extract_for_indicator(cls, text: str, indicator_type: str) -> Dict[str, Any]:
        """
        Extract tất cả values cho một indicator type cụ thể
        
        Returns:
            {
                'actual_value': float,
                'change_yoy': float,
                'source_texts': {'value': str, 'growth': str},
                'quarter': int
            }
        """
        result = {
            'actual_value': None,
            'change_yoy': None,
            'source_texts': {},
            'quarter': None
        }
        
        # Extract quarter
        result['quarter'] = cls.extract_quarter(text)
        
        # Extract based on indicator type
        if indicator_type == 'cpi':
            value, source = cls.extract_cpi(text)
            result['actual_value'] = value
            result['source_texts']['value'] = source
        elif indicator_type in ['export', 'investment']:
            value, source = cls.extract_value_usd(text)
            if value:
                result['actual_value'] = value
                result['source_texts']['value'] = source
            else:
                # Fallback to VND
                value, source = cls.extract_value_vnd(text)
                result['actual_value'] = value
                result['source_texts']['value'] = source
        else:
            value, source = cls.extract_value_vnd(text)
            result['actual_value'] = value
            result['source_texts']['value'] = source
        
        # Extract growth
        growth, source = cls.extract_growth(text)
        result['change_yoy'] = growth
        result['source_texts']['growth'] = source
        
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
    
    def get_article_content(self, url: str) -> Optional[str]:
        """Fetch và extract nội dung bài viết"""
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
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
        year: int = 2025
    ) -> Dict[str, Any]:
        """
        Extract và save dữ liệu theo pipeline chuẩn
        
        Returns:
            {indicator_type: {success: bool, data: {...}, validation: {...}}}
        """
        results = {}
        
        # Step 1: Normalize text
        text = TextNormalizer.normalize(text)
        logger.info(f" Normalized text: {len(text)} chars")
        
        # Step 2: Detect candidates bằng dictionary
        candidates = IndicatorDictionary.detect_candidates(text)
        logger.info(f" Dictionary detected {len(candidates)} candidates: {list(candidates.keys())}")
        
        # Step 3: Process each requested indicator
        for indicator_type in indicator_types:
            try:
                # Skip if not in candidates (no keyword match)
                if indicator_type not in candidates:
                    logger.info(f" Skipping {indicator_type.upper()} - no keyword match")
                    results[indicator_type] = {
                        'success': False,
                        'skipped': True,
                        'reason': 'No keyword match in text'
                    }
                    continue
                
                # Skip GRDP temporarily
                if indicator_type == 'grdp':
                    logger.info(f" Skipping GRDP (preserving existing data)")
                    results[indicator_type] = {
                        'success': False,
                        'skipped': True,
                        'reason': 'Skipped to preserve existing data'
                    }
                    continue
                
                logger.info(f" Processing {indicator_type.upper()}...")
                
                # Step 4: Find context around keywords
                contexts = IndicatorDictionary.find_keyword_context(text, indicator_type)
                if not contexts:
                    results[indicator_type] = {
                        'success': False,
                        'error': 'No context found for keywords'
                    }
                    continue
                
                # Step 5: LLM confirms indicator type (ONLY YES/NO)
                best_context = contexts[0]  # Use first context
                
                if self.classifier and self.use_llm:
                    confirmation = self.classifier.confirm_indicator(best_context, indicator_type)
                    logger.info(f"    LLM confirm: {confirmation['confirm']} (conf: {confirmation['confidence']:.2f})")
                    
                    if not confirmation['confirm'] and confirmation['confidence'] > 0.8:
                        logger.info(f"    LLM rejected {indicator_type.upper()}: {confirmation['reasoning']}")
                        results[indicator_type] = {
                            'success': False,
                            'rejected_by_llm': True,
                            'reason': confirmation['reasoning']
                        }
                        continue
                else:
                    confirmation = {'confirm': True, 'confidence': 0.7}
                
                # Step 6: Extract values using REGEX ONLY
                extracted = ValueExtractor.extract_for_indicator(best_context, indicator_type)
                logger.info(f"    Regex extracted: value={extracted['actual_value']}, yoy={extracted['change_yoy']}")
                
                if not extracted['actual_value'] and not extracted['change_yoy']:
                    # Try with full text
                    extracted = ValueExtractor.extract_for_indicator(text, indicator_type)
                    logger.info(f"    Full text extracted: value={extracted['actual_value']}, yoy={extracted['change_yoy']}")
                
                if not extracted['actual_value'] and not extracted['change_yoy']:
                    results[indicator_type] = {
                        'success': False,
                        'error': 'No numeric values found by regex'
                    }
                    continue
                
                # Step 7: Build data object
                quarter = extracted['quarter']
                period_type = 'quarter' if quarter else 'year'
                
                data = {
                    'province': 'Hưng Yên',
                    'year': year,
                    'quarter': quarter,
                    'period_type': period_type,
                    'data_status': 'official',
                    'actual_value': extracted['actual_value'],
                    'change_yoy': extracted['change_yoy'],
                    'last_updated': self._calculate_timestamp(year, quarter),
                    'data_source': source_url
                }
                
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
                    logger.warning(f"    Validation failed: {validation_errors}")
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
                logger.info(f"    Saved {indicator_type.upper()} (id={record.id})")
                
            except Exception as e:
                logger.error(f"    Error processing {indicator_type}: {e}")
                results[indicator_type] = {
                    'success': False,
                    'error': str(e)
                }
        
        return results
    
    def _calculate_timestamp(self, year: int, quarter: Optional[int]) -> datetime:
        """Calculate data timestamp (end of period)"""
        if quarter == 1:
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
        
        # Check for existing record
        query = self.db.query(model_class).filter(
            model_class.province == data['province'],
            model_class.year == data['year']
        )
        
        if data.get('quarter'):
            query = query.filter(model_class.quarter == data['quarter'])
        
        existing = query.first()
        
        if existing:
            # Update existing
            for key, value in data.items():
                if hasattr(existing, key) and value is not None:
                    setattr(existing, key, value)
            self.db.commit()
            self.db.refresh(existing)
            logger.info(f"    Updated existing record id={existing.id}")
            return existing
        else:
            # Create new
            record = model_class(**data)
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            logger.info(f"    Created new record id={record.id}")
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
        logger.warning(" EconomicLLMExtractor is DEPRECATED. Use UniversalEconomicExtractor instead.")
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
