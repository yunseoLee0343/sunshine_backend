"""PestReferenceGuardrail — TICKET-019.

Enforces non-diagnostic, reference-only constraints on pest/disease answers.
Pure functions and classes — no I/O, no DB, no LLM calls.

Design:
  PestReferenceGuardrail.apply()
    └─ _ensure_disclaimer()     — injects mandatory caution text if absent
    └─ NonDiagnosticAnswerValidator.validate()
         └─ checks flagged diagnostic phrases
         └─ checks disclaimer presence in [주의]
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.chat_answer import ParsedAnswer

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# The exact string that must appear in the [주의] section.
REQUIRED_DISCLAIMER = "본 답변은 참고용이며 정확한 진단은 전문가 확인이 필요합니다"

# Phrases that imply a definitive diagnosis or chemical prescription.
# Presence of any of these in the answer triggers a failed validation.
DIAGNOSTIC_PATTERNS: tuple[str, ...] = (
    "확진",  # confirmed diagnosis
    "처방",  # prescription
    "살균제를 사용",  # use fungicide (command form)
    "살충제를 사용",  # use insecticide (command form)
    "농약을 사용",  # use pesticide (command form)
    "병입니다",  # it is [X] disease
    "균입니다",  # it is [X] fungus
    "해충입니다",  # it is [X] pest
)


# ---------------------------------------------------------------------------
# Validation result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    flagged_phrases: tuple[str, ...]
    has_disclaimer: bool


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class NonDiagnosticAnswerValidator:
    """Checks that a parsed answer avoids diagnostic language and carries the disclaimer."""

    def validate(self, parsed: ParsedAnswer) -> ValidationResult:
        full_text = " ".join([parsed.결론, parsed.근거, parsed.행동, parsed.주의])
        flagged = tuple(p for p in DIAGNOSTIC_PATTERNS if p in full_text)
        has_disclaimer = REQUIRED_DISCLAIMER in parsed.주의
        return ValidationResult(
            is_valid=len(flagged) == 0 and has_disclaimer,
            flagged_phrases=flagged,
            has_disclaimer=has_disclaimer,
        )


# ---------------------------------------------------------------------------
# Guardrail result
# ---------------------------------------------------------------------------


@dataclass
class PestGuardrailResult:
    answer: ParsedAnswer
    is_reference_only: bool
    diagnosis_allowed: bool
    validation: ValidationResult


# ---------------------------------------------------------------------------
# Guardrail
# ---------------------------------------------------------------------------


class PestReferenceGuardrail:
    """Applies pest/disease reference constraints to a parsed LLM answer.

    Always:
      - Ensures REQUIRED_DISCLAIMER is present in [주의].
      - Sets is_reference_only=True and diagnosis_allowed=False.
      - Runs NonDiagnosticAnswerValidator and records result.
    """

    def __init__(self) -> None:
        self._validator = NonDiagnosticAnswerValidator()

    def apply(self, parsed: ParsedAnswer) -> PestGuardrailResult:
        enhanced = self._ensure_disclaimer(parsed)
        validation = self._validator.validate(enhanced)
        return PestGuardrailResult(
            answer=enhanced,
            is_reference_only=True,
            diagnosis_allowed=False,
            validation=validation,
        )

    def _ensure_disclaimer(self, parsed: ParsedAnswer) -> ParsedAnswer:
        if REQUIRED_DISCLAIMER in parsed.주의:
            return parsed
        separator = " " if parsed.주의 else ""
        new_주의 = f"{parsed.주의}{separator}{REQUIRED_DISCLAIMER}."
        return ParsedAnswer(
            결론=parsed.결론,
            근거=parsed.근거,
            행동=parsed.행동,
            주의=new_주의,
        )
