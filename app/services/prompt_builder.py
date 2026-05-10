"""PromptBuilder — TICKET-016.

Converts a ForwardContext into a deterministic LLM system-prompt string.

Guarantees:
  - Same ForwardContext → identical prompt bytes (no datetime.now(), no random).
  - All four answer-format sections ([결론][근거][행동][주의]) are mandated.
  - Rule-engine results always outrank retrieved knowledge chunks when the two
    conflict (authority guardrail).
  - Pest/disease questions carry a reference-only disclaimer.
  - Unknown intent or thin evidence triggers a clarification-first guardrail.

No LLM calls, no DB access, no external I/O.
"""

from __future__ import annotations

from app.domain.evidence import ChunkEvidence, ForwardContext
from app.domain.prompt_build_result import PromptBuildResult, build_prompt_result

# ---------------------------------------------------------------------------
# Guardrail identifiers
# ---------------------------------------------------------------------------

_GR_RULE_AUTHORITY = "rule_engine_authority"
_GR_PEST = "pest_reference_only"
_GR_UNKNOWN = "unknown_intent_clarify"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


class PromptBuilder:
    """Pure, stateless prompt builder. Instantiate once and reuse freely."""

    def build(self, ctx: ForwardContext) -> PromptBuildResult:
        guardrails = _select_guardrails(ctx)
        system_prompt = _render_system_prompt(ctx, guardrails)
        return build_prompt_result(
            system_prompt=system_prompt,
            user_turn=ctx.question,
            intent=ctx.intent,
            guardrails_applied=guardrails,
        )


# ---------------------------------------------------------------------------
# Guardrail selection (deterministic)
# ---------------------------------------------------------------------------


def _select_guardrails(ctx: ForwardContext) -> list[str]:
    applied: list[str] = []

    # Rule-engine authority: applied whenever the rule engine has any output
    if ctx.rule_reason_codes or ctx.rule_evidence_facts:
        applied.append(_GR_RULE_AUTHORITY)

    # Pest guardrail: pest-related intent
    if ctx.intent == "pest_reference_question":
        applied.append(_GR_PEST)

    # Unknown / thin-evidence guardrail
    evidence_thin = not any(ctx.source_coverage.values())
    if ctx.intent == "unknown_question" or evidence_thin:
        applied.append(_GR_UNKNOWN)

    return sorted(applied)


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


def _render_system_prompt(ctx: ForwardContext, guardrails: list[str]) -> str:
    parts: list[str] = []

    parts.append(_ROLE_HEADER)
    parts.append(_render_context(ctx))
    parts.append(_render_rule_section(ctx))
    parts.append(_render_knowledge_section(ctx))
    parts.append(_ANSWER_FORMAT)
    parts.append(_render_guardrails(guardrails))

    return "\n\n".join(p for p in parts if p.strip())


# ---------------------------------------------------------------------------
# Fixed text blocks (Korean)
# ---------------------------------------------------------------------------

_ROLE_HEADER = """\
# 식물 관리 전문가 AI

당신은 신뢰할 수 있는 식물 관리 전문가 AI입니다.
아래 제공된 식물 상태 데이터와 지식 청크를 바탕으로 사용자 질문에 답변하세요.
제공되지 않은 정보는 스스로 만들어내지 마세요.\
"""

_ANSWER_FORMAT = """\
## 답변 형식 (필수)

답변은 반드시 아래 4개 섹션을 모두 포함해야 합니다.
섹션 레이블은 정확히 대괄호 형식([결론] 등)을 사용하세요.

[결론] 질문에 대한 핵심 요약 답변 (2~3문장)
[근거] 룰 엔진 분석 결과 및 지식 청크를 근거로 한 설명
[행동] 사용자가 지금 즉시 취해야 할 구체적인 실천 사항
[주의] 부작용, 예외 상황 또는 추가 확인이 필요한 사항\
"""

_GUARDRAIL_RULE_AUTHORITY = """\
### 룰 엔진 우선 원칙
룰 엔진이 도출한 분석 결과(primary_action, reason_codes)와 지식 청크 내용이 \
서로 충돌할 경우, **룰 엔진의 결과를 최우선으로 반영**하세요.
지식 청크는 룰 결과를 보완하는 참고 자료로만 활용하세요.\
"""

_GUARDRAIL_PEST = """\
### 병충해 참고 전용 원칙
병충해 관련 정보를 다룰 때는 다음 규칙을 반드시 준수하세요.
- 확정적인 진단("이 병입니다", "이 해충입니다")을 내리지 마세요.
- 특정 약제나 화학적 처방을 지시하지 마세요.
- 모든 병충해 정보는 "참고용 지식"임을 [주의] 섹션에 명시하세요.
- 전문 농업 기관 또는 전문가 상담을 권유하세요.\
"""

_GUARDRAIL_UNKNOWN = """\
### 불확실 상황 처리 원칙
질문 의도가 불명확하거나 관련 지식이 충분하지 않은 경우:
- 확신 있는 단정적 답변을 피하세요.
- [결론] 섹션에서 "추가 정보가 필요합니다"를 명시하세요.
- [행동] 섹션에 사용자에게 필요한 추가 정보 요청을 포함하세요.\
"""

_GUARDRAIL_MAP = {
    _GR_RULE_AUTHORITY: _GUARDRAIL_RULE_AUTHORITY,
    _GR_PEST:           _GUARDRAIL_PEST,
    _GR_UNKNOWN:        _GUARDRAIL_UNKNOWN,
}


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def _render_context(ctx: ForwardContext) -> str:
    lines: list[str] = ["## 현재 질문 및 의도"]
    lines.append(f"- 질문: {ctx.question}")
    lines.append(f"- 의도: {ctx.intent}")

    # Character state
    lines.append("\n### 식물 캐릭터 상태")
    if ctx.character:
        c = ctx.character
        lines.append(f"- 기분: {c.mood}")
        lines.append(f"- 표정: {c.expression}")
        lines.append(f"- 상태 메시지: {c.status_message}")
        lines.append(f"- 현재 주요 조치: {c.primary_action}")
        lines.append(f"- 원인 코드: {c.reason_code}")
    else:
        lines.append("- 캐릭터 상태 없음")

    # Environment snapshot
    lines.append("\n### 환경 스냅샷")
    if ctx.snapshot:
        s = ctx.snapshot
        lines.append(f"- 창 구간: {s.window}")
        lines.append(f"- 온도(평균): {_fmt_num(s.temperature_avg_c, '°C')}")
        lines.append(f"- 습도(평균): {_fmt_num(s.humidity_avg_pct, '%')}")
        lines.append(f"- 조도(평균): {_fmt_num(s.light_avg_lux, 'lux')}")
        lines.append(f"- 토양 수분(평균): {_fmt_num(s.soil_moisture_avg_pct, '%')}")
    else:
        lines.append("- 환경 스냅샷 없음")

    # Recent care logs
    lines.append("\n### 최근 관리 기록")
    if ctx.recent_care_logs:
        for log in ctx.recent_care_logs:
            note_part = f" (메모: {log.note})" if log.note else ""
            lines.append(f"- [{log.acted_at}] {log.action_type}{note_part}")
    else:
        lines.append("- 최근 관리 기록 없음")

    return "\n".join(lines)


def _render_rule_section(ctx: ForwardContext) -> str:
    lines: list[str] = ["## 룰 엔진 분석 결과"]
    lines.append(f"- 주요 조치(primary_action): {ctx.rule_primary_action}")

    if ctx.rule_reason_codes:
        codes = ", ".join(ctx.rule_reason_codes)
        lines.append(f"- 원인 코드(reason_codes): {codes}")
    else:
        lines.append("- 원인 코드: 없음")

    if ctx.rule_evidence_facts:
        lines.append("- 증거 데이터:")
        for k in sorted(ctx.rule_evidence_facts.keys()):
            lines.append(f"  • {k}: {ctx.rule_evidence_facts[k]}")
    else:
        lines.append("- 증거 데이터: 없음")

    return "\n".join(lines)


def _render_knowledge_section(ctx: ForwardContext) -> str:
    lines: list[str] = ["## 관련 지식 청크"]

    coverage_any = any(ctx.source_coverage.values())
    if not coverage_any:
        lines.append("관련 지식 청크가 없습니다.")
        return "\n".join(lines)

    # Group by chunk_kind for readability; order by rank
    for chunk in sorted(ctx.retrieved_chunks, key=lambda c: c.rank):
        lines.append(_render_chunk(chunk))

    # Source coverage summary
    lines.append("\n### 지식 커버리지")
    for layer in sorted(ctx.source_coverage.keys()):
        covered = "✓" if ctx.source_coverage[layer] else "✗"
        lines.append(f"- {layer}: {covered}")

    return "\n".join(lines)


def _render_chunk(chunk: ChunkEvidence) -> str:
    return (
        f"\n[청크 #{chunk.rank} | 종류: {chunk.chunk_kind} "
        f"| 유사도: {chunk.similarity_score:.4f}]\n{chunk.chunk_text}"
    )


def _render_guardrails(guardrails: list[str]) -> str:
    if not guardrails:
        return ""
    lines: list[str] = ["## 가드레일 (반드시 준수)"]
    for gr in guardrails:
        text = _GUARDRAIL_MAP.get(gr, "")
        if text:
            lines.append(text)
    return "\n\n".join(lines)


def _fmt_num(value: float | None, unit: str) -> str:
    if value is None:
        return "데이터 없음"
    return f"{value:.1f} {unit}"
