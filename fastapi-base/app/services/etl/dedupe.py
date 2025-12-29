import hashlib
from typing import List, Dict, Set
import logging

logger = logging.getLogger(__name__)


class Deduplicator:
    def __init__(self, threshold: float = 0.9):
        self.threshold = threshold
        self.seen_hashes: Set[str] = set()
    
    def deduplicate(self, documents: List[Dict]) -> List[Dict]:
        unique_docs = []
        
        for doc in documents:
            url = doc.get('metadata', {}).get('url', '')
            content = doc.get('cleaned_content') or doc.get('raw_content', '')
            
            dedupe_key = url if url else content
            doc_hash = self._compute_hash(dedupe_key)
            
            if doc_hash not in self.seen_hashes:
                self.seen_hashes.add(doc_hash)
                unique_docs.append(doc)
        
        logger.info(f"Deduplication: {len(documents)} -> {len(unique_docs)} documents")
        return unique_docs
    
    def _compute_hash(self, text: str) -> str:
        normalized = text.lower().strip()
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def reset(self):
        self.seen_hashes.clear()
