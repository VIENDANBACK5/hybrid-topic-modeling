"""
Enhanced deduplicator with multiple strategies
"""
import hashlib
from typing import List, Dict, Set, Optional
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)


class Deduplicator:
    """Enhanced deduplicator with multiple strategies"""
    
    def __init__(
        self, 
        strategy: str = 'hash',
        similarity_threshold: float = 0.9,
        use_url: bool = True,
        use_title: bool = True
    ):
        """
        Args:
            strategy: 'hash', 'similarity', or 'hybrid'
            similarity_threshold: For similarity-based dedup (0.0-1.0)
            use_url: Include URL in deduplication
            use_title: Include title in deduplication
        """
        self.strategy = strategy
        self.similarity_threshold = similarity_threshold
        self.use_url = use_url
        self.use_title = use_title
        
        self.seen_hashes: Set[str] = set()
        self.seen_urls: Set[str] = set()
        self.seen_contents: List[str] = []
    
    def deduplicate(self, documents: List[Dict]) -> List[Dict]:
        """
        Deduplicate documents using configured strategy
        
        Args:
            documents: List of document dicts
        
        Returns:
            List of unique documents
        """
        if self.strategy == 'hash':
            return self._deduplicate_by_hash(documents)
        elif self.strategy == 'similarity':
            return self._deduplicate_by_similarity(documents)
        elif self.strategy == 'hybrid':
            return self._deduplicate_hybrid(documents)
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")
    
    def _deduplicate_by_hash(self, documents: List[Dict]) -> List[Dict]:
        """Fast hash-based deduplication"""
        unique_docs = []
        
        for doc in documents:
            # Build dedup key
            key_parts = []
            
            if self.use_url:
                url = doc.get('metadata', {}).get('url', '') or doc.get('url', '')
                if url:
                    key_parts.append(f"url:{url}")
            
            if self.use_title:
                title = doc.get('metadata', {}).get('title', '') or doc.get('title', '')
                if title:
                    key_parts.append(f"title:{title}")
            
            # Always include content
            content = doc.get('cleaned_content') or doc.get('content') or doc.get('raw_content', '')
            key_parts.append(f"content:{content[:1000]}")  # Use first 1000 chars
            
            # Compute hash
            dedupe_key = '|'.join(key_parts)
            doc_hash = self._compute_hash(dedupe_key)
            
            # Check if seen
            if doc_hash not in self.seen_hashes:
                self.seen_hashes.add(doc_hash)
                unique_docs.append(doc)
        
        logger.info(f"Hash dedup: {len(documents)} -> {len(unique_docs)} documents")
        return unique_docs
    
    def _deduplicate_by_similarity(self, documents: List[Dict]) -> List[Dict]:
        """Similarity-based deduplication (slower but more accurate)"""
        unique_docs = []
        
        for doc in documents:
            content = doc.get('cleaned_content') or doc.get('content') or doc.get('raw_content', '')
            
            # Check URL first (fast)
            if self.use_url:
                url = doc.get('metadata', {}).get('url', '') or doc.get('url', '')
                if url and url in self.seen_urls:
                    continue
            
            # Check similarity with existing docs
            is_duplicate = False
            for seen_content in self.seen_contents:
                similarity = self._compute_similarity(content, seen_content)
                if similarity >= self.similarity_threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_docs.append(doc)
                self.seen_contents.append(content)
                
                if self.use_url:
                    url = doc.get('metadata', {}).get('url', '') or doc.get('url', '')
                    if url:
                        self.seen_urls.add(url)
        
        logger.info(f"Similarity dedup: {len(documents)} -> {len(unique_docs)} documents")
        return unique_docs
    
    def _deduplicate_hybrid(self, documents: List[Dict]) -> List[Dict]:
        """Hybrid: hash first, then similarity for edge cases"""
        # Phase 1: Fast hash deduplication
        hash_unique = self._deduplicate_by_hash(documents)
        
        # Phase 2: Similarity check on remaining docs (optional, for high-value content)
        if len(hash_unique) > 100:
            # Skip similarity for large datasets (too slow)
            return hash_unique
        
        # Reset for similarity check
        self.seen_contents = []
        self.seen_urls = set()
        
        return self._deduplicate_by_similarity(hash_unique)
    
    def _compute_hash(self, text: str) -> str:
        """Compute MD5 hash of text"""
        normalized = text.lower().strip()
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def _compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute similarity between two texts using SequenceMatcher
        
        Returns:
            Similarity score (0.0 to 1.0)
        """
        # Normalize
        text1 = text1.lower().strip()[:5000]  # Limit length for performance
        text2 = text2.lower().strip()[:5000]
        
        # Quick check: if lengths differ too much, likely not duplicates
        len1, len2 = len(text1), len(text2)
        if len1 == 0 or len2 == 0:
            return 0.0
        
        ratio = max(len1, len2) / min(len1, len2)
        if ratio > 2.0:  # More than 2x length difference
            return 0.0
        
        # Compute similarity
        return SequenceMatcher(None, text1, text2).ratio()
    
    def reset(self):
        """Reset all seen data"""
        self.seen_hashes.clear()
        self.seen_urls.clear()
        self.seen_contents.clear()
    
    def get_stats(self) -> Dict:
        """Get deduplication statistics"""
        return {
            'strategy': self.strategy,
            'unique_hashes': len(self.seen_hashes),
            'unique_urls': len(self.seen_urls),
            'unique_contents': len(self.seen_contents),
            'similarity_threshold': self.similarity_threshold if self.strategy in ['similarity', 'hybrid'] else None
        }
