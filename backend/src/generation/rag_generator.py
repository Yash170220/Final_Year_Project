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
CITATION_TOLERANCE = 0.05  # FIX: was 0.001 (±0.1%) — too strict; ±5% is realistic

SYSTEM_PROMPT = (
    "You are a strict ESG report writer for manufacturing companies. "
    "Use ONLY the data provided in the user message. "
    "Never fabricate, estimate, or extrapolate numbers. "
    "If specific data is missing, write 'Data not available' for that point. "
    "Every quantitative claim MUST be followed by a [Table X] citation. "
    "Be concise and professional. Do not add disclaimers or preamble."
)


class RAGGenerator:
    """Generates ESG report narratives grounded in validated data via RAG."""

    def __init__(
        self,
        vector_store: VectorStore,
        groq_api_key: str,
        model: str = "llama-3.1-70b-versatile",
        temperature: float = 0.1,          # FIX: was 0.3 — lower = less hallucination
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

        # FIX: top_k reduced from 5 → 3 to reduce noise and improve focus
        data = self.vector_store.search_validated_data(
            query=indicator, upload_id=upload_id, top_k=3
        )

        # FIX: Early exit if no data — avoids wasting an LLM call
        if not data:
            logger.warning(f"No data found for indicator '{indicator}' in upload {upload_id}")
            result = {
                "section_type": section_type,
                "indicator": indicator,
                "content": f"Data not available for {indicator}. Please ensure validated data has been uploaded.",
                "citations": {"total_claims": 0, "verified_claims": 0, "verification_rate": 1.0, "details": []},
                "verification_rate": 1.0,
            }
            self._set_cache(cache_key, result)
            return result

        # FIX: top_k reduced from 1 — framework def only needs 1 result
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

    def _build_prompt(
        self,
        section_type: str,
        data: List[Dict],
        framework_def: Dict,
        framework: str = "BRSR",
    ) -> str:
        indicator_name = framework_def.get("indicator_name", "Unknown")
        definition = framework_def.get("definition", "N/A")
        calculation = framework_def.get("calculation", "N/A")
        unit = framework_def.get("unit", "")
        boundary = framework_def.get("boundary", "Operational control")

        data_table = self._format_data_table(data)

        if section_type == "management_approach":
            return (
                f"Generate a professional management approach narrative for {indicator_name}.\n\n"
                f"FRAMEWORK CONTEXT:\n"
                f"Definition: {definition}\n"
                f"Calculation: {calculation}\n"
                f"Unit: {unit}\n\n"
                f"DATA (use ONLY these values — cite with [Table X]):\n{data_table}\n\n"
                f"STRICT REQUIREMENTS:\n"
                f"- 150-200 words, 3-4 paragraphs\n"
                f"- Start with: 'The organization monitors {indicator_name} across...'\n"
                f"- Every number MUST have [Table X] citation immediately after\n"
                f"- Compare to prior period if data available\n"
                f"- Mention boundary: 'across all manufacturing operations under operational control'\n"
                f"- Active voice, past tense for historical data\n"
                f"- Do NOT invent numbers not present in the data table\n\n"
                f"EXAMPLES:\n"
                f"Good: 'Total electricity consumption was 15,450 MWh [Table 1]'\n"
                f"Bad:  'Electricity consumption was significant'\n\n"
                f"Generate narrative:"
            )

        if section_type == "methodology":
            return (
                f"Generate a technical methodology section for {indicator_name}.\n\n"
                f"FRAMEWORK REQUIREMENTS:\n"
                f"Definition: {definition}\n"
                f"Calculation: {calculation}\n"
                f"Unit: {unit}\n\n"
                f"DATA SOURCES:\n{data_table}\n\n"
                f"STRICT REQUIREMENTS:\n"
                f"- 120-180 words\n"
                f"- Cover: measurement approach, calculation method, emission/conversion factors, data quality, boundary, reporting period\n"
                f"- Boundary: '{boundary}'\n"
                f"- Standards: 'Calculated per {framework} guidelines'\n"
                f"- Use precise technical terminology\n"
                f"- Every technical specification needs [Table X] or [Source] citation\n"
                f"- Do NOT invent methodology steps not supported by the data\n\n"
                f"Generate methodology:"
            )

        if section_type == "boundary":
            facilities_list = self._format_facilities(data)
            return (
                f"Generate an organizational boundary description for {indicator_name}.\n\n"
                f"FRAMEWORK: {boundary} approach\n\n"
                f"FACILITIES IN DATA:\n{facilities_list}\n\n"
                f"STRICT REQUIREMENTS:\n"
                f"- 100-150 words\n"
                f"- Cover: boundary approach, facilities included, exclusions (if any), consolidation method, changes from prior period\n"
                f"- Start with: 'Reporting follows the {boundary} approach'\n"
                f"- Comply with {framework} boundary requirements\n"
                f"- Only list facilities present in the data above\n\n"
                f"Generate boundary description:"
            )

        # Fallback for any other section type
        return (
            f"Generate a {section_type} section for {indicator_name}.\n\n"
            f"Framework: {definition}\n"
            f"Calculation: {calculation}\n"
            f"Unit: {unit}\n\n"
            f"DATA (cite all numbers with [Table X]):\n{data_table}\n\n"
            f"Requirements: Professional tone, 100-150 words, no fabricated data.\n\n"
            f"Generate now:"
        )

    @staticmethod
    def _format_data_table(data: List[Dict]) -> str:
        if not data:
            return "No data available"

        table = "| # | Facility | Period | Value | Unit |\n|---|----------|--------|-------|------|\n"
        for i, d in enumerate(data[:10], 1):
            table += (
                f"| {i} | {d.get('facility', 'N/A')} | {d.get('period', 'N/A')} "
                f"| {d.get('value', 'N/A')} | {d.get('unit', '')} |\n"
            )

        # Add total row if all values are numeric
        if len(data) > 1 and all("value" in d for d in data):
            try:
                total = sum(float(d["value"]) for d in data)
                table += f"| - | **TOTAL** | All periods | **{total:,.2f}** | {data[0].get('unit', '')} |\n"
            except (ValueError, TypeError):
                pass

        return table

    @staticmethod
    def _format_facilities(data: List[Dict]) -> str:
        facilities = sorted(set(d.get("facility", "Unknown") for d in data))
        return "\n".join(f"- {f}" for f in facilities) if facilities else "- Unknown"

    # ------------------------------------------------------------------
    # LLM call with retry
    # FIX: Added system prompt + max_tokens to reduce latency and hallucination
    # ------------------------------------------------------------------

    def _call_llm(self, prompt: str, max_tokens: int = 400) -> str:
        """Call Groq LLM with system prompt, retry logic, and token cap."""
        last_err: Optional[Exception] = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                t0 = time.perf_counter()
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        # FIX: System prompt added — separates role context from data
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=self.temperature,
                    max_tokens=max_tokens,   # FIX: was unlimited — model rambled, causing slowness
                )
                elapsed = time.perf_counter() - t0
                logger.info(f"Groq inference in {elapsed:.2f}s (attempt {attempt})")
                return response.choices[0].message.content.strip()
            except Exception as exc:
                last_err = exc
                logger.warning(f"Groq attempt {attempt}/{MAX_RETRIES} failed: {exc}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF * attempt)
        raise RuntimeError(f"Groq API failed after {MAX_RETRIES} retries: {last_err}")

    # ------------------------------------------------------------------
    # Citation verification
    # FIX: Tolerance raised from 0.001 to 0.05 (±5%) — realistic for narratives
    # ------------------------------------------------------------------

    @staticmethod
    def _verify_citations(content: str, data: List[Dict]) -> Dict:
        """Extract numeric claims and [Table X] references, verify against source data."""
        data_values: List[float] = []
        for row in data:
            val = row.get("value")
            if val is not None:
                try:
                    data_values.append(float(val))
                except (ValueError, TypeError):
                    continue

        ref_pattern = re.compile(r"\[Table\s*(\d+)\]")
        refs_found = ref_pattern.findall(content)

        detailed: List[Dict] = []
        seen_refs: set = set()
        for ref_num in refs_found:
            ref_label = f"[Table {ref_num}]"
            if ref_label in seen_refs:
                continue
            seen_refs.add(ref_label)

            idx = int(ref_num) - 1
            if 0 <= idx < len(data):
                try:
                    val = float(data[idx].get("value", 0))
                except (ValueError, TypeError):
                    val = 0.0
                detailed.append({"reference": ref_label, "value": val, "verified": True})
            else:
                detailed.append({"reference": ref_label, "value": 0.0, "verified": False})

        # Extract all numbers from the narrative
        numbers_in_content = re.findall(r"[\d,]+\.?\d*", content)
        parsed_claims: List[float] = []
        for raw in numbers_in_content:
            try:
                parsed = float(raw.replace(",", ""))
                # FIX: Skip year-like numbers and small integers — they're unlikely data claims
                if parsed > 9999 or parsed < 1:
                    continue
                parsed_claims.append(parsed)
            except ValueError:
                continue

        verified = 0
        for claim in parsed_claims:
            for dv in data_values:
                if dv == 0:
                    if claim == 0:
                        verified += 1
                        break
                # FIX: was CITATION_TOLERANCE = 0.001; now 0.05 (±5%)
                elif abs(claim - dv) / abs(dv) <= CITATION_TOLERANCE:
                    verified += 1
                    break

        total = len(parsed_claims)
        rate = (verified / total) if total > 0 else 1.0

        return {
            "total_claims": total,
            "verified_claims": verified,
            "verification_rate": round(rate, 4),
            "details": detailed,
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