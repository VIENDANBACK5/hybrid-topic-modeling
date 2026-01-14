"""
Universal Economic Data Extractor
Crawl và extract dữ liệu kinh tế từ thongkehungyen.nso.gov.vn
"""
import re
import logging
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
import requests
from bs4 import BeautifulSoup
from langchain_openai import ChatOpenAI

from app.models.model_iip_detail import IIPDetail
from app.models.model_agri_detail import AgriProductionDetail
from app.models.model_retail_detail import RetailServicesDetail
from app.models.model_export_detail import ExportDetail
from app.models.model_investment_detail import InvestmentDetail
from app.models.model_budget_detail import BudgetRevenueDetail
from app.models.model_cpi_detail import CPIDetail
from app.models.model_grdp_detail import GRDPDetail

logger = logging.getLogger(__name__)


class EconomicLLMExtractor:
    """
    LLM-based extractor for accurate economic data extraction
    Helps avoid confusion between different economic indicators
    """
    
    INDICATOR_DEFINITIONS = {
        'iip': 'Industrial Production Index - Chỉ số sản xuất công nghiệp (tỷ đồng). Thường dao động 1000-10000 tỷ/quý cho tỉnh nhỏ.',
        'grdp': 'Gross Regional Domestic Product - Tổng sản phẩm trên địa bàn (tỷ đồng). Rất lớn, thường 40000-250000 tỷ/năm.',
        'agri': 'Agricultural Production - Sản xuất nông nghiệp (tỷ đồng). Thường 5000-20000 tỷ/quý.',
        'retail': 'Retail & Services - Bán lẻ hàng hóa và dịch vụ tiêu dùng (tỷ đồng). Thường 10000-50000 tỷ/quý.',
        'export': 'Export Value - Kim ngạch xuất khẩu (triệu USD hoặc tỷ VND). Thường 50-500 triệu USD/quý.',
        'investment': 'Investment - Đầu tư (triệu USD hoặc tỷ VND). FDI thường 50-500 triệu USD.',
        'budget': 'Budget Revenue - Thu ngân sách (tỷ VND). Thường 2000-10000 tỷ/quý.',
        'cpi': 'Consumer Price Index - Chỉ số giá tiêu dùng (index number, thường quanh 100-110).'
    }
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not found, LLM extraction disabled")
            self.llm = None
        else:
            self.llm = ChatOpenAI(
                model="openai/gpt-4o-mini",
                temperature=0,
                openai_api_key=api_key,
                base_url="https://openrouter.ai/api/v1"
            )
    
    def analyze_all_indicators(self, text: str, year: int) -> Dict[str, Any]:
        """
        Gọi LLM 1 LẦN DUY NHẤT để phân tích TẤT CẢ các chỉ số trong văn bản
        Tối ưu hơn nhiều so với gọi từng chỉ số riêng lẻ
        
        Returns:
            {
                'indicators': [
                    {
                        'type': 'grdp',
                        'confidence': 0.95,
                        'actual_value': 40000,
                        'change_yoy': 8.5,
                        'quarter': 1,
                        ...
                    },
                    ...
                ]
            }
        """
        if not self.llm:
            return {'error': 'LLM not available'}
        
        prompt = f"""Bạn là chuyên gia phân tích dữ liệu kinh tế Việt Nam. Phân tích văn bản và XÁC ĐỊNH TẤT CẢ các chỉ số kinh tế có trong văn bản.

ĐỊNH NGHĨA CÁC CHỈ SỐ:
- GRDP: Tổng sản phẩm địa bàn (40,000-250,000 tỷ/năm) - "GDP", "quy mô kinh tế", "tổng sản phẩm"
- IIP: Sản xuất công nghiệp (1,000-10,000 tỷ/quý) - "sản xuất công nghiệp", "chế biến chế tạo"
- Agri: Nông nghiệp (2,000-20,000 tỷ/quý) - "nông nghiệp", "lương thực"
- Retail: Bán lẻ & dịch vụ (10,000-50,000 tỷ/quý) - "bán lẻ", "dịch vụ tiêu dùng"
- Export: Xuất khẩu (50-500 triệu USD/quý) - "xuất khẩu", "kim ngạch"
- Investment: Đầu tư (50-1,000 triệu USD) - "FDI", "đầu tư"
- Budget: Thu ngân sách (2,000-10,000 tỷ/quý) - "thu ngân sách", "thu thuế"
- CPI: Chỉ số giá (95-115 index) - "CPI", "lạm phát", "chỉ số giá"

VĂN BẢN:
{text[:5000]}

YÊU CẦU QUAN TRỌNG:
- CHỈ trích xuất giá trị xuất hiện TRỰC TIẾP trong văn bản gốc
- KHÔNG được tự suy luận hoặc ước tính giá trị
- PHẢI có "source_text": đoạn văn bản gốc chứa giá trị (tối đa 200 ký tự)
- Nếu KHÔNG TÌM THẤY giá trị cụ thể, KHÔNG liệt kê chỉ số đó
- Kiểm tra KHOẢNG GIÁ TRỊ hợp lý cho từng chỉ số
- Nếu một giá trị quá lớn cho IIP (>10,000) thì có thể là GRDP hoặc Retail
- Một văn bản có thể chứa NHIỀU chỉ số khác nhau

Trả về JSON format (CHỈ JSON, không text khác):
{{
    "indicators": [
        {{
            "type": "grdp",
            "confidence": 0.95,
            "year": {year},
            "quarter": 1,
            "actual_value": 40000,
            "change_yoy": 8.5,
            "source_text": "Tổng sản phẩm trên địa bàn tỉnh (GRDP) năm 2024 ước đạt 40.000 tỷ đồng, tăng 7,70%",
            "reasoning": "Văn bản đề cập 'tổng sản phẩm địa bàn' với giá trị 40 nghìn tỷ"
        }}
    ]
}}
"""
        
        try:
            result = self.llm.invoke(prompt)
            content = result.content.strip()
            
            # Extract JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                indicators = data.get('indicators', [])
                logger.info(f"    LLM phát hiện {len(indicators)} chỉ số: {[i['type'] for i in indicators]}")
                for ind in indicators:
                    logger.info(f"       {ind['type'].upper()}: {ind.get('actual_value')} (confidence: {ind.get('confidence')})")
                    if 'source_text' in ind:
                        logger.info(f"         Source: {ind['source_text'][:150]}")
                return data
            else:
                logger.error(f"    No JSON in LLM response: {content[:200]}")
                return {'error': 'No JSON in response'}
                
        except Exception as e:
            logger.error(f"    LLM error: {e}")
            return {'error': str(e)}
    
    def analyze_and_extract(self, text: str, candidate_types: List[str], year: int) -> Dict[str, Any]:
        """
        DEPRECATED: Dùng analyze_all_indicators() thay thế
        Legacy method for single indicator analysis
        """
        if not self.llm:
            return {'error': 'LLM not available'}
        
        # Build indicator descriptions
        indicator_info = "\n".join([
            f"- {itype}: {self.INDICATOR_DEFINITIONS.get(itype, 'Unknown')}"
            for itype in candidate_types
        ])
        
        prompt = f"""Phân tích văn bản và xác định chỉ số kinh tế.

CÁC CHỈ SỐ: {indicator_info}
VĂN BẢN: {text[:4000]}

Trả về JSON:
{{
    "indicator_type": "iip/grdp/etc",
    "confidence": 0.95,
    "year": {year},
    "quarter": 1,
    "actual_value": 1000,
    "change_yoy": 5.5,
    "reasoning": "..."
}}
"""
        
        try:
            result = self.llm.invoke(prompt)
            content = result.content.strip()
            json_match = re.search(r'\{[^}]*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return data
            return {'error': 'No JSON in response'}
        except Exception as e:
            return {'error': str(e)}


class ArticleCrawler:
    """Crawl danh sách bài viết từ trang thống kê"""
    
    BASE_URL = "https://thongkehungyen.nso.gov.vn"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        # Disable SSL verification for this domain
        self.session.verify = False
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    def get_article_list(self, max_pages: int = 5) -> List[Dict[str, str]]:
        """
        Lấy danh sách bài viết từ nhiều trang
        
        Returns:
            List of {title, url, date, summary}
        """
        articles = []
        
        for page in range(1, max_pages + 1):
            url = f"{self.BASE_URL}/tinh-hinh-kinh-te-xa-hoi?page={page}"
            logger.info(f" Crawling page {page}: {url}")
            
            try:
                resp = self.session.get(url, timeout=30)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.content, 'html.parser')
                
                # Tìm các bài viết (adjust selector dựa vào cấu trúc thực tế)
                article_items = soup.select('.article-item, .news-item, .post-item')
                
                if not article_items:
                    article_items = soup.find_all('a', href=re.compile(r'/tinh-hinh'))
                
                logger.info(f"   Found {len(article_items)} articles on page {page}")
                
                for item in article_items:
                    try:
                        if item.name == 'a':
                            link = item
                            title = item.get_text(strip=True)
                        else:
                            link = item.find('a')
                            title = link.get_text(strip=True) if link else ""
                        
                        if not link or not title:
                            continue
                        
                        href = link.get('href', '')
                        if not href.startswith('http'):
                            href = self.BASE_URL + href
                        
                        logger.debug(f"    Found article: {title[:50]}... -> {href}")  # DEBUG
                        
                        # Extract date if available
                        date_elem = item.find(class_=re.compile(r'date|time'))
                        date_str = date_elem.get_text(strip=True) if date_elem else ""
                        
                        # Extract summary if available
                        summary_elem = item.find(class_=re.compile(r'summary|description|excerpt'))
                        summary = summary_elem.get_text(strip=True) if summary_elem else ""
                        
                        articles.append({
                            'title': title,
                            'url': href,
                            'date': date_str,
                            'summary': summary
                        })
                        
                    except Exception as e:
                        logger.warning(f"    Error parsing article item: {e}")
                        continue
                
            except Exception as e:
                logger.error(f" Error crawling page {page}: {e}")
                continue
        
        logger.info(f" Total articles found: {len(articles)}")
        return articles
    
    def get_article_content(self, url: str) -> Optional[str]:
        """Lấy nội dung đầy đủ của bài viết - ENHANCED"""
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Remove navigation, header, footer, sidebar
            for element in soup.find_all(['nav', 'header', 'footer', 'aside']):
                element.decompose()
            
            for element in soup.find_all(class_=re.compile(r'menu|nav|header|footer|sidebar|widget|advertisement')):
                element.decompose()
            
            # Try multiple selectors for main content
            content = None
            selectors = [
                ('div', re.compile(r'article-content|post-content|entry-content|main-content')),
                ('article', None),
                ('main', None),
                ('div', {'id': re.compile(r'content|article|post|main')}),
                ('div', {'class': re.compile(r'detail|body|text')}),
            ]
            
            for tag, attrs in selectors:
                if attrs:
                    if isinstance(attrs, dict):
                        content = soup.find(tag, attrs)
                    else:
                        content = soup.find(tag, class_=attrs)
                else:
                    content = soup.find(tag)
                
                if content:
                    text = content.get_text(separator='\n', strip=True)
                    # Validate: content should have some economic keywords or numbers
                    if len(text) > 200 and (
                        re.search(r'\d+[.,]\d+|tăng|giảm|%|tỷ|triệu|nghìn', text, re.IGNORECASE)
                    ):
                        logger.info(f"    Extracted {len(text)} chars using {tag} selector")
                        return text
            
            paragraphs = soup.find_all('p')
            if paragraphs:
                text = '\n'.join(p.get_text(strip=True) for p in paragraphs)
                if len(text) > 200:
                    logger.info(f"    Extracted {len(text)} chars from paragraphs")
                    return text
            
            logger.warning(f"    No suitable content found in {url}")
            return None
            
        except Exception as e:
            logger.error(f" Error fetching content from {url}: {e}")
            return None


class IndicatorClassifier:
    """Phân loại bài viết thuộc chỉ số nào - ENHANCED VERSION"""
    
    PATTERNS = {
        'grdp': [
            r'grdp|tổng sản phẩm.*địa bàn|gross.*domestic.*product',
            r'quy mô kinh tế|tăng trưởng kinh tế|tăng trưởng gdp',
            r'giá hiện hành|giá so sánh|gdp.*tỉnh|gdp.*tăng',
            r'kinh tế.*tăng.*%|tăng trưởng.*đạt.*%'
        ],
        'iip': [
            r'iip|chỉ số.*sản xuất.*công nghiệp|industrial.*production',
            r'sản xuất công nghiệp|ngành công nghiệp|công nghiệp.*tăng',
            r'chế biến.*chế tạo|khai khoáng|sản xuất.*điện',
            r'giá trị.*sản xuất.*công nghiệp'
        ],
        'agri': [
            r'nông nghiệp|sản xuất.*nông.*nghiệp|agriculture',
            r'lương thực|cây trồng|vật nuôi|thủy sản',
            r'nông.*lâm.*ngư|trồng trọt|chăn nuôi',
            r'giá trị.*nông nghiệp|nông nghiệp.*tăng'
        ],
        'retail': [
            r'bán lẻ|dịch vụ.*tiêu dùng|retail.*service',
            r'tổng mức.*bán lẻ|doanh thu.*dịch vụ',
            r'thương mại.*dịch vụ|tiêu dùng.*hàng.*hóa',
            r'bán lẻ.*hàng.*hóa|doanh số.*bán lẻ'
        ],
        'export': [
            r'xuất khẩu|kim ngạch.*xuất|export',
            r'hàng hóa xuất khẩu|thị trường xuất khẩu',
            r'giá trị.*xuất.*khẩu|xuất.*hàng|triệu.*usd',
            r'xuất.*sang.*nước|hàng.*xuất.*khẩu'
        ],
        'investment': [
            r'đầu tư|fdi|vốn.*đầu tư|investment',
            r'thu hút.*đầu tư|giải ngân.*vốn',
            r'vốn.*fdi|dự án.*đầu tư|đầu tư.*nước ngoài',
            r'đầu tư.*trực tiếp|đầu tư.*trong.*nước|ddi',
            r'vốn.*đăng.*ký|vốn.*thực hiện'
        ],
        'budget': [
            r'ngân sách|thu.*ngân.*sách|budget.*revenue',
            r'thu.*thuế|thu.*nội địa|thu.*địa phương',
            r'thu.*ngân sách.*nhà nước|tổng.*thu',
            r'thuế.*giá.*trị.*gia.*tăng|thuế.*thu nhập',
            r'tỷ.*lệ.*thực.*hiện|vượt.*dự.*toán'
        ],
        'cpi': [
            r'cpi|giá.*tiêu dùng|consumer.*price',
            r'lạm phát|chỉ số.*giá|tăng.*giá',
            r'giá.*cả.*thị.*trường|chỉ số.*giá.*tiêu.*dùng',
            r'biến động.*giá|tăng.*giảm.*giá'
        ]
    }
    
    @classmethod
    def classify(cls, text: str) -> List[str]:
        """
        Phân loại text thuộc các chỉ số nào
        
        Returns:
            List of indicator types: ['grdp', 'iip', ...]
        """
        text_lower = text.lower()
        matched_types = []
        
        for indicator_type, patterns in cls.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    matched_types.append(indicator_type)
                    break
        
        return matched_types


class UniversalEconomicExtractor:
    """
    Extract dữ liệu kinh tế từ text và lưu vào bảng tương ứng
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
    
    # VALUE RANGE VALIDATION (tỷ VND unless noted)
    VALUE_RANGES = {
        'iip': (1000, 10000, 'tỷ VND'),  # IIP cho tỉnh nhỏ
        'grdp': (40000, 250000, 'tỷ VND'),  # GRDP toàn tỉnh
        'agri': (2000, 20000, 'tỷ VND'),
        'retail': (10000, 50000, 'tỷ VND'),
        'export': (50, 500, 'triệu USD'),
        'investment': (50, 1000, 'triệu USD'),
        'budget': (2000, 10000, 'tỷ VND'),
        'cpi': (95, 115, 'index')  # CPI là chỉ số, không phải tiền
    }
    
    def __init__(self, db: Session, use_llm: bool = True):
        self.db = db
        self.use_llm = use_llm
        self.llm_extractor = EconomicLLMExtractor() if use_llm else None
    
    def extract_and_save(
        self,
        text: str,
        indicator_types: List[str],
        source_url: str,
        year: int = 2025
    ) -> Dict[str, Any]:
        """
        Extract và save dữ liệu - AUTO SỬ DỤNG LLM để phân tích tối ưu
        
        Returns:
            {indicator_type: {success: bool, record: ..., validation: ...}}
        """
        results = {}
        
        # OPTIMIZATION: Gọi LLM 1 LẦN duy nhất để phân tích TẤT CẢ indicators
        llm_analysis = None
        if self.llm_extractor and self.llm_extractor.llm:
            logger.info(f" Using LLM to analyze ALL indicators in one call...")
            llm_analysis = self.llm_extractor.analyze_all_indicators(text, year)
            
            if llm_analysis and 'indicators' in llm_analysis:
                indicators_found = llm_analysis['indicators']
                logger.info(f"    LLM analysis complete: {len(indicators_found)} indicators detected")
                
                # Tạo mapping từ LLM results
                llm_results_map = {
                    ind['type']: ind for ind in indicators_found
                }
                
                # CHỈ XỬ LÝ các indicators mà LLM xác định có trong văn bản
                # Bỏ qua các indicators không liên quan -> TIẾT KIỆM THỜI GIAN
                valid_indicator_types = [t for t in indicator_types if t in llm_results_map or t == 'grdp']
                
                if valid_indicator_types:
                    logger.info(f"    Processing {len(valid_indicator_types)} relevant indicators: {valid_indicator_types}")
                else:
                    logger.warning(f"    No relevant indicators found by LLM")
            else:
                logger.warning(f"    LLM analysis failed, falling back to regex for all types")
                llm_results_map = {}
                valid_indicator_types = indicator_types
        else:
            logger.info(f" LLM not available, using regex extraction")
            llm_results_map = {}
            valid_indicator_types = indicator_types
        
        # Process each indicator
        for indicator_type in valid_indicator_types:
            try:
                # SKIP grdp_detail temporarily to preserve existing data
                if indicator_type == 'grdp':
                    logger.info(f" Skipping GRDP (preserving existing data)")
                    results[indicator_type] = {
                        'success': False,
                        'skipped': True,
                        'reason': 'Skipped to preserve existing data'
                    }
                    continue
                
                logger.info(f" Extracting {indicator_type.upper()} from text...")
                
                # Sử dụng kết quả từ LLM nếu có
                if indicator_type in llm_results_map:
                    llm_data = llm_results_map[indicator_type]
                    logger.info(f"    Using LLM result for {indicator_type.upper()}")
                    
                    data = {
                        'province': 'Hưng Yên',
                        'year': llm_data.get('year', year),
                        'quarter': llm_data.get('quarter'),
                        'period_type': 'quarter' if llm_data.get('quarter') else 'year',
                        'data_status': 'official',
                        'actual_value': llm_data.get('actual_value'),
                        'change_yoy': llm_data.get('change_yoy'),
                        'last_updated': self._calculate_data_timestamp(
                            llm_data.get('year', year), 
                            llm_data.get('quarter')
                        )
                    }
                    
                    # Add indicator-specific fields using regex
                    if indicator_type == 'export':
                        data.update(self._extract_export_fields(text))
                    elif indicator_type == 'investment':
                        data.update(self._extract_investment_fields(text))
                    elif indicator_type == 'budget':
                        data.update(self._extract_budget_fields(text))
                    elif indicator_type == 'cpi':
                        data.update(self._extract_cpi_fields(text))
                    elif indicator_type == 'retail':
                        data.update(self._extract_retail_fields(text))
                else:
                    # Fallback to regex extraction
                    data = self._extract_by_type(text, indicator_type, year)
                
                # Calculate data timestamp if not set
                if data and 'last_updated' not in data:
                    quarter = data.get('quarter')
                    data['last_updated'] = self._calculate_data_timestamp(year, quarter)
                
                if data:
                    # Validate data quality
                    validation = self._validate_data(data, indicator_type)
                    
                    if not validation['is_valid']:
                        logger.warning(f"    Data validation failed: {validation['errors']}")
                        results[indicator_type] = {
                            'success': False,
                            'error': 'Validation failed',
                            'validation': validation,
                            'data': data
                        }
                        continue
                    
                    # Save to database
                    record = self._save_to_db(indicator_type, data, source_url)
                    results[indicator_type] = {
                        'success': True,
                        'record': record,
                        'data': data,
                        'validation': validation
                    }
                    logger.info(f"    Saved {indicator_type} data (id={record.id})")
                else:
                    results[indicator_type] = {
                        'success': False,
                        'error': 'No data extracted'
                    }
                    logger.warning(f"    No {indicator_type} data found")
                    
            except Exception as e:
                logger.error(f"    Error extracting {indicator_type}: {e}")
                results[indicator_type] = {
                    'success': False,
                    'error': str(e)
                }
        
        return results
    
    def _validate_data(self, data: Dict, indicator_type: str) -> Dict:
        """
        Validate extracted data quality - ENHANCED with value range checks
        
        Returns:
            {is_valid: bool, errors: [], warnings: [], completeness: %}
        """
        errors = []
        warnings = []
        
        # Check required fields
        if not data.get('actual_value') and not data.get('change_yoy'):
            errors.append("Missing both actual_value and change_yoy")
        
        # Check value ranges based on indicator type
        actual_value = data.get('actual_value')
        if actual_value and indicator_type in self.VALUE_RANGES:
            min_val, max_val, unit = self.VALUE_RANGES[indicator_type]
            
            if not (min_val <= actual_value <= max_val):
                errors.append(
                    f" {indicator_type.upper()} value {actual_value:,.0f} {unit} "
                    f"ngoài khoảng hợp lý ({min_val:,.0f} - {max_val:,.0f} {unit}). "
                    f"Có thể đang nhầm với chỉ số khác!"
                )
            
            # Additional warnings for suspicious values
            if indicator_type == 'iip' and actual_value > 50000:
                warnings.append(f" IIP {actual_value:,.0f} tỷ quá lớn - có thể là GRDP hoặc Retail?")
            elif indicator_type == 'grdp' and actual_value < 10000:
                warnings.append(f" GRDP {actual_value:,.0f} tỷ quá nhỏ - có thể là IIP hoặc Agri?")
            elif indicator_type == 'cpi' and actual_value > 200:
                warnings.append(f" CPI {actual_value} không hợp lý - CPI là chỉ số (100-110), không phải tiền")
        
        # Check growth rate reasonableness
        if data.get('change_yoy'):
            yoy = float(data['change_yoy'])
            if abs(yoy) > 50:
                warnings.append(f"Extreme YoY growth: {yoy}% (unusual for most indicators)")
            elif abs(yoy) > 100:
                errors.append(f" YoY growth {yoy}% không hợp lý (>100%)")
        
        # Check specific fields by indicator type
        if indicator_type == 'export':
            if data.get('export_usd') and data.get('export_vnd'):
                # Check if USD/VND conversion is reasonable (1 USD ~ 24,000 VND)
                usd_to_vnd = data['export_vnd'] / data['export_usd']
                if not (20 < usd_to_vnd < 30):
                    warnings.append(f"USD/VND ratio unusual: {usd_to_vnd:.0f}")
        
        # Calculate completeness score
        total_fields = len(data)
        filled_fields = sum(1 for v in data.values() if v is not None)
        completeness = (filled_fields / total_fields * 100) if total_fields > 0 else 0
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'completeness': round(completeness, 1),
            'filled_fields': filled_fields,
            'total_fields': total_fields
        }
    
    def _extract_by_type(self, text: str, indicator_type: str, year: int) -> Optional[Dict]:
        """Extract dữ liệu theo loại chỉ số - ENHANCED WITH LLM"""
        
        # Try LLM extraction first if available
        if self.llm_extractor and self.llm_extractor.llm:
            try:
                logger.info(f"    Using LLM for {indicator_type.upper()} extraction...")
                llm_result = self.llm_extractor.analyze_and_extract(
                    text=text,
                    candidate_types=[indicator_type],
                    year=year
                )
                
                if llm_result and 'error' not in llm_result:
                    # Verify LLM suggested the correct type
                    suggested_type = llm_result.get('indicator_type')
                    confidence = llm_result.get('confidence', 0)
                    
                    if suggested_type != indicator_type:
                        logger.warning(
                            f"    LLM suggests '{suggested_type}' instead of '{indicator_type}' "
                            f"(confidence: {confidence})"
                        )
                        # If high confidence, use LLM's suggestion
                        if confidence > 0.8:
                            logger.info(f"    Switching to {suggested_type.upper()} based on LLM")
                            indicator_type = suggested_type
                    
                    # Convert LLM result to our format
                    base_data = {
                        'province': 'Hưng Yên',
                        'year': llm_result.get('year', year),
                        'quarter': llm_result.get('quarter'),
                        'period_type': 'quarter' if llm_result.get('quarter') else 'year',
                        'data_status': 'official',
                        'actual_value': llm_result.get('actual_value'),
                        'change_yoy': llm_result.get('change_yoy')
                    }
                    
                    # Add indicator-specific fields
                    if indicator_type == 'export':
                        base_data.update(self._extract_export_fields(text))
                    elif indicator_type == 'investment':
                        base_data.update(self._extract_investment_fields(text))
                    elif indicator_type == 'budget':
                        base_data.update(self._extract_budget_fields(text))
                    elif indicator_type == 'cpi':
                        base_data.update(self._extract_cpi_fields(text))
                    elif indicator_type == 'retail':
                        base_data.update(self._extract_retail_fields(text))
                    
                    logger.info(f"    LLM extraction successful: {base_data.get('actual_value')} {llm_result.get('value_unit', '')}")
                    return base_data
                    
            except Exception as e:
                logger.warning(f"    LLM extraction failed, falling back to regex: {e}")
        
        # Fallback to regex-based extraction
        logger.info(f"    Using regex for {indicator_type.upper()} extraction...")
        
        # Detect period (quarter only)
        quarter = self._detect_quarter(text)
        
        base_data = {
            'province': 'Hưng Yên',
            'year': year,
            'quarter': quarter,
            'period_type': 'quarter' if quarter else 'year',
            'data_status': 'official'
        }
        
        # Extract actual value and growth
        actual_value = self._extract_value(text)
        change_yoy = self._extract_growth(text)
        
        if actual_value or change_yoy:
            base_data['actual_value'] = actual_value
            base_data['change_yoy'] = change_yoy
            
            # Extract specific fields based on type
            if indicator_type == 'export':
                base_data.update(self._extract_export_fields(text))
            elif indicator_type == 'investment':
                base_data.update(self._extract_investment_fields(text))
            elif indicator_type == 'budget':
                base_data.update(self._extract_budget_fields(text))
            elif indicator_type == 'cpi':
                base_data.update(self._extract_cpi_fields(text))
            elif indicator_type == 'retail':
                base_data.update(self._extract_retail_fields(text))
            
            return base_data
        
        return None
    
    def _extract_quarterly_breakdown(self, text: str) -> Optional[Dict]:
        """Extract quarterly growth breakdown (Q1, Q2, Q3, Q4)"""
        quarterly = {}
        
        # parterns
        quarter_patterns = [
            (r'quý\s*I[^IV].*?tăng\s*(\d+)[.,](\d+)\s*%', 1),
            (r'quý\s*1.*?tăng\s*(\d+)[.,](\d+)\s*%', 1),
            (r'quý\s*II[^IV].*?tăng\s*(\d+)[.,](\d+)\s*%', 2),
            (r'quý\s*2.*?tăng\s*(\d+)[.,](\d+)\s*%', 2),
            (r'quý\s*III.*?tăng\s*(\d+)[.,](\d+)\s*%', 3),
            (r'quý\s*3.*?tăng\s*(\d+)[.,](\d+)\s*%', 3),
            (r'quý\s*IV.*?tăng\s*(\d+)[.,](\d+)\s*%', 4),
            (r'quý\s*4.*?tăng\s*(\d+)[.,](\d+)\s*%', 4),
        ]
        
        for pattern, q_num in quarter_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                growth = float(f"{match.group(1)}.{match.group(2)}")
                quarterly[f'Q{q_num}'] = growth
        
        return quarterly if quarterly else None
    
    def _detect_quarter(self, text: str) -> Optional[int]:
        """Detect quarter from text - FIXED to get LAST mentioned quarter"""
        patterns = [
            (r'quý\s*I(?![IV])|quý\s*1\b|quarter\s*1', 1),
            (r'quý\s*II(?![IV])|quý\s*2\b|quarter\s*2', 2),
            (r'quý\s*III|quý\s*3\b|quarter\s*3', 3),
            (r'quý\s*IV|quý\s*4\b|quarter\s*4', 4),
        ]
        
        # Find ALL quarters mentioned and take the LAST one
        found_quarters = []
        for pattern, q in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                found_quarters.append((match.start(), q))
        
        if found_quarters:
            # Sort by position and return the last one
            found_quarters.sort(key=lambda x: x[0])
            return found_quarters[-1][1]
        
        # Special case: "6 tháng đầu năm" = H1 (first half), "3 tháng đầu năm" = Q1
        if re.search(r'3\s*tháng\s*đầu', text, re.IGNORECASE):
            return 1
        if re.search(r'6\s*tháng\s*đầu', text, re.IGNORECASE):
            # 6 months = H1, but if no specific quarter, could be Q2
            return 2
        
        return None
    
    def _detect_month(self, text: str) -> Optional[int]:
        """Detect month from text"""
        match = re.search(r'tháng\s*(\d{1,2})', text, re.IGNORECASE)
        if match:
            month = int(match.group(1))
            if 1 <= month <= 12:
                return month
        return None
    
    def _calculate_data_timestamp(self, year: int, quarter: Optional[int]) -> datetime:
        """
        Calculate timestamp based on data period (end of quarter/year)
        NOT publication date - this is when the data period ends
        
        Examples:
        - Q1 2024 -> 31/3/2024
        - Q2 2024 -> 30/6/2024  
        - Q3 2024 -> 30/9/2024
        - Q4 2024 -> 31/12/2024
        - Year 2024 (no quarter) -> 31/12/2024
        """
        if quarter == 1:
            return datetime(year, 3, 31)
        elif quarter == 2:
            return datetime(year, 6, 30)
        elif quarter == 3:
            return datetime(year, 9, 30)
        elif quarter == 4:
            return datetime(year, 12, 31)
        else:
            # No quarter specified - use end of year
            return datetime(year, 12, 31)
        """Extract publication/release date from text for last_updated field - ENHANCED"""
        
        matches = list(re.finditer(r'(\d{1,2})/(\d{1,2})/(\d{4})', text))
        if matches:
            # Take the LAST date mentioned (most recent/relevant)
            match = matches[-1]
            try:
                day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                if 1 <= day <= 31 and 1 <= month <= 12:
                    return datetime(year, month, day)
            except:
                pass
        
        
        matches = list(re.finditer(r'ngày\s*(\d{1,2}).*?tháng\s*(\d{1,2}).*?năm\s*(\d{4})', text, re.IGNORECASE))
        if matches:
            match = matches[-1]
            try:
                day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                if 1 <= day <= 31 and 1 <= month <= 12:
                    return datetime(year, month, day)
            except:
                pass
        
        
        matches = list(re.finditer(r'tháng\s*(\d{1,2})[/\s]+(?:năm\s*)?(\d{4})', text, re.IGNORECASE))
        if matches:
            match = matches[-1]
            try:
                month, year = int(match.group(1)), int(match.group(2))
                if 1 <= month <= 12:
                    # Use last day of the month
                    if month in [1,3,5,7,8,10,12]:
                        day = 31
                    elif month in [4,6,9,11]:
                        day = 30
                    else:  # February
                        day = 29 if year % 4 == 0 else 28
                    return datetime(year, month, day)
            except:
                pass
        
        
        matches = list(re.finditer(r'năm\s*(\d{4})', text, re.IGNORECASE))
        if matches:
            match = matches[-1]
            try:
                year = int(match.group(1))
                if 2000 <= year <= 2030:
                    return datetime(year, 12, 31)
            except:
                pass
        
        return datetime.now()
    
    def _extract_value(self, text: str) -> Optional[float]:
        """Extract main value - ENHANCED với nhiều patterns"""
        
        match = re.search(r'(\d{1,3})[.,](\d{3})\s*tỷ', text)
        if match:
            return float(f"{match.group(1)}{match.group(2)}")
        
        
        match = re.search(r'đạt\s+(\d+)[.,](\d+)\s*tỷ', text)
        if match:
            return float(f"{match.group(1)}{match.group(2)}")
        
        
        match = re.search(r'ước.*?đạt\s*(\d+)[.,](\d+)\s*tỷ', text)
        if match:
            return float(f"{match.group(1)}{match.group(2)}")
        
        
        match = re.search(r'giá\s*trị.*?(\d+)[.,](\d+)\s*tỷ', text)
        if match:
            return float(f"{match.group(1)}{match.group(2)}")
        
        
        match = re.search(r'đạt\s*(\d+)\s*tỷ', text)
        if match:
            return float(match.group(1)) * 1000
        
        
        match = re.search(r'(\d+)[.,](\d+)\s*nghìn\s*tỷ', text)
        if match:
            return float(f"{match.group(1)}{match.group(2)}") * 1000
        
        return None
    
    def _extract_growth(self, text: str) -> Optional[float]:
        """Extract growth rate - ENHANCED"""
        
        match = re.search(r'tăng\s*(\d+)[.,](\d+)\s*%', text)
        if match:
            return float(f"{match.group(1)}.{match.group(2)}")
        
        
        match = re.search(r'tăng\s*(\d+)\s*%', text)
        if match:
            return float(match.group(1))
        
        
        match = re.search(r'tăng\s*trưởng\s*(\d+)[.,](\d+)\s*%', text)
        if match:
            return float(f"{match.group(1)}.{match.group(2)}")
        
        
        match = re.search(r'cùng\s*kỳ.*?\+?(\d+)[.,](\d+)\s*%', text)
        if match:
            return float(f"{match.group(1)}.{match.group(2)}")
        
        
        match = re.search(r'giảm\s*(\d+)[.,](\d+)\s*%', text)
        if match:
            return -float(f"{match.group(1)}.{match.group(2)}")
        
        return None
    
    def _extract_export_fields(self, text: str) -> Dict:
        """Extract export-specific fields - ENHANCED"""
        data = {}
        
        # Export value in USD - Multiple patterns
        patterns_usd = [
            r'(\d+[.,]\d+)\s*triệu\s*(USD|usd|đô la)',
            r'kim\s*ngạch.*?(\d+[.,]\d+)\s*triệu.*?(USD|usd)',
            r'xuất\s*khẩu.*?(\d+[.,]\d+)\s*triệu.*?(USD|usd)',
            r'(\d+)\s*triệu\s*(USD|usd)'
        ]
        
        for pattern in patterns_usd:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).replace(',', '.')
                data['export_usd'] = float(val)
                break
        
        # Export value in VND
        match = re.search(r'xuất\s*khẩu.*?(\d+[.,]\d+)\s*tỷ', text, re.IGNORECASE)
        if match:
            val = match.group(1).replace(',', '')
            data['export_vnd'] = float(val)
        
        # Top products - tìm danh sách sản phẩm
        products = []
        product_patterns = [
            r'(?:sản phẩm|mặt hàng|nhóm hàng).*?(?:chính|chủ yếu|chủ lực).*?[:]?\s*([^.]+)',
            r'(?:xuất khẩu).*?(?:gồm|bao gồm).*?[:]?\s*([^.]+)'
        ]
        for pattern in product_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                product_text = match.group(1)
                # Split by common delimiters
                items = re.split(r'[,;]', product_text)
                products.extend([p.strip() for p in items if len(p.strip()) > 2])
                break
        
        if products:
            data['top_products'] = ', '.join(products[:5])  # Top 5
        
        # Top markets
        markets = []
        market_patterns = [
            r'(?:thị trường|nước|khu vực).*?[:]?\s*([^.]+)',
            r'(?:xuất sang|xuất khẩu đến).*?[:]?\s*([^.]+)'
        ]
        for pattern in market_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                market_text = match.group(1)
                items = re.split(r'[,;]', market_text)
                markets.extend([m.strip() for m in items if len(m.strip()) > 2])
                break
        
        if markets:
            data['top_markets'] = ', '.join(markets[:5])
        
        return data
    
    def _extract_investment_fields(self, text: str) -> Dict:
        """Extract investment-specific fields - ENHANCED"""
        data = {}
        
        # FDI registered capital
        fdi_patterns = [
            r'vốn.*?fdi.*?đăng.*?ký.*?(\d+[.,]\d+)\s*triệu.*?USD',
            r'fdi.*?đăng.*?ký.*?(\d+[.,]\d+)\s*triệu.*?USD',
            r'vốn.*?đăng.*?ký.*?(\d+[.,]\d+)\s*triệu.*?USD',
            r'đăng.*?ký.*?mới.*?(\d+[.,]\d+)\s*triệu.*?USD'
        ]
        
        for pattern in fdi_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).replace(',', '.')
                data['fdi_registered'] = float(val)
                break
        
        # FDI disbursed
        disbursed_patterns = [
            r'giải.*?ngân.*?(\d+[.,]\d+)\s*triệu.*?USD',
            r'vốn.*?thực.*?hiện.*?(\d+[.,]\d+)\s*triệu.*?USD',
            r'thực.*?hiện.*?fdi.*?(\d+[.,]\d+)\s*triệu.*?USD'
        ]
        
        for pattern in disbursed_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).replace(',', '.')
                data['fdi_disbursed'] = float(val)
                break
        
        # Number of FDI projects
        match = re.search(r'(\d+)\s*dự\s*án.*?fdi', text, re.IGNORECASE)
        if match:
            data['fdi_projects_new'] = float(match.group(1))
        
        # DDI (Domestic Direct Investment)
        ddi_patterns = [
            r'đầu.*?tư.*?trong.*?nước.*?(\d+[.,]\d+)\s*tỷ',
            r'ddi.*?(\d+[.,]\d+)\s*tỷ',
            r'vốn.*?trong.*?nước.*?(\d+[.,]\d+)\s*tỷ'
        ]
        
        for pattern in ddi_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).replace(',', '')
                data['ddi_value'] = float(val)
                break
        
        # Public investment
        public_patterns = [
            r'đầu.*?tư.*?công.*?(\d+[.,]\d+)\s*tỷ',
            r'vốn.*?ngân.*?sách.*?(\d+[.,]\d+)\s*tỷ'
        ]
        
        for pattern in public_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).replace(',', '')
                data['public_investment'] = float(val)
                break
        
        return data
    
    def _extract_budget_fields(self, text: str) -> Dict:
        """Extract budget-specific fields - ENHANCED"""
        data = {}
        
        # Tax revenue
        tax_patterns = [
            r'thu.*?thuế.*?(\d+[.,]\d+)\s*tỷ',
            r'thuế.*?thu.*?(\d+[.,]\d+)\s*tỷ',
            r'thu.*?từ.*?thuế.*?(\d+[.,]\d+)\s*tỷ'
        ]
        
        for pattern in tax_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).replace(',', '')
                data['tax_revenue'] = float(val)
                break
        
        # Non-tax revenue
        match = re.search(r'thu.*?ngoài.*?thuế.*?(\d+[.,]\d+)\s*tỷ', text, re.IGNORECASE)
        if match:
            val = match.group(1).replace(',', '')
            data['non_tax_revenue'] = float(val)
        
        # Land revenue
        land_patterns = [
            r'thu.*?(?:từ|tiền).*?đất.*?(\d+[.,]\d+)\s*tỷ',
            r'sử\s*dụng.*?đất.*?(\d+[.,]\d+)\s*tỷ'
        ]
        
        for pattern in land_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).replace(',', '')
                data['land_revenue'] = float(val)
                break
        
        # Budget target
        match = re.search(r'dự.*?toán.*?(\d+[.,]\d+)\s*tỷ', text, re.IGNORECASE)
        if match:
            val = match.group(1).replace(',', '')
            data['budget_target'] = float(val)
        
        # Execution rate
        exec_patterns = [
            r'đạt\s*(\d+[.,]\d+)\s*%.*?dự.*?toán',
            r'thực.*?hiện.*?(\d+[.,]\d+)\s*%',
            r'tỷ.*?lệ.*?(\d+[.,]\d+)\s*%'
        ]
        
        for pattern in exec_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).replace(',', '.')
                data['execution_rate'] = float(val)
                break
        
        return data
    
    def _extract_cpi_fields(self, text: str) -> Dict:
        """Extract CPI-specific fields - ENHANCED"""
        data = {}
        
        # Overall CPI index
        cpi_patterns = [
            r'cpi\s*(?:đạt|là)?\s*(\d+[.,]\d+)',
            r'chỉ\s*số.*?giá.*?(\d+[.,]\d+)',
            r'cpi.*?tháng.*?(\d+[.,]\d+)'
        ]
        
        for pattern in cpi_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).replace(',', '.')
                data['actual_value'] = float(val)
                break
        
        # Food CPI
        match = re.search(r'(?:lương thực|thực phẩm).*?(\d+[.,]\d+)\s*%', text, re.IGNORECASE)
        if match:
            val = match.group(1).replace(',', '.')
            data['cpi_food'] = float(val)
        
        # Housing CPI
        match = re.search(r'(?:nhà ở|nhà đất).*?(\d+[.,]\d+)\s*%', text, re.IGNORECASE)
        if match:
            val = match.group(1).replace(',', '.')
            data['cpi_housing'] = float(val)
        
        # Transport CPI
        match = re.search(r'(?:giao thông|vận tải).*?(\d+[.,]\d+)\s*%', text, re.IGNORECASE)
        if match:
            val = match.group(1).replace(',', '.')
            data['cpi_transport'] = float(val)
        
        # Education CPI
        match = re.search(r'giáo\s*dục.*?(\d+[.,]\d+)\s*%', text, re.IGNORECASE)
        if match:
            val = match.group(1).replace(',', '.')
            data['cpi_education'] = float(val)
        
        # Healthcare CPI
        match = re.search(r'y\s*tế.*?(\d+[.,]\d+)\s*%', text, re.IGNORECASE)
        if match:
            val = match.group(1).replace(',', '.')
            data['cpi_healthcare'] = float(val)
        
        # Core CPI
        match = re.search(r'cpi\s*(?:cơ bản|lõi).*?(\d+[.,]\d+)', text, re.IGNORECASE)
        if match:
            val = match.group(1).replace(',', '.')
            data['core_cpi'] = float(val)
        
        # Inflation rate
        inflation_patterns = [
            r'lạm\s*phát.*?(\d+[.,]\d+)\s*%',
            r'tăng.*?giá.*?(\d+[.,]\d+)\s*%'
        ]
        
        for pattern in inflation_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).replace(',', '.')
                data['inflation_rate'] = float(val)
                break
        
        return data
    
    def _extract_retail_fields(self, text: str) -> Dict:
        """Extract retail-specific fields - ENHANCED"""
        data = {}
        
        # Retail value
        retail_patterns = [
            r'bán\s*lẻ.*?(\d+[.,]\d+)\s*tỷ',
            r'hàng\s*hóa.*?bán.*?(\d+[.,]\d+)\s*tỷ',
            r'tổng.*?mức.*?bán.*?(\d+[.,]\d+)\s*tỷ'
        ]
        
        for pattern in retail_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).replace(',', '')
                data['retail_value'] = float(val)
                break
        
        # Services value
        service_patterns = [
            r'dịch\s*vụ.*?(\d+[.,]\d+)\s*tỷ',
            r'doanh\s*thu.*?dịch\s*vụ.*?(\d+[.,]\d+)\s*tỷ',
            r'tiêu\s*dùng.*?dịch\s*vụ.*?(\d+[.,]\d+)\s*tỷ'
        ]
        
        for pattern in service_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).replace(',', '')
                data['services_value'] = float(val)
                break
        
        return data
    
    def _save_to_db(self, indicator_type: str, data: Dict, source_url: str) -> Any:
        """Save data to appropriate table"""
        model_class = self.MODEL_MAP.get(indicator_type)
        if not model_class:
            raise ValueError(f"Unknown indicator type: {indicator_type}")
        
        # Add source
        data['data_source'] = source_url
        
        # Check if record exists
        query = self.db.query(model_class).filter(
            model_class.province == data['province'],
            model_class.year == data['year']
        )
        
        if data.get('quarter'):
            query = query.filter(model_class.quarter == data['quarter'])
        elif data.get('month'):
            query = query.filter(model_class.month == data['month'])
        else:
            query = query.filter(
                model_class.quarter.is_(None),
                model_class.month.is_(None)
            )
        
        existing = query.first()
        
        if existing:
            # Update
            for key, value in data.items():
                if value is not None and hasattr(existing, key):
                    setattr(existing, key, value)
            # Use last_updated from data if available, otherwise current time
            if 'last_updated' not in data:
                existing.last_updated = datetime.now()
            self.db.commit()
            self.db.refresh(existing)
            logger.info(f"    Updated existing record id={existing.id}")
            return existing
        else:
            # Create new
            new_record = model_class(**data)
            self.db.add(new_record)
            self.db.commit()
            self.db.refresh(new_record)
            logger.info(f"    Created new record id={new_record.id}")
            return new_record
