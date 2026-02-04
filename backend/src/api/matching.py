"""Matching API endpoints"""
import json
import logging
from typing import Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.common.database import get_db
from src.common.models import Upload, MatchedIndicator
from src.common.schemas import MatchingReviewRequest, ErrorResponse
from src.matching.service import MatchingService
from src.matching.rule_matcher import RuleBasedMatcher
from src.matching.llm_matcher import LLMMatcher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/matching", tags=["matching"])


def get_matching_service(db: Session = Depends(get_db)) -> MatchingService:
    """Dependency to create matching service"""
    # Load synonym dictionary
    rule_matcher = RuleBasedMatcher("data/validation-rules/synonym_dictionary.json")
    
    # Get standard indicators from dictionary
    standard_indicators = [
        data["canonical_name"]
        for data in rule_matcher.indicators.values()
    ]
    
    # Create LLM matcher
    llm_matcher = LLMMatcher(standard_indicators)
    
    # Create service
    return MatchingService(rule_matcher, llm_matcher, db)


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
        auto_approved = sum(1 for r in results if not r.requires_review)
        needs_review = sum(1 for r in results if r.requires_review)
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
        
    except Exception as e:
        logger.exception(f"Error processing matching: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing matching: {str(e)}"
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
            "requires_review": not match.reviewed,
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
    
    # Get sample data context (first 5 values) from metadata
    metadata = upload.metadata or {}
    
    results = []
    for item in review_items:
        # Try to get sample values for this header
        sample_values = []
        if "column_names" in metadata:
            try:
                col_index = metadata["column_names"].index(item.original_header)
                # This would need actual data - simplified for now
                sample_values = ["Sample data not available"]
            except (ValueError, KeyError):
                pass
        
        results.append({
            "indicator_id": str(item.indicator_id),
            "original_header": item.original_header,
            "matched_indicator": item.matched_indicator,
            "confidence": round(item.confidence, 3),
            "method": item.method,
            "reasoning": item.reasoning,
            "sample_values": sample_values
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
    
    try:
        # Approve/correct match
        service.approve_match(
            indicator_id=request.indicator_id,
            approved=request.approved,
            corrected_match=request.corrected_match,
            notes=request.notes
        )
        
        # Get updated match
        match = db.query(MatchedIndicator).filter(
            MatchedIndicator.id == request.indicator_id
        ).first()
        
        if not match:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Indicator {request.indicator_id} not found"
            )
        
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.exception(f"Error reviewing match: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reviewing match: {str(e)}"
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
    if total > 0:
        auto_approved_pct = (stats["total"] - stats["requires_review"]) / total * 100
        needs_review_pct = stats["requires_review"] / total * 100
    else:
        auto_approved_pct = 0.0
        needs_review_pct = 0.0
    
    return {
        "upload_id": str(upload_id),
        "statistics": {
            "total_headers": total,
            "auto_approved": stats["total"] - stats["requires_review"],
            "auto_approved_pct": round(auto_approved_pct, 1),
            "needs_review": stats["requires_review"],
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.exception(f"Error rematching: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rematching: {str(e)}"
        )
