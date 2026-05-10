"""Chat Care Answer schemas — TICKET-018."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChatAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: uuid.UUID
    user_id: uuid.UUID
    question: str = Field(..., min_length=1, max_length=2000)


class ParsedAnswer(BaseModel):
    결론: str
    근거: str
    행동: str
    주의: str


class ChatAnswerResponse(BaseModel):
    request_id: uuid.UUID
    plant_id: uuid.UUID
    intent: str
    answer: ParsedAnswer
    guardrails_applied: list[str]
    prompt_hash: str
    model_name: str
    input_tokens: int
    output_tokens: int
    from_cache: bool
    created_at: datetime
