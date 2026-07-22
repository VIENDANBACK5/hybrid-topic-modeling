"""
TopicGPT Service - Wrapper for TopicGPT integration
Provides LLM-powered topic modeling enhancements
"""
import os
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TopicGPTService:
    """
    TopicGPT Service - Intelligent topic modeling with LLMs
    
    Features:
    - Generate natural language topic labels
    - Create detailed topic descriptions
    - Merge similar topics
    - Categorize content
    - Extract keywords and tags
    """
    
    def __init__(
        self,
        api: str = "openai",
        model: str = "gpt-4o-mini",
        cache_enabled: bool = True,
        cache_dir: str = "data/cache/topicgpt"
    ):
        """
        Initialize TopicGPT Service
        
        Args:
            api: API provider ('openai', 'gemini', 'azure', 'vertex')
            model: Model name
            cache_enabled: Enable caching to save costs
            cache_dir: Directory for caching results
        """
        self.api = api
        self.model = model
        self.cache_enabled = cache_enabled
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize API client
        self.client = None
        self._init_api_client()
        
        # Cache storage
        self._cache = {}
        self._load_cache()
        
        logger.info(f"TopicGPT Service initialized with {api}/{model}")
    
    def _init_api_client(self):
        """Initialize LLM API client"""
        try:
            if self.api == "openai":
                from openai import OpenAI
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    logger.warning("OPENAI_API_KEY not found - TopicGPT features disabled")
                    return
                self.client = OpenAI(api_key=api_key)
                logger.info(" OpenAI client initialized")
            
            elif self.api == "gemini":
                import google.generativeai as genai
                api_key = os.getenv("GEMINI_API_KEY")
                if not api_key:
                    logger.warning("GEMINI_API_KEY not found")
                    return
                genai.configure(api_key=api_key)
                self.client = genai.GenerativeModel(self.model)
                logger.info(" Gemini client initialized")
            
            else:
                logger.warning(f"API {self.api} not yet implemented")
        
        except Exception as e:
            logger.error(f"Failed to initialize API client: {e}")
            self.client = None
    
    def _load_cache(self):
        """Load cached results from disk"""
        cache_file = self.cache_dir / "cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self._cache = json.load(f)
                logger.info(f"Loaded {len(self._cache)} cached results")
            except Exception as e:
                logger.warning(f"Could not load cache: {e}")
                self._cache = {}
    
    def _save_cache(self):
        """Save cache to disk"""
        if not self.cache_enabled:
            return
        
        cache_file = self.cache_dir / "cache.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Could not save cache: {e}")
    
    def _get_cache_key(self, operation: str, **kwargs) -> str:
        """Generate cache key"""
        key_data = f"{operation}:{json.dumps(kwargs, sort_keys=True)}"
        import hashlib
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _call_llm(self, prompt: str, max_tokens: int = 500, temperature: float = 0.3) -> Optional[str]:
        """Call LLM API with caching"""
        if not self.client:
            logger.warning("LLM client not initialized")
            return None
        
        # Check cache
        cache_key = self._get_cache_key("llm_call", prompt=prompt[:100])
        if self.cache_enabled and cache_key in self._cache:
            logger.debug("Using cached LLM response")
            return self._cache[cache_key]
        
        try:
            if self.api == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant for Vietnamese text analysis."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                result = response.choices[0].message.content
            
            elif self.api == "gemini":
                response = self.client.generate_content(prompt)
                result = response.text
            
            else:
                logger.warning(f"API {self.api} not implemented")
                return None
            
            # Cache result
            if self.cache_enabled:
                self._cache[cache_key] = result
                self._save_cache()
            
            return result
        
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            return None
    
    # ==================== TOPIC MODELING FEATURES ====================
    
    def generate_topic_label(self, keywords: List[str], representative_docs: List[str] = None) -> Optional[str]:
        """
        Generate natural language label for a topic from keywords
        
        Args:
            keywords: List of top keywords for the topic
            representative_docs: Sample documents (optional)
        
        Returns:
            Natural language topic label
        """
        if not keywords:
            return None
        
        # Build prompt
        keywords_str = ", ".join(keywords[:10])
        
        prompt = f"""Phân tích các từ khóa từ bài viết mạng xã hội tiếng Việt và tạo tên chủ đề phù hợp:

Từ khóa: {keywords_str}

LƯU Ý QUAN TRỌNG:
- Các từ khóa này được trích xuất tự động từ văn bản tiếng Việt
- "ai" = đại từ nghi vấn (who/someone), KHÔNG phải tên người
- "báo" = thông báo/báo cáo/tin tức, KHÔNG phải con báo
- "ông" = đại từ xưng hô, KHÔNG phải tên riêng
- Các từ có gạch dưới như "hưng_yên" = cụm từ ghép
- Từ "translate" thường là artifact từ Facebook dịch tự động, bỏ qua

Yêu cầu:
- Tên chủ đề ngắn gọn (3-7 từ tiếng Việt)
- Phản ánh đúng chủ đề thảo luận trên mạng xã hội
- Nếu có địa danh (hưng_yên, hà_nội) thì đề cập
- Chỉ trả về tên chủ đề, không giải thích

Ví dụ:
- hưng_yên, tỉnh, hà_nội, phát_triển → Phát triển Hưng Yên
- chụp, ảnh, hưng_yên, kỷ_yếu → Dịch vụ chụp ảnh Hưng Yên
- xe_máy, giao_thông, đường, tai_nạn → An toàn giao thông
- ma_túy, bắt_giữ, công_an, hình_sự → Đấu tranh phòng chống ma túy

Tên chủ đề:"""
        
        result = self._call_llm(prompt, max_tokens=50, temperature=0.3)
        if result:
            # Clean result
            result = result.strip().strip('"').strip("'")
            logger.info(f"Generated label: {result} from keywords: {keywords_str[:50]}")
        
        return result
    
    def generate_topic_description(
        self,
        topic_label: str,
        keywords: List[str],
        representative_docs: List[str] = None
    ) -> Optional[str]:
        """
        Generate detailed description for a topic
        
        Args:
            topic_label: Topic label
            keywords: Topic keywords
            representative_docs: Sample documents
        
        Returns:
            Detailed topic description
        """
        keywords_str = ", ".join(keywords[:15])
        
        # Add sample docs if available
        docs_context = ""
        if representative_docs and len(representative_docs) > 0:
            sample_docs = representative_docs[:3]
            docs_context = "\n\nCác văn bản mẫu:\n" + "\n".join([f"- {doc[:150]}..." for doc in sample_docs])
        
        prompt = f"""Hãy viết mô tả chi tiết cho chủ đề sau:

Tên chủ đề: {topic_label}
Từ khóa: {keywords_str}{docs_context}

Yêu cầu:
- Mô tả chi tiết nội dung chủ đề này
- 2-3 câu, rõ ràng, súc tích
- Bằng tiếng Việt
- Chỉ trả về mô tả, không thêm tiêu đề

Mô tả:"""
        
        result = self._call_llm(prompt, max_tokens=200, temperature=0.4)
        if result:
            result = result.strip()
            logger.info(f"Generated description for: {topic_label}")
        
        return result
    
    def refine_topics(
        self,
        topics: List[Dict],
        merge_threshold: float = 0.85
    ) -> Dict:
        """
        Analyze and suggest topic merges
        
        Args:
            topics: List of topics with labels and keywords
            merge_threshold: Similarity threshold for merging
        
        Returns:
            Dict with merge suggestions
        """
        if len(topics) < 2:
            return {"merges": [], "message": "Not enough topics to merge"}
        
        # Build topic list
        topic_list = []
        for i, topic in enumerate(topics[:20]):  # Limit to 20 topics
            label = topic.get('label', topic.get('name', f"Topic {i}"))
            keywords = topic.get('keywords', [])
            keywords_str = ", ".join(keywords[:5]) if isinstance(keywords, list) else str(keywords)
            topic_list.append(f"{i+1}. {label} ({keywords_str})")
        
        topics_text = "\n".join(topic_list)
        
        prompt = f"""Phân tích danh sách các chủ đề sau và tìm các chủ đề tương tự nên được gộp lại:

{topics_text}

Yêu cầu:
- Tìm các cặp chủ đề tương tự (có nội dung chồng lấp)
- Đề xuất tên mới cho chủ đề sau khi gộp
- Trả về dạng JSON: {{"merges": [{{"topics": [1, 3], "new_name": "Tên mới"}}]}}
- Nếu không có gì cần gộp, trả về {{"merges": []}}

Kết quả:"""
        
        result = self._call_llm(prompt, max_tokens=500, temperature=0.2)
        
        if result:
            try:
                # Parse JSON from result
                import re
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    merge_data = json.loads(json_match.group())
                    logger.info(f"Found {len(merge_data.get('merges', []))} merge suggestions")
                    return merge_data
            except Exception as e:
                logger.warning(f"Could not parse merge suggestions: {e}")
        
        return {"merges": [], "message": "No merges suggested"}
    
    # ==================== CONTENT ANALYSIS FEATURES ====================
    
    def categorize_content(
        self,
        text: str,
        categories: List[str] = None,
        max_chars: int = 500
    ) -> Dict:
        """
        Categorize content into predefined categories
        
        Args:
            text: Content to categorize
            categories: List of possible categories
            max_chars: Max characters to analyze
        
        Returns:
            Dict with category and confidence
        """
        if not text:
            return {"category": "Unknown", "confidence": 0.0}
        
        # Default Vietnamese categories
        if not categories:
            categories = [
                "Chính trị",
                "Kinh tế",
                "Xã hội",
                "Giáo dục",
                "Khoa học & Công nghệ",
                "Văn hóa",
                "Thể thao",
                "Giải trí",
                "Y tế & Sức khỏe",
                "Môi trường",
                "Pháp luật",
                "Đời sống",
                "Khác"
            ]
        
        # Truncate text
        text_sample = text[:max_chars]
        categories_str = ", ".join(categories)
        
        prompt = f"""Phân loại văn bản sau vào một trong các danh mục:

Danh mục: {categories_str}

Văn bản:
{text_sample}

Yêu cầu:
- Chọn 1 danh mục phù hợp nhất
- Đánh giá độ tin cậy (0.0-1.0)
- Trả về JSON: {{"category": "Tên danh mục", "confidence": 0.95}}

Kết quả:"""
        
        result = self._call_llm(prompt, max_tokens=100, temperature=0.2)
        
        if result:
            try:
                import re
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    logger.info(f"Categorized as: {data.get('category')} (confidence: {data.get('confidence')})")
                    return data
            except Exception as e:
                logger.warning(f"Could not parse categorization result: {e}")
        
        return {"category": "Unknown", "confidence": 0.0}
    
    def extract_keywords_and_tags(
        self,
        text: str,
        max_keywords: int = 10,
        max_chars: int = 1000
    ) -> Dict:
        """
        Extract keywords and tags from text
        
        Args:
            text: Content to analyze
            max_keywords: Maximum keywords to extract
            max_chars: Max characters to analyze
        
        Returns:
            Dict with keywords and tags
        """
        if not text:
            return {"keywords": [], "tags": []}
        
        text_sample = text[:max_chars]
        
        prompt = f"""Trích xuất từ khóa và thẻ tag từ văn bản sau:

{text_sample}

Yêu cầu:
- Tìm {max_keywords} từ khóa quan trọng nhất
- Tìm các thẻ tag phù hợp (hashtag style)
- Trả về JSON: {{"keywords": ["từ1", "từ2"], "tags": ["#tag1", "#tag2"]}}

Kết quả:"""
        
        result = self._call_llm(prompt, max_tokens=300, temperature=0.3)
        
        if result:
            try:
                import re
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    logger.info(f"Extracted {len(data.get('keywords', []))} keywords")
                    return data
            except Exception as e:
                logger.warning(f"Could not parse extraction result: {e}")
        
        return {"keywords": [], "tags": []}
    
    def summarize_content(
        self,
        text: str,
        max_length: int = 200,
        max_input_chars: int = 2000
    ) -> Optional[str]:
        """
        Generate summary of content
        
        Args:
            text: Content to summarize
            max_length: Maximum summary length in words
            max_input_chars: Max input characters
        
        Returns:
            Summary text
        """
        if not text:
            return None
        
        text_sample = text[:max_input_chars]
        
        prompt = f"""Tóm tắt ngắn gọn nội dung sau (tối đa {max_length} từ):

{text_sample}

Yêu cầu:
- Tóm tắt súc tích, đầy đủ ý chính
- Bằng tiếng Việt
- Không thêm ý kiến cá nhân
- Chỉ trả về tóm tắt, không thêm tiêu đề

Tóm tắt:"""
        
        result = self._call_llm(prompt, max_tokens=max_length * 2, temperature=0.3)
        
        if result:
            result = result.strip()
            logger.info(f"Generated summary: {len(result)} chars")
            return result
        
        return None
    
    def detect_similarity(
        self,
        text1: str,
        text2: str,
        max_chars: int = 300
    ) -> float:
        """
        Detect semantic similarity between two texts
        
        Args:
            text1: First text
            text2: Second text
            max_chars: Max characters per text
        
        Returns:
            Similarity score (0.0-1.0)
        """
        if not text1 or not text2:
            return 0.0
        
        sample1 = text1[:max_chars]
        sample2 = text2[:max_chars]
        
        prompt = f"""Đánh giá mức độ tương đồng về nội dung giữa 2 văn bản sau:

Văn bản 1:
{sample1}

Văn bản 2:
{sample2}

Yêu cầu:
- Đánh giá mức độ tương đồng (0.0 = hoàn toàn khác, 1.0 = giống hệt)
- Trả về JSON: {{"similarity": 0.85, "reason": "Lý do ngắn gọn"}}

Kết quả:"""
        
        result = self._call_llm(prompt, max_tokens=150, temperature=0.2)
        
        if result:
            try:
                import re
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    similarity = float(data.get('similarity', 0.0))
                    logger.info(f"Similarity: {similarity:.2f}")
                    return similarity
            except Exception as e:
                logger.warning(f"Could not parse similarity result: {e}")
        
        return 0.0
    
    # ==================== UTILITY FEATURES ====================
    
    def is_available(self) -> bool:
        """Check if service is available"""
        return self.client is not None
    
    def get_stats(self) -> Dict:
        """Get service statistics"""
        return {
            "api": self.api,
            "model": self.model,
            "cache_enabled": self.cache_enabled,
            "cached_items": len(self._cache),
            "available": self.is_available()
        }
    
    def clear_cache(self):
        """Clear all cached results"""
        self._cache = {}
        self._save_cache()
        logger.info("Cache cleared")


# Global instance (lazy initialization)
_topicgpt_service = None

def get_topicgpt_service() -> TopicGPTService:
    """Get or create global TopicGPT service instance"""
    global _topicgpt_service
    if _topicgpt_service is None:
        # Default to GPT-4o-mini for cost efficiency
        api = os.getenv("TOPICGPT_API", "openai")
        model = os.getenv("TOPICGPT_MODEL", "gpt-4o-mini")
        _topicgpt_service = TopicGPTService(api=api, model=model)
    return _topicgpt_service
