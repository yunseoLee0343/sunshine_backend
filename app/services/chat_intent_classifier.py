"""Hybrid Chat Intent Classifier — TICKET-013.

Stage 1: LightweightIntentClassifier (regex, confidence=0.95)
Stage 2: MockIntentClassifier (deterministic fallback, confidence≤0.70)

No external API calls. No DB access. Pure classification logic.
"""

from __future__ import annotations

from app.llm.intent_classifier_mock import MockIntentClassifier
from app.schemas.chat_intent import ClassifierStage, Intent
from app.services.lightweight_intent_classifier import LightweightIntentClassifier

_STAGE1 = LightweightIntentClassifier()
_STAGE2 = MockIntentClassifier()


class ChatIntentClassifier:
    """Orchestrates the two-stage hybrid classification pipeline."""

    def classify(self, question: str) -> tuple[Intent, float, ClassifierStage]:
        """Return (intent, confidence, stage).

        Tries Stage 1 first; falls back to Stage 2 if Stage 1 returns None.
        """
        result = _STAGE1.classify(question)
        if result is not None:
            intent, confidence = result
            return intent, confidence, "rule"

        intent, confidence = _STAGE2.classify(question)
        return intent, confidence, "llm"
