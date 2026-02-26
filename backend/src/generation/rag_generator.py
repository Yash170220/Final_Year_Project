"""RAG-based narrative generator for ESG reports using Groq LLM."""
import json
import logging
import re
import time
from typing import Dict, List, Optional
from uuid import UUID

import redis
from groq import Groq

from src.generation.vector_store import VectorStore

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF = 1.0
CACHE_TTL_SECONDS = 3600
CITATION_TOLERANCE = 0.001  # ±0.1%


class RAGGenerator:
    """Generates ESG report narratives grounded in validated data via RAG."""

    def __init__(
        self,
        vector_store: VectorStore,
        groq_api_key: str,
        model: str = "llama-3.1-70b-versatile",
        temperature: float = 0.3,
        redis_url: str = "redis://localhost:6379/0",
    ):
        self.vector_store = vector_store
        self.client = Groq(api_key=groq_api_key)
        self.model = model
        self.temperature = temperature

        try:
            self.cache = redis.from_url(redis_url, decode_responses=True)
            self.cache.ping()
            logger.info("Redis cache connected for RAG generator")
        except Exception:
            logger.warning("Redis unavailable — RAG generator will run without cache")
            self.cache = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_narrative(
        self,
        section_type: str,
        upload_id: UUID,
        indicator: str,
        framework: str = "BRSR",
    ) -> Dict:
        """Generate a grounded narrative for a single indicator section.

        Returns dict with: section_type, indicator, content, citations,
        verification_rate.
        """
        cache_key = f"{upload_id}:{indicator}:{section_type}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            logger.info(f"Cache hit for {cache_key}")
            return cached

        data = self.vector_store.search_validated_data(
            query=indicator, upload_id=upload_id, top_k=5
        )
        framework_defs = self.vector_store.search_framework_definitions(
            query=indicator, framework=framework, top_k=1
        )
        framework_def = framework_defs[0] if framework_defs else {
            "indicator_name": indicator,
            "definition": "N/A",
            "calculation": "N/A",
        }

        prompt = self._build_prompt(section_type, data, framework_def, framework)
        content = self._call_llm(prompt)
        citations = self._verify_citations(content, data)

        result = {
            "section_type": section_type,
            "indicator": indicator,
            "content": content,
            "citations": citations,
            "verification_rate": citations["verification_rate"],
        }

        self._set_cache(cache_key, result)
        return result

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    @staticmethod
    def _build_prompt(
        section_type: str,
        data: List[Dict],
        framework_def: Dict,
        framework: str = "BRSR",
    ) -> str:
        indicator_name = framework_def.get("indicator_name", "Unknown")
        definition = framework_def.get("definition", "N/A")
        calculation = framework_def.get("calculation", "N/A")

        data_block = "\n".join(
            f"  [Table {i + 1}] {row.get('text', '')} "
            f"(value={row.get('value')}, unit={row.get('unit', '')}, "
            f"period={row.get('period', '')}, facility={row.get('facility', '')})"
            for i, row in enumerate(data)
        )
        if not data_block:
            data_block = "  No data available."

        return (
            f"Generate a {section_type} section for the indicator: {indicator_name}.\n\n"
            f"RULES:\n"
            f"1. Use ONLY the provided data — no fabrication.\n"
            f"2. Cite numbers with [Table X] referencing the data rows below.\n"
            f"3. Follow {framework} terminology and reporting conventions.\n"
            f"4. 100-150 words, factual, past tense.\n\n"
            f"Framework definition: {definition}\n"
            f"Calculation method: {calculation}\n\n"
            f"Data:\n{data_block}\n\n"
            f"Generate now."
        )

    # ------------------------------------------------------------------
    # LLM call with retry
    # ------------------------------------------------------------------

    def _call_llm(self, prompt: str) -> str:
        last_err: Optional[Exception] = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                t0 = time.perf_counter()
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.temperature,
                )
                elapsed = time.perf_counter() - t0
                logger.info(f"Groq inference in {elapsed:.2f}s (attempt {attempt})")
                return response.choices[0].message.content
            except Exception as exc:
                last_err = exc
                logger.warning(f"Groq attempt {attempt}/{MAX_RETRIES} failed: {exc}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF * attempt)
        raise RuntimeError(f"Groq API failed after {MAX_RETRIES} retries: {last_err}")

    # ------------------------------------------------------------------
    # Citation verification
    # ------------------------------------------------------------------

    @staticmethod
    def _verify_citations(content: str, data: List[Dict]) -> Dict:
        """Extract numeric claims from the generated text and check against source data."""
        numbers_in_content = re.findall(r"[\d,]+\.?\d*", content)
        parsed_claims: List[float] = []
        for raw in numbers_in_content:
            try:
                parsed_claims.append(float(raw.replace(",", "")))
            except ValueError:
                continue

        data_values: List[float] = []
        for row in data:
            val = row.get("value")
            if val is not None:
                try:
                    data_values.append(float(val))
                except (ValueError, TypeError):
                    continue

        verified = 0
        for claim in parsed_claims:
            for dv in data_values:
                if dv == 0:
                    if claim == 0:
                        verified += 1
                        break
                elif abs(claim - dv) / abs(dv) <= CITATION_TOLERANCE:
                    verified += 1
                    break

        total = len(parsed_claims)
        rate = (verified / total) if total > 0 else 1.0

        return {
            "total_claims": total,
            "verified_claims": verified,
            "verification_rate": round(rate, 4),
        }

    # ------------------------------------------------------------------
    # Redis cache helpers
    # ------------------------------------------------------------------

    def _get_cache(self, key: str) -> Optional[Dict]:
        if self.cache is None:
            return None
        try:
            raw = self.cache.get(f"rag:{key}")
            return json.loads(raw) if raw else None
        except Exception:
            return None

    def _set_cache(self, key: str, value: Dict) -> None:
        if self.cache is None:
            return
        try:
            self.cache.setex(f"rag:{key}", CACHE_TTL_SECONDS, json.dumps(value))
        except Exception as exc:
            logger.warning(f"Failed to cache RAG result: {exc}")
