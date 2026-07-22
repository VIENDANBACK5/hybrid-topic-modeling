"""
API Endpoints for Important Posts
Quản lý các bài viết báo chí đặc biệt quan trọng
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from app.core.database import get_db
from app.models.model_important_post import ImportantPost
from app.schemas.schema_important_post import (
    ImportantPostCreate,
    ImportantPostUpdate,
    ImportantPostResponse,
    ImportantPostListResponse,
    ImportantPostStatsResponse
)

router = APIRouter(prefix="/api/important-posts", tags=["Important Posts"])
logger = logging.getLogger(__name__)


# =============================================================================
# CRUD OPERATIONS
# =============================================================================

@router.post("/", response_model=ImportantPostResponse, status_code=201)
def create_important_post(
    post: ImportantPostCreate,
    db: Session = Depends(get_db)
):
    """
    Tạo mới một bài viết quan trọng
    
    Args:
        post: Dữ liệu bài viết
        
    Returns:
        ImportantPostResponse: Bài viết đã tạo
    """
    # Check if URL already exists
    existing = db.query(ImportantPost).filter(ImportantPost.url == post.url).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Post with URL already exists: {post.url}")
    
    # Create new post
    db_post = ImportantPost(**post.model_dump())
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    
    logger.info(f"Created important post: {db_post.id} - {db_post.title[:50]}")
    return db_post


@router.get("/{post_id}", response_model=ImportantPostResponse)
def get_important_post(
    post_id: int,
    db: Session = Depends(get_db)
):
    """
    Lấy chi tiết một bài viết theo ID
    
    Args:
        post_id: ID của bài viết
        
    Returns:
        ImportantPostResponse: Chi tiết bài viết
    """
    post = db.query(ImportantPost).filter(ImportantPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail=f"Post not found: {post_id}")
    
    return post


@router.put("/{post_id}", response_model=ImportantPostResponse)
def update_important_post(
    post_id: int,
    post_update: ImportantPostUpdate,
    db: Session = Depends(get_db)
):
    """
    Cập nhật một bài viết
    
    Args:
        post_id: ID của bài viết
        post_update: Dữ liệu cần cập nhật
        
    Returns:
        ImportantPostResponse: Bài viết đã cập nhật
    """
    db_post = db.query(ImportantPost).filter(ImportantPost.id == post_id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail=f"Post not found: {post_id}")
    
    # Update fields
    update_data = post_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_post, field, value)
    
    db_post.updated_at = datetime.now().timestamp()
    db.commit()
    db.refresh(db_post)
    
    logger.info(f"Updated important post: {post_id}")
    return db_post


@router.delete("/{post_id}", status_code=204)
def delete_important_post(
    post_id: int,
    db: Session = Depends(get_db)
):
    """
    Xóa một bài viết
    
    Args:
        post_id: ID của bài viết
    """
    db_post = db.query(ImportantPost).filter(ImportantPost.id == post_id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail=f"Post not found: {post_id}")
    
    db.delete(db_post)
    db.commit()
    
    logger.info(f"Deleted important post: {post_id}")


# =============================================================================
# LIST & SEARCH OPERATIONS
# =============================================================================

@router.get("/", response_model=ImportantPostListResponse)
def list_important_posts(
    page: int = Query(1, ge=1, description="Số trang"),
    page_size: int = Query(10, ge=1, le=100, description="Số bài viết mỗi trang"),
    type_newspaper: Optional[str] = Query(None, description="Lọc theo loại báo (medical, economic, ...)"),
    data_type: Optional[str] = Query(None, description="Lọc theo loại dữ liệu (newspaper, social, ...)"),
    dvhc: Optional[str] = Query(None, description="Lọc theo đơn vị hành chính"),
    is_featured: Optional[int] = Query(None, description="Lọc bài nổi bật (1) hay không (0)"),
    min_importance: Optional[float] = Query(None, ge=0, le=10, description="Điểm quan trọng tối thiểu"),
    search: Optional[str] = Query(None, description="Tìm kiếm trong title hoặc content"),
    sort_by: str = Query("id", description="Sắp xếp theo field (id, created_at, importance_score, ...)"),
    order: str = Query("desc", regex="^(asc|desc)$", description="Thứ tự sắp xếp"),
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách bài viết quan trọng với filter và pagination
    
    Args:
        page: Số trang (bắt đầu từ 1)
        page_size: Số bài viết mỗi trang
        type_newspaper: Lọc theo loại báo
        data_type: Lọc theo loại dữ liệu
        dvhc: Lọc theo đơn vị hành chính
        is_featured: Lọc bài nổi bật
        min_importance: Điểm quan trọng tối thiểu
        search: Từ khóa tìm kiếm
        sort_by: Trường sắp xếp
        order: Thứ tự sắp xếp (asc/desc)
        
    Returns:
        ImportantPostListResponse: Danh sách bài viết với pagination
    """
    # Build query
    query = db.query(ImportantPost)
    
    # Apply filters
    if type_newspaper:
        query = query.filter(ImportantPost.type_newspaper == type_newspaper)
    
    if data_type:
        query = query.filter(ImportantPost.data_type == data_type)
    
    if dvhc:
        query = query.filter(ImportantPost.dvhc == dvhc)
    
    if is_featured is not None:
        query = query.filter(ImportantPost.is_featured == is_featured)
    
    if min_importance is not None:
        query = query.filter(ImportantPost.importance_score >= min_importance)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                ImportantPost.title.ilike(search_pattern),
                ImportantPost.content.ilike(search_pattern)
            )
        )
    
    # Count total
    total = query.count()
    
    # Apply sorting
    sort_column = getattr(ImportantPost, sort_by, ImportantPost.id)
    if order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Apply pagination
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()
    
    total_pages = (total + page_size - 1) // page_size
    
    return ImportantPostListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/by-type/{type_newspaper}", response_model=ImportantPostListResponse)
def get_posts_by_type(
    type_newspaper: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    sort_by: str = Query("id"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách bài viết theo loại báo (medical, economic, ...)
    
    Args:
        type_newspaper: Loại báo
        page: Số trang
        page_size: Số bài viết mỗi trang
        sort_by: Trường sắp xếp
        order: Thứ tự sắp xếp
        
    Returns:
        ImportantPostListResponse: Danh sách bài viết
    """
    return list_important_posts(
        page=page,
        page_size=page_size,
        type_newspaper=type_newspaper,
        data_type=None,
        dvhc=None,
        is_featured=None,
        min_importance=None,
        search=None,
        sort_by=sort_by,
        order=order,
        db=db
    )


# =============================================================================
# STATISTICS & ANALYTICS
# =============================================================================

@router.get("/stats/overview", response_model=ImportantPostStatsResponse)
def get_posts_statistics(
    type_newspaper: Optional[str] = Query(None, description="Lọc theo loại báo"),
    limit_recent: int = Query(5, ge=1, le=50, description="Số bài viết gần nhất"),
    db: Session = Depends(get_db)
):
    """
    Lấy thống kê tổng quan về các bài viết quan trọng
    
    Args:
        type_newspaper: Lọc theo loại báo
        limit_recent: Số bài viết gần nhất cần lấy
        
    Returns:
        ImportantPostStatsResponse: Thống kê tổng quan
    """
    # Base query
    base_query = db.query(ImportantPost)
    if type_newspaper:
        base_query = base_query.filter(ImportantPost.type_newspaper == type_newspaper)
    
    # Total posts
    total_posts = base_query.count()
    
    # By type
    by_type_query = db.query(
        ImportantPost.type_newspaper,
        func.count(ImportantPost.id).label('count')
    )
    if type_newspaper:
        by_type_query = by_type_query.filter(ImportantPost.type_newspaper == type_newspaper)
    
    by_type = {row.type_newspaper or 'unknown': row.count 
               for row in by_type_query.group_by(ImportantPost.type_newspaper).all()}
    
    # By featured
    by_featured_query = db.query(
        ImportantPost.is_featured,
        func.count(ImportantPost.id).label('count')
    )
    if type_newspaper:
        by_featured_query = by_featured_query.filter(ImportantPost.type_newspaper == type_newspaper)
    
    by_featured = {('featured' if row.is_featured == 1 else 'normal'): row.count 
                   for row in by_featured_query.group_by(ImportantPost.is_featured).all()}
    
    # Average importance score
    avg_score_result = base_query.filter(ImportantPost.importance_score.isnot(None))\
        .with_entities(func.avg(ImportantPost.importance_score)).scalar()
    avg_importance_score = float(avg_score_result) if avg_score_result else None
    
    # Recent posts
    recent_posts = base_query.order_by(ImportantPost.created_at.desc()).limit(limit_recent).all()
    
    return ImportantPostStatsResponse(
        total_posts=total_posts,
        by_type=by_type,
        by_featured=by_featured,
        avg_importance_score=avg_importance_score,
        recent_posts=recent_posts
    )


# =============================================================================
# BULK OPERATIONS
# =============================================================================

@router.post("/bulk/import", status_code=201)
def bulk_import_posts(
    posts: List[ImportantPostCreate],
    skip_duplicates: bool = Query(True, description="Bỏ qua các URL đã tồn tại"),
    db: Session = Depends(get_db)
):
    """
    Import hàng loạt bài viết từ API nguồn
    
    Args:
        posts: Danh sách bài viết cần import
        skip_duplicates: Bỏ qua các URL đã tồn tại
        
    Returns:
        Dict với thông tin import
    """
    created_count = 0
    skipped_count = 0
    error_count = 0
    errors = []
    
    for post in posts:
        try:
            # Check if exists
            existing = db.query(ImportantPost).filter(ImportantPost.url == post.url).first()
            if existing:
                if skip_duplicates:
                    skipped_count += 1
                    continue
                else:
                    raise ValueError(f"URL already exists: {post.url}")
            
            # Create post
            db_post = ImportantPost(**post.model_dump())
            db.add(db_post)
            
            # Commit mỗi bài để tránh rollback hết khi có lỗi
            try:
                db.commit()
                created_count += 1
            except Exception as commit_error:
                db.rollback()
                error_count += 1
                errors.append(f"Error committing URL {post.url}: {str(commit_error)}")
                logger.error(f"Error committing post: {commit_error}")
            
        except Exception as e:
            error_count += 1
            errors.append(f"Error with URL {post.url}: {str(e)}")
            logger.error(f"Error importing post: {e}")
    
    logger.info(f"Bulk import: {created_count} created, {skipped_count} skipped, {error_count} errors")
    
    return {
        "created": created_count,
        "skipped": skipped_count,
        "errors": error_count,
        "error_details": errors[:10]  # Return first 10 errors
    }


@router.put("/bulk/update-featured")
def bulk_update_featured(
    post_ids: List[int],
    is_featured: int = Query(..., ge=0, le=1),
    db: Session = Depends(get_db)
):
    """
    Cập nhật cờ featured cho nhiều bài viết
    
    Args:
        post_ids: Danh sách ID bài viết
        is_featured: Giá trị featured (0 hoặc 1)
        
    Returns:
        Dict với số bài viết đã cập nhật
    """
    updated = db.query(ImportantPost)\
        .filter(ImportantPost.id.in_(post_ids))\
        .update(
            {ImportantPost.is_featured: is_featured},
            synchronize_session=False
        )
    
    db.commit()
    
    logger.info(f"Bulk updated featured status for {updated} posts")
    
    return {
        "updated": updated,
        "is_featured": is_featured
    }
