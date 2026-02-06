"""API endpoints for data normalization."""

from pathlib import Path
from typing import Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.common.database import get_db
from src.common.models import NormalizedData, MatchedIndicator
from src.normalization import (
    NormalizationService,
    UnitNormalizer,
    NormalizationError,
)

router = APIRouter(prefix="/api/v1/normalization", tags=["normalization"])


def get_normalization_service(db: Session = Depends(get_db)) -> NormalizationService:
    """Get normalization service instance."""
    conversion_factors_path = Path(__file__).parent.parent.parent / "data" / "validation-rules" / "conversion_factors.json"
    normalizer = UnitNormalizer(str(conversion_factors_path))
    return NormalizationService(normalizer, db)


@router.post("/process/{upload_id}")
def process_normalization(
    upload_id: UUID,
    service: NormalizationService = Depends(get_normalization_service)
) -> Dict:
    """Process normalization for an upload.
    
    Args:
        upload_id: Upload UUID
        service: NormalizationService instance
        
    Returns:
        NormalizationSummary as dict
    """
    try:
        summary = service.normalize_data(upload_id)
        
        return {
            "total_records": summary.total_records,
            "successfully_normalized": summary.successfully_normalized,
            "failed_normalization": summary.failed_normalization,
            "unique_units_detected": summary.unique_units_detected,
            "conversions_applied": [
                {
                    "conversion": key,
                    "count": value
                }
                for key, value in summary.conversions_applied.items()
            ],
            "errors": summary.errors
        }
    except NormalizationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Normalization failed: {str(e)}")


@router.get("/results/{upload_id}")
def get_normalization_results(
    upload_id: UUID,
    indicator_name: str = None,
    service: NormalizationService = Depends(get_normalization_service)
) -> Dict:
    """Get normalized data results.
    
    Args:
        upload_id: Upload UUID
        indicator_name: Optional filter by indicator name
        service: NormalizationService instance
        
    Returns:
        Normalized data grouped by indicator
    """
    try:
        df = service.get_normalized_data(upload_id, indicator_name)
        
        if df.is_empty():
            return {
                "upload_id": str(upload_id),
                "indicators": [],
                "total_records": 0
            }
        
        # Group by indicator
        indicators = {}
        for row in df.iter_rows(named=True):
            indicator = row["indicator"]
            if indicator not in indicators:
                indicators[indicator] = {
                    "indicator": indicator,
                    "records": []
                }
            
            indicators[indicator]["records"].append({
                "row_index": row["row_index"],
                "original_value": row["original_value"],
                "original_unit": row["original_unit"],
                "normalized_value": row["normalized_value"],
                "normalized_unit": row["normalized_unit"]
            })
        
        return {
            "upload_id": str(upload_id),
            "indicators": list(indicators.values()),
            "total_records": len(df)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve results: {str(e)}")


@router.get("/conversions/{upload_id}")
def get_conversions(
    upload_id: UUID,
    db: Session = Depends(get_db)
) -> Dict:
    """Get all conversions applied for an upload.
    
    Args:
        upload_id: Upload UUID
        db: Database session
        
    Returns:
        List of conversions with metadata
    """
    try:
        # Query normalized data with matched indicators
        results = (
            db.query(
                MatchedIndicator.canonical_indicator,
                NormalizedData.original_unit,
                NormalizedData.normalized_unit,
                NormalizedData.conversion_factor,
                NormalizedData.metadata
            )
            .join(MatchedIndicator)
            .filter(MatchedIndicator.upload_id == upload_id)
            .all()
        )
        
        if not results:
            return {
                "upload_id": str(upload_id),
                "conversions": []
            }
        
        # Group by indicator and units
        conversions_map = {}
        for indicator, orig_unit, norm_unit, factor, metadata in results:
            key = f"{indicator}|{orig_unit}|{norm_unit}"
            
            if key not in conversions_map:
                conversions_map[key] = {
                    "indicator": indicator,
                    "original_unit": orig_unit,
                    "normalized_unit": norm_unit,
                    "conversion_factor": factor,
                    "source": metadata.get("conversion_source", "Unknown") if metadata else "Unknown",
                    "formula": metadata.get("formula", "") if metadata else "",
                    "record_count": 0
                }
            
            conversions_map[key]["record_count"] += 1
        
        return {
            "upload_id": str(upload_id),
            "conversions": list(conversions_map.values())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve conversions: {str(e)}")


@router.get("/errors/{upload_id}")
def get_normalization_errors(
    upload_id: UUID,
    service: NormalizationService = Depends(get_normalization_service),
    db: Session = Depends(get_db)
) -> Dict:
    """Get normalization errors and suggestions.
    
    Args:
        upload_id: Upload UUID
        service: NormalizationService instance
        db: Database session
        
    Returns:
        List of errors with suggestions
    """
    try:
        # Check for unit conflicts
        conflicts = service.check_unit_conflicts(upload_id)
        
        # Get indicators without normalized data
        matched_indicators = (
            db.query(MatchedIndicator)
            .filter(
                MatchedIndicator.upload_id == upload_id,
                MatchedIndicator.approved.is_(True)
            )
            .all()
        )
        
        errors = []
        
        # Add conflict errors
        for indicator, units in conflicts.items():
            errors.append({
                "indicator": indicator,
                "issue": "Conflicting units detected",
                "details": f"Multiple units found: {', '.join(units)}",
                "suggestion": "Review data source and ensure consistent units"
            })
        
        # Check for indicators with no normalized data
        for indicator in matched_indicators:
            count = (
                db.query(NormalizedData)
                .filter(NormalizedData.matched_indicator_id == indicator.id)
                .count()
            )
            
            if count == 0:
                errors.append({
                    "indicator": indicator.canonical_indicator,
                    "issue": "No normalized data",
                    "details": f"Header: {indicator.matched_header}",
                    "suggestion": "Unit could not be detected. Specify unit in header or review manually"
                })
        
        return {
            "upload_id": str(upload_id),
            "error_count": len(errors),
            "errors": errors
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve errors: {str(e)}")


@router.get("/summary/{upload_id}")
def get_normalization_summary(
    upload_id: UUID,
    db: Session = Depends(get_db)
) -> Dict:
    """Get comprehensive normalization summary.
    
    Args:
        upload_id: Upload UUID
        db: Database session
        
    Returns:
        Complete summary with statistics
    """
    try:
        # Get total matched indicators
        total_indicators = (
            db.query(MatchedIndicator)
            .filter(
                MatchedIndicator.upload_id == upload_id,
                MatchedIndicator.approved.is_(True)
            )
            .count()
        )
        
        # Get total normalized records
        total_normalized = (
            db.query(NormalizedData)
            .join(MatchedIndicator)
            .filter(MatchedIndicator.upload_id == upload_id)
            .count()
        )
        
        # Get unique units
        units = (
            db.query(NormalizedData.original_unit)
            .join(MatchedIndicator)
            .filter(MatchedIndicator.upload_id == upload_id)
            .distinct()
            .all()
        )
        
        # Get conversion summary
        conversions = (
            db.query(
                NormalizedData.original_unit,
                NormalizedData.normalized_unit
            )
            .join(MatchedIndicator)
            .filter(MatchedIndicator.upload_id == upload_id)
            .all()
        )
        
        conversion_counts = {}
        for orig, norm in conversions:
            key = f"{orig}→{norm}"
            conversion_counts[key] = conversion_counts.get(key, 0) + 1
        
        return {
            "upload_id": str(upload_id),
            "total_indicators": total_indicators,
            "total_normalized_records": total_normalized,
            "unique_units": [u[0] for u in units],
            "conversions": [
                {"conversion": k, "count": v}
                for k, v in conversion_counts.items()
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve summary: {str(e)}")
