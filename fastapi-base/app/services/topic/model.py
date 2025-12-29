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
        embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    ):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.use_gpu = use_gpu
        self.min_topic_size = min_topic_size
        self.embedding_model_name = embedding_model
        
        self.topic_model = None
        self.embedding_model = None
        self.topics = None
        self.probs = None
    
    def _setup_embedding_model(self):
        from sentence_transformers import SentenceTransformer
        
        device = 'cuda' if self.use_gpu else 'cpu'
        self.embedding_model = SentenceTransformer(self.embedding_model_name, device=device)
        logger.info(f"Embedding model loaded on {device}")
        return self.embedding_model
    
    def _setup_umap(self):
        from umap import UMAP
        return UMAP(
            n_components=5,
            n_neighbors=15,
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
    
    def fit(self, documents: List[str]) -> Tuple[List[int], np.ndarray]:
        from bertopic import BERTopic
        from sklearn.feature_extraction.text import CountVectorizer
        
        if not self.embedding_model:
            self._setup_embedding_model()
        
        logger.info(f"Fitting BERTopic on {len(documents)} documents...")
        
        umap_model = self._setup_umap()
        hdbscan_model = self._setup_hdbscan()
        
        min_df_value = max(1, min(3, len(documents) // 50))
        
        vectorizer_model = CountVectorizer(
            stop_words=None,
            ngram_range=(1, 2),
            min_df=min_df_value
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
        
        self.topics, self.probs = self.topic_model.fit_transform(documents)
        
        logger.info(f"Topics found: {len(set(self.topics)) - 1}")
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
            
            results.append({
                'topic_id': topic_id,
                'count': int(row['Count']),
                'words': [{'word': word, 'score': float(score)} for word, score in topic_words],
                'representative_docs': self.topic_model.get_representative_docs(topic_id)
            })
        
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
    
    def save(self, model_name: str = "bertopic_model"):
        if not self.topic_model:
            raise ValueError("No model to save")
        
        model_dir = self.model_dir / model_name
        model_dir.mkdir(parents=True, exist_ok=True)
        
        save_path = model_dir / "model"
        self.topic_model.save(str(save_path), serialization="pytorch", save_ctfidf=True, save_embedding_model=False)
        logger.info(f"Model saved to {save_path}")
        
        return str(model_dir)
    
    def load(self, model_name: str = "bertopic_model"):
        from bertopic import BERTopic
        
        load_path = self.model_dir / model_name
        
        if not load_path.exists():
            raise FileNotFoundError(f"Model not found: {load_path}")
        
        self.topic_model = BERTopic.load(str(load_path))
        logger.info(f"Model loaded from {load_path}")
        
        return self.topic_model
