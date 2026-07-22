"""
Sentiment Analysis Service - Multi-label
Phân tích cảm xúc văn bản tiếng Việt với nhiều sắc thái

Sắc thái cảm xúc:
- Tích cực: vui_mừng, ủng_hộ, tin_tưởng, hài_lòng
- Tiêu cực: phẫn_nộ, lo_ngại, thất_vọng, chỉ_trích
- Trung tính: trung_lập, hoài_nghi
"""
import logging
from typing import List, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# Định nghĩa các sắc thái cảm xúc
EMOTION_CATEGORIES = {
    # Tích cực
    "vui_mừng": {"vi": "Vui mừng", "group": "positive", "icon": ""},
    "ủng_hộ": {"vi": "Ủng hộ", "group": "positive", "icon": ""},
    "tin_tưởng": {"vi": "Tin tưởng", "group": "positive", "icon": ""},
    "hài_lòng": {"vi": "Hài lòng", "group": "positive", "icon": ""},
    "tự_hào": {"vi": "Tự hào", "group": "positive", "icon": ""},
    "hy_vọng": {"vi": "Hy vọng", "group": "positive", "icon": ""},
    
    # Tiêu cực  
    "phẫn_nộ": {"vi": "Phẫn nộ", "group": "negative", "icon": ""},
    "lo_ngại": {"vi": "Lo ngại", "group": "negative", "icon": ""},
    "thất_vọng": {"vi": "Thất vọng", "group": "negative", "icon": ""},
    "chỉ_trích": {"vi": "Chỉ trích", "group": "negative", "icon": ""},
    "buồn_bã": {"vi": "Buồn bã", "group": "negative", "icon": ""},
    "sợ_hãi": {"vi": "Sợ hãi", "group": "negative", "icon": ""},
    
    # Trung tính
    "trung_lập": {"vi": "Trung lập", "group": "neutral", "icon": ""},
    "hoài_nghi": {"vi": "Hoài nghi", "group": "neutral", "icon": ""},
    "ngạc_nhiên": {"vi": "Ngạc nhiên", "group": "neutral", "icon": ""},
}


@dataclass 
class SentimentResult:
    """Kết quả phân tích cảm xúc đa sắc thái"""
    emotion: str  # vui_mừng, phẫn_nộ, lo_ngại, etc.
    emotion_vi: str  # Vui mừng, Phẫn nộ, etc.
    group: str  # positive, negative, neutral
    group_vi: str  # Tích cực, Tiêu cực, Trung lập
    confidence: float
    icon: str
    all_scores: Dict[str, float]  # Scores cho tất cả emotions


class SentimentAnalyzer:
    """Vietnamese Sentiment Analyzer - Multi-label với 15 sắc thái cảm xúc"""
    
    def __init__(self):
        self._init_emotion_lexicon()
    
    def _init_emotion_lexicon(self):
        """Từ điển cảm xúc đa sắc thái tiếng Việt"""
        
        # === TÍCH CỰC ===
        self.emotion_lexicon = {
            "vui_mừng": {
                "words": {
                    'vui', 'vui vẻ', 'vui mừng', 'hạnh phúc', 'phấn khởi', 'hân hoan',
                    'hồ hởi', 'sung sướng', 'thích thú', 'hài hước', 'cười', 'lạc quan',
                    'hứng khởi', 'tươi vui', 'rạng rỡ', 'tươi cười', 'sảng khoái',
                    'ăn mừng', 'chúc mừng', 'kỷ niệm', 'lễ hội', 'thắng lợi'
                },
                "weight": 1.0
            },
            
            "ủng_hộ": {
                "words": {
                    'ủng hộ', 'đồng ý', 'đồng tình', 'tán thành', 'hưởng ứng', 
                    'chia sẻ', 'cổ vũ', 'khuyến khích', 'động viên', 'hoan nghênh',
                    'chấp nhận', 'công nhận', 'thừa nhận', 'đánh giá cao', 'khen ngợi',
                    'ca ngợi', 'tôn vinh', 'biểu dương', 'ghi nhận', 'trân trọng'
                },
                "weight": 1.0
            },
            
            "tin_tưởng": {
                "words": {
                    'tin tưởng', 'tin cậy', 'đáng tin', 'trung thành', 'chính trực',
                    'minh bạch', 'rõ ràng', 'công khai', 'chính xác', 'xác thực',
                    'uy tín', 'đáng giá', 'cam kết', 'bảo đảm', 'an tâm',
                    'vững chắc', 'kiên định', 'nhất quán', 'chắc chắn'
                },
                "weight": 1.0
            },
            
            "hài_lòng": {
                "words": {
                    'hài lòng', 'thỏa mãn', 'mãn nguyện', 'toại nguyện', 'đáp ứng',
                    'đạt yêu cầu', 'tốt', 'hay', 'đẹp', 'chất lượng', 'hiệu quả',
                    'hoàn hảo', 'tuyệt vời', 'xuất sắc', 'ưu tú', 'nổi bật',
                    'ấn tượng', 'đáng khen', 'khá', 'ổn', 'được'
                },
                "weight": 1.0
            },
            
            "tự_hào": {
                "words": {
                    'tự hào', 'vinh dự', 'vinh quang', 'hãnh diện', 'kiêu hãnh',
                    'thành tựu', 'kỳ tích', 'chiến công', 'danh hiệu', 'kỷ lục',
                    'huy chương', 'giải thưởng', 'đẳng cấp', 'đỉnh cao', 'vô địch',
                    'vương miện', 'ngôi sao', 'anh hùng', 'tiên phong'
                },
                "weight": 1.2
            },
            
            "hy_vọng": {
                "words": {
                    'hy vọng', 'kỳ vọng', 'mong đợi', 'mong chờ', 'triển vọng',
                    'cơ hội', 'tiềm năng', 'khả quan', 'sáng sủa', 'tươi sáng',
                    'phát triển', 'tiến bộ', 'cải thiện', 'nâng cao', 'hồi phục',
                    'khôi phục', 'tái sinh', 'đổi mới', 'đột phá'
                },
                "weight": 1.0
            },
            
            # === TIÊU CỰC ===
            "phẫn_nộ": {
                "words": {
                    'phẫn nộ', 'tức giận', 'giận dữ', 'nổi giận', 'bức xúc',
                    'phản đối', 'lên án', 'tố cáo', 'vạch trần', 'chỉ điểm',
                    'căm phẫn', 'căm hờn', 'căm ghét', 'oán hận', 'thù địch',
                    'bất bình', 'bất mãn', 'uất ức', 'cay cú', 'điên tiết',
                    'ngang ngược', 'trắng trợn', 'quá đáng', 'thái quá'
                },
                "weight": 1.3
            },
            
            "lo_ngại": {
                "words": {
                    'lo ngại', 'lo lắng', 'lo âu', 'quan ngại', 'băn khoăn',
                    'bất an', 'hoang mang', 'hồi hộp', 'căng thẳng', 'áp lực',
                    'nguy cơ', 'rủi ro', 'đe dọa', 'tiềm ẩn', 'bất ổn',
                    'khủng hoảng', 'cảnh báo', 'báo động', 'nghiêm trọng'
                },
                "weight": 1.2
            },
            
            "thất_vọng": {
                "words": {
                    'thất vọng', 'chán nản', 'chán chường', 'thất bại', 'thua cuộc',
                    'không như kỳ vọng', 'kém', 'tệ', 'dở', 'yếu', 'thiếu',
                    'hụt hẫng', 'mất hy vọng', 'bế tắc', 'thất thủ',
                    'xuống dốc', 'suy giảm', 'tụt', 'giảm sút'
                },
                "weight": 1.0
            },
            
            "chỉ_trích": {
                "words": {
                    'chỉ trích', 'phê phán', 'phê bình', 'góp ý', 'nhận xét',
                    'đánh giá tiêu cực', 'phản bác', 'bác bỏ', 'bất đồng',
                    'không đồng ý', 'nghi ngờ', 'chất vấn', 'tra hỏi',
                    'điều tra', 'kiểm tra', 'xem xét', 'thanh tra'
                },
                "weight": 0.8
            },
            
            "buồn_bã": {
                "words": {
                    'buồn', 'buồn bã', 'buồn phiền', 'đau buồn', 'tiếc nuối',
                    'xót xa', 'thương xót', 'thương tiếc', 'chia buồn', 'tang thương',
                    'tủi thân', 'cô đơn', 'lẻ loi', 'trống vắng', 'u sầu',
                    'bi ai', 'bi thương', 'đau lòng', 'xé lòng', 'nước mắt'
                },
                "weight": 1.0
            },
            
            "sợ_hãi": {
                "words": {
                    'sợ hãi', 'sợ', 'khiếp sợ', 'kinh hãi', 'kinh hoàng',
                    'hoảng sợ', 'hoảng loạn', 'run sợ', 'khủng khiếp', 'đáng sợ',
                    'rùng mình', 'ớn lạnh', 'ghê rợn', 'hãi hùng', 'thảm khốc',
                    'bi kịch', 'thảm họa', 'thảm cảnh', 'kinh khủng'
                },
                "weight": 1.2
            },
            
            # === TRUNG TÍNH ===
            "trung_lập": {
                "words": {
                    'bình thường', 'thông báo', 'cho biết', 'phát biểu', 'tuyên bố',
                    'theo', 'theo đó', 'cụ thể', 'chi tiết', 'thông tin',
                    'báo cáo', 'kết quả', 'số liệu', 'thống kê', 'dữ liệu',
                    'ghi nhận', 'diễn ra', 'tổ chức', 'thực hiện', 'tiến hành'
                },
                "weight": 0.5
            },
            
            "hoài_nghi": {
                "words": {
                    'hoài nghi', 'nghi ngờ', 'không chắc', 'chưa rõ', 'mập mờ',
                    'còn tranh cãi', 'gây tranh luận', 'khó nói', 'khó đoán',
                    'bất ngờ', 'kỳ lạ', 'lạ lùng', 'khác thường', 'đáng ngờ',
                    'mơ hồ', 'không rõ ràng', 'lưỡng lự', 'phân vân'
                },
                "weight": 0.8
            },
            
            "ngạc_nhiên": {
                "words": {
                    'ngạc nhiên', 'bất ngờ', 'sửng sốt', 'kinh ngạc', 'choáng',
                    'há hốc', 'trố mắt', 'không tin nổi', 'không ngờ', 'đột ngột',
                    'thình lình', 'bất thình lình', 'ngoài dự kiến', 'lạ',
                    'lần đầu', 'chưa từng', 'hiếm có', 'độc đáo'
                },
                "weight": 0.7
            }
        }
        
        # Từ phủ định và tăng cường
        self.negation_words = {'không', 'chưa', 'chẳng', 'đừng', 'không hề', 'chả', 'chẳng hề'}
        self.intensifiers = {'rất', 'quá', 'cực kỳ', 'vô cùng', 'hết sức', 'siêu', 'thật sự', 'hoàn toàn'}
        self.diminishers = {'hơi', 'khá', 'tương đối', 'có phần', 'một chút'}
    
    def analyze(self, text: str) -> SentimentResult:
        """Phân tích cảm xúc đa sắc thái của văn bản"""
        if not text or not text.strip():
            return self._default_result()
        
        text_lower = text.lower()
        
        # Tính điểm cho từng emotion
        emotion_scores = {}
        for emotion, data in self.emotion_lexicon.items():
            score = self._calculate_emotion_score(text_lower, data["words"], data["weight"])
            emotion_scores[emotion] = score
        
        # Tìm emotion có điểm cao nhất
        if not any(emotion_scores.values()):
            return self._default_result()
        
        # Normalize scores
        total = sum(emotion_scores.values()) + 0.01
        normalized_scores = {k: round(v / total, 4) for k, v in emotion_scores.items()}
        
        # Tìm emotion chính
        main_emotion = max(emotion_scores, key=emotion_scores.get)
        main_score = emotion_scores[main_emotion]
        
        # Nếu điểm thấp, coi như trung lập
        if main_score < 0.5:
            main_emotion = "trung_lập"
        
        emotion_info = EMOTION_CATEGORIES[main_emotion]
        confidence = min(0.95, 0.4 + (main_score / (total + 0.1)) * 0.6)
        
        group_vi_map = {"positive": "Tích cực", "negative": "Tiêu cực", "neutral": "Trung lập"}
        
        return SentimentResult(
            emotion=main_emotion,
            emotion_vi=emotion_info["vi"],
            group=emotion_info["group"],
            group_vi=group_vi_map[emotion_info["group"]],
            confidence=round(confidence, 4),
            icon=emotion_info["icon"],
            all_scores=normalized_scores
        )
    
    def _calculate_emotion_score(self, text: str, words: set, weight: float) -> float:
        """Tính điểm cho một emotion cụ thể"""
        score = 0.0
        text_words = text.split()
        
        # Check từng từ/cụm từ
        for term in words:
            if ' ' in term:
                # Cụm từ
                if term in text:
                    score += 1.5 * weight
            else:
                # Từ đơn
                for i, word in enumerate(text_words):
                    if term in word:
                        multiplier = 1.0
                        # Check intensifier trước đó
                        if i > 0 and text_words[i-1] in self.intensifiers:
                            multiplier = 1.5
                        elif i > 0 and text_words[i-1] in self.diminishers:
                            multiplier = 0.7
                        # Check negation
                        if i > 0 and text_words[i-1] in self.negation_words:
                            score -= 0.5 * weight  # Phủ định
                        else:
                            score += multiplier * weight
        
        return max(0, score)
    
    def _default_result(self) -> SentimentResult:
        """Kết quả mặc định khi không phát hiện cảm xúc"""
        return SentimentResult(
            emotion="trung_lập",
            emotion_vi="Trung lập", 
            group="neutral",
            group_vi="Trung lập",
            confidence=0.6,
            icon="",
            all_scores={k: 0.0 for k in EMOTION_CATEGORIES.keys()}
        )
    
    def analyze_batch(self, texts: List[str]) -> List[SentimentResult]:
        """Phân tích hàng loạt"""
        return [self.analyze(text) for text in texts]
    
    def get_available_emotions(self) -> Dict:
        """Trả về danh sách các sắc thái cảm xúc có sẵn"""
        return EMOTION_CATEGORIES


# Singleton
_analyzer = None

def get_sentiment_analyzer() -> SentimentAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentAnalyzer()
    return _analyzer
