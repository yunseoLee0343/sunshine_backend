"""Mock LLM intent classifier (Stage 2) — TICKET-013.

Deterministic fallback for questions the regex classifier couldn't handle.
Uses broader secondary keyword matching. Always returns a result — never
raises, never calls any external API, never accesses the DB.

Returns confidence=0.70 for a secondary keyword match, or 0.50 for
the "unknown_question" fallback.
"""

from __future__ import annotations

import re

from app.schemas.chat_intent import Intent

# Broader, fuzzier patterns than Stage 1 — catch partial or compound phrasing.
_SECONDARY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("watering_question",    re.compile(r"물|water|촉촉|젖|건조|마름|흙", re.I)),
    ("light_question",       re.compile(r"빛|light|어두|밝|창가|창문|해", re.I)),
    ("humidity_question",    re.compile(r"습|humid|건조|분무|안개|공기", re.I)),
    ("temperature_question", re.compile(r"온|도|temp|차가|뜨거|춥|덥|따뜻", re.I)),
    ("pest_reference_question",   re.compile(r"벌레|충|병|썩|해|rot|pest|bug|spot|점|반점", re.I)),
    ("companion_plant_question",  re.compile(r"같이|함께|궁합|companion|함께|mix|어울", re.I)),
    ("species_care_question",     re.compile(r"키우|기르|관리|방법|care|grow|재배", re.I)),
]

_CONFIDENCE_LLM_MATCH    = 0.70
_CONFIDENCE_LLM_FALLBACK = 0.50


class MockIntentClassifier:
    """Deterministic Stage 2 mock; simulates an LLM without any API call."""

    def classify(self, question: str) -> tuple[Intent, float]:
        for intent, pat in _SECONDARY_PATTERNS:
            if pat.search(question):
                return intent, _CONFIDENCE_LLM_MATCH  # type: ignore[return-value]
        return "unknown_question", _CONFIDENCE_LLM_FALLBACK
