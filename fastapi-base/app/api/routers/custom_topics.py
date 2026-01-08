"""
Custom Topics API Endpoints
Quản lý topics tự định nghĩa và phân loại bài viết
"""

import logging
import time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.core.database import get_db
from app.models.model_custom_topic import CustomTopic, ArticleCustomTopic, TopicTemplate
from app.models.model_article import Article
from app.schemas.schema_custom_topic import (
    CustomTopicCreate,
    CustomTopicUpdate,
    CustomTopicResponse,
    CustomTopicDetailResponse,
    ClassifyArticlesRequest,
    BulkClassificationResponse,
    ArticleWithTopicsResponse,
    TopicWithArticlesResponse,
    TopicTemplateCreate,
    TopicTemplateResponse,
    ApplyTemplateRequest,
    ClassificationOverview,
    ClassificationMethod,
    TopicClassificationResult
)
from app.services.topic.custom_classifier import get_classifier
from app.core.auth import verify_api_key
from fastapi import Security

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/custom-topics", tags=["Custom Topics"])


# ============================================
# TOPIC CRUD
# ============================================

@router.post("/", response_model=CustomTopicResponse, status_code=201)
async def create_topic(
    topic: CustomTopicCreate,
    db: Session = Depends(get_db),
    api_key: str = Security(verify_api_key)
):
    """
    🆕 Tạo topic mới
    
    **Yêu cầu:**
    - Tên topic phải unique
    - Ít nhất 3 từ khóa
    - (Tùy chọn) Câu văn mẫu để improve accuracy
    
    **Ví dụ:**
    ```json
    {
      "name": "Chính trị Việt Nam",
      "description": "Tin tức chính trị trong nước",
      "keywords": ["quốc hội", "chính phủ", "bộ trưởng", "nghị quyết", "chính sách"],
      "example_docs": [
        "Quốc hội thông qua nghị quyết về kinh tế",
        "Chính phủ ban hành chính sách mới"
      ],
      "min_confidence": 0.6,
      "color": "#EF4444"
    }
    ```
    """
    # Check duplicate name
    existing = db.query(CustomTopic).filter(CustomTopic.name == topic.name).first()
    if existing:
        raise HTTPException(400, f"Topic với tên '{topic.name}' đã tồn tại")
    
    # Generate slug
    import re
    import unicodedata
    slug = unicodedata.normalize('NFKD', topic.name).encode('ascii', 'ignore').decode('utf-8')
    slug = re.sub(r'[^\w\s-]', '', slug).strip().lower()
    slug = re.sub(r'[-\s]+', '-', slug)
    
    # Check duplicate slug
    slug_base = slug
    counter = 1
    while db.query(CustomTopic).filter(CustomTopic.slug == slug).first():
        slug = f"{slug_base}-{counter}"
        counter += 1
    
    # Create topic
    db_topic = CustomTopic(
        **topic.dict(),
        slug=slug
    )
    db.add(db_topic)
    db.commit()
    db.refresh(db_topic)
    
    logger.info(f" Created topic: {db_topic.name} (ID: {db_topic.id})")
    
    # Clear classifier cache
    get_classifier().clear_cache()
    
    return db_topic


@router.get("/", response_model=List[CustomTopicResponse])
async def list_topics(
    active_only: bool = Query(True, description="Chỉ lấy topics đang active"),
    parent_id: Optional[int] = Query(None, description="Lọc theo parent (nested topics)"),
    search: Optional[str] = Query(None, description="Tìm kiếm theo tên"),
    db: Session = Depends(get_db)
):
    """
     Danh sách topics
    
    **Filters:**
    - `active_only`: Chỉ lấy topics active (default: true)
    - `parent_id`: Lấy sub-topics của parent
    - `search`: Tìm kiếm theo tên
    """
    query = db.query(CustomTopic)
    
    if active_only:
        query = query.filter(CustomTopic.is_active == True)
    
    if parent_id is not None:
        query = query.filter(CustomTopic.parent_id == parent_id)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(CustomTopic.name.ilike(search_pattern))
    
    topics = query.order_by(CustomTopic.display_order, CustomTopic.name).all()
    
    return topics


@router.get("/{topic_id}", response_model=CustomTopicDetailResponse)
async def get_topic(
    topic_id: int,
    db: Session = Depends(get_db)
):
    """
    🔍 Chi tiết 1 topic (kèm children và parent)
    """
    topic = db.query(CustomTopic).filter(CustomTopic.id == topic_id).first()
    if not topic:
        raise HTTPException(404, f"Topic {topic_id} không tồn tại")
    
    return topic


@router.put("/{topic_id}", response_model=CustomTopicResponse)
async def update_topic(
    topic_id: int,
    updates: CustomTopicUpdate,
    db: Session = Depends(get_db),
    api_key: str = Security(verify_api_key)
):
    """
    ✏️ Cập nhật topic
    
    **Note:** Sau khi update, nên chạy lại classification để cập nhật kết quả
    """
    topic = db.query(CustomTopic).filter(CustomTopic.id == topic_id).first()
    if not topic:
        raise HTTPException(404, f"Topic {topic_id} không tồn tại")
    
    # Update fields
    for key, value in updates.dict(exclude_unset=True).items():
        if key == 'name' and value:
            # Check duplicate name
            existing = db.query(CustomTopic).filter(
                CustomTopic.name == value,
                CustomTopic.id != topic_id
            ).first()
            if existing:
                raise HTTPException(400, f"Topic '{value}' đã tồn tại")
        
        setattr(topic, key, value)
    
    db.commit()
    db.refresh(topic)
    
    logger.info(f" Updated topic: {topic.name} (ID: {topic.id})")
    
    # Clear cache
    get_classifier().clear_cache()
    
    return topic


@router.delete("/{topic_id}")
async def delete_topic(
    topic_id: int,
    hard_delete: bool = Query(False, description="Xóa vĩnh viễn (mất data)"),
    db: Session = Depends(get_db),
    api_key: str = Security(verify_api_key)
):
    """
    🗑️ Xóa topic
    
    **Soft delete (default):** Set is_active = False  
    **Hard delete:** Xóa vĩnh viễn (mất tất cả mappings)
    """
    topic = db.query(CustomTopic).filter(CustomTopic.id == topic_id).first()
    if not topic:
        raise HTTPException(404, f"Topic {topic_id} không tồn tại")
    
    if hard_delete:
        # Delete mappings first
        db.query(ArticleCustomTopic).filter(ArticleCustomTopic.topic_id == topic_id).delete()
        db.delete(topic)
        db.commit()
        logger.warning(f"🗑️ Hard deleted topic: {topic.name} (ID: {topic_id})")
        return {"message": "Topic đã được xóa vĩnh viễn"}
    else:
        # Soft delete
        topic.is_active = False
        db.commit()
        logger.info(f" Soft deleted topic: {topic.name} (ID: {topic_id})")
        return {"message": "Topic đã được vô hiệu hóa"}


# ============================================
# CLASSIFICATION
# ============================================

@router.post("/classify", response_model=BulkClassificationResponse)
async def classify_articles(
    request: ClassifyArticlesRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    api_key: str = Security(verify_api_key)
):
    """
     Phân loại bài viết vào custom topics
    
    **Modes:**
    - `article_ids`: Phân loại specific articles
    - `all_unclassified`: Phân loại tất cả chưa có custom topic
    - `all_articles`: Phân loại lại tất cả (re-classify)
    
    **Methods:**
    - `keyword`: So khớp từ khóa (nhanh, độ chính xác trung bình)
    - `embedding`: Semantic similarity (chậm, chính xác cao)
    - `hybrid`: Kết hợp cả 2 (khuyên dùng)
    
    **Ví dụ:**
    ```json
    {
      "all_unclassified": true,
      "method": "hybrid",
      "save_results": true,
      "topic_ids": [1, 2, 3]
    }
    ```
    """
    start_time = time.time()
    
    # Get topics
    topic_query = db.query(CustomTopic).filter(CustomTopic.is_active == True)
    if request.topic_ids:
        topic_query = topic_query.filter(CustomTopic.id.in_(request.topic_ids))
    topics = topic_query.all()
    
    if not topics:
        raise HTTPException(400, "Không có topics nào để phân loại")
    
    # Get articles
    if request.all_articles:
        articles = db.query(Article).all()
    elif request.all_unclassified:
        # Lấy articles chưa có custom topic
        classified_ids = db.query(ArticleCustomTopic.article_id).distinct()
        articles = db.query(Article).filter(~Article.id.in_(classified_ids)).all()
    elif request.article_ids:
        articles = db.query(Article).filter(Article.id.in_(request.article_ids)).all()
    else:
        raise HTTPException(400, "Phải chỉ định article_ids hoặc all_unclassified hoặc all_articles")
    
    if not articles:
        raise HTTPException(400, "Không có articles nào để phân loại")
    
    logger.info(f" Classifying {len(articles)} articles into {len(topics)} topics using {request.method}")
    
    # Classify
    classifier = get_classifier()
    results = classifier.classify_articles_bulk(
        articles=articles,
        topics=topics,
        method=request.method,
        min_confidence_override=request.min_confidence
    )
    
    # Save results
    summary = {"saved": 0, "skipped": 0, "errors": 0}
    if request.save_results:
        summary = classifier.save_classification_results(db, results, save_logs=True)
    
    processing_time = int((time.time() - start_time) * 1000)
    
    logger.info(f" Classification completed in {processing_time}ms: {summary}")
    
    return BulkClassificationResponse(
        total_articles=len(articles),
        total_topics=len(topics),
        processing_time_ms=processing_time,
        results=results,
        summary=summary
    )


@router.get("/articles/{article_id}/topics", response_model=List[TopicClassificationResult])
async def get_article_topics(
    article_id: int,
    min_confidence: float = Query(0.0, ge=0, le=1, description="Lọc theo confidence"),
    db: Session = Depends(get_db)
):
    """
    📄 Lấy danh sách topics của 1 article
    """
    mappings = db.query(ArticleCustomTopic).join(CustomTopic).filter(
        ArticleCustomTopic.article_id == article_id,
        ArticleCustomTopic.confidence >= min_confidence,
        CustomTopic.is_active == True
    ).order_by(ArticleCustomTopic.confidence.desc()).all()
    
    results = []
    for mapping in mappings:
        result = TopicClassificationResult(
            topic_id=mapping.topic_id,
            topic_name=mapping.topic.name,
            confidence=mapping.confidence,
            method=ClassificationMethod(mapping.method),
            is_accepted=True
        )
        results.append(result)
    
    return results


@router.get("/topics/{topic_id}/articles", response_model=TopicWithArticlesResponse)
async def get_topic_articles(
    topic_id: int,
    min_confidence: float = Query(0.5, ge=0, le=1),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
     Lấy danh sách articles thuộc 1 topic
    """
    topic = db.query(CustomTopic).filter(CustomTopic.id == topic_id).first()
    if not topic:
        raise HTTPException(404, f"Topic {topic_id} không tồn tại")
    
    # Get mappings
    mappings = db.query(ArticleCustomTopic).join(Article).filter(
        ArticleCustomTopic.topic_id == topic_id,
        ArticleCustomTopic.confidence >= min_confidence
    ).order_by(
        ArticleCustomTopic.confidence.desc()
    ).offset(offset).limit(limit).all()
    
    articles = []
    for mapping in mappings:
        articles.append({
            "article_id": mapping.article_id,
            "title": mapping.article.title,
            "confidence": mapping.confidence,
            "method": mapping.method,
            "published_date": mapping.article.published_datetime,
            "classified_at": mapping.classified_at
        })
    
    total = db.query(ArticleCustomTopic).filter(
        ArticleCustomTopic.topic_id == topic_id,
        ArticleCustomTopic.confidence >= min_confidence
    ).count()
    
    return TopicWithArticlesResponse(
        topic_id=topic.id,
        topic_name=topic.name,
        total_articles=total,
        articles=articles
    )


# ============================================
# STATISTICS & OVERVIEW
# ============================================

@router.get("/stats/overview", response_model=ClassificationOverview)
async def get_classification_overview(db: Session = Depends(get_db)):
    """
     Tổng quan hệ thống phân loại
    """
    from sqlalchemy import func, distinct
    
    # Total topics
    total_topics = db.query(func.count(CustomTopic.id)).scalar()
    active_topics = db.query(func.count(CustomTopic.id)).filter(CustomTopic.is_active == True).scalar()
    
    # Total classified articles
    total_classified = db.query(func.count(distinct(ArticleCustomTopic.article_id))).scalar()
    
    # Total articles
    total_articles = db.query(func.count(Article.id)).scalar()
    total_unclassified = total_articles - total_classified
    
    # Avg topics per article
    avg_topics = db.query(
        func.avg(func.count(ArticleCustomTopic.id))
    ).group_by(ArticleCustomTopic.article_id).scalar() or 0.0
    
    # Method distribution
    methods = db.query(
        ArticleCustomTopic.method,
        func.count(ArticleCustomTopic.id)
    ).group_by(ArticleCustomTopic.method).all()
    method_dist = {method: count for method, count in methods}
    
    # Top topics
    top_topics_data = db.query(
        CustomTopic.id,
        CustomTopic.name,
        func.count(ArticleCustomTopic.article_id).label('count'),
        func.avg(ArticleCustomTopic.confidence).label('avg_conf')
    ).join(ArticleCustomTopic).group_by(
        CustomTopic.id, CustomTopic.name
    ).order_by(func.count(ArticleCustomTopic.article_id).desc()).limit(10).all()
    
    top_topics = []
    for topic_id, name, count, avg_conf in top_topics_data:
        top_topics.append({
            "topic_id": topic_id,
            "topic_name": name,
            "article_count": count,
            "avg_confidence": round(avg_conf, 3),
            "method_distribution": {},
            "recent_articles": []
        })
    
    return ClassificationOverview(
        total_topics=total_topics,
        active_topics=active_topics,
        total_classified_articles=total_classified,
        total_unclassified_articles=total_unclassified,
        avg_topics_per_article=round(avg_topics, 2),
        classification_methods=method_dist,
        top_topics=top_topics
    )


# ============================================
# TEMPLATES
# ============================================

@router.post("/templates", response_model=TopicTemplateResponse, status_code=201)
async def create_template(
    template: TopicTemplateCreate,
    db: Session = Depends(get_db),
    api_key: str = Security(verify_api_key)
):
    """
     Tạo template topics (để tái sử dụng)
    
    **Ví dụ:** Template "News Categories" với Politics, Economy, Sports, ...
    """
    db_template = TopicTemplate(**template.dict())
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    
    logger.info(f" Created template: {db_template.name}")
    
    return db_template


@router.get("/templates", response_model=List[TopicTemplateResponse])
async def list_templates(
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """ Danh sách templates"""
    query = db.query(TopicTemplate).filter(TopicTemplate.is_public == True)
    
    if category:
        query = query.filter(TopicTemplate.category == category)
    
    return query.order_by(TopicTemplate.usage_count.desc()).all()


@router.post("/templates/apply")
async def apply_template(
    request: ApplyTemplateRequest,
    db: Session = Depends(get_db),
    api_key: str = Security(verify_api_key)
):
    """
     Áp dụng template để tạo hàng loạt topics
    
    **Note:** Sẽ skip topics trùng tên (trừ khi override_existing=true)
    """
    template = db.query(TopicTemplate).filter(TopicTemplate.id == request.template_id).first()
    if not template:
        raise HTTPException(404, "Template không tồn tại")
    
    created = []
    skipped = []
    
    for topic_data in template.topics_data:
        # Check existing
        existing = db.query(CustomTopic).filter(CustomTopic.name == topic_data['name']).first()
        
        if existing and not request.override_existing:
            skipped.append(topic_data['name'])
            continue
        
        if existing and request.override_existing:
            # Update existing
            for key, value in topic_data.items():
                setattr(existing, key, value)
            created.append(existing.name)
        else:
            # Create new
            import re, unicodedata
            slug = unicodedata.normalize('NFKD', topic_data['name']).encode('ascii', 'ignore').decode('utf-8')
            slug = re.sub(r'[^\w\s-]', '', slug).strip().lower()
            slug = re.sub(r'[-\s]+', '-', slug)
            
            new_topic = CustomTopic(
                name=topic_data['name'],
                slug=slug,
                description=topic_data.get('description', ''),
                keywords=topic_data['keywords'],
                example_docs=topic_data.get('example_docs'),
                color=topic_data.get('color', '#3B82F6'),
                icon=topic_data.get('icon')
            )
            db.add(new_topic)
            created.append(new_topic.name)
    
    db.commit()
    
    # Update usage count
    template.usage_count += 1
    db.commit()
    
    logger.info(f" Applied template '{template.name}': created {len(created)}, skipped {len(skipped)}")
    
    return {
        "message": f"Created {len(created)} topics, skipped {len(skipped)}",
        "created": created,
        "skipped": skipped
    }
