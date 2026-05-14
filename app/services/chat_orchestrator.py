"""ChatOrchestrator — TICKET-018 + TICKET-019 + TICKET-021 + TICKET-032.

Full pipeline (standard intents):
  0.5 STT: audio_uri → transcript (TICKET-031)
  1.  Intent classification (ChatIntentClassifier)
  1.5 Vision analysis: image_uri → visual_facts (TICKET-030)
  2.  Retrieval — try/except, optional; skipped when rag_layers is empty
  3.  Evidence building (EvidenceBuilderService → ForwardContext)
  4.  Prompt building (PromptBuilder)
  5+6 LLM completion + self-healing validation (SelfHealingOrchestrator, TICKET-032)
  6b. Pest guardrail (TICKET-019) — applied when intent == pest_reference_question
  6c. TTS: answer → audio_response (TICKET-031)
  7.  Persist ChatRequest + LlmRun + LlmSelfHealingLog rows

Companion branch (companion_plant_question — TICKET-021):
  Calls CompanionRecommendationService, formats result as 4-section answer,
  persists with profile="companion_orchestrator"; skips steps 2-6b.

Idempotent: a duplicate request_id returns the cached LlmRun result.
No network calls at import time.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.retrieval import RagLayer
from app.llm.client_factory import get_llm_client
from app.llm.mock_audio_client import MockAudioClient
from app.llm.mock_vision_client import MockVisionClient
from app.models.chat_request import ChatRequest
from app.models.llm_run import LlmRun
from app.models.llm_self_healing_log import LlmSelfHealingLog
from app.models.plant import Plant
from app.schemas.chat_answer import ChatAnswerResponse, ParsedAnswer
from app.schemas.evidence_bundle import EvidenceBuildRequest
from app.schemas.retrieval import RetrievalRequest
from app.services.audio_port import AudioMetadata
from app.services.chat_evaluation_service import ChatEvaluationService
from app.services.chat_intent_classifier import ChatIntentClassifier
from app.services.companion_recommendation_service import (
    CompanionRecommendationService,
    PlantOwnershipError,
    companion_prompt_hash,
    format_companion_answer,
)
from app.services.evidence_builder import EvidenceBuilderService, PlantNotFoundError
from app.services.llm_port import LLMRequest
from app.services.pest_reference_guardrail import PestReferenceGuardrail
from app.services.prompt_builder import PromptBuilder
from app.services.response_parser import parse_answer
from app.services.retrieval_service import RetrievalService
from app.services.self_healing_orchestrator import SelfHealingOrchestrator

_CLASSIFIER = ChatIntentClassifier()
_PROMPT_BUILDER = PromptBuilder()
_LLM_CLIENT = get_llm_client()
_PEST_GUARDRAIL = PestReferenceGuardrail()
_VISION_CLIENT = MockVisionClient()
_AUDIO_CLIENT = MockAudioClient()
_HEALER = SelfHealingOrchestrator()

_PEST_INTENT = "pest_reference_question"
_COMPANION_INTENT = "companion_plant_question"
_COMPANION_MODEL = "companion-filter-v1"

_INTENT_TO_RAG_LAYERS: dict[str, list[RagLayer]] = {
    "watering_question": ["care_knowledge", "species_profile"],
    "light_question": ["care_knowledge", "species_profile"],
    "humidity_question": ["care_knowledge", "species_profile"],
    "temperature_question": ["care_knowledge", "species_profile"],
    "species_care_question": ["species_profile", "care_knowledge"],
    "pest_reference_question": ["pest_disease_reference", "species_profile"],
    "companion_plant_question": [],
    "unknown_question": ["species_profile", "care_knowledge"],
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
        question: str | None,
        request_id: uuid.UUID,
        image_uri: str | None = None,
        audio_uri: str | None = None,
    ) -> ChatAnswerResponse:
        now = datetime.now(UTC)

        # ---- idempotency check ---------------------------------------------
        existing = await session.get(ChatRequest, request_id)
        if existing is not None:
            return await self._load_cached(session, existing)

        # ---- 0.5. STT: audio → transcript — TICKET-031 --------------------
        if audio_uri:
            stt_result = await _AUDIO_CLIENT.stt(audio_uri)
            effective_question = stt_result.transcript
        elif question:
            effective_question = question
        else:
            raise ValueError("question or audio_uri is required")

        # ---- 1. intent classification --------------------------------------
        intent, _confidence, _stage = _CLASSIFIER.classify(effective_question)

        # ---- 1.5. vision analysis (optional) — TICKET-030 -----------------
        visual_facts: list[str] = []
        if image_uri:
            vision_result = await _VISION_CLIENT.analyze(image_uri)
            visual_facts = list(vision_result.visual_symptoms)
            if vision_result.suggests_pest and intent == "unknown_question":
                intent = _PEST_INTENT

        # ---- companion branch (TICKET-021) --------------------------------
        if intent == _COMPANION_INTENT:
            return await self._run_companion(
                session,
                plant_id=plant_id,
                user_id=user_id,
                question=effective_question,
                request_id=request_id,
                now=now,
            )

        # ---- 2. retrieval (optional) ---------------------------------------
        rag_layers: list[RagLayer] = _INTENT_TO_RAG_LAYERS.get(intent, _FALLBACK_RAG_LAYERS)
        retrieval_run_id: uuid.UUID | None = None
        if rag_layers:
            plant = await session.get(Plant, plant_id)
            species_profile_id = plant.species_profile_id if plant is not None else None
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
            question=effective_question,
            intent=intent,  # type: ignore[arg-type]
            rag_layers=rag_layers,
            retrieval_run_id=retrieval_run_id,
            visual_facts=visual_facts,
        )
        evidence_svc = EvidenceBuilderService(session)
        ctx, from_cache = await evidence_svc.build(evidence_req)

        # ---- 4. prompt building --------------------------------------------
        prompt_result = _PROMPT_BUILDER.build(ctx)

        # ---- 5+6. LLM completion + self-healing validation — TICKET-032 ---
        llm_req = LLMRequest(
            request_id=request_id,
            system_prompt=prompt_result.system_prompt,
            user_turn=prompt_result.user_turn,
            prompt_hash=prompt_result.prompt_hash,
        )
        healing_result = await _HEALER.run_with_healing(
            llm_client=_LLM_CLIENT,
            llm_request=llm_req,
            ctx=ctx,
        )
        llm_resp = healing_result.final_llm_response
        parsed = healing_result.parsed_answer

        # ---- 6b. pest reference guardrail (TICKET-019) ---------------------
        is_reference_only = False
        diagnosis_allowed = True
        if intent == _PEST_INTENT:
            gr = _PEST_GUARDRAIL.apply(parsed)
            parsed = gr.answer
            is_reference_only = gr.is_reference_only
            diagnosis_allowed = gr.diagnosis_allowed

        # ---- 6c. TTS: answer → audio — TICKET-031 -------------------------
        audio_response: AudioMetadata | None = None
        audio_uri_out: str | None = None
        audio_duration: float | None = None
        if audio_uri:
            tts_text = f"{parsed.결론} {parsed.근거} {parsed.행동}"
            tts_result = await _AUDIO_CLIENT.tts(tts_text)
            audio_response = tts_result
            audio_uri_out = tts_result.audio_uri
            audio_duration = tts_result.duration_seconds

        # ---- 7. persist ----------------------------------------------------
        chat_row = ChatRequest(
            id=request_id,
            user_id=user_id,
            plant_id=plant_id,
            question=effective_question,
            status=intent,
            audio_uri_in=audio_uri,
            audio_uri_out=audio_uri_out,
            audio_duration_seconds=audio_duration,
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

        for attempt in healing_result.attempts:
            healing_log = LlmSelfHealingLog(
                id=uuid.uuid4(),
                request_id=request_id,
                attempt_number=attempt.attempt_num,
                passed=attempt.validation_result.passed,
                failed_checks=list(attempt.validation_result.failed_checks),
                validation_errors=list(attempt.validation_result.errors),
                correction_prompt_snippet=attempt.correction_prompt,
                response_snippet=attempt.response_text[:500],
                created_at=now,
            )
            session.add(healing_log)
        await session.flush()

        # ---- 8. evaluation (TICKET-034, best-effort) ----------------------
        try:
            eval_svc = ChatEvaluationService(session)
            await eval_svc.evaluate_and_save(
                request_id=request_id,
                question=effective_question,
                answer=parsed,
                ctx=ctx,
                intent=intent,
            )
        except Exception:
            pass

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
            audio_response=audio_response,
            created_at=now,
        )

    async def _run_companion(
        self,
        session: AsyncSession,
        *,
        plant_id: uuid.UUID,
        user_id: uuid.UUID,
        question: str,
        request_id: uuid.UUID,
        now: datetime,
    ) -> ChatAnswerResponse:
        """Companion branch: filter-based answer, no LLM, no evidence pipeline."""
        rec_resp = None
        try:
            svc = CompanionRecommendationService(session)
            rec_resp = await svc.recommend(plant_id, user_id, top_k=5)
        except (PlantNotFoundError, PlantOwnershipError):
            pass

        parsed = format_companion_answer(rec_resp)
        ph = companion_prompt_hash(plant_id, question)
        content = f"[결론] {parsed.결론}\n\n[근거] {parsed.근거}\n\n[행동] {parsed.행동}\n\n[주의] {parsed.주의}"

        chat_row = ChatRequest(
            id=request_id,
            user_id=user_id,
            plant_id=plant_id,
            question=question,
            status=_COMPANION_INTENT,
            created_at=now,
        )
        session.add(chat_row)
        await session.flush()

        llm_run = LlmRun(
            id=uuid.uuid4(),
            request_id=request_id,
            profile="companion_orchestrator",
            model_name=_COMPANION_MODEL,
            prompt_hash=ph,
            prompt_text=question,
            response_text=content,
            tokens_in=0,
            tokens_out=len(content) // 4,
            latency_ms=0,
            created_at=now,
        )
        session.add(llm_run)
        await session.flush()

        return ChatAnswerResponse(
            request_id=request_id,
            plant_id=plant_id,
            intent=_COMPANION_INTENT,
            answer=parsed,
            guardrails_applied=[],
            prompt_hash=ph,
            model_name=_COMPANION_MODEL,
            input_tokens=0,
            output_tokens=len(content) // 4,
            from_cache=False,
            created_at=now,
        )

    async def _load_cached(self, session: AsyncSession, chat_row: ChatRequest) -> ChatAnswerResponse:
        result = await session.execute(
            select(LlmRun)
            .where(
                LlmRun.request_id == chat_row.id,
                LlmRun.profile.in_(["chat_orchestrator", "companion_orchestrator"]),
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
