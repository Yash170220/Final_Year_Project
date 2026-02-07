"""Validation Service for ESG Data Quality Management"""
from typing import List, Dict, Optional, Any
from uuid import UUID
from datetime import datetime
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.validation.engine import (
    ValidationEngine,
    NormalizedRecord,
    ValidationResult as EngineValidationResult
)
from src.common.models import (
    NormalizedData,
    ValidationResult as DBValidationResult,
    Upload,
    AuditLog,
    AuditAction,
    Severity
)
from pydantic import BaseModel, Field


class ValidationSummary(BaseModel):
    """Summary statistics for validation results"""
    total_records: int
    valid_records: int  # No errors or warnings
    records_with_errors: int
    records_with_warnings: int
    validation_pass_rate: float  # Percentage without errors
    error_breakdown: Dict[str, int] = Field(default_factory=dict)  # rule_name → count
    warning_breakdown: Dict[str, int] = Field(default_factory=dict)  # rule_name → count


class ValidationReport(BaseModel):
    """Comprehensive validation report"""
    upload_id: UUID
    summary: ValidationSummary
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ValidationService:
    """Service for validating ESG data and managing validation results"""
    
    def __init__(self, validation_engine: ValidationEngine, db_session: Session):
        """
        Initialize validation service
        
        Args:
            validation_engine: Initialized validation engine
            db_session: SQLAlchemy database session
        """
        self.engine = validation_engine
        self.db = db_session
    
    def validate_upload(self, upload_id: UUID, industry: str) -> ValidationSummary:
        """
        Validate all normalized data for a given upload
        
        Args:
            upload_id: UUID of the upload to validate
            industry: Industry category for validation rules
        
        Returns:
            ValidationSummary with statistics and breakdowns
        """
        # Get all normalized data for this upload
        normalized_records = self.db.query(NormalizedData).filter(
            NormalizedData.upload_id == upload_id
        ).all()
        
        if not normalized_records:
            raise ValueError(f"No normalized data found for upload {upload_id}")
        
        # Convert to NormalizedRecord objects for validation
        validation_records = []
        for record in normalized_records:
            validation_record = NormalizedRecord(
                id=record.id,
                indicator=record.indicator_id,  # Will need to resolve indicator name
                value=record.normalized_value,
                unit=record.normalized_unit,
                original_value=record.original_value,
                original_unit=record.original_unit,
                metadata={}
            )
            validation_records.append((record.id, validation_record))
        
        # Group records by indicator for batch validation
        records_by_indicator: Dict[str, List[tuple]] = defaultdict(list)
        for record_id, record in validation_records:
            records_by_indicator[record.indicator].append((record_id, record))
        
        # Run validation for each indicator group
        all_validation_results = []
        for indicator, records in records_by_indicator.items():
            # Extract just the validation records
            records_only = [r[1] for r in records]
            
            # Run batch validation
            batch_results = self.engine.validate_batch(records_only, industry)
            
            # Flatten results
            for data_id, results in batch_results.items():
                for result in results:
                    all_validation_results.append(result)
        
        # Save validation results to database
        if all_validation_results:
            self.save_validation_results(all_validation_results, upload_id)
        
        # Generate and return summary
        summary = self._generate_summary(normalized_records, all_validation_results)
        
        # Log audit trail
        self._log_validation_audit(upload_id, summary)
        
        return summary
    
    def validate_indicator_batch(
        self, 
        records: List[NormalizedRecord], 
        industry: str
    ) -> List[EngineValidationResult]:
        """
        Apply validation rules to a batch of records
        
        Args:
            records: List of normalized records to validate
            industry: Industry category
        
        Returns:
            List of validation violations (errors and warnings)
        """
        # Use validation engine's batch validation
        batch_results = self.engine.validate_batch(records, industry)
        
        # Flatten results into a single list
        all_results = []
        for data_id, results in batch_results.items():
            all_results.extend(results)
        
        return all_results
    
    def get_validation_errors(self, upload_id: UUID) -> List[Dict[str, Any]]:
        """
        Get all validation errors for an upload
        
        Args:
            upload_id: UUID of the upload
        
        Returns:
            List of validation errors, ordered by indicator and rule name
        """
        errors = self.db.query(DBValidationResult).join(
            NormalizedData,
            DBValidationResult.data_id == NormalizedData.id
        ).filter(
            and_(
                NormalizedData.upload_id == upload_id,
                DBValidationResult.severity == Severity.ERROR,
                DBValidationResult.is_valid == False
            )
        ).order_by(
            DBValidationResult.rule_name
        ).all()
        
        return [self._serialize_validation_result(error) for error in errors]
    
    def get_validation_warnings(self, upload_id: UUID) -> List[Dict[str, Any]]:
        """
        Get all validation warnings for an upload
        
        Args:
            upload_id: UUID of the upload
        
        Returns:
            List of validation warnings
        """
        warnings = self.db.query(DBValidationResult).join(
            NormalizedData,
            DBValidationResult.data_id == NormalizedData.id
        ).filter(
            and_(
                NormalizedData.upload_id == upload_id,
                DBValidationResult.severity == Severity.WARNING,
                DBValidationResult.is_valid == False
            )
        ).order_by(
            DBValidationResult.rule_name
        ).all()
        
        return [self._serialize_validation_result(warning) for warning in warnings]
    
    def save_validation_results(
        self, 
        results: List[EngineValidationResult],
        upload_id: Optional[UUID] = None
    ) -> None:
        """
        Save validation results to database
        
        Args:
            results: List of validation results from engine
            upload_id: Optional upload ID for audit logging
        """
        if not results:
            return
        
        # Bulk insert validation results
        db_results = []
        for result in results:
            # Parse citation if it's too long for TEXT field
            citation = result.citation[:500] if result.citation else ""
            
            db_result = DBValidationResult(
                data_id=result.data_id,
                rule_name=result.rule_name,
                is_valid=result.is_valid,
                severity=Severity.ERROR if result.severity == "error" else Severity.WARNING,
                message=result.message,
                citation=citation
            )
            db_results.append(db_result)
        
        # Bulk insert
        self.db.bulk_save_objects(db_results)
        self.db.commit()
        
        # Log audit trail
        if upload_id:
            audit_log = AuditLog(
                entity_id=upload_id,
                entity_type="upload",
                action=AuditAction.REVIEWED,
                actor="validation_service",
                changes={
                    "validation_results_count": len(results),
                    "errors": sum(1 for r in results if r.severity == "error"),
                    "warnings": sum(1 for r in results if r.severity == "warning")
                }
            )
            self.db.add(audit_log)
            self.db.commit()
    
    def generate_validation_report(self, upload_id: UUID) -> ValidationReport:
        """
        Generate comprehensive validation report
        
        Args:
            upload_id: UUID of the upload
        
        Returns:
            ValidationReport with summary, errors, warnings, and recommendations
        """
        # Get all normalized records
        normalized_records = self.db.query(NormalizedData).filter(
            NormalizedData.upload_id == upload_id
        ).all()
        
        # Get all validation results
        all_results = self.db.query(DBValidationResult).join(
            NormalizedData,
            DBValidationResult.data_id == NormalizedData.id
        ).filter(
            NormalizedData.upload_id == upload_id
        ).all()
        
        # Convert to engine validation results for summary generation
        engine_results = []
        for db_result in all_results:
            if not db_result.is_valid:
                engine_result = EngineValidationResult(
                    data_id=db_result.data_id,
                    rule_name=db_result.rule_name,
                    is_valid=db_result.is_valid,
                    severity="error" if db_result.severity == Severity.ERROR else "warning",
                    message=db_result.message,
                    citation=db_result.citation,
                    suggested_fixes=[]
                )
                engine_results.append(engine_result)
        
        # Generate summary
        summary = self._generate_summary(normalized_records, engine_results)
        
        # Get errors and warnings
        errors = self.get_validation_errors(upload_id)
        warnings = self.get_validation_warnings(upload_id)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(summary, errors, warnings)
        
        return ValidationReport(
            upload_id=upload_id,
            summary=summary,
            errors=errors,
            warnings=warnings,
            recommendations=recommendations
        )
    
    def _generate_summary(
        self, 
        normalized_records: List[NormalizedData],
        validation_results: List[EngineValidationResult]
    ) -> ValidationSummary:
        """Generate validation summary statistics"""
        total_records = len(normalized_records)
        
        # Track which records have errors or warnings
        records_with_errors = set()
        records_with_warnings = set()
        error_breakdown = defaultdict(int)
        warning_breakdown = defaultdict(int)
        
        for result in validation_results:
            if result.severity == "error":
                records_with_errors.add(result.data_id)
                error_breakdown[result.rule_name] += 1
            else:  # warning
                records_with_warnings.add(result.data_id)
                warning_breakdown[result.rule_name] += 1
        
        # Calculate valid records (no errors or warnings)
        all_invalid_records = records_with_errors.union(records_with_warnings)
        valid_records = total_records - len(all_invalid_records)
        
        # Calculate pass rate (no errors, warnings OK)
        validation_pass_rate = (
            ((total_records - len(records_with_errors)) / total_records * 100)
            if total_records > 0 else 100.0
        )
        
        return ValidationSummary(
            total_records=total_records,
            valid_records=valid_records,
            records_with_errors=len(records_with_errors),
            records_with_warnings=len(records_with_warnings),
            validation_pass_rate=round(validation_pass_rate, 2),
            error_breakdown=dict(error_breakdown),
            warning_breakdown=dict(warning_breakdown)
        )
    
    def _serialize_validation_result(self, db_result: DBValidationResult) -> Dict[str, Any]:
        """Convert database validation result to dictionary"""
        return {
            "id": str(db_result.id),
            "data_id": str(db_result.data_id),
            "rule_name": db_result.rule_name,
            "is_valid": db_result.is_valid,
            "severity": db_result.severity.value,
            "message": db_result.message,
            "citation": db_result.citation,
            "created_at": db_result.created_at.isoformat() if db_result.created_at else None
        }
    
    def _generate_recommendations(
        self, 
        summary: ValidationSummary,
        errors: List[Dict[str, Any]],
        warnings: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate actionable recommendations based on validation results"""
        recommendations = []
        
        # High error rate
        if summary.validation_pass_rate < 50:
            recommendations.append(
                "⚠️ Critical: Over 50% of records have validation errors. "
                "Review data collection and entry processes."
            )
        
        # Common error patterns
        if summary.error_breakdown:
            most_common_error = max(
                summary.error_breakdown.items(), 
                key=lambda x: x[1]
            )
            recommendations.append(
                f"🔍 Most common error: '{most_common_error[0]}' "
                f"({most_common_error[1]} occurrences). "
                "Focus on fixing this issue first."
            )
        
        # Range validation errors
        range_errors = [
            err for err in errors 
            if "range" in err.get("rule_name", "").lower()
        ]
        if range_errors:
            recommendations.append(
                "📏 Multiple values outside expected ranges detected. "
                "Check for unit conversion errors or decimal place mistakes."
            )
        
        # Outlier detection
        outlier_errors = [
            err for err in errors 
            if "outlier" in err.get("rule_name", "").lower()
        ]
        if outlier_errors:
            recommendations.append(
                "📊 Statistical outliers detected. "
                "Review highlighted values for data entry errors or anomalies."
            )
        
        # Temporal consistency issues
        temporal_warnings = [
            warn for warn in warnings
            if "temporal" in warn.get("rule_name", "").lower()
        ]
        if temporal_warnings:
            recommendations.append(
                "📅 Temporal consistency issues found. "
                "Verify that monthly data sums match annual totals."
            )
        
        # Scope classification errors
        scope_errors = [
            err for err in errors
            if "scope" in err.get("rule_name", "").lower()
        ]
        if scope_errors:
            recommendations.append(
                "🎯 Scope classification errors detected. "
                "Review GHG Protocol guidelines for proper emission source categorization."
            )
        
        # If no issues
        if summary.records_with_errors == 0 and summary.records_with_warnings == 0:
            recommendations.append(
                "✅ Excellent! All records passed validation. "
                "Data is ready for report generation."
            )
        elif summary.records_with_errors == 0:
            recommendations.append(
                "✅ Good! No errors found, only warnings. "
                "Review warnings for potential data quality improvements."
            )
        
        return recommendations
    
    def _log_validation_audit(self, upload_id: UUID, summary: ValidationSummary) -> None:
        """Log validation activity to audit log"""
        audit_log = AuditLog(
            entity_id=upload_id,
            entity_type="upload",
            action=AuditAction.REVIEWED,
            actor="validation_service",
            changes={
                "total_records": summary.total_records,
                "valid_records": summary.valid_records,
                "records_with_errors": summary.records_with_errors,
                "records_with_warnings": summary.records_with_warnings,
                "validation_pass_rate": summary.validation_pass_rate
            }
        )
        self.db.add(audit_log)
        self.db.commit()
    
    def get_validation_statistics(self, upload_id: UUID) -> Dict[str, Any]:
        """
        Get detailed validation statistics for an upload
        
        Args:
            upload_id: UUID of the upload
        
        Returns:
            Dictionary with detailed statistics
        """
        # Get all validation results
        all_results = self.db.query(DBValidationResult).join(
            NormalizedData,
            DBValidationResult.data_id == NormalizedData.id
        ).filter(
            NormalizedData.upload_id == upload_id
        ).all()
        
        # Calculate statistics
        total_validations = len(all_results)
        passed = sum(1 for r in all_results if r.is_valid)
        failed = total_validations - passed
        errors = sum(1 for r in all_results if r.severity == Severity.ERROR and not r.is_valid)
        warnings = sum(1 for r in all_results if r.severity == Severity.WARNING and not r.is_valid)
        
        # Get unique rules applied
        rules_applied = set(r.rule_name for r in all_results)
        
        return {
            "total_validations": total_validations,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "warnings": warnings,
            "pass_rate": round((passed / total_validations * 100) if total_validations > 0 else 0, 2),
            "rules_applied": list(rules_applied),
            "rules_count": len(rules_applied)
        }
    
    def revalidate_record(self, data_id: UUID, industry: str) -> List[EngineValidationResult]:
        """
        Re-run validation for a single record
        
        Args:
            data_id: UUID of the normalized data record
            industry: Industry category
        
        Returns:
            List of validation results
        """
        # Get the record
        record = self.db.query(NormalizedData).filter(
            NormalizedData.id == data_id
        ).first()
        
        if not record:
            raise ValueError(f"Record {data_id} not found")
        
        # Convert to validation record
        validation_record = NormalizedRecord(
            id=record.id,
            indicator=record.indicator_id,
            value=record.normalized_value,
            unit=record.normalized_unit,
            original_value=record.original_value,
            original_unit=record.original_unit,
            metadata={}
        )
        
        # Run validation
        results = self.engine.validate_record(validation_record, industry)
        
        # Delete old validation results for this record
        self.db.query(DBValidationResult).filter(
            DBValidationResult.data_id == data_id
        ).delete()
        
        # Save new results
        if results:
            self.save_validation_results(results, record.upload_id)
        
        return results
