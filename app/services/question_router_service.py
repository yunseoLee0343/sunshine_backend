"""QuestionRouterService — TICKET-062.

Deterministic keyword-based question router. No LLM, no DB.
Routes Korean plant-care questions to the appropriate fast-path handler.

Priority order (first match wins):
  companion > pest_reference > sql_sensor > sql_care_log > rag_lookup > rule_only > llm_required
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.question_router import QuestionRouteDecision, Route


@dataclass(frozen=True)
class _Rule:
    route: Route
    keywords: tuple[str, ...]
    reason_code: str


# Rules are evaluated in declaration order; first match wins.
_RULES: tuple[_Rule, ...] = (
    # ── companion plants ──────────────────────────────────────────────────
    _Rule(
        "companion",
        ("함께 두", "같이 두", "어울리는 식물", "궁합", "컴패니언", "같이 키워"),
        "companion_keywords",
    ),
    # ── pest / disease reference ──────────────────────────────────────────
    _Rule(
        "pest_reference",
        ("병충해", "벌레", "해충", "곰팡이", "반점", "점이 생겼", "잎이 노랗", "잎이 누렇", "흰가루", "깍지벌레", "진딧물"),
        "pest_keywords",
    ),
    # ── live sensor reading ───────────────────────────────────────────────
    _Rule(
        "sql_sensor",
        (
            "현재 습도", "현재 온도", "현재 조도", "현재 토양",
            "지금 습도", "지금 온도", "지금 조도", "지금 토양",
            "최근 습도", "최근 온도", "최근 조도", "최근 토양수분",
            "실시간", "센서", "건조해", "건조한가",
        ),
        "sensor_keywords",
    ),
    # ── care-log history ─────────────────────────────────────────────────
    _Rule(
        "sql_care_log",
        (
            "물 준 기록", "물 준 날", "마지막 물", "언제 줬", "언제 물을",
            "관리 기록", "케어 기록", "돌본 기록", "최근에 물",
        ),
        "care_log_keywords",
    ),
    # ── RAG knowledge lookup ─────────────────────────────────────────────
    _Rule(
        "rag_lookup",
        (
            "키우는 법", "재배법", "관리법", "키우는 방법", "관리 방법",
            "어떻게 키워", "어떻게 관리", "어디 두면", "배치",
            "햇빛", "일조", "물주기 주기", "얼마나 자주", "며칠마다",
            "계절", "봄", "여름", "가을", "겨울", "환경",
            "심는 법", "분갈이", "흙", "토양 종류",
        ),
        "rag_keywords",
    ),
    # ── simple care rule (schedule / threshold) ───────────────────────────
    _Rule(
        "rule_only",
        (
            "물 줘야", "물 줘도 돼", "물을 줘야", "지금 물 줘",
            "상태 어때", "괜찮아", "잘 자라고 있", "잘 크고 있",
        ),
        "rule_keywords",
    ),
    # ── complex reasoning / image / uncertain ────────────────────────────
    _Rule(
        "llm_required",
        (
            "왜", "이유가", "원인이", "진단해", "분석해",
            "사진", "이미지", "보면", "봐줘",
            "이상한 것 같", "모르겠", "복잡한",
        ),
        "llm_keywords",
    ),
)


class QuestionRouterService:
    """Routes a user question to the appropriate fast-path without LLM or DB."""

    def route(self, question: str, *, locale: str = "ko-KR") -> QuestionRouteDecision:
        """Return a routing decision for *question*.

        Matching is substring-based and case-insensitive.
        The first rule whose keywords appear in the question wins.
        Falls back to ``unknown`` when no rule matches.
        """
        q = question.strip()

        for rule in _RULES:
            for kw in rule.keywords:
                if kw in q:
                    return QuestionRouteDecision.make(
                        route=rule.route,
                        confidence=0.90,
                        reason_codes=[rule.reason_code, f"keyword:{kw}"],
                    )

        return QuestionRouteDecision.make(
            route="unknown",
            confidence=0.40,
            reason_codes=["no_keyword_match"],
        )
