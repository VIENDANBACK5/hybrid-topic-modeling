#!/usr/bin/env python3
"""
Test tích hợp: Train BERTopic và tự động lưu vào database
"""

import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def main():
    print("\n" + "="*80)
    print("TEST TÍCH HỢP: BERTopic Training → Auto-save to Database")
    print("="*80 + "\n")
    
    sys.path.insert(0, '/app')
    
    from app.services.topic.model import TopicModel
    from app.models.model_article import Article
    
    # Connect to database
    DATABASE_URL = "postgresql://postgres:postgres@db:5432/DBHuYe"
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # 1. Load articles from database
        print("📚 Bước 1: Load articles từ database...")
        articles = db.query(Article).limit(50).all()
        documents = [f"{a.title} {a.content or ''}" for a in articles]
        article_ids = [a.id for a in articles]
        
        print(f"   ✅ Loaded {len(documents)} articles")
        print(f"   📋 Article IDs: {article_ids[:10]}...")
        
        # 2. Train BERTopic với auto-save
        print("\n🤖 Bước 2: Training BERTopic với auto-save...")
        topic_model = TopicModel(
            min_topic_size=3,
            use_vietnamese_tokenizer=True,
            enable_topicgpt=False
        )
        
        # Fit with db session - will auto-save
        topics, probs = topic_model.fit(documents, db=db, save_to_db=True, article_ids=article_ids)
        
        num_topics = len(set(topics)) - 1
        print(f"\n   ✅ Training completed!")
        print(f"   📊 Topics discovered: {num_topics}")
        
        # 3. Verify saved data
        print("\n🔍 Bước 3: Verify dữ liệu đã lưu...")
        
        from app.models.model_bertopic_discovered import (
            TopicTrainingSession,
            BertopicDiscoveredTopic,
            ArticleBertopicTopic
        )
        
        # Latest session
        latest_session = db.query(TopicTrainingSession).order_by(
            TopicTrainingSession.created_at.desc()
        ).first()
        
        if latest_session:
            print(f"\n   ✅ Training Session:")
            print(f"      - ID: {latest_session.session_id}")
            print(f"      - Documents: {latest_session.num_documents}")
            print(f"      - Topics found: {latest_session.num_topics_found}")
            print(f"      - Duration: {latest_session.training_duration_seconds:.1f}s")
            print(f"      - Status: {latest_session.status}")
            
            # Topics in this session
            session_topics = db.query(BertopicDiscoveredTopic).filter(
                BertopicDiscoveredTopic.training_session_id == latest_session.session_id
            ).order_by(BertopicDiscoveredTopic.topic_id).all()
            
            print(f"\n   ✅ Discovered Topics: {len(session_topics)} topics")
            for topic in session_topics[:5]:
                if topic.is_outlier:
                    print(f"      {topic.topic_id}. Outliers ({topic.document_count} docs)")
                else:
                    keywords = [kw['word'] for kw in topic.keywords[:3]]
                    print(f"      {topic.topic_id}. {', '.join(keywords)} ({topic.document_count} docs)")
            
            if len(session_topics) > 5:
                print(f"      ... and {len(session_topics) - 5} more topics")
            
            # Mappings
            mappings_count = db.query(ArticleBertopicTopic).filter(
                ArticleBertopicTopic.training_session_id == latest_session.session_id
            ).count()
            
            print(f"\n   ✅ Article-Topic Mappings: {mappings_count} mappings")
            
            # Top articles by confidence
            from sqlalchemy import func
            top_mappings = db.query(
                Article.title,
                BertopicDiscoveredTopic.topic_label,
                ArticleBertopicTopic.probability
            ).join(
                ArticleBertopicTopic,
                Article.id == ArticleBertopicTopic.article_id
            ).join(
                BertopicDiscoveredTopic,
                ArticleBertopicTopic.bertopic_topic_id == BertopicDiscoveredTopic.id
            ).filter(
                ArticleBertopicTopic.training_session_id == latest_session.session_id,
                BertopicDiscoveredTopic.topic_id != -1
            ).order_by(
                ArticleBertopicTopic.probability.desc()
            ).limit(5).all()
            
            print(f"\n   📈 Top 5 classifications:")
            for title, topic_label, prob in top_mappings:
                print(f"      - {title[:60]}... → {topic_label} ({prob:.3f})")
        
        print("\n" + "="*80)
        print("✅ TEST HOÀN THÀNH!")
        print("="*80)
        print("\n💡 Kết luận:")
        print("   - BERTopic đã tự động lưu topics vào database sau khi train")
        print("   - Có thể review, convert sang custom topics, hoặc theo dõi evolution")
        print("   - Không cần code thêm gì, chỉ cần gọi: topic_model.fit(docs, db=db)\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()

if __name__ == '__main__':
    sys.exit(main())
