"""
LLM Content Enricher - Enrich crawled content with LLM-powered metadata
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class LLMContentEnricher:
    """
    Enrich crawled content with LLM-generated metadata
    
    Features:
    - Auto-categorization
    - Keyword/tag extraction
    - Summarization
    - Quality scoring
    - Entity extraction
    """
    
    def __init__(self, topicgpt_service=None):
        """
        Initialize LLM Content Enricher
        
        Args:
            topicgpt_service: TopicGPT service instance (optional, will create if needed)
        """
        if topicgpt_service:
            self.topicgpt = topicgpt_service
        else:
            from app.services.topic.topicgpt_service import get_topicgpt_service
            self.topicgpt = get_topicgpt_service()
        
        self.enabled = self.topicgpt.is_available()
        
        if self.enabled:
            logger.info("✅ LLM Content Enricher enabled")
        else:
            logger.warning("⚠️ LLM Content Enricher disabled (no API key)")
    
    def should_enrich(self, document: Dict, min_length: int = 500) -> bool:
        """
        Decide if document should be enriched with LLM
        
        Args:
            document: Document dict
            min_length: Minimum content length
        
        Returns:
            True if should enrich
        """
        if not self.enabled:
            return False
        
        # Check content length
        content = document.get('content') or document.get('cleaned_content', '')
        if len(content) < min_length:
            return False
        
        # Already enriched?
        if document.get('llm_enriched'):
            return False
        
        return True
    
    def enrich_document(
        self,
        document: Dict,
        features: List[str] = None,
        max_content_chars: int = 2000
    ) -> Dict:
        """
        Enrich a single document with LLM features
        
        Args:
            document: Document to enrich
            features: List of features to extract (None = all)
                     Options: 'category', 'summary', 'keywords', 'tags', 'quality'
            max_content_chars: Max characters to analyze
        
        Returns:
            Enriched document
        """
        if not self.should_enrich(document):
            return document
        
        content = document.get('content') or document.get('cleaned_content', '')
        if not content:
            return document
        
        # Default: all features
        if features is None:
            features = ['category', 'summary', 'keywords', 'quality']
        
        enriched = document.copy()
        enriched['llm_enriched'] = True
        enriched['llm_enriched_at'] = datetime.now().isoformat()
        
        try:
            # Feature: Categorization
            if 'category' in features:
                category_result = self.topicgpt.categorize_content(
                    text=content[:1000],
                    max_chars=1000
                )
                enriched['llm_category'] = category_result.get('category')
                enriched['llm_category_confidence'] = category_result.get('confidence', 0.0)
                logger.info(f"Categorized: {category_result.get('category')} "
                           f"(confidence: {category_result.get('confidence', 0):.2f})")
            
            # Feature: Summary
            if 'summary' in features:
                summary = self.topicgpt.summarize_content(
                    text=content,
                    max_length=150,
                    max_input_chars=max_content_chars
                )
                if summary:
                    enriched['llm_summary'] = summary
                    logger.info(f"Generated summary: {len(summary)} chars")
            
            # Feature: Keywords & Tags
            if 'keywords' in features or 'tags' in features:
                extraction = self.topicgpt.extract_keywords_and_tags(
                    text=content,
                    max_keywords=10,
                    max_chars=1500
                )
                if 'keywords' in features:
                    enriched['llm_keywords'] = extraction.get('keywords', [])
                if 'tags' in features:
                    enriched['llm_tags'] = extraction.get('tags', [])
                logger.info(f"Extracted {len(extraction.get('keywords', []))} keywords, "
                           f"{len(extraction.get('tags', []))} tags")
            
            # Feature: Quality Score
            if 'quality' in features:
                quality_score = self._assess_quality(content)
                enriched['llm_quality_score'] = quality_score
                enriched['is_high_quality'] = quality_score >= 0.7
                logger.info(f"Quality score: {quality_score:.2f}")
        
        except Exception as e:
            logger.error(f"Error enriching document: {e}")
            enriched['llm_error'] = str(e)
        
        return enriched
    
    def enrich_batch(
        self,
        documents: List[Dict],
        features: List[str] = None,
        selective: bool = True
    ) -> List[Dict]:
        """
        Enrich multiple documents (with smart selection)
        
        Args:
            documents: List of documents
            features: Features to extract
            selective: Only enrich high-value documents (save cost)
        
        Returns:
            List of enriched documents
        """
        if not self.enabled:
            logger.warning("LLM enrichment disabled")
            return documents
        
        enriched_docs = []
        enriched_count = 0
        
        for doc in documents:
            # Smart selection: only enrich valuable content
            if selective and not self._is_high_value(doc):
                enriched_docs.append(doc)
                continue
            
            if self.should_enrich(doc):
                enriched = self.enrich_document(doc, features=features)
                enriched_docs.append(enriched)
                enriched_count += 1
            else:
                enriched_docs.append(doc)
        
        logger.info(f"Enriched {enriched_count}/{len(documents)} documents")
        return enriched_docs
    
    def _is_high_value(self, document: Dict) -> bool:
        """
        Determine if document is high-value (worth LLM cost)
        
        Criteria:
        - Long content (>1000 chars)
        - From trusted domains
        - Has many images/videos
        - Recent (published recently)
        """
        content = document.get('content') or document.get('cleaned_content', '')
        
        # Long content
        if len(content) > 2000:
            return True
        
        # Trusted domains (customize this list)
        trusted_domains = [
            'vnexpress.net', 'dantri.com.vn', 'thanhnien.vn',
            'tuoitre.vn', 'baohungyen.vn', 'baomoi.com'
        ]
        url = document.get('metadata', {}).get('url', '')
        if any(domain in url for domain in trusted_domains):
            return True
        
        # Has media
        metadata = document.get('metadata', {})
        has_images = metadata.get('has_images', False)
        has_videos = metadata.get('has_videos', False)
        if has_images or has_videos:
            return True
        
        # Recent content (if published_at available)
        published = document.get('metadata', {}).get('published_at')
        if published:
            # Consider as high-value if recent
            try:
                from datetime import datetime, timedelta
                pub_date = datetime.fromisoformat(published.replace('Z', '+00:00'))
                if datetime.now() - pub_date < timedelta(days=7):
                    return True
            except:
                pass
        
        return False
    
    def _assess_quality(self, content: str) -> float:
        """
        Assess content quality (simple heuristics)
        
        Returns:
            Quality score (0.0-1.0)
        """
        if not content:
            return 0.0
        
        score = 0.5  # Base score
        
        # Length factor
        length = len(content)
        if length > 1000:
            score += 0.1
        if length > 2000:
            score += 0.1
        
        # Has proper structure (paragraphs)
        paragraphs = content.split('\n\n')
        if len(paragraphs) >= 3:
            score += 0.1
        
        # Has Vietnamese characters
        vietnamese_chars = ['ă', 'â', 'ê', 'ô', 'ơ', 'ư', 'đ', 'á', 'à', 'ả', 'ã', 'ạ']
        if any(char in content.lower() for char in vietnamese_chars):
            score += 0.1
        
        # Not too short sentences (not a list)
        sentences = content.split('.')
        avg_sentence_len = sum(len(s) for s in sentences) / len(sentences) if sentences else 0
        if avg_sentence_len > 50:
            score += 0.1
        
        return min(1.0, score)
    
    def enrich_metadata_only(self, document: Dict) -> Dict:
        """
        Quick enrichment - only metadata, no heavy processing
        
        Args:
            document: Document to enrich
        
        Returns:
            Document with enriched metadata
        """
        if not self.enabled or not self.should_enrich(document, min_length=300):
            return document
        
        content = document.get('content') or document.get('cleaned_content', '')
        enriched = document.copy()
        
        try:
            # Quick categorization only
            category_result = self.topicgpt.categorize_content(
                text=content[:500],
                max_chars=500
            )
            enriched['llm_category'] = category_result.get('category')
            enriched['llm_category_confidence'] = category_result.get('confidence', 0.0)
            enriched['llm_enriched'] = True
            enriched['llm_enriched_type'] = 'metadata_only'
            
            logger.info(f"Quick enrichment: {category_result.get('category')}")
        
        except Exception as e:
            logger.error(f"Error in quick enrichment: {e}")
        
        return enriched
    
    def get_stats(self) -> Dict:
        """Get enrichment statistics"""
        return {
            "enabled": self.enabled,
            "service": "TopicGPT",
            "features": [
                "categorization",
                "summarization",
                "keyword_extraction",
                "quality_assessment"
            ]
        }


# Global instance
_enricher = None

def get_content_enricher() -> LLMContentEnricher:
    """Get or create global content enricher"""
    global _enricher
    if _enricher is None:
        _enricher = LLMContentEnricher()
    return _enricher
