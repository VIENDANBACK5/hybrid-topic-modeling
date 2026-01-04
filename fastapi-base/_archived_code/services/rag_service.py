"""
RAG (Retrieval-Augmented Generation) Service
Tìm kiếm và hỏi đáp trên dữ liệu đã crawl
"""
import logging
from typing import List, Dict, Optional
import numpy as np

logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG service cho search và Q&A trên articles
    
    Flow:
    1. User đặt câu hỏi
    2. Embed câu hỏi thành vector
    3. Tìm top-k articles liên quan (similarity search)
    4. Dùng LLM để generate answer từ context
    """
    
    def __init__(self):
        self.embedding_model = None
        self.llm_client = None
        self.embedding_cache = {}
        self.faiss_index = None
        self.article_ids = []
        self._setup()
    
    def _setup(self):
        """Setup embedding model (optimized)"""
        try:
            from sentence_transformers import SentenceTransformer
            
            model_name = "keepitreal/vietnamese-sbert"
            self.embedding_model = SentenceTransformer(model_name)
            self.embedding_model.max_seq_length = 128
            
            logger.info(f"RAG: Loaded embedding model {model_name} (max_seq_length=128)")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
    
    def embed_query(self, query: str) -> np.ndarray:
        """Embed user query into vector"""
        if not self.embedding_model:
            self._setup()
        
        return self.embedding_model.encode([query])[0]
    
    def search_similar_articles(
        self, 
        query: str, 
        articles: List[Dict],
        top_k: int = 5,
        use_cache: bool = True
    ) -> List[Dict]:
        """
        Tìm articles giống nhất với query (OPTIMIZED)
        
        Args:
            query: Câu hỏi của user
            articles: List articles từ DB
            top_k: Số lượng articles trả về
            use_cache: Dùng embedding cache
        
        Returns:
            List articles sorted by relevance
        """
        if not articles:
            return []
        
        # Embed query
        query_embedding = self.embed_query(query)
        
        # Build texts for all articles
        texts = []
        for article in articles:
            title = article.get('title', '') or ''
            content = article.get('content', '') or ''
            text = f"{title} {content}".strip()
            texts.append(text[:500])  # Limit to 500 chars
        
        # Batch encode all articles (FAST)
        logger.info(f"Encoding {len(texts)} articles in batch...")
        article_embeddings = self.embedding_model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False
        )
        
        # Use FAISS for fast similarity search if many articles
        if len(articles) > 100:
            try:
                import faiss
                
                # Build index
                dimension = article_embeddings.shape[1]
                index = faiss.IndexFlatIP(dimension)  # Inner product = cosine similarity
                
                # Normalize vectors
                faiss.normalize_L2(article_embeddings)
                faiss.normalize_L2(query_embedding.reshape(1, -1))
                
                index.add(article_embeddings)
                
                # Search
                actual_top_k = min(top_k, len(articles))
                similarities, indices = index.search(
                    query_embedding.reshape(1, -1),
                    actual_top_k
                )
                
                # Build results
                results = []
                for i, (idx, sim) in enumerate(zip(indices[0], similarities[0])):
                    article = articles[int(idx)]
                    results.append({
                        **article,
                        'similarity': float(sim),
                        'rank': i + 1
                    })
                
                return results
                
            except Exception as e:
                logger.warning(f"FAISS failed: {e}, using numpy fallback")
        
        # Fallback: numpy cosine similarity
        from sklearn.metrics.pairwise import cosine_similarity
        
        similarities = cosine_similarity(
            [query_embedding],
            article_embeddings
        )[0]
        
        # Get top-k
        actual_top_k = min(top_k, len(articles))
        top_indices = np.argsort(similarities)[::-1][:actual_top_k]
        
        results = []
        for i, idx in enumerate(top_indices):
            article = articles[idx]
            results.append({
                **article,
                'similarity': float(similarities[idx]),
                'rank': i + 1
            })
        
        return results
    
    def qa(
        self,
        question: str,
        articles: List[Dict],
        top_k: int = 5,
        use_llm: bool = True
    ) -> Dict:
        """
        Q&A với RAG (OPTIMIZED)
        
        Args:
            question: Câu hỏi
            articles: List articles từ DB
            top_k: Số articles để lấy context
            use_llm: Dùng LLM để generate answer
        
        Returns:
            Dict with answer and sources
        """
        # Search relevant articles
        relevant_articles = self.search_similar_articles(
            query=question,
            articles=articles,
            top_k=top_k
        )
        
        if not relevant_articles:
            return {
                "answer": "Không tìm thấy thông tin liên quan.",
                "sources": []
            }
        
        # If not using LLM, just return sources
        if not use_llm:
            return {
                "answer": f"Tìm thấy {len(relevant_articles)} tài liệu liên quan.",
                "sources": relevant_articles
            }
        
        # Generate answer with LLM
        try:
            import openai
            from app.core.config import settings
            
            # Build context from top articles
            context_parts = []
            sources = []
            
            for i, article in enumerate(relevant_articles[:5]):
                title = article.get('title', '')
                content = article.get('content', '')[:500]
                url = article.get('url', '')
                
                context_parts.append(f"[{i+1}] {title}\n{content}")
                sources.append({
                    "title": title,
                    "url": url,
                    "similarity": article.get('similarity', 0),
                    "rank": i + 1
                })
            
            context = "\n\n".join(context_parts)
            
            # Call OpenAI
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Bạn là trợ lý AI thông minh. Trả lời câu hỏi dựa trên context được cung cấp. Trả lời bằng tiếng Việt, ngắn gọn và chính xác."
                    },
                    {
                        "role": "user",
                        "content": f"Context:\n{context}\n\nCâu hỏi: {question}\n\nTrả lời:"
                    }
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            answer = response.choices[0].message.content
            
            return {
                "answer": answer,
                "sources": sources
            }
            
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return {
                "answer": f"Tìm thấy {len(relevant_articles)} tài liệu liên quan nhưng không thể tạo câu trả lời.",
                "sources": relevant_articles[:5]
            }
    
    def generate_answer(
        self,
        question: str,
        context_articles: List[Dict],
        max_tokens: int = 500
    ) -> str:
        """
        Generate answer using LLM (deprecated - use qa() instead)
        """
        result = self.qa(
            question=question,
            articles=context_articles,
            use_llm=True
        )
        return result.get("answer", "")
