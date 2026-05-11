"""MockHealingLLMClient — TICKET-032.

Deterministic mock for testing the self-healing pipeline.

Behaviour:
  - If "error-trigger" is in the system_prompt AND this is NOT a
    SELF_CORRECTION_REQUEST: return a malformed response (no section markers).
  - All other calls: delegate to MockLLMClient (always valid 4-section answer).

Stateful only in call_count — safe to reuse within a single test.
"""

from __future__ import annotations

from app.llm.mock_client import MockLLMClient, _META
from app.services.llm_port import LLMRequest, LLMResponse

_ERROR_TRIGGER = "error-trigger"
_CORRECTION_MARKER = "SELF_CORRECTION_REQUEST"

_BROKEN_CONTENT = "응답 생성 중 일시적인 오류가 발생했습니다. 형식 없이 반환합니다."


class MockHealingLLMClient:
    """LLMPort mock that deliberately fails on the first call when
    'error-trigger' is present, then heals on subsequent correction calls."""

    def __init__(self) -> None:
        self.call_count: int = 0

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.call_count += 1
        is_correction = _CORRECTION_MARKER in request.system_prompt
        is_error_trigger = _ERROR_TRIGGER in request.system_prompt

        if is_error_trigger and not is_correction:
            return LLMResponse(
                request_id=request.request_id,
                content=_BROKEN_CONTENT,
                prompt_hash=request.prompt_hash,
                model_metadata=_META,
                input_tokens=len(request.system_prompt) // 4,
                output_tokens=len(_BROKEN_CONTENT) // 4,
                finish_reason="error",
            )

        return await MockLLMClient().complete(request)
