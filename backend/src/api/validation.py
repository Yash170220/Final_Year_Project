"""API endpoints for data validation"""
from typing import List, Dict, Any, Optional
from uuid import UUID
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.validation.engine import (
    ValidationEngine,
    NormalizedRecord,
    ValidationResult
)
from src.validation.service import (
    ValidationService,
    ValidationSummary,
    ValidationReport
)
from src.common.database import get_db


router = APIRouter(prefix="/api/v1/validation", tags=["validation"])


# Initialize validation engine
RULES_PATH = Path(__file__).parent.parent.parent / "data" / "validation-rules" / "validation_rules.json"
try:
    validation_engine = ValidationEngine(str(RULES_PATH))
except FileNotFoundError:
    validation_engine = None
    print(f"Warning: Validation rules not found at {RULES_PATH}")


class ValidateRecordRequest(BaseModel):
    """Request model for single record validation"""
    record: NormalizedRecord
    industry: str


class ValidateRecordResponse(BaseModel):
    """Response model for single record validation"""
    data_id: UUID
    is_valid: bool
    validation_results: List[ValidationResult]
    total_errors: int
    total_warnings: int


class ValidateBatchRequest(BaseModel):
    """Request model for batch validation"""
    records: List[NormalizedRecord]
    industry: str


class ValidateBatchResponse(BaseModel):
    """Response model for batch validation"""
    total_records: int
    valid_records: int
    invalid_records: int
    validation_results: Dict[str, List[ValidationResult]]
    summary: Dict[str, Any]


class ValidationRulesSummaryResponse(BaseModel):
    """Response model for validation rules summary"""
    total_rules: int
    industries: List[str]
    rules_by_industry: Dict[str, int]
    validation_types: List[str]


class ValidateUploadRequest(BaseModel):
    """Request model for upload validation"""
    upload_id: UUID
    industry: str


class ValidationStatisticsResponse(BaseModel):
    """Response model for validation statistics"""
    total_validations: int
    passed: int
    failed: int
    errors: int
    warnings: int
    pass_rate: float
    rules_applied: List[str]
    rules_count: int


def get_validation_service(db: Session = Depends(get_db)) -> ValidationService:
    """Dependency to get validation service instance"""
    if validation_engine is None:
        raise HTTPException(status_code=503, detail="Validation engine not initialized")
    return ValidationService(validation_engine, db)


@router.get("/health")
async def validation_health():
    """Check if validation engine is ready"""
    if validation_engine is None:
        raise HTTPException(status_code=503, detail="Validation engine not initialized")
    
    return {
        "status": "healthy",
        "engine_ready": True,
        "rules_loaded": validation_engine.get_rules_summary()["total_rules"]
    }


@router.get("/rules/summary", response_model=ValidationRulesSummaryResponse)
async def get_rules_summary():
    """Get summary of loaded validation rules"""
    if validation_engine is None:
        raise HTTPException(status_code=503, detail="Validation engine not initialized")
    
    summary = validation_engine.get_rules_summary()
    return ValidationRulesSummaryResponse(**summary)


@router.post("/validate/record", response_model=ValidateRecordResponse)
async def validate_single_record(request: ValidateRecordRequest):
    """
    Validate a single normalized record against industry rules
    
    Args:
        request: Record and industry information
    
    Returns:
        Validation results with errors and warnings
    """
    if validation_engine is None:
        raise HTTPException(status_code=503, detail="Validation engine not initialized")
    
    try:
        results = validation_engine.validate_record(request.record, request.industry)
        
        # Count errors and warnings
        errors = sum(1 for r in results if r.severity == "error")
        warnings = sum(1 for r in results if r.severity == "warning")
        
        return ValidateRecordResponse(
            data_id=request.record.id,
            is_valid=errors == 0,  # Valid if no errors (warnings are OK)
            validation_results=results,
            total_errors=errors,
            total_warnings=warnings
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")


@router.post("/validate/batch", response_model=ValidateBatchResponse)
async def validate_batch_records(request: ValidateBatchRequest):
    """
    Validate multiple records in batch, including cross-record validations
    
    Args:
        request: List of records and industry information
    
    Returns:
        Batch validation results with summary statistics
    """
    if validation_engine is None:
        raise HTTPException(status_code=503, detail="Validation engine not initialized")
    
    try:
        results = validation_engine.validate_batch(request.records, request.industry)
        
        # Calculate summary statistics
        total_records = len(request.records)
        invalid_records = len(results)
        valid_records = total_records - invalid_records
        
        total_errors = 0
        total_warnings = 0
        errors_by_rule = {}
        
        for record_results in results.values():
            for result in record_results:
                if result.severity == "error":
                    total_errors += 1
                else:
                    total_warnings += 1
                
                # Count by rule name
                if result.rule_name not in errors_by_rule:
                    errors_by_rule[result.rule_name] = 0
                errors_by_rule[result.rule_name] += 1
        
        # Convert UUID keys to strings for JSON serialization
        results_serializable = {
            str(data_id): record_results 
            for data_id, record_results in results.items()
        }
        
        summary = {
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "errors_by_rule": errors_by_rule,
            "validation_rate": f"{(valid_records / total_records * 100):.1f}%"
        }
        
        return ValidateBatchResponse(
            total_records=total_records,
            valid_records=valid_records,
            invalid_records=invalid_records,
            validation_results=results_serializable,
            summary=summary
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch validation error: {str(e)}")


@router.get("/rules")
async def get_validation_rules(industry: Optional[str] = None):
    """
    List all available validation rules
    
    Filterable by industry. Returns rule descriptions, parameters,
    and citations for transparency.
    
    Args:
        industry: Optional industry filter (cement_industry, steel_industry, etc.)
    
    Returns:
        List of validation rules with descriptions and citations
    
    Example:
        GET /api/v1/validation/rules
        GET /api/v1/validation/rules?industry=cement_industry
    
    Response:
        {
          "total_rules": 20,
          "industries": ["cement_industry", "steel_industry", ...],
          "rules": [
            {
              "rule_name": "cement_emission_range",
              "industry": "cement_industry",
              "description": "Cement production emissions typically 800-1,100 kg CO₂/tonne clinker",
              "indicator": "Scope 1 GHG Emissions per tonne clinker",
              "validation_type": "range",
              "severity": "error",
              "parameters": {"min": 800, "max": 1100, "unit": "kg CO₂/tonne"},
              "citation": "Andrew (2019) - Global CO₂ emissions from cement production"
            }
          ]
        }
    """
    if validation_engine is None:
        raise HTTPException(status_code=503, detail="Validation engine not initialized")
    
    try:
        # Get all rules or filter by industry
        if industry:
            if industry not in validation_engine.rules:
                raise HTTPException(status_code=404, detail=f"Industry '{industry}' not found")
            industries_to_process = {industry: validation_engine.rules[industry]}
        else:
            industries_to_process = validation_engine.rules
        
        # Format rules for response
        rules_list = []
        for industry_name, industry_rules in industries_to_process.items():
            for rule in industry_rules.values():
                rule_dict = {
                    "rule_name": rule.rule_name,
                    "industry": industry_name,
                    "description": rule.description,
                    "indicator": rule.indicator,
                    "validation_type": rule.validation_type,
                    "severity": rule.severity,
                    "parameters": rule.parameters,
                    "citation": rule.citation,
                    "error_message": rule.error_message,
                    "suggested_fixes": rule.suggested_fixes
                }
                rules_list.append(rule_dict)
        
        return {
            "total_rules": len(rules_list),
            "industries": list(validation_engine.rules.keys()) if not industry else [industry],
            "filtered_by": industry if industry else "all",
            "rules": rules_list
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving rules: {str(e)}")


@router.post("/validate/temporal")
async def validate_temporal_consistency(
    monthly_data: Dict[str, float],
    annual_total: float,
    industry: str = "cross_industry"
):
    """
    Validate temporal consistency between monthly and annual data
    
    Args:
        monthly_data: Dictionary of month names to values
        annual_total: Annual total value
        industry: Industry context (defaults to cross_industry)
    
    Returns:
        Validation result
    """
    if validation_engine is None:
        raise HTTPException(status_code=503, detail="Validation engine not initialized")
    
    try:
        # Get temporal consistency rule
        rule = None
        for r in validation_engine.rules.get("cross_industry", {}).values():
            if r.rule_name == "monthly_sum_equals_annual":
                rule = r
                break
        
        if rule is None:
            raise HTTPException(status_code=404, detail="Temporal consistency rule not found")
        
        from uuid import uuid4
        result = validation_engine.temporal_consistency(
            monthly_data,
            annual_total,
            rule,
            uuid4()
        )
        
        if result is None:
            return {
                "is_valid": True,
                "message": "Monthly data sums to annual total within tolerance"
            }
        else:
            return {
                "is_valid": False,
                "validation_result": result
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Temporal validation error: {str(e)}")


# New service-based endpoints

@router.post("/process/{upload_id}", response_model=ValidationSummary)
async def process_validation(
    upload_id: UUID,
    industry: str,
    service: ValidationService = Depends(get_validation_service)
):
    """
    Trigger validation for normalized data
    
    Accepts industry parameter (cement_industry, steel_industry, automotive_industry)
    and validates all normalized data for the upload.
    
    Args:
        upload_id: UUID of the upload to validate
        industry: Industry category (cement_industry, steel_industry, automotive_industry)
        service: Validation service instance
    
    Returns:
        ValidationSummary with statistics and error breakdowns
    
    Example:
        POST /api/v1/validation/process/{upload_id}?industry=cement_industry
    """
    try:
        summary = service.validate_upload(upload_id, industry)
        return summary
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")


@router.get("/errors/{upload_id}")
async def get_validation_errors(
    upload_id: UUID,
    service: ValidationService = Depends(get_validation_service)
):
    """
    Get all validation errors for an upload
    
    Returns all critical validation errors with suggested fixes
    formatted for easy review.
    
    Args:
        upload_id: UUID of the upload
        service: Validation service instance
    
    Returns:
        List of validation errors with suggested fixes and citations
    
    Example Response:
        {
          "upload_id": "uuid",
          "total_errors": 50,
          "errors": [
            {
              "indicator": "Scope 1 Emissions",
              "rule": "cement_emission_range",
              "severity": "error",
              "message": "Value 15000 kg CO₂/tonne outside range (800-1100)",
              "suggested_fixes": ["Check if value should be in tonnes instead of kg"],
              "citation": "Andrew (2019)"
            }
          ]
        }
    """
    try:
        errors = service.get_validation_errors(upload_id)
        
        # Enhance error format with suggested fixes
        enhanced_errors = []
        for error in errors:
            # Get the rule to access suggested fixes
            rule_name = error.get("rule_name", "")
            suggested_fixes = []
            
            # Try to get suggested fixes from the rule
            for industry_rules in validation_engine.rules.values():
                for rule in industry_rules.values():
                    if rule.rule_name == rule_name:
                        suggested_fixes = rule.suggested_fixes
                        break
            
            enhanced_error = {
                "data_id": error.get("data_id"),
                "indicator": error.get("rule_name", "Unknown"),  # You may want to resolve actual indicator name
                "rule": error.get("rule_name"),
                "severity": error.get("severity"),
                "message": error.get("message"),
                "suggested_fixes": suggested_fixes,
                "citation": error.get("citation", ""),
                "created_at": error.get("created_at")
            }
            enhanced_errors.append(enhanced_error)
        
        return {
            "upload_id": str(upload_id),
            "total_errors": len(enhanced_errors),
            "errors": enhanced_errors
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving validation errors: {str(e)}")


@router.get("/warnings/{upload_id}")
async def get_validation_warnings(
    upload_id: UUID,
    service: ValidationService = Depends(get_validation_service)
):
    """
    Get all validation warnings for an upload
    
    Returns all validation warnings (less critical than errors).
    These are issues that should be reviewed but don't block processing.
    
    Args:
        upload_id: UUID of the upload
        service: Validation service instance
    
    Returns:
        List of validation warnings with suggested improvements
    
    Example Response:
        {
          "upload_id": "uuid",
          "total_warnings": 30,
          "warnings": [
            {
              "indicator": "Energy Intensity",
              "rule": "cement_energy_range",
              "severity": "warning",
              "message": "Energy intensity at upper bound of typical range",
              "suggested_fixes": ["Review kiln efficiency metrics"],
              "citation": "IEA Technology Roadmap"
            }
          ]
        }
    """
    try:
        warnings = service.get_validation_warnings(upload_id)
        
        # Enhance warning format with suggested fixes
        enhanced_warnings = []
        for warning in warnings:
            rule_name = warning.get("rule_name", "")
            suggested_fixes = []
            
            # Get suggested fixes from the rule
            for industry_rules in validation_engine.rules.values():
                for rule in industry_rules.values():
                    if rule.rule_name == rule_name:
                        suggested_fixes = rule.suggested_fixes
                        break
            
            enhanced_warning = {
                "data_id": warning.get("data_id"),
                "indicator": warning.get("rule_name", "Unknown"),
                "rule": warning.get("rule_name"),
                "severity": warning.get("severity"),
                "message": warning.get("message"),
                "suggested_fixes": suggested_fixes,
                "citation": warning.get("citation", ""),
                "created_at": warning.get("created_at")
            }
            enhanced_warnings.append(enhanced_warning)
        
        return {
            "upload_id": str(upload_id),
            "total_warnings": len(enhanced_warnings),
            "warnings": enhanced_warnings
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving validation warnings: {str(e)}")


@router.get("/report/{upload_id}")
async def get_comprehensive_report(
    upload_id: UUID,
    service: ValidationService = Depends(get_validation_service)
):
    """
    Generate comprehensive validation report
    
    Includes summary statistics, all errors, warnings, recommendations,
    and chart data for error distribution visualization.
    Export as JSON format.
    
    Args:
        upload_id: UUID of the upload
        service: Validation service instance
    
    Returns:
        Comprehensive validation report with charts data
    
    Example Response:
        {
          "summary": {
            "total_records": 1500,
            "valid_records": 1420,
            "records_with_errors": 50,
            "records_with_warnings": 30,
            "validation_pass_rate": 94.67
          },
          "errors": [...],
          "warnings": [...],
          "recommendations": [
            "Review 50 records flagged with emission range errors",
            "Consider updating clinker ratio calculation for Plant B"
          ],
          "charts_data": {
            "error_distribution": {...},
            "warning_distribution": {...}
          }
        }
    """
    try:
        report = service.generate_validation_report(upload_id)
        
        # Enhance errors with suggested fixes
        enhanced_errors = []
        for error in report.errors:
            rule_name = error.get("rule_name", "")
            suggested_fixes = []
            citation = error.get("citation", "")
            
            # Get full rule details
            for industry_rules in validation_engine.rules.values():
                for rule in industry_rules.values():
                    if rule.rule_name == rule_name:
                        suggested_fixes = rule.suggested_fixes
                        if not citation:
                            citation = rule.citation
                        break
            
            enhanced_error = {
                "indicator": error.get("rule_name", "Unknown"),
                "rule": rule_name,
                "severity": error.get("severity"),
                "message": error.get("message"),
                "suggested_fix": suggested_fixes[0] if suggested_fixes else "Review data entry",
                "citation": citation
            }
            enhanced_errors.append(enhanced_error)
        
        # Enhance warnings
        enhanced_warnings = []
        for warning in report.warnings:
            rule_name = warning.get("rule_name", "")
            suggested_fixes = []
            citation = warning.get("citation", "")
            
            for industry_rules in validation_engine.rules.values():
                for rule in industry_rules.values():
                    if rule.rule_name == rule_name:
                        suggested_fixes = rule.suggested_fixes
                        if not citation:
                            citation = rule.citation
                        break
            
            enhanced_warning = {
                "indicator": warning.get("rule_name", "Unknown"),
                "rule": rule_name,
                "severity": warning.get("severity"),
                "message": warning.get("message"),
                "suggested_fix": suggested_fixes[0] if suggested_fixes else "Review for optimization",
                "citation": citation
            }
            enhanced_warnings.append(enhanced_warning)
        
        # Generate charts data for visualization
        charts_data = {
            "error_distribution": report.summary.error_breakdown,
            "warning_distribution": report.summary.warning_breakdown,
            "pass_rate": {
                "passed": report.summary.total_records - report.summary.records_with_errors,
                "failed": report.summary.records_with_errors
            },
            "severity_breakdown": {
                "errors": report.summary.records_with_errors,
                "warnings": report.summary.records_with_warnings,
                "valid": report.summary.valid_records
            }
        }
        
        return {
            "upload_id": str(upload_id),
            "summary": {
                "total_records": report.summary.total_records,
                "valid_records": report.summary.valid_records,
                "records_with_errors": report.summary.records_with_errors,
                "records_with_warnings": report.summary.records_with_warnings,
                "validation_pass_rate": round(report.summary.validation_pass_rate, 2)
            },
            "errors": enhanced_errors,
            "warnings": enhanced_warnings,
            "recommendations": report.recommendations,
            "charts_data": charts_data,
            "generated_at": report.generated_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating validation report: {str(e)}")


@router.get("/upload/{upload_id}/statistics", response_model=ValidationStatisticsResponse)
async def get_validation_statistics(
    upload_id: UUID,
    service: ValidationService = Depends(get_validation_service)
):
    """
    Get detailed validation statistics for an upload
    
    Args:
        upload_id: UUID of the upload
        service: Validation service instance
    
    Returns:
        Detailed validation statistics
    """
    try:
        stats = service.get_validation_statistics(upload_id)
        return ValidationStatisticsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving validation statistics: {str(e)}")


@router.post("/revalidate/record/{data_id}")
async def revalidate_record(
    data_id: UUID,
    industry: str,
    service: ValidationService = Depends(get_validation_service)
):
    """
    Re-run validation for a single record
    
    Args:
        data_id: UUID of the normalized data record
        industry: Industry category
        service: Validation service instance
    
    Returns:
        New validation results
    """
    try:
        results = service.revalidate_record(data_id, industry)
        return {
            "data_id": str(data_id),
            "validation_results": [
                {
                    "rule_name": r.rule_name,
                    "is_valid": r.is_valid,
                    "severity": r.severity,
                    "message": r.message,
                    "citation": r.citation
                }
                for r in results
            ],
            "total_issues": len(results)
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Re-validation error: {str(e)}")


# New review/bypass endpoints

class MarkReviewedRequest(BaseModel):
    """Request model for marking error as reviewed"""
    result_id: UUID
    reviewer: str
    notes: str


class SuppressWarningRequest(BaseModel):
    """Request model for suppressing warning"""
    result_id: UUID
    reason: str
    reviewer: str = "system"


class BulkReviewRequest(BaseModel):
    """Request model for bulk review"""
    result_ids: List[UUID]
    reviewer: str
    notes: str


@router.post("/review/mark-reviewed")
async def mark_error_reviewed(
    request: MarkReviewedRequest,
    service: ValidationService = Depends(get_validation_service)
):
    """
    Mark a validation error as reviewed
    
    Used when an error is a false positive or has been acknowledged.
    Updates the validation result and logs the review in audit trail.
    
    Args:
        request: Review information (result_id, reviewer, notes)
        service: Validation service instance
    
    Returns:
        Success confirmation
    
    Example:
        {
          "result_id": "uuid",
          "reviewer": "john.doe@company.com",
          "notes": "False positive - value is correct for this special case"
        }
    """
    try:
        service.mark_error_as_reviewed(
            request.result_id,
            request.reviewer,
            request.notes
        )
        return {
            "status": "success",
            "message": "Error marked as reviewed",
            "result_id": str(request.result_id),
            "reviewer": request.reviewer
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error marking as reviewed: {str(e)}")


@router.post("/review/suppress-warning")
async def suppress_validation_warning(
    request: SuppressWarningRequest,
    service: ValidationService = Depends(get_validation_service)
):
    """
    Suppress a validation warning
    
    Acknowledges a warning so it doesn't appear in future reports.
    Cannot be used for errors - errors must be marked as reviewed.
    
    Args:
        request: Suppression information (result_id, reason, reviewer)
        service: Validation service instance
    
    Returns:
        Success confirmation
    
    Example:
        {
          "result_id": "uuid",
          "reason": "Acceptable variance for this facility type",
          "reviewer": "jane.smith@company.com"
        }
    """
    try:
        service.suppress_warning(
            request.result_id,
            request.reason,
            request.reviewer
        )
        return {
            "status": "success",
            "message": "Warning suppressed",
            "result_id": str(request.result_id)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error suppressing warning: {str(e)}")


@router.post("/review/bulk-review")
async def bulk_review_errors(
    request: BulkReviewRequest,
    service: ValidationService = Depends(get_validation_service)
):
    """
    Mark multiple validation errors as reviewed in bulk
    
    Efficient way to review multiple similar errors at once.
    
    Args:
        request: Bulk review information (result_ids, reviewer, notes)
        service: Validation service instance
    
    Returns:
        Number of items successfully reviewed
    """
    try:
        count = service.bulk_review_errors(
            request.result_ids,
            request.reviewer,
            request.notes
        )
        return {
            "status": "success",
            "reviewed_count": count,
            "total_requested": len(request.result_ids)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk review error: {str(e)}")


@router.get("/unreviewed/{upload_id}")
async def get_unreviewed_errors(
    upload_id: UUID,
    service: ValidationService = Depends(get_validation_service)
):
    """
    Get validation errors that haven't been reviewed
    
    Used for blocking export until all errors are reviewed or corrected.
    Only returns unreviewed errors - reviewed errors are excluded.
    
    Args:
        upload_id: UUID of the upload
        service: Validation service instance
    
    Returns:
        List of unreviewed validation errors
    
    Example Response:
        {
          "upload_id": "uuid",
          "unreviewed_count": 15,
          "errors": [...],
          "blocking_export": true
        }
    """
    try:
        errors = service.get_unreviewed_errors(upload_id)
        return {
            "upload_id": str(upload_id),
            "unreviewed_count": len(errors),
            "errors": errors,
            "blocking_export": len(errors) > 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving unreviewed errors: {str(e)}")


@router.get("/review-summary/{upload_id}")
async def get_review_summary(
    upload_id: UUID,
    service: ValidationService = Depends(get_validation_service)
):
    """
    Get summary of review status for an upload
    
    Shows total errors, reviewed errors, unreviewed errors, warnings status,
    and whether the upload is ready for export.
    
    Args:
        upload_id: UUID of the upload
        service: Validation service instance
    
    Returns:
        Review summary with export readiness status
    
    Example Response:
        {
          "total_errors": 50,
          "reviewed_errors": 35,
          "unreviewed_errors": 15,
          "total_warnings": 30,
          "suppressed_warnings": 10,
          "active_warnings": 20,
          "ready_for_export": false,
          "final_pass_rate": 92.5
        }
    """
    try:
        summary = service.get_review_summary(upload_id)
        return {
            "upload_id": str(upload_id),
            **summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating review summary: {str(e)}")


@router.get("/final-pass-rate/{upload_id}")
async def get_final_pass_rate(
    upload_id: UUID,
    service: ValidationService = Depends(get_validation_service)
):
    """
    Calculate final pass rate excluding reviewed/suppressed items
    
    Returns the actual pass rate after human review, excluding:
    - Reviewed errors (false positives)
    - Suppressed warnings
    
    Args:
        upload_id: UUID of the upload
        service: Validation service instance
    
    Returns:
        Final pass rate as percentage
    
    Example Response:
        {
          "upload_id": "uuid",
          "initial_pass_rate": 85.5,
          "final_pass_rate": 94.2,
          "improvement": 8.7
        }
    """
    try:
        final_rate = service.calculate_final_pass_rate(upload_id)
        
        # Get initial pass rate for comparison
        stats = service.get_validation_statistics(upload_id)
        initial_rate = stats.get("pass_rate", 0)
        
        return {
            "upload_id": str(upload_id),
            "initial_pass_rate": initial_rate,
            "final_pass_rate": final_rate,
            "improvement": round(final_rate - initial_rate, 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating final pass rate: {str(e)}")


@router.get("/reviewed-items/{upload_id}")
async def get_reviewed_items(
    upload_id: UUID,
    service: ValidationService = Depends(get_validation_service)
):
    """
    Get all reviewed items (errors and suppressed warnings)
    
    Shows which items have been reviewed and why, for audit purposes.
    
    Args:
        upload_id: UUID of the upload
        service: Validation service instance
    
    Returns:
        Dictionary with reviewed errors and suppressed warnings
    """
    try:
        items = service.get_reviewed_items(upload_id)
        return {
            "upload_id": str(upload_id),
            **items
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving reviewed items: {str(e)}")
