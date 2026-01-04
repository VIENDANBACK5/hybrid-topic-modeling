"""
Human-in-the-Loop (HITL) API
Provides endpoints for human review and approval of ML outputs
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, func
from app.core.database import get_db
from app.models.model_base import Base
import logging
import json

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================
# Database Models for HITL
# ============================================

class TopicReview(Base):
    """Topic review/approval records"""
    __tablename__ = "topic_reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, index=True)
    original_label = Column(String(255))
    suggested_label = Column(String(255))
    final_label = Column(String(255))
    original_description = Column(Text)
    final_description = Column(Text)
    keywords = Column(JSON)
    status = Column(String(50), default="pending")  # pending, approved, rejected, merged
    reviewer = Column(String(100))
    review_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime)
    merged_into = Column(Integer, nullable=True)  # If merged, target topic_id


class EntityReview(Base):
    """Entity review/approval records"""
    __tablename__ = "entity_reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    entity_text = Column(String(255), index=True)
    entity_type = Column(String(50))  # PERSON, ORG, LOCATION
    canonical_form = Column(String(255))  # Standardized form
    status = Column(String(50), default="pending")
    reviewer = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime)


# ============================================
# Request/Response Models
# ============================================

class TopicReviewRequest(BaseModel):
    """Request to submit topic for review"""
    topic_id: int
    original_label: str
    suggested_label: Optional[str] = None
    original_description: Optional[str] = None
    keywords: Optional[List[str]] = None


class TopicApprovalRequest(BaseModel):
    """Request to approve/reject topic"""
    final_label: str
    final_description: Optional[str] = None
    status: str = "approved"  # approved, rejected, merged
    review_notes: Optional[str] = None
    reviewer: str = "anonymous"
    merged_into: Optional[int] = None


class EntityReviewRequest(BaseModel):
    """Request to review entity"""
    entity_text: str
    entity_type: str
    canonical_form: Optional[str] = None


class EntityApprovalRequest(BaseModel):
    """Request to approve entity canonical form"""
    canonical_form: str
    status: str = "approved"
    reviewer: str = "anonymous"


class ReviewStats(BaseModel):
    """Review statistics"""
    pending_topics: int
    approved_topics: int
    rejected_topics: int
    merged_topics: int
    pending_entities: int
    approved_entities: int


# ============================================
# Topic Review Endpoints
# ============================================

@router.post("/topics/submit")
async def submit_topic_for_review(
    request: TopicReviewRequest,
    db: Session = Depends(get_db)
):
    """
    📝 Submit topic for human review
    
    Call this after TopicGPT generates labels to queue for human approval
    """
    try:
        review = TopicReview(
            topic_id=request.topic_id,
            original_label=request.original_label,
            suggested_label=request.suggested_label or request.original_label,
            original_description=request.original_description,
            keywords=request.keywords,
            status="pending"
        )
        db.add(review)
        db.commit()
        db.refresh(review)
        
        return {
            "status": "submitted",
            "review_id": review.id,
            "message": "Topic submitted for review"
        }
    except Exception as e:
        logger.error(f"Submit review error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topics/pending")
async def get_pending_topics(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    📋 Get pending topic reviews
    """
    try:
        reviews = db.query(TopicReview).filter(
            TopicReview.status == "pending"
        ).order_by(TopicReview.created_at.desc()).limit(limit).all()
        
        return {
            "count": len(reviews),
            "reviews": [
                {
                    "id": r.id,
                    "topic_id": r.topic_id,
                    "original_label": r.original_label,
                    "suggested_label": r.suggested_label,
                    "original_description": r.original_description,
                    "keywords": r.keywords,
                    "created_at": r.created_at.isoformat() if r.created_at else None
                }
                for r in reviews
            ]
        }
    except Exception as e:
        logger.error(f"Get pending error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/topics/{review_id}/approve")
async def approve_topic(
    review_id: int,
    request: TopicApprovalRequest,
    db: Session = Depends(get_db)
):
    """
    ✅ Approve or reject topic review
    
    Args:
        review_id: ID of the review
        request: Approval details
    """
    try:
        review = db.query(TopicReview).filter(TopicReview.id == review_id).first()
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        
        review.final_label = request.final_label
        review.final_description = request.final_description
        review.status = request.status
        review.review_notes = request.review_notes
        review.reviewer = request.reviewer
        review.reviewed_at = datetime.utcnow()
        
        if request.merged_into:
            review.merged_into = request.merged_into
            review.status = "merged"
        
        db.commit()
        
        # Update the actual topic if approved
        if request.status == "approved":
            # TODO: Update topic in topic model/database
            pass
        
        return {
            "status": "updated",
            "review_id": review_id,
            "final_status": review.status
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Approve error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topics/all")
async def get_all_topic_reviews(
    status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    📊 Get all topic reviews with optional status filter
    """
    try:
        query = db.query(TopicReview)
        if status:
            query = query.filter(TopicReview.status == status)
        
        reviews = query.order_by(TopicReview.created_at.desc()).limit(limit).all()
        
        return {
            "count": len(reviews),
            "reviews": [
                {
                    "id": r.id,
                    "topic_id": r.topic_id,
                    "original_label": r.original_label,
                    "suggested_label": r.suggested_label,
                    "final_label": r.final_label,
                    "status": r.status,
                    "reviewer": r.reviewer,
                    "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None
                }
                for r in reviews
            ]
        }
    except Exception as e:
        logger.error(f"Get all reviews error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Entity Review Endpoints
# ============================================

@router.post("/entities/submit")
async def submit_entity_for_review(
    request: EntityReviewRequest,
    db: Session = Depends(get_db)
):
    """
    📝 Submit entity for canonicalization review
    """
    try:
        # Check if already exists
        existing = db.query(EntityReview).filter(
            EntityReview.entity_text == request.entity_text,
            EntityReview.entity_type == request.entity_type
        ).first()
        
        if existing:
            return {
                "status": "exists",
                "review_id": existing.id,
                "canonical_form": existing.canonical_form
            }
        
        review = EntityReview(
            entity_text=request.entity_text,
            entity_type=request.entity_type,
            canonical_form=request.canonical_form or request.entity_text,
            status="pending"
        )
        db.add(review)
        db.commit()
        db.refresh(review)
        
        return {
            "status": "submitted",
            "review_id": review.id
        }
    except Exception as e:
        logger.error(f"Submit entity error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/pending")
async def get_pending_entities(
    entity_type: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    📋 Get pending entity reviews
    """
    try:
        query = db.query(EntityReview).filter(EntityReview.status == "pending")
        if entity_type:
            query = query.filter(EntityReview.entity_type == entity_type)
        
        reviews = query.order_by(EntityReview.created_at.desc()).limit(limit).all()
        
        return {
            "count": len(reviews),
            "reviews": [
                {
                    "id": r.id,
                    "entity_text": r.entity_text,
                    "entity_type": r.entity_type,
                    "canonical_form": r.canonical_form,
                    "created_at": r.created_at.isoformat() if r.created_at else None
                }
                for r in reviews
            ]
        }
    except Exception as e:
        logger.error(f"Get pending entities error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/entities/{review_id}/approve")
async def approve_entity(
    review_id: int,
    request: EntityApprovalRequest,
    db: Session = Depends(get_db)
):
    """
    ✅ Approve entity canonical form
    """
    try:
        review = db.query(EntityReview).filter(EntityReview.id == review_id).first()
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        
        review.canonical_form = request.canonical_form
        review.status = request.status
        review.reviewer = request.reviewer
        review.reviewed_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "status": "updated",
            "review_id": review_id,
            "canonical_form": review.canonical_form
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Approve entity error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Statistics & Bulk Operations
# ============================================

@router.get("/stats", response_model=ReviewStats)
async def get_review_stats(db: Session = Depends(get_db)):
    """
    📊 Get review statistics
    """
    try:
        pending_topics = db.query(TopicReview).filter(TopicReview.status == "pending").count()
        approved_topics = db.query(TopicReview).filter(TopicReview.status == "approved").count()
        rejected_topics = db.query(TopicReview).filter(TopicReview.status == "rejected").count()
        merged_topics = db.query(TopicReview).filter(TopicReview.status == "merged").count()
        
        pending_entities = db.query(EntityReview).filter(EntityReview.status == "pending").count()
        approved_entities = db.query(EntityReview).filter(EntityReview.status == "approved").count()
        
        return ReviewStats(
            pending_topics=pending_topics,
            approved_topics=approved_topics,
            rejected_topics=rejected_topics,
            merged_topics=merged_topics,
            pending_entities=pending_entities,
            approved_entities=approved_entities
        )
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/topics/bulk-approve")
async def bulk_approve_topics(
    review_ids: List[int],
    reviewer: str = "bulk",
    db: Session = Depends(get_db)
):
    """
    ✅ Bulk approve multiple topics
    """
    try:
        updated = 0
        for review_id in review_ids:
            review = db.query(TopicReview).filter(TopicReview.id == review_id).first()
            if review and review.status == "pending":
                review.final_label = review.suggested_label
                review.status = "approved"
                review.reviewer = reviewer
                review.reviewed_at = datetime.utcnow()
                updated += 1
        
        db.commit()
        
        return {
            "status": "completed",
            "updated": updated,
            "total": len(review_ids)
        }
    except Exception as e:
        logger.error(f"Bulk approve error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export")
async def export_approved_labels(
    format: str = "json",
    db: Session = Depends(get_db)
):
    """
    📤 Export approved labels for training
    
    Use this to create training data for fine-tuning
    """
    try:
        # Get approved topic reviews
        topics = db.query(TopicReview).filter(TopicReview.status == "approved").all()
        
        # Get approved entity reviews
        entities = db.query(EntityReview).filter(EntityReview.status == "approved").all()
        
        data = {
            "exported_at": datetime.utcnow().isoformat(),
            "topics": [
                {
                    "topic_id": t.topic_id,
                    "original_label": t.original_label,
                    "final_label": t.final_label,
                    "keywords": t.keywords
                }
                for t in topics
            ],
            "entities": [
                {
                    "entity_text": e.entity_text,
                    "entity_type": e.entity_type,
                    "canonical_form": e.canonical_form
                }
                for e in entities
            ]
        }
        
        return data
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
