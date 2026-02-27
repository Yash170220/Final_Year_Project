"""API endpoint for RAG-based narrative generation."""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.common.config import settings
from src.common.database import get_db
from src.common.models import (
    NormalizedData,
    Upload,
    UploadStatus,
    ValidationResult,
)
from src.common.schemas import (
    ErrorResponse,
    GenerationRequest,
    GenerationResponse,
    GenerationSummary,
    NarrativeCitation,
    NarrativeItem,
)
from src.generation.rag_generator import RAGGenerator
from src.generation.vector_store import VectorStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/generation", tags=["generation"])

_vector_store: VectorStore | None = None
_rag_generator: RAGGenerator | None = None


def _get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


def _get_rag_generator() -> RAGGenerator:
    global _rag_generator
    if _rag_generator is None:
        vs = _get_vector_store()
        _rag_generator = RAGGenerator(
            vector_store=vs,
            groq_api_key=settings.groq.api_key,
            model=settings.groq.model,
            temperature=settings.groq.temperature,
            redis_url=settings.redis.url,
        )
    return _rag_generator


def _load_validated_data_to_qdrant(
    upload_id: UUID, db: Session, vs: VectorStore
) -> int:
    """Query validated NormalizedData rows and push them into Qdrant."""
    rows = (
        db.query(NormalizedData)
        .filter(NormalizedData.upload_id == upload_id)
        .all()
    )
    if not rows:
        return 0

    records = []
    for r in rows:
        indicator_name = (
            r.indicator.matched_indicator if r.indicator else str(r.indicator_id)
        )
        facility = None
        period = None
        upload = r.upload
        if upload and upload.file_metadata:
            facility = upload.file_metadata.get("facility_name")
            period = upload.file_metadata.get("reporting_period")

        records.append(
            {
                "data_id": str(r.id),
                "indicator": indicator_name,
                "value": r.normalized_value,
                "unit": r.normalized_unit,
                "period": period or "",
                "facility": facility or "",
            }
        )

    return vs.add_validated_data(upload_id, records)


@router.post(
    "/{upload_id}",
    response_model=GenerationResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Upload not found"},
        409: {"model": ErrorResponse, "description": "Validation incomplete"},
        500: {"model": ErrorResponse, "description": "Generation failed"},
    },
    summary="Generate ESG report narratives",
    description=(
        "Generates grounded narratives for each section × indicator combination. "
        "Requires that the upload has been validated first."
    ),
)
async def generate_narratives(
    upload_id: UUID,
    body: GenerationRequest,
    db: Session = Depends(get_db),
):
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail=f"Upload {upload_id} not found")

    if upload.status != UploadStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Upload status is '{upload.status.value}'. "
                "Pipeline must be completed before generation."
            ),
        )

    has_validation = (
        db.query(ValidationResult)
        .join(NormalizedData, NormalizedData.id == ValidationResult.data_id)
        .filter(NormalizedData.upload_id == upload_id)
        .first()
    )
    if not has_validation:
        raise HTTPException(
            status_code=409,
            detail="No validation results found. Run validation before generation.",
        )

    try:
        vs = _get_vector_store()
        rag = _get_rag_generator()
    except Exception as exc:
        logger.error(f"Failed to initialise generation services: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Generation services unavailable (Qdrant or Groq not reachable)",
        )

    try:
        loaded = _load_validated_data_to_qdrant(upload_id, db, vs)
        logger.info(f"Loaded {loaded} validated records into Qdrant for {upload_id}")
    except Exception as exc:
        logger.error(f"Failed to load data into Qdrant: {exc}")
        raise HTTPException(
            status_code=500, detail=f"Failed to load data into vector store: {exc}"
        )

    narratives: list[NarrativeItem] = []
    for indicator in body.indicators:
        for section in body.sections:
            try:
                result = rag.generate_narrative(
                    section_type=section,
                    upload_id=upload_id,
                    indicator=indicator,
                    framework=body.framework,
                )
                narratives.append(
                    NarrativeItem(
                        indicator=result["indicator"],
                        section=result["section_type"],
                        content=result["content"],
                        citations=NarrativeCitation(**result["citations"]),
                        verification_rate=result["verification_rate"],
                    )
                )
            except Exception as exc:
                logger.error(
                    f"Narrative generation failed for {indicator}/{section}: {exc}"
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Groq generation failed for {indicator}/{section}: {exc}",
                )

    total = len(narratives)
    overall_rate = (
        sum(n.verification_rate for n in narratives) / total if total else 1.0
    )

    return GenerationResponse(
        upload_id=upload_id,
        narratives=narratives,
        summary=GenerationSummary(
            total_narratives=total,
            overall_verification_rate=round(overall_rate, 4),
        ),
    )
