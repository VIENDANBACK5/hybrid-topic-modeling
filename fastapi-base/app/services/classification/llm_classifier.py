"""
Service phân loại bài viết sử dụng LLM (OpenAI/GPT)
"""
import os
import json
import logging
from typing import Optional, Dict, List, Tuple
from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMFieldClassifier:
    """Phân loại bài viết bằng LLM"""
    
    def __init__(self):
        self.client = None
        self.api_key = os.getenv("OPENAI_API_KEY")
        
        if self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
                logger.info("✅ OpenAI client initialized for field classification")
            except Exception as e:
                logger.error(f"❌ Failed to initialize OpenAI client: {e}")
        else:
            logger.warning("⚠️ OPENAI_API_KEY not found - LLM classification disabled")
    
    def is_available(self) -> bool:
        """Kiểm tra LLM có sẵn sàng không"""
        return self.client is not None
    
    def classify_article(
        self,
        title: str,
        content: str,
        fields: List[Dict],
        model: str = "gpt-3.5-turbo"
    ) -> Optional[Tuple[int, float, str]]:
        """
        Phân loại bài viết bằng LLM
        
        Args:
            title: Tiêu đề bài viết
            content: Nội dung bài viết
            fields: Danh sách lĩnh vực với id, name, description
            model: Model OpenAI sử dụng
            
        Returns:
            Tuple (field_id, confidence_score, explanation) hoặc None
        """
        if not self.is_available():
            logger.warning("LLM not available for classification")
            return None
        
        # Chuẩn bị text
        article_text = f"{title}\n\n{content}" if content else title
        if not article_text or len(article_text.strip()) < 10:
            return None
        
        # Giới hạn độ dài để tiết kiệm token
        max_chars = 2000
        if len(article_text) > max_chars:
            article_text = article_text[:max_chars] + "..."
        
        # Tạo danh sách lĩnh vực cho prompt
        fields_info = []
        for field in fields:
            fields_info.append(
                f"{field['id']}. {field['name']}: {field.get('description', '')}"
            )
        
        # Tạo prompt
        prompt = f"""Phân tích bài viết sau và xác định lĩnh vực phù hợp nhất.

DANH SÁCH LĨNH VỰC:
{chr(10).join(fields_info)}

BÀI VIẾT:
{article_text}

YÊU CẦU:
- Đọc và phân tích nội dung bài viết
- Chọn 1 lĩnh vực phù hợp nhất từ danh sách trên
- Trả về JSON với format: {{"field_id": số, "confidence": số từ 0-1, "reason": "lý do ngắn gọn"}}
- Nếu không phù hợp lĩnh vực nào, trả về field_id = 0

Chỉ trả về JSON, không giải thích thêm."""

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Bạn là chuyên gia phân loại tin tức Việt Nam."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=150,
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            field_id = result.get("field_id", 0)
            confidence = float(result.get("confidence", 0))
            reason = result.get("reason", "")
            
            if field_id > 0 and confidence > 0:
                logger.info(f"✅ LLM classified: field_id={field_id}, confidence={confidence:.2f}")
                return (field_id, confidence, reason)
            else:
                logger.warning("❌ LLM could not classify article")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse LLM response: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ LLM classification error: {e}")
            return None
    
    def classify_batch(
        self,
        articles: List[Dict],
        fields: List[Dict],
        model: str = "gpt-3.5-turbo"
    ) -> List[Optional[Tuple[int, float, str]]]:
        """
        Phân loại nhiều bài viết (từng bài một để tránh rate limit)
        
        Args:
            articles: List of {id, title, content}
            fields: Danh sách lĩnh vực
            model: Model OpenAI
            
        Returns:
            List of classification results
        """
        results = []
        
        for article in articles:
            result = self.classify_article(
                title=article.get("title", ""),
                content=article.get("content", ""),
                fields=fields,
                model=model
            )
            results.append(result)
        
        return results
