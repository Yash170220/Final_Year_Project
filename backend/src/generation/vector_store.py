"""Qdrant vector store for RAG-based ESG report generation."""
import logging
import uuid
from typing import Dict, List, Optional
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

VALIDATED_DATA_COLLECTION = "validated_data"
FRAMEWORK_DEFS_COLLECTION = "framework_definitions"
VECTOR_SIZE = 384
BATCH_SIZE = 500


class VectorStore:
    """Qdrant-backed vector store for validated ESG data and framework definitions."""

    def __init__(self, host: str = "localhost", port: int = 6333):
        self.client = QdrantClient(host=host, port=port)
        self.encoder = SentenceTransformer("all-MiniLM-L6-v2")
        self._ensure_collections()

    def _ensure_collections(self) -> None:
        """Create collections if they don't already exist."""
        existing = {c.name for c in self.client.get_collections().collections}

        for name in (VALIDATED_DATA_COLLECTION, FRAMEWORK_DEFS_COLLECTION):
            if name not in existing:
                self.client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(
                        size=VECTOR_SIZE, distance=Distance.COSINE
                    ),
                )
                logger.info(f"Created Qdrant collection: {name}")

    # ------------------------------------------------------------------
    # Validated data
    # ------------------------------------------------------------------

    def add_validated_data(
        self, upload_id: UUID, records: List[Dict]
    ) -> int:
        """Embed and upsert validated ESG records.

        Each record dict should contain:
            data_id, indicator, value, unit, period, facility

        Returns the number of points upserted.
        """
        points: List[PointStruct] = []

        for record in records:
            text = (
                f"{record.get('facility', 'Unknown facility')} consumed "
                f"{record.get('value', '')} {record.get('unit', '')} of "
                f"{record.get('indicator', '')} in {record.get('period', '')}"
            )
            embedding = self.encoder.encode(text).tolist()

            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "upload_id": str(upload_id),
                    "data_id": str(record.get("data_id", "")),
                    "indicator": record.get("indicator", ""),
                    "value": record.get("value"),
                    "unit": record.get("unit", ""),
                    "period": record.get("period", ""),
                    "facility": record.get("facility", ""),
                    "text": text,
                },
            )
            points.append(point)

            if len(points) >= BATCH_SIZE:
                self.client.upsert(
                    collection_name=VALIDATED_DATA_COLLECTION, points=points
                )
                logger.info(f"Upserted batch of {len(points)} validated-data points")
                points = []

        if points:
            self.client.upsert(
                collection_name=VALIDATED_DATA_COLLECTION, points=points
            )
            logger.info(f"Upserted final batch of {len(points)} validated-data points")

        total = len(records)
        logger.info(f"Added {total} validated-data records for upload {upload_id}")
        return total

    # ------------------------------------------------------------------
    # Framework definitions
    # ------------------------------------------------------------------

    def add_framework_definitions(self, definitions: List[Dict]) -> int:
        """Embed and upsert framework/indicator definitions.

        Each dict should contain:
            indicator_id, indicator_name, definition, unit, calculation,
            framework
        """
        points: List[PointStruct] = []

        for defn in definitions:
            text = (
                f"{defn.get('indicator_name', '')}: "
                f"{defn.get('definition', '')}. "
                f"Calculation: {defn.get('calculation', 'N/A')}"
            )
            embedding = self.encoder.encode(text).tolist()

            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "indicator_id": str(defn.get("indicator_id", "")),
                    "indicator_name": defn.get("indicator_name", ""),
                    "definition": defn.get("definition", ""),
                    "unit": defn.get("unit", ""),
                    "calculation": defn.get("calculation", ""),
                    "framework": defn.get("framework", "BRSR"),
                    "text": text,
                },
            )
            points.append(point)

            if len(points) >= BATCH_SIZE:
                self.client.upsert(
                    collection_name=FRAMEWORK_DEFS_COLLECTION, points=points
                )
                points = []

        if points:
            self.client.upsert(
                collection_name=FRAMEWORK_DEFS_COLLECTION, points=points
            )

        total = len(definitions)
        logger.info(f"Added {total} framework definitions")
        return total

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_validated_data(
        self,
        query: str,
        upload_id: UUID,
        top_k: int = 5,
    ) -> List[Dict]:
        """Semantic search over validated data scoped to a single upload."""
        query_vector = self.encoder.encode(query).tolist()

        response = self.client.query_points(
            collection_name=VALIDATED_DATA_COLLECTION,
            query=query_vector,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="upload_id",
                        match=MatchValue(value=str(upload_id)),
                    )
                ]
            ),
            limit=top_k,
        )

        return [
            {
                "text": hit.payload.get("text", ""),
                "indicator": hit.payload.get("indicator", ""),
                "value": hit.payload.get("value"),
                "unit": hit.payload.get("unit", ""),
                "period": hit.payload.get("period", ""),
                "facility": hit.payload.get("facility", ""),
                "similarity": round(hit.score, 4),
                "data_id": hit.payload.get("data_id", ""),
            }
            for hit in response.points
        ]

    def search_framework_definitions(
        self,
        query: str,
        framework: str = "BRSR",
        top_k: int = 3,
    ) -> List[Dict]:
        """Semantic search over framework indicator definitions."""
        query_vector = self.encoder.encode(query).tolist()

        response = self.client.query_points(
            collection_name=FRAMEWORK_DEFS_COLLECTION,
            query=query_vector,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="framework",
                        match=MatchValue(value=framework),
                    )
                ]
            ),
            limit=top_k,
        )

        return [
            {
                "indicator_name": hit.payload.get("indicator_name", ""),
                "definition": hit.payload.get("definition", ""),
                "unit": hit.payload.get("unit", ""),
                "calculation": hit.payload.get("calculation", ""),
                "framework": hit.payload.get("framework", ""),
                "similarity": round(hit.score, 4),
                "text": hit.payload.get("text", ""),
            }
            for hit in response.points
        ]
