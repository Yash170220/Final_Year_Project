"""Matching API endpoints"""
import logging
from typing import Dict, List
from uuid import UUID
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.common.database import get_db
from src.common.models import Upload, MatchedIndicator
from src.common.schemas import MatchingReviewRequest, ErrorResponse
from src.matching.service import MatchingService, REVIEW_THRESHOLD
from src.matching.rule_matcher import RuleBasedMatcher
from src.matching.llm_matcher import LLMMatcher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/matching", tags=["matching"])

# Cache matchers to avoid recreation on every request
_rule_matcher = None
_llm_matcher = None


@lru_cache(maxsize=1)
def get_rule_matcher() -> RuleBasedMatcher:
    """Get cached rule matcher instance"""
    global _rule_matcher
    if _rule_matcher is None:
        _rule_matcher = RuleBasedMatcher("data/validation-rules/synonym_dictionary.json")
    return _rule_matcher


@lru_cache(maxsize=1)
def get_llm_matcher() -> LLMMatcher:
    """Get cached LLM matcher instance"""
    global _llm_matcher
    if _llm_matcher is None:
        rule_matcher = get_rule_matcher()
        standard_indicators = [
            data["canonical_name"]
            for data in rule_matcher.indicators.values()
        ]
        _llm_matcher = LLMMatcher(standard_indicators)
    return _llm_matcher


def get_matching_service(db: Session = Depends(get_db)) -> MatchingService:
    """Dependency to create matching service with cached matchers"""
    rule_matcher = get_rule_matcher()
    llm_matcher = get_llm_matcher()
    return MatchingService(rule_matcher, llm_matcher, db, actor="api")


@router.post(
    "/process/{upload_id}",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Upload not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Processing error"}
    },
    summary="Process matching for uploaded file",
    description="Trigger entity matching for all headers in uploaded file"
)
async def process_matching(
    upload_id: UUID,
    db: Session = Depends(get_db),
    service: MatchingService = Depends(get_matching_service)
):
    """Process matching for uploaded file"""
    logger.info(f"Processing matching for upload: {upload_id}")
    
    # Get upload record
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload {upload_id} not found"
        )
    
    # Get headers from metadata
    metadata = upload.metadata or {}
    headers = metadata.get("column_names", [])
    
    if not headers:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No headers found in upload metadata"
        )
    
    try:
        # Process matching
        results = service.match_headers(upload_id, headers)
        
        # Calculate summary
        total = len(results)
        needs_review = sum(1 for r in results if r.requires_review)
        auto_approved = total - needs_review
        avg_confidence = sum(r.confidence for r in results) / total if total > 0 else 0.0
        
        return {
            "upload_id": str(upload_id),
            "summary": {
                "total": total,
                "auto_approved": auto_approved,
                "needs_review": needs_review,
                "avg_confidence": round(avg_confidence, 3)
            },
            "message": f"Matched {total} headers successfully"
        }
        
    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Validation error"
        )
    except Exception as e:
        logger.exception(f"Error processing matching: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/results/{upload_id}",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Upload not found"}
    },
    summary="Get matching results",
    description="Get all matching results for an upload"
)
async def get_matching_results(
    upload_id: UUID,
    db: Session = Depends(get_db)
):
    """Get all matching results for an upload"""
    logger.info(f"Fetching matching results for upload: {upload_id}")
    
    # Verify upload exists
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload {upload_id} not found"
        )
    
    # Get all matches
    matches = db.query(MatchedIndicator).filter(
        MatchedIndicator.upload_id == upload_id
    ).all()
    
    results = []
    for match in matches:
        results.append({
            "indicator_id": str(match.id),
            "original_header": match.original_header,
            "matched_indicator": match.matched_indicator,
            "confidence": round(match.confidence_score, 3),
            "method": match.matching_method.value,
            "requires_review": match.confidence_score < REVIEW_THRESHOLD,
            "reviewed": match.reviewed,
            "notes": match.reviewer_notes
        })
    
    return {
        "upload_id": str(upload_id),
        "total_matches": len(results),
        "results": results
    }


@router.get(
    "/review-queue/{upload_id}",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Upload not found"}
    },
    summary="Get review queue",
    description="Get headers requiring manual review (confidence < 0.85)"
)
async def get_review_queue(
    upload_id: UUID,
    db: Session = Depends(get_db),
    service: MatchingService = Depends(get_matching_service)
):
    """Get review queue for an upload"""
    logger.info(f"Fetching review queue for upload: {upload_id}")
    
    # Verify upload exists
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload {upload_id} not found"
        )
    
    # Get review queue
    review_items = service.get_review_queue(upload_id)
    
    results = []
    for item in review_items:
        results.append({
            "indicator_id": str(item.indicator_id),
            "original_header": item.original_header,
            "matched_indicator": item.matched_indicator,
            "confidence": round(item.confidence, 3),
            "method": item.method,
            "reasoning": item.reasoning
        })
    
    return {
        "upload_id": str(upload_id),
        "review_count": len(results),
        "items": results
    }


@router.post(
    "/review",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Indicator not found"},
        422: {"model": ErrorResponse, "description": "Validation error"}
    },
    summary="Review and approve/correct match",
    description="Submit review for a matched indicator"
)
async def review_match(
    request: MatchingReviewRequest,
    db: Session = Depends(get_db),
    service: MatchingService = Depends(get_matching_service)
):
    """Review and approve or correct a match"""
    logger.info(f"Reviewing match: {request.indicator_id}")
    
    # Check existence first
    match = db.query(MatchedIndicator).filter(
        MatchedIndicator.id == request.indicator_id
    ).first()
    
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )
    
    try:
        # Approve/correct match
        service.approve_match(
            indicator_id=request.indicator_id,
            approved=request.approved,
            corrected_match=request.corrected_match,
            notes=request.notes
        )
        
        # Refresh to get updated data
        db.refresh(match)
        
        return {
            "indicator_id": str(match.id),
            "original_header": match.original_header,
            "matched_indicator": match.matched_indicator,
            "confidence": round(match.confidence_score, 3),
            "reviewed": match.reviewed,
            "notes": match.reviewer_notes,
            "message": "Review submitted successfully"
        }
        
    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Validation error"
        )
    except Exception as e:
        logger.exception(f"Error reviewing match: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/stats/{upload_id}",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Upload not found"}
    },
    summary="Get matching statistics",
    description="Get detailed statistics for matching results"
)
async def get_matching_stats(
    upload_id: UUID,
    db: Session = Depends(get_db),
    service: MatchingService = Depends(get_matching_service)
):
    """Get matching statistics for an upload"""
    logger.info(f"Fetching matching stats for upload: {upload_id}")
    
    # Verify upload exists
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload {upload_id} not found"
        )
    
    # Get statistics
    stats = service.get_matching_stats(upload_id)
    
    # Calculate percentages
    total = stats["total"]
    needs_review = stats["requires_review"]
    auto_approved = total - needs_review
    
    if total > 0:
        auto_approved_pct = auto_approved / total * 100
        needs_review_pct = needs_review / total * 100
    else:
        auto_approved_pct = 0.0
        needs_review_pct = 0.0
    
    return {
        "upload_id": str(upload_id),
        "statistics": {
            "total_headers": total,
            "auto_approved": auto_approved,
            "auto_approved_pct": round(auto_approved_pct, 1),
            "needs_review": needs_review,
            "needs_review_pct": round(needs_review_pct, 1),
            "reviewed": stats["reviewed"],
            "avg_confidence": round(stats["avg_confidence"], 3),
            "by_method": stats["by_method"]
        }
    }


@router.post(
    "/rematch/{indicator_id}",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Indicator not found"}
    },
    summary="Rematch a header",
    description="Re-run matching for a single header"
)
async def rematch_header(
    indicator_id: UUID,
    db: Session = Depends(get_db),
    service: MatchingService = Depends(get_matching_service)
):
    """Rematch a single header"""
    logger.info(f"Rematching indicator: {indicator_id}")
    
    try:
        result = service.rematch_header(indicator_id)
        
        return {
            "indicator_id": str(indicator_id),
            "original_header": result.original_header,
            "matched_indicator": result.matched_indicator,
            "confidence": round(result.confidence, 3),
            "method": result.method,
            "requires_review": result.requires_review,
            "message": "Rematch completed successfully"
        }
        
    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )
    except Exception as e:
        logger.exception(f"Error rematching: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
