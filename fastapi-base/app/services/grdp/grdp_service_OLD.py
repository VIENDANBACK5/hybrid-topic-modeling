"""
GRDP Extraction Service - Simple Text Extraction

Extract GRDP data from text content using:
- Regex patterns for structured data
- Schema-guided LLM for complex extraction
"""
import re
import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from langchain_openai import ChatOpenAI

from app.models.model_grdp_detail import GRDPDetail

logger = logging.getLogger(__name__)


# ========================================
# OFFICIAL SOURCE CONFIG (Reference only)
# ========================================

OFFICIAL_SOURCES = {
    "statistical_report": {
        "url": "https://thongkehungyen.nso.gov.vn/tinh-hinh-kinh-te-xa-hoi/14",
        "title": "Báo cáo thống kê kinh tế - xã hội",
        "priority": 1
    },
    "executive_summary": {
        "url": "https://hungyen.gov.vn/tong-ket-cong-tac-chi-dao-dieu-hanh-phat-trien-kinh-te-xa-hoi-nam-2025-trien-khai-ke-hoach-dieu-hanh-c284386.html",
        "title": "Tổng kết công tác chỉ đạo, điều hành phát triển kinh tế - xã hội năm 2025",
        "priority": 2
    }
}


# ========================================
# TEXT EXTRACTION
# ========================================

def extract_grdp_data(text: str, year: int = 2025, quarter: Optional[int] = None) -> Dict:
    """
    Extract GRDP data from text using comprehensive regex patterns
    
    Example text:
    'Tổng sản phẩm trên địa bàn tỉnh (GRDP) 9 tháng năm 2025 ước đạt 114.792 tỷ đồng, 
    tăng 8,01% so với cùng kỳ năm 2024...'
    """
        domain = get_domain(url)
        
        # Get domain-specific selectors
        selectors = SELECTORS.get(domain, {
            "content": [".content", "article", ".post"],
            "title": ["h1"],
            "tables": ["table"]
        })
        
        # Extract title
        title = ""
        for selector in selectors.get("title", ["h1"]):
            elem = soup.select_one(selector)
            if elem:
                title = elem.get_text(strip=True)
                break
        
        # Extract main content
        content = ""
        for selector in selectors.get("content", ["article"]):
            elem = soup.select_one(selector)
            if elem:
                content = elem.get_text(separator='\n', strip=True)
                break
        
        if not content:
            content = soup.get_text(separator='\n', strip=True)
        
        # Clean content
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r'\s+', ' ', content)
        
        # Extract tables (for structured data)
        tables = []
        for selector in selectors.get("tables", ["table"]):
            for table in soup.select(selector):
                table_text = table.get_text(separator=' | ', strip=True)
                if len(table_text) > 50:  # Filter out small tables
                    tables.append(table_text)
        
        result = {
            "title": title[:500],
            "content": content[:100000],  # Increased limit
            "tables": tables[:10],  # Max 10 tables
            "url": url,
            "domain": domain
        }
        
        logger.info(f" Parsed: {len(content)} chars, {len(tables)} tables")
        return result
        
    except Exception as e:
        logger.error(f"Parse error: {e}")
        return None


# ========================================
# LAYER 3: DATA EXTRACTION
# ========================================

def extract_from_tables(tables: List[str], year: int = 2025) -> Dict:
    """Extract GRDP from structured tables"""
    result = {}
    
    for table in tables:
        table_lower = table.lower()
        
        # Look for GRDP row in tables
        if 'grdp' in table_lower or 'tổng sản phẩm' in table_lower:
            # Extract value patterns from table cells
            value_match = re.search(r'(\d{2,3})[.,](\d{3})\s*tỷ', table_lower)
            if value_match:
                result['actual_value'] = float(value_match.group(1) + value_match.group(2))
                logger.info(f" Found GRDP in table: {result['actual_value']} tỷ")
            
            # Extract growth rate
            growth_match = re.search(r'tăng\s*(\d+)[.,](\d+)\s*%', table_lower)
            if growth_match:
                result['change_yoy'] = float(f"{growth_match.group(1)}.{growth_match.group(2)}")
                logger.info(f" Found growth in table: {result['change_yoy']}%")
    
    return result


def regex_extract_grdp(text: str, year: int = 2025, tables: Optional[List[str]] = None) -> Dict:
    """
    Extract GRDP data using:
    1. Structured tables (highest priority)
    2. Regex patterns in text
    """
    result = {
        'province': 'Hưng Yên',
        'year': year,
        'quarter': None,
        'period_type': 'year',
        'actual_value': None,
        'change_yoy': None,
        'change_prev_period': None,
        'data_status': 'official'
    }
    
    # Try tables first (more reliable)
    if tables:
        table_data = extract_from_tables(tables, year)
        result.update({k: v for k, v in table_data.items() if v is not None})
    
    text_lower = text.lower()
    
    # GRDP value patterns (support: 114.792, 633.000, 114792)
    # Use .{0,200} to skip text between keyword and number
    patterns = [
        r'grdp.{0,200}?(\d{2,3})[.,](\d{3})\s*tỷ',  # 55.000 or 114.792
        r'tổng sản phẩm.{0,200}?(\d{2,3})[.,](\d{3})\s*tỷ',
        r'grdp.{0,200}?(\d{5,6})\s*tỷ',  # 114792 or 55000
        r'tổng sản phẩm.{0,200}?(\d{5,6})\s*tỷ',
    ]
    
    for p in patterns:
        m = re.search(p, text_lower, re.DOTALL)
        if m:
            if len(m.groups()) == 2:  # Format: 114.792
                val = float(m.group(1) + m.group(2))
            else:  # Format: 114792
                val = float(m.group(1))
            result['actual_value'] = val
            logger.info(f"Found GRDP: {val} tỷ đồng")
            break
    
    # Growth rate patterns  
    growth_patterns = [
        r'grdp.{0,100}?tăng\s*(\d+)[.,](\d+)\s*%',
        r'tổng sản phẩm.{0,100}?tăng\s*(\d+)[.,](\d+)\s*%',
        r'tăng\s*(\d+)[.,](\d+)\s*%.*?grdp',
        r'tăng\s*(\d+)[.,](\d+)\s*%.*?tổng sản phẩm',
    ]
    
    for p in growth_patterns:
        m = re.search(p, text_lower, re.DOTALL)
        if m:
            growth = float(f"{m.group(1)}.{m.group(2)}")
            result['change_yoy'] = growth
            result['change_prev_period'] = growth
            logger.info(f"Found growth: {growth}%")
            break
    
    # Period detection
    if '9 tháng' in text_lower:
        result['quarter'] = 3
        result['period_type'] = 'quarter'
    elif '6 tháng' in text_lower:
        result['quarter'] = 2  
        result['period_type'] = 'quarter'
    
    return result


EXTRACTION_PROMPT = """Bạn là chuyên gia trích xuất dữ liệu kinh tế từ báo cáo thống kê chính thức.

**NHIỆM VỤ**: Trích xuất GRDP (Tổng sản phẩm trên địa bàn) của tỉnh Hưng Yên

**QUY TẮC NGHIÊM NGẶT**:
1.  CHỈ trích xuất số liệu XUẤT HIỆN RÕ RÀNG trong văn bản
2.  TUYỆT ĐỐI KHÔNG suy đoán hoặc tính toán
3.  Nếu không tìm thấy → trả null
4.  Đơn vị: tỷ đồng (không cần chuyển đổi)
5.  Tỷ lệ tăng trưởng: % (so với cùng kỳ năm trước)

**OUTPUT JSON SCHEMA**:
{{
  "province": "Hưng Yên",
  "year": <năm> (number),
  "quarter": <quý 1-4> hoặc null nếu là cả năm (number|null),
  "period_type": "year" hoặc "quarter" (string),
  "actual_value": <giá trị GRDP> (number|null),
  "change_yoy": <tỷ lệ tăng so năm trước> (number|null),
  "data_status": "official"
}}

**VÍ DỤ**:
- "GRDP ước đạt 166.106 tỷ đồng, tăng 8,78%" 
  → {{"actual_value": 166106, "change_yoy": 8.78}}
- "9 tháng đầu năm, tổng sản phẩm tăng 8,20%"
  → {{"quarter": 3, "period_type": "quarter", "change_yoy": 8.20, "actual_value": null}}

**VĂN BẢN CẦN TRÍCH XUẤT**:
<<<
{text}
>>>

**YÊU CẦU**: Chỉ trả về JSON hợp lệ, không giải thích thêm."""


class GRDPLLMExtractor:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found")
        self.llm = ChatOpenAI(
            model="openai/gpt-4o-mini",
            temperature=0,
            openai_api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
    
    def extract(self, text: str) -> Optional[Dict]:
        try:
            prompt = EXTRACTION_PROMPT.format(text=text[:8000])
            result = self.llm.invoke(prompt)
            json_match = re.search(r'\{[^{}]*\}', result.content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.error(f"LLM error: {e}")
        return None


# ========================================
# LAYER 4: VALIDATION
# ========================================

def validate_grdp(data: Dict) -> Tuple[bool, List[str]]:
    """
    Multi-layer validation:
    - Range checks
    - Logic consistency
    - Data completeness
    """
    warnings = []
    is_valid = True
    
    # Validate growth rate
    yoy = data.get('change_yoy')
    if yoy is not None:
        if not (-10 <= yoy <= 20):
            warnings.append(f" change_yoy {yoy}% ngoài khoảng hợp lý (-10% đến 20%)")
            is_valid = False
        elif yoy < 0:
            warnings.append(f"ℹ Tăng trưởng âm {yoy}% (recession)")
    
    # Validate GRDP value
    val = data.get('actual_value')
    if val is not None:
        if not (40000 <= val <= 500000):
            warnings.append(f" GRDP value {val} tỷ ngoài khoảng hợp lý (40-500 nghìn tỷ)")
            is_valid = False
        
        # Check if value is reasonable for Hưng Yên (small province)
        if val > 250000:
            warnings.append(f"ℹ GRDP {val} tỷ rất cao cho tỉnh nhỏ như Hưng Yên")
    
    # Validate QoQ change
    qoq = data.get('change_qoq')
    if qoq is not None and abs(qoq) > 50:
        warnings.append(f" change_qoq {qoq}% quá lớn (không hợp lý)")
        is_valid = False
    
    # Check data completeness
    if not val and not yoy:
        warnings.append(" Không có dữ liệu (cả value và growth đều null)")
        is_valid = False
    
    # Validate year
    year = data.get('year')
    if year and not (2020 <= year <= 2030):
        warnings.append(f" Year {year} ngoài khoảng hợp lý")
        is_valid = False
    
    # Validate quarter
    quarter = data.get('quarter')
    if quarter and not (1 <= quarter <= 4):
        warnings.append(f" Quarter {quarter} không hợp lệ (phải 1-4)")
        is_valid = False
    
    if not warnings:
        warnings.append(" Validation passed")
    
    return is_valid, warnings


# ========================================
# MAIN SERVICE
# ========================================

class GRDPDataExtractor:
    PROVINCE = "Hưng Yên"
    
    def __init__(self, db: Session):
        self.db = db
        self._llm = None
    
    def _get_llm(self):
        if self._llm is None:
            self._llm = GRDPLLMExtractor()
        return self._llm
    
    def extract_from_official(self, source_key: str = "statistical_report", use_llm: bool = True) -> Optional[Dict]:
        """
        ETL Pipeline for official sources:
        1. Smart fetch (Playwright/Requests)
        2. Enhanced parsing with tables
        3. Multi-layer extraction (tables → regex → LLM)
        4. Validation
        """
        source = OFFICIAL_SOURCES.get(source_key)
        if not source:
            logger.error(f"Unknown source: {source_key}")
            return None
        
        url = source['url']
        logger.info(f" Fetching {source['type']} page: {url}")
        
        # Layer 1: Smart scraping
        html = smart_fetch(url, force_playwright=(source['type'] == 'js_rendered'))
        if not html:
            logger.error("Failed to fetch page")
            return None
        
        # Layer 2: Enhanced parsing
        article = parse_article(html, url)
        if not article:
            logger.error("Failed to parse article")
            return None
        
        logger.info(f" {article['title'][:80]}...")
        
        # Layer 3: Multi-layer extraction
        # Step 1: Try tables first (most reliable)
        result = regex_extract_grdp(article['content'], year=2025, tables=article.get('tables', []))
        
        # Step 2: Fallback to LLM if needed
        if use_llm and not result.get('actual_value') and not result.get('change_yoy'):
            logger.info(" Using schema-guided LLM extraction...")
            # Give LLM both content and tables
            full_text = article['content']
            if article.get('tables'):
                full_text += "\n\n=== TABLES ===\n" + "\n\n".join(article['tables'])
            
            llm_result = self._get_llm().extract(full_text[:15000])
            if llm_result:
                result.update({k: v for k, v in llm_result.items() if v is not None})
        
        result['data_source'] = url
        result['province'] = self.PROVINCE
        
        # Layer 4: Validation
        is_valid, warnings = validate_grdp(result)
        for warning in warnings:
            if warning.startswith(''):
                logger.warning(warning)
            else:
                logger.info(warning)
        
        logger.info(f" Extracted: GRDP={result.get('actual_value')} tỷ, Growth={result.get('change_yoy')}%")
        return result
    
    def _try_fetch_forecast_from_previous_report(self, year: int, quarter: Optional[int]) -> Optional[float]:
        """Tìm forecast trong TẤT CẢ bài báo có sẵn (không bắt buộc theo thứ tự)"""
        try:
            logger.info(f" Searching forecast for Q{quarter}/{year} in all available reports...")
            
            # Duyệt qua TẤT CẢ các bài báo trong OFFICIAL_SOURCES
            for source_key, source_info in OFFICIAL_SOURCES.items():
                try:
                    logger.info(f"   Checking {source_key}...")
                    html = smart_fetch(source_info['url'])
                    if not html:
                        continue
                    
                    article = parse_article(html, source_info['url'])
                    if not article:
                        continue
                    
                    text_lower = article['content'].lower()
                    
                    # Tìm forecast cho kỳ hiện tại với nhiều pattern
                    if quarter:
                        forecast_patterns = [
                            rf'dự báo.*?quý\s*{quarter}.*?năm\s*{year}.*?(\d{{3}})[.,](\d{{3}})\s*tỷ',
                            rf'ước\s*tính.*?quý\s*{quarter}.*?năm\s*{year}.*?(\d{{3}})[.,](\d{{3}})\s*tỷ',
                            rf'quý\s*{quarter}.*?{year}.*?dự\s*kiến.*?(\d{{3}})[.,](\d{{3}})\s*tỷ',
                            # Linh hoạt hơn - không cần năm
                            rf'dự báo.*?quý\s*{quarter}.*?(\d{{3}})[.,](\d{{3}})\s*tỷ',
                            rf'ước\s*tính.*?quý\s*{quarter}.*?(\d{{3}})[.,](\d{{3}})\s*tỷ',
                        ]
                    else:
                        # Forecast cho cả năm
                        forecast_patterns = [
                            rf'dự báo.*?năm\s*{year}.*?(\d{{3}})[.,](\d{{3}})\s*tỷ',
                            rf'ước\s*tính.*?năm\s*{year}.*?(\d{{3}})[.,](\d{{3}})\s*tỷ',
                        ]
                    
                    for p in forecast_patterns:
                        m = re.search(p, text_lower)
                        if m:
                            val = float(m.group(1) + m.group(2))
                            logger.info(f" Found forecast in {source_key}: {val} tỷ")
                            return val
                            
                except Exception as e:
                    logger.debug(f"   Error checking {source_key}: {e}")
                    continue
            
            logger.info("ℹ No forecast found in any available reports")
        except Exception as e:
            logger.error(f"Error searching forecasts: {e}")
        return None
    
    def _calculate_missing_fields(self, data: Dict) -> Dict:
        """Tính các trường thiếu từ BẤT KỲ data nào có sẵn trong DB (không bắt buộc liền kề)"""
        if not data.get('actual_value'):
            return data
        
        year = data.get('year')
        quarter = data.get('quarter')
        current_value = float(data['actual_value'])
        
        # Tìm KỲ GẦN NHẤT trước đó (không bắt buộc liền kề)
        query = self.db.query(GRDPDetail).filter(
            GRDPDetail.province == data.get('province', self.PROVINCE),
            GRDPDetail.actual_value.isnot(None)
        )
        
        if quarter:
            # Tìm quý gần nhất trước đó (bất kỳ quý nào < hiện tại)
            query = query.filter(
                or_(
                    and_(GRDPDetail.year == year, GRDPDetail.quarter < quarter),
                    GRDPDetail.year < year
                )
            ).order_by(GRDPDetail.year.desc(), GRDPDetail.quarter.desc())
        else:
            # Data cả năm - tìm năm trước
            query = query.filter(
                GRDPDetail.year < year,
                GRDPDetail.quarter.is_(None)
            ).order_by(GRDPDetail.year.desc())
        
        prev_record = query.first()
        
        if prev_record and prev_record.actual_value:
            prev_value = float(prev_record.actual_value)
            prev_label = f"Q{prev_record.quarter}/{prev_record.year}" if prev_record.quarter else str(prev_record.year)
            
            # Tính change_qoq (nếu là data theo quý và có data trước)
            if quarter and not data.get('change_qoq'):
                change_qoq = ((current_value - prev_value) / prev_value) * 100
                data['change_qoq'] = round(change_qoq, 2)
                logger.info(f" Calculated change_qoq: {data['change_qoq']}% (vs {prev_label})")
            
            # Tính change_prev_period
            if not data.get('change_prev_period') or data.get('change_prev_period') == data.get('change_yoy'):
                change_prev = ((current_value - prev_value) / prev_value) * 100
                data['change_prev_period'] = round(change_prev, 2)
                logger.info(f" Calculated change_prev_period: {data['change_prev_period']}% (vs {prev_label})")
        else:
            logger.info(f" No previous period data found in DB")
        
        return data
    
    def save(self, data: Dict, force_update: bool = True) -> GRDPDetail:
        # Tính các trường thiếu từ data kỳ trước
        data = self._calculate_missing_fields(data)
        
        # Nếu thiếu forecast_value, thử tìm từ bài báo trước
        if not data.get('forecast_value'):
            forecast = self._try_fetch_forecast_from_previous_report(
                year=data['year'],
                quarter=data.get('quarter')
            )
            if forecast:
                data['forecast_value'] = forecast
        
        query = self.db.query(GRDPDetail).filter(
            GRDPDetail.province == data['province'],
            GRDPDetail.year == data['year']
        )
        if data.get('quarter'):
            query = query.filter(GRDPDetail.quarter == data['quarter'])
        else:
            query = query.filter(GRDPDetail.quarter.is_(None))
        
        existing = query.first()
        fields = ['province', 'period_type', 'year', 'quarter', 
                  'actual_value', 'forecast_value', 'change_yoy', 
                  'change_qoq', 'change_prev_period', 'data_status', 'data_source']
        clean_data = {k: data.get(k) for k in fields if k in data}
        
        if existing and force_update:
            for k, v in clean_data.items():
                if v is not None:
                    setattr(existing, k, v)
            existing.last_updated = datetime.now()
            self.db.commit()
            self.db.refresh(existing)
            logger.info(f" Updated id={existing.id}")
            return existing
        
        if not existing:
            new_rec = GRDPDetail(**clean_data)
            self.db.add(new_rec)
            self.db.commit()
            self.db.refresh(new_rec)
            logger.info(f" Created id={new_rec.id}")
            return new_rec
        
        return existing
    
    def extract_from_url(self, url: str, year: int = 2025, quarter: Optional[int] = None,
                         use_llm: bool = True, text_content: Optional[str] = None) -> Optional[Dict]:
        """
        Extract GRDP from custom URL using full ETL pipeline
        Supports both text_content (legacy) and smart scraping
        """
        logger.info(f" Processing custom URL: {url}")
        
        # If user provides text content directly, use it (backward compatible)
        if text_content:
            logger.info(" Using provided text content (legacy mode)")
            article = {
                "title": "User provided",
                "content": text_content,
                "tables": [],
                "url": url
            }
        else:
            # Use smart scraping pipeline
            logger.info(" Using smart scraping pipeline")
            html = smart_fetch(url)
            if not html:
                logger.error("Failed to fetch URL")
                return None
            
            article = parse_article(html, url)
            if not article:
                logger.error("Failed to parse article")
                return None
        
        logger.info(f" Processing: {article.get('title', '')[:80]}...")
        
        # Multi-layer extraction
        result = regex_extract_grdp(article['content'], year=year, tables=article.get('tables', []))
        
        # Fallback to LLM with schema guidance
        if use_llm and not result.get('actual_value') and not result.get('change_yoy'):
            logger.info(" Using schema-guided LLM extraction...")
            full_text = article['content']
            if article.get('tables'):
                full_text += "\n\n=== TABLES ===\n" + "\n\n".join(article['tables'])
            
            llm_result = self._get_llm().extract(full_text[:15000])
            if llm_result:
                result.update({k: v for k, v in llm_result.items() if v is not None})
        
        result['data_source'] = url
        result['province'] = self.PROVINCE
        
        if quarter:
            result['quarter'] = quarter
            result['period_type'] = 'quarter'
        
        # Validation
        is_valid, warnings = validate_grdp(result)
        for warning in warnings:
            if warning.startswith(''):
                logger.warning(warning)
            else:
                logger.info(warning)
        
        logger.info(f" Extracted: GRDP={result.get('actual_value')} tỷ, Growth={result.get('change_yoy')}%")
        return result
    
    def get_or_extract_grdp(self, year: int = 2025, quarter: Optional[int] = None,
                            use_llm: bool = True, force_update: bool = True,
                            source_key: str = "latest") -> Optional[GRDPDetail]:
        data = self.extract_from_official(source_key, use_llm)
        if not data:
            return None
        
        if year:
            data['year'] = year
        if quarter:
            data['quarter'] = quarter
            data['period_type'] = 'quarter'
        
        return self.save(data, force_update)
