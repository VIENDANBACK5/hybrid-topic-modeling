"""
Keyphrase Extraction Service
Extract meaningful phrases (n-grams) instead of single words for WordCloud
WITH Named Entity Recognition for proper nouns
"""
import logging
from typing import List, Dict, Optional
from collections import Counter
import re

logger = logging.getLogger(__name__)

# Vietnamese locations and entities to preserve
VIETNAMESE_ENTITIES = {
    'locations': [
        'hưng yên', 'phố hiến', 'khoái châu', 'văn lâm', 'văn giang', 'yên mỹ',
        'mỹ hào', 'ân thi', 'kim động', 'tiên lữ', 'phù cừ',
        'hà nội', 'hải phòng', 'thái bình', 'hải dương', 'bắc ninh', 'bắc giang',
        'nam định', 'ninh bình', 'hà nam', 'vĩnh phúc', 'quảng ninh',
        'việt nam', 'trung quốc', 'đông nam á'
    ],
    'organizations': [
        'ubnd', 'ủy ban nhân dân', 'bộ giao thông vận tải', 'bộ xây dựng',
        'bộ kế hoạch và đầu tư', 'quốc hội', 'chính phủ', 'tỉnh ủy', 'thành ủy',
        'công an', 'bệnh viện', 'trường đại học', 'trường trung học'
    ],
    'landmarks': [
        'chùa dâu', 'đền triều', 'phủ giầy', 'lăng mộ', 'di tích lịch sử',
        'khu di tích', 'bảo tàng', 'nhà thờ', 'đình làng'
    ]
}


class KeyphraseExtractor:
    def __init__(self, use_vietnamese_tokenizer: bool = True):
        self.use_vietnamese_tokenizer = use_vietnamese_tokenizer
        self.tokenizer = None
        self.vectorizer = None
        self.ner_model = None
        
        # Flatten entities for quick lookup
        self.entities = []
        for entity_list in VIETNAMESE_ENTITIES.values():
            self.entities.extend(entity_list)
        
        if use_vietnamese_tokenizer:
            self._setup_tokenizer()
            self._setup_ner()
    
    def _setup_ner(self):
        """Setup NER model if available"""
        try:
            from underthesea import ner
            self.ner_model = ner
            logger.info("Vietnamese NER loaded")
        except Exception as e:
            logger.warning(f"Could not load NER: {e}")
    
    def _setup_tokenizer(self):
        """Setup Vietnamese tokenizer"""
        try:
            from underthesea import word_tokenize
            self.tokenizer = word_tokenize
            logger.info("Vietnamese tokenizer loaded")
        except Exception as e:
            logger.warning(f"Could not load tokenizer: {e}")
    
    def extract_entities(self, texts: List[str]) -> List[str]:
        """
        WITH entity preservation
        Returns phrases with scores
        """
        if not texts:
            return []
        
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            
            # 1. Extract entities first
            entities = self.extract_entities(texts)
            logger.info(f"Found {len(entities)} entities to preserve")
            
            # Vietnamese stopwords
            stopwords = [
                'của', 'và', 'có', 'được', 'này', 'cho', 'từ', 'với', 'theo', 'tại',
                'trong', 'các', 'một', 'là', 'để', 'đã', 'không', 'về', 'người',
                'khi', 'như', 'nên', 'cũng', 'đang', 'sẽ', 'bị', 'do', 'vào', 'ra'
            ]
            
            # Tokenize nếu có
            if self.tokenizer:
                processed_texts = []
                for text in texts:
                    try:
                        tokens = self.tokenizer.tokenize(text)
                        processed_texts.append(" ".join(tokens))
                    except:
                        processed_texts.append(text)
            else:
                processed_texts = texts
            
            # TF-IDF vectorizer
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
            
            # Calculate average TF-IDF score for each phrase
            phrase_scores = {}
            for idx, phrase in enumerate(feature_names):
                score = tfidf_matrix[:, idx].mean()
                phrase_scores[phrase] = float(score)
            
            # 2. Boost entity scores (x2 for entities)
            for phrase in phrase_scores:
                phrase_clean = self._clean_phrase(phrase)
                if phrase_clean in entities:
                    phrase_scores[phrase] *= 2.0
                    logger.debug(f"Boosted entity: {phrase_clean}")
            
            # Sort and return top N
            sorted_phrases = sorted(phrase_scores.items(), key=lambda x: x[1], reverse=True)
            
            results = []
            seen = set()
            
            # 3. Prioritize entities in results
            for entity in entities[:20]:  # Top 20 entities first
                if entity not in seen:
                    # Find in sorted_phrases
                    for phrase, score in sorted_phrases:
                        if entity in phrase.lower():
                            results.append({
                                "phrase": entity,
                                "score": score * 2.0,  # Boosted
                                "type": "entity"
                            })
                            seen.add(entity)
                            break
            
            # 4. Add other phrases
            for phrase, score in sorted_phrases:
                phrase_clean = self._clean_phrase(phrase)
                if phrase_clean and len(phrase_clean) > 2 and phrase_clean not in seen:
                    results.append({
                        "phrase": phrase_clean,
                        "score": round(score, 4),
                        "type": "tfidf"
                    })
                    seen.add(phrase_clean)
                
                if len(results) >= top_n:
                    break
            
            logger.info(f"Extracted {len(results)} keyphrases (with entities preserved)")
            return results[:top_n]
            
        except Exception as e:
            logger.error(f"TF-IDF extraction failed: {e}")
            return []
    
    def extract_keyphrases_ctfidf(
        self,
        texts: List[str],
        labels: Optional[List[int]] = None,
        top_n: int = 50
    ) -> List[Dict]:
        """
        Extract keyphrases using c-TF-IDF (class-based TF-IDF)
        Better for topic modeling context
        """
        if not texts:
            return []
        
        try:
            from sklearn.feature_extraction.text import CountVectorizer
            from sklearn.preprocessing import normalize
            import numpy as np
            
            stopwords = [
                'của', 'và', 'có', 'được', 'này', 'cho', 'từ', 'với', 'theo', 'tại',
                'trong', 'các', 'một', 'là', 'để', 'đã', 'không', 'về', 'người'
            ]
            
            # Tokenize
            if self.tokenizer:
                processed_texts = []
                for text in texts:
                    try:
                        tokens = self.tokenizer.tokenize(text)
                        processed_texts.append(" ".join(tokens))
                    except:
                        processed_texts.append(text)
            else:
                processed_texts = texts
            
            # CountVectorizer with n-grams
            vectorizer = CountVectorizer(
                ngram_range=(1, 3),
                min_df=2,
                max_df=0.8,
                stop_words=stopwords,
                lowercase=True
            )
            
            X = vectorizer.fit_transform(processed_texts)
            feature_names = vectorizer.get_feature_names_out()
            
            # If no labels, treat all as one class
            if labels is None:
                labels = [0] * len(texts)
            
            # Calculate c-TF-IDF
            unique_labels = list(set(labels))
            phrase_scores = {}
            
            for label in unique_labels:
                # Get docs for this label
                label_indices = [i for i, l in enumerate(labels) if l == label]
                if not label_indices:
                    continue
                
                # Sum word counts for this class
                class_counts = X[label_indices].sum(axis=0).A1
                
                # Number of docs per class
                docs_per_class = len(label_indices)
                
                # IDF: log(total_docs / docs_with_term)
                df = (X > 0).sum(axis=0).A1
                idf = np.log(len(texts) / (df + 1))
                
                # c-TF-IDF
                ctfidf = (class_counts / docs_per_class) * idf
                
                # Store scores
                for idx, phrase in enumerate(feature_names):
                    score = ctfidf[idx]
                    if phrase not in phrase_scores:
                        phrase_scores[phrase] = 0
                    phrase_scores[phrase] = max(phrase_scores[phrase], score)
            
            # Sort and return
            sorted_phrases = sorted(phrase_scores.items(), key=lambda x: x[1], reverse=True)
            
            results = []
            for phrase, score in sorted_phrases[:top_n]:
                phrase_clean = self._clean_phrase(phrase)
                if phrase_clean and len(phrase_clean) > 2:
                    results.append({
                        "phrase": phrase_clean,
                        "score": round(float(score), 4),
                        "type": "ctfidf"
                    })
            
            logger.info(f"Extracted {len(results)} keyphrases using c-TF-IDF")
            return results
            
        except Exception as e:
            logger.error(f"c-TF-IDF extraction failed: {e}")
            return []
    
    def extract_keyphrases_count(
        self,
        texts: List[str],
        top_n: int = 50,
        ngram_range: tuple = (2, 3)
    ) -> List[Dict]:
        """
        Simple count-based keyphrase extraction
        Focus on phrases (2-3 words) instead of single words
        """
        if not texts:
            return []
        
        try:
            from sklearn.feature_extraction.text import CountVectorizer
            
            stopwords = [
                'của', 'và', 'có', 'được', 'này', 'cho', 'từ', 'với', 'theo', 'tại',
                'trong', 'các', 'một', 'là', 'để', 'đã', 'không', 'về', 'người'
            ]
            
            # Tokenize
            if self.tokenizer:
                processed_texts = []
                for text in texts:
                    try:
                        tokens = self.tokenizer.tokenize(text)
                        processed_texts.append(" ".join(tokens))
                    except:
                        processed_texts.append(text)
            else:
                processed_texts = texts
            
            vectorizer = CountVectorizer(
                ngram_range=ngram_range,
                min_df=2,
                max_df=0.8,
                stop_words=stopwords,
                lowercase=True,
                max_features=200
            )
            
            X = vectorizer.fit_transform(processed_texts)
            feature_names = vectorizer.get_feature_names_out()
            
            # Sum counts
            counts = X.sum(axis=0).A1
            
            # Sort by count
            phrase_counts = list(zip(feature_names, counts))
            phrase_counts.sort(key=lambda x: x[1], reverse=True)
            
            results = []
            for phrase, count in phrase_counts[:top_n]:
                phrase_clean = self._clean_phrase(phrase)
                if phrase_clean and len(phrase_clean) > 2:
                    results.append({
                        "phrase": phrase_clean,
                        "count": int(count),
                        "type": "count"
                    })
            
            logger.info(f"Extracted {len(results)} keyphrases by count")
            return results
            
        except Exception as e:
            logger.error(f"Count extraction failed: {e}")
            return []
    
    def _clean_phrase(self, phrase: str) -> str:
        """Clean and normalize phrase"""
        # Remove underscores (from tokenizer)
        phrase = phrase.replace('_', ' ')
        
        # Remove extra spaces
        phrase = ' '.join(phrase.split())
        
        # Remove if starts/ends with stopwords
        stopwords_pattern = r'^(của|và|có|được|này|cho|từ|với|theo|tại|trong|các)\s+|\s+(của|và|có|được|này|cho|từ|với|theo|tại|trong|các)$'
        phrase = re.sub(stopwords_pattern, '', phrase, flags=re.IGNORECASE).strip()
        
        return phrase


# Singleton
_extractor_instance: Optional[KeyphraseExtractor] = None


def get_keyphrase_extractor() -> KeyphraseExtractor:
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = KeyphraseExtractor()
    return _extractor_instance
