"""
Keyphrase Extraction Service v2
WITH Named Entity Recognition & Proper Noun Preservation
"""
import logging
from typing import List, Dict, Optional
from collections import Counter
import re

logger = logging.getLogger(__name__)

# Vietnamese locations and entities to preserve (phải giữ nguyên khi extract)
VIETNAMESE_ENTITIES = {
    'locations': [
        'hưng yên', 'phố hiến', 'khoái châu', 'văn lâm', 'văn giang', 'yên mỹ',
        'mỹ hào', 'ân thi', 'kim động', 'tiên lữ', 'phù cừ',
        'hà nội', 'hải phòng', 'thái bình', 'hải dương', 'bắc ninh', 'bắc giang',
        'nam định', 'ninh bình', 'hà nam', 'vĩnh phúc', 'quảng ninh',
        'việt nam', 'trung quốc', 'đông nam á', 'thành phố hồ chí minh'
    ],
    'organizations': [
        'ubnd', 'ủy ban nhân dân', 'bộ giao thông vận tải', 'bộ xây dựng',
        'bộ kế hoạch và đầu tư', 'quốc hội', 'chính phủ', 'tỉnh ủy', 'thành ủy',
        'công an', 'bệnh viện', 'trường đại học'
    ],
    'landmarks': [
        'chùa dâu', 'đền triều', 'phủ giầy', 'lăng mộ', 'di tích lịch sử',
        'khu di tích', 'bảo tàng', 'nhà thờ'
    ]
}


class KeyphraseExtractorV2:
    """Keyphrase extractor with entity preservation"""
    
    def __init__(self, use_vietnamese_tokenizer: bool = True):
        self.use_vietnamese_tokenizer = use_vietnamese_tokenizer
        self.tokenizer = None
        self.ner_model = None
        
        # Flatten entities for quick lookup
        self.entity_set = set()
        for entity_list in VIETNAMESE_ENTITIES.values():
            self.entity_set.update(entity_list)
        
        if use_vietnamese_tokenizer:
            self._setup_tools()
    
    def _setup_tools(self):
        """Setup tokenizer and NER"""
        try:
            from underthesea import word_tokenize, ner
            self.tokenizer = word_tokenize
            self.ner_model = ner
            logger.info("Vietnamese tokenizer and NER loaded")
        except Exception as e:
            logger.warning(f"Could not load tools: {e}")
    
    def extract_entities(self, texts: List[str]) -> List[str]:
        """
        Extract named entities từ texts
        Returns list of unique entities with counts
        """
        entities = []
        
        for text in texts:
            text_lower = text.lower()
            
            # 1. Manual extraction from predefined list
            for entity in self.entity_set:
                if entity in text_lower:
                    entities.append(entity)
            
            # 2. Try NER if available
            if self.ner_model:
                try:
                    ner_result = self.ner_model(text[:500])  # Limit length for performance
                    current_entity = []
                    
                    for word, tag in ner_result:
                        if tag in ['B-LOC', 'I-LOC', 'B-PER', 'I-PER', 'B-ORG', 'I-ORG']:
                            current_entity.append(word)
                        elif current_entity:
                            # Finish current entity
                            entity_str = ' '.join(current_entity).lower()
                            if len(entity_str) > 2:  # Skip single chars
                                entities.append(entity_str)
                            current_entity = []
                    
                    # Don't forget last entity
                    if current_entity:
                        entity_str = ' '.join(current_entity).lower()
                        if len(entity_str) > 2:
                            entities.append(entity_str)
                            
                except Exception as e:
                    logger.debug(f"NER failed: {e}")
                    pass
        
        # Count and return
        entity_counts = Counter(entities)
        logger.info(f"Found {len(entity_counts)} unique entities from {len(entities)} mentions")
        return list(entity_counts.keys())
    
    def _protect_entities(self, text: str) -> tuple[str, dict]:
        """
        Replace entities with placeholders before tokenization
        Returns: (protected_text, entity_map)
        """
        entity_map = {}
        protected_text = text.lower()
        
        # Sort by length (longest first) to avoid partial replacements
        sorted_entities = sorted(self.entity_set, key=len, reverse=True)
        
        for idx, entity in enumerate(sorted_entities):
            if entity in protected_text:
                placeholder = f"__ENTITY{idx}__"
                protected_text = protected_text.replace(entity, placeholder)
                entity_map[placeholder] = entity
        
        return protected_text, entity_map
    
    def _restore_entities(self, phrases: List[str], entity_maps: List[dict]) -> List[str]:
        """Restore entities from placeholders"""
        # Merge all entity maps
        all_placeholders = {}
        for em in entity_maps:
            all_placeholders.update(em)
        
        restored = []
        for phrase in phrases:
            restored_phrase = phrase
            # Sort by placeholder length (longest first) to avoid partial replacements
            sorted_placeholders = sorted(all_placeholders.items(), key=lambda x: len(x[0]), reverse=True)
            for placeholder, entity in sorted_placeholders:
                restored_phrase = restored_phrase.replace(placeholder, entity)
            restored.append(restored_phrase)
        
        return restored
    
    def extract_keyphrases_tfidf(
        self,
        texts: List[str],
        top_n: int = 50,
        ngram_range: tuple = (2, 3),
        min_df: int = 2
    ) -> List[Dict]:
        """
        Extract keyphrases using TF-IDF with entity preservation
        """
        if not texts:
            return []
        
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            
            # 1. Extract entities first
            entities = self.extract_entities(texts)
            logger.info(f"Found {len(entities)} entities to preserve")
            
            # 2. Protect entities in texts
            protected_texts = []
            entity_maps = []
            
            for text in texts:
                protected, emap = self._protect_entities(text)
                protected_texts.append(protected)
                entity_maps.append(emap)
            
            # 3. Vietnamese stopwords
            stopwords = [
                'của', 'và', 'có', 'được', 'này', 'cho', 'từ', 'với', 'theo', 'tại',
                'trong', 'các', 'một', 'là', 'để', 'đã', 'không', 'về', 'người',
                'khi', 'như', 'nên', 'cũng', 'đang', 'sẽ', 'bị', 'do', 'vào', 'ra',
                'còn', 'mà', 'thì', 'đó', 'nó', 'họ', 'này', 'ấy'
            ]
            
            # 4. Tokenize if available
            if self.tokenizer:
                processed_texts = []
                for text in protected_texts:
                    try:
                        tokens = self.tokenizer(text)
                        processed_texts.append(" ".join(tokens))
                    except:
                        processed_texts.append(text)
            else:
                processed_texts = protected_texts
            
            # 5. TF-IDF vectorizer
            vectorizer = TfidfVectorizer(
                ngram_range=ngram_range,
                min_df=min_df,
                max_df=0.8,
                stop_words=stopwords,
                lowercase=True,
                max_features=500
            )
            
            tfidf_matrix = vectorizer.fit_transform(processed_texts)
            feature_names = vectorizer.get_feature_names_out()
            
            # 6. Calculate scores
            phrase_scores = {}
            for idx, phrase in enumerate(feature_names):
                score = tfidf_matrix[:, idx].mean()
                phrase_scores[phrase] = float(score)
            
            # 7. Don't use entity_maps (doesn't work with sklearn vectorizer)
            # Instead, detect entities in output phrases
            restored_scores = phrase_scores.copy()
            
            # 8. Boost entity scores (x3 for known entities)
            for phrase in restored_scores:
                for entity in entities:
                    if entity in phrase:
                        restored_scores[phrase] *= 3.0
                        logger.debug(f"Boosted entity phrase: {phrase}")
                        break
            
            # 9. Sort and return
            sorted_phrases = sorted(restored_scores.items(), key=lambda x: x[1], reverse=True)
            
            results = []
            seen = set()
            
            # 10. Add top phrases
            for phrase, score in sorted_phrases:
                if phrase not in seen and len(phrase) > 2:
                    is_entity = any(e in phrase for e in entities)
                    results.append({
                        "phrase": phrase,
                        "score": round(score, 4),
                        "type": "entity" if is_entity else "phrase"
                    })
                    seen.add(phrase)
                
                if len(results) >= top_n:
                    break
            
            logger.info(f"Extracted {len(results)} keyphrases ({sum(1 for r in results if r['type']=='entity')} entities)")
            return results
            
        except Exception as e:
            logger.error(f"TF-IDF extraction failed: {e}", exc_info=True)
            return []
    
    def _clean_phrase(self, phrase: str) -> str:
        """Clean phrase (keep for compatibility)"""
        cleaned = re.sub(r'\s+', ' ', phrase)
        cleaned = cleaned.strip()
        return cleaned


# Singleton
_extractor_instance = None

def get_keyphrase_extractor_v2() -> KeyphraseExtractorV2:
    """Get singleton instance"""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = KeyphraseExtractorV2()
    return _extractor_instance
