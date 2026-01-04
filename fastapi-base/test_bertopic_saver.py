#!/usr/bin/env python3
"""
Test script để demo việc lưu BERTopic discovered topics vào database
"""

import sys
import time
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Mock BERTopic result for demonstration
MOCK_BERTOPIC_RESULT = {
    'topics': [
        {
            'topic_id': 0,
            'natural_label': 'Chính trị & Chính phủ',
            'description': 'Các chủ đề về chính trị, quốc hội, chính phủ',
            'count': 45,
            'words': [
                {'word': 'chính phủ', 'score': 0.85},
                {'word': 'quốc hội', 'score': 0.78},
                {'word': 'nghị quyết', 'score': 0.72},
                {'word': 'bộ trưởng', 'score': 0.68},
                {'word': 'chính sách', 'score': 0.65},
            ],
            'representative_docs': [
                'Quốc hội thông qua nghị quyết về chính sách tài chính',
                'Chính phủ ban hành quy định mới về đầu tư',
                'Bộ trưởng trình bày báo cáo tại phiên họp'
            ]
        },
        {
            'topic_id': 1,
            'natural_label': 'Kinh tế & Đầu tư',
            'description': 'Các tin về kinh tế, đầu tư, tài chính',
            'count': 38,
            'words': [
                {'word': 'đầu tư', 'score': 0.88},
                {'word': 'kinh tế', 'score': 0.82},
                {'word': 'doanh nghiệp', 'score': 0.75},
                {'word': 'tăng trưởng', 'score': 0.70},
                {'word': 'thị trường', 'score': 0.67},
            ],
            'representative_docs': [
                'Tăng trưởng kinh tế đạt 6.5% trong quý III',
                'Doanh nghiệp FDI đầu tư 2 tỷ USD vào Việt Nam',
                'Thị trường chứng khoán phục hồi mạnh mẽ'
            ]
        },
        {
            'topic_id': 2,
            'natural_label': 'Du lịch & Văn hóa',
            'description': 'Các bài về du lịch, di sản văn hóa',
            'count': 32,
            'words': [
                {'word': 'du lịch', 'score': 0.90},
                {'word': 'di sản', 'score': 0.80},
                {'word': 'lễ hội', 'score': 0.75},
                {'word': 'văn hóa', 'score': 0.72},
                {'word': 'du khách', 'score': 0.68},
            ],
            'representative_docs': [
                'Hưng Yên phát triển du lịch di sản văn hóa Phố Hiến',
                'Lễ hội truyền thống thu hút hàng nghìn du khách',
                'Di sản văn hóa phi vật thể được bảo tồn'
            ]
        },
        {
            'topic_id': 3,
            'natural_label': 'Giáo dục & Đào tạo',
            'description': 'Tin tức về giáo dục, trường học, thi cử',
            'count': 28,
            'words': [
                {'word': 'giáo dục', 'score': 0.87},
                {'word': 'trường học', 'score': 0.79},
                {'word': 'học sinh', 'score': 0.76},
                {'word': 'thi cử', 'score': 0.71},
                {'word': 'đào tạo', 'score': 0.68},
            ],
            'representative_docs': [
                'Trường học đầu tư cơ sở vật chất hiện đại',
                'Học sinh đạt giải quốc gia môn toán',
                'Kỳ thi tốt nghiệp THPT diễn ra thuận lợi'
            ]
        },
        {
            'topic_id': 4,
            'natural_label': 'Y tế & Sức khỏe',
            'description': 'Các tin về y tế, bệnh viện, chăm sóc sức khỏe',
            'count': 25,
            'words': [
                {'word': 'y tế', 'score': 0.89},
                {'word': 'bệnh viện', 'score': 0.83},
                {'word': 'bệnh nhân', 'score': 0.77},
                {'word': 'sức khỏe', 'score': 0.74},
                {'word': 'vaccine', 'score': 0.69},
            ],
            'representative_docs': [
                'Bệnh viện đa khoa tỉnh nâng cấp trang thiết bị',
                'Chương trình tiêm chủng miễn phí cho trẻ em',
                'Bệnh nhân COVID-19 được điều trị thành công'
            ]
        },
        {
            'topic_id': -1,
            'natural_label': 'Outliers',
            'description': 'Các bài không thuộc topic nào rõ ràng',
            'count': 12,
            'words': [],
            'representative_docs': []
        }
    ]
}

MOCK_DOCUMENT_TOPICS = [
    {'doc_id': 324, 'topic_id': 0, 'probability': 0.85},
    {'doc_id': 325, 'topic_id': 0, 'probability': 0.78},
    {'doc_id': 326, 'topic_id': 1, 'probability': 0.92},
    {'doc_id': 327, 'topic_id': 1, 'probability': 0.76},
    {'doc_id': 328, 'topic_id': 2, 'probability': 0.88},
    {'doc_id': 329, 'topic_id': 2, 'probability': 0.81},
    {'doc_id': 330, 'topic_id': 3, 'probability': 0.79},
    {'doc_id': 331, 'topic_id': 3, 'probability': 0.85},
    {'doc_id': 332, 'topic_id': 4, 'probability': 0.90},
    {'doc_id': 333, 'topic_id': 4, 'probability': 0.77},
    {'doc_id': 334, 'topic_id': -1, 'probability': 0.30},
    {'doc_id': 335, 'topic_id': -1, 'probability': 0.25},
]

def main():
    print("\n" + "="*80)
    print("DEMO: Lưu BERTopic Discovered Topics vào Database")
    print("="*80 + "\n")
    
    # Import saver
    sys.path.insert(0, '/app')
    from app.services.topic.bertopic_saver import BertopicTopicSaver
    
    # Connect to database
    DATABASE_URL = "postgresql://postgres:postgres@db:5432/DBHuYe"
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        saver = BertopicTopicSaver()
        
        # Mock training parameters
        training_params = {
            'model_type': 'bertopic',
            'model_version': 'v1.0.0',
            'min_topic_size': 10,
            'embedding_model': 'paraphrase-multilingual-MiniLM-L12-v2',
            'use_vietnamese_tokenizer': True,
            'use_topicgpt': False,
            'num_documents': 200,
            'training_duration_seconds': 45.5
        }
        
        print("🚀 Bước 1: Lưu thông tin training session...")
        start_time = time.time()
        
        session_id = saver.save_full_training_result(
            db=db,
            topic_model_result=MOCK_BERTOPIC_RESULT,
            training_params=training_params,
            document_topics=MOCK_DOCUMENT_TOPICS,
            model_saved_path='/app/data/models/bertopic_model_20240115.pkl',
            notes='Demo training session - Mock data'
        )
        
        elapsed = time.time() - start_time
        
        print(f"✅ Hoàn thành trong {elapsed:.2f}s")
        print(f"\n📋 Training Session ID: {session_id}")
        
        # Query results
        print("\n" + "-"*80)
        print("📊 KẾT QUẢ ĐÃ LƯU:")
        print("-"*80 + "\n")
        
        # Training session
        from app.models.model_bertopic_discovered import TopicTrainingSession
        session = db.query(TopicTrainingSession).filter(
            TopicTrainingSession.session_id == session_id
        ).first()
        
        print(f"✅ Training Session:")
        print(f"   - Session ID: {session.session_id}")
        print(f"   - Model: {session.model_type}")
        print(f"   - Documents: {session.num_documents}")
        print(f"   - Topics found: {session.num_topics_found}")
        print(f"   - Outliers: {session.num_outliers}")
        print(f"   - Duration: {session.training_duration_seconds}s")
        print(f"   - Status: {session.status}")
        print(f"   - Model path: {session.model_saved_path}")
        
        # Discovered topics
        from app.models.model_bertopic_discovered import BertopicDiscoveredTopic
        topics = db.query(BertopicDiscoveredTopic).filter(
            BertopicDiscoveredTopic.training_session_id == session_id
        ).order_by(BertopicDiscoveredTopic.topic_id).all()
        
        print(f"\n✅ Discovered Topics: {len(topics)} topics")
        for topic in topics:
            if topic.is_outlier:
                print(f"   {topic.topic_id}. {topic.topic_label} (outlier)")
                print(f"      - Documents: {topic.document_count}")
            else:
                keywords = [f"{kw['word']} ({kw['score']:.2f})" for kw in topic.keywords[:3]]
                print(f"   {topic.topic_id}. {topic.topic_label}")
                print(f"      - Documents: {topic.document_count}")
                print(f"      - Keywords: {', '.join(keywords)}")
        
        # Article mappings
        from app.models.model_bertopic_discovered import ArticleBertopicTopic
        mappings_count = db.query(ArticleBertopicTopic).filter(
            ArticleBertopicTopic.training_session_id == session_id
        ).count()
        
        print(f"\n✅ Article-Topic Mappings: {mappings_count} mappings")
        
        # Sample mappings
        from sqlalchemy import func
        sample_mappings = db.query(
            ArticleBertopicTopic.article_id,
            BertopicDiscoveredTopic.topic_label,
            ArticleBertopicTopic.probability
        ).join(
            BertopicDiscoveredTopic,
            ArticleBertopicTopic.bertopic_topic_id == BertopicDiscoveredTopic.id
        ).filter(
            ArticleBertopicTopic.training_session_id == session_id,
            BertopicDiscoveredTopic.topic_id != -1
        ).order_by(
            ArticleBertopicTopic.probability.desc()
        ).limit(5).all()
        
        print("\n   Top 5 mappings by confidence:")
        for article_id, topic_label, prob in sample_mappings:
            print(f"   - Article {article_id} → {topic_label} ({prob:.2f})")
        
        # Topic distribution
        topic_dist = db.query(
            BertopicDiscoveredTopic.topic_label,
            func.count(ArticleBertopicTopic.id).label('count')
        ).join(
            ArticleBertopicTopic,
            BertopicDiscoveredTopic.id == ArticleBertopicTopic.bertopic_topic_id
        ).filter(
            BertopicDiscoveredTopic.training_session_id == session_id,
            BertopicDiscoveredTopic.topic_id != -1
        ).group_by(
            BertopicDiscoveredTopic.topic_label
        ).order_by(
            func.count(ArticleBertopicTopic.id).desc()
        ).all()
        
        print("\n📈 Phân bố articles theo topic:")
        for topic_label, count in topic_dist:
            print(f"   - {topic_label}: {count} articles")
        
        print("\n" + "="*80)
        print("✅ DEMO HOÀN THÀNH!")
        print("="*80)
        print("\n💡 Khi train BERTopic thực tế, chỉ cần gọi:")
        print("   saver.save_full_training_result(db, topic_model_result, params, doc_topics)")
        print("\n📝 Dữ liệu đã được lưu vào 3 bảng:")
        print("   1. topic_training_sessions - Thông tin session")
        print("   2. bertopic_discovered_topics - Các topics phát hiện được")
        print("   3. article_bertopic_topics - Mapping articles ↔ topics")
        print("\n🔄 Có thể:")
        print("   - Review các topics phát hiện được")
        print("   - Convert sang custom topics")
        print("   - Theo dõi evolution của topics qua các lần training")
        print("   - So sánh custom vs discovered topics\n")
        
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
