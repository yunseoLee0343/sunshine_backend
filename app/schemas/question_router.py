"""Question router API schemas — TICKET-062."""

from pydantic import BaseModel

from app.domain.question_router import QuestionRouteDecision  # re-exported


class QuestionRouteRequest(BaseModel):
    """Request schema for future /router/classify endpoint."""

    question: str
    locale: str = "ko-KR"


__all__ = ["QuestionRouteRequest", "QuestionRouteDecision"]
