"""Conversational RAG chat service scoped to user's uploaded ESG data."""
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

import redis
from groq import Groq

from src.generation.vector_store import VectorStore

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.6
MAX_HISTORY = 10
HISTORY_TTL = 86400  # 24 hours

FORBIDDEN_TOPICS = [
    "stock price", "investment advice", "legal advice",
    "medical", "political", "write code", "hack",
]

VALID_KEYWORDS = [
    "electricity", "emission", "water", "waste",
    "energy", "scope", "consumption", "production",
    "facility", "plant", "total", "average", "compare",
    "fuel", "gas", "carbon", "ghg", "renewable",
    "intensity", "reduction", "recycle", "discharge",
]


class ChatService:
    """Upload-scoped conversational RAG — answers only from the user's data."""

    def __init__(
        self,
        vector_store: VectorStore,
        groq_api_key: str,
        model: str = "llama-3.1-70b-versatile",
        redis_url: str = "redis://localhost:6379/0",
    ):
        self.vector_store = vector_store
        self.groq = Groq(api_key=groq_api_key)
        self.model = model

        try:
            self.redis = redis.from_url(redis_url, decode_responses=True)
            self.redis.ping()
        except Exception:
            logger.warning("Redis unavailable — chat history will not persist")
            self.redis = None

    @staticmethod
    def _validate_question(question: str) -> bool:
        """Reject off-topic or forbidden questions."""
        q_lower = question.lower()
        for topic in FORBIDDEN_TOPICS:
            if topic in q_lower:
                return False
        return any(kw in q_lower for kw in VALID_KEYWORDS)

    def chat(
        self,
        upload_id: UUID,
        question: str,
        session_id: str,
    ) -> Dict:
        if not self._validate_question(question):
            return {
                "answer": (
                    "I can only answer questions about your ESG data metrics "
                    "(electricity, emissions, water, waste, etc.). "
                    "Please ask about your facility's environmental performance."
                ),
                "sources": [],
                "confidence": 0.0,
            }

        history = self._get_history(session_id)

        search_results = self.vector_store.search_validated_data(
            query=question, upload_id=upload_id, top_k=5
        )

        if not search_results or search_results[0]["similarity"] < SIMILARITY_THRESHOLD:
            answer = (
                "I don't have information about this in your uploaded data. "
                "Please ask about metrics like electricity, emissions, water, "
                "or waste from your facility reports."
            )
            self._save_to_history(session_id, question, answer)
            return {"answer": answer, "sources": [], "confidence": 0.0}

        prompt = self._build_chat_prompt(question, search_results, history)

        try:
            completion = self.groq.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=500,
            )
            answer = completion.choices[0].message.content
        except Exception as exc:
            logger.error(f"Groq chat error: {exc}")
            answer = "Sorry, I encountered an error generating a response. Please try again."

        sources = [
            {
                "indicator": r["indicator"],
                "value": r["value"],
                "unit": r["unit"],
                "period": r["period"],
                "facility": r["facility"],
                "similarity": round(r["similarity"], 2),
            }
            for r in search_results[:3]
        ]

        self._save_to_history(session_id, question, answer)

        return {
            "answer": answer,
            "sources": sources,
            "confidence": round(search_results[0]["similarity"], 4),
        }

    # ------------------------------------------------------------------
    # Prompts
    # ------------------------------------------------------------------

    @staticmethod
    def _system_prompt() -> str:
        return (
            "You are an ESG data assistant. Answer questions using ONLY the "
            "provided data context.\n\n"
            "STRICT RULES:\n"
            "1. Use ONLY facts from the data provided below.\n"
            "2. If information is not in data, say: "
            '"This information is not available in the uploaded data."\n'
            '3. Cite sources: "According to the data, [fact] '
            '[Source: facility/period]."\n'
            "4. Be concise (2-3 sentences max).\n"
            "5. Never use external knowledge or general ESG information.\n"
            "6. For comparisons, only compare data that exists in the upload.\n\n"
            "FORMAT:\n"
            "- Answer the question directly.\n"
            "- Reference specific values with units.\n"
            "- Mention facility and time period.\n"
            "- Keep it factual and brief."
        )

    @staticmethod
    def _build_chat_prompt(
        question: str,
        data: List[Dict],
        history: List[Dict],
    ) -> str:
        data_context = "\n".join(
            f"- {d['facility']} in {d['period']}: "
            f"{d['indicator']} = {d['value']} {d['unit']}"
            for d in data[:5]
        )

        history_text = ""
        if history:
            recent = history[-4:]
            history_text = (
                "Previous conversation:\n"
                + "\n".join(
                    f"Q: {h['question']}\nA: {h['answer']}" for h in recent
                )
                + "\n\n"
            )

        return (
            f"{history_text}"
            f"Current question: {question}\n\n"
            f"Available data from upload:\n{data_context}\n\n"
            f"Answer based ONLY on the data above. "
            f"If the question cannot be answered with this data, say so."
        )

    # ------------------------------------------------------------------
    # History (Redis-backed)
    # ------------------------------------------------------------------

    def _get_history(self, session_id: str) -> List[Dict]:
        if self.redis is None:
            return []
        try:
            raw = self.redis.get(f"chat_history:{session_id}")
            return json.loads(raw) if raw else []
        except Exception:
            return []

    def _save_to_history(
        self, session_id: str, question: str, answer: str
    ) -> None:
        if self.redis is None:
            return
        try:
            history = self._get_history(session_id)
            history.append({
                "question": question,
                "answer": answer,
                "timestamp": datetime.now().isoformat(),
            })
            if len(history) > MAX_HISTORY:
                history = history[-MAX_HISTORY:]
            self.redis.setex(
                f"chat_history:{session_id}", HISTORY_TTL, json.dumps(history)
            )
        except Exception as exc:
            logger.warning(f"Failed to save chat history: {exc}")

    def clear_history(self, session_id: str) -> None:
        if self.redis is None:
            return
        try:
            self.redis.delete(f"chat_history:{session_id}")
        except Exception:
            pass
