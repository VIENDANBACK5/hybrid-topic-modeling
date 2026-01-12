"""
TopicGPT Service V2 - LangChain-powered version
Provides LLM-powered topic modeling with better structure and maintainability
"""
import os
import logging
from typing import List, Dict, Optional
from pathlib import Path
import json
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_community.callbacks import get_openai_callback
from langchain_core.runnables import RunnablePassthrough
from langchain_community.cache import SQLiteCache
from langchain.globals import set_llm_cache

logger = logging.getLogger(__name__)


# ==================== OUTPUT MODELS ====================

class TopicLabel(BaseModel):
    """Topic label output"""
    name: str = Field(description="Tên chủ đề ngắn gọn 3-7 từ")
    confidence: float = Field(description="Độ tin cậy 0-1", ge=0.0, le=1.0)


class TopicDescription(BaseModel):
    """Topic description output"""
    description: str = Field(description="Mô tả chi tiết 2-3 câu")


class CategoryResult(BaseModel):
    """Categorization result"""
    category: str = Field(description="Tên danh mục")
    confidence: float = Field(description="Độ tin cậy 0-1", ge=0.0, le=1.0)


class KeywordsAndTags(BaseModel):
    """Keywords and tags extraction"""
    keywords: List[str] = Field(description="Danh sách từ khóa")
    tags: List[str] = Field(description="Danh sách hashtags")


class SimilarityResult(BaseModel):
    """Similarity comparison result"""
    similarity: float = Field(description="Điểm tương đồng 0-1", ge=0.0, le=1.0)
    reason: str = Field(description="Lý do đánh giá")


class MergeResult(BaseModel):
    """Topic merge result"""
    merges: List[Dict] = Field(description="Danh sách đề xuất gộp topic")


# ==================== MAIN SERVICE ====================

class TopicGPTServiceV2:
    """
    TopicGPT Service V2 - LangChain Edition
    
    Improvements:
    - Structured output with Pydantic
    - Better prompt management
    - Automatic retry logic
    - Token usage tracking
    - SQLite cache for persistence
    """
    
    def __init__(
        self,
        api: str = "openai",
        model: str = "gpt-4o-mini",
        cache_enabled: bool = True,
        cache_dir: str = "data/cache/topicgpt"
    ):
        self.api = api
        self.model = model
        self.cache_enabled = cache_enabled
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize LangChain LLM
        self.llm = None
        self._init_llm()
        
        # Setup cache
        if cache_enabled:
            cache_path = str(self.cache_dir / "langchain.db")
            set_llm_cache(SQLiteCache(database_path=cache_path))
            logger.info(f"LangChain cache enabled at {cache_path}")
        
        # Token usage stats
        self.total_tokens = 0
        self.total_cost = 0.0
        
        logger.info(f"TopicGPT V2 initialized with {api}/{model}")
    
    def _init_llm(self):
        """Initialize LangChain LLM"""
        try:
            if self.api == "openai":
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    logger.warning("OPENAI_API_KEY not found")
                    return
                
                self.llm = ChatOpenAI(
                    model=self.model,
                    temperature=0.3,
                    max_tokens=500,
                    timeout=30,
                    max_retries=3,
                    api_key=api_key
                )
                logger.info("✅ ChatOpenAI initialized")
            
            elif self.api == "gemini":
                api_key = os.getenv("GEMINI_API_KEY")
                if not api_key:
                    logger.warning("GEMINI_API_KEY not found")
                    return
                
                self.llm = ChatGoogleGenerativeAI(
                    model=self.model,
                    temperature=0.3,
                    max_tokens=500,
                    timeout=30,
                    max_retries=3,
                    google_api_key=api_key
                )
                logger.info("✅ ChatGoogleGenerativeAI initialized")
            
            else:
                logger.warning(f"API {self.api} not supported")
        
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            self.llm = None
    
    # ==================== TOPIC MODELING FEATURES ====================
    
    def generate_topic_label(
        self,
        keywords: List[str],
        representative_docs: List[str] = None
    ) -> Optional[str]:
        """Generate natural language label for a topic"""
        if not self.llm or not keywords:
            return None
        
        keywords_str = ", ".join(keywords[:10])
        
        # Create prompt template
        template = """Phân tích các từ khóa từ bài viết mạng xã hội tiếng Việt và tạo tên chủ đề phù hợp:

Từ khóa: {keywords}

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

Tên chủ đề:"""
        
        prompt = PromptTemplate(
            input_variables=["keywords"],
            template=template
        )
        
        try:
            with get_openai_callback() as cb:
                chain = prompt | self.llm
                result = chain.invoke({"keywords": keywords_str})
                
                # Track usage
                self.total_tokens += cb.total_tokens
                self.total_cost += cb.total_cost
                
                label = result.content.strip().strip('"').strip("'")
                logger.info(f"Generated label: {label} (tokens: {cb.total_tokens}, cost: ${cb.total_cost:.4f})")
                return label
        
        except Exception as e:
            logger.error(f"Error generating topic label: {e}")
            return None
    
    def generate_topic_description(
        self,
        topic_label: str,
        keywords: List[str],
        representative_docs: List[str] = None
    ) -> Optional[str]:
        """Generate detailed description for a topic"""
        if not self.llm:
            return None
        
        keywords_str = ", ".join(keywords[:15])
        
        docs_context = ""
        if representative_docs and len(representative_docs) > 0:
            sample_docs = representative_docs[:3]
            docs_context = "\n\nCác văn bản mẫu:\n" + "\n".join([f"- {doc[:150]}..." for doc in sample_docs])
        
        template = """Hãy viết mô tả chi tiết cho chủ đề sau:

Tên chủ đề: {topic_label}
Từ khóa: {keywords}{docs_context}

Yêu cầu:
- Mô tả chi tiết nội dung chủ đề này
- 2-3 câu, rõ ràng, súc tích
- Bằng tiếng Việt
- Chỉ trả về mô tả, không thêm tiêu đề

Mô tả:"""
        
        prompt = PromptTemplate(
            input_variables=["topic_label", "keywords", "docs_context"],
            template=template
        )
        
        try:
            with get_openai_callback() as cb:
                chain = prompt | self.llm
                result = chain.invoke({
                    "topic_label": topic_label,
                    "keywords": keywords_str,
                    "docs_context": docs_context
                })
                
                self.total_tokens += cb.total_tokens
                self.total_cost += cb.total_cost
                
                description = result.content.strip()
                logger.info(f"Generated description (tokens: {cb.total_tokens})")
                return description
        
        except Exception as e:
            logger.error(f"Error generating description: {e}")
            return None
    
    def categorize_content(
        self,
        text: str,
        categories: List[str] = None,
        max_chars: int = 500
    ) -> Dict:
        """Categorize content with structured output"""
        if not self.llm or not text:
            return {"category": "Unknown", "confidence": 0.0}
        
        if not categories:
            categories = [
                "Chính trị", "Kinh tế", "Xã hội", "Giáo dục",
                "Khoa học & Công nghệ", "Văn hóa", "Thể thao",
                "Giải trí", "Y tế & Sức khỏe", "Môi trường",
                "Pháp luật", "Đời sống", "Khác"
            ]
        
        text_sample = text[:max_chars]
        categories_str = ", ".join(categories)
        
        # Setup parser
        parser = PydanticOutputParser(pydantic_object=CategoryResult)
        
        template = """Phân loại văn bản sau vào một trong các danh mục:

Danh mục: {categories}

Văn bản:
{text}

{format_instructions}

Kết quả:"""
        
        prompt = PromptTemplate(
            input_variables=["categories", "text"],
            template=template,
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        try:
            with get_openai_callback() as cb:
                chain = prompt | self.llm | parser
                result = chain.invoke({
                    "categories": categories_str,
                    "text": text_sample
                })
                
                self.total_tokens += cb.total_tokens
                self.total_cost += cb.total_cost
                
                logger.info(f"Categorized: {result.category} (conf: {result.confidence:.2f})")
                return result.dict()
        
        except Exception as e:
            logger.error(f"Error categorizing content: {e}")
            return {"category": "Unknown", "confidence": 0.0}
    
    def extract_keywords_and_tags(
        self,
        text: str,
        max_keywords: int = 10,
        max_chars: int = 1000
    ) -> Dict:
        """Extract keywords and tags with structured output"""
        if not self.llm or not text:
            return {"keywords": [], "tags": []}
        
        text_sample = text[:max_chars]
        parser = PydanticOutputParser(pydantic_object=KeywordsAndTags)
        
        template = """Trích xuất từ khóa và thẻ tag từ văn bản sau:

{text}

Yêu cầu:
- Tìm {max_keywords} từ khóa quan trọng nhất
- Tìm các thẻ tag phù hợp (hashtag style)

{format_instructions}

Kết quả:"""
        
        prompt = PromptTemplate(
            input_variables=["text", "max_keywords"],
            template=template,
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        try:
            with get_openai_callback() as cb:
                chain = prompt | self.llm | parser
                result = chain.invoke({
                    "text": text_sample,
                    "max_keywords": max_keywords
                })
                
                self.total_tokens += cb.total_tokens
                self.total_cost += cb.total_cost
                
                logger.info(f"Extracted {len(result.keywords)} keywords")
                return result.dict()
        
        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            return {"keywords": [], "tags": []}
    
    def summarize_content(
        self,
        text: str,
        max_length: int = 200,
        max_input_chars: int = 2000
    ) -> Optional[str]:
        """Generate summary"""
        if not self.llm or not text:
            return None
        
        text_sample = text[:max_input_chars]
        
        template = """Tóm tắt ngắn gọn nội dung sau (tối đa {max_length} từ):

{text}

Yêu cầu:
- Tóm tắt súc tích, đầy đủ ý chính
- Bằng tiếng Việt
- Không thêm ý kiến cá nhân
- Chỉ trả về tóm tắt

Tóm tắt:"""
        
        prompt = PromptTemplate(
            input_variables=["text", "max_length"],
            template=template
        )
        
        try:
            with get_openai_callback() as cb:
                chain = prompt | self.llm
                result = chain.invoke({
                    "text": text_sample,
                    "max_length": max_length
                })
                
                self.total_tokens += cb.total_tokens
                self.total_cost += cb.total_cost
                
                summary = result.content.strip()
                logger.info(f"Generated summary: {len(summary)} chars")
                return summary
        
        except Exception as e:
            logger.error(f"Error summarizing: {e}")
            return None
    
    def detect_similarity(
        self,
        text1: str,
        text2: str,
        max_chars: int = 300
    ) -> float:
        """Detect semantic similarity with structured output"""
        if not self.llm or not text1 or not text2:
            return 0.0
        
        sample1 = text1[:max_chars]
        sample2 = text2[:max_chars]
        
        parser = PydanticOutputParser(pydantic_object=SimilarityResult)
        
        template = """Đánh giá mức độ tương đồng về nội dung giữa 2 văn bản sau:

Văn bản 1:
{text1}

Văn bản 2:
{text2}

Yêu cầu:
- Đánh giá mức độ tương đồng (0.0 = hoàn toàn khác, 1.0 = giống hệt)

{format_instructions}

Kết quả:"""
        
        prompt = PromptTemplate(
            input_variables=["text1", "text2"],
            template=template,
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        try:
            with get_openai_callback() as cb:
                chain = prompt | self.llm | parser
                result = chain.invoke({
                    "text1": sample1,
                    "text2": sample2
                })
                
                self.total_tokens += cb.total_tokens
                self.total_cost += cb.total_cost
                
                logger.info(f"Similarity: {result.similarity:.2f}")
                return result.similarity
        
        except Exception as e:
            logger.error(f"Error detecting similarity: {e}")
            return 0.0
    
    # ==================== UTILITY FEATURES ====================
    
    def is_available(self) -> bool:
        """Check if service is available"""
        return self.llm is not None
    
    def get_stats(self) -> Dict:
        """Get service statistics"""
        return {
            "api": self.api,
            "model": self.model,
            "cache_enabled": self.cache_enabled,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "available": self.is_available()
        }


# Global instance
_topicgpt_v2_service = None

def get_topicgpt_v2_service() -> TopicGPTServiceV2:
    """Get or create global TopicGPT V2 service instance"""
    global _topicgpt_v2_service
    if _topicgpt_v2_service is None:
        api = os.getenv("TOPICGPT_API", "openai")
        model = os.getenv("TOPICGPT_MODEL", "gpt-4o-mini")
        _topicgpt_v2_service = TopicGPTServiceV2(api=api, model=model)
    return _topicgpt_v2_service
