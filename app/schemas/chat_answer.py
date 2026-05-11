"""Chat Care Answer schemas — TICKET-018 + TICKET-019 + TICKET-031."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.audio_port import AudioMetadata


class ChatAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: uuid.UUID
    user_id: uuid.UUID
    question: str | None = Field(default=None, min_length=1, max_length=2000)
    image_uri: str | None = None
    audio_uri: str | None = None

    @model_validator(mode="after")
    def _require_question_or_audio(self) -> "ChatAnswerRequest":
        if not self.question and not self.audio_uri:
            raise ValueError("question or audio_uri is required")
        return self


class ParsedAnswer(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "결론": "물 부족 상태입니다.",
                "근거": "토양 수분이 30% 미만으로 낮게 측정되었습니다.",
                "행동": "지금 바로 물을 충분히 주세요.",
                "주의": "화분 받침에 물이 고이지 않도록 주의하세요.",
            }
        }
    )

    결론: str
    근거: str
    행동: str
    주의: str


class ChatAnswerResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "request_id": "d4e5f6a7-b8c9-0123-defa-234567890123",
                "plant_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "intent": "watering_question",
                "answer": {
                    "결론": "물 부족 상태입니다.",
                    "근거": "토양 수분이 낮습니다.",
                    "행동": "물을 주세요.",
                    "주의": "과습 주의",
                },
                "guardrails_applied": [],
                "prompt_hash": "abc123def456",
                "model_name": "claude-sonnet-4-6",
                "input_tokens": 1200,
                "output_tokens": 350,
                "from_cache": False,
                "created_at": "2026-05-11T12:00:00Z",
                "is_reference_only": False,
                "diagnosis_allowed": True,
            }
        }
    )

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
    # Safety metadata — TICKET-019
    is_reference_only: bool = False  # True for pest_reference_question
    diagnosis_allowed: bool = True  # False for pest_reference_question
    # Audio response — TICKET-031 (None when no audio_uri was supplied)
    audio_response: AudioMetadata | None = None
