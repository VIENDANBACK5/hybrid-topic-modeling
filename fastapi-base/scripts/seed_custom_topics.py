"""Seed Data - Custom Topics"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.model_custom_topic import CustomTopic, TopicTemplate
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def seed_news_topics():
    db = SessionLocal()
    
    topics_data = [
        {
            "name": "Chính trị Việt Nam",
            "slug": "chinh-tri-viet-nam",
            "description": "Tin tức chính trị trong nước, quốc hội, chính phủ, nghị quyết, chính sách",
            "keywords": [
                "quốc hội", "chính phủ", "bộ trưởng", "thủ tướng", "chủ tịch nước",
                "nghị quyết", "chính sách", "luật", "nghị định", "quyết định"
            ],
            "example_docs": [
                "Quốc hội thông qua nghị quyết về phát triển kinh tế-xã hội",
                "Chính phủ ban hành chính sách mới hỗ trợ doanh nghiệp",
                "Thủ tướng yêu cầu đẩy nhanh tiến độ các dự án trọng điểm"
            ],
            "negative_keywords": ["cổ phiếu", "bóng đá", "thời tiết"],
            "min_confidence": 0.6,
            "color": "#DC2626",
            "icon": "🏛️",
            "display_order": 1
        },
        {
            "name": "Kinh tế & Tài chính",
            "slug": "kinh-te-tai-chinh",
            "description": "Kinh tế vĩ mô, tài chính, ngân hàng, chứng khoán, doanh nghiệp",
            "keywords": [
                "GDP", "lạm phát", "lãi suất", "ngân hàng", "tín dụng",
                "xuất khẩu", "nhập khẩu", "FDI", "đầu tư", "kinh tế"
            ],
            "example_docs": [
                "GDP quý 1 tăng trưởng 6.5% so với cùng kỳ",
                "Ngân hàng Nhà nước điều chỉnh lãi suất điều hành",
                "Kim ngạch xuất khẩu đạt mức kỷ lục trong tháng 3"
            ],
            "min_confidence": 0.55,
            "color": "#2563EB",
            "icon": "💰",
            "display_order": 2
        },
        {
            "name": "Chứng khoán",
            "slug": "chung-khoan",
            "description": "Thị trường chứng khoán, cổ phiếu, VN-Index, giao dịch",
            "keywords": [
                "VN-Index", "cổ phiếu", "chứng khoán", "HOSE", "HNX", "UPCOM",
                "blue chip", "penny", "thị giá", "thanh khoản", "niêm yết",
                "giao dịch", "mã cổ phiếu", "khớp lệnh"
            ],
            "example_docs": [
                "VN-Index tăng điểm mạnh trong phiên sáng nay",
                "Cổ phiếu ngân hàng dẫn dắt thị trường",
                "Thanh khoản HOSE đạt 20,000 tỷ đồng"
            ],
            "min_confidence": 0.7,
            "color": "#059669",
            "icon": "📈",
            "display_order": 3
        },
        {
            "name": "Bất động sản",
            "slug": "bat-dong-san",
            "description": "Thị trường bất động sản, nhà đất, căn hộ, dự án",
            "keywords": [
                "bất động sản", "nhà đất", "căn hộ", "chung cư", "biệt thự",
                "đất nền", "dự án", "thị trường nhà đất", "giá nhà", "giao dịch nhà đất"
            ],
            "example_docs": [
                "Giá nhà tại TP.HCM tăng 15% trong quý đầu năm",
                "Thị trường căn hộ cao cấp sôi động trở lại",
                "Chính sách tín dụng mới ảnh hưởng đến thị trường bất động sản"
            ],
            "min_confidence": 0.65,
            "color": "#7C3AED",
            "icon": "🏘️",
            "display_order": 4
        },
        {
            "name": "Y tế & Sức khỏe",
            "slug": "y-te-suc-khoe",
            "description": "Y tế, sức khỏe, bệnh viện, dịch bệnh, vaccine",
            "keywords": [
                "y tế", "sức khỏe", "bệnh viện", "bác sĩ", "bệnh nhân",
                "thuốc", "vaccine", "dịch bệnh", "COVID", "khám chữa bệnh",
                "bảo hiểm y tế"
            ],
            "example_docs": [
                "Bệnh viện Chợ Rẫy đưa vào hoạt động phòng khám mới",
                "Vaccine COVID-19 mới được Bộ Y tế phê duyệt",
                "Dịch sốt xuất huyết gia tăng tại các tỉnh phía Nam"
            ],
            "min_confidence": 0.6,
            "color": "#DC2626",
            "icon": "🏥",
            "display_order": 5
        },
        {
            "name": "Giáo dục",
            "slug": "giao-duc",
            "description": "Giáo dục, đào tạo, trường học, thi cử, học sinh, sinh viên",
            "keywords": [
                "giáo dục", "đào tạo", "trường học", "học sinh", "sinh viên",
                "thi", "tuyển sinh", "đại học", "cao đẳng", "THPT",
                "chương trình học", "giáo viên"
            ],
            "example_docs": [
                "Kỳ thi tốt nghiệp THPT 2024 diễn ra vào tháng 6",
                "Trường Đại học Y Hà Nội công bố chỉ tiêu tuyển sinh",
                "Bộ Giáo dục triển khai chương trình giáo dục phổ thông mới"
            ],
            "min_confidence": 0.6,
            "color": "#F59E0B",
            "icon": "🎓",
            "display_order": 6
        },
        {
            "name": "Công nghệ",
            "slug": "cong-nghe",
            "description": "Công nghệ thông tin, chuyển đổi số, AI, startup, tech",
            "keywords": [
                "công nghệ", "công nghệ thông tin", "chuyển đổi số", "AI",
                "trí tuệ nhân tạo", "startup", "app", "phần mềm", "ứng dụng",
                "dữ liệu", "internet", "5G", "điện thoại", "laptop"
            ],
            "example_docs": [
                "Startup Việt Nam gọi vốn thành công 10 triệu USD",
                "Chính phủ đẩy mạnh chuyển đổi số quốc gia",
                "Ứng dụng AI mới giúp chẩn đoán bệnh chính xác 95%"
            ],
            "min_confidence": 0.55,
            "color": "#3B82F6",
            "icon": "💻",
            "display_order": 7
        },
        {
            "name": "Xã hội",
            "slug": "xa-hoi",
            "description": "Tin tức xã hội, dân sinh, đời sống, cộng đồng",
            "keywords": [
                "xã hội", "dân sinh", "đời sống", "cộng đồng", "người dân",
                "an sinh", "an toàn", "tai nạn", "cứu hộ", "từ thiện",
                "môi trường"
            ],
            "example_docs": [
                "Hỗ trợ khẩn cấp cho người dân vùng lũ lụt",
                "Tai nạn giao thông nghiêm trọng trên quốc lộ 1A",
                "Chiến dịch làm sạch môi trường biển thu hút hàng nghìn người tham gia"
            ],
            "min_confidence": 0.5,
            "color": "#10B981",
            "icon": "👥",
            "display_order": 8
        },
        {
            "name": "Thể thao",
            "slug": "the-thao",
            "description": "Thể thao, bóng đá, SEA Games, Olympic, vận động viên",
            "keywords": [
                "thể thao", "bóng đá", "SEA Games", "Olympic", "vận động viên",
                "huấn luyện viên", "tuyển quốc gia", "V-League", "World Cup",
                "tennis", "cầu lông", "bơi lội", "võ thuật"
            ],
            "example_docs": [
                "Tuyển Việt Nam giành chiến thắng 3-1 trước Thái Lan",
                "VĐV Nguyễn Thị Ánh Viên phá kỷ lục SEA Games",
                "V-League 2024 khởi tranh với 14 đội tham dự"
            ],
            "min_confidence": 0.7,
            "color": "#F97316",
            "icon": "⚽",
            "display_order": 9
        },
        {
            "name": "Văn hóa & Giải trí",
            "slug": "van-hoa-giai-tri",
            "description": "Văn hóa, nghệ thuật, điện ảnh, âm nhạc, người nổi tiếng",
            "keywords": [
                "văn hóa", "giải trí", "nghệ thuật", "điện ảnh", "phim",
                "âm nhạc", "ca sĩ", "diễn viên", "sao", "nghệ sĩ",
                "concert", "show", "liveshow", "MV", "album"
            ],
            "example_docs": [
                "Phim Việt đoạt giải Cánh diều vàng 2024",
                "Ca sĩ Mỹ Tâm tổ chức liveshow tại Hà Nội",
                "Triển lãm nghệ thuật đương đại thu hút hàng nghìn người xem"
            ],
            "min_confidence": 0.6,
            "color": "#EC4899",
            "icon": "🎭",
            "display_order": 10
        },
        {
            "name": "Pháp luật",
            "slug": "phap-luat",
            "description": "Pháp luật, tòa án, công an, tội phạm, án lệ",
            "keywords": [
                "pháp luật", "luật pháp", "tòa án", "công an", "cảnh sát",
                "tội phạm", "án", "xét xử", "bị cáo", "vụ án",
                "vi phạm", "bắt giữ", "khởi tố"
            ],
            "example_docs": [
                "Tòa án xét xử vụ án tham nhũng lớn tại tỉnh X",
                "Công an bắt giữ đường dây ma túy xuyên quốc gia",
                "Luật mới về an toàn giao thông có hiệu lực từ tháng 7"
            ],
            "min_confidence": 0.65,
            "color": "#6B7280",
            "icon": "⚖️",
            "display_order": 11
        },
        {
            "name": "Du lịch",
            "slug": "du-lich",
            "description": "Du lịch, điểm đến, khách sạn, resort, lễ hội",
            "keywords": [
                "du lịch", "tour", "điểm đến", "khách sạn", "resort",
                "lễ hội", "festival", "di sản", "danh lam", "thắng cảnh",
                "du khách", "homestay"
            ],
            "example_docs": [
                "Việt Nam đón 8 triệu lượt khách quốc tế trong 6 tháng đầu năm",
                "Phú Quốc lọt top 10 đảo đẹp nhất châu Á",
                "Lễ hội hoa Đà Lạt thu hút hàng vạn du khách"
            ],
            "min_confidence": 0.6,
            "color": "#14B8A6",
            "icon": "✈️",
            "display_order": 12
        }
    ]
    
    created_count = 0
    skipped_count = 0
    
    for topic_data in topics_data:
        # Check if exists
        existing = db.query(CustomTopic).filter(CustomTopic.name == topic_data['name']).first()
        if existing:
            print(f"⚠️  Skipped: {topic_data['name']} (already exists)")
            skipped_count += 1
            continue
        
        # Create topic
        topic = CustomTopic(**topic_data)
        db.add(topic)
        created_count += 1
        print(f"✅ Created: {topic_data['name']}")
    
    db.commit()
    db.close()
    
    print(f"\n{'='*60}")
    print(f"✅ Seeded {created_count} topics")
    print(f"⚠️  Skipped {skipped_count} topics (already exist)")
    print(f"{'='*60}")


def seed_templates():
    """Seed templates"""
    db = SessionLocal()
    
    # Template 1: News Categories (Vietnamese)
    template1 = TopicTemplate(
        name="Vietnamese News Categories",
        description="Các chủ đề tin tức phổ biến tại Việt Nam",
        category="news",
        is_public=True,
        topics_data=[
            {
                "name": "Chính trị",
                "description": "Tin chính trị",
                "keywords": ["chính trị", "quốc hội", "chính phủ"],
                "color": "#DC2626",
                "icon": "🏛️"
            },
            {
                "name": "Kinh tế",
                "description": "Tin kinh tế",
                "keywords": ["kinh tế", "GDP", "lạm phát"],
                "color": "#2563EB",
                "icon": "💰"
            },
            {
                "name": "Xã hội",
                "description": "Tin xã hội",
                "keywords": ["xã hội", "dân sinh", "đời sống"],
                "color": "#10B981",
                "icon": "👥"
            },
            {
                "name": "Thể thao",
                "description": "Tin thể thao",
                "keywords": ["thể thao", "bóng đá", "vận động viên"],
                "color": "#F97316",
                "icon": "⚽"
            },
            {
                "name": "Giải trí",
                "description": "Tin giải trí",
                "keywords": ["giải trí", "ca sĩ", "diễn viên"],
                "color": "#EC4899",
                "icon": "🎭"
            }
        ]
    )
    
    # Check if exists
    existing = db.query(TopicTemplate).filter(TopicTemplate.name == template1.name).first()
    if not existing:
        db.add(template1)
        db.commit()
        print(f"✅ Created template: {template1.name}")
    else:
        print(f"⚠️  Template already exists: {template1.name}")
    
    db.close()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🌱 SEEDING CUSTOM TOPICS")
    print("="*60 + "\n")
    
    print("📌 Seeding topics...")
    seed_news_topics()
    
    print("\n📋 Seeding templates...")
    seed_templates()
    
    print("\n✅ SEEDING COMPLETED!\n")
