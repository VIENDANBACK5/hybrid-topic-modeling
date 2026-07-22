"""Test script for verifying the embedding fine-tuning pipeline end-to-end"""

import os
import sys
from pathlib import Path
from sqlalchemy import text
from datetime import datetime

# Add root folder to python path
sys.path.append(str(Path(__file__).resolve().parents[3]))

from app.core.database import SessionLocal
from app.services.topic.embedding_manager import EmbeddingManager
from app.services.topic.embedding_dataset import EmbeddingDatasetGenerator
from app.services.topic.embedding_trainer import EmbeddingTrainer
from app.services.topic.embedding_evaluator import EmbeddingEvaluator
from app.models.model_article import Article
from app.models.model_bertopic_discovered import TopicTrainingSession, BertopicDiscoveredTopic, ArticleBertopicTopic
from app.models.model_embedding_training import EmbeddingTrainingSession


def setup_dummy_data_if_needed(db):
    """Inserts dummy data to guarantee training pairs can be generated under any database state"""
    # Check if there is any articles
    count_articles = db.query(Article).count()
    if count_articles < 5:
        print("Inserting dummy articles...")
        for i in range(1, 11):
            art = Article(
                id=1000 + i,
                title=f"Bài viết thử nghiệm công nghệ số {i}",
                content=f"Đây là nội dung bài viết thử nghiệm về chuyển đổi số và kinh tế số lần thứ {i}. Công nghệ Blockchain và Trí tuệ nhân tạo (AI) đang phát triển rất nhanh tại Việt Nam.",
                created_at=datetime.now()
            )
            db.add(art)
        db.commit()
        
    # Always create a new test session to ensure independent and reproducible execution
    import uuid
    session_id = f"session_test_{uuid.uuid4().hex[:8]}"
    print(f"Creating test BERTopic session: {session_id}")
    ts = TopicTrainingSession(
        session_id=session_id,
        model_type="bertopic",
        min_topic_size=2,
        num_documents=10,
        status="completed",
        started_at=datetime.now(),
        completed_at=datetime.now()
    )
    db.add(ts)
    db.commit()
    
    # Insert a high quality topic
    topic = BertopicDiscoveredTopic(
        training_session_id=session_id,
        topic_id=1,
        topic_label="Chuyển đổi số & AI",
        keywords={"words": [{"word": "công_nghệ", "score": 0.9}, {"word": "số", "score": 0.8}]},
        document_count=10,
        is_outlier=False
    )
    db.add(topic)
    db.commit()
    
    # Mappings
    articles = db.query(Article).limit(10).all()
    for idx, art in enumerate(articles):
        mapping = ArticleBertopicTopic(
            article_id=art.id,
            bertopic_topic_id=topic.id,
            probability=0.95,
            training_session_id=session_id
        )
        db.add(mapping)
    db.commit()
    return session_id


def main():
    print("==================================================")
    print("STARTING EMBEDDING PIPELINE END-TO-END VERIFICATION")
    print("==================================================")
    
    db = SessionLocal()
    try:
        # Create database tables if they do not exist
        from app.models.model_base import Base
        from app.core.database import get_engine
        Base.metadata.create_all(bind=get_engine())
        
        # Prep dummy data and get fresh session ID
        test_session_id = setup_dummy_data_if_needed(db)
        
        # Monkeypatch the class to return our test session ID for all instances
        EmbeddingDatasetGenerator.get_latest_completed_session = lambda self: test_session_id
        
        # 1. Test EmbeddingManager
        print("\n--- 1. Testing EmbeddingManager ---")
        manager = EmbeddingManager()
        active_config = manager.get_active_config()
        print(f"Current active model: {active_config['active_version']} ({active_config['model_path']})")
        
        # 2. Test Dataset Generator
        print("\n--- 2. Testing EmbeddingDatasetGenerator ---")
        dataset_generator = EmbeddingDatasetGenerator(db)
        latest_session = dataset_generator.get_latest_completed_session()
        print(f"Latest completed BERTopic session: {latest_session}")
        
        # Generate examples (use very loose parameters to guarantee we get pairs from dummy data)
        train_ex, val_ex, num_docs = dataset_generator.generate_input_examples(
            min_topic_size=2,
            min_avg_prob=0.5,
            max_pairs_per_topic=5,
            min_doc_prob=0.5,
            val_split=0.2
        )
        print(f"Generated {len(train_ex)} training examples, {len(val_ex)} validation examples using {num_docs} documents.")
        assert len(train_ex) > 0, "No training pairs generated!"
        
        # 3. Test Trainer & Evaluator
        print("\n--- 3. Testing EmbeddingTrainer & Evaluator (Micro-training) ---")
        trainer = EmbeddingTrainer(db)
        
        # Run training with micro hyperparameters to finish fast (1 epoch, batch_size 2)
        print("Running micro fine-tuning session...")
        result = trainer.run_fine_tuning(
            epochs=1,
            batch_size=2,
            learning_rate=2e-5,
            warmup_ratio=0.0,
            min_topic_size=2,
            min_avg_prob=0.5,
            max_pairs_per_topic=5,
            min_doc_prob=0.5,
            val_split=0.2,
            force_train=True
        )
        
        print(f"Training status: {result['status']}")
        if result['status'] == 'success':
            print(f"Version generated: {result['version']}")
            print(f"Candidate Metrics: {result['metrics']}")
            print(f"Deployed: {result['deployed']} (Reason: {result['reason']})")
        else:
            print(f"Training failed or skipped: {result.get('error') or result.get('message')}")
            sys.exit(1)

        # 4. Verify EmbeddingManager loading the fine-tuned model
        print("\n--- 4. Verifying Model Loading ---")
        loaded_model = manager.get_current_model(device="cpu")
        print(f"Successfully loaded model: {loaded_model}")
        
        print("\n==================================================")
        print("VERIFICATION COMPLETED SUCCESSFULLY!")
        print("==================================================")
        
    except Exception as e:
        print(f"\n❌ Verification failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
