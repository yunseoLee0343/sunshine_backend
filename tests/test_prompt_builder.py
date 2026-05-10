"""TICKET-016 — PromptBuilder pure-logic tests (no DB, no LLM)."""

from __future__ import annotations

import hashlib
import uuid

import pytest

from app.domain.evidence import (
    CareLogEvidence,
    CharacterEvidence,
    ChunkEvidence,
    ForwardContext,
    SnapshotEvidence,
)
from app.domain.prompt_build_result import PromptBuildResult, build_prompt_result
from app.services.prompt_builder import (
    _GR_PEST,
    _GR_RULE_AUTHORITY,
    _GR_UNKNOWN,
    PromptBuilder,
    _select_guardrails,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ctx(**overrides) -> ForwardContext:
    defaults = dict(
        plant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        question="몬스테라 물주기 알려줘",
        intent="watering_question",
        rag_layers=["care_knowledge"],
        character=None,
        snapshot=None,
        recent_care_logs=[],
        rule_evidence_facts={},
        rule_reason_codes=[],
        rule_primary_action="none",
        retrieved_chunks=[],
        source_coverage={"care_knowledge": False},
    )
    defaults.update(overrides)
    return ForwardContext.build(**defaults)


_builder = PromptBuilder()


# ---------------------------------------------------------------------------
# PromptBuildResult
# ---------------------------------------------------------------------------


def test_prompt_build_result_hash_is_sha256_of_system_prompt() -> None:
    r = build_prompt_result(
        system_prompt="test prompt",
        user_turn="question",
        intent="watering_question",
        guardrails_applied=[],
    )
    expected = hashlib.sha256("test prompt".encode()).hexdigest()
    assert r.prompt_hash == expected


def test_prompt_build_result_is_frozen() -> None:
    r = build_prompt_result(
        system_prompt="test",
        user_turn="q",
        intent="watering_question",
        guardrails_applied=[],
    )
    with pytest.raises((AttributeError, TypeError)):
        r.system_prompt = "mutated"  # type: ignore[misc]


def test_guardrails_applied_is_sorted_tuple() -> None:
    r = build_prompt_result(
        system_prompt="test",
        user_turn="q",
        intent="watering_question",
        guardrails_applied=[_GR_UNKNOWN, _GR_PEST],
    )
    assert r.guardrails_applied == tuple(sorted([_GR_PEST, _GR_UNKNOWN]))


def test_token_estimate_positive() -> None:
    r = _builder.build(_ctx())
    assert r.token_estimate > 0


# ---------------------------------------------------------------------------
# Determinism: same ForwardContext → identical prompt
# ---------------------------------------------------------------------------


def test_prompt_is_deterministic() -> None:
    ctx = _ctx(question="몬스테라 물은 얼마나 자주 줘야 해?")
    r1 = _builder.build(ctx)
    r2 = _builder.build(ctx)
    assert r1.system_prompt == r2.system_prompt
    assert r1.prompt_hash == r2.prompt_hash


def test_different_question_produces_different_prompt() -> None:
    h1 = _builder.build(_ctx(question="물주기")).prompt_hash
    h2 = _builder.build(_ctx(question="빛 요구량")).prompt_hash
    assert h1 != h2


def test_different_intent_produces_different_prompt() -> None:
    h1 = _builder.build(_ctx(intent="watering_question")).prompt_hash
    h2 = _builder.build(_ctx(intent="light_question")).prompt_hash
    assert h1 != h2


# ---------------------------------------------------------------------------
# Answer format: all 4 section labels present
# ---------------------------------------------------------------------------


def test_prompt_contains_결론_section() -> None:
    r = _builder.build(_ctx())
    assert "[결론]" in r.system_prompt


def test_prompt_contains_근거_section() -> None:
    r = _builder.build(_ctx())
    assert "[근거]" in r.system_prompt


def test_prompt_contains_행동_section() -> None:
    r = _builder.build(_ctx())
    assert "[행동]" in r.system_prompt


def test_prompt_contains_주의_section() -> None:
    r = _builder.build(_ctx())
    assert "[주의]" in r.system_prompt


# ---------------------------------------------------------------------------
# Guardrail: rule-engine authority
# ---------------------------------------------------------------------------


def test_rule_authority_guardrail_applied_when_reason_codes_present() -> None:
    ctx = _ctx(rule_reason_codes=["low_soil_moisture"])
    r = _builder.build(ctx)
    assert _GR_RULE_AUTHORITY in r.guardrails_applied


def test_rule_authority_guardrail_applied_when_evidence_facts_present() -> None:
    ctx = _ctx(rule_evidence_facts={"watering.soil_moisture_avg_pct": 18.5})
    r = _builder.build(ctx)
    assert _GR_RULE_AUTHORITY in r.guardrails_applied


def test_rule_authority_text_in_prompt_when_applied() -> None:
    ctx = _ctx(rule_reason_codes=["low_soil_moisture"])
    r = _builder.build(ctx)
    assert "룰 엔진" in r.system_prompt
    assert "최우선" in r.system_prompt


def test_rule_authority_not_applied_when_no_rule_output() -> None:
    ctx = _ctx(rule_reason_codes=[], rule_evidence_facts={})
    r = _builder.build(ctx)
    assert _GR_RULE_AUTHORITY not in r.guardrails_applied


# ---------------------------------------------------------------------------
# Guardrail: pest reference only
# ---------------------------------------------------------------------------


def test_pest_guardrail_applied_for_pest_intent() -> None:
    ctx = _ctx(intent="pest_reference_question")
    r = _builder.build(ctx)
    assert _GR_PEST in r.guardrails_applied


def test_pest_guardrail_text_in_prompt() -> None:
    ctx = _ctx(intent="pest_reference_question")
    r = _builder.build(ctx)
    assert "진단" in r.system_prompt
    assert "참고용" in r.system_prompt


def test_pest_guardrail_not_applied_for_watering_intent() -> None:
    ctx = _ctx(intent="watering_question")
    r = _builder.build(ctx)
    assert _GR_PEST not in r.guardrails_applied


# ---------------------------------------------------------------------------
# Guardrail: unknown / thin evidence
# ---------------------------------------------------------------------------


def test_unknown_guardrail_applied_for_unknown_intent() -> None:
    ctx = _ctx(intent="unknown_question")
    r = _builder.build(ctx)
    assert _GR_UNKNOWN in r.guardrails_applied


def test_unknown_guardrail_applied_when_all_coverage_false() -> None:
    ctx = _ctx(
        intent="watering_question",
        source_coverage={"care_knowledge": False, "species_profile": False},
    )
    r = _builder.build(ctx)
    assert _GR_UNKNOWN in r.guardrails_applied


def test_unknown_guardrail_not_applied_when_coverage_exists() -> None:
    ctx = _ctx(
        intent="watering_question",
        source_coverage={"care_knowledge": True},
    )
    r = _builder.build(ctx)
    assert _GR_UNKNOWN not in r.guardrails_applied


def test_unknown_guardrail_text_in_prompt() -> None:
    ctx = _ctx(intent="unknown_question")
    r = _builder.build(ctx)
    assert "추가 정보" in r.system_prompt


# ---------------------------------------------------------------------------
# Context sections rendered
# ---------------------------------------------------------------------------


def test_question_appears_in_prompt() -> None:
    ctx = _ctx(question="잎이 노래져요")
    r = _builder.build(ctx)
    assert "잎이 노래져요" in r.system_prompt


def test_intent_appears_in_prompt() -> None:
    ctx = _ctx(intent="light_question")
    r = _builder.build(ctx)
    assert "light_question" in r.system_prompt


def test_character_state_rendered_when_present() -> None:
    char = CharacterEvidence(
        mood="sad", expression="😢",
        status_message="물이 부족해요",
        primary_action="water", reason_code="low_soil_moisture",
    )
    ctx = _ctx(character=char)
    r = _builder.build(ctx)
    assert "물이 부족해요" in r.system_prompt
    assert "low_soil_moisture" in r.system_prompt


def test_character_absent_shows_fallback() -> None:
    ctx = _ctx(character=None)
    r = _builder.build(ctx)
    assert "캐릭터 상태 없음" in r.system_prompt


def test_snapshot_metrics_rendered_when_present() -> None:
    snap = SnapshotEvidence(
        window="latest",
        temperature_avg_c=22.5,
        humidity_avg_pct=60.0,
        light_avg_lux=3000.0,
        soil_moisture_avg_pct=35.0,
    )
    ctx = _ctx(snapshot=snap)
    r = _builder.build(ctx)
    assert "22.5" in r.system_prompt
    assert "60.0" in r.system_prompt


def test_snapshot_none_metrics_show_data_없음() -> None:
    snap = SnapshotEvidence(
        window="latest",
        temperature_avg_c=None,
        humidity_avg_pct=None,
        light_avg_lux=None,
        soil_moisture_avg_pct=None,
    )
    ctx = _ctx(snapshot=snap)
    r = _builder.build(ctx)
    assert "데이터 없음" in r.system_prompt


def test_care_log_rendered() -> None:
    log = CareLogEvidence(
        action_type="watering",
        note="흠뻑 줬음",
        acted_at="2026-05-10T08:00:00+00:00",
    )
    ctx = _ctx(recent_care_logs=[log])
    r = _builder.build(ctx)
    assert "watering" in r.system_prompt
    assert "흠뻑 줬음" in r.system_prompt


def test_rule_evidence_facts_sorted_in_prompt() -> None:
    ctx = _ctx(
        rule_evidence_facts={
            "watering.soil_moisture_avg_pct": 18.5,
            "light.light_avg_lux": 500.0,
        },
        rule_reason_codes=["low_soil_moisture"],
    )
    r = _builder.build(ctx)
    # Both keys must appear in alphabetical order
    idx_light = r.system_prompt.index("light.light_avg_lux")
    idx_water = r.system_prompt.index("watering.soil_moisture_avg_pct")
    assert idx_light < idx_water


def test_chunks_rendered_in_rank_order() -> None:
    c1 = ChunkEvidence(
        chunk_document_id=str(uuid.uuid4()), plant_knowledge_id=str(uuid.uuid4()),
        chunk_kind="care_requirement", chunk_text="관리 정보", similarity_score=0.9, rank=1,
    )
    c2 = ChunkEvidence(
        chunk_document_id=str(uuid.uuid4()), plant_knowledge_id=str(uuid.uuid4()),
        chunk_kind="seasonal_watering", chunk_text="계절별 물주기", similarity_score=0.8, rank=2,
    )
    ctx = _ctx(
        retrieved_chunks=[c2, c1],  # intentionally reversed order
        source_coverage={"care_knowledge": True},
    )
    r = _builder.build(ctx)
    idx1 = r.system_prompt.index("관리 정보")
    idx2 = r.system_prompt.index("계절별 물주기")
    assert idx1 < idx2  # rank 1 must appear before rank 2


def test_no_chunks_shows_fallback() -> None:
    ctx = _ctx(retrieved_chunks=[], source_coverage={"care_knowledge": False})
    r = _builder.build(ctx)
    assert "지식 청크가 없습니다" in r.system_prompt


# ---------------------------------------------------------------------------
# user_turn matches question verbatim
# ---------------------------------------------------------------------------


def test_user_turn_matches_question() -> None:
    ctx = _ctx(question="몬스테라 빛은 얼마나 필요해?")
    r = _builder.build(ctx)
    assert r.user_turn == "몬스테라 빛은 얼마나 필요해?"


# ---------------------------------------------------------------------------
# No forbidden imports
# ---------------------------------------------------------------------------


def test_prompt_builder_has_no_llm_imports() -> None:
    import app.services.prompt_builder as mod
    src = open(mod.__file__, encoding="utf-8").read()
    for forbidden in ("openai", "anthropic", "requests", "httpx", "torch"):
        assert forbidden not in src, f"Forbidden import: {forbidden!r}"


def test_prompt_build_result_has_no_llm_imports() -> None:
    import app.domain.prompt_build_result as mod
    src = open(mod.__file__, encoding="utf-8").read()
    for forbidden in ("openai", "anthropic", "requests", "httpx"):
        assert forbidden not in src, f"Forbidden import: {forbidden!r}"
