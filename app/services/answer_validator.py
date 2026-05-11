"""AnswerValidator — TICKET-032.

Two-stage validation pipeline for LLM answers:
  1. FormatValidator  — all four mandatory sections present and non-empty.
  2. HallucinationChecker — heuristic consistency check against ForwardContext.

Both validators are pure functions; no I/O, no external calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.evidence import ForwardContext
from app.schemas.chat_answer import ParsedAnswer

_MIN_SECTION_LEN = 5  # chars — below this is considered placeholder / empty


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidationResult:
    passed: bool
    errors: list[str]
    failed_checks: list[str]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


class AnswerValidator:
    """Compose format + hallucination checks into one ValidationResult."""

    def validate(self, answer: ParsedAnswer, ctx: ForwardContext) -> ValidationResult:
        errors: list[str] = []
        failed: list[str] = []

        fmt_errors = _check_format(answer)
        if fmt_errors:
            errors.extend(fmt_errors)
            failed.append("format")

        hall_errors = _check_hallucination(answer, ctx)
        if hall_errors:
            errors.extend(hall_errors)
            failed.append("hallucination")

        return ValidationResult(
            passed=not errors,
            errors=errors,
            failed_checks=failed,
        )


# ---------------------------------------------------------------------------
# Format check
# ---------------------------------------------------------------------------


def _check_format(answer: ParsedAnswer) -> list[str]:
    """Return error messages for missing or effectively-empty sections."""
    errors: list[str] = []
    for label, value in (
        ("결론", answer.결론),
        ("근거", answer.근거),
        ("행동", answer.행동),
        ("주의", answer.주의),
    ):
        if not value or len(value.strip()) < _MIN_SECTION_LEN:
            errors.append(f"[{label}] 섹션이 누락되었거나 내용이 너무 짧습니다 (최소 {_MIN_SECTION_LEN}자 필요)")
    return errors


# ---------------------------------------------------------------------------
# Hallucination check
# ---------------------------------------------------------------------------

# Patterns in the 행동 section that contradict an active watering recommendation.
_ANTI_WATER_PHRASES = ("물주기 불필요", "물을 주지 마", "물주기 금지", "급수 불필요")

# Threshold: if the rule engine says watering is urgent but the answer advises
# against it, flag as a contradiction.
_WATERING_RULE_ACTIONS = ("water_now", "watering_recommended", "물주기 권장", "물을 주세요")


def _check_hallucination(answer: ParsedAnswer, ctx: ForwardContext) -> list[str]:
    """Heuristic hallucination checks against ForwardContext evidence.

    Checks performed:
    1. Minimum meaningful length per section (catches stub / error responses).
    2. Rule engine contradiction: if the rule engine recommends watering but the
       answer's 행동 section explicitly advises against it.
    """
    errors: list[str] = []

    # Check 1 — minimum content length (proxy for "actually answered")
    for label, value in (
        ("결론", answer.결론),
        ("근거", answer.근거),
        ("행동", answer.행동),
        ("주의", answer.주의),
    ):
        text = (value or "").strip()
        if len(text) < _MIN_SECTION_LEN:
            # Format check already covers this; skip duplicate reporting.
            continue

    # Check 2 — rule engine contradiction
    action_text = (answer.행동 or "").lower()
    rule_action = (ctx.rule_primary_action or "").lower()
    rule_says_water = any(kw in rule_action for kw in ("water_now", "watering_recommended"))
    answer_forbids_water = any(phrase in action_text for phrase in _ANTI_WATER_PHRASES)
    if rule_says_water and answer_forbids_water:
        errors.append(
            "답변의 [행동] 섹션이 룰 엔진 권고(물주기 권장)와 모순됩니다"
        )

    # Check 3 — no evidence but answer claims specific retrieved-chunk knowledge
    chunk_claim_phrases = ("지식 청크에 따르면", "청크 데이터에 의하면", "검색된 정보에 따르면")
    basis_text = (answer.근거 or "").lower()
    if not ctx.retrieved_chunks and any(p in basis_text for p in chunk_claim_phrases):
        errors.append(
            "검색된 지식 청크가 없으나 답변이 지식 청크를 근거로 인용하고 있습니다"
        )

    return errors
