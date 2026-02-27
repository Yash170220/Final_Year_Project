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


class MatchingReviewItem(BaseModel):
    """Single review item within a bulk review request"""
    indicator_id: UUID
    approved: bool
    corrected_match: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = Field(None, max_length=1000)

    @field_validator("corrected_match")
    @classmethod
    def validate_corrected_match(cls, v: Optional[str], info) -> Optional[str]:
        if not info.data.get("approved") and not v:
            raise ValueError("corrected_match required when approved=False")
        return v


class MatchingReviewRequest(BaseModel):
    """Bulk review request body for POST /{upload_id}"""
    reviews: List[MatchingReviewItem]


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


class MatchingStatsSchema(BaseModel):
    """Matching statistics"""
    total_headers: int = 0
    auto_approved: int = 0
    needs_review: int = 0
    avg_confidence: float = 0.0


class MatchingResultItem(BaseModel):
    """Single matching result row"""
    indicator_id: UUID
    original_header: str
    matched_indicator: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    requires_review: bool


class ReviewQueueItem(MatchingResultItem):
    """Review queue entry (extends result with reasoning)"""
    reasoning: Optional[str] = None


class MatchingResponse(BaseModel):
    """Consolidated GET response for matching"""
    upload_id: UUID
    status: str
    stats: MatchingStatsSchema
    results: List[MatchingResultItem] = Field(default_factory=list)
    review_queue: List[ReviewQueueItem] = Field(default_factory=list)


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

class UploadMetadata(BaseModel):
    """Metadata about an uploaded file"""
    row_count: int = 0
    column_count: int = 0
    file_size_mb: Optional[float] = None
    facility_name: Optional[str] = None
    reporting_period: Optional[str] = None


class UploadDetailResponse(BaseModel):
    """Consolidated upload detail: status + preview in one response"""
    upload_id: UUID
    filename: str
    file_type: str
    status: str
    upload_time: datetime
    metadata: UploadMetadata
    headers: List[str] = Field(default_factory=list)
    preview: List[Dict] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class IndicatorListResponse(BaseModel):
    """List of matched indicators"""
    upload_id: UUID
    indicators: List[MatchingResult]
    total_count: int
    review_required_count: int


# --- Normalization schemas ---

class NormalizationSummarySchema(BaseModel):
    """Summary stats for normalization"""
    total_records: int = 0
    successfully_normalized: int = 0
    failed_normalization: int = 0
    normalization_rate: float = 0.0


class NormalizationConversion(BaseModel):
    """Single conversion type applied"""
    indicator: str
    from_unit: str
    to_unit: str
    conversion_factor: float
    conversion_source: str = "Unknown"
    record_count: int = 0


class NormalizationErrorItem(BaseModel):
    """Single normalization error"""
    indicator: str
    issue: str
    suggestion: str


class NormalizationDataSample(BaseModel):
    """Single row from normalized data"""
    data_id: UUID
    indicator: str
    original_value: float
    original_unit: str
    normalized_value: float
    normalized_unit: str


class NormalizationResponse(BaseModel):
    """Consolidated GET response for normalization"""
    upload_id: UUID
    status: str
    summary: NormalizationSummarySchema
    conversions: List[NormalizationConversion] = Field(default_factory=list)
    errors: List[NormalizationErrorItem] = Field(default_factory=list)
    data_sample: List[NormalizationDataSample] = Field(default_factory=list)


# --- Validation consolidated schemas ---

class ValidationSummarySchema(BaseModel):
    """Validation summary stats"""
    total_records: int = 0
    valid_records: int = 0
    records_with_errors: int = 0
    records_with_warnings: int = 0
    validation_pass_rate: float = 0.0
    unreviewed_errors: int = 0


class ValidationErrorItem(BaseModel):
    """Single validation error"""
    result_id: UUID
    indicator: str
    rule_name: str
    severity: str
    message: str
    actual_value: Optional[float] = None
    expected_range: Optional[List[float]] = None
    citation: Optional[str] = None
    suggested_fixes: List[str] = Field(default_factory=list)
    reviewed: bool = False
    reviewer_notes: Optional[str] = None


class ValidationWarningItem(BaseModel):
    """Single validation warning"""
    result_id: UUID
    rule_name: str
    severity: str
    message: str
    reviewed: bool = False


class ValidationDetailResponse(BaseModel):
    """Consolidated GET response for validation"""
    upload_id: UUID
    status: str
    industry: Optional[str] = None
    summary: ValidationSummarySchema
    error_breakdown: Dict[str, int] = Field(default_factory=dict)
    warning_breakdown: Dict[str, int] = Field(default_factory=dict)
    errors: List[ValidationErrorItem] = Field(default_factory=list)
    warnings: List[ValidationWarningItem] = Field(default_factory=list)


class ValidationReviewItem(BaseModel):
    """Single review action"""
    result_id: UUID
    reviewed: bool = True
    notes: Optional[str] = None


class ValidationReviewRequest(BaseModel):
    """Bulk review request for POST /{upload_id}"""
    reviews: List[ValidationReviewItem]


# --- Generation schemas ---

class GenerationRequest(BaseModel):
    """Request body for narrative generation"""
    sections: List[str] = Field(
        ..., min_length=1, description="Section types to generate"
    )
    indicators: List[str] = Field(
        ..., min_length=1, description="Indicator names to generate for"
    )
    framework: str = Field(default="BRSR", description="Framework to use")


class NarrativeCitation(BaseModel):
    """Citation verification details"""
    total_claims: int = 0
    verified_claims: int = 0
    verification_rate: float = 1.0


class NarrativeItem(BaseModel):
    """Single generated narrative"""
    indicator: str
    section: str
    content: str
    citations: NarrativeCitation
    verification_rate: float = 1.0


class GenerationSummary(BaseModel):
    """Summary stats for the generation batch"""
    total_narratives: int = 0
    overall_verification_rate: float = 1.0


class GenerationResponse(BaseModel):
    """Response for POST /api/v1/generation/{upload_id}"""
    upload_id: UUID
    narratives: List[NarrativeItem] = Field(default_factory=list)
    summary: GenerationSummary


# --- Provenance schemas ---

class ProvenanceActivity(BaseModel):
    """Activity that produced a lineage step"""
    type: str = ""
    timestamp: str = ""
    agent: str = ""


class LineageStep(BaseModel):
    """Single step in the provenance chain"""
    entity_id: str
    entity_type: str = ""
    activity: ProvenanceActivity = Field(default_factory=ProvenanceActivity)


class ProvenanceResponse(BaseModel):
    """Response for GET /api/v1/provenance/{entity_id}"""
    entity_id: str
    entity_type: str = ""
    lineage_chain: List[LineageStep] = Field(default_factory=list)
    total_steps: int = 0


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
