"""
GRDP Extraction Service - Structured Data Extraction Pipeline

Architecture (CHUẨN CÔNG NGHIỆP):
1. Text Normalization - Chuẩn hóa số, đơn vị
2. Chunking - Theo ngữ nghĩa (tiêu đề, đoạn)
3. Candidate Retrieval - BM25 tìm chunks liên quan
4. LLM Extraction - Schema-guided JSON extraction
5. Validation - Rules engine chống hallucination
6. Fill DB - Upsert với conflict resolution

⚠️ LLM KHÔNG phải để search — mà để EXTRACT structured data
"""
import re
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from collections import Counter
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, text

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.models.model_article import Article
from app.models.model_economic_indicators import EconomicIndicator
from app.models.model_grdp_detail import GRDPDetail

logger = logging.getLogger(__name__)


# ========================================
# STEP 1: TEXT NORMALIZATION
# ========================================

def normalize_text(text: str) -> str:
    """
    Chuẩn hóa văn bản:
    - Số: 58.123 → 58123, 8,2 → 8.2
    - Đơn vị: thống nhất
    - Loại bỏ rác (header, footer, quảng cáo)
    """
    if not text:
        return ""
    
    # Loại bỏ URLs
    text = re.sub(r'https?://\S+|www\.\S+', ' ', text)
    
    # Loại bỏ hashtags, mentions
    text = re.sub(r'#\w+|@\w+', ' ', text)
    
    # Chuẩn hóa số có dấu chấm ngăn cách hàng nghìn: 58.123 → 58123
    text = re.sub(r'(\d{1,3})\.(\d{3})(?:\.(\d{3}))?(?!\d)', 
                  lambda m: m.group(1) + m.group(2) + (m.group(3) or ''), text)
    
    # Chuẩn hóa số thập phân: 8,2% → 8.2%
    text = re.sub(r'(\d+),(\d+)', r'\1.\2', text)
    
    # Chuẩn hóa đơn vị
    text = re.sub(r'tỷ\s*(?:VNĐ|đồng|vnđ)', 'tỷ đồng', text, flags=re.IGNORECASE)
    text = re.sub(r'triệu\s*(?:VNĐ|đồng|vnđ)', 'triệu đồng', text, flags=re.IGNORECASE)
    
    # Chuẩn hóa GRDP/GADP
    text = re.sub(r'\bGADP\b', 'GRDP', text, flags=re.IGNORECASE)
    
    # Loại bỏ multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


# ========================================
# STEP 2: SEMANTIC CHUNKING
# ========================================

def chunk_by_semantic(text: str) -> List[Dict[str, Any]]:
    """
    Chunk theo ngữ nghĩa, không phải random tokens.
    Ưu tiên các đoạn có chứa keyword kinh tế.
    """
    chunks = []
    
    # Split theo đoạn (2+ newlines hoặc .)
    paragraphs = re.split(r'\n\s*\n|(?<=[.!?])\s+(?=[A-ZÀÁẢÃẠ])', text)
    
    # Keywords cho GRDP
    grdp_keywords = [
        'grdp', 'gdp', 'tổng sản phẩm', 'quy mô kinh tế',
        'tăng trưởng', 'growth', 'bình quân đầu người',
        'cơ cấu kinh tế', 'nông nghiệp', 'công nghiệp', 'dịch vụ',
        'giá hiện hành', 'giá so sánh'
    ]
    
    for i, para in enumerate(paragraphs):
        para = para.strip()
        if len(para) < 20:  # Bỏ đoạn quá ngắn
            continue
        
        # Tính relevance score
        para_lower = para.lower()
        keyword_count = sum(1 for kw in grdp_keywords if kw in para_lower)
        
        # Có số liệu không?
        has_numbers = bool(re.search(r'\d+(?:\.\d+)?(?:\s*%|\s*tỷ|\s*triệu)', para))
        
        chunks.append({
            'text': para,
            'index': i,
            'keyword_score': keyword_count,
            'has_numbers': has_numbers,
            'relevance': keyword_count * 2 + (3 if has_numbers else 0)
        })
    
    # Sort theo relevance giảm dần
    chunks.sort(key=lambda x: x['relevance'], reverse=True)
    
    return chunks


# ========================================
# STEP 3: CANDIDATE RETRIEVAL (BM25)
# ========================================

def retrieve_grdp_candidates(db: Session, province: str, year: int, limit: int = 20) -> List[Dict]:
    """
    BM25-style search: Tìm articles có khả năng chứa GRDP data.
    Không dùng vector, chỉ keyword matching.
    """
    # Tính date range: year ± 6 tháng
    start_ts = datetime(year - 1, 7, 1).timestamp()
    end_ts = datetime(year + 1, 6, 30).timestamp()
    
    # Query với ILIKE (case-insensitive)
    query = db.query(Article).filter(
        and_(
            Article.published_date >= start_ts,
            Article.published_date <= end_ts,
            or_(
                Article.content.ilike(f'%{province}%'),
                Article.title.ilike(f'%{province}%')
            ),
            or_(
                Article.content.ilike('%GRDP%'),
                Article.content.ilike('%GADP%'),
                Article.content.ilike('%GDP%'),
                Article.content.ilike('%tổng sản phẩm%'),
                Article.content.ilike('%tăng trưởng%'),
                Article.content.ilike('%quy mô kinh tế%')
            )
        )
    ).order_by(desc(Article.published_date)).limit(limit)
    
    articles = query.all()
    
    candidates = []
    for article in articles:
        # Normalize text
        content = normalize_text(f"{article.title}\n\n{article.content}")
        
        # Chunk theo semantic
        chunks = chunk_by_semantic(content)
        
        # Lấy top chunks có relevance cao
        top_chunks = [c for c in chunks if c['relevance'] >= 3][:5]
        
        if top_chunks:
            candidates.append({
                'article_id': article.id,
                'url': article.url,
                'title': article.title,
                'chunks': top_chunks,
                'total_relevance': sum(c['relevance'] for c in top_chunks)
            })
    
    # Sort theo total_relevance
    candidates.sort(key=lambda x: x['total_relevance'], reverse=True)
    
    logger.info(f"📚 Retrieved {len(candidates)} candidate articles with {sum(len(c['chunks']) for c in candidates)} chunks")
    
    return candidates


# ========================================
# STEP 4: LLM EXTRACTION (Schema-guided)
# ========================================

EXTRACTION_PROMPT = """Bạn là chuyên gia trích xuất dữ liệu kinh tế Việt Nam.

NHIỆM VỤ: Trích xuất dữ liệu GRDP từ văn bản vào JSON schema.

QUY TẮC BẮT BUỘC:
1. CHỈ trích xuất số liệu XUẤT HIỆN RÕ RÀNG trong văn bản
2. KHÔNG ước tính, suy đoán, tính toán
3. Nếu không tìm thấy → trả về null
4. Số liệu phải khớp với tỉnh {province} và năm {year}
5. Đơn vị: GRDP = tỷ đồng, bình quân = triệu đồng, tỷ trọng = %

SCHEMA OUTPUT (JSON):
{{
  "province": "string - tên tỉnh",
  "year": number,
  "quarter": number hoặc null,
  "grdp_current_price": number hoặc null (tỷ đồng),
  "grdp_per_capita": number hoặc null (triệu đồng),
  "growth_rate": number hoặc null (%),
  "agriculture_sector_pct": number hoặc null (%),
  "industry_sector_pct": number hoặc null (%),
  "service_sector_pct": number hoặc null (%)
}}

VĂN BẢN CẦN TRÍCH XUẤT:
<<<
{text}
>>>

Trả về CHÍNH XÁC 1 JSON object. Không giải thích."""


class GRDPLLMExtractor:
    """LLM-based structured data extraction"""
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found")
        
        self.llm = ChatOpenAI(
            model="openai/gpt-4o-mini",
            temperature=0,  # Deterministic
            openai_api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
    
    def extract(self, text: str, province: str, year: int) -> Optional[Dict]:
        """Extract GRDP data từ text chunk"""
        try:
            prompt = EXTRACTION_PROMPT.format(
                province=province,
                year=year,
                text=text
            )
            
            result = self.llm.invoke(prompt)
            content = result.content.strip()
            
            # Parse JSON - tìm JSON trong response
            json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return data
            
            return None
            
        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
            return None


# ========================================
# STEP 5: VALIDATION & RULES ENGINE
# ========================================

def validate_grdp_data(data: Dict) -> Tuple[bool, List[str], str]:
    """
    Validate extracted data với business rules.
    
    Returns:
        (is_valid, errors, data_status)
    """
    errors = []
    data_status = "official"
    
    if not data:
        return False, ["Empty data"], "invalid"
    
    # Rule 1: Year phải hợp lệ
    year = data.get('year')
    if year and not (2000 <= year <= 2030):
        errors.append(f"Year {year} out of range [2000-2030]")
    
    # Rule 2: Growth rate phải hợp lý (-20% to 30%)
    growth = data.get('growth_rate')
    if growth is not None:
        if not (-20 <= growth <= 30):
            errors.append(f"Growth rate {growth}% unrealistic")
            data_status = "estimated"
    
    # Rule 3: GRDP phải dương
    grdp = data.get('grdp_current_price')
    if grdp is not None and grdp <= 0:
        errors.append(f"GRDP {grdp} must be positive")
    
    # Rule 4: Tổng cơ cấu ngành ≈ 100%
    sectors = [
        data.get('agriculture_sector_pct'),
        data.get('industry_sector_pct'),
        data.get('service_sector_pct')
    ]
    valid_sectors = [s for s in sectors if s is not None]
    if len(valid_sectors) == 3:
        total = sum(valid_sectors)
        if not (95 <= total <= 105):
            errors.append(f"Sector sum {total}% not ≈ 100%")
            data_status = "estimated"
    
    # Rule 5: Per capita hợp lý (10-500 triệu đồng)
    per_capita = data.get('grdp_per_capita')
    if per_capita is not None:
        if not (10 <= per_capita <= 500):
            errors.append(f"Per capita {per_capita} triệu unrealistic")
            data_status = "estimated"
    
    # Rule 6: GRDP Hưng Yên ~50,000-200,000 tỷ đồng
    if grdp is not None and data.get('province') == 'Hưng Yên':
        if not (30000 <= grdp <= 300000):
            errors.append(f"GRDP {grdp} tỷ unrealistic for Hưng Yên")
            data_status = "estimated"
    
    is_valid = len(errors) == 0
    
    if errors:
        logger.warning(f"⚠️ Validation warnings: {errors}")
    
    return is_valid, errors, data_status


def merge_extractions(extractions: List[Dict]) -> Dict:
    """
    Merge nhiều extractions từ các chunks khác nhau.
    Ưu tiên: giá trị xuất hiện nhiều nhất (voting).
    """
    if not extractions:
        return {}
    
    if len(extractions) == 1:
        return extractions[0]
    
    # Merge field by field
    merged = {}
    fields = [
        'province', 'year', 'quarter',
        'grdp_current_price', 'grdp_per_capita', 'growth_rate',
        'agriculture_sector_pct', 'industry_sector_pct', 'service_sector_pct'
    ]
    
    for field in fields:
        values = [e.get(field) for e in extractions if e.get(field) is not None]
        if values:
            # Lấy giá trị xuất hiện nhiều nhất (voting)
            counter = Counter(values)
            merged[field] = counter.most_common(1)[0][0]
    
    return merged


# ========================================
# STEP 6: MAIN EXTRACTOR SERVICE
# ========================================

class GRDPDataExtractor:
    """
    Main orchestrator cho GRDP extraction pipeline:
    1. Retrieve candidates (BM25)
    2. Chunk semantic
    3. LLM extract (schema-guided)
    4. Validate
    5. Fill DB
    """
    
    PROVINCE = "Hưng Yên"
    
    def __init__(self, db: Session):
        self.db = db
        self.province = self.PROVINCE
        self.llm_extractor = None
    
    def _get_llm_extractor(self):
        """Lazy init LLM extractor"""
        if self.llm_extractor is None:
            self.llm_extractor = GRDPLLMExtractor()
        return self.llm_extractor
    
    def extract_grdp_from_articles(self, year: int, quarter: Optional[int] = None, use_llm: bool = True) -> Optional[Dict]:
        """
        Pipeline chính:
        1. Retrieve candidate articles
        2. Extract từ chunks bằng LLM
        3. Merge & validate
        """
        logger.info(f"🎯 Extracting GRDP: {self.province} - {year}")
        
        # Step 1: Retrieve candidates
        candidates = retrieve_grdp_candidates(self.db, self.province, year, limit=20)
        
        if not candidates:
            logger.info("❌ No candidate articles found")
            return None
        
        logger.info(f"📚 Found {len(candidates)} candidate articles")
        
        # Step 2-3: Extract từ từng chunk
        all_extractions = []
        sources = []
        
        for cand in candidates[:10]:  # Top 10 articles
            article_extractions = []
            
            for chunk in cand['chunks'][:3]:  # Top 3 chunks per article
                if use_llm:
                    # LLM extraction
                    extractor = self._get_llm_extractor()
                    extracted = extractor.extract(
                        text=chunk['text'],
                        province=self.province,
                        year=year
                    )
                else:
                    # Regex fallback
                    extracted = self._regex_extract(chunk['text'], year)
                
                if extracted and any(v is not None for k, v in extracted.items() if k not in ['province', 'year', 'quarter']):
                    article_extractions.append(extracted)
                    logger.info(f"  ✓ Extracted from article {cand['article_id']}: {chunk['text'][:50]}...")
            
            if article_extractions:
                sources.append(cand['url'])
                all_extractions.extend(article_extractions)
        
        if not all_extractions:
            logger.info("❌ No data extracted from any chunks")
            return None
        
        logger.info(f"📊 Total {len(all_extractions)} extractions from {len(sources)} articles")
        
        # Step 4: Merge extractions
        merged = merge_extractions(all_extractions)
        
        # Ensure required fields
        merged['province'] = self.province
        merged['year'] = year
        merged['quarter'] = quarter
        
        # Step 5: Validate
        is_valid, errors, data_status = validate_grdp_data(merged)
        merged['data_status'] = data_status
        merged['data_source'] = ' + '.join(sources[:3])
        
        logger.info(f"✅ Merged result: GRDP={merged.get('grdp_current_price')}, Growth={merged.get('growth_rate')}%")
        
        return merged
    
    def _regex_extract(self, text: str, year: int) -> Dict:
        """Regex-based extraction (fallback khi không dùng LLM)"""
        result = {
            'province': self.province,
            'year': year,
            'quarter': None
        }
        
        text_lower = text.lower()
        
        # GRDP value (tìm số lớn + "tỷ")
        patterns = [
            r'grdp.*?(?:đạt|ước đạt|là)\s*(\d+(?:\.\d+)?)\s*tỷ',
            r'tổng sản phẩm.*?(\d+(?:\.\d+)?)\s*tỷ',
            r'(\d{4,6})\s*tỷ.*?(?:grdp|tổng sản phẩm)',
        ]
        for p in patterns:
            m = re.search(p, text_lower)
            if m:
                try:
                    result['grdp_current_price'] = float(m.group(1))
                    break
                except:
                    pass
        
        # Growth rate
        m = re.search(r'tăng(?:\s+trưởng)?.*?(\d+(?:\.\d+)?)\s*%', text_lower)
        if m:
            try:
                result['growth_rate'] = float(m.group(1))
            except:
                pass
        
        # Per capita
        m = re.search(r'bình quân.*?(\d+(?:\.\d+)?)\s*triệu', text_lower)
        if m:
            try:
                result['grdp_per_capita'] = float(m.group(1))
            except:
                pass
        
        # Sectors
        sectors = {
            'agriculture_sector_pct': r'nông nghiệp.*?(\d+(?:\.\d+)?)\s*%',
            'industry_sector_pct': r'công nghiệp.*?(\d+(?:\.\d+)?)\s*%',
            'service_sector_pct': r'dịch vụ.*?(\d+(?:\.\d+)?)\s*%'
        }
        for field, pattern in sectors.items():
            m = re.search(pattern, text_lower)
            if m:
                try:
                    result[field] = float(m.group(1))
                except:
                    pass
        
        return result
    
    def extract_grdp_from_economic_indicators(self, year: int, quarter: Optional[int] = None) -> Optional[Dict]:
        """Extract từ bảng economic_indicators (đã có sẵn)"""
        try:
            query = self.db.query(EconomicIndicator).filter(
                EconomicIndicator.province == self.province,
                EconomicIndicator.year == year
            )
            
            if quarter:
                query = query.filter(EconomicIndicator.quarter == quarter)
            
            indicator = query.first()
            
            if not indicator:
                return None
            
            result = {
                'province': self.province,
                'year': year,
                'quarter': quarter,
                'data_source': 'economic_indicators table',
                'data_status': 'official'
            }
            
            # Map fields
            field_map = {
                'grdp_current_price': 'grdp_current_price',
                'grdp_per_capita': 'grdp_per_capita',
                'grdp_growth_rate': 'growth_rate'
            }
            
            for src, dst in field_map.items():
                if hasattr(indicator, src):
                    val = getattr(indicator, src)
                    if val is not None:
                        result[dst] = val
            
            return result
            
        except Exception as e:
            logger.error(f"Error reading economic_indicators: {e}")
            return None
    
    def extract_grdp_data(self, year: int, quarter: Optional[int] = None, use_llm: bool = True) -> Optional[Dict]:
        """
        Main extraction: articles → indicators → LLM pure
        """
        # Priority 1: Articles
        logger.info("📄 Step 1: Extracting from articles...")
        data = self.extract_grdp_from_articles(year, quarter, use_llm)
        if data:
            logger.info("✅ Found in articles")
            return data
        
        # Priority 2: Economic Indicators table
        logger.info("📊 Step 2: Checking economic_indicators table...")
        data = self.extract_grdp_from_economic_indicators(year, quarter)
        if data:
            logger.info("✅ Found in economic_indicators")
            return data
        
        logger.info("❌ No GRDP data found")
        return None
    
    def save_grdp_detail(self, data: Dict, force_update: bool = True) -> GRDPDetail:
        """Save/Update vào DB với ON CONFLICT logic"""
        try:
            # Check existing
            query = self.db.query(GRDPDetail).filter(
                GRDPDetail.province == data['province'],
                GRDPDetail.year == data['year']
            )
            
            if data.get('quarter'):
                query = query.filter(GRDPDetail.quarter == data['quarter'])
            else:
                query = query.filter(GRDPDetail.quarter.is_(None))
            
            existing = query.first()
            
            # Clean data - chỉ giữ fields hợp lệ
            clean_fields = [
                'province', 'year', 'quarter',
                'grdp_current_price', 'grdp_per_capita', 'growth_rate',
                'agriculture_sector_pct', 'industry_sector_pct', 'service_sector_pct',
                'rank_national', 'forecast_year_end', 'data_status', 'data_source'
            ]
            clean_data = {k: data.get(k) for k in clean_fields if k in data}
            
            if existing:
                if force_update:
                    for key, value in clean_data.items():
                        if value is not None:
                            setattr(existing, key, value)
                    existing.last_updated = datetime.now()
                    self.db.commit()
                    self.db.refresh(existing)
                    logger.info(f"♻️ Updated GRDP id={existing.id}")
                    return existing
                else:
                    return existing
            else:
                new_record = GRDPDetail(**clean_data)
                self.db.add(new_record)
                self.db.commit()
                self.db.refresh(new_record)
                logger.info(f"✨ Created GRDP id={new_record.id}")
                return new_record
                
        except Exception as e:
            logger.error(f"Save error: {e}")
            self.db.rollback()
            raise
    
    def get_or_extract_grdp(self, year: int, quarter: Optional[int] = None, use_llm: bool = True, force_update: bool = True) -> Optional[GRDPDetail]:
        """Wrapper: extract + save"""
        data = self.extract_grdp_data(year, quarter, use_llm)
        
        if not data:
            return None
        
        return self.save_grdp_detail(data, force_update)
