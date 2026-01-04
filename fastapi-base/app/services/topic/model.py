from pathlib import Path
from typing import List, Optional, Dict, Tuple
import numpy as np
import logging

logger = logging.getLogger(__name__)


class TopicModel:
    def __init__(
        self,
        model_dir: str = "data/models",
        use_gpu: bool = False,
        min_topic_size: int = 10,
        embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        use_vietnamese_tokenizer: bool = True,
        enable_topicgpt: bool = False
    ):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.use_gpu = use_gpu
        self.min_topic_size = min_topic_size
        self.embedding_model_name = embedding_model
        self.use_vietnamese_tokenizer = use_vietnamese_tokenizer
        self.enable_topicgpt = enable_topicgpt
        
        self.topic_model = None
        self.embedding_model = None
        self.topics = None
        self.probs = None
        self.vietnamese_tokenizer = None
        self.topicgpt_service = None
        
        # Setup Vietnamese tokenizer nếu enable
        if self.use_vietnamese_tokenizer:
            self._setup_vietnamese_tokenizer()
        
        # Setup TopicGPT nếu enable
        if self.enable_topicgpt:
            self._setup_topicgpt()
    
    def _setup_vietnamese_tokenizer(self):
        """Setup Underthesea Vietnamese tokenizer"""
        try:
            from app.services.etl.vietnamese_tokenizer import get_vietnamese_tokenizer
            self.vietnamese_tokenizer = get_vietnamese_tokenizer()
            if self.vietnamese_tokenizer:
                logger.info("✅ Vietnamese tokenizer enabled (Underthesea)")
            else:
                logger.warning("⚠️ Vietnamese tokenizer not available, using default")
        except Exception as e:
            logger.warning(f"⚠️ Could not setup Vietnamese tokenizer: {e}")
            self.vietnamese_tokenizer = None
    
    def _setup_topicgpt(self):
        """Setup TopicGPT service for LLM enhancement"""
        try:
            from app.services.topic.topicgpt_service import get_topicgpt_service
            self.topicgpt_service = get_topicgpt_service()
            if self.topicgpt_service and self.topicgpt_service.client:
                logger.info(f"✅ TopicGPT enabled ({self.topicgpt_service.api}/{self.topicgpt_service.model})")
            else:
                logger.warning("⚠️ TopicGPT not available (no API key)")
                self.topicgpt_service = None
        except Exception as e:
            logger.warning(f"⚠️ Could not setup TopicGPT: {e}")
            self.topicgpt_service = None
    
    def _setup_embedding_model(self):
        from sentence_transformers import SentenceTransformer
        
        device = 'cuda' if self.use_gpu else 'cpu'
        self.embedding_model = SentenceTransformer(self.embedding_model_name, device=device)
        logger.info(f"Embedding model loaded on {device}")
        return self.embedding_model
    
    def _setup_umap(self, n_samples: int):
        from umap import UMAP
        # Adjust n_neighbors based on sample size
        n_neighbors = min(15, n_samples - 1) if n_samples > 1 else 1
        n_components = min(5, n_samples - 1) if n_samples > 1 else 1
        
        return UMAP(
            n_components=n_components,
            n_neighbors=n_neighbors,
            min_dist=0.0,
            metric='cosine',
            random_state=42
        )
    
    def _setup_hdbscan(self):
        from hdbscan import HDBSCAN
        return HDBSCAN(
            min_cluster_size=self.min_topic_size,
            min_samples=5,
            metric='euclidean',
            cluster_selection_method='eom',
            prediction_data=True
        )
    
    def _preprocess_vietnamese(self, text: str) -> str:
        """Preprocess Vietnamese text với tokenizer"""
        if not text or not self.vietnamese_tokenizer:
            return text
        
        try:
            # Tokenize và join lại với underscore
            tokens = self.vietnamese_tokenizer(text)
            # Chỉ lấy từ đơn và bigrams (bỏ trigrams để không quá dài)
            filtered = [t for t in tokens if ' ' not in t or t.count(' ') == 1]
            return ' '.join(filtered) if filtered else text
        except Exception as e:
            logger.warning(f"⚠️ Vietnamese preprocessing error: {e}")
            return text
    
    def fit(self, documents: List[str], db=None, save_to_db: bool = True, article_ids: List[int] = None) -> Tuple[List[int], np.ndarray]:
        """
        Fit BERTopic model và tự động lưu discovered topics vào database
        
        Args:
            documents: List of documents
            db: Database session (optional, nếu muốn lưu vào DB)
            save_to_db: Enable auto-save to database
            article_ids: List of article IDs tương ứng với documents
        """
        from bertopic import BERTopic
        from sklearn.feature_extraction.text import CountVectorizer
        import time
        import uuid
        
        if not self.embedding_model:
            self._setup_embedding_model()
        
        logger.info(f"Fitting BERTopic on {len(documents)} documents...")
        training_start_time = time.time()
        
        # Preprocess với Vietnamese tokenizer nếu enabled
        processed_documents = documents  # Keep original
        if self.use_vietnamese_tokenizer and self.vietnamese_tokenizer:
            logger.info("🔧 Preprocessing documents with Vietnamese tokenizer...")
            try:
                processed_documents = [self._preprocess_vietnamese(doc) for doc in documents]
                logger.info("✅ Vietnamese preprocessing completed")
            except Exception as e:
                logger.warning(f"⚠️ Vietnamese preprocessing failed: {e}, using original docs")
                processed_documents = documents
        
        umap_model = self._setup_umap(len(processed_documents))
        hdbscan_model = self._setup_hdbscan()
        
        min_df_value = 1 if len(processed_documents) < 100 else max(1, min(3, len(processed_documents) // 50))
        max_df_value = 1.0 if len(processed_documents) < 100 else 0.85  # No max_df limit for small datasets
        
        # Vietnamese stopwords
        vietnamese_stopwords = [
            'là', 'của', 'và', 'có', 'được', 'cho', 'trong', 'đã', 'này',
            'các', 'với', 'không', 'từ', 'một', 'người', 'những', 'sau',
            'vào', 'ra', 'về', 'như', 'khi', 'sẽ', 'để', 'theo', 'item',
            'href', 'http', 'https', 'www', 'com', 'vn'
        ]
        
        vectorizer_model = CountVectorizer(
            stop_words=vietnamese_stopwords,
            ngram_range=(1, 2 if len(processed_documents) < 50 else 3),  # Smaller ngram for small datasets
            min_df=min_df_value,
            max_df=max_df_value
        )
        
        self.topic_model = BERTopic(
            embedding_model=self.embedding_model,
            umap_model=umap_model,
            hdbscan_model=hdbscan_model,
            vectorizer_model=vectorizer_model,
            top_n_words=10,
            nr_topics=None,
            calculate_probabilities=True,
            verbose=True
        )
        
        self.topics, self.probs = self.topic_model.fit_transform(processed_documents)
        
        training_duration = time.time() - training_start_time
        num_topics = len(set(self.topics)) - 1
        logger.info(f"Topics found: {num_topics} (training took {training_duration:.1f}s)")
        
        # Auto-save to database
        if save_to_db and db is not None:
            try:
                logger.info("💾 Saving discovered topics to database...")
                self._save_to_database(db, documents, training_duration, article_ids)
            except Exception as e:
                logger.error(f"❌ Failed to save topics to database: {e}")
        
        return self.topics, self.probs
    
    def transform(self, documents: List[str]) -> Tuple[List[int], np.ndarray]:
        if not self.topic_model:
            raise ValueError("Model not fitted. Call fit() first.")
        
        topics, probs = self.topic_model.transform(documents)
        return topics, probs
    
    def get_topic_info(self) -> Dict:
        if not self.topic_model:
            raise ValueError("Model not fitted.")
        
        topic_info = self.topic_model.get_topic_info()
        
        results = []
        for _, row in topic_info.iterrows():
            topic_id = int(row['Topic'])
            if topic_id == -1:
                continue
            
            topic_words = self.topic_model.get_topic(topic_id)
            keywords = [word for word, score in topic_words]
            representative_docs = self.topic_model.get_representative_docs(topic_id)
            
            # Replace underscore với space trong keywords cho output
            topic_words_display = [(word.replace('_', ' '), score) for word, score in topic_words]
            
            topic_result = {
                'topic_id': topic_id,
                'count': int(row['Count']),
                'words': [{'word': word, 'score': float(score)} for word, score in topic_words_display],
                'representative_docs': representative_docs
            }
            
            # Enhance với TopicGPT nếu enabled
            if self.enable_topicgpt and self.topicgpt_service:
                try:
                    # Generate natural topic label (no language parameter)
                    label = self.topicgpt_service.generate_topic_label(
                        keywords=keywords[:10],
                        representative_docs=representative_docs[:3]
                    )
                    topic_result['natural_label'] = label
                    
                    # Generate description (needs topic_label)
                    description = self.topicgpt_service.generate_topic_description(
                        topic_label=label,
                        keywords=keywords[:10],
                        representative_docs=representative_docs[:3]
                    )
                    topic_result['description'] = description
                    
                    logger.info(f"✅ TopicGPT enhanced topic {topic_id}: {label}")
                except Exception as e:
                    logger.warning(f"⚠️ TopicGPT failed for topic {topic_id}: {e}")
            
            results.append(topic_result)
        
        return {'topics': results}
    
    def get_document_topics(self, documents: List[str]) -> List[Dict]:
        if not self.topics:
            raise ValueError("No topics assigned. Call fit() first.")
        
        return [
            {
                'doc_id': i,
                'topic_id': int(topic),
                'probability': float(prob[topic]) if prob is not None else 0.0,
                'text': doc[:200]
            }
            for i, (doc, topic, prob) in enumerate(zip(documents, self.topics, self.probs))
        ]
    
    def _save_to_database(self, db, documents: List[str], training_duration: float, article_ids: List[int] = None):
        """Lưu discovered topics vào database sau khi training"""
        import uuid
        from app.services.topic.bertopic_saver import BertopicTopicSaver
        
        # Get topic info from BERTopic
        topic_info_df = self.topic_model.get_topic_info()
        
        # Convert DataFrame to dict format
        topics_data = []
        for _, row in topic_info_df.iterrows():
            topic_id = int(row['Topic'])
            
            # Get top words for this topic
            if topic_id == -1:
                words_data = []
            else:
                topic_words = self.topic_model.get_topic(topic_id)
                words_data = [
                    {'word': word, 'score': float(score)}
                    for word, score in topic_words[:10]
                ]
            
            # Get representative docs
            repr_docs = []
            if hasattr(self.topic_model, 'representative_docs_') and self.topic_model.representative_docs_:
                if topic_id in self.topic_model.representative_docs_:
                    repr_docs = self.topic_model.representative_docs_[topic_id][:3]
            
            topics_data.append({
                'topic_id': topic_id,
                'natural_label': row.get('Name', f'Topic {topic_id}'),
                'description': row.get('Representation', ''),
                'count': int(row.get('Count', 0)),
                'words': words_data,
                'representative_docs': repr_docs
            })
        
        topic_model_result = {'topics': topics_data}
        
        # Prepare document-topic mappings với article_ids thực tế
        document_topics = []
        for i, topic in enumerate(self.topics):
            if article_ids and i < len(article_ids):
                article_id = article_ids[i]  # Use real article ID
            else:
                article_id = i + 1  # Fallback
            
            document_topics.append({
                'doc_id': article_id,
                'topic_id': int(topic),
                'probability': float(self.probs[i][topic]) if self.probs is not None else 0.0
            })
        
        # Training parameters
        training_params = {
            'model_type': 'bertopic',
            'min_topic_size': self.min_topic_size,
            'embedding_model': self.embedding_model_name,
            'use_vietnamese_tokenizer': self.use_vietnamese_tokenizer,
            'use_topicgpt': self.enable_topicgpt,
            'num_documents': len(documents),
            'training_duration_seconds': training_duration
        }
        
        # Save to database
        saver = BertopicTopicSaver()
        session_id = saver.save_full_training_result(
            db=db,
            topic_model_result=topic_model_result,
            training_params=training_params,
            document_topics=document_topics,
            model_saved_path=None,
            notes='Auto-saved from TopicModel.fit()'
        )
        
        logger.info(f"✅ Saved discovered topics to database (session: {session_id})")
        return session_id
    
    def save(self, model_name: str = "bertopic_model"):
        if not self.topic_model:
            raise ValueError("No model to save")
        
        save_path = self.model_dir / model_name
        save_path.mkdir(parents=True, exist_ok=True)
        
        # Save with embedding model name for reload
        self.topic_model.save(
            str(save_path),
            serialization="safetensors",
            save_ctfidf=True,
            save_embedding_model=self.embedding_model_name  # Save model name string
        )
        logger.info(f"Model saved to {save_path}")
        
        return str(save_path)
    
    def load(self, model_name: str = "bertopic_model"):
        from bertopic import BERTopic
        
        load_path = self.model_dir / model_name
        
        if not load_path.exists():
            raise FileNotFoundError(f"Model not found: {load_path}")
        
        # Load model with embedding
        self._setup_embedding_model()
        self.topic_model = BERTopic.load(
            str(load_path),
            embedding_model=self.embedding_model
        )
        logger.info(f"Model loaded from {load_path}")
        
        return self.topic_model
        logger.info(f"Model loaded from {load_path}")
        
        return self.topic_model
