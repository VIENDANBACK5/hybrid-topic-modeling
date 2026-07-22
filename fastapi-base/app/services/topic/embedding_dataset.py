"""Embedding Dataset - Query database to construct positive training pairs with Quality Filtering"""

import random
import logging
from typing import List, Dict, Tuple, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from sentence_transformers import InputExample

logger = logging.getLogger(__name__)


class EmbeddingDatasetGenerator:
    """Generates positive training pairs from database with Topic Quality Filtering to prevent confirmation bias"""

    def __init__(self, db: Session):
        self.db = db

    def get_latest_completed_session(self) -> Optional[str]:
        """Find the latest completed BERTopic training session ID"""
        query = text("""
            SELECT session_id 
            FROM topic_training_sessions
            WHERE status = 'completed' AND model_type = 'bertopic'
            ORDER BY completed_at DESC
            LIMIT 1
        """)
        result = self.db.execute(query).first()
        return result[0] if result else None

    def get_high_quality_topics(
        self, 
        session_id: str, 
        min_topic_size: int = 20, 
        min_avg_prob: float = 0.85
    ) -> List[Dict[str, Any]]:
        """
        Query and filter topics using Quality Filtering:
        - Must belong to the specified session_id
        - Exclude outlier topic (-1)
        - Must have at least min_topic_size documents
        - Average assignment probability must be >= min_avg_prob
        """
        query = text("""
            SELECT 
                t.id as db_topic_id,
                t.topic_id,
                t.document_count,
                AVG(m.probability) as avg_prob
            FROM bertopic_discovered_topics t
            JOIN article_bertopic_topics m ON t.id = m.bertopic_topic_id
            WHERE t.training_session_id = :session_id
              AND t.topic_id != -1
              AND t.document_count >= :min_topic_size
            GROUP BY t.id, t.topic_id, t.document_count
            HAVING AVG(m.probability) >= :min_avg_prob
        """)
        
        result = self.db.execute(query, {
            "session_id": session_id,
            "min_topic_size": min_topic_size,
            "min_avg_prob": min_avg_prob
        }).fetchall()
        
        topics = []
        for r in result:
            topics.append({
                "db_topic_id": r[0],
                "topic_id": r[1],
                "document_count": r[2],
                "avg_prob": float(r[3])
            })
            
        logger.info(f"Quality Filtered: Found {len(topics)} topics (out of session {session_id}) with size >= {min_topic_size} and avg prob >= {min_avg_prob}")
        return topics

    def build_positive_pairs(
        self, 
        topics: List[Dict[str, Any]], 
        session_id: str, 
        max_pairs_per_topic: int = 200,
        min_doc_prob: float = 0.9
    ) -> List[Tuple[str, str, int]]:
        """
        For each high-quality topic:
        - Retrieve all articles associated with probability >= min_doc_prob
        - Pair them up randomly up to max_pairs_per_topic
        Returns:
            List of (doc_a_text, doc_b_text, topic_id)
        """
        all_pairs = []
        
        for topic in topics:
            db_topic_id = topic["db_topic_id"]
            topic_id = topic["topic_id"]
            
            # Fetch article title and content for documents in this topic with high probability
            query = text("""
                SELECT a.title, a.content
                FROM articles a
                JOIN article_bertopic_topics m ON a.id = m.article_id
                WHERE m.bertopic_topic_id = :db_topic_id
                  AND m.training_session_id = :session_id
                  AND m.probability >= :min_doc_prob
                  AND a.content IS NOT NULL
            """)
            
            rows = self.db.execute(query, {
                "db_topic_id": db_topic_id,
                "session_id": session_id,
                "min_doc_prob": min_doc_prob
            }).fetchall()
            
            documents = []
            for r in rows:
                title = r[0] or ""
                content = r[1] or ""
                doc = f"{title}\n{content}".strip()
                if len(doc) > 50:  # Skip trivial texts
                    documents.append(doc)
            
            num_docs = len(documents)
            if num_docs < 2:
                continue
                
            # Construct pairs
            topic_pairs = []
            # If the number of documents is small, we can generate all combinations
            # If large, we sample pairs randomly
            if num_docs * (num_docs - 1) // 2 <= max_pairs_per_topic:
                for i in range(num_docs):
                    for j in range(i + 1, num_docs):
                        topic_pairs.append((documents[i], documents[j], topic_id))
            else:
                # Randomly sample pairs to avoid combinatorial explosion
                attempts = 0
                while len(topic_pairs) < max_pairs_per_topic and attempts < max_pairs_per_topic * 5:
                    idx1, idx2 = random.sample(range(num_docs), 2)
                    pair = (documents[idx1], documents[idx2], topic_id)
                    if pair not in topic_pairs and (pair[1], pair[0], pair[2]) not in topic_pairs:
                        topic_pairs.append(pair)
                    attempts += 1
            
            all_pairs.extend(topic_pairs)
            logger.info(f"   Topic {topic_id}: Generated {len(topic_pairs)} positive pairs from {num_docs} documents")

        return all_pairs

    def generate_input_examples(
        self, 
        min_topic_size: int = 20, 
        min_avg_prob: float = 0.85, 
        max_pairs_per_topic: int = 200,
        min_doc_prob: float = 0.9,
        val_split: float = 0.1
    ) -> Tuple[List[InputExample], List[InputExample], int]:
        """
        Main pipeline:
        1. Find latest completed BERTopic session
        2. Query high-quality topics
        3. Build positive pairs
        4. Split into train & validation sets and wrap in InputExample
        
        Returns:
            (train_examples, val_examples, num_raw_documents_used)
        """
        session_id = self.get_latest_completed_session()
        if not session_id:
            logger.warning("No completed BERTopic sessions found in DB to generate training pairs.")
            return [], [], 0
            
        topics = self.get_high_quality_topics(
            session_id=session_id,
            min_topic_size=min_topic_size,
            min_avg_prob=min_avg_prob
        )
        
        if not topics:
            logger.warning("No topics passed the quality filtering criteria.")
            return [], [], 0
            
        raw_pairs = self.build_positive_pairs(
            topics=topics,
            session_id=session_id,
            max_pairs_per_topic=max_pairs_per_topic,
            min_doc_prob=min_doc_prob
        )
        
        if not raw_pairs:
            logger.warning("No positive pairs could be constructed from filtered topics.")
            return [], [], 0
            
        # Count distinct documents used
        unique_docs = set()
        for doc_a, doc_b, _ in raw_pairs:
            unique_docs.add(doc_a)
            unique_docs.add(doc_b)
            
        # Shuffle raw pairs
        random.seed(42)
        random.shuffle(raw_pairs)
        
        # Convert to InputExamples (MultipleNegativesRankingLoss takes pairs of texts)
        examples = [InputExample(texts=[p[0], p[1]]) for p in raw_pairs]
        
        # Split into train & validation
        split_idx = int(len(examples) * (1 - val_split))
        train_examples = examples[:split_idx]
        val_examples = examples[split_idx:]
        
        logger.info(f"Embedding dataset generation complete: {len(train_examples)} train pairs, {len(val_examples)} validation pairs (used {len(unique_docs)} documents)")
        
        return train_examples, val_examples, len(unique_docs)
