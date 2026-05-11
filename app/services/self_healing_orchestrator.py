"""SelfHealingOrchestrator — TICKET-032.

Wraps the LLM completion + answer parsing steps with a validation loop:

  for attempt in 1..MAX_ATTEMPTS:
      response = llm.complete(request)
      answer   = parse(response)
      result   = validator.validate(answer, ctx)
      if result.passed:
          break
      request = build_correction_request(request, result)

Returns a HealingResult that the ChatOrchestrator persists as
llm_self_healing_logs rows and includes in the audit trail.

Stateless, pure (no DB access, no network calls).
"""

from __future__ import annotations

import dataclasses
import hashlib
from dataclasses import dataclass, field

from app.domain.evidence import ForwardContext
from app.schemas.chat_answer import ParsedAnswer
from app.services.answer_validator import AnswerValidator, ValidationResult
from app.services.llm_port import LLMPort, LLMRequest, LLMResponse
from app.services.response_parser import parse_answer

MAX_ATTEMPTS = 3

_VALIDATOR = AnswerValidator()

# Marker injected into correction prompts so mocks (and future real clients)
# can detect they are responding to a self-correction request.
_CORRECTION_MARKER = "SELF_CORRECTION_REQUEST"

_CORRECTION_SNIPPET_LEN = 500


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HealingAttempt:
    attempt_num: int
    response_text: str
    validation_result: ValidationResult
    correction_prompt: str | None  # None for the final attempt (win or lose)


@dataclass
class HealingResult:
    final_llm_response: LLMResponse
    parsed_answer: ParsedAnswer
    healing_occurred: bool  # True when at least one retry was needed
    total_attempts: int
    attempts: list[HealingAttempt]


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class SelfHealingOrchestrator:
    """Stateless; instantiate once and reuse freely."""

    async def run_with_healing(
        self,
        *,
        llm_client: LLMPort,
        llm_request: LLMRequest,
        ctx: ForwardContext,
    ) -> HealingResult:
        attempts: list[HealingAttempt] = []
        current_request = llm_request
        llm_resp: LLMResponse | None = None
        parsed: ParsedAnswer | None = None
        validation: ValidationResult | None = None

        for attempt_num in range(1, MAX_ATTEMPTS + 1):
            llm_resp = await llm_client.complete(current_request)
            parsed = parse_answer(llm_resp.content)
            validation = _VALIDATOR.validate(parsed, ctx)

            is_last = attempt_num == MAX_ATTEMPTS
            if validation.passed or is_last:
                attempts.append(
                    HealingAttempt(
                        attempt_num=attempt_num,
                        response_text=llm_resp.content,
                        validation_result=validation,
                        correction_prompt=None,
                    )
                )
                break

            # Build correction prompt for the next iteration
            correction_prompt = _build_correction_prompt(current_request.system_prompt, validation)
            correction_hash = hashlib.sha256(correction_prompt.encode("utf-8")).hexdigest()
            attempts.append(
                HealingAttempt(
                    attempt_num=attempt_num,
                    response_text=llm_resp.content,
                    validation_result=validation,
                    correction_prompt=correction_prompt[:_CORRECTION_SNIPPET_LEN],
                )
            )
            current_request = dataclasses.replace(
                current_request,
                system_prompt=correction_prompt,
                prompt_hash=correction_hash,
            )

        healing_occurred = len(attempts) > 1 or (
            len(attempts) == 1 and not attempts[0].validation_result.passed
        )

        return HealingResult(
            final_llm_response=llm_resp,  # type: ignore[arg-type]
            parsed_answer=parsed,  # type: ignore[arg-type]
            healing_occurred=healing_occurred,
            total_attempts=len(attempts),
            attempts=attempts,
        )


# ---------------------------------------------------------------------------
# Correction prompt builder
# ---------------------------------------------------------------------------


def _build_correction_prompt(original_prompt: str, result: ValidationResult) -> str:
    error_lines = "\n".join(f"  - {e}" for e in result.errors)
    checks = ", ".join(result.failed_checks)
    header = (
        f"## {_CORRECTION_MARKER}\n\n"
        f"이전 응답이 다음 검증을 통과하지 못했습니다 (실패 항목: {checks}):\n"
        f"{error_lines}\n\n"
        "위 오류를 수정하여 [결론][근거][행동][주의] 형식으로 다시 답변하세요.\n\n"
        "---\n\n"
    )
    return header + original_prompt
