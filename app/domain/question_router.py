"""Question router domain — TICKET-062.

Pure value objects. No DB, no LLM, no I/O.
"""

from typing import Literal

from pydantic import BaseModel

Route = Literal[
    "rule_only",
    "sql_sensor",
    "sql_care_log",
    "rag_lookup",
    "llm_required",
    "companion",
    "pest_reference",
    "unknown",
]

# Routes that require a second LLM call to synthesize an answer.
_LLM_REQUIRED_ROUTES: frozenset[str] = frozenset(["llm_required", "unknown"])

# Sources that each route draws from at answer time.
ROUTE_SOURCES: dict[str, list[str]] = {
    "rule_only": [],
    "sql_sensor": ["sensor_snapshot"],
    "sql_care_log": ["care_log"],
    "rag_lookup": ["rag_care_knowledge"],
    "pest_reference": ["rag_pest_reference"],
    "companion": ["companion_table"],
    "llm_required": [],
    "unknown": [],
}


class QuestionRouteDecision(BaseModel):
    """Result of routing a user question to a fast-path or LLM handler."""

    route: Route
    confidence: float
    reason_codes: list[str]
    required_sources: list[str]
    second_llm_required: bool

    @classmethod
    def make(
        cls,
        route: Route,
        confidence: float,
        reason_codes: list[str],
    ) -> "QuestionRouteDecision":
        return cls(
            route=route,
            confidence=confidence,
            reason_codes=reason_codes,
            required_sources=ROUTE_SOURCES.get(route, []),
            second_llm_required=route in _LLM_REQUIRED_ROUTES,
        )
