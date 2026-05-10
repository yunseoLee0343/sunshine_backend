"""Chat Intent Classification schemas — TICKET-013."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

Intent = Literal[
    "watering_question",
    "light_question",
    "humidity_question",
    "temperature_question",
    "species_care_question",
    "pest_reference_question",
    "companion_plant_question",
    "unknown_question",
]

ClassifierStage = Literal["rule", "llm"]


# ---------------------------------------------------------------------------
# Routing metadata (deterministic per intent — no DB storage needed)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IntentRouting:
    selected_rule_modules: list[str]
    selected_rag_layers: list[str]
    requires_evidence: bool


ROUTING_TABLE: dict[str, IntentRouting] = {
    "watering_question": IntentRouting(
        selected_rule_modules=["watering"],
        selected_rag_layers=["species_care"],
        requires_evidence=True,
    ),
    "light_question": IntentRouting(
        selected_rule_modules=["light"],
        selected_rag_layers=["species_care"],
        requires_evidence=True,
    ),
    "humidity_question": IntentRouting(
        selected_rule_modules=["humidity"],
        selected_rag_layers=["species_care"],
        requires_evidence=True,
    ),
    "temperature_question": IntentRouting(
        selected_rule_modules=["temperature"],
        selected_rag_layers=["species_care"],
        requires_evidence=True,
    ),
    "species_care_question": IntentRouting(
        selected_rule_modules=[],
        selected_rag_layers=["species_care", "general"],
        requires_evidence=False,
    ),
    "pest_reference_question": IntentRouting(
        selected_rule_modules=[],
        selected_rag_layers=["pest", "species_care"],
        requires_evidence=False,
    ),
    "companion_plant_question": IntentRouting(
        selected_rule_modules=[],
        selected_rag_layers=["companion", "species_care"],
        requires_evidence=False,
    ),
    "unknown_question": IntentRouting(
        selected_rule_modules=[],
        selected_rag_layers=["general"],
        requires_evidence=False,
    ),
}


# ---------------------------------------------------------------------------
# Request / Response DTOs
# ---------------------------------------------------------------------------

class ChatIntentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: uuid.UUID               # caller-supplied; used for idempotency
    user_id: uuid.UUID
    plant_id: uuid.UUID | None = None
    question: str = Field(..., min_length=1, max_length=2000)

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question must not be blank")
        return v


class ChatIntentResponse(BaseModel):
    request_id: uuid.UUID
    intent: Intent
    confidence: float
    stage: ClassifierStage
    selected_rule_modules: list[str]
    selected_rag_layers: list[str]
    requires_evidence: bool
    created_at: datetime
