"""ChatIntentRepository — TICKET-013.

Persists ChatRequest (always) and LlmRun (only when stage=="llm").
Provides idempotent lookup by request_id so duplicate submissions
return the cached classification.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_request import ChatRequest
from app.models.llm_run import LlmRun
from app.schemas.chat_intent import (
    ROUTING_TABLE,
    ChatIntentResponse,
    ClassifierStage,
    Intent,
)


class ChatIntentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_request_id(self, request_id: uuid.UUID) -> ChatIntentResponse | None:
        """Return a previously stored classification, or None if not found."""
        row = await self.session.get(ChatRequest, request_id)
        if row is None:
            return None

        # Determine stage: LlmRun exists ↔ stage was "llm"
        llm_row = await self._find_llm_run(request_id)
        stage: ClassifierStage = "llm" if llm_row is not None else "rule"
        confidence = float(llm_row.tokens_in) / 100.0 if llm_row is not None and llm_row.tokens_in is not None else 0.95

        return self._build_response(row, stage, confidence)

    async def save(
        self,
        *,
        request_id: uuid.UUID,
        user_id: uuid.UUID,
        plant_id: uuid.UUID | None,
        question: str,
        intent: Intent,
        confidence: float,
        stage: ClassifierStage,
        now: datetime | None = None,
    ) -> ChatIntentResponse:
        ts = now or datetime.now(UTC)

        chat_row = ChatRequest(
            id=request_id,
            user_id=user_id,
            plant_id=plant_id,
            question=question,
            status=intent,
            created_at=ts,
        )
        self.session.add(chat_row)
        await self.session.flush()

        if stage == "llm":
            # Store confidence as integer hundredths in tokens_in (avoids schema change)
            llm_row = LlmRun(
                id=uuid.uuid4(),
                request_id=request_id,
                profile="intent_classifier_mock",
                model_name="mock-v1",
                tokens_in=round(confidence * 100),
                created_at=ts,
            )
            self.session.add(llm_row)
            await self.session.flush()

        return self._build_response(chat_row, stage, confidence)

    # ------------------------------------------------------------------

    async def _find_llm_run(self, request_id: uuid.UUID) -> LlmRun | None:
        result = await self.session.execute(select(LlmRun).where(LlmRun.request_id == request_id).limit(1))
        return result.scalar_one_or_none()

    @staticmethod
    def _build_response(
        row: ChatRequest,
        stage: ClassifierStage,
        confidence: float,
    ) -> ChatIntentResponse:
        intent: Intent = row.status  # type: ignore[assignment]
        routing = ROUTING_TABLE.get(intent, ROUTING_TABLE["unknown_question"])
        return ChatIntentResponse(
            request_id=row.id,
            intent=intent,
            confidence=confidence,
            stage=stage,
            selected_rule_modules=list(routing.selected_rule_modules),
            selected_rag_layers=list(routing.selected_rag_layers),
            requires_evidence=routing.requires_evidence,
            created_at=row.created_at,
        )
