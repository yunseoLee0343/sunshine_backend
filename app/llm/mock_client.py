"""MockLLMClient — TICKET-017.

Deterministic LLM stand-in. No network, no API key, no DB.

Determinism contract:
  - Same `prompt_hash` → identical `content` bytes.
  - The response always contains all four mandatory sections:
    [결론] [근거] [행동] [주의]
  - Guardrail awareness:
    * Pest guardrail detected → adds "참고용 지식" disclaimer in [주의].
    * "물주기 금지" directive detected → [행동] avoids recommending watering.
    * Unknown/thin-evidence guardrail detected → [결론] requests clarification.
"""

from __future__ import annotations

from app.services.llm_port import (
    LLMRequest,
    LLMResponse,
    ModelMetadata,
    StreamingNotSupportedError,
)

_MODEL_NAME = "mock-model-v1"
_PROVIDER = "mock"
_API_VERSION = "2026-05-10"

_META = ModelMetadata(
    model_name=_MODEL_NAME,
    provider=_PROVIDER,
    api_version=_API_VERSION,
)

# ---------------------------------------------------------------------------
# Guardrail detection helpers (keyword-based, no regex needed)
# ---------------------------------------------------------------------------

_PEST_SIGNAL = "참고용 지식"  # set by PromptBuilder pest guardrail
_WATERING_BAN = "물주기 금지"  # hypothetical directive for tests
_UNKNOWN_SIGNAL = "추가 정보가 필요합니다"  # set by PromptBuilder unknown guardrail
_RULE_AUTH_SIGNAL = "룰 엔진의 결과를 최우선"  # set by rule-engine authority guardrail


# ---------------------------------------------------------------------------
# Response template engine
# ---------------------------------------------------------------------------


def _build_response(request: LLMRequest) -> str:
    """Compose a deterministic 4-section response from the prompt hash."""

    # Derive a 0–255 variation index from the first two hex chars of the hash
    variation = int(request.prompt_hash[:2], 16) % 4

    pest_mode = _PEST_SIGNAL in request.system_prompt
    watering_ban = _WATERING_BAN in request.system_prompt
    unknown_mode = _UNKNOWN_SIGNAL in request.system_prompt
    rule_auth = _RULE_AUTH_SIGNAL in request.system_prompt

    # ---- [결론] -----------------------------------------------------------
    if unknown_mode:
        conclusion = (
            "추가 정보가 필요합니다. 식물의 현재 환경 데이터나 증상을 더 자세히 알려주시면 "
            "더 정확한 답변을 드릴 수 있습니다."
        )
    else:
        _conclusions = [
            "현재 식물 상태를 분석한 결과, 주어진 환경 조건에 맞는 관리가 필요합니다.",
            "센서 데이터와 룰 엔진 분석을 종합하면 식물이 현재 관리 조치를 필요로 합니다.",
            "제공된 환경 데이터를 기반으로 식물의 현재 상태를 요약했습니다.",
            "룰 엔진과 지식 청크를 종합하여 식물 상태에 대한 핵심 답변을 제공합니다.",
        ]
        conclusion = _conclusions[variation]

    # ---- [근거] -----------------------------------------------------------
    if rule_auth:
        basis = (
            "룰 엔진 분석 결과(primary_action, reason_codes)를 최우선으로 적용했습니다. "
            "지식 청크는 이를 보완하는 참고 자료로 활용했습니다."
        )
    else:
        _bases = [
            "환경 스냅샷 데이터와 관련 지식 청크를 바탕으로 분석했습니다.",
            "최근 관리 기록과 센서 측정값을 근거로 현재 상태를 판단했습니다.",
            "식물 종 특성과 현재 환경 지표를 비교하여 분석했습니다.",
            "캐릭터 상태와 환경 데이터를 종합하여 근거를 도출했습니다.",
        ]
        basis = _bases[variation]

    # ---- [행동] -----------------------------------------------------------
    if watering_ban:
        action = "현재 물주기는 권장하지 않습니다. 대신 환경 조건(빛, 온도, 습도)을 점검하고 이상이 없는지 확인하세요."
    elif unknown_mode:
        action = "현재 식물의 환경 데이터(토양 수분, 조도, 온도, 습도)를 측정하여 추가 정보를 제공해주세요."
    else:
        _actions = [
            "오늘 중으로 식물의 토양 수분을 확인하고, 필요 시 적절히 관리해주세요.",
            "현재 환경 조건을 점검하고 권장 범위에 맞게 조절해주세요.",
            "최근 관리 기록을 참고하여 정기적인 관리 루틴을 유지하세요.",
            "식물의 현재 상태를 관찰하며 권장 관리 방법을 따라주세요.",
        ]
        action = _actions[variation]

    # ---- [주의] -----------------------------------------------------------
    _cautions = [
        "과도한 관리는 오히려 식물에 해가 될 수 있으니 적정 수준을 유지하세요.",
        "환경 변화가 급격한 경우 식물이 스트레스를 받을 수 있습니다.",
        "증상이 지속될 경우 전문가 상담을 고려해보세요.",
        "계절 변화에 따라 관리 방법을 조절하는 것이 좋습니다.",
    ]
    caution = _cautions[variation]

    if pest_mode:
        caution += (
            " ※ 병충해 정보는 참고용 지식으로만 활용하세요. "
            "확정적인 진단이나 약제 처방은 전문 농업 기관에 문의하시기 바랍니다."
        )

    return f"[결론] {conclusion}\n\n[근거] {basis}\n\n[행동] {action}\n\n[주의] {caution}"


# ---------------------------------------------------------------------------
# MockLLMClient
# ---------------------------------------------------------------------------


class MockLLMClient:
    """Drop-in LLMPort implementation. No network, no external state."""

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if request.stream:
            raise StreamingNotSupportedError("Streaming is not supported in this implementation.")

        content = _build_response(request)

        return LLMResponse(
            request_id=request.request_id,
            content=content,
            prompt_hash=request.prompt_hash,
            model_metadata=_META,
            input_tokens=len(request.system_prompt + request.user_turn) // 4,
            output_tokens=len(content) // 4,
            finish_reason="stop",
        )
