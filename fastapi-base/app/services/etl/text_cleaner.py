import re
import unicodedata
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class TextCleaner:
    """
    Advanced Vietnamese Text Cleaner
    - Normalize Unicode & Vietnamese diacritics
    - Fix common typos & abbreviations
    - Word tokenization with underthesea
    - Remove stopwords
    """
    
    def __init__(self):
        self._init_vietnamese_resources()
    
    def _init_vietnamese_resources(self):
        """Initialize Vietnamese NLP resources"""
        try:
            from underthesea import word_tokenize
            self.word_tokenize = word_tokenize
            logger.info("✅ Underthesea loaded successfully")
        except ImportError:
            logger.warning("⚠️ Underthesea not available, using basic tokenization")
            self.word_tokenize = None
        
        # Vietnamese stopwords (expanded list)
        self.stopwords = {
            'và', 'của', 'có', 'được', 'trong', 'là', 'các', 'với', 'theo', 'này',
            'cho', 'từ', 'để', 'những', 'đã', 'một', 'về', 'được', 'người', 'tại',
            'bị', 'không', 'khi', 'thì', 'vào', 'ra', 'như', 'còn', 'bởi', 'lại',
            'đến', 'ở', 'sau', 'trên', 'đang', 'sẽ', 'làm', 'nên', 'nếu', 'bằng',
            'rằng', 'đây', 'đó', 'nữa', 'nhiều', 'hay', 'mà', 'cả', 'nó', 'họ',
            'ai', 'gì', 'đâu', 'sao', 'thế', 'vì', 'nào', 'đều', 'rất', 'cũng',
            'chỉ', 'nhưng', 'nào', 'giữa', 'trước', 'đi', 'việc', 'nay', 'mỗi'
        }
        
        # Vietnamese abbreviations & chat words normalization
        self.abbreviations = {
            'k': 'không', 'ko': 'không', 'hok': 'không', 'hem': 'không',
            'dc': 'được', 'đc': 'được', 'vs': 'với', 'j': 'gì',
            'h': 'giờ', 'r': 'rồi', 'cx': 'cũng', 'ntn': 'như thế nào',
            'sao': 'sao', 'thế nào': 'thế nào', 'tn': 'Việt Nam',
            'vn': 'Việt Nam', 'tp': 'thành phố', 'tphcm': 'thành phố hồ chí minh',
            'tp.hcm': 'thành phố hồ chí minh', 'hn': 'hà nội', 'hà nội': 'hà nội',
            'đhqg': 'đại học quốc gia', 'ubnd': 'ủy ban nhân dân',
            'ubmttq': 'ủy ban mặt trận tổ quốc', 'bch': 'ban chấp hành',
            'btt': 'bí thư', 'ct': 'chủ tịch', 'ttu': 'thường trực',
            'ttp': 'thành phố', 'tx': 'thị xã', 'tt': 'thị trấn'
        }
        
        # Vietnamese diacritics normalization (common typos)
        self.diacritic_fixes = {
            'hoà': 'hòa', 'hòan': 'hoàn', 'toàn': 'toàn',
            'dùng': 'dùng', 'dùn': 'dùng', 'tìn': 'tìm',
            'thơì': 'thời', 'giơì': 'giời', 'ngươì': 'người'
        }
    
    def clean(self, text: str, language: Optional[str] = 'vi', 
              deep_clean: bool = True, tokenize: bool = False) -> str:
        """
        Clean Vietnamese text with advanced preprocessing
        
        Args:
            text: Input text
            language: Language code (default 'vi')
            deep_clean: Apply Vietnamese-specific cleaning
            tokenize: Return tokenized text (word_tokenize)
        
        Returns:
            Cleaned text
        """
        if not text:
            return ''
        
        # Basic cleaning
        text = self._normalize_unicode(text)
        text = self._remove_html_entities(text)
        text = self._remove_urls(text)
        text = self._remove_emails(text)
        text = self._remove_phone_numbers(text)
        text = self._remove_special_chars(text)
        
        # Vietnamese-specific cleaning
        if deep_clean and language == 'vi':
            text = self._normalize_vietnamese_diacritics(text)
            text = self._expand_abbreviations(text)
            text = text.lower()  # Lowercase for consistency
        
        text = self._normalize_whitespace(text)
        text = self._remove_repeated_chars(text)
        
        # Tokenization
        if tokenize and self.word_tokenize:
            text = self._tokenize_vietnamese(text)
        
        return text.strip()
    
    def clean_for_topic_modeling(self, text: str) -> str:
        """
        Clean text specifically for topic modeling
        - Remove stopwords
        - Tokenize
        - Keep only meaningful words
        """
        # Deep clean
        text = self.clean(text, deep_clean=True, tokenize=True)
        
        # Remove stopwords
        words = text.split()
        words = [w for w in words if w not in self.stopwords and len(w) > 2]
        
        return ' '.join(words)
    
    def _tokenize_vietnamese(self, text: str) -> str:
        """Vietnamese word tokenization using underthesea"""
        try:
            if self.word_tokenize:
                return self.word_tokenize(text, format="text")
            else:
                return text
        except Exception as e:
            logger.warning(f"Tokenization error: {e}")
            return text
    
    def _normalize_vietnamese_diacritics(self, text: str) -> str:
        """Fix common Vietnamese diacritic typos"""
        for wrong, correct in self.diacritic_fixes.items():
            text = re.sub(r'\b' + wrong + r'\b', correct, text, flags=re.IGNORECASE)
        return text
    
    def _expand_abbreviations(self, text: str) -> str:
        """Expand Vietnamese abbreviations and chat words"""
        words = text.split()
        expanded = []
        for word in words:
            word_lower = word.lower()
            # Check if it's an abbreviation
            if word_lower in self.abbreviations:
                expanded.append(self.abbreviations[word_lower])
            else:
                expanded.append(word)
        return ' '.join(expanded)
    
    def _remove_special_chars(self, text: str) -> str:
        """Remove emojis, special characters (keep Vietnamese diacritics)"""
        # Keep Vietnamese characters, numbers, spaces, basic punctuation
        text = re.sub(r'[^\w\sàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ.,!?;:\-]', ' ', text)
        return text
    
    def _normalize_unicode(self, text: str) -> str:
        return unicodedata.normalize('NFC', text)
    
    def _remove_html_entities(self, text: str) -> str:
        text = re.sub(r'&[a-zA-Z]+;', ' ', text)
        text = re.sub(r'&#\d+;', ' ', text)
        return text
    
    def _remove_urls(self, text: str) -> str:
        return re.sub(r'http[s]?://\S+', '', text)
    
    def _remove_emails(self, text: str) -> str:
        return re.sub(r'\S+@\S+', '', text)
    
    def _remove_phone_numbers(self, text: str) -> str:
        return re.sub(r'[\d\s\(\)\-\.]{10,}', '', text)
    
    def _normalize_whitespace(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text
    
    def _remove_repeated_chars(self, text: str) -> str:
        return re.sub(r'(.)\1{3,}', r'\1\1', text)
