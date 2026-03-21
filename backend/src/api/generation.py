"""API endpoint for RAG-based narrative generation with AI recommendations."""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.common.config import settings
from src.common.database import get_db
from src.common.models import (
    NormalizedData,
    Upload,
    UploadStatus,
)
from src.common.schemas import (
    CitationDetail,
    ErrorResponse,
    GenerationRequest,
    GenerationResponse,
    GenerationSummary,
    NarrativeItem,
    RecommendationItem,
)
from src.generation.rag_generator import RAGGenerator
from src.generation.recommendation_engine import RecommendationEngine
from src.generation.vector_store import VectorStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/generation", tags=["generation"])

# Priority indicators — generate narratives for these first
PRIORITY_INDICATORS = [
    "Scope 1 GHG Emissions",
    "Total Electricity Consumption",
    "Total Water Consumption",
    "Non-Hazardous Waste Generated",
]

_vector_store: VectorStore | None = None
_rag_generator: RAGGenerator | None = None
_rec_engine: RecommendationEngine | None = None


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


def _get_rec_engine() -> RecommendationEngine:
    global _rec_engine
    if _rec_engine is None:
        _rec_engine = RecommendationEngine(
            groq_api_key=settings.groq.api_key,
            model=settings.groq.model,
        )
    return _rec_engine


def _load_validated_data(upload_id: UUID, db: Session) -> list[dict]:
    """Return validated NormalizedData rows as plain dicts."""
    rows = (
        db.query(NormalizedData)
        .filter(NormalizedData.upload_id == upload_id)
        .all()
    )
    records = []
    for r in rows:
        indicator_name = (
            r.indicator.matched_indicator if r.indicator else str(r.indicator_id)
        )
        records.append({
            "data_id": str(r.id),
            "indicator": indicator_name,
            "value": r.normalized_value,
            "unit": r.normalized_unit,
            # FIX: Use facility/period from NormalizedData columns directly
            "period": r.period or "",
            "facility": r.facility or "",
        })
    return records


def _push_to_qdrant(upload_id: UUID, records: list[dict], vs: VectorStore) -> int:
    if not records:
        return 0
    return vs.add_validated_data(upload_id, records)


def _generate_single(
    rag: RAGGenerator,
    section: str,
    upload_id: UUID,
    indicator: str,
    framework: str,
) -> NarrativeItem:
    """Generate a single narrative — runs in thread pool."""
    result = rag.generate_narrative(
        section_type=section,
        upload_id=upload_id,
        indicator=indicator,
        framework=framework,
    )
    cit_details = [
        CitationDetail(**d)
        for d in result["citations"].get("details", [])
    ]
    content_text = result["content"]
    return NarrativeItem(
        indicator=result["indicator"],
        section=result["section_type"],
        content=content_text,
        citations=cit_details,
        verification_rate=result["verification_rate"],
        word_count=len(content_text.split()),
    )


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
        "Generates grounded narratives for each section x indicator combination. "
        "Runs in parallel for speed. Defaults to top 4 priority ESG indicators. "
        "Optionally includes AI-powered improvement recommendations."
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

    validated_data = _load_validated_data(upload_id, db)
    if not validated_data:
        raise HTTPException(
            status_code=409,
            detail="No normalized data found. Run normalization before generation.",
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
        loaded = _push_to_qdrant(upload_id, validated_data, vs)
        logger.info(f"Loaded {loaded} validated records into Qdrant for {upload_id}")
    except Exception as exc:
        logger.error(f"Failed to load data into Qdrant: {exc}")
        raise HTTPException(
            status_code=500, detail=f"Failed to load data into vector store: {exc}"
        )

    # FIX: Limit to priority indicators by default to avoid 80+ sequential Groq calls
    indicators = body.indicators
    if not indicators:
        all_indicators = sorted(set(d["indicator"] for d in validated_data))
        # Use priority list if available, otherwise take first 4
        indicators = [i for i in PRIORITY_INDICATORS if i in all_indicators]
        if not indicators:
            indicators = all_indicators[:4]

    logger.info(f"Generating narratives for {len(indicators)} indicators x {len(body.sections)} sections")

    # FIX: Run all narrative generations in parallel using ThreadPoolExecutor
    # Groq calls are I/O-bound so parallelism gives ~5x speedup
    loop = asyncio.get_event_loop()
    tasks = [
        (indicator, section)
        for indicator in indicators
        for section in body.sections
    ]

    narratives: list[NarrativeItem] = []
    errors_encountered = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(
                _generate_single, rag, section, upload_id, indicator, body.framework
            ): (indicator, section)
            for indicator, section in tasks
        }

        for future, (indicator, section) in futures.items():
            try:
                narrative = future.result()
                narratives.append(narrative)
            except Exception as exc:
                logger.error(f"Narrative failed for {indicator}/{section}: {exc}")
                errors_encountered.append(f"{indicator}/{section}: {exc}")

    if errors_encountered and not narratives:
        raise HTTPException(
            status_code=500,
            detail=f"All narrative generations failed: {errors_encountered[0]}",
        )

    # Sort narratives by indicator then section for consistent ordering
    section_order = {s: i for i, s in enumerate(body.sections)}
    narratives.sort(key=lambda n: (n.indicator, section_order.get(n.section, 99)))

    # Recommendations
    recommendations: list[RecommendationItem] | None = None
    high_priority_count = 0
    if body.include_recommendations:
        try:
            rec = _get_rec_engine()
            industry = "cement"
            if upload.file_metadata:
                industry = upload.file_metadata.get("industry", "cement")
            raw_recs = rec.generate_recommendations(
                upload_id=str(upload_id),
                validated_data=validated_data,
                industry=industry,
            )
            recommendations = [RecommendationItem(**r) for r in raw_recs]
            high_priority_count = sum(
                1 for r in recommendations if r.priority == "high"
            )
        except Exception as exc:
            logger.warning(f"Recommendation generation failed (non-fatal): {exc}")

    total = len(narratives)
    total_citations = sum(len(n.citations) for n in narratives)
    overall_rate = (
        sum(n.verification_rate for n in narratives) / total if total else 1.0
    )

    return GenerationResponse(
        upload_id=upload_id,
        framework=body.framework,
        narratives=narratives,
        recommendations=recommendations,
        summary=GenerationSummary(
            total_narratives=total,
            total_citations=total_citations,
            overall_verification_rate=round(overall_rate, 4),
            high_priority_recommendations=high_priority_count,
        ),
    )