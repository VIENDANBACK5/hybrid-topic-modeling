"""
GRDP Extraction Service - Simple Text Input

Extract GRDP data from text content
"""
import re
import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from langchain_openai import ChatOpenAI

from app.models.model_grdp_detail import GRDPDetail

logger = logging.getLogger(__name__)


# ========================================
# TEXT EXTRACTION
# ========================================

def extract_grdp_comprehensive(text: str, year: int = 2025) -> Dict:
    """
    Extract comprehensive GRDP data from text
    
    Example input:
    'Tổng sản phẩm trên địa bàn tỉnh (GRDP) 9 tháng năm 2025 ước đạt 114.792 tỷ đồng, 
    tăng 8,01% so với cùng kỳ năm 2024. Phân theo quý: sơ bộ quý I tăng 8,80%; 
    quý II tăng 7,40%; ước tính quý III tăng 7,93%...'
    """
    text_lower = text.lower()
    
    result = {
        'province': 'Hưng Yên',
        'year': year,
        'quarter': None,
        'period_type': 'year',
        'actual_value': None,
        'forecast_value': None,
        'change_yoy': None,
        'change_qoq': None,
        'change_prev_period': None,
        'data_status': 'official',
        'quarterly_breakdown': {}  # Store Q1, Q2, Q3, Q4 growth rates
    }
    
    # Detect period: 9 tháng (Q3), 6 tháng (Q2), cả năm, etc.
    if '9 tháng' in text_lower or '9 thang' in text_lower:
        result['quarter'] = 3
        result['period_type'] = 'quarter'
        result['period_label'] = '9 tháng'
    elif '6 tháng' in text_lower or '6 thang' in text_lower:
        result['quarter'] = 2
        result['period_type'] = 'quarter'
        result['period_label'] = '6 tháng'
    elif '3 tháng' in text_lower or 'quý i' in text_lower or 'quy i' in text_lower:
        result['quarter'] = 1
        result['period_type'] = 'quarter'
        result['period_label'] = 'Quý I'
    elif 'cả năm' in text_lower or 'ca nam' in text_lower or 'năm ' + str(year) in text_lower:
        result['quarter'] = None
        result['period_type'] = 'year'
        result['period_label'] = f'Cả năm {year}'
    
    # Extract main GRDP value (theo giá so sánh)
    # Patterns: "114.792 tỷ đồng", "166.106 tỷ", "219846 tỷ"
    grdp_patterns = [
        r'grdp.*?ước\s*đạt.*?(\d{2,3})[.,](\d{3})\s*tỷ',  # GRDP ... ước đạt 114.792 tỷ
        r'tổng sản phẩm.*?ước\s*đạt.*?(\d{2,3})[.,](\d{3})\s*tỷ',  # Tổng sản phẩm ... ước đạt
        r'grdp.*?đạt.*?(\d{2,3})[.,](\d{3})\s*tỷ',  # GRDP đạt 166.106 tỷ
        r'tổng sản phẩm.*?đạt.*?(\d{2,3})[.,](\d{3})\s*tỷ',
    ]
    
    for pattern in grdp_patterns:
        match = re.search(pattern, text_lower)
        if match:
            val = float(match.group(1) + match.group(2))
            result['actual_value'] = val
            logger.info(f" Found GRDP: {val} tỷ đồng")
            break
    
    # Extract growth rate (tăng trưởng so với cùng kỳ)
    growth_patterns = [
        r'grdp.*?tăng\s*(\d+)[.,](\d+)\s*%',
        r'tổng sản phẩm.*?tăng\s*(\d+)[.,](\d+)\s*%',
        r'tăng\s*(\d+)[.,](\d+)\s*%.*?(?:so với|cùng kỳ)',
    ]
    
    for pattern in growth_patterns:
        match = re.search(pattern, text_lower)
        if match:
            growth = float(f"{match.group(1)}.{match.group(2)}")
            result['change_yoy'] = growth
            result['change_prev_period'] = growth
            logger.info(f" Found growth YoY: {growth}%")
            break
    
    # Extract quarterly breakdown (quý I tăng X%, quý II tăng Y%)
    quarter_patterns = {
        1: [r'quý\s*i\s*tăng\s*(\d+)[.,](\d+)\s*%', r'quy\s*i\s*tang\s*(\d+)[.,](\d+)\s*%'],
        2: [r'quý\s*ii\s*tăng\s*(\d+)[.,](\d+)\s*%', r'quy\s*ii\s*tang\s*(\d+)[.,](\d+)\s*%'],
        3: [r'quý\s*iii\s*tăng\s*(\d+)[.,](\d+)\s*%', r'quy\s*iii\s*tang\s*(\d+)[.,](\d+)\s*%'],
        4: [r'quý\s*iv\s*tăng\s*(\d+)[.,](\d+)\s*%', r'quy\s*iv\s*tang\s*(\d+)[.,](\d+)\s*%'],
    }
    
    for q, patterns in quarter_patterns.items():
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                growth = float(f"{match.group(1)}.{match.group(2)}")
                result['quarterly_breakdown'][f'Q{q}'] = growth
                logger.info(f" Found Q{q} growth: {growth}%")
                break
    
    # Extract GRDP giá hiện hành (nominal GDP)
    nominal_patterns = [
        r'giá hiện hành.*?(\d{2,3})[.,](\d{3})\s*tỷ',
        r'quy mô kinh tế.*?(\d{2,3})[.,](\d{3})\s*tỷ',
    ]
    
    for pattern in nominal_patterns:
        match = re.search(pattern, text_lower)
        if match:
            nominal_grdp = float(match.group(1) + match.group(2))
            result['grdp_nominal'] = nominal_grdp
            logger.info(f" Found nominal GRDP: {nominal_grdp} tỷ đồng")
            break
    
    # Extract ranking info
    ranking_pattern = r'xếp thứ\s*(\d+)[/\s](\d+)'
    matches = re.findall(ranking_pattern, text_lower)
    if matches:
        if len(matches) >= 1:
            result['ranking_regional'] = f"{matches[0][0]}/{matches[0][1]}"
        if len(matches) >= 2:
            result['ranking_national'] = f"{matches[1][0]}/{matches[1][1]}"
    
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
  "quarterly_breakdown": {{
    "Q1": <tỷ lệ tăng Q1> (number|null),
    "Q2": <tỷ lệ tăng Q2> (number|null),
    "Q3": <tỷ lệ tăng Q3> (number|null),
    "Q4": <tỷ lệ tăng Q4> (number|null)
  }},
  "grdp_nominal": <GRDP giá hiện hành> (number|null),
  "data_status": "official"
}}

**VÍ DỤ**:
Input: "GRDP 9 tháng năm 2025 ước đạt 114.792 tỷ đồng, tăng 8,01% so với cùng kỳ. Quý I tăng 8,80%; quý II tăng 7,40%"
Output: {{"year": 2025, "quarter": 3, "actual_value": 114792, "change_yoy": 8.01, "quarterly_breakdown": {{"Q1": 8.80, "Q2": 7.40}}}}

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
            prompt = EXTRACTION_PROMPT.format(text=text[:15000])
            result = self.llm.invoke(prompt)
            
            # Extract JSON from response
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', result.content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
        return None


def validate_grdp(data: Dict) -> tuple[bool, List[str]]:
    """Validate GRDP data"""
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
    
    # Check completeness
    if not val and not yoy:
        warnings.append(" Không có dữ liệu (cả value và growth đều null)")
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
    
    def extract_from_text(self, text: str, year: int = 2025, quarter: Optional[int] = None,
                         use_llm: bool = True) -> Optional[Dict]:
        """
        Extract GRDP from text content
        
        Args:
            text: Text content containing GRDP data
            year: Year (default 2025)
            quarter: Quarter (1-4) or None for full year
            use_llm: Whether to use LLM if regex fails
        
        Returns:
            Dict with extracted GRDP data
        """
        logger.info(f" Extracting GRDP from text ({len(text)} chars)")
        
        # Step 1: Regex extraction
        result = extract_grdp_comprehensive(text, year=year)
        
        # Step 2: LLM fallback if needed
        if use_llm and not result.get('actual_value') and not result.get('change_yoy'):
            logger.info(" Using LLM for extraction...")
            llm_result = self._get_llm().extract(text)
            if llm_result:
                # Merge LLM results
                for key, value in llm_result.items():
                    if value is not None and key not in ['quarterly_breakdown']:
                        result[key] = value
                # Handle quarterly breakdown separately
                if 'quarterly_breakdown' in llm_result:
                    result['quarterly_breakdown'].update(llm_result['quarterly_breakdown'])
        
        # Override with explicit parameters
        if year:
            result['year'] = year
        if quarter:
            result['quarter'] = quarter
            result['period_type'] = 'quarter'
        
        result['province'] = self.PROVINCE
        
        # Validation
        is_valid, warnings = validate_grdp(result)
        for warning in warnings:
            if warning.startswith(''):
                logger.warning(warning)
            else:
                logger.info(warning)
        
        logger.info(f" Extracted: GRDP={result.get('actual_value')} tỷ, Growth={result.get('change_yoy')}%")
        
        # Check quarterly breakdown
        if result.get('quarterly_breakdown'):
            logger.info(f" Quarterly breakdown: {result['quarterly_breakdown']}")
        
        return result
    
    def _calculate_missing_fields(self, data: Dict) -> Dict:
        """Tính các trường thiếu từ data kỳ trước trong DB"""
        if not data.get('actual_value'):
            return data
        
        year = data.get('year')
        quarter = data.get('quarter')
        current_value = float(data['actual_value'])
        
        # Find previous period
        query = self.db.query(GRDPDetail).filter(
            GRDPDetail.province == data.get('province', self.PROVINCE),
            GRDPDetail.actual_value.isnot(None)
        )
        
        if quarter:
            query = query.filter(
                or_(
                    and_(GRDPDetail.year == year, GRDPDetail.quarter < quarter),
                    GRDPDetail.year < year
                )
            ).order_by(GRDPDetail.year.desc(), GRDPDetail.quarter.desc())
        else:
            query = query.filter(
                GRDPDetail.year < year,
                GRDPDetail.quarter.is_(None)
            ).order_by(GRDPDetail.year.desc())
        
        prev_record = query.first()
        
        if prev_record and prev_record.actual_value:
            prev_value = float(prev_record.actual_value)
            prev_label = f"Q{prev_record.quarter}/{prev_record.year}" if prev_record.quarter else str(prev_record.year)
            
            # Calculate QoQ
            if quarter and not data.get('change_qoq'):
                change_qoq = ((current_value - prev_value) / prev_value) * 100
                data['change_qoq'] = round(change_qoq, 2)
                logger.info(f" Calculated change_qoq: {data['change_qoq']}% (vs {prev_label})")
            
            # Calculate prev_period
            if not data.get('change_prev_period') or data.get('change_prev_period') == data.get('change_yoy'):
                change_prev = ((current_value - prev_value) / prev_value) * 100
                data['change_prev_period'] = round(change_prev, 2)
                logger.info(f" Calculated change_prev_period: {data['change_prev_period']}% (vs {prev_label})")
        
        return data
    
    def save(self, data: Dict, force_update: bool = True) -> GRDPDetail:
        """Save GRDP data to database"""
        # Calculate missing fields
        data = self._calculate_missing_fields(data)
        
        # Find existing record
        query = self.db.query(GRDPDetail).filter(
            GRDPDetail.province == data['province'],
            GRDPDetail.year == data['year']
        )
        if data.get('quarter'):
            query = query.filter(GRDPDetail.quarter == data['quarter'])
        else:
            query = query.filter(GRDPDetail.quarter.is_(None))
        
        existing = query.first()
        
        # Prepare clean data (exclude computed properties like period_label)
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
