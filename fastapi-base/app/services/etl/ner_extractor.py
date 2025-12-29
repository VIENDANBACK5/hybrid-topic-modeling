"""
NER Extractor - Named Entity Recognition for Vietnamese text
Extracts: PERSON, ORG, LOCATION, DATE, etc.
"""
import logging
import re
from typing import List, Dict, Optional, Set, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class VietnameseNERExtractor:
    """
    Vietnamese Named Entity Recognition
    
    Features:
    - Rule-based NER for Vietnamese
    - Pattern matching for common entities
    - Organization, Person, Location, Date extraction
    - Optional spaCy integration (if available)
    """
    
    def __init__(self, use_spacy: bool = False):
        """
        Initialize NER Extractor
        
        Args:
            use_spacy: Try to use spaCy if available (optional)
        """
        self.use_spacy = use_spacy
        self.spacy_nlp = None
        
        # Try to load spaCy Vietnamese model
        if use_spacy:
            try:
                import spacy
                # Try Vietnamese model first, fallback to multilingual
                for model_name in ['vi_core_news_lg', 'vi_core_news_md', 'xx_ent_wiki_sm']:
                    try:
                        self.spacy_nlp = spacy.load(model_name)
                        logger.info(f"✅ Loaded spaCy model: {model_name}")
                        break
                    except:
                        continue
                        
                if not self.spacy_nlp:
                    logger.warning("No spaCy Vietnamese model found, using rule-based NER")
            except ImportError:
                logger.warning("spaCy not installed, using rule-based NER")
        
        # Vietnamese entity patterns
        self._init_patterns()
        
        logger.info("NER Extractor initialized")
    
    def _init_patterns(self):
        """Initialize regex patterns for Vietnamese entities"""
        
        # Title patterns for PERSON
        self.person_titles = [
            r'(?:Ông|Bà|Anh|Chị|Cô|Chú|Bác|Dì|Cậu|Mợ)',
            r'(?:Đồng chí|Đ/c|GS|PGS|TS|ThS|BS|KS|CN)',
            r'(?:Giáo sư|Phó giáo sư|Tiến sĩ|Thạc sĩ|Bác sĩ|Kỹ sư)',
            r'(?:Chủ tịch|Phó chủ tịch|Bí thư|Phó bí thư)',
            r'(?:Giám đốc|Phó giám đốc|Tổng giám đốc)',
            r'(?:Trưởng phòng|Phó phòng|Trưởng ban|Phó ban)',
        ]
        
        # Organization patterns
        self.org_patterns = [
            r'(?:Công ty|Cty|CT)\s+(?:TNHH|CP|Cổ phần|Trách nhiệm hữu hạn)?\s*[A-ZÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ][^\.,;!?\n]{2,50}',
            r'(?:Tập đoàn|Tổng công ty)\s+[A-ZÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ][^\.,;!?\n]{2,50}',
            r'(?:Ngân hàng|NH)\s+(?:TMCP|thương mại cổ phần)?\s*[A-ZÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ][^\.,;!?\n]{2,40}',
            r'(?:Trường|Trường Đại học|ĐH|Học viện)\s+[A-ZÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ][^\.,;!?\n]{2,50}',
            r'(?:Bệnh viện|BV)\s+[A-ZÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ][^\.,;!?\n]{2,40}',
            r'(?:Sở|Ban|Ủy ban|UBND|HĐND)\s+[A-ZÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ][^\.,;!?\n]{2,50}',
            r'(?:Bộ|Cục|Vụ|Viện)\s+[A-ZÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ][^\.,;!?\n]{2,50}',
            r'(?:Đảng ủy|Chi bộ|Đảng bộ)\s+[^\.,;!?\n]{2,50}',
        ]
        
        # Location patterns
        self.location_patterns = [
            r'(?:tỉnh|Tỉnh)\s+[A-ZÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ][a-zàáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ\s]{2,30}',
            r'(?:thành phố|TP|Thành phố)\s+[A-ZÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ][a-zàáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ\s]{2,30}',
            r'(?:huyện|Huyện)\s+[A-ZÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ][a-zàáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ\s]{2,30}',
            r'(?:xã|Xã|phường|Phường|thị trấn|Thị trấn)\s+[A-ZÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ][a-zàáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ\s]{2,30}',
            r'(?:quận|Quận)\s+[A-ZÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ0-9][a-zàáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ\s]{0,20}',
        ]
        
        # Vietnamese provinces/cities list
        self.vn_provinces = {
            'Hà Nội', 'Hồ Chí Minh', 'Đà Nẵng', 'Hải Phòng', 'Cần Thơ',
            'An Giang', 'Bà Rịa - Vũng Tàu', 'Bắc Giang', 'Bắc Kạn', 'Bạc Liêu',
            'Bắc Ninh', 'Bến Tre', 'Bình Định', 'Bình Dương', 'Bình Phước',
            'Bình Thuận', 'Cà Mau', 'Cao Bằng', 'Đắk Lắk', 'Đắk Nông',
            'Điện Biên', 'Đồng Nai', 'Đồng Tháp', 'Gia Lai', 'Hà Giang',
            'Hà Nam', 'Hà Tĩnh', 'Hải Dương', 'Hậu Giang', 'Hòa Bình',
            'Hưng Yên', 'Khánh Hòa', 'Kiên Giang', 'Kon Tum', 'Lai Châu',
            'Lâm Đồng', 'Lạng Sơn', 'Lào Cai', 'Long An', 'Nam Định',
            'Nghệ An', 'Ninh Bình', 'Ninh Thuận', 'Phú Thọ', 'Phú Yên',
            'Quảng Bình', 'Quảng Nam', 'Quảng Ngãi', 'Quảng Ninh', 'Quảng Trị',
            'Sóc Trăng', 'Sơn La', 'Tây Ninh', 'Thái Bình', 'Thái Nguyên',
            'Thanh Hóa', 'Thừa Thiên Huế', 'Tiền Giang', 'Trà Vinh', 'Tuyên Quang',
            'Vĩnh Long', 'Vĩnh Phúc', 'Yên Bái'
        }
        
        # Date patterns (Vietnamese)
        self.date_patterns = [
            r'(?:ngày|Ngày)\s+\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'(?:ngày|Ngày)\s+\d{1,2}\s+(?:tháng|thg)\s+\d{1,2}(?:\s+(?:năm)?\s*\d{2,4})?',
            r'(?:tháng|Tháng)\s+\d{1,2}[/-]\d{2,4}',
            r'(?:năm|Năm)\s+\d{4}',
            r'(?:quý|Quý)\s+[IVX1-4]+[/-]?\d{4}',
        ]
        
        # Money patterns
        self.money_patterns = [
            r'\d+(?:[.,]\d{3})*\s*(?:tỷ|triệu|nghìn|ngàn|đồng|VNĐ|USD|EUR)',
            r'\d+(?:[.,]\d+)?\s*(?:tỷ đồng|triệu đồng|nghìn đồng)',
        ]
    
    def extract(self, text: str) -> Dict[str, List[Dict]]:
        """
        Extract named entities from text
        
        Args:
            text: Input text (Vietnamese)
            
        Returns:
            Dict with entity types as keys, list of entities as values
            {
                "PERSON": [{"text": "...", "start": 0, "end": 10}],
                "ORG": [...],
                "LOCATION": [...],
                "DATE": [...],
                "MONEY": [...]
            }
        """
        if not text:
            return {}
        
        entities = defaultdict(list)
        seen = set()  # Avoid duplicates
        
        # Use spaCy if available
        if self.spacy_nlp:
            spacy_entities = self._extract_spacy(text)
            for ent_type, ents in spacy_entities.items():
                for ent in ents:
                    key = (ent_type, ent['text'].lower())
                    if key not in seen:
                        entities[ent_type].append(ent)
                        seen.add(key)
        
        # Rule-based extraction
        rule_entities = self._extract_rules(text)
        for ent_type, ents in rule_entities.items():
            for ent in ents:
                key = (ent_type, ent['text'].lower())
                if key not in seen:
                    entities[ent_type].append(ent)
                    seen.add(key)
        
        return dict(entities)
    
    def _extract_spacy(self, text: str) -> Dict[str, List[Dict]]:
        """Extract entities using spaCy"""
        entities = defaultdict(list)
        
        if not self.spacy_nlp:
            return entities
        
        try:
            doc = self.spacy_nlp(text[:100000])  # Limit text length
            
            for ent in doc.ents:
                ent_type = ent.label_
                # Map spaCy labels to our standard
                type_map = {
                    'PER': 'PERSON',
                    'PERSON': 'PERSON',
                    'ORG': 'ORG',
                    'GPE': 'LOCATION',
                    'LOC': 'LOCATION',
                    'DATE': 'DATE',
                    'TIME': 'DATE',
                    'MONEY': 'MONEY',
                }
                ent_type = type_map.get(ent_type, ent_type)
                
                entities[ent_type].append({
                    'text': ent.text,
                    'start': ent.start_char,
                    'end': ent.end_char,
                    'source': 'spacy'
                })
        except Exception as e:
            logger.warning(f"spaCy extraction error: {e}")
        
        return entities
    
    def _extract_rules(self, text: str) -> Dict[str, List[Dict]]:
        """Extract entities using regex rules"""
        entities = defaultdict(list)
        
        # Extract PERSON (names with titles)
        for title_pattern in self.person_titles:
            # Name pattern after title
            pattern = title_pattern + r'\s+([A-ZÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ][a-zàáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ]+(?:\s+[A-ZÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ][a-zàáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ]+){1,5})'
            for match in re.finditer(pattern, text):
                full_match = match.group(0)
                entities['PERSON'].append({
                    'text': full_match.strip(),
                    'start': match.start(),
                    'end': match.end(),
                    'source': 'rule'
                })
        
        # Extract ORG
        for pattern in self.org_patterns:
            for match in re.finditer(pattern, text):
                entities['ORG'].append({
                    'text': match.group(0).strip(),
                    'start': match.start(),
                    'end': match.end(),
                    'source': 'rule'
                })
        
        # Extract LOCATION
        for pattern in self.location_patterns:
            for match in re.finditer(pattern, text):
                entities['LOCATION'].append({
                    'text': match.group(0).strip(),
                    'start': match.start(),
                    'end': match.end(),
                    'source': 'rule'
                })
        
        # Check for known provinces
        for province in self.vn_provinces:
            for match in re.finditer(re.escape(province), text, re.IGNORECASE):
                entities['LOCATION'].append({
                    'text': province,
                    'start': match.start(),
                    'end': match.end(),
                    'source': 'gazetteer'
                })
        
        # Extract DATE
        for pattern in self.date_patterns:
            for match in re.finditer(pattern, text):
                entities['DATE'].append({
                    'text': match.group(0).strip(),
                    'start': match.start(),
                    'end': match.end(),
                    'source': 'rule'
                })
        
        # Extract MONEY
        for pattern in self.money_patterns:
            for match in re.finditer(pattern, text):
                entities['MONEY'].append({
                    'text': match.group(0).strip(),
                    'start': match.start(),
                    'end': match.end(),
                    'source': 'rule'
                })
        
        return entities
    
    def extract_batch(self, texts: List[str]) -> List[Dict[str, List[Dict]]]:
        """Extract entities from multiple texts"""
        return [self.extract(text) for text in texts]
    
    def get_entity_summary(self, entities: Dict[str, List[Dict]]) -> Dict:
        """Get summary statistics of extracted entities"""
        summary = {
            'total_entities': 0,
            'by_type': {},
            'top_entities': {}
        }
        
        for ent_type, ents in entities.items():
            summary['by_type'][ent_type] = len(ents)
            summary['total_entities'] += len(ents)
            
            # Count frequency
            freq = defaultdict(int)
            for ent in ents:
                freq[ent['text']] += 1
            
            # Top 5 by frequency
            top = sorted(freq.items(), key=lambda x: -x[1])[:5]
            summary['top_entities'][ent_type] = [
                {'text': t, 'count': c} for t, c in top
            ]
        
        return summary


# Singleton instance
_ner_extractor = None

def get_ner_extractor(use_spacy: bool = False) -> VietnameseNERExtractor:
    """Get NER extractor singleton"""
    global _ner_extractor
    if _ner_extractor is None:
        _ner_extractor = VietnameseNERExtractor(use_spacy=use_spacy)
    return _ner_extractor
