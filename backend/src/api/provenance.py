"""API endpoint for W3C PROV-O provenance tracing."""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from src.common.provenance import get_provenance_tracker
from src.common.schemas import (
    ErrorResponse,
    LineageStep,
    ProvenanceActivity,
    ProvenanceResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/provenance", tags=["provenance"])

ALLOWED_FORMATS = {"turtle", "json-ld", "xml", "n3", "nt"}
FORMAT_MEDIA_TYPES = {
    "turtle": "text/turtle",
    "json-ld": "application/ld+json",
    "xml": "application/rdf+xml",
    "n3": "text/n3",
    "nt": "application/n-triples",
}


@router.get(
    "/{entity_id}",
    response_model=ProvenanceResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Entity not found"},
        400: {"model": ErrorResponse, "description": "Invalid format"},
    },
    summary="Trace provenance lineage",
    description=(
        "Returns the full derivation chain for an entity back to the "
        "original uploaded file. Use ?format=turtle to get raw W3C PROV graph."
    ),
)
async def trace_provenance(
    entity_id: str,
    format: Optional[str] = Query(
        None,
        description="RDF serialization format (turtle, json-ld, xml, n3, nt)",
    ),
):
    tracker = get_provenance_tracker()

    if not tracker.entity_exists(entity_id):
        raise HTTPException(
            status_code=404,
            detail=f"Entity '{entity_id}' not found in provenance graph",
        )

    if format is not None:
        fmt = format.lower()
        if fmt not in ALLOWED_FORMATS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format '{format}'. Use one of: {', '.join(sorted(ALLOWED_FORMATS))}",
            )
        rdf_data = tracker.export_provenance(entity_id, fmt=fmt)
        return PlainTextResponse(
            content=rdf_data,
            media_type=FORMAT_MEDIA_TYPES.get(fmt, "text/plain"),
        )

    entity_type = tracker.get_entity_type(entity_id) or ""
    lineage_raw = tracker.query_lineage(entity_id)

    chain = [
        LineageStep(
            entity_id=step["entity_id"],
            entity_type=step.get("entity_type", ""),
            activity=ProvenanceActivity(**step.get("activity", {})),
        )
        for step in lineage_raw
    ]

    return ProvenanceResponse(
        entity_id=entity_id,
        entity_type=entity_type,
        lineage_chain=chain,
        total_steps=len(chain),
    )
