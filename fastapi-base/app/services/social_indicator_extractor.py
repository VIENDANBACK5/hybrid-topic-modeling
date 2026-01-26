"""
Social Indicator Extractor - Trích xuất chỉ số xã hội từ articles

HIỆN TẠI: 42 bảng detail/statistics trong DB
(Đã mở rộng từ 27 bảng ban đầu)

Pipeline:
    Articles → LLM Classification → Regex Extraction → Validation → DB

NGUYÊN TẮC:
- LLM CHỈ dùng để classify và detect relevance
- Số liệu = REGEX ONLY từ văn bản gốc
- KHÔNG sinh ảo, KHÔNG bịa số - không có thì để NULL

LƯU Ý: File này chỉ define một số indicators cơ bản
Nhiều bảng khác được tạo qua migrations và scripts khác
"""
import re
import logging
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

# LLM imports
try:
    from openai import OpenAI
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


# =============================================================================
# CATEGORY MAPPING - Map article.category to field_key
# =============================================================================
# CHUẨN HÓA: Category chỉ có 8 giá trị mặc định (1-1 mapping)

CATEGORY_TO_FIELD = {
    # 8 giá trị category chuẩn
    "medical": "y_te",                      # Y tế & Chăm sóc sức khỏe
    "education": "giao_duc",                # Giáo dục & Đào tạo
    "transportation": "ha_tang_giao_thong", # Hạ tầng & Giao thông
    "environment": "moi_truong",            # Môi trường & Biến đổi khí hậu
    "policy": "an_sinh_xa_hoi",             # An sinh xã hội & Chính sách
    "security": "an_ninh_trat_tu",          # An ninh, Trật tự & Quốc phòng
    "management": "hanh_chinh_cong",        # Hành chính công & Quản lý Nhà nước
    "politics": "xay_dung_dang",            # Xây dựng Đảng & Hệ thống chính trị
    "society": "van_hoa_the_thao",          # Văn hóa, Thể thao & Đời sống tinh thần
}

# Reverse mapping: field_key -> list of categories
FIELD_TO_CATEGORIES = {}
for cat, field in CATEGORY_TO_FIELD.items():
    if field not in FIELD_TO_CATEGORIES:
        FIELD_TO_CATEGORIES[field] = []
    FIELD_TO_CATEGORIES[field].append(cat)


# =============================================================================
# FIELD DEFINITIONS - 9 Lĩnh vực với keywords và patterns
# =============================================================================

FIELD_DEFINITIONS = {
    # LĨNH VỰC 1: Xây dựng Đảng & Hệ thống chính trị
    "xay_dung_dang": {
        "name": "Xây dựng Đảng & Hệ thống chính trị",
        "province": "Hưng Yên",  # Hard-code tỉnh, không auto-detect
        "indicators": {
            "cadre_statistics": {
                "name": "Thống kê số lượng cán bộ",
                "keywords": ["cán bộ", "công chức", "viên chức", "biên chế", "hợp đồng",
                            "cấp tỉnh", "cấp huyện", "cấp xã", "lao động"],
                # Pre-filter: URL/title patterns để tìm bài liên quan nhanh
                "url_patterns": ["bien-che", "can-bo", "cong-chuc", "vien-chuc", "nhan-su"],
                "title_patterns": ["biên chế", "cán bộ", "công chức", "viên chức", "nhân sự", "tạm giao"],
                # Unit validation: đơn vị mong đợi cho mỗi field
                "units": {
                    "total_authorized": "người",
                    "provincial_level": "người",
                    "commune_level": "người",
                    "contract_workers": "người"
                },
                "patterns": {
                    # Tổng số biên chế: "6.485 người" hoặc "gần 6500 biên chế"
                    # Negative lookahead: không match nếu sau đó là "cấp tỉnh", "cấp xã", "hợp đồng"
                    "total_authorized": r"(?:tổng số|tạm giao|giao|có|gần|khoảng|trên|dưới)(?:[\s\w]{0,30}?)(?<!cấp\s)(?<!tỉnh\s)(?<!xã\s)(\d+[.,]?\d*)\s*(?:người|biên chế|cán bộ|viên chức)(?!.*(?:cấp tỉnh|cấp xã|hợp đồng))",
                    # Cấp tỉnh: "hơn 2.000 biên chế cho cấp tỉnh" hoặc "sở ban ngành 2016 người"
                    "provincial_level": r"(?:cấp tỉnh|tỉnh|sở[,\s]+ban[,\s]+ngành|cơ quan tỉnh)[\s\w,]{0,50}?(?:được giao|giao|nhận|có|hơn|gần)?[\s]*(\d+[.,]?\d*)\s*(?:biên chế|cán bộ|người|viên chức)",
                    # Cấp xã: "hơn 4.400 biên chế cấp xã" hoặc "xã, phường nhận 4469"
                    "commune_level": r"(?:cấp xã|xã[,\s]+phường|phường[,\s]+xã|cấp cơ sở|xã và phường)[\s\w,]{0,50}?(?:được giao|giao|nhận|có|hơn|gần)?[\s]*(\d+[.,]?\d*)\s*(?:biên chế|cán bộ|người|viên chức)",
                    # Hợp đồng: "240 lao động hợp đồng" hoặc "hợp đồng 68 lao động"
                    "contract_workers": r"(?:có|gồm|trong đó)?[\s]*(\d+[.,]?\d*)\s*(?:lao động|người|cán bộ)?[\s]*(?:hợp đồng|làm việc theo hợp đồng)",
                }
            }
        }
    },
    
    # LĨNH VỰC 2: Văn hóa, Thể thao & Đời sống tinh thần
    "van_hoa_the_thao": {
        "name": "Văn hóa, Thể thao & Đời sống tinh thần",
        "province": "Hưng Yên",  # Hard-code tỉnh
        "indicators": {
            "culture_lifestyle_stats": {
                "name": "Thống kê văn hóa và đời sống",
                "keywords": [
                    "di tích", "di sản", "văn hóa phi vật thể", "danh thắng",
                    "khách tham quan", "du khách", "lượt khách", "du lịch văn hóa",
                    "doanh thu du lịch", "phát triển du lịch", "khu du lịch",
                    "lễ hội", "không gian văn hóa", "bảo tàng", "nhà văn hóa"
                ],
                # Pre-filter patterns - CHẶT HƠN
                "url_patterns": [
                    "di-tich", "di-san", "van-hoa", "du-lich", "khach-tham-quan",
                    "danh-thang", "le-hoi", "khu-du-lich", "hung-yen-don-khach"
                ],
                "title_patterns": [
                    "di tích", "di sản", "văn hóa phi vật thể", "danh thắng",
                    "khách tham quan", "du lịch", "lượt khách", "khu du lịch",
                    "lễ hội", "Hưng Yên đón khách", "phát triển du lịch"
                ],
                # Unit validation
                "units": {
                    "total_heritage_sites": "di tích",
                    "tourist_visitors": "lượt",
                    "tourism_revenue_billion": "tỷ"
                },
                "patterns": {
                    # Tổng số di tích: "123 di tích" - PHẢI có từ "di tích" trong context, giới hạn 1-500
                    "total_heritage_sites": r"(?:tổng\s*số|có|hiện\s*có|gồm|quản\s*lý){0,30}\s*((?:[1-9]|[1-9][0-9]|[1-4][0-9]{2}|500))\s*(?:di\s*tích|công\s*trình\s*di\s*tích|danh\s*thắng|di\s*sản)",
                    
                    # Số khách tham quan: "1.5 triệu lượt khách" - PHẢI có context du lịch, từ 0.1-50 triệu
                    "tourist_visitors": r"(?:đón|thu\s*hút|tiếp\s*đón|phục\s*vụ){0,30}\s*([0-9]|[1-4][0-9]|50)(?:[.,][0-9]+)?\s*(triệu|nghìn|ngàn)?\s*(?:lượt|du\s*khách|khách\s*du\s*lịch|lượt\s*khách|người\s*tham\s*quan)",
                    
                    # Doanh thu du lịch: "150 tỷ đồng từ du lịch" - PHẢI có "du lịch" hoặc "văn hóa" trước số, từ 10-10000 tỷ
                    "tourism_revenue_billion": r"(?:doanh\s*thu|thu\s*nhập){0,20}\s*(?:du\s*lịch|văn\s*hóa|từ\s*du\s*lịch){0,30}[^\d]{0,30}([1-9][0-9]{1,3}|10000)\s*tỷ\s*(?:đồng|VNĐ)?",
                }
            }
        }
    },
    
    # LĨNH VỰC 3: Môi trường & Biến đổi khí hậu
    "moi_truong": {
        "name": "Môi trường & Biến đổi khí hậu",
        "indicators": {
            # "air_quality": {
            #     "name": "Chỉ số chất lượng không khí (AQI)",
            #     "keywords": ["chất lượng không khí", "ô nhiễm không khí", "AQI", "bụi mịn", 
            #                 "PM2.5", "PM10", "khí thải"],
            #     "patterns": {
            #         "aqi_score": r"(?:AQI|chỉ số\s*(?:chất lượng)?\s*không khí)[:\s]+(\d+[.,]?\d*)",
            #         "pm25": r"PM2[.,]5[:\s]+(\d+[.,]?\d*)",
            #         "pm10": r"PM10[:\s]+(\d+[.,]?\d*)",
            #         "good_days_pct": r"(\d+[.,]?\d*)\s*%\s*(?:ngày|số ngày)\s*(?:không khí)?\s*(?:tốt|đạt)",
            #     }
            # },
            "climate_resilience": {
                "name": "Khả năng chống chịu biến đổi khí hậu",
                "keywords": ["biến đổi khí hậu", "thiên tai", "lũ lụt", "hạn hán", "bão",
                            "nước biển dâng", "thích ứng", "phòng chống thiên tai"],
                "patterns": {
                    "flood_risk_score": r"(?:rủi ro|nguy cơ)\s*lũ[:\s]+(\d+[.,]?\d*)",
                    "green_coverage_pct": r"(?:tỷ lệ|tỉ lệ)\s*(?:che phủ|phủ xanh|rừng)[:\s]+(\d+[.,]?\d*)\s*%",
                    "adaptation_investment_billion": r"(?:đầu tư|vốn)\s*(?:thích ứng|phòng chống)[:\s]+(\d+(?:[.,]\d+)?)\s*tỷ",
                }
            },
            "waste_management": {
                "name": "Quản lý & xử lý chất thải",
                "keywords": ["rác thải", "chất thải", "thu gom rác", "xử lý rác", "tái chế",
                            "bãi rác", "nước thải", "xử lý nước thải"],
                "patterns": {
                    "waste_collection_rate": r"(?:tỷ lệ|tỉ lệ)\s*thu gom[:\s]+(\d+[.,]?\d*)\s*%",
                    "waste_treatment_rate": r"(?:tỷ lệ|tỉ lệ)\s*xử lý[:\s]+(\d+[.,]?\d*)\s*%",
                    "recycling_rate": r"(?:tỷ lệ|tỉ lệ)\s*tái chế[:\s]+(\d+[.,]?\d*)\s*%",
                    "total_waste_tons": r"(\d+(?:[.,]\d+)?)\s*(?:tấn|nghìn tấn)\s*(?:rác|chất thải)",
                    "wastewater_treatment_rate": r"(?:tỷ lệ|tỉ lệ)\s*xử lý\s*nước thải[:\s]+(\d+[.,]?\d*)\s*%",
                }
            }
        }
    },
    
    # LĨNH VỰC 4: An sinh xã hội & Chính sách
    "an_sinh_xa_hoi": {
        "name": "An sinh xã hội & Chính sách",
        "province": "Hưng Yên",  # Hard-code tỉnh
        "indicators": {
            "hdi": {
                "name": "Chỉ số phát triển con người (HDI)",
                "keywords": ["HDI", "phát triển con người", "tuổi thọ", "giáo dục", "thu nhập bình quân",
                            "chỉ số HDI", "năm đi học", "GNI", "thu nhập đầu người"],
                # Pre-filter patterns
                "url_patterns": ["hdi", "phat-trien-con-nguoi", "tuoi-tho", "thu-nhap", "giao-duc"],
                "title_patterns": ["HDI", "phát triển con người", "tuổi thọ", "thu nhập bình quân", 
                                  "chỉ số HDI", "năm đi học", "GNI"],
                # Unit validation
                "units": {
                    "hdi_score": "điểm (0-1)",
                    "life_expectancy": "năm/tuổi",
                    "mean_schooling_years": "năm",
                    "expected_schooling_years": "năm",
                    "gni_per_capita": "USD/người"
                },
                "patterns": {
                    # 1. Điểm HDI: "HDI đạt 0.725" hoặc "chỉ số HDI 0.7" (0-1)
                    "hdi_score": r"(?:HDI|ch\u1ec9 s\u1ed1\s*(?:HDI|ph\u00e1t tri\u1ec3n\s*con ng\u01b0\u1eddi))[:\s]*(?:\u0111\u1ea1t|\u0111o|\u00f4ng)?[:\s]*(\d+[.,]?\d*)",
                    # 2. Tuổi thọ trung bình: "tuổi thọ 76.5 năm" hoặc "tuổi thọ trung bình đạt 75 tuổi"
                    "life_expectancy": r"tu\u1ed5i th\u1ecd\s*(?:trung b\u00ecnh)?[:\s]*(?:\u0111\u1ea1t|l\u00e0)?[:\s]*(\d+[.,]?\d*)\s*(?:tu\u1ed5i|n\u0103m)",
                    # 3. Số năm đi học trung bình: "số năm đi học 8.5 năm" hoặc "trung bình 9 năm đi học"
                    "mean_schooling_years": r"(?:s\u1ed1 n\u0103m|n\u0103m)\s*(?:\u0111i h\u1ecdc|h\u1ecdc tập|h\u1ecdc v\u1ea5n)\s*(?:trung b\u00ecnh)?[:\s]*(?:\u0111\u1ea1t|l\u00e0)?[:\s]*(\d+[.,]?\d*)\s*n\u0103m",
                    # 4. Số năm đi học kỳ vọng: "kỳ vọng 12.5 năm" hoặc "số năm học kỳ vọng 13 năm"
                    "expected_schooling_years": r"(?:s\u1ed1 n\u0103m h\u1ecdc|n\u0103m \u0111i h\u1ecdc)?\s*k\u1ef3 v\u1ecdng[:\s]*(?:\u0111\u1ea1t|l\u00e0)?[:\s]*(\d+[.,]?\d*)\s*n\u0103m",
                    # 5. Thu nhập bình quân: "GNI 3,500 USD" hoặc "thu nhập đầu người 4000 đô la"
                    "gni_per_capita": r"(?:thu nh\u1eadp|GNI|thu nh\u1eadp \u0111\u1ea7u ng\u01b0\u1eddi|thu nh\u1eadp b\u00ecnh qu\u00e2n)[:\s]*(?:\u0111\u1ea1t|l\u00e0)?[:\s]*(\d+(?:[.,]\d+)?)\s*(?:USD|\u0111\u00f4 la|dollar)",
                }
            },
            "social_security_coverage": {
                "name": "Tỷ lệ bao phủ an sinh xã hội",
                "keywords": ["bảo hiểm xã hội", "BHXH", "bảo hiểm y tế", "BHYT", "lương hưu",
                            "trợ cấp", "bảo hiểm thất nghiệp", "an sinh"],
                "patterns": {
                    "coverage_rate": r"(?:tỷ lệ|tỉ lệ)\s*(?:bao phủ|tham gia)\s*(?:an sinh|BHXH)[:\s]+(\d+[.,]?\d*)\s*%",
                    "health_insurance_coverage": r"(?:tỷ lệ|tỉ lệ)\s*(?:bao phủ|tham gia)\s*(?:BHYT|bảo hiểm y tế)[:\s]+(\d+[.,]?\d*)\s*%",
                    "social_insurance_coverage": r"(?:tỷ lệ|tỉ lệ)\s*(?:bao phủ|tham gia)\s*(?:BHXH|bảo hiểm xã hội)[:\s]+(\d+[.,]?\d*)\s*%",
                    "beneficiaries_count": r"(\d+(?:[.,]\d+)?)\s*(?:người|lao động)\s*(?:tham gia|thụ hưởng)",
                }
            },
            "social_budget": {
                "name": "Chi ngân sách cho an sinh xã hội",
                "keywords": ["ngân sách an sinh", "chi xã hội", "trợ cấp xã hội", "giảm nghèo",
                            "bảo trợ xã hội", "hỗ trợ người nghèo"],
                "patterns": {
                    "social_budget_pct": r"(?:tỷ lệ|tỉ lệ|tỷ trọng)\s*chi\s*(?:an sinh|xã hội)[:\s]+(\d+[.,]?\d*)\s*%",
                    "total_social_budget_billion": r"chi\s*(?:an sinh|xã hội)[:\s]+(\d+(?:[.,]\d+)?)\s*tỷ",
                    "poverty_reduction_billion": r"chi\s*(?:giảm nghèo|xóa đói)[:\s]+(\d+(?:[.,]\d+)?)\s*tỷ",
                    "budget_execution_rate": r"(?:tỷ lệ|tỉ lệ)\s*giải ngân[:\s]+(\d+[.,]?\d*)\s*%",
                }
            }
        }
    },
    
    # LĨNH VỰC 5: An ninh, Trật tự & Quốc phòng
    "an_ninh_trat_tu": {
        "name": "An ninh, Trật tự & Quốc phòng",
        "province": "Hưng Yên",
        "url_patterns": [
            "ma-tuy", "phong-chong-ma-tuy", "bat-giu-ma-tuy",
            "toi-pham", "an-ninh", "cong-an", "phong-chong-toi-pham",
            "hung-yen-bat-giu", "hung-yen-phat-hien",
            "tong-ket-cong-an-hung-yen", "bao-cao-trat-tu"
        ],
        "title_patterns": [
            "ma túy", "phòng chống ma túy", "bắt giữ ma túy", "tang vật ma túy",
            "tội phạm", "giảm tội phạm", "an ninh", "công an",
            "Hưng Yên bắt giữ", "Hưng Yên phát hiện", "tổng kết công an",
            "an ninh Hưng Yên", "Hưng Yên triệt phá", "công an Hưng Yên"
        ],
        "indicators": {
            "security": {
                "name": "An ninh trật tự",
                "keywords": [
                    "ma túy", "ma tuý", "phòng chống ma túy", "bắt giữ ma túy",
                    "vụ ma túy", "đối tượng ma túy", "tang vật ma túy",
                    "tội phạm", "giảm tội phạm", "phòng chống tội phạm",
                    "an ninh trật tự", "ANTT", "công an", "lực lượng công an",
                    "tổng kết công tác", "báo cáo an ninh", "toàn tỉnh", "địa bàn"
                ],
                "patterns": {
                    # Số vụ ma túy - BẮT BUỘC phải có "Hưng Yên/toàn tỉnh/địa bàn" trong context gần
                    # TRÁNH: "cả nước", "toàn quốc" bằng negative lookahead
                    # VD: "Năm 2024, trên địa bàn Hưng Yên phát hiện 125 vụ ma túy"
                    "drug_cases": r"(?:Hưng\s*Yên|toàn\s*tỉnh|địa\s*bàn)(?:(?!cả\s*nước|toàn\s*quốc).){0,300}?(?:phát\s*hiện|bắt\s*giữ|xử\s*lý|triệt\s*phá|phá)[\s\S]{0,100}?(\d{2,4})\s*vụ[\s\S]{0,50}?(?:ma\s*túy|vi\s*phạm)",
                    
                    # Số người vi phạm ma túy - BẮT BUỘC context tỉnh
                    # VD: "Công an Hưng Yên bắt giữ 250 đối tượng ma túy"
                    "drug_offenders": r"(?:Hưng\s*Yên|toàn\s*tỉnh|địa\s*bàn)(?:(?!cả\s*nước|toàn\s*quốc).){0,300}?(?:bắt\s*giữ|khởi\s*tố|xử\s*lý)[\s\S]{0,100}?(\d{2,4})\s*(?:đối\s*tượng|người|trường\s*hợp)[\s\S]{0,100}?(?:ma\s*túy|vi\s*phạm)",
                    
                    # Tỷ lệ giảm tội phạm - BẮT BUỘC context tỉnh, tránh con số quá cao (>30% không thực tế)
                    # VD: "Toàn tỉnh tội phạm giảm 15%"
                    "crime_reduction_rate": r"(?:Hưng\s*Yên|toàn\s*tỉnh|địa\s*bàn)(?:(?!cả\s*nước|toàn\s*quốc).){0,300}?(?:tội\s*phạm|vụ\s*án)[\s\S]{0,100}?giảm[\s\S]{0,50}?(\d{1,2})\s*%",
                },
                "units": {
                    "drug_cases": "vụ",
                    "drug_offenders": "người",
                    "crime_reduction_rate": "%"
                }
            }
        }
    },
    
    # LĨNH VỰC 6: Hành chính công & Quản lý Nhà nước
    "hanh_chinh_cong": {
        "name": "Hành chính công & Quản lý Nhà nước",
        "province": "Hưng Yên",
        "url_patterns": [
            "par-index", "par", "cai-cach-hanh-chinh", "cchc", 
            "sipas", "hai-long", "dich-vu-cong", "mot-cua", 
            "thu-tuc-hanh-chinh", "chuyen-doi-so", "hung-yen-nang-cao"
        ],
        "title_patterns": [
            "PAR Index", "PAR-Index", "cải cách hành chính", "CCHC",
            "SIPAS", "hài lòng", "sự hài lòng", "dịch vụ công",
            "thủ tục hành chính", "một cửa", "chuyển đổi số",
            "Hưng Yên nâng cao", "chất lượng phục vụ"
        ],
        "indicators": {
            "par_index": {
                "name": "Chỉ số cải cách hành chính (PAR Index)",
                "keywords": [
                    "PAR Index", "PAR-Index", "chỉ số PAR", "cải cách hành chính", 
                    "CCHC", "thủ tục hành chính", "TTHC", "dịch vụ công", 
                    "một cửa", "bộ phận một cửa", "thủ tục đơn giản hóa",
                    "cải thiện môi trường kinh doanh", "PCI", "DDCI",
                    "giải quyết hồ sơ", "tiếp nhận hồ sơ", "trả kết quả",
                    "cắt giảm thời gian", "rút ngắn quy trình"
                ],
                "patterns": {
                    "par_index_score": r"(?:PAR[\s-]*Index|chỉ\s*số\s*(?:cải\s*cách\s*)?hành\s*chính|CCHC){0,50}[^\d]{0,50}(?:đạt|là|đứng|xếp|hạng|điểm)?{0,50}[:\s]*(\d+[.,]?\d*)\s*(?:điểm|%)?",
                    "admin_procedure_score": r"(?:điểm|chỉ\s*số|kết\s*quả){0,30}\s*(?:thủ\s*tục|TTHC){0,30}\s*(?:hành\s*chính)?{0,50}[:\s]*(\d+[.,]?\d*)\s*(?:điểm|%)?",
                    "onestop_processing_rate": r"(?:tỷ\s*lệ|tỉ\s*lệ){0,20}\s*giải\s*quyết{0,30}(?:đúng|trước)?\s*(?:hạn|thời\s*gian)?{0,50}[:\s]*(\d+[.,]?\d*)\s*%",
                    "simplified_procedures_count": r"(\d+(?:[.,]\d+)?)\s*(?:thủ\s*tục|TTHC|quy\s*trình){0,30}\s*(?:đơn\s*giản|rút\s*gọn|cắt\s*giảm)",
                },
                "units": {
                    "par_index_score": "điểm",
                    "admin_procedure_score": "điểm",
                    "onestop_processing_rate": "%",
                    "simplified_procedures_count": "thủ tục"
                }
            },
            "sipas": {
                "name": "Chỉ số hài lòng của người dân (SIPAS)",
                "keywords": [
                    "SIPAS", "chỉ số SIPAS", "chỉ số hài lòng", "sự hài lòng", 
                    "mức độ hài lòng", "đánh giá người dân", "đánh giá của dân", 
                    "khảo sát hài lòng", "khảo sát người dân", "phản hồi người dân",
                    "chất lượng phục vụ", "thái độ cán bộ", "tiếp dân",
                    "giải quyết khiếu nại", "giải quyết thắc mắc"
                ],
                "patterns": {
                    "sipas_score": r"(?:SIPAS|chỉ\s*số\s*hài\s*lòng|mức\s*độ\s*hài\s*lòng){0,50}[^\d]{0,50}(?:đạt|là|đứng|xếp|hạng|điểm)?{0,50}[:\s]*(\d+[.,]?\d*)\s*(?:điểm|%)?",
                    "service_access_score": r"(?:điểm|chỉ\s*số|đánh\s*giá){0,30}\s*(?:tiếp\s*cận|dễ\s*dàng\s*tiếp\s*cận){0,50}[:\s]*(\d+[.,]?\d*)\s*(?:điểm|%)?",
                    "respondents_count": r"(\d+(?:[.,]\d+)?)\s*(?:người|phản\s*hồi|người\s*được\s*khảo\s*sát|người\s*tham\s*gia|mẫu)",
                    "satisfaction_rate": r"(?:tỷ\s*lệ|tỉ\s*lệ){0,20}\s*hài\s*lòng{0,50}[:\s]*(\d+[.,]?\d*)\s*%",
                },
                "units": {
                    "sipas_score": "điểm",
                    "service_access_score": "điểm",
                    "respondents_count": "người",
                    "satisfaction_rate": "%"
                }
            },
            "egovernment": {
                "name": "Chính phủ số / E-Government",
                "keywords": ["chính phủ số", "chính quyền số", "dịch vụ công trực tuyến", 
                            "chuyển đổi số", "số hóa", "DVCTT mức độ 4"],
                "patterns": {
                    "online_services_count": r"(\d+)\s*dịch vụ\s*(?:công)?\s*trực tuyến",
                    "level_4_services_count": r"(\d+)\s*(?:dịch vụ|DVCTT)\s*mức độ 4",
                    "online_transaction_rate": r"(?:tỷ lệ|tỉ lệ)\s*(?:giao dịch|hồ sơ)\s*trực tuyến[:\s]+(\d+[.,]?\d*)\s*%",
                    "digital_document_rate": r"(?:tỷ lệ|tỉ lệ)\s*(?:số hóa|điện tử hóa)[:\s]+(\d+[.,]?\d*)\s*%",
                }
            }
        }
    },
    
    # LĨNH VỰC 7: Y tế & Chăm sóc sức khỏe
    "y_te": {
        "name": "Y tế & Chăm sóc sức khỏe",
        "province": "Hưng Yên",  # Hard-code tỉnh
        "indicators": {
            "health_statistics": {
                "name": "Thống kê Y tế & Dân số",
                "keywords": ["bảo hiểm y tế", "BHYT", "dân số", "cao tuổi", "khám sức khỏe", 
                            "tỷ số giới tính", "khai sinh", "tham gia BHYT"],
                # Pre-filter patterns
                "url_patterns": ["bao-hiem-y-te", "bhyt", "dan-so", "cao-tuoi", "khai-sinh"],
                "title_patterns": ["bảo hiểm y tế", "BHYT", "dân số", "cao tuổi", "khám sức khỏe", "tỷ số giới tính"],
                # Unit validation
                "units": {
                    "bhyt_coverage_rate": "%",
                    "total_insured": "người",
                    "voluntary_insured": "người",
                    "natural_population_growth_rate": "%",
                    "elderly_health_checkup_rate": "%",
                    "sex_ratio_at_birth": "ratio"
                },
                "patterns": {
                    # 1. Tỷ lệ bao phủ BHYT: "95.5% dân số tham gia BHYT" (phải có %)
                    "bhyt_coverage_rate": r"(?:tỷ lệ|tỉ lệ|tỷ suất)\s*(?:bao phủ|tham gia|người có)\s*(?:BHYT|bảo hiểm y tế)[:\s]*(?:đạt)?[:\s]*(\d+[.,]?\d*)\s*%",
                    # 2. Số người tham gia BHYT: "950 nghìn người" hoặc "950.000 người có BHYT"
                    # Phải xử lý "nghìn", "triệu" trong code, regex chỉ lấy số + unit
                    "total_insured": r"(?:có|gồm)?[\s]*(\d+[.,]?\d*)\s*(nghìn|ngàn|triệu)?\s*(?:người|thẻ|hộ)\s*(?:có|tham gia|được cấp|đang tham gia)\s*(?:BHYT|bảo hiểm y tế)",
                    # 3. Số người BHYT tự nguyện: "120 nghìn người tự nguyện"
                    "voluntary_insured": r"(\d+[.,]?\d*)\s*(nghìn|ngàn|triệu)?\s*(?:người|hộ|thẻ)\s*(?:tham gia)?\s*(?:BHYT)?\s*tự nguyện",
                    # 4. Tốc độ tăng dân số tự nhiên: "1.2%" hoặc "tăng 0.8%" (phải có %)
                    "natural_population_growth_rate": r"(?:tốc độ|tỷ lệ)\s*tăng\s*dân số\s*(?:tự nhiên)?[:\s]*(?:là|đạt)?[:\s]*(\d+[.,]?\d*)\s*(?:%|‰)",
                    # 5. Người cao tuổi khám: "80% cao tuổi được khám" (phải có %)
                    "elderly_health_checkup_rate": r"(\d+[.,]?\d*)\s*%\s*(?:người\s*)?(?:cao tuổi|người già)\s*(?:được|đi)?\s*(?:khám|khám sức khỏe|khám định kỳ)",
                    # 6. Tỷ số giới tính khi sinh: "110.5" hoặc "tỷ số 110.5/100" (số thuần, không %)
                    "sex_ratio_at_birth": r"(?:tỷ số|tỉ số)\s*giới tính\s*(?:khi sinh)?[:\s]*(?:là)?[:\s]*(\d+[.,]?\d*)(?:/100|\s*bé trai)?",
                }
            },
            "haq_index": {
                "name": "Chất lượng dịch vụ y tế (HAQ Index)",
                "keywords": ["HAQ", "chất lượng y tế", "bệnh viện", "giường bệnh", "bác sĩ",
                            "y tá", "điều dưỡng", "cơ sở y tế", "tử vong", "sơ sinh"],
                # Pre-filter patterns
                "url_patterns": ["benh-vien", "y-te", "bac-si", "dieu-duong", "chat-luong-y-te"],
                "title_patterns": ["bệnh viện", "giường bệnh", "bác sĩ", "điều dưỡng", "y tá", "cơ sở y tế", "chất lượng y tế"],
                # Unit validation
                "units": {
                    "hospital_beds_per_10k": "giường/10k dân",
                    "doctors_per_10k": "bác sĩ/10k dân",
                    "nurses_per_10k": "điều dưỡng/10k dân",
                    "infant_mortality_rate": "‰"
                },
                "patterns": {
                    # Số giường bệnh/10k dân: "25.5 giường/10.000 dân"
                    "hospital_beds_per_10k": r"(\d+[.,]?\d*)\s*giường\s*(?:bệnh)?[/\s]*(?:trên|cho)?[/\s]*(?:vạn|10[.,]?000|mười nghìn)\s*dân",
                    # Số bác sĩ/10k dân: "12.3 bác sĩ/vạn dân"
                    "doctors_per_10k": r"(\d+[.,]?\d*)\s*bác sĩ[/\s]*(?:trên|cho)?[/\s]*(?:vạn|10[.,]?000|mười nghìn)\s*dân",
                    # Số điều dưỡng/10k dân: "28 điều dưỡng/10.000 dân"
                    "nurses_per_10k": r"(\d+[.,]?\d*)\s*(?:điều dưỡng|y tá)[/\s]*(?:trên|cho)?[/\s]*(?:vạn|10[.,]?000|mười nghìn)\s*dân",
                    # Tỷ lệ tử vong sơ sinh: "4.5‰" hoặc "4.5 trên 1000 trẻ sinh sống"
                    "infant_mortality_rate": r"(?:tỷ lệ|tỉ lệ)\s*tử vong\s*(?:trẻ|sơ sinh|trẻ sơ sinh)[:\s]*(?:là)?[:\s]*(\d+[.,]?\d*)\s*(?:‰|%o|/1[.,]?000)?",
                }
            }
        }
    },
    
    # LĨNH VỰC 8: Giáo dục & Đào tạo
    "giao_duc": {
        "name": "Giáo dục & Đào tạo",
        "province": "Hưng Yên",
        "url_patterns": [
            "giao-duc", "dao-tao", "hoc-sinh", "giao-vien", "truong-hoc",
            "tot-nghiep-thpt", "thi-tot-nghiep", "ky-thi-quoc-gia",
            "chat-luong-giao-duc", "eqi", "hung-yen-dat-chuan"
        ],
        "title_patterns": [
            "giáo dục", "đào tạo", "học sinh", "giáo viên", "trường học",
            "tốt nghiệp THPT", "thi tốt nghiệp", "kỳ thi quốc gia",
            "chất lượng giáo dục", "EQI", "Hưng Yên đạt chuẩn",
            "phổ cập giáo dục", "xóa mù chữ"
        ],
        "indicators": {
            "eqi": {
                "name": "Chỉ số chất lượng giáo dục (EQI)",
                "url_patterns": ["chat-luong-giao-duc", "eqi", "pho-cap-giao-duc", "xoa-mu-chu", "giao-vien-dat-chuan"],
                "title_patterns": ["chất lượng giáo dục", "EQI", "phổ cập giáo dục", "xóa mù chữ", "giáo viên đạt chuẩn", "biết chữ"],
                "keywords": [
                    "chất lượng giáo dục", "EQI", "chỉ số giáo dục",
                    "tỷ lệ biết chữ", "phổ cập giáo dục", "xóa mù chữ",
                    "nhập học", "hoàn thành", "tốt nghiệp",
                    "giáo viên", "GV", "giáo viên đạt chuẩn", "trình độ giáo viên",
                    "học sinh", "tỷ lệ ra lớp", "tỷ lệ đi học",
                    "trường học", "cơ sở giáo dục", "trường chuẩn quốc gia",
                    "phòng học", "thiết bị dạy học", "sách giáo khoa"
                ],
                "patterns": {
                    # Tỷ lệ biết chữ: "99.5% dân số biết chữ" - tránh nhầm "kết nối", "đồng bộ"
                    "literacy_rate": r"(?<!kết\s*nối\s)(?<!đồng\s*bộ\s)(?<!xác\s*thực\s)(?:tỷ\s*lệ|tỉ\s*lệ){0,20}\s*(?:biết\s*chữ|xóa\s*mù\s*chữ|người\s*biết\s*chữ){0,50}[^\d]{0,50}[:\s]*(99\.[0-9]|[89][0-9])\s*%",
                    
                    # Tỷ lệ nhập học/ra lớp: "98.5% học sinh ra lớp" - tránh nhầm "số hóa", "gắn mã"  
                    "school_enrollment_rate": r"(?<!số\s*hóa\s)(?<!gắn\s*mã\s)(?<!kết\s*nối\s)(?:tỷ\s*lệ|tỉ\s*lệ){0,20}\s*(?:đi\s*học|nhập\s*học|ra\s*lớp|phổ\s*cập){0,50}(?:\s*(?:tiểu\s*học|trung\s*học|THCS|THPT))?{0,50}[^\d]{0,50}[:\s]*([89][0-9]|100)\s*%",
                    
                    # Tỷ lệ hoàn thành tiểu học: "95% học sinh hoàn thành tiểu học"
                    "primary_completion_rate": r"(?:tỷ\s*lệ|tỉ\s*lệ){0,20}\s*(?:hoàn\s*thành|tốt\s*nghiệp){0,30}\s*tiểu\s*học{0,50}[^\d]{0,50}[:\s]*([89][0-9]|100)\s*%",
                    
                    # Tỷ lệ giáo viên đạt chuẩn: "85% giáo viên đạt chuẩn" - phải có "giáo viên" và "đạt chuẩn"
                    "teacher_qualification_rate": r"(?:tỷ\s*lệ|tỉ\s*lệ){0,20}\s*(?:giáo\s*viên|GV){0,30}\s*(?:đạt\s*chuẩn|có\s*trình\s*độ){0,50}[^\d]{0,50}[:\s]*([6-9][0-9]|100)\s*%",
                    
                    # Tỷ lệ HS/GV: "18 học sinh/giáo viên", "1/20" - phải nhỏ hơn 50
                    "student_teacher_ratio": r"(?<!có\s)(?<!đạt\s)(?<!được\s)([1-4][0-9]|[5-9])\s*(?:học\s*sinh|HS)?\s*[/:]\s*(?:giáo\s*viên|GV|1)",
                },
                "units": {
                    "literacy_rate": "%",
                    "school_enrollment_rate": "%",
                    "primary_completion_rate": "%",
                    "teacher_qualification_rate": "%",
                    "student_teacher_ratio": "HS/GV"
                }
            },
            "highschool_graduation": {
                "name": "Tỷ lệ tốt nghiệp THPT",
                "url_patterns": ["tot-nghiep-thpt", "thi-tot-nghiep", "ky-thi-thpt", "thpt-quoc-gia", "diem-thi-thpt"],
                "title_patterns": ["tốt nghiệp THPT", "thi tốt nghiệp", "kỳ thi THPT", "THPT quốc gia", "điểm thi", "thí sinh đỗ"],
                "keywords": [
                    "tốt nghiệp THPT", "thi tốt nghiệp THPT", "kỳ thi THPT",
                    "kỳ thi tốt nghiệp", "kỳ thi quốc gia", "thi quốc gia",
                    "thi THPT quốc gia", "điểm thi THPT", "kết quả thi",
                    "thí sinh", "thí sinh dự thi", "thí sinh tốt nghiệp",
                    "đỗ tốt nghiệp", "đạt tốt nghiệp", "hoàn thành THPT",
                    "điểm trung bình", "điểm TB", "học sinh xuất sắc",
                    "môn thi", "bài thi"
                ],
                "patterns": {
                    # Tỷ lệ đỗ tốt nghiệp: "98.5% đỗ tốt nghiệp" - phải >70% và <100%
                    "graduation_rate": r"(?:tỷ\s*lệ|tỉ\s*lệ){0,20}\s*(?:đỗ|tốt\s*nghiệp|đạt){0,30}(?:\s*THPT)?{0,50}[^\d]{0,50}[:\s]*([7-9][0-9]\.[0-9]{1,2}|100|[89][0-9])\s*%",
                    
                    # Tổng số thí sinh: "15.000 thí sinh dự thi" - phải từ 5k-35k cho Hưng Yên
                    "total_candidates": r"(?<!tỷ\s*lệ\s)(?<!tỉ\s*lệ\s)((?:[1-3][0-9]|[5-9])(?:[.,][0-9]{3})?)\s*(?:thí\s*sinh|học\s*sinh|em|HS)(?:\s*(?:dự\s*thi|tham\s*gia))?",
                    
                    # Số thí sinh đỗ: "14.500 thí sinh đỗ tốt nghiệp"
                    "passed_candidates": r"(?<!tỷ\s*lệ\s)(?<!tỉ\s*lệ\s)((?:[1-3][0-9]|[5-9])(?:[.,][0-9]{3})?)\s*(?:thí\s*sinh|học\s*sinh|em|HS){0,20}\s*(?:đỗ|đạt|tốt\s*nghiệp)",
                    
                    # Điểm trung bình: "Điểm TB: 6.85" - phải từ 4.0-10.0
                    "average_score": r"(?:điểm|Điểm){0,20}\s*(?:trung\s*bình|TB){0,50}[^\d]{0,50}[:\s]*([4-9]\.[0-9]{1,2}|10(?:\.0{1,2})?)",
                },
                "units": {
                    "graduation_rate": "%",
                    "total_candidates": "thí sinh",
                    "passed_candidates": "thí sinh",
                    "average_score": "điểm"
                }
            },
            "tvet_employment": {
                "name": "Việc làm sau đào tạo nghề (TVET)",
                "keywords": ["đào tạo nghề", "giáo dục nghề nghiệp", "GDNN", "việc làm sau tốt nghiệp",
                            "học nghề", "trường nghề", "cao đẳng nghề"],
                "patterns": {
                    "employment_rate": r"(?:tỷ lệ|tỉ lệ)\s*(?:có việc làm|việc làm)[:\s]+(\d+[.,]?\d*)\s*%",
                    "total_graduates": r"(\d+(?:[.,]\d+)?)\s*(?:học viên|sinh viên)\s*tốt nghiệp",
                    "tvet_enrollment": r"tuyển sinh[:\s]+(\d+(?:[.,]\d+)?)\s*(?:học viên|người|chỉ tiêu)",
                    "tvet_facilities": r"(\d+)\s*(?:cơ sở|trường)\s*(?:GDNN|đào tạo nghề)",
                }
            }
        }
    },
    
    # LĨNH VỰC 9: Hạ tầng & Giao thông
    # LĨNH VỰC 9: Hạ tầng & Giao thông
    "ha_tang_giao_thong": {
        "name": "Hạ tầng & Giao thông",
        "province": "Hưng Yên",
        "url_patterns": [
            "tai-nan-giao-thong", "tngt", "an-toan-giao-thong",
            "atgt", "tong-ket", "bao-cao", "tinh-hinh-tngt",
            "hung-yen-giam-tai-nan", "atgt", "6-thang", "quy",
            "csgt-hung-yen"
        ],
        "title_patterns": [
            "TNGT", "an toàn giao thông", "tình hình TNGT",
            "Hưng Yên giảm tai nạn", "tổng kết ATGT",
            "báo cáo tai nạn", "6 tháng", "quý", "năm 2024", "năm 2025",
            "địa bàn Hưng Yên", "toàn tỉnh"
        ],
        "indicators": {
            "traffic_safety": {
                "name": "An toàn giao thông",
                "keywords": [
                    "tai nạn giao thông", "TNGT", "an toàn giao thông", "ATGT",
                    "tử vong giao thông", "tử vong do tai nạn", "chết do tai nạn",
                    "bị thương", "người bị thương", "thương tích giao thông",
                    "vi phạm giao thông", "nồng độ cồn", "say rượu lái xe",
                    "CSGT", "cảnh sát giao thông", "tuần tra", "xử lý vi phạm",
                    "giảm tai nạn", "tăng cường ATGT", "kiểm soát giao thông"
                ],
                "patterns": {
                    # Số vụ tai nạn: "toàn tỉnh xảy ra 353 vụ TNGT" - PHẢI có context tổng hợp (toàn tỉnh/địa bàn)
                    "accidents_total": r"(?:toàn\s*tỉnh|địa\s*bàn|trên\s*địa\s*bàn){0,30}\s*(?:xảy\s*ra|có|ghi\s*nhận){0,20}\s*([5-9][0-9]|[1-9][0-9]{2}|1000)\s*(?:vụ)?\s*(?:tai\s*nạn|TNGT)",
                    
                    # Số người tử vong: "làm chết 212 người" - PHẢI có context số lượng lớn (>10)
                    "fatalities": r"(?:làm\s*chết|tử\s*vong|thiệt\s*mạng){0,30}\s*([1-9][0-9]|[1-9][0-9]{2}|500)\s*(?:người|trường\s*hợp|nạn\s*nhân)",
                    
                    # Số người bị thương: "bị thương 263 người" - từ 20-1000 người
                    "injuries": r"(?:bị\s*thương){0,30}\s*([2-9][0-9]|[1-9][0-9]{2}|1000)\s*(?:người|trường\s*hợp|nạn\s*nhân)",
                    
                    # Tỷ lệ giảm tai nạn: "giảm 15% TNGT" - từ 1-50%
                    "accident_reduction_rate": r"(?:giảm){0,20}\s*([1-4][0-9]|50)\s*%\s*(?:tai\s*nạn|TNGT|vụ)",
                    
                    # Số vụ vi phạm nồng độ cồn: "xử lý 3829 trường hợp vi phạm nồng độ cồn" - từ 500-10000 vụ
                    "drunk_driving_cases": r"(?:xử\s*lý|phạt|lập\s*biên\s*bản){0,30}\s*([5-9][0-9]{2}|[1-9][0-9]{3}|10000)\s*(?:vụ|trường\s*hợp){0,20}\s*(?:vi\s*phạm)?{0,20}\s*nồng\s*độ\s*cồn",
                },
                "units": {
                    "accidents_total": "vụ",
                    "fatalities": "người",
                    "injuries": "người",
                    "accident_reduction_rate": "%",
                    "drunk_driving_cases": "vụ"
                }
            }
        }
    }
}


# =============================================================================
# LLM CLASSIFIER - Chỉ dùng để classify, KHÔNG extract số
# =============================================================================

class LLMClassifier:
    """Use LLM to classify if article is relevant to a field/indicator"""
    
    def __init__(self):
        self.client = None
        self.model = None
        if LLM_AVAILABLE and OPENAI_API_KEY:
            if OPENAI_API_KEY.startswith("sk-or-v1-"):
                self.client = OpenAI(
                    api_key=OPENAI_API_KEY,
                    base_url="https://openrouter.ai/api/v1"
                )
                self.model = "openai/gpt-4o-mini"
            else:
                self.client = OpenAI(api_key=OPENAI_API_KEY)
                self.model = "gpt-4o-mini"
    
    def classify_article(
        self, 
        title: str, 
        content: str, 
        field_key: str,
        url: str = ""
    ) -> Dict[str, Any]:
        """
        Classify article - PRE-FILTER bằng URL/title trước, không cần đọc hết content
        
        Strategy:
        1. Pre-filter: Check URL/title patterns first (FAST)
        2. If matched: Extract keywords từ title/first paragraph only
        3. Province: Hard-code từ field definition, KHÔNG auto-detect
        
        Returns:
            {
                "is_relevant": bool,
                "relevant_indicators": ["indicator1", "indicator2"],
                "confidence": float,
                "province": str (hard-coded),
                "year": int or None,
                "quarter": int or None,
                "month": int or None
            }
        """
        field_def = FIELD_DEFINITIONS.get(field_key)
        if not field_def:
            return {"is_relevant": False, "relevant_indicators": [], "confidence": 0}
        
        # STEP 1: Pre-filter by URL/title patterns (NHANH)
        relevant_indicators = []
        for ind_key, ind_def in field_def['indicators'].items():
            # Check URL patterns
            url_patterns = ind_def.get('url_patterns', [])
            url_match = any(pattern in url.lower() for pattern in url_patterns) if url else False
            
            # Check title patterns
            title_patterns = ind_def.get('title_patterns', [])
            title_match = any(pattern in title.lower() for pattern in title_patterns)
            
            # Nếu match URL hoặc title → relevant
            if url_match or title_match:
                relevant_indicators.append(ind_key)
                logger.info(f"Pre-filter MATCH: {ind_key} - URL:{url_match} Title:{title_match}")
        
        # STEP 2: Nếu không match URL/title, fallback keyword check (CHỈ title + 500 ký tự đầu)
        if not relevant_indicators:
            text_sample = f"{title} {content[:500]}".lower()
            for ind_key, ind_def in field_def['indicators'].items():
                keyword_count = sum(1 for kw in ind_def['keywords'] if kw.lower() in text_sample)
                if keyword_count >= 2:  # At least 2 keywords
                    relevant_indicators.append(ind_key)
        
        if not relevant_indicators:
            return {"is_relevant": False, "relevant_indicators": [], "confidence": 0}
        
        # Extract period info (title + first 500 chars only)
        text_sample = f"{title} {content[:500]}"
        year = self._extract_year(text_sample)
        quarter = self._extract_quarter(text_sample)
        month = self._extract_month(text_sample)
        
        # PROVINCE: Hard-code từ field definition, KHÔNG auto-detect
        province = field_def.get('province', 'Hưng Yên')
        
        return {
            "is_relevant": True,
            "relevant_indicators": relevant_indicators,
            "confidence": 0.9 if relevant_indicators else 0.5,
            "province": province,
            "year": year,
            "quarter": quarter,
            "month": month
        }
    
    def _extract_year(self, text: str) -> Optional[int]:
        match = re.search(r'năm\s*(20\d{2})', text)
        if match:
            return int(match.group(1))
        match = re.search(r'(20\d{2})', text)
        if match:
            return int(match.group(1))
        return datetime.now().year
    
    def _extract_quarter(self, text: str) -> Optional[int]:
        match = re.search(r'quý\s*([IVX]+|[1-4])', text, re.IGNORECASE)
        if match:
            q = match.group(1).upper()
            quarter_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, '1': 1, '2': 2, '3': 3, '4': 4}
            return quarter_map.get(q)
        return None
    
    def _extract_month(self, text: str) -> Optional[int]:
        match = re.search(r'tháng\s*(\d{1,2})', text)
        if match:
            m = int(match.group(1))
            if 1 <= m <= 12:
                return m
        return None


# =============================================================================
# VALUE EXTRACTOR - Extract numbers using REGEX only
# =============================================================================

class ValueExtractor:
    """Extract numeric values from text using REGEX - NO LLM"""
    
    @staticmethod
    def parse_number_with_unit(value_str: str, unit_str: str = None) -> Optional[float]:
        """
        Parse Vietnamese number format with unit (nghìn, triệu, tỷ)
        
        Args:
            value_str: Number string (e.g., "950" or "1.5")
            unit_str: Unit string (e.g., "nghìn", "triệu", "tỷ")
        
        Returns:
            Converted float value
        """
        if not value_str:
            return None
        
        # Clean number string
        value_str = value_str.replace(',', '.').replace(' ', '').strip()
        
        try:
            value = float(value_str)
        except ValueError:
            return None
        
        # Apply multiplier based on unit
        if unit_str:
            unit_lower = unit_str.lower().strip()
            if unit_lower in ['nghìn', 'ngàn']:
                value *= 1_000
            elif unit_lower == 'triệu':
                value *= 1_000_000
            elif unit_lower == 'tỷ':
                value *= 1_000_000_000
        
        return value
    
    @staticmethod
    def extract_values(
        text: str, 
        patterns: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Extract all values matching the patterns with unit handling
        
        Args:
            text: Text to extract from
            patterns: Dict of field_name -> regex_pattern
        
        Returns:
            Dict of field_name -> extracted_value (or None)
        """
        results = {}
        text = text.replace('\xa0', ' ')  # normalize nbsp
        
        for field_name, pattern in patterns.items():
            try:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    # Check if pattern has 2 groups (number + unit)
                    if match.lastindex and match.lastindex >= 2:
                        value_str = match.group(1)
                        unit_str = match.group(2) if match.lastindex >= 2 else None
                        value = ValueExtractor.parse_number_with_unit(value_str, unit_str)
                    else:
                        # Single group: just number
                        value_str = match.group(1).replace(',', '.').replace(' ', '')
                        try:
                            value = float(value_str)
                        except ValueError:
                            value = None
                    
                    results[field_name] = value
                else:
                    results[field_name] = None
            except Exception as e:
                logger.debug(f"Regex error for {field_name}: {e}")
                results[field_name] = None
        
        return results


# =============================================================================
# LLM EXTRACTOR - Extract with context understanding (EXPENSIVE but SMART)
# =============================================================================

class SmartExtractor:
    """
    Smart Extractor - Kết hợp LLM + Regex
    
    Strategy:
    1. Thử LLM trước (nếu có API key) - context-aware, thông minh
    2. Fallback/Merge với Regex - đảm bảo không bỏ sót
    3. Priority: LLM results > Regex results
    """
    
    def __init__(self):
        self.llm_available = False
        self.client = None
        self.model = None
        
        if LLM_AVAILABLE and OPENAI_API_KEY:
            try:
                if OPENAI_API_KEY.startswith("sk-or-v1-"):
                    self.client = OpenAI(
                        api_key=OPENAI_API_KEY,
                        base_url="https://openrouter.ai/api/v1"
                    )
                    self.model = "openai/gpt-4o-mini"
                else:
                    self.client = OpenAI(api_key=OPENAI_API_KEY)
                    self.model = "gpt-4o-mini"
                self.llm_available = True
                logger.info("SmartExtractor: LLM mode enabled (context-aware)")
            except Exception as e:
                logger.warning(f"SmartExtractor: LLM init failed, using regex only: {e}")
        else:
            logger.info("SmartExtractor: Regex mode only (no LLM API key)")
    
    def extract_values(
        self,
        text: str,
        indicator_key: str,
        indicator_def: Dict,
        patterns: Dict[str, str],
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        Extract values using LLM (smart) + Regex (fallback)
        
        Strategy:
        1. Try LLM first if available and use_llm=True - hiểu context phức tạp
        2. Always try Regex as backup
        3. Merge results: LLM values override Regex if not null
        
        Args:
            use_llm: If False, skip LLM and use Regex only
        
        Returns:
            Dict of field_name -> extracted_value (or None)
        """
        results = {}
        
        # Step 1: Try LLM extraction (context-aware) if enabled
        llm_results = {}
        if use_llm and self.llm_available and self.client:
            try:
                llm_results = self._extract_with_llm(text, indicator_key, indicator_def, patterns)
                logger.debug(f"LLM extracted {sum(1 for v in llm_results.values() if v is not None)}/{len(patterns)} fields")
            except Exception as e:
                logger.warning(f"LLM extraction failed: {e}, falling back to regex")
        
        # Step 2: Always try Regex extraction (fast, pattern-based)
        regex_results = ValueExtractor.extract_values(text, patterns)
        logger.debug(f"Regex extracted {sum(1 for v in regex_results.values() if v is not None)}/{len(patterns)} fields")
        
        # Step 3: Merge results (LLM priority > Regex)
        for field_name in patterns.keys():
            llm_value = llm_results.get(field_name)
            regex_value = regex_results.get(field_name)
            
            # Priority: LLM > Regex
            if llm_value is not None:
                results[field_name] = llm_value
            elif regex_value is not None:
                results[field_name] = regex_value
            else:
                results[field_name] = None
        
        return results
    
    def _extract_with_llm(
        self,
        text: str,
        indicator_key: str,
        indicator_def: Dict,
        patterns: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Extract values using LLM with structured output
        """
        if not self.client:
            return {}
        
        # Build field descriptions with detailed context
        field_descriptions = []
        for field_name in patterns.keys():
            field_label = field_name.replace('_', ' ').title()
            # Add specific guidance for common confusing fields
            if field_name == 'total_candidates':
                field_label += " (Tổng số thí sinh DỰ THI/THAM GIA, KHÔNG PHẢI 'đạt điểm 10' hay 'đỗ tốt nghiệp')"
            elif field_name == 'passed_candidates':
                field_label += " (Số thí sinh ĐỖ TỐT NGHIỆP/ĐẠT TỐT NGHIỆP, KHÔNG PHẢI 'đạt điểm 10 một môn')"
            elif field_name == 'graduation_rate':
                field_label += " (Tỷ lệ % ĐỖ TỐT NGHIỆP của toàn bộ thí sinh, KHÔNG PHẢI tỷ lệ đạt điểm cao)"
            field_descriptions.append(f"- {field_name}: {field_label}")
        
        fields_text = "\n".join(field_descriptions)
        
        # Get unit expectations for validation
        units = indicator_def.get('units', {})
        units_text = "\n".join([f"- {field}: đơn vị '{unit}'" for field, unit in units.items()]) if units else "Không có ràng buộc đơn vị"
        
        # Get province from field definition
        province = indicator_def.get('province', 'Hưng Yên')
        
        prompt = f"""Trích xuất SỐ LIỆU CHÍNH XÁC từ văn bản dưới đây. Đọc KỸ toàn bộ văn bản để hiểu context.

========== VĂN BẢN ==========
{text[:5000]}
========== HẾT VĂN BẢN ==========

CHỈ SỐ CẦN TRÍCH XUẤT: {indicator_def['name']}
TỈNH/THÀNH PHỐ: {province}

CÁC TRƯỜNG DỮ LIỆU:
{fields_text}

ĐƠN VỊ MONG ĐỢI:
{units_text}

QUI TẮC BẮT BUỘC:
1. CHỈ trích xuất số XUẤT HIỆN TRONG VĂN BẢN - TUYỆT ĐỐI KHÔNG SINH SỐ, KHÔNG BỊA
2. **CHỈ extract nếu số liệu về tỉnh {province}** - KHÔNG extract số liệu của tỉnh khác hoặc toàn quốc
3. Nếu văn bản KHÔNG đề cập đến {province} hoặc chỉ đề cập chung chung → TẤT CẢ TRƯỜNG ĐỂ NULL
4. Nếu không tìm thấy số liệu cụ thể cho {province} → ĐỂ NULL - không đoán, không tính toán, không suy luận
5. PHẢI kiểm tra đơn vị: nếu số có đơn vị khác đơn vị mong đợi → ĐỂ NULL
4. Chuyển đổi đơn vị về số thực:
   - "gần 6500" hoặc "6.485" → 6485 (bỏ dấu phân cách)
   - "hơn 2.000 người" → 2000 (nếu đơn vị mong đợi là 'người')
   - "123,5 tỷ" → 123.5 (GIỮ NGUYÊN số, KHÔNG nhân 1 tỷ)
   - "45.6%" → 45.6 (bỏ ký hiệu %)
   - "950 nghìn người" → 950000 (nhân 1000)
   - "1.2 triệu lượt" → 1200000 (nhân 1 triệu)
5. Cụm từ gần đúng: "gần", "hơn", "khoảng", "trên", "dưới" → vẫn lấy số đó
6. Phân biệt context:
   - "giảm 30%" ≠ "đạt 70%" ≠ "tăng 50%" → Chỉ lấy số phù hợp với trường
   - "kế hoạch 1000" ≠ "thực hiện 800" → Ưu tiên số THỰC HIỆN
   - "năm trước 500" ≠ "năm nay 600" → Ưu tiên số MỚI NHẤT
   - "Thái Bình: 95%" ≠ "Hưng Yên: 92%" → CHỈ lấy số của Hưng Yên
7. Nhiều số cùng loại: lấy số MỚI NHẤT/CHÍNH THỨC/THỰC HIỆN (không lấy kế hoạch/dự kiến)
8. Số âm: Nếu là "giảm X" hoặc "âm X" → không lấy (để null), trừ khi trường yêu cầu số âm

VÍ DỤ ĐÚNG (Context-aware):
- Văn bản: "Hưng Yên tạm giao gần 6500 biên chế cho năm 2025"
  → total_authorized: 6500 (số thực hiện, về Hưng Yên)
  
- Văn bản: "Tỉnh {province}: tỷ lệ tốt nghiệp THPT đạt 95.2%, có 18.500 thí sinh dự thi, 17.600 em đỗ"
  → graduation_rate: 95.2 , total_candidates: 18500 , passed_candidates: 17600 - Văn bản: "{province} có 628 thí sinh đạt điểm 10 môn Toán"
  → total_candidates: NULL ✗ (đây là số thí sinh đạt điểm 10 MỘT MÔN, không phải tổng số dự thi)
  
- Văn bản: "Năm 2024, trên địa bàn {province} phát hiện 125 vụ ma túy, bắt giữ 240 đối tượng"
  → drug_cases: 125 , drug_offenders: 240 (rõ ràng về {province})

VÍ DỤ SAI - PHẢI TRẢ VỀ NULL:
- Văn bản: "Toàn quốc có 850.000 thí sinh dự thi THPT" → TẤT CẢ NULL ✗ (toàn quốc, không phải {province})
- Văn bản: "Thái Bình có tỷ lệ tốt nghiệp 97.5%" → TẤT CẢ NULL ✗ (tỉnh khác)
- Văn bản: "{province} có 100 thí sinh đạt điểm 10" → total_candidates: NULL ✗ (đạt điểm 10 ≠ tổng số dự thi)
- Văn bản: "Điểm sàn đại học năm 2017 là..." → TẤT CẢ NULL ✗ (không phải thống kê {province})
- Văn bản chỉ đề cập "đạt chuẩn", "chất lượng" mà không có số cụ thể → NULL ✗
- Văn bản không có số → trả về 1000 → SAI, phải null ✗

Trả về JSON (chỉ JSON thuần, không markdown, không giải thích):
{{
  "field_name_1": số hoặc null,
  "field_name_2": số hoặc null,
  ...
}}"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": f"Bạn là chuyên gia trích xuất dữ liệu. CHỈ trích xuất số liệu về tỉnh {province}. TUYỆT ĐỐI KHÔNG extract số của tỉnh khác hoặc toàn quốc. Nếu không có số cụ thể về {province} → TẤT CẢ trả null. Chỉ trả về JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content.strip()
        extracted = json.loads(content)
        
        # Validate and convert to float
        results = {}
        for field_name in patterns.keys():
            value = extracted.get(field_name)
            if value is not None and value != "null":
                try:
                    results[field_name] = float(value)
                except (ValueError, TypeError):
                    results[field_name] = None
            else:
                results[field_name] = None
        
        return results


# =============================================================================
# SOCIAL INDICATOR SERVICE - Main service
# =============================================================================

# =============================================================================
# SOCIAL INDICATOR SERVICE - Main service
# =============================================================================

class SocialIndicatorService:
    """Main service for extracting social indicators from articles"""
    
    def __init__(self, db: Session):
        self.db = db
        self.classifier = LLMClassifier()
        self.extractor = SmartExtractor()  # Tự động dùng LLM + Regex
        """Convert Vietnamese number format to float"""
        if not value_str:
            return None
        
        # Remove spaces and replace comma with dot
        value_str = value_str.strip().replace(' ', '').replace(',', '.')
        
        # Handle "nghìn", "triệu", "tỷ"
        multiplier = 1
        if 'tỷ' in value_str.lower():
            multiplier = 1_000_000_000
            value_str = re.sub(r'tỷ', '', value_str, flags=re.IGNORECASE)
        elif 'triệu' in value_str.lower():
            multiplier = 1_000_000
            value_str = re.sub(r'triệu', '', value_str, flags=re.IGNORECASE)
        elif 'nghìn' in value_str.lower() or 'ngàn' in value_str.lower():
            multiplier = 1_000
            value_str = re.sub(r'nghìn|ngàn', '', value_str, flags=re.IGNORECASE)
        


# =============================================================================
# SOCIAL INDICATOR SERVICE - Main service
# =============================================================================

class SocialIndicatorService:
    """Main service for extracting social indicators from articles"""
    
    def __init__(self, db: Session):
        self.db = db
        self.classifier = LLMClassifier()
        self.extractor = SmartExtractor()  # Tự động dùng LLM + Regex
    
    def get_model_class(self, indicator_key: str):
        """Get SQLAlchemy model class for an indicator"""
        from app.models.model_indicator_details import INDICATOR_DETAIL_MODELS
        return INDICATOR_DETAIL_MODELS.get(indicator_key)
    
    def process_field(
        self,
        field_key: str,
        limit: int = 100,
        year_filter: Optional[int] = None,
        province_filter: Optional[str] = None,
        use_category_filter: bool = True,
        use_llm: bool = False
    ) -> Dict[str, Any]:
        """
        Process articles for a specific field and fill indicator tables
        
        Args:
            field_key: Key of the field (e.g., 'xay_dung_dang')
            limit: Max number of articles to process
            year_filter: Filter articles by year
            province_filter: Filter by province
            use_category_filter: If True, filter by category column first (faster)
            use_llm: If True, use LLM (GPT) for indicator extraction
        
        Returns:
            Summary of processing results
        """
        field_def = FIELD_DEFINITIONS.get(field_key)
        if not field_def:
            return {"error": f"Unknown field: {field_key}"}
        
        from app.models.model_article import Article
        from sqlalchemy import or_, func
        
        # Get categories for this field
        categories = FIELD_TO_CATEGORIES.get(field_key, [])
        
        # Build query
        query = self.db.query(Article)
        
        # Strategy 1: Filter by category if available and enabled
        if use_category_filter and categories:
            # Check if any articles have category set
            sample_with_category = self.db.query(Article).filter(
                Article.category.isnot(None),
                Article.category != ''
            ).limit(1).first()
            
            if sample_with_category:
                # Use category filter - MUCH FASTER
                category_filters = [
                    func.lower(Article.category) == cat.lower() 
                    for cat in categories
                ]
                query = query.filter(or_(*category_filters))
                logger.info(f"Filtering by categories: {categories}")
            else:
                # Fallback to keyword search if no categories are set
                logger.info("No articles with category found, using keyword search")
                query = self._add_keyword_filters(query, field_def, Article)
        else:
            # Strategy 2: Keyword-based search (slower but works without categories)
            query = self._add_keyword_filters(query, field_def, Article)
        
        # Add additional filters
        if province_filter:
            query = query.filter(Article.province == province_filter)
        
        if year_filter:
            query = query.filter(
                func.extract('year', Article.published_date) == year_filter
            )
        
        # Execute query
        articles = query.order_by(Article.published_date.desc()).limit(limit).all()
        
        results = {
            "field": field_def['name'],
            "field_key": field_key,
            "categories_used": categories if use_category_filter else [],
            "articles_found": len(articles),
            "articles_processed": 0,
            "records_created": 0,
            "indicators_filled": {},
            "errors": []
        }
        
        for article in articles:
            # Save article_id before processing to avoid lazy loading issues after exception
            article_id = getattr(article, 'id', 'unknown')
            try:
                article_result = self._process_article_for_field(
                    article, field_key, field_def, use_llm=use_llm
                )
                if article_result.get("records_created", 0) > 0:
                    results["articles_processed"] += 1
                    results["records_created"] += article_result["records_created"]
                    for ind_key, count in article_result.get("by_indicator", {}).items():
                        results["indicators_filled"][ind_key] = results["indicators_filled"].get(ind_key, 0) + count
            except Exception as e:
                # Rollback on error to clear invalid transaction
                self.db.rollback()
                logger.error(f"Error processing article {article_id}: {e}")
                results["errors"].append(f"Article {article_id}: {str(e)}")
        
        return results
    
    def _add_keyword_filters(self, query, field_def: Dict, Article):
        """Add keyword-based filters to query (fallback when no category)"""
        from sqlalchemy import or_
        
        all_keywords = []
        for ind_def in field_def['indicators'].values():
            all_keywords.extend(ind_def['keywords'])
        
        # Limit keywords to avoid too complex query
        unique_keywords = list(set(all_keywords))[:15]
        
        keyword_filters = [
            Article.content.ilike(f'%{kw}%') for kw in unique_keywords
        ] + [
            Article.title.ilike(f'%{kw}%') for kw in unique_keywords
        ]
        
        return query.filter(or_(*keyword_filters))
    
    def _process_article_for_field(
        self,
        article,
        field_key: str,
        field_def: Dict,
        use_llm: bool = False
    ) -> Dict[str, Any]:
        """Process a single article for a field"""
        result = {"records_created": 0, "by_indicator": {}}
        
        # Classify article (with URL for pre-filtering)
        classification = self.classifier.classify_article(
            article.title or "",
            article.content or "",
            field_key,
            url=article.url or ""
        )
        
        if not classification.get("is_relevant"):
            return result
        
        # Extract period info
        year = classification.get("year") or datetime.now().year
        quarter = classification.get("quarter")
        month = classification.get("month")
        # Province: từ classification (hard-coded), KHÔNG dùng article.province
        province = classification.get("province", "Hưng Yên")
        
        # Process each relevant indicator
        for ind_key in classification.get("relevant_indicators", []):
            ind_def = field_def['indicators'].get(ind_key)
            if not ind_def:
                continue
            
            # Extract values using SmartExtractor (LLM + Regex tự động)
            extracted = self.extractor.extract_values(
                article.content or "",
                ind_key,
                ind_def,
                ind_def.get('patterns', {}),
                use_llm=use_llm
            )
            
            # Check if we got any values
            non_null_values = {k: v for k, v in extracted.items() if v is not None}
            if not non_null_values:
                continue
            
            # Get model class
            model_class = self.get_model_class(ind_key)
            if not model_class:
                logger.warning(f"No model class for indicator: {ind_key}")
                continue
            
            # Check if record already exists
            existing = self.db.query(model_class).filter(
                model_class.province == province,
                model_class.year == year,
                model_class.quarter == quarter if quarter else model_class.quarter.is_(None),
            ).first()
            
            if existing:
                # Update existing record with new values (only if null)
                updated = False
                for field_name, value in non_null_values.items():
                    if hasattr(existing, field_name) and getattr(existing, field_name) is None:
                        setattr(existing, field_name, value)
                        updated = True
                if updated:
                    existing.data_source = article.url[:255] if article.url else None
                    existing.updated_at = datetime.now()
                    self.db.commit()
            else:
                # Create new record
                record_data = {
                    "province": province,
                    "year": year,
                    "quarter": quarter,
                    "month": month,
                    "data_source": article.url[:255] if article.url else None,
                    "data_status": "official",
                    **non_null_values
                }
                
                new_record = model_class(**record_data)
                self.db.add(new_record)
                self.db.commit()
                
                result["records_created"] += 1
                result["by_indicator"][ind_key] = result["by_indicator"].get(ind_key, 0) + 1
        
        return result
    
    def get_field_summary(self, field_key: str) -> Dict[str, Any]:
        """Get summary of data in all indicators for a field"""
        field_def = FIELD_DEFINITIONS.get(field_key)
        if not field_def:
            return {"error": f"Unknown field: {field_key}"}
        
        summary = {
            "field": field_def['name'],
            "field_key": field_key,
            "indicators": {}
        }
        
        for ind_key, ind_def in field_def['indicators'].items():
            model_class = self.get_model_class(ind_key)
            if not model_class:
                continue
            
            count = self.db.query(model_class).count()
            latest = self.db.query(model_class).order_by(
                model_class.year.desc(),
                model_class.quarter.desc().nullsfirst()
            ).first()
            
            summary["indicators"][ind_key] = {
                "name": ind_def['name'],
                "total_records": count,
                "latest_year": latest.year if latest else None,
                "latest_quarter": latest.quarter if latest else None
            }
        
        return summary


# =============================================================================
# EXPORT
# =============================================================================

__all__ = [
    'FIELD_DEFINITIONS',
    'CATEGORY_TO_FIELD',
    'FIELD_TO_CATEGORIES',
    'LLMClassifier',
    'ValueExtractor',
    'SocialIndicatorService'
]
