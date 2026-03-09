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
                f"You are an expert ESG report writer. Generate a professional "
                f"management approach narrative for {indicator_name}.\n\n"
                f"CONTEXT:\n"
                f"Framework Definition: {definition}\n"
                f"Calculation Method: {calculation}\n"
                f"Unit: {unit}\n\n"
                f"AVAILABLE DATA:\n{data_table}\n\n"
                f"REQUIREMENTS:\n"
                f'1. Start with organizational scope: "The organization monitors '
                f'{indicator_name} across X facilities..."\n'
                f'2. Present current performance with exact numbers and citations: "[Table X]"\n'
                f'3. Compare to baseline/prior period if data available: "representing a X% change from..."\n'
                f"4. Explain significant trends (>5% change)\n"
                f"5. Mention boundary and coverage: "
                f'"across all manufacturing operations under operational control"\n'
                f"6. Professional tone, active voice, past tense for historical data\n"
                f"7. 150-200 words, structured in 3-4 concise paragraphs\n"
                f"8. Every quantitative claim MUST have [Table X] citation\n\n"
                f"STYLE GUIDE:\n"
                f'Good: "Total electricity consumption was 15,450 MWh [Table 2]"\n'
                f'Bad:  "We used electricity"\n'
                f'Good: "Plant A achieved a 12% reduction through LED retrofits"\n'
                f'Bad:  "Things improved"\n\n'
                f"Generate professional narrative now:"
            )

        if section_type == "methodology":
            return (
                f"Generate technical methodology section for {indicator_name}.\n\n"
                f"FRAMEWORK REQUIREMENTS:\n"
                f"Definition: {definition}\n"
                f"Standard Calculation: {calculation}\n"
                f"Required Unit: {unit}\n\n"
                f"DATA SOURCES:\n{data_table}\n\n"
                f"STRUCTURE REQUIRED:\n"
                f'1. Measurement approach: "Data collected from [metering systems/invoices/direct measurement]"\n'
                f'2. Calculation methodology: "{calculation}"\n'
                f"3. Emission/conversion factors used (if applicable)\n"
                f'4. Data quality: "Measured data from calibrated meters with +/-2% accuracy"\n'
                f'5. Organizational boundary: "{boundary}"\n'
                f'6. Reporting period and frequency: "Monthly data aggregated for annual reporting"\n'
                f'7. Standards followed: "Calculated per {framework} guidelines"\n\n'
                f"TECHNICAL REQUIREMENTS:\n"
                f"- Use precise technical terminology\n"
                f"- Cite all emission factors, conversion factors, and standards\n"
                f"- Explain any deviations from standard methodology\n"
                f"- 120-180 words\n"
                f"- Every technical specification needs [Source] citation\n\n"
                f"Generate methodology now:"
            )

        if section_type == "boundary":
            facilities_list = self._format_facilities(data)
            return (
                f"Generate organizational boundary description for {indicator_name}.\n\n"
                f"FRAMEWORK: {boundary} approach\n\n"
                f"FACILITIES IN DATA:\n{facilities_list}\n\n"
                f"STRUCTURE:\n"
                f'1. Boundary approach: "Reporting follows [{boundary}] approach"\n'
                f"2. Facilities included: List all facilities with brief description\n"
                f'3. Exclusions (if any): "The following are excluded: [list with rationale]"\n'
                f'4. Consolidation method: "Data aggregated across all included facilities"\n'
                f'5. Changes from prior period: "No changes to boundary" or detail changes\n\n'
                f"REQUIREMENTS:\n"
                f"- Clear, unambiguous scope definition\n"
                f"- Justify exclusions if any\n"
                f"- 100-150 words\n"
                f"- Compliance with {framework} boundary requirements\n\n"
                f"Generate boundary description now:"
            )

        return (
            f"Generate {section_type} section for {indicator_name} "
            f"using ONLY the provided data. Cite with [Table X].\n\n"
            f"Framework: {definition}\nCalculation: {calculation}\n"
            f"Unit: {unit}\n\nData:\n{data_table}\n\nGenerate now:"
        )

    @staticmethod
    def _format_data_table(data: List[Dict]) -> str:
        if not data:
            return "No data available"

        table = "| Facility | Period | Value | Unit |\n|----------|--------|-------|------|\n"
        for i, d in enumerate(data[:10], 1):
            table += (
                f"| {d.get('facility', 'N/A')} | {d.get('period', 'N/A')} "
                f"| {d.get('value', 'N/A')} | {d.get('unit', '')} | [Table {i}]\n"
            )

        if len(data) > 1 and all("value" in d for d in data):
            try:
                total = sum(float(d["value"]) for d in data)
                table += f"| **TOTAL** | All periods | **{total}** | {data[0].get('unit', '')} |\n"
            except (ValueError, TypeError):
                pass

        return table

    @staticmethod
    def _format_facilities(data: List[Dict]) -> str:
        facilities = sorted(set(d.get("facility", "Unknown") for d in data))
        return "\n".join(f"- {f}" for f in facilities) if facilities else "- Unknown"

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

        numbers_in_content = re.findall(r"[\d,]+\.?\d*", content)
        parsed_claims: List[float] = []
        for raw in numbers_in_content:
            try:
                parsed_claims.append(float(raw.replace(",", "")))
            except ValueError:
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
