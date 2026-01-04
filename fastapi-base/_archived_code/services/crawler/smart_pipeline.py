"""
Smart Crawler Pipeline - Enhanced crawler with LLM integration
Combines traditional crawling with intelligent LLM-powered features
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime

from .fetchers import WebFetcher, RSSFetcher, FileFetcher, APIFetcher
from app.services.etl.text_cleaner import TextCleaner
from app.services.etl.hybrid_dedupe import get_hybrid_deduplicator
from .llm_content_enricher import get_content_enricher
from .cost_optimizer import get_cost_optimizer

logger = logging.getLogger(__name__)


class SmartCrawlerPipeline:
    """
    Smart Crawler Pipeline với LLM Integration
    
    Features:
    - Traditional crawling (fast, free)
    - LLM content enrichment (selective, costly)
    - Hybrid deduplication (hash + semantic)
    - Cost-aware operations
    - Smart filtering and categorization
    """
    
    def __init__(
        self,
        enable_llm: bool = True,
        llm_features: List[str] = None,
        cost_aware: bool = True
    ):
        """
        Initialize Smart Crawler Pipeline
        
        Args:
            enable_llm: Enable LLM features
            llm_features: List of LLM features to enable
                         Options: 'categorize', 'summarize', 'keywords', 'semantic_dedupe'
            cost_aware: Enable cost optimization
        """
        # Traditional components (always enabled)
        self.fetchers = {
            'web': WebFetcher(),
            'rss': RSSFetcher(),
            'file': FileFetcher(),
            'api': APIFetcher()
        }
        self.cleaner = TextCleaner()
        
        # LLM components (optional)
        self.enable_llm = enable_llm
        self.llm_features = llm_features or []
        self.cost_aware = cost_aware
        
        if enable_llm:
            self.enricher = get_content_enricher()
            self.hybrid_deduper = get_hybrid_deduplicator()
            
            if cost_aware:
                self.cost_optimizer = get_cost_optimizer()
            else:
                self.cost_optimizer = None
            
            logger.info(f"✅ Smart Crawler Pipeline initialized with LLM "
                       f"(features: {', '.join(llm_features) if llm_features else 'all'})")
        else:
            self.enricher = None
            self.hybrid_deduper = None
            self.cost_optimizer = None
            logger.info("Smart Crawler Pipeline initialized (LLM disabled)")
    
    async def run(
        self,
        source_type: str,
        source: str,
        clean: bool = True,
        dedupe: bool = True,
        enrich: bool = None,
        semantic_dedupe: bool = None,
        **kwargs
    ) -> Dict:
        """
        Run smart crawler pipeline
        
        Args:
            source_type: Type of source ('web', 'rss', 'file', 'api')
            source: Source URL/path
            clean: Clean text
            dedupe: Deduplicate documents
            enrich: Enable LLM enrichment (None = auto based on cost)
            semantic_dedupe: Enable semantic deduplication (None = auto)
            **kwargs: Additional crawler parameters
        
        Returns:
            Dict with crawled and processed documents
        """
        logger.info(f"🚀 Smart crawl starting: {source_type}:{source}")
        
        # Stage 1: Fetch documents
        fetcher = self.fetchers.get(source_type)
        if not fetcher:
            raise ValueError(f"Unsupported source type: {source_type}")
        
        raw_docs = await fetcher.fetch(source, **kwargs)
        
        if not raw_docs:
            return {
                'status': 'no_data',
                'processed': 0,
                'documents': [],
                'pipeline_info': {'stage': 'fetch', 'result': 'empty'}
            }
        
        logger.info(f"✅ Fetched {len(raw_docs)} documents")
        
        # Stage 2: Clean text (traditional)
        if clean:
            logger.info("🧹 Cleaning documents...")
            for doc in raw_docs:
                doc['cleaned_content'] = self.cleaner.clean(doc.get('raw_content', ''))
                doc['content'] = doc['cleaned_content']
            logger.info(f"✅ Cleaned {len(raw_docs)} documents")
        else:
            for doc in raw_docs:
                doc['content'] = doc.get('raw_content', '')
        
        # Stage 3: Deduplication (hybrid: hash + semantic)
        if dedupe:
            logger.info("🔍 Deduplicating...")
            
            # Decide on semantic dedupe
            if semantic_dedupe is None:
                # Auto-decide based on cost and document count
                if self.enable_llm and self.cost_aware:
                    decision = self.cost_optimizer.should_enable_feature(
                        "semantic_deduplication",
                        batch_size=min(len(raw_docs), 50)
                    )
                    semantic_dedupe = decision.get('enabled', False)
                    logger.info(f"Semantic dedupe: {semantic_dedupe} ({decision.get('reason')})")
                else:
                    semantic_dedupe = self.enable_llm
            
            # Use hybrid deduplicator if available
            if self.enable_llm and self.hybrid_deduper:
                raw_docs = self.hybrid_deduper.deduplicate(
                    raw_docs,
                    use_semantic=semantic_dedupe
                )
            else:
                # Fallback to basic hash dedupe
                from app.services.etl.dedupe import Deduplicator
                basic_deduper = Deduplicator()
                basic_deduper.reset()
                raw_docs = basic_deduper.deduplicate(raw_docs)
            
            logger.info(f"✅ After dedupe: {len(raw_docs)} unique documents")
        
        # Stage 4: LLM Enrichment (selective, cost-aware)
        enriched_count = 0
        if enrich is None:
            # Auto-decide on enrichment
            enrich = self.enable_llm and len(raw_docs) > 0
        
        if enrich and self.enable_llm and self.enricher:
            logger.info("🤖 LLM enrichment starting...")
            
            # Determine which features to enable
            features_to_use = self._decide_features(raw_docs)
            
            if features_to_use:
                # Enrich documents (selective based on value)
                for doc in raw_docs:
                    if self._should_enrich_doc(doc):
                        enriched_doc = self.enricher.enrich_document(
                            doc,
                            features=features_to_use,
                            max_content_chars=2000
                        )
                        
                        if enriched_doc.get('llm_enriched'):
                            enriched_count += 1
                            
                            # Record usage for cost tracking
                            if self.cost_optimizer:
                                for feature in features_to_use:
                                    self.cost_optimizer.record_usage(
                                        operation=self._feature_to_operation(feature)
                                    )
                
                logger.info(f"✅ Enriched {enriched_count}/{len(raw_docs)} documents")
            else:
                logger.info("⏭️  Skipping enrichment (budget or feature constraints)")
        
        # Stage 5: Post-processing and metadata
        pipeline_info = {
            'stages': {
                'fetch': {'count': len(raw_docs)},
                'clean': {'enabled': clean},
                'dedupe': {
                    'enabled': dedupe,
                    'semantic': semantic_dedupe
                },
                'enrich': {
                    'enabled': enrich and enriched_count > 0,
                    'count': enriched_count
                }
            },
            'llm_enabled': self.enable_llm,
            'cost_tracking': self.cost_optimizer.get_usage_report() if self.cost_optimizer else None
        }
        
        logger.info(f"🎉 Smart crawl complete: {len(raw_docs)} documents")
        
        return {
            'status': 'success',
            'processed': len(raw_docs),
            'documents': raw_docs,
            'pipeline_info': pipeline_info
        }
    
    def _decide_features(self, documents: List[Dict]) -> List[str]:
        """
        Decide which LLM features to enable based on cost and value
        
        Args:
            documents: List of documents
        
        Returns:
            List of features to enable
        """
        if not self.enable_llm:
            return []
        
        # If specific features requested, use those
        if self.llm_features:
            enabled = []
            for feature in self.llm_features:
                if self.cost_aware and self.cost_optimizer:
                    decision = self.cost_optimizer.should_enable_feature(
                        feature,
                        batch_size=len([d for d in documents if self._should_enrich_doc(d)])
                    )
                    if decision.get('enabled'):
                        enabled.append(feature)
                else:
                    enabled.append(feature)
            return enabled
        
        # Auto-decide based on budget and doc count
        features = []
        
        # Categorization (cheap, high value)
        if not self.cost_aware or self.cost_optimizer.can_afford("categorize", len(documents)):
            features.append('category')
        
        # Keywords (medium cost, good value)
        if not self.cost_aware or self.cost_optimizer.can_afford("extract_keywords", len(documents) // 2):
            features.append('keywords')
        
        # Summary (expensive, selective)
        long_docs = [d for d in documents if len(d.get('content', '')) > 1500]
        if len(long_docs) > 0:
            if not self.cost_aware or self.cost_optimizer.can_afford("summarize", len(long_docs)):
                features.append('summary')
        
        return features
    
    def _should_enrich_doc(self, document: Dict) -> bool:
        """Decide if document should be enriched"""
        if not self.enable_llm or not self.enricher:
            return False
        
        # Check with enricher
        if not self.enricher.should_enrich(document):
            return False
        
        # Check with cost optimizer
        if self.cost_aware and self.cost_optimizer:
            return self.cost_optimizer.should_use_llm_for_doc(
                document,
                operation="categorize",  # Use cheapest operation for decision
                priority="normal"
            )
        
        return True
    
    def _feature_to_operation(self, feature: str) -> str:
        """Map feature name to operation for cost tracking"""
        mapping = {
            'category': 'categorize',
            'summary': 'summarize',
            'keywords': 'extract_keywords',
            'tags': 'extract_keywords',
            'quality': 'categorize'  # Similar cost
        }
        return mapping.get(feature, feature)
    
    def get_pipeline_stats(self) -> Dict:
        """Get pipeline statistics"""
        stats = {
            "llm_enabled": self.enable_llm,
            "llm_features": self.llm_features,
            "cost_aware": self.cost_aware,
            "fetchers": list(self.fetchers.keys())
        }
        
        if self.enable_llm:
            stats["enricher"] = self.enricher.get_stats() if self.enricher else None
            stats["deduplicator"] = self.hybrid_deduper.get_stats() if self.hybrid_deduper else None
            stats["cost_optimizer"] = self.cost_optimizer.get_usage_report() if self.cost_optimizer else None
        
        return stats
    
    def configure_llm_features(self, features: List[str]):
        """
        Dynamically configure LLM features
        
        Args:
            features: List of features to enable
        """
        self.llm_features = features
        logger.info(f"LLM features configured: {', '.join(features)}")
    
    def set_daily_budget(self, budget: float):
        """
        Set daily budget for LLM operations
        
        Args:
            budget: Budget in USD
        """
        if self.cost_optimizer:
            self.cost_optimizer.daily_budget = budget
            logger.info(f"Daily budget set to ${budget}")
        else:
            logger.warning("Cost optimizer not enabled")


# Global instance
_smart_pipeline = None

def get_smart_crawler_pipeline(**kwargs) -> SmartCrawlerPipeline:
    """Get or create global smart crawler pipeline"""
    global _smart_pipeline
    if _smart_pipeline is None:
        _smart_pipeline = SmartCrawlerPipeline(**kwargs)
    return _smart_pipeline
