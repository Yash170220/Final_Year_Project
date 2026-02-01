"""Pydantic schemas for API requests and responses"""
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# Request Schemas

class FileUploadRequest(BaseModel):
    """File upload request schema"""
    facility_name: str = Field(..., min_length=1, max_length=255)
    reporting_period: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$")

    @field_validator("reporting_period")
    @classmethod
    def validate_period(cls, v: str) -> str:
        """Validate reporting period format"""
        try:
            year, month = v.split("-")
            if not (1900 <= int(year) <= 2100):
                raise ValueError("Year must be between 1900 and 2100")
        except Exception:
            raise ValueError("Invalid reporting period format. Use YYYY-MM")
        return v


class MatchingReviewRequest(BaseModel):
    """Matching review request schema"""
    indicator_id: UUID
    approved: bool
    corrected_match: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = Field(None, max_length=1000)

    @field_validator("corrected_match")
    @classmethod
    def validate_corrected_match(cls, v: Optional[str], info) -> Optional[str]:
        """Ensure corrected_match is provided if not approved"""
        if not info.data.get("approved") and not v:
            raise ValueError("corrected_match required when approved=False")
        return v


# Response Schemas

class UploadResponse(BaseModel):
    """Upload response schema"""
    upload_id: UUID
    filename: str
    status: str
    detected_headers: List[str]
    preview_data: Dict[str, List]

    model_config = {"from_attributes": True}


class MatchingResult(BaseModel):
    """Matching result schema"""
    indicator_id: UUID
    original_header: str
    matched_indicator: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    requires_review: bool

    @field_validator("requires_review", mode="before")
    @classmethod
    def set_requires_review(cls, v, info) -> bool:
        """Auto-set requires_review based on confidence"""
        confidence = info.data.get("confidence", 0.0)
        return confidence < 0.85

    model_config = {"from_attributes": True}


class ValidationError(BaseModel):
    """Validation error detail schema"""
    data_id: UUID
    rule_name: str
    severity: str
    message: str
    citation: Optional[str] = None

    model_config = {"from_attributes": True}


class ValidationResponse(BaseModel):
    """Validation response schema"""
    total_records: int = Field(..., ge=0)
    valid_count: int = Field(..., ge=0)
    error_count: int = Field(..., ge=0)
    warning_count: int = Field(..., ge=0)
    errors: List[ValidationError] = Field(default_factory=list)

    @field_validator("total_records")
    @classmethod
    def validate_totals(cls, v: int, info) -> int:
        """Ensure counts add up correctly"""
        valid = info.data.get("valid_count", 0)
        errors = info.data.get("error_count", 0)
        warnings = info.data.get("warning_count", 0)
        if valid + errors != v:
            raise ValueError("valid_count + error_count must equal total_records")
        return v


# Additional Common Schemas

class UploadStatusResponse(BaseModel):
    """Upload status check response"""
    upload_id: UUID
    status: str
    progress: Optional[float] = Field(None, ge=0.0, le=100.0)
    message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IndicatorListResponse(BaseModel):
    """List of matched indicators"""
    upload_id: UUID
    indicators: List[MatchingResult]
    total_count: int
    review_required_count: int


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
