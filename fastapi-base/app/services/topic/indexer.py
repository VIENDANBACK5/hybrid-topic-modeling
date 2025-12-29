import numpy as np
import faiss
from pathlib import Path
from typing import List, Tuple, Optional
import pickle
import logging

logger = logging.getLogger(__name__)


class FAISSIndexer:
    def __init__(self, index_dir: str = "data/indexes", dimension: int = 768):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        self.dimension = dimension
        self.index = None
        self.id_map = {}
    
    def build(self, embeddings: np.ndarray, doc_ids: List[str]):
        if embeddings.shape[1] != self.dimension:
            raise ValueError(f"Embedding dimension mismatch: {embeddings.shape[1]} vs {self.dimension}")
        
        logger.info(f"Building FAISS index for {len(embeddings)} vectors")
        
        embeddings = embeddings.astype('float32')
        
        self.index = faiss.IndexFlatIP(self.dimension)
        
        faiss.normalize_L2(embeddings)
        
        self.index.add(embeddings)
        
        self.id_map = {i: doc_id for i, doc_id in enumerate(doc_ids)}
        
        logger.info(f"FAISS index built: {self.index.ntotal} vectors")
    
    def is_built(self) -> bool:
        """Check if index is built"""
        return self.index is not None and self.index.ntotal > 0
    
    def search(self, query_embedding: np.ndarray, k: int = 10) -> List[Tuple[str, float]]:
        if self.index is None:
            raise ValueError("Index not built. Call build() first.")
        
        query_embedding = query_embedding.astype('float32').reshape(1, -1)
        faiss.normalize_L2(query_embedding)
        
        scores, indices = self.index.search(query_embedding, k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1:
                doc_id = self.id_map.get(int(idx))
                results.append((doc_id, float(score)))
        
        return results
    
    def save(self, index_name: str = "faiss_index"):
        if self.index is None:
            raise ValueError("No index to save")
        
        index_path = self.index_dir / f"{index_name}.index"
        map_path = self.index_dir / f"{index_name}_map.pkl"
        
        faiss.write_index(self.index, str(index_path))
        
        with open(map_path, 'wb') as f:
            pickle.dump(self.id_map, f)
        
        logger.info(f"Index saved to {index_path}")
        return str(index_path)
    
    def load(self, index_name: str = "faiss_index"):
        index_path = self.index_dir / f"{index_name}.index"
        map_path = self.index_dir / f"{index_name}_map.pkl"
        
        if not index_path.exists():
            raise FileNotFoundError(f"Index not found: {index_path}")
        
        self.index = faiss.read_index(str(index_path))
        
        with open(map_path, 'rb') as f:
            self.id_map = pickle.load(f)
        
        logger.info(f"Index loaded from {index_path}: {self.index.ntotal} vectors")
        return self.index
