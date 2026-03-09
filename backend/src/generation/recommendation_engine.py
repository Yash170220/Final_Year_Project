"""AI-powered recommendation engine comparing facility data against industry benchmarks."""
import logging
from typing import Dict, List, Optional

from groq import Groq

logger = logging.getLogger(__name__)

BENCHMARKS: Dict[str, Dict[str, Dict]] = {
    "cement": {
        "Scope 1 Emissions Intensity": {
            "avg": 950, "best": 800, "unit": "kg CO2/tonne clinker",
        },
        "Energy Intensity": {
            "avg": 3.5, "best": 2.9, "unit": "GJ/tonne clinker",
        },
        "Total Electricity Consumption": {
            "avg": 90, "best": 75, "unit": "kWh/tonne cement",
        },
        "Water Consumption": {
            "avg": 0.6, "best": 0.4, "unit": "m3/tonne cement",
        },
    },
    "steel": {
        "Scope 1 Emissions Intensity (BF-BOF)": {
            "avg": 2100, "best": 1800, "unit": "kg CO2/tonne steel",
        },
        "Scope 1 Emissions Intensity (EAF)": {
            "avg": 500, "best": 400, "unit": "kg CO2/tonne steel",
        },
        "Energy Intensity": {
            "avg": 20, "best": 16, "unit": "GJ/tonne steel",
        },
        "Water Consumption": {
            "avg": 4.0, "best": 2.5, "unit": "m3/tonne steel",
        },
    },
}

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


class RecommendationEngine:
    """Generates actionable recommendations by comparing performance to benchmarks."""

    def __init__(self, groq_api_key: str, model: str = "llama-3.1-70b-versatile"):
        self.groq = Groq(api_key=groq_api_key)
        self.model = model
        self.benchmarks = BENCHMARKS

    def generate_recommendations(
        self,
        upload_id: str,
        validated_data: List[Dict],
        industry: str,
    ) -> List[Dict]:
        by_indicator: Dict[str, List[Dict]] = {}
        for record in validated_data:
            by_indicator.setdefault(record["indicator"], []).append(record)

        recommendations: List[Dict] = []

        for indicator, records in by_indicator.items():
            if not records:
                continue

            values = [r["value"] for r in records if r.get("value") is not None]
            if not values:
                continue

            avg_value = sum(values) / len(values)
            benchmark = self._get_benchmark(indicator, industry)
            if not benchmark:
                continue

            gap_pct = ((avg_value - benchmark["avg"]) / benchmark["avg"]) * 100

            if abs(gap_pct) < 5:
                priority = "low"
                status = "On par with industry average"
            elif gap_pct > 5:
                priority = "high" if gap_pct > 20 else "medium"
                status = f"{abs(gap_pct):.0f}% above industry average"
            else:
                priority = "low"
                status = f"{abs(gap_pct):.0f}% below industry average (good performance)"

            suggestions: List[str] = []
            if gap_pct > 5:
                suggestions = self._generate_ai_suggestions(
                    indicator=indicator,
                    current=avg_value,
                    benchmark=benchmark,
                    industry=industry,
                    gap_pct=gap_pct,
                )

            recommendations.append({
                "indicator": indicator,
                "current_value": round(avg_value, 2),
                "unit": records[0].get("unit", ""),
                "industry_average": benchmark["avg"],
                "best_in_class": benchmark["best"],
                "gap_percentage": round(gap_pct, 1),
                "status": status,
                "priority": priority,
                "suggestions": suggestions,
            })

        recommendations.sort(key=lambda x: PRIORITY_ORDER.get(x["priority"], 2))
        return recommendations

    # ------------------------------------------------------------------

    def _get_benchmark(self, indicator: str, industry: str) -> Optional[Dict]:
        industry_benchmarks = self.benchmarks.get(industry)
        if not industry_benchmarks:
            return None
        ind_lower = indicator.lower()
        for bench_name, bench_data in industry_benchmarks.items():
            if bench_name.lower() in ind_lower or ind_lower in bench_name.lower():
                return bench_data
        return None

    def _generate_ai_suggestions(
        self,
        indicator: str,
        current: float,
        benchmark: Dict,
        industry: str,
        gap_pct: float,
    ) -> List[str]:
        prompt = (
            f"You are an ESG improvement consultant for {industry} manufacturing.\n\n"
            f"CURRENT SITUATION:\n"
            f"- Metric: {indicator}\n"
            f"- Current performance: {current:.2f} {benchmark['unit']}\n"
            f"- Industry average: {benchmark['avg']} {benchmark['unit']}\n"
            f"- Best-in-class: {benchmark['best']} {benchmark['unit']}\n"
            f"- Performance gap: {gap_pct:.0f}% above average (needs improvement)\n\n"
            f"Generate 3-4 SPECIFIC, ACTIONABLE recommendations to close this gap.\n\n"
            f"Each recommendation should include:\n"
            f"1. Technology/practice name\n"
            f"2. Estimated impact (% reduction)\n"
            f"3. Typical investment range\n"
            f"4. Payback period (years)\n"
            f"5. Implementation complexity (Low/Medium/High)\n\n"
            f"Be specific to {industry} industry. Focus on proven technologies. "
            f"Prioritize by ROI (best ROI first). Keep each to 2-3 lines.\n\n"
            f"Generate 3-4 recommendations now (numbered list):"
        )

        try:
            response = self.groq.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=600,
            )
            text = response.choices[0].message.content

            suggestions = [
                line.strip()
                for line in text.split("\n")
                if line.strip()
                and any(line.strip().startswith(f"{i}.") for i in range(1, 10))
            ]
            suggestions = [
                s.split(". ", 1)[1] if ". " in s else s for s in suggestions
            ]
            return suggestions[:4]

        except Exception as exc:
            logger.error(f"AI suggestion generation failed: {exc}")
            return [f"Error generating suggestions: {exc}"]
