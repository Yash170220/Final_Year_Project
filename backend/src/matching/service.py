"""Matching service orchestrating rule-based and LLM matching"""
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.common.models import MatchedIndicator, MatchingMethod, AuditLog, AuditAction
from src.matching.rule_matcher import RuleBasedMatcher
from src.matching.llm_matcher import LLMMatcher

logger = logging.getLogger(__name__)


class MatchingResult:
    """Result of matching operation"""
    def __init__(
        self,
        original_header: str,
        matched_indicator: str,
        confidence: float,
        method: str,
        requires_review: bool,
        indicator_id: Optional[UUID] = None,
        unit: Optional[str] = None,
        category: Optional[str] = None,
        reasoning: Optional[str] = None
    ):
        self.original_header = original_header
        self.matched_indicator = matched_indicator
        self.confidence = confidence
        self.method = method
        self.requires_review = requires_review
        self.indicator_id = indicator_id
        self.unit = unit
        self.category = category
        self.reasoning = reasoning

    def __repr__(self):
        return f"<MatchingResult({self.original_header} → {self.matched_indicator}, {self.confidence:.2f})>"


class MatchingService:
    """Service for matching headers to standard indicators"""

    def __init__(
        self,
        rule_matcher: RuleBasedMatcher,
        llm_matcher: LLMMatcher,
        db: Session
    ):
        """Initialize matching service"""
        self.rule_matcher = rule_matcher
        self.llm_matcher = llm_matcher
        self.db = db
        self.confidence_threshold = 0.80
        self.review_threshold = 0.85

    def match_headers(
        self,
        upload_id: UUID,
        headers: List[str]
    ) -> List[MatchingResult]:
        """Match all headers for an upload"""
        logger.info(f"Matching {len(headers)} headers for upload {upload_id}")
        
        results = []
        
        for header in headers:
            try:
                # Get best match
                result = self.get_best_match(header)
                
                if result:
                    # Save to database
                    indicator_id = self.save_match(upload_id, header, result)
                    result.indicator_id = indicator_id
                    results.append(result)
                    
                    logger.info(
                        f"Matched '{header}' → '{result.matched_indicator}' "
                        f"({result.confidence:.2f}, {result.method})"
                    )
                else:
                    logger.warning(f"No match found for header: {header}")
                    
            except Exception as e:
                logger.error(f"Error matching header '{header}': {e}")
                continue
        
        # Log audit trail
        audit = AuditLog(
            entity_id=upload_id,
            entity_type="uploads",
            action=AuditAction.UPDATED,
            actor="system",
            timestamp=datetime.utcnow(),
            changes={
                "matched_headers": len(results),
                "requires_review": sum(1 for r in results if r.requires_review)
            }
        )
        self.db.add(audit)
        self.db.commit()
        
        logger.info(
            f"Matching complete: {len(results)}/{len(headers)} matched, "
            f"{sum(1 for r in results if r.requires_review)} require review"
        )
        
        return results

    def get_best_match(self, header: str) -> Optional[MatchingResult]:
        """Get best match using rule-based then LLM fallback"""
        logger.debug(f"Finding best match for: {header}")
        
        # Try rule-based matching first
        rule_result = self.rule_matcher.match(header)
        
        if rule_result and rule_result.confidence >= self.confidence_threshold:
            logger.debug(f"Rule-based match accepted: {rule_result.confidence:.2f}")
            return MatchingResult(
                original_header=header,
                matched_indicator=rule_result.canonical_name,
                confidence=rule_result.confidence,
                method=rule_result.method,
                requires_review=rule_result.confidence < self.review_threshold,
                unit=rule_result.unit,
                category=rule_result.category
            )
        
        # Fallback to LLM matching
        logger.debug("Rule-based match insufficient, trying LLM...")
        llm_result = self.llm_matcher.match(header)
        
        if llm_result and llm_result.confidence >= 0.7:
            logger.debug(f"LLM match accepted: {llm_result.confidence:.2f}")
            return MatchingResult(
                original_header=header,
                matched_indicator=llm_result.canonical_name,
                confidence=llm_result.confidence,
                method=llm_result.method,
                requires_review=llm_result.confidence < self.review_threshold,
                reasoning=llm_result.reasoning
            )
        
        # No good match found
        logger.debug(f"No sufficient match found for: {header}")
        return None

    def save_match(
        self,
        upload_id: UUID,
        header: str,
        result: MatchingResult
    ) -> UUID:
        """Save match result to database"""
        logger.debug(f"Saving match: {header} → {result.matched_indicator}")
        
        # Determine matching method enum
        if result.method == "exact":
            method = MatchingMethod.RULE
        elif result.method == "fuzzy":
            method = MatchingMethod.RULE
        elif result.method == "llm":
            method = MatchingMethod.LLM
        else:
            method = MatchingMethod.MANUAL
        
        # Create matched indicator record
        matched_indicator = MatchedIndicator(
            upload_id=upload_id,
            original_header=header,
            matched_indicator=result.matched_indicator,
            confidence_score=result.confidence,
            matching_method=method,
            reviewed=not result.requires_review,
            reviewer_notes=result.reasoning if result.reasoning else None
        )
        
        self.db.add(matched_indicator)
        self.db.commit()
        self.db.refresh(matched_indicator)
        
        logger.debug(f"Saved match with ID: {matched_indicator.id}")
        
        return matched_indicator.id

    def get_review_queue(self, upload_id: UUID) -> List[MatchingResult]:
        """Get headers requiring manual review"""
        logger.info(f"Fetching review queue for upload {upload_id}")
        
        # Query unreviewed matches
        matches = (
            self.db.query(MatchedIndicator)
            .filter(
                MatchedIndicator.upload_id == upload_id,
                MatchedIndicator.reviewed == False
            )
            .order_by(MatchedIndicator.confidence_score.asc())
            .all()
        )
        
        results = []
        for match in matches:
            result = MatchingResult(
                original_header=match.original_header,
                matched_indicator=match.matched_indicator,
                confidence=match.confidence_score,
                method=match.matching_method.value,
                requires_review=True,
                indicator_id=match.id,
                reasoning=match.reviewer_notes
            )
            results.append(result)
        
        logger.info(f"Found {len(results)} matches requiring review")
        
        return results

    def approve_match(
        self,
        indicator_id: UUID,
        approved: bool,
        corrected_match: Optional[str] = None,
        notes: Optional[str] = None
    ) -> None:
        """Approve or correct a match"""
        logger.info(f"Reviewing match {indicator_id}: approved={approved}")
        
        # Get match record
        match = self.db.query(MatchedIndicator).filter(
            MatchedIndicator.id == indicator_id
        ).first()
        
        if not match:
            raise ValueError(f"Match {indicator_id} not found")
        
        # Store original for audit
        original_match = match.matched_indicator
        
        # Update match
        match.reviewed = True
        match.reviewer_notes = notes
        
        if not approved and corrected_match:
            match.matched_indicator = corrected_match
            match.matching_method = MatchingMethod.MANUAL
            match.confidence_score = 1.0  # Manual corrections are 100% confident
            logger.info(f"Corrected match: {original_match} → {corrected_match}")
        
        # Log audit trail
        audit = AuditLog(
            entity_id=indicator_id,
            entity_type="matched_indicators",
            action=AuditAction.REVIEWED,
            actor="user",
            timestamp=datetime.utcnow(),
            changes={
                "approved": approved,
                "original_match": original_match,
                "corrected_match": corrected_match if corrected_match else original_match,
                "notes": notes
            }
        )
        self.db.add(audit)
        
        self.db.commit()
        
        logger.info(f"Match {indicator_id} reviewed successfully")

    def get_matching_stats(self, upload_id: UUID) -> dict:
        """Get matching statistics for an upload"""
        matches = self.db.query(MatchedIndicator).filter(
            MatchedIndicator.upload_id == upload_id
        ).all()
        
        if not matches:
            return {
                "total": 0,
                "reviewed": 0,
                "requires_review": 0,
                "avg_confidence": 0.0,
                "by_method": {}
            }
        
        stats = {
            "total": len(matches),
            "reviewed": sum(1 for m in matches if m.reviewed),
            "requires_review": sum(1 for m in matches if not m.reviewed),
            "avg_confidence": sum(m.confidence_score for m in matches) / len(matches),
            "by_method": {}
        }
        
        # Count by method
        for match in matches:
            method = match.matching_method.value
            stats["by_method"][method] = stats["by_method"].get(method, 0) + 1
        
        return stats

    def rematch_header(self, indicator_id: UUID) -> MatchingResult:
        """Rematch a single header (useful after corrections)"""
        match = self.db.query(MatchedIndicator).filter(
            MatchedIndicator.id == indicator_id
        ).first()
        
        if not match:
            raise ValueError(f"Match {indicator_id} not found")
        
        # Get new match
        result = self.get_best_match(match.original_header)
        
        if result:
            # Update existing record
            match.matched_indicator = result.matched_indicator
            match.confidence_score = result.confidence
            match.matching_method = (
                MatchingMethod.LLM if result.method == "llm" else MatchingMethod.RULE
            )
            match.reviewed = not result.requires_review
            
            self.db.commit()
            
            result.indicator_id = indicator_id
        
        return result
