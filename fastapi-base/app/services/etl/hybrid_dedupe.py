"""
Hybrid Deduplicator - Combine hash-based + semantic deduplication
"""
import hashlib
import logging
from typing import List, Dict, Set, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class HybridDeduplicator:
    """
    Hybrid Deduplication Strategy:
    1. Fast hash-based deduplication (exact matches)
    2. Semantic LLM-based deduplication (paraphrases/similar content)
    
    Optimized for cost:
    - Hash dedupe: Free, instant
    - Semantic dedupe: Expensive, only for remaining duplicates
    """
    
    def __init__(
        self,
        hash_threshold: float = 0.9,
        semantic_threshold: float = 0.85,
        topicgpt_service=None,
        enable_semantic: bool = True
    ):
        """
        Initialize Hybrid Deduplicator
        
        Args:
            hash_threshold: Similarity threshold for hash matching
            semantic_threshold: Similarity threshold for semantic matching
            topicgpt_service: TopicGPT service instance
            enable_semantic: Enable semantic deduplication (costly)
        """
        self.hash_threshold = hash_threshold
        self.semantic_threshold = semantic_threshold
        self.enable_semantic = enable_semantic
        
        # Hash storage
        self.seen_hashes: Set[str] = set()
        self.url_hashes: Dict[str, str] = {}
        self.content_hashes: Dict[str, str] = {}
        
        # Initialize TopicGPT service for semantic matching
        if enable_semantic:
            if topicgpt_service:
                self.topicgpt = topicgpt_service
            else:
                from app.services.topic.topicgpt_service import get_topicgpt_service
                self.topicgpt = get_topicgpt_service()
            
            if not self.topicgpt.is_available():
                logger.warning("TopicGPT not available - semantic dedupe disabled")
                self.enable_semantic = False
        
        logger.info(f"Hybrid Deduplicator initialized "
                   f"(semantic: {'enabled' if self.enable_semantic else 'disabled'})")
    
    def _compute_hash(self, text: str, method: str = "md5") -> str:
        """Compute hash of text"""
        normalized = text.lower().strip()
        
        if method == "md5":
            return hashlib.md5(normalized.encode('utf-8')).hexdigest()
        elif method == "sha256":
            return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
        else:
            return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def _compute_simhash(self, text: str, num_bits: int = 64) -> int:
        """
        Compute SimHash for near-duplicate detection
        Simple implementation for fuzzy matching
        """
        # Tokenize
        tokens = text.lower().split()
        
        # Create bit vector
        v = [0] * num_bits
        
        for token in tokens:
            # Hash token
            h = hash(token)
            
            # Update bit vector
            for i in range(num_bits):
                if h & (1 << i):
                    v[i] += 1
                else:
                    v[i] -= 1
        
        # Generate final hash
        simhash = 0
        for i in range(num_bits):
            if v[i] > 0:
                simhash |= (1 << i)
        
        return simhash
    
    def _hamming_distance(self, hash1: int, hash2: int) -> int:
        """Calculate Hamming distance between two hashes"""
        x = hash1 ^ hash2
        distance = 0
        while x:
            distance += 1
            x &= x - 1
        return distance
    
    def deduplicate(
        self,
        documents: List[Dict],
        use_url: bool = True,
        use_content: bool = True,
        use_semantic: bool = None
    ) -> List[Dict]:
        """
        Deduplicate documents using hybrid approach
        
        Args:
            documents: List of documents
            use_url: Use URL for deduplication
            use_content: Use content for deduplication
            use_semantic: Enable semantic deduplication (None = auto)
        
        Returns:
            List of unique documents
        """
        if not documents:
            return []
        
        logger.info(f"Deduplicating {len(documents)} documents...")
        
        # Stage 1: Fast hash-based deduplication
        unique_docs = self._hash_deduplicate(
            documents,
            use_url=use_url,
            use_content=use_content
        )
        
        logger.info(f"After hash dedupe: {len(unique_docs)} documents")
        
        # Stage 2: Semantic deduplication (if enabled and needed)
        if use_semantic is None:
            use_semantic = self.enable_semantic
        
        if use_semantic and len(unique_docs) > 1:
            unique_docs = self._semantic_deduplicate(unique_docs)
            logger.info(f"After semantic dedupe: {len(unique_docs)} documents")
        
        logger.info(f"Final: {len(unique_docs)}/{len(documents)} unique documents")
        return unique_docs
    
    def _hash_deduplicate(
        self,
        documents: List[Dict],
        use_url: bool = True,
        use_content: bool = True
    ) -> List[Dict]:
        """
        Stage 1: Fast hash-based deduplication
        - Exact URL matches
        - Exact content matches
        - Near-duplicate detection with SimHash
        """
        unique_docs = []
        seen_exact = set()
        simhashes = {}
        
        for doc in documents:
            # Extract URL and content
            url = doc.get('metadata', {}).get('url', '')
            content = doc.get('cleaned_content') or doc.get('content', '')
            
            # Skip if no content
            if not content and not url:
                continue
            
            # Check exact URL match
            if use_url and url:
                url_hash = self._compute_hash(url)
                if url_hash in seen_exact:
                    logger.debug(f"Duplicate URL: {url[:50]}")
                    continue
                seen_exact.add(url_hash)
            
            # Check exact content match
            if use_content and content:
                content_hash = self._compute_hash(content)
                if content_hash in seen_exact:
                    logger.debug(f"Duplicate content: {content[:50]}")
                    continue
                seen_exact.add(content_hash)
                
                # Compute SimHash for near-duplicate detection
                simhash = self._compute_simhash(content)
                
                # Check against existing simhashes
                is_near_duplicate = False
                for existing_hash, _ in simhashes.items():
                    distance = self._hamming_distance(simhash, existing_hash)
                    # If Hamming distance < 3 bits, consider near-duplicate
                    if distance < 3:
                        is_near_duplicate = True
                        logger.debug(f"Near-duplicate detected (distance: {distance})")
                        break
                
                if is_near_duplicate:
                    continue
                
                simhashes[simhash] = content[:100]
            
            # Add to unique documents
            unique_docs.append(doc)
        
        return unique_docs
    
    def _semantic_deduplicate(
        self,
        documents: List[Dict],
        batch_size: int = 50
    ) -> List[Dict]:
        """
        Stage 2: Semantic deduplication using LLM
        - Detect paraphrased content
        - Group similar articles
        - Keep best from each group
        
        Args:
            documents: Pre-filtered documents from hash dedupe
            batch_size: Max documents to compare (cost control)
        
        Returns:
            Deduplicated documents
        """
        if not self.enable_semantic or not self.topicgpt.is_available():
            logger.warning("Semantic dedupe not available")
            return documents
        
        # Limit batch size to control cost
        if len(documents) > batch_size:
            logger.warning(f"Too many documents ({len(documents)}), limiting to {batch_size}")
            # Keep first batch_size documents (or implement smarter selection)
            documents = documents[:batch_size]
        
        # Group similar documents
        groups = []
        processed = set()
        
        for i, doc1 in enumerate(documents):
            if i in processed:
                continue
            
            # Start new group
            group = [i]
            content1 = doc1.get('cleaned_content') or doc1.get('content', '')
            
            # Compare with remaining documents
            for j in range(i + 1, len(documents)):
                if j in processed:
                    continue
                
                doc2 = documents[j]
                content2 = doc2.get('cleaned_content') or doc2.get('content', '')
                
                # Skip if content too short
                if len(content1) < 200 or len(content2) < 200:
                    continue
                
                # Check semantic similarity
                try:
                    similarity = self.topicgpt.detect_similarity(
                        text1=content1,
                        text2=content2,
                        max_chars=300
                    )
                    
                    if similarity >= self.semantic_threshold:
                        group.append(j)
                        processed.add(j)
                        logger.info(f"Similar docs found (similarity: {similarity:.2f})")
                
                except Exception as e:
                    logger.warning(f"Error checking similarity: {e}")
                    continue
            
            groups.append(group)
            processed.add(i)
        
        # Keep best document from each group
        unique_docs = []
        for group in groups:
            # Select best document (longest content, or first)
            best_idx = max(group, key=lambda idx: len(
                documents[idx].get('cleaned_content') or 
                documents[idx].get('content', '')
            ))
            unique_docs.append(documents[best_idx])
        
        logger.info(f"Semantic dedupe: {len(documents)} -> {len(unique_docs)} documents "
                   f"({len(groups)} groups)")
        
        return unique_docs
    
    def find_duplicates(
        self,
        documents: List[Dict],
        return_groups: bool = True
    ) -> Dict:
        """
        Find duplicate groups without removing them
        
        Args:
            documents: List of documents
            return_groups: Return grouped duplicates
        
        Returns:
            Dict with duplicate information
        """
        # Hash-based duplicates
        hash_groups = defaultdict(list)
        
        for i, doc in enumerate(documents):
            content = doc.get('cleaned_content') or doc.get('content', '')
            if content:
                content_hash = self._compute_hash(content)
                hash_groups[content_hash].append(i)
        
        # Find actual duplicates (groups with >1 document)
        duplicate_groups = {
            h: indices for h, indices in hash_groups.items()
            if len(indices) > 1
        }
        
        total_duplicates = sum(len(group) - 1 for group in duplicate_groups.values())
        
        result = {
            "total_documents": len(documents),
            "duplicate_groups": len(duplicate_groups),
            "total_duplicates": total_duplicates,
            "unique_documents": len(documents) - total_duplicates
        }
        
        if return_groups:
            result["groups"] = [
                {
                    "hash": h[:16],
                    "count": len(indices),
                    "indices": indices,
                    "sample": documents[indices[0]].get('metadata', {}).get('url', '')[:100]
                }
                for h, indices in list(duplicate_groups.items())[:10]  # Limit to 10 groups
            ]
        
        return result
    
    def reset(self):
        """Reset deduplicator state"""
        self.seen_hashes.clear()
        self.url_hashes.clear()
        self.content_hashes.clear()
        logger.info("Deduplicator reset")
    
    def get_stats(self) -> Dict:
        """Get deduplication statistics"""
        return {
            "hash_threshold": self.hash_threshold,
            "semantic_threshold": self.semantic_threshold,
            "semantic_enabled": self.enable_semantic,
            "seen_hashes": len(self.seen_hashes),
            "url_hashes": len(self.url_hashes),
            "content_hashes": len(self.content_hashes)
        }


# Global instance
_deduplicator = None

def get_hybrid_deduplicator() -> HybridDeduplicator:
    """Get or create global hybrid deduplicator"""
    global _deduplicator
    if _deduplicator is None:
        _deduplicator = HybridDeduplicator()
    return _deduplicator
