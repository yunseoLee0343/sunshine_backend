"""Chat Intent API — TICKET-013.

POST /chat/intent
"""

from __future__ import annotations

from fastapi import APIRouter

from app.db.session import AsyncSessionLocal
from app.repositories.chat_intent_repository import ChatIntentRepository
from app.schemas.chat_intent import ChatIntentRequest, ChatIntentResponse
from app.services.chat_intent_classifier import ChatIntentClassifier

router = APIRouter(prefix="/chat", tags=["chat"])

_CLASSIFIER = ChatIntentClassifier()


@router.post("/intent", response_model=ChatIntentResponse, status_code=201)
async def classify_intent(req: ChatIntentRequest) -> ChatIntentResponse:
    """Classify the question intent and persist the result.

    Idempotent: re-submitting the same request_id returns the cached result
    without re-classifying. No answer is generated; only routing metadata
    is returned.
    """
    async with AsyncSessionLocal() as session:
        repo = ChatIntentRepository(session)

        cached = await repo.find_by_request_id(req.request_id)
        if cached is not None:
            return cached

        intent, confidence, stage = _CLASSIFIER.classify(req.question)

        result = await repo.save(
            request_id=req.request_id,
            user_id=req.user_id,
            plant_id=req.plant_id,
            question=req.question,
            intent=intent,
            confidence=confidence,
            stage=stage,
        )
        await session.commit()

    return result
