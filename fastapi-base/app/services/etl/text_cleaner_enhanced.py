"""
Enhanced text cleaner with more Vietnamese-specific optimizations
"""
import re
import unicodedata
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class TextCleaner:
    """Enhanced text cleaner for Vietnamese content"""
    
    def __init__(self):
        # Vietnamese stopwords (common words to optionally remove)
        self.stopwords = set([
            'và', 'của', 'có', 'được', 'là', 'các', 'trong', 'cho', 'với',
            'này', 'đó', 'để', 'từ', 'về', 'theo', 'như', 'hay', 'hoặc',
            'tại', 'bởi', 'do', 'vì', 'nên', 'mà', 'nhưng', 'khi', 'nếu',
            'thì', 'cũng', 'rằng', 'đã', 'chưa', 'nữa', 'ra', 'vào', 'lại'
            'ở', 'thì', 'là', 'đến', 'đi', 'nói', 'biết', 'muốn', 'phải',
        ])
        
        # Common Vietnamese accents normalization
        self.accent_map = {
            'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
            'ằ': 'ă', 'ắ': 'ă', 'ẳ': 'ă', 'ẵ': 'ă', 'ặ': 'ă',
            'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
            'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
            'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
            'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
            'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y'
        }
    
    def clean(
        self, 
        text: str, 
        language: Optional[str] = 'vi',
        remove_stopwords: bool = False,
        min_word_length: int = 2
    ) -> str:
        """
        Clean text with configurable options
        
        Args:
            text: Input text
            language: Language code ('vi' for Vietnamese)
            remove_stopwords: Whether to remove stopwords
            min_word_length: Minimum word length to keep
        """
        if not text:
            return ''
        
        # Step 1: Normalize Unicode
        text = self._normalize_unicode(text)
        
        # Step 2: Remove HTML tags and entities
        text = self._remove_html(text)
        text = self._remove_html_entities(text)
        
        # Step 3: Remove URLs, emails, phone numbers
        text = self._remove_urls(text)
        text = self._remove_emails(text)
        text = self._remove_phone_numbers(text)
        
        # Step 4: Remove special characters but keep Vietnamese
        text = self._remove_special_chars(text, language)
        
        # Step 5: Normalize whitespace
        text = self._normalize_whitespace(text)
        
        # Step 6: Remove repeated characters (typos)
        text = self._remove_repeated_chars(text)
        
        # Step 7: Remove short words
        if min_word_length > 1:
            text = self._remove_short_words(text, min_word_length)
        
        # Step 8: Remove stopwords (optional)
        if remove_stopwords and language == 'vi':
            text = self._remove_stopwords(text)
        
        return text.strip()
    
    def _normalize_unicode(self, text: str) -> str:
        """Normalize Unicode to NFC form"""
        return unicodedata.normalize('NFC', text)
    
    def _remove_html(self, text: str) -> str:
        """Remove HTML tags"""
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'<!--.*?-->', ' ', text, flags=re.DOTALL)
        return text
    
    def _remove_html_entities(self, text: str) -> str:
        """Remove HTML entities"""
        text = re.sub(r'&[a-zA-Z]+;', ' ', text)
        text = re.sub(r'&#\d+;', ' ', text)
        text = re.sub(r'&#x[0-9a-fA-F]+;', ' ', text)
        return text
    
    def _remove_urls(self, text: str) -> str:
        """Remove URLs"""
        # Remove http(s) URLs
        text = re.sub(r'https?://\S+', '', text)
        # Remove www URLs
        text = re.sub(r'www\.\S+', '', text)
        return text
    
    def _remove_emails(self, text: str) -> str:
        """Remove email addresses"""
        return re.sub(r'\S+@\S+\.\S+', '', text)
    
    def _remove_phone_numbers(self, text: str) -> str:
        """Remove phone numbers (Vietnamese format)"""
        # Vietnamese phone: 0xxx-xxx-xxx or +84-xxx-xxx-xxx
        text = re.sub(r'[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,9}', '', text)
        return text
    
    def _remove_special_chars(self, text: str, language: str = 'vi') -> str:
        """Remove special characters but keep Vietnamese characters"""
        if language == 'vi':
            # Keep Vietnamese characters, alphanumeric, and basic punctuation
            text = re.sub(r'[^\w\s\u00C0-\u1EF9.,!?;:\-()]', ' ', text)
        else:
            # Keep only alphanumeric and basic punctuation
            text = re.sub(r'[^\w\s.,!?;:\-()]', ' ', text)
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace"""
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        # Replace multiple newlines with double newline
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        return text
    
    def _remove_repeated_chars(self, text: str, max_repeat: int = 2) -> str:
        """Remove repeated characters (e.g., 'heeeello' -> 'hello')"""
        pattern = r'(.)\1{' + str(max_repeat) + ',}'
        return re.sub(pattern, r'\1' * max_repeat, text)
    
    def _remove_short_words(self, text: str, min_length: int = 2) -> str:
        """Remove words shorter than min_length"""
        words = text.split()
        filtered_words = [w for w in words if len(w) >= min_length]
        return ' '.join(filtered_words)
    
    def _remove_stopwords(self, text: str) -> str:
        """Remove Vietnamese stopwords"""
        words = text.split()
        filtered_words = [w for w in words if w.lower() not in self.stopwords]
        return ' '.join(filtered_words)
    
    def extract_sentences(self, text: str, min_length: int = 10) -> List[str]:
        """
        Extract sentences from text
        
        Args:
            text: Input text
            min_length: Minimum sentence length in characters
        
        Returns:
            List of sentences
        """
        # Split by sentence-ending punctuation
        sentences = re.split(r'[.!?]+', text)
        
        # Filter and clean
        sentences = [s.strip() for s in sentences if len(s.strip()) >= min_length]
        
        return sentences
    
    def extract_numbers(self, text: str) -> List[str]:
        """Extract all numbers from text"""
        return re.findall(r'\b\d+(?:[.,]\d+)?\b', text)
    
    def extract_dates(self, text: str) -> List[str]:
        """Extract Vietnamese date patterns"""
        patterns = [
            r'\d{1,2}/\d{1,2}/\d{4}',  # DD/MM/YYYY
            r'\d{1,2}-\d{1,2}-\d{4}',  # DD-MM-YYYY
            r'\d{4}-\d{1,2}-\d{1,2}',  # YYYY-MM-DD
            r'ngày \d{1,2} tháng \d{1,2} năm \d{4}'  # Vietnamese format
        ]
        
        dates = []
        for pattern in patterns:
            dates.extend(re.findall(pattern, text, re.IGNORECASE))
        
        return dates
    
    def get_word_count(self, text: str) -> int:
        """Get word count"""
        return len(text.split())
    
    def get_char_count(self, text: str, include_spaces: bool = False) -> int:
        """Get character count"""
        if include_spaces:
            return len(text)
        else:
            return len(text.replace(' ', ''))
