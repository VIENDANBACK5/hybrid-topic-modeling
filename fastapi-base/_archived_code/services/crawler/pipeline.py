from typing import Dict, List
from .fetchers import WebFetcher, RSSFetcher, FileFetcher, APIFetcher
from app.services.etl.text_cleaner import TextCleaner
from app.services.etl.dedupe import Deduplicator
import logging

logger = logging.getLogger(__name__)


class CrawlerPipeline:
    def __init__(self):
        self.fetchers = {
            'web': WebFetcher(),
            'rss': RSSFetcher(),
            'file': FileFetcher(),
            'api': APIFetcher()
        }
        self.cleaner = TextCleaner()
        self.deduper = Deduplicator()
    
    async def run(
        self,
        source_type: str,
        source: str,
        clean: bool = True,
        dedupe: bool = True,
        **kwargs
    ) -> Dict:
        fetcher = self.fetchers.get(source_type)
        if not fetcher:
            raise ValueError(f"Unsupported source type: {source_type}")
        
        logger.info(f"Fetching from {source_type}: {source}")
        raw_docs = await fetcher.fetch(source, **kwargs)
        
        if not raw_docs:
            return {'status': 'no_data', 'processed': 0, 'documents': []}
        
        logger.info(f"Fetched {len(raw_docs)} documents")
        
        if clean:
            logger.info("Cleaning documents...")
            for doc in raw_docs:
                doc['cleaned_content'] = self.cleaner.clean(doc['raw_content'])
                doc['content'] = doc['cleaned_content']
        else:
            for doc in raw_docs:
                doc['content'] = doc['raw_content']
        
        if dedupe:
            logger.info("Deduplicating...")
            self.deduper.reset()
            raw_docs = self.deduper.deduplicate(raw_docs)
        
        logger.info(f"Pipeline complete: {len(raw_docs)} documents")
        
        return {
            'status': 'success',
            'processed': len(raw_docs),
            'documents': raw_docs
        }
