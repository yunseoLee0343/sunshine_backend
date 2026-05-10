"""ChatOrchestrator — TICKET-018 + TICKET-019.

Full 7-step pipeline:
  1. Intent classification (ChatIntentClassifier)
  2. Retrieval — try/except, optional; skipped when rag_layers is empty
  3. Evidence building (EvidenceBuilderService → ForwardContext)
  4. Prompt building (PromptBuilder)
  5. LLM completion (MockLLMClient)
  6. Response parsing ([결론][근거][행동][주의])
  6b. Pest guardrail (TICKET-019) — applied when intent == pest_reference_question
  7. Persist ChatRequest + LlmRun

Idempotent: a duplicate request_id returns the cached LlmRun result.
No network calls at import time.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.retrieval import RagLayer
from app.llm.mock_client import MockLLMClient
from app.models.chat_request import ChatRequest
from app.models.llm_run import LlmRun
from app.models.plant import Plant
from app.schemas.chat_answer import ChatAnswerRequest, ChatAnswerResponse, ParsedAnswer
from app.schemas.evidence_bundle import EvidenceBuildRequest
from app.schemas.retrieval import RetrievalRequest
from app.services.chat_intent_classifier import ChatIntentClassifier
from app.services.evidence_builder import EvidenceBuilderService, PlantNotFoundError
from app.services.llm_port import LLMRequest
from app.services.pest_reference_guardrail import PestReferenceGuardrail
from app.services.prompt_builder import PromptBuilder
from app.services.response_parser import parse_answer
from app.services.retrieval_service import RetrievalService

_CLASSIFIER = ChatIntentClassifier()
_PROMPT_BUILDER = PromptBuilder()
_LLM_CLIENT = MockLLMClient()
_PEST_GUARDRAIL = PestReferenceGuardrail()

_PEST_INTENT = "pest_reference_question"

_INTENT_TO_RAG_LAYERS: dict[str, list[RagLayer]] = {
    "watering_question":      ["care_knowledge", "species_profile"],
    "light_question":         ["care_knowledge", "species_profile"],
    "humidity_question":      ["care_knowledge", "species_profile"],
    "temperature_question":   ["care_knowledge", "species_profile"],
    "species_care_question":  ["species_profile", "care_knowledge"],
    "pest_reference_question":["pest_disease_reference", "species_profile"],
    "companion_plant_question": [],
    "unknown_question":       ["species_profile", "care_knowledge"],
}

_FALLBACK_RAG_LAYERS: list[RagLayer] = ["species_profile", "care_knowledge"]


class ChatOrchestrator:
    """Stateless orchestrator. Instantiate once and reuse freely."""

    async def run(
        self,
        session: AsyncSession,
        *,
        plant_id: uuid.UUID,
        user_id: uuid.UUID,
        question: str,
        request_id: uuid.UUID,
    ) -> ChatAnswerResponse:
        now = datetime.now(UTC)

        # ---- idempotency check ---------------------------------------------
        existing = await session.get(ChatRequest, request_id)
        if existing is not None:
            return await self._load_cached(session, existing)

        # ---- 1. intent classification --------------------------------------
        intent, _confidence, _stage = _CLASSIFIER.classify(question)

        # ---- 2. retrieval (optional) ---------------------------------------
        rag_layers: list[RagLayer] = _INTENT_TO_RAG_LAYERS.get(
            intent, _FALLBACK_RAG_LAYERS
        )
        retrieval_run_id: uuid.UUID | None = None
        if rag_layers:
            plant = await session.get(Plant, plant_id)
            species_profile_id = (
                plant.species_profile_id if plant is not None else None
            )
            try:
                retrieval_req = RetrievalRequest(
                    request_id=uuid.uuid4(),
                    user_id=user_id,
                    question=question,
                    species_profile_id=species_profile_id,
                    rag_layers=rag_layers,
                    top_k=5,
                )
                retrieval_svc = RetrievalService(session)
                retrieval_result = await retrieval_svc.query(retrieval_req)
                retrieval_run_id = retrieval_result.request_id
            except Exception:
                pass

        # ---- 3. evidence building ------------------------------------------
        evidence_req = EvidenceBuildRequest(
            plant_id=plant_id,
            user_id=user_id,
            question=question,
            intent=intent,  # type: ignore[arg-type]
            rag_layers=rag_layers,
            retrieval_run_id=retrieval_run_id,
        )
        evidence_svc = EvidenceBuilderService(session)
        ctx, from_cache = await evidence_svc.build(evidence_req)

        # ---- 4. prompt building --------------------------------------------
        prompt_result = _PROMPT_BUILDER.build(ctx)

        # ---- 5. LLM completion ---------------------------------------------
        llm_req = LLMRequest(
            request_id=request_id,
            system_prompt=prompt_result.system_prompt,
            user_turn=prompt_result.user_turn,
            prompt_hash=prompt_result.prompt_hash,
        )
        llm_resp = await _LLM_CLIENT.complete(llm_req)

        # ---- 6. response parsing -------------------------------------------
        parsed = parse_answer(llm_resp.content)

        # ---- 6b. pest reference guardrail (TICKET-019) ---------------------
        is_reference_only = False
        diagnosis_allowed = True
        if intent == _PEST_INTENT:
            gr = _PEST_GUARDRAIL.apply(parsed)
            parsed = gr.answer
            is_reference_only = gr.is_reference_only
            diagnosis_allowed = gr.diagnosis_allowed

        # ---- 7. persist ----------------------------------------------------
        chat_row = ChatRequest(
            id=request_id,
            user_id=user_id,
            plant_id=plant_id,
            question=question,
            status=intent,
            created_at=now,
        )
        session.add(chat_row)
        await session.flush()

        llm_run = LlmRun(
            id=uuid.uuid4(),
            request_id=request_id,
            profile="chat_orchestrator",
            model_name=llm_resp.model_metadata.model_name,
            prompt_hash=llm_resp.prompt_hash,
            prompt_text=prompt_result.system_prompt,
            response_text=llm_resp.content,
            tokens_in=llm_resp.input_tokens,
            tokens_out=llm_resp.output_tokens,
            latency_ms=0,
            created_at=now,
        )
        session.add(llm_run)
        await session.flush()

        return ChatAnswerResponse(
            request_id=request_id,
            plant_id=plant_id,
            intent=intent,
            answer=parsed,
            guardrails_applied=list(prompt_result.guardrails_applied),
            prompt_hash=llm_resp.prompt_hash,
            model_name=llm_resp.model_metadata.model_name,
            input_tokens=llm_resp.input_tokens,
            output_tokens=llm_resp.output_tokens,
            from_cache=from_cache,
            is_reference_only=is_reference_only,
            diagnosis_allowed=diagnosis_allowed,
            created_at=now,
        )

    async def _load_cached(
        self, session: AsyncSession, chat_row: ChatRequest
    ) -> ChatAnswerResponse:
        result = await session.execute(
            select(LlmRun)
            .where(
                LlmRun.request_id == chat_row.id,
                LlmRun.profile == "chat_orchestrator",
            )
            .limit(1)
        )
        llm_run = result.scalar_one_or_none()

        is_pest = chat_row.status == _PEST_INTENT
        is_reference_only = is_pest
        diagnosis_allowed = not is_pest

        if llm_run is None:
            return ChatAnswerResponse(
                request_id=chat_row.id,
                plant_id=chat_row.plant_id or uuid.uuid4(),
                intent=chat_row.status,
                answer=ParsedAnswer(결론="", 근거="", 행동="", 주의=""),
                guardrails_applied=[],
                prompt_hash="",
                model_name="",
                input_tokens=0,
                output_tokens=0,
                from_cache=True,
                is_reference_only=is_reference_only,
                diagnosis_allowed=diagnosis_allowed,
                created_at=chat_row.created_at,
            )

        parsed = parse_answer(llm_run.response_text or "")
        return ChatAnswerResponse(
            request_id=chat_row.id,
            plant_id=chat_row.plant_id or uuid.uuid4(),
            intent=chat_row.status,
            answer=parsed,
            guardrails_applied=[],
            prompt_hash=llm_run.prompt_hash or "",
            model_name=llm_run.model_name or "",
            input_tokens=llm_run.tokens_in or 0,
            output_tokens=llm_run.tokens_out or 0,
            from_cache=True,
            is_reference_only=is_reference_only,
            diagnosis_allowed=diagnosis_allowed,
            created_at=chat_row.created_at,
        )
