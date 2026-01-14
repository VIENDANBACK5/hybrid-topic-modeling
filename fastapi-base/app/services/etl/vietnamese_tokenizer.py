"""
Vietnamese Tokenizer cho BERTopic
Sử dụng underthesea - thư viện NLP tiếng Việt phổ biến nhất
Tích hợp TextCleaner cho preprocessing chuyên sâu
"""
import re
import logging
from typing import List, Callable, Optional

logger = logging.getLogger(__name__)

# Initialize TextCleaner singleton
_text_cleaner = None
_text_cleaner_initialized = False

def get_text_cleaner():
    """Get or create TextCleaner singleton"""
    global _text_cleaner, _text_cleaner_initialized

    if _text_cleaner_initialized:
        return _text_cleaner
    
    _text_cleaner_initialized = True

    if _text_cleaner is None:
        try:
            from app.services.etl.text_cleaner import TextCleaner
            _text_cleaner = TextCleaner()
            logger.info(" TextCleaner initialized for preprocessing")
        except Exception as e:
            logger.warning(f" Could not initialize TextCleaner: {e}")
            _text_cleaner = None
    return _text_cleaner

# Vietnamese stopwords
VIETNAMESE_STOPWORDS = {
    'và', 'của', 'cho', 'với', 'từ', 'trong', 'trên', 'dưới', 'sau', 'trước',
    'khi', 'nếu', 'thì', 'là', 'có', 'được', 'bị', 'sẽ', 'đã', 'đang',
    'mà', 'nhưng', 'hoặc', 'nên', 'để', 'vì', 'do', 'bởi', 'theo', 'về',
    'này', 'đó', 'kia', 'đây', 'đâu', 'nào', 'sao', 'thế', 'vậy', 'thế nào',
    'tôi', 'bạn', 'anh', 'chị', 'em', 'chúng', 'họ', 'mình', 'ta', 'người',
    'cái', 'con', 'chiếc', 'bài', 'việc', 'điều', 'nơi', 'lúc', 'thời',
    'rất', 'quá', 'lắm', 'nhất', 'hơn', 'kém', 'bằng', 'với', 'như',
    'một', 'hai', 'ba', 'bốn', 'năm', 'sáu', 'bảy', 'tám', 'chín', 'mười',
    'nhiều', 'ít', 'tất cả', 'mỗi', 'mọi', 'các', 'những', 'mấy',
    'không', 'chưa', 'chẳng', 'chả', 'đừng', 'không phải',
    'thì', 'là', 'ở', 'tại', 'vào', 'ra', 'lên', 'xuống', 'qua', 'lại',
    'cũng', 'cùng', 'vẫn', 'đều', 'mới', 'còn', 'chỉ', 'mới', 'vừa',
    'nên', 'phải', 'cần', 'nên', 'được', 'bị', 'có thể', 'không thể'
}

def fallback_tokenize(text: str) -> List[str]:
    if not text:
        return []
    text = text.lower().strip()

    return re.findall(
        r'[a-zA-ZÀÁẢÃẠÂẦẤẨẪẬĂẰẮẲẴẶÈÉẺẼẸÊỀẾỂỄỆ'
        r'ÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮ'
        r'ỰỲÝỶỸỴĐ]+', text
    )
_vietnamese_tokenizer = None
_tokenizer_initialized = False
def get_vietnamese_tokenizer() -> Optional[Callable[[str], List[str]]]:
    """
    Tạo Vietnamese tokenizer sử dụng underthesea
    Trả về cả từ đơn và cụm từ có nghĩa (phrases)
    Returns None nếu không cài đặt được, sẽ fallback về simple tokenizer
    """
    global _vietnamese_tokenizer, _tokenizer_initialized

    if _tokenizer_initialized:
        return _vietnamese_tokenizer
    
    _tokenizer_initialized = True
    try:
        from underthesea import word_tokenize
        logger.info(" Sử dụng underthesea cho Vietnamese tokenization với phrase extraction")
        
        cleaner = get_text_cleaner()

        def vietnamese_tokenize(text: str) -> List[str]:
            """Tokenize tiếng Việt với underthesea và tạo cụm từ có nghĩa"""
            if not text or not isinstance(text, str):
                return []
            
            # PREPROCESSING với TextCleaner
            if cleaner:
                # Deep clean: normalize diacritics, expand abbreviations, lowercase
                try:
                    text = cleaner.clean(text, deep_clean=True, tokenize=False)
                except Exception as e:
                    logger.warning(f" Lỗi khi sử dụng TextCleaner: {e}")
                    return fallback_tokenize(text)
            else:
                text = text.lower().strip()
            
            if not text:
                return []
            
            try:
                # Word segmentation với underthesea
                tokens = word_tokenize(text, format="text")
                # Split thành list và filter (giữ nguyên dấu _ để giữ phrases)
                words = tokens.split()
                
                # Filter: loại bỏ stopwords, số, ký tự đặc biệt
                filtered_words = []
                for word in words:
                    # Loại bỏ stopwords
                    if word in VIETNAMESE_STOPWORDS:
                        continue
                    
                    # Loại bỏ số thuần túy
                    if word.isdigit():
                        continue
                    
                    # Loại bỏ từ quá ngắn (< 2 ký tự) hoặc quá dài (> 30)
                    if len(word) < 2 or len(word) > 30:
                        continue
                    
                    # Loại bỏ từ chỉ có ký tự đặc biệt
                    if not re.search(r'[a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', word, re.I):
                        continue
                    
                    filtered_words.append(word)
                
                # Tạo cụm từ có nghĩa (phrases) từ các từ đã filter
                # Nối các từ liên tiếp không phải stopwords thành cụm từ
                phrases = list(filtered_words)
                
                # Thêm từ đơn
                #phrases.extend(filtered_words)
                
                # Tạo bigrams (2 từ)
                for i in range(len(filtered_words) - 1):
                    bigram = f"{filtered_words[i]} {filtered_words[i+1]}"
                    # Chỉ thêm bigram nếu không quá dài và có nghĩa
                    if len(bigram) <= 40:
                        phrases.append(bigram)
                
                # Tạo trigrams (3 từ) cho các cụm từ phổ biến
                for i in range(len(filtered_words) - 2):
                    trigram = f"{filtered_words[i]} {filtered_words[i+1]} {filtered_words[i+2]}"
                    # Chỉ thêm trigram nếu không quá dài
                    if len(trigram) <= 50:
                        phrases.append(trigram)
                
                return phrases
                
            except Exception as e:
                logger.warning(f"Lỗi khi tokenize với underthesea: {e}, fallback về simple tokenizer")
                return fallback_tokenize(text)
        
        _vietnamese_tokenizer = vietnamese_tokenize
        return _vietnamese_tokenizer
        
    except ImportError:
        logger.warning(" underthesea chưa được cài đặt. Sử dụng simple tokenizer.")
        logger.warning(" Cài đặt: pip install underthesea")
        _vietnamese_tokenizer = None
        return None
    except Exception as e:
        logger.warning(f" Lỗi khi khởi tạo underthesea: {e}. Sử dụng simple tokenizer.")
        _vietnamese_tokenizer = None
        return None


def simple_vietnamese_tokenize(text: str) -> List[str]:
    """
    Simple Vietnamese tokenizer fallback
    Tách từ đơn giản dựa trên khoảng trắng và regex
    """
    if not text or not isinstance(text, str):
        return []
    
    # PREPROCESSING với TextCleaner
    cleaner = get_text_cleaner()
    if cleaner:
        text = cleaner.clean(text, deep_clean=True, tokenize=False)
    else:
        text = text.lower().strip()
    
    if not text:
        return []
    
    # Tách từ theo khoảng trắng và dấu câu
    # Giữ lại các từ tiếng Việt (có dấu) và tiếng Anh
    words = re.findall(
        r'[a-zA-ZÀÁẢÃẠÂẦẤẨẪẬĂẰẮẲẴẶÈÉẺẼẸÊỀẾỂỄỆ'
        r'ÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮ'
        r'ỰỲÝỶỸỴĐ]+', text
    )
    
    # Filter
    filtered_words = []
    for word in words:
        # Loại bỏ stopwords
        if word in VIETNAMESE_STOPWORDS:
            continue
        
        # Loại bỏ số
        if word.isdigit():
            continue
        
        # Loại bỏ từ quá ngắn hoặc quá dài
        if len(word) < 2 or len(word) > 30:
            continue
        
        filtered_words.append(word)
    return filtered_words


def create_vietnamese_vectorizer_tokenizer():
    """
    Tạo tokenizer function cho CountVectorizer
    Returns callable function hoặc None
    """
    tokenizer = get_vietnamese_tokenizer()
    
    return tokenizer if tokenizer else fallback_tokenize