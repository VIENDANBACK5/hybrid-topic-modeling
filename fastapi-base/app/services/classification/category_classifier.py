"""
Category Classifier - Phân loại chủ đề tự động
Phân loại nội dung vào các danh mục: Giáo dục, Y tế, Giao thông, Hành chính công...
"""
import logging
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# Định nghĩa các danh mục chủ đề
CATEGORIES = {
    "giao_duc": {
        "vi": "Giáo dục",
        "icon": "📚",
        "keywords": {
            "giáo dục", "học sinh", "sinh viên", "trường học", "đại học", "cao đẳng",
            "tiểu học", "trung học", "mầm non", "giáo viên", "thầy cô", "hiệu trưởng",
            "thi cử", "kỳ thi", "tuyển sinh", "điểm chuẩn", "học phí", "học bổng",
            "sách giáo khoa", "chương trình học", "bộ giáo dục", "đào tạo", "bằng cấp",
            "thạc sĩ", "tiến sĩ", "nghiên cứu sinh", "du học", "trường quốc tế",
            "giảng viên", "lớp học", "bài giảng", "môn học", "điểm số", "học kỳ"
        }
    },
    "y_te": {
        "vi": "Y tế - Sức khỏe",
        "icon": "🏥",
        "keywords": {
            "y tế", "bệnh viện", "bác sĩ", "y bác sĩ", "điều dưỡng", "bệnh nhân",
            "khám bệnh", "chữa bệnh", "thuốc", "vaccine", "tiêm chủng", "dịch bệnh",
            "covid", "corona", "sốt xuất huyết", "cúm", "ung thư", "tim mạch",
            "phẫu thuật", "cấp cứu", "sức khỏe", "dinh dưỡng", "bảo hiểm y tế",
            "phòng khám", "trạm y tế", "bộ y tế", "who", "y tá", "dược", "dược phẩm",
            "bệnh", "điều trị", "chẩn đoán", "xét nghiệm", "tử vong", "ca nhiễm"
        }
    },
    "giao_thong": {
        "vi": "Giao thông",
        "icon": "🚗",
        "keywords": {
            "giao thông", "đường bộ", "đường sắt", "đường thủy", "hàng không",
            "tai nạn", "va chạm", "xe máy", "ô tô", "xe buýt", "tàu điện", "metro",
            "cao tốc", "quốc lộ", "tỉnh lộ", "cầu", "hầm", "nút giao", "ngã tư",
            "tắc đường", "kẹt xe", "ùn tắc", "giờ cao điểm", "bằng lái", "đăng kiểm",
            "csgt", "cảnh sát giao thông", "phạt nguội", "vi phạm", "tốc độ",
            "sân bay", "ga tàu", "bến xe", "cảng", "vận tải", "logistics",
            "grab", "taxi", "xe ôm", "đường sá", "hạ tầng giao thông"
        }
    },
    "hanh_chinh_cong": {
        "vi": "Hành chính công",
        "icon": "🏛️",
        "keywords": {
            "hành chính", "thủ tục", "giấy tờ", "công chứng", "chứng thực",
            "căn cước", "cmnd", "hộ khẩu", "khai sinh", "kết hôn", "đăng ký",
            "ubnd", "ủy ban", "chính quyền", "cơ quan", "công chức", "viên chức",
            "dịch vụ công", "một cửa", "cổng dịch vụ", "số hóa", "chuyển đổi số",
            "cải cách", "phường", "xã", "quận", "huyện", "tỉnh", "thành phố",
            "văn phòng", "hồ sơ", "đơn từ", "giấy phép", "chấp thuận", "phê duyệt"
        }
    },
    "kinh_te": {
        "vi": "Kinh tế - Tài chính",
        "icon": "💰",
        "keywords": {
            "kinh tế", "tài chính", "ngân hàng", "chứng khoán", "cổ phiếu",
            "lãi suất", "tỷ giá", "đô la", "vàng", "bất động sản", "nhà đất",
            "doanh nghiệp", "công ty", "startup", "đầu tư", "vốn", "lợi nhuận",
            "thuế", "xuất khẩu", "nhập khẩu", "thương mại", "fdi", "gdp",
            "lạm phát", "thất nghiệp", "việc làm", "lương", "thu nhập",
            "thị trường", "giá cả", "hàng hóa", "tiêu dùng", "bán lẻ"
        }
    },
    "moi_truong": {
        "vi": "Môi trường",
        "icon": "🌿",
        "keywords": {
            "môi trường", "ô nhiễm", "khí thải", "nước thải", "rác thải",
            "biến đổi khí hậu", "hiệu ứng nhà kính", "nóng lên toàn cầu",
            "thiên tai", "lũ lụt", "hạn hán", "bão", "động đất", "sạt lở",
            "rừng", "phá rừng", "trồng cây", "xanh", "sinh thái", "đa dạng sinh học",
            "năng lượng tái tạo", "điện mặt trời", "điện gió", "xử lý rác",
            "bụi mịn", "pm2.5", "aqi", "chất lượng không khí"
        }
    },
    "an_ninh_phap_luat": {
        "vi": "An ninh - Pháp luật",
        "icon": "⚖️",
        "keywords": {
            "công an", "cảnh sát", "an ninh", "trật tự", "tội phạm", "phạm tội",
            "bắt giữ", "truy nã", "điều tra", "khởi tố", "xét xử", "tòa án",
            "viện kiểm sát", "luật sư", "bị cáo", "bị hại", "án tù", "tử hình",
            "tham nhũng", "hối lộ", "lừa đảo", "trộm cắp", "cướp", "giết người",
            "ma túy", "buôn lậu", "rửa tiền", "vi phạm pháp luật", "hình sự",
            "dân sự", "hành chính", "luật", "nghị định", "thông tư"
        }
    },
    "xa_hoi": {
        "vi": "Xã hội",
        "icon": "👥",
        "keywords": {
            "xã hội", "dân sinh", "đời sống", "cộng đồng", "từ thiện", "nhân đạo",
            "người nghèo", "hộ nghèo", "an sinh", "bảo trợ", "trợ cấp",
            "người già", "trẻ em", "phụ nữ", "người khuyết tật", "dân tộc thiểu số",
            "lao động", "công nhân", "nông dân", "ngư dân", "thất nghiệp",
            "nhà ở", "giá điện", "giá xăng", "giá gas", "vật giá", "đắt đỏ"
        }
    },
    "van_hoa_giai_tri": {
        "vi": "Văn hóa - Giải trí",
        "icon": "🎭",
        "keywords": {
            "văn hóa", "nghệ thuật", "âm nhạc", "ca sĩ", "diễn viên", "nghệ sĩ",
            "phim", "điện ảnh", "gameshow", "truyền hình", "ca nhạc", "concert",
            "festival", "lễ hội", "du lịch", "di sản", "di tích", "bảo tàng",
            "sách", "văn học", "thơ", "nhạc", "hội họa", "nhiếp ảnh",
            "thể thao", "bóng đá", "sea games", "olympic", "cầu thủ", "huấn luyện viên"
        }
    },
    "cong_nghe": {
        "vi": "Công nghệ",
        "icon": "💻",
        "keywords": {
            "công nghệ", "internet", "mạng", "wifi", "4g", "5g", "smartphone",
            "iphone", "android", "laptop", "máy tính", "phần mềm", "ứng dụng",
            "ai", "trí tuệ nhân tạo", "machine learning", "blockchain", "crypto",
            "facebook", "google", "youtube", "tiktok", "zalo", "mạng xã hội",
            "startup công nghệ", "fintech", "edtech", "ecommerce", "online"
        }
    },
    "quoc_te": {
        "vi": "Quốc tế",
        "icon": "🌍",
        "keywords": {
            "quốc tế", "thế giới", "toàn cầu", "nước ngoài", "liên hợp quốc",
            "mỹ", "trung quốc", "nga", "nhật bản", "hàn quốc", "châu âu",
            "asean", "apec", "g7", "g20", "nato", "eu", "who",
            "ngoại giao", "đại sứ", "lãnh sự", "hiệp định", "hợp tác",
            "chiến tranh", "xung đột", "hòa bình", "trừng phạt", "cấm vận"
        }
    },
    "khac": {
        "vi": "Khác",
        "icon": "📌",
        "keywords": set()
    }
}


@dataclass
class ClassificationResult:
    """Kết quả phân loại"""
    category: str  # giao_duc, y_te, ...
    category_vi: str  # Giáo dục, Y tế, ...
    icon: str
    confidence: float
    matched_keywords: List[str]
    all_scores: Dict[str, float]


class CategoryClassifier:
    """Phân loại nội dung vào các danh mục"""
    
    def __init__(self):
        self.categories = CATEGORIES
    
    def classify(self, text: str, title: str = None) -> ClassificationResult:
        """Phân loại nội dung vào danh mục phù hợp nhất"""
        if not text and not title:
            return self._default_result()
        
        # Combine title và content (title có weight cao hơn)
        full_text = f"{(title or '')} {(title or '')} {text or ''}".lower()
        
        # Tính score cho mỗi category
        scores = {}
        matched = {}
        
        for cat_id, cat_info in self.categories.items():
            if cat_id == "khac":
                continue
            
            score = 0
            matches = []
            
            for keyword in cat_info["keywords"]:
                if keyword in full_text:
                    # Keyword dài hơn có weight cao hơn
                    weight = len(keyword.split())
                    score += weight
                    matches.append(keyword)
            
            scores[cat_id] = score
            matched[cat_id] = matches
        
        # Tìm category có score cao nhất
        if not any(scores.values()):
            return self._default_result()
        
        best_cat = max(scores, key=scores.get)
        best_score = scores[best_cat]
        
        # Normalize scores
        total = sum(scores.values()) + 0.01
        normalized = {k: round(v/total, 4) for k, v in scores.items()}
        
        # Confidence dựa trên score
        confidence = min(0.95, 0.3 + (best_score / 10) * 0.65)
        
        cat_info = self.categories[best_cat]
        
        return ClassificationResult(
            category=best_cat,
            category_vi=cat_info["vi"],
            icon=cat_info["icon"],
            confidence=round(confidence, 4),
            matched_keywords=matched[best_cat][:10],
            all_scores=normalized
        )
    
    def classify_batch(self, items: List[Dict]) -> List[ClassificationResult]:
        """Phân loại hàng loạt"""
        return [
            self.classify(item.get("content", ""), item.get("title", ""))
            for item in items
        ]
    
    def _default_result(self) -> ClassificationResult:
        return ClassificationResult(
            category="khac",
            category_vi="Khác",
            icon="📌",
            confidence=0.5,
            matched_keywords=[],
            all_scores={}
        )
    
    def get_categories(self) -> Dict:
        """Trả về danh sách categories"""
        return {
            cat_id: {"vi": info["vi"], "icon": info["icon"]}
            for cat_id, info in self.categories.items()
        }


# Singleton
_classifier = None

def get_category_classifier() -> CategoryClassifier:
    global _classifier
    if _classifier is None:
        _classifier = CategoryClassifier()
    return _classifier
