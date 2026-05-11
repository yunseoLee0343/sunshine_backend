"""TICKET-023 — Demo seed unit tests.

All tests are DB-free. They verify:
  - ID generation stability (uuid5 reproducibility)
  - make_vector determinism and shape
  - SeedResult accumulation logic
  - Scenario step structure and count
  - Intent classifier accuracy on the 12-step scenario's sample questions
  - _step12_intent_classifier passes without DB
"""

from __future__ import annotations

import uuid

from app.seeds.demo_scenario import ScenarioStep, _step12_intent_classifier
from app.seeds.demo_seed import (
    DEMO_KNOWLEDGE_ID,
    DEMO_MONSTERA_SPECIES_ID,
    DEMO_PHILODENDRON_SPECIES_ID,
    DEMO_PLANT_ID,
    DEMO_POTHOS_SPECIES_ID,
    DEMO_SANSEVIERIA_SPECIES_ID,
    DEMO_SPATHIPHYLLUM_SPECIES_ID,
    DEMO_USER_ID,
    SeedResult,
    demo_id,
    make_vector,
)

# ---------------------------------------------------------------------------
# demo_id (ID stability)
# ---------------------------------------------------------------------------


def test_demo_id_returns_uuid() -> None:
    result = demo_id("test-entity")
    assert isinstance(result, uuid.UUID)


def test_demo_id_is_stable() -> None:
    assert demo_id("user-001") == demo_id("user-001")


def test_demo_id_varies_by_name() -> None:
    assert demo_id("entity-a") != demo_id("entity-b")


def test_demo_user_id_is_stable() -> None:
    assert DEMO_USER_ID == demo_id("user-001")


def test_demo_plant_id_is_stable() -> None:
    assert DEMO_PLANT_ID == demo_id("plant-monstera-001")


def test_demo_monstera_species_id_is_stable() -> None:
    assert DEMO_MONSTERA_SPECIES_ID == demo_id("species-monstera")


def test_demo_pothos_species_id_is_stable() -> None:
    assert DEMO_POTHOS_SPECIES_ID == demo_id("species-pothos")


def test_demo_philodendron_species_id_is_stable() -> None:
    assert DEMO_PHILODENDRON_SPECIES_ID == demo_id("species-philodendron")


def test_demo_spathiphyllum_species_id_is_stable() -> None:
    assert DEMO_SPATHIPHYLLUM_SPECIES_ID == demo_id("species-spathiphyllum")


def test_demo_sansevieria_species_id_is_stable() -> None:
    assert DEMO_SANSEVIERIA_SPECIES_ID == demo_id("species-sansevieria")


def test_demo_knowledge_id_is_stable() -> None:
    assert DEMO_KNOWLEDGE_ID == demo_id("knowledge-monstera")


def test_all_demo_ids_unique() -> None:
    ids = [
        DEMO_USER_ID,
        DEMO_PLANT_ID,
        DEMO_MONSTERA_SPECIES_ID,
        DEMO_POTHOS_SPECIES_ID,
        DEMO_PHILODENDRON_SPECIES_ID,
        DEMO_SPATHIPHYLLUM_SPECIES_ID,
        DEMO_SANSEVIERIA_SPECIES_ID,
        DEMO_KNOWLEDGE_ID,
    ]
    assert len(set(ids)) == len(ids)


# ---------------------------------------------------------------------------
# make_vector (determinism and shape)
# ---------------------------------------------------------------------------


def test_make_vector_default_dim() -> None:
    v = make_vector("test-chunk")
    assert len(v) == 384


def test_make_vector_custom_dim() -> None:
    v = make_vector("test", dim=16)
    assert len(v) == 16


def test_make_vector_is_deterministic() -> None:
    v1 = make_vector("care_knowledge:abc")
    v2 = make_vector("care_knowledge:abc")
    assert v1 == v2


def test_make_vector_varies_by_seed() -> None:
    v1 = make_vector("seed-a")
    v2 = make_vector("seed-b")
    assert v1 != v2


def test_make_vector_values_in_range() -> None:
    v = make_vector("range-check", dim=64)
    assert all(-1.0 <= x <= 1.0 for x in v)


def test_make_vector_elements_are_floats() -> None:
    v = make_vector("type-check", dim=8)
    assert all(isinstance(x, float) for x in v)


# ---------------------------------------------------------------------------
# SeedResult
# ---------------------------------------------------------------------------


def test_seed_result_starts_empty() -> None:
    r = SeedResult()
    assert r.created == []
    assert r.skipped == []
    assert r.errors == []


def test_seed_result_record_created() -> None:
    r = SeedResult()
    r.record("created", "user:demo-001")
    assert "user:demo-001" in r.created
    assert len(r.skipped) == 0


def test_seed_result_record_skipped() -> None:
    r = SeedResult()
    r.record("skipped", "plant:초록이")
    assert "plant:초록이" in r.skipped


def test_seed_result_record_error() -> None:
    r = SeedResult()
    r.record("error", "snapshot:1h")
    assert "snapshot:1h" in r.errors


def test_seed_result_to_dict_keys() -> None:
    r = SeedResult()
    r.record("created", "x")
    r.record("skipped", "y")
    d = r.to_dict()
    assert set(d.keys()) == {"created", "skipped", "errors", "summary"}


def test_seed_result_to_dict_summary_counts() -> None:
    r = SeedResult()
    r.record("created", "a")
    r.record("created", "b")
    r.record("skipped", "c")
    d = r.to_dict()
    assert d["summary"]["created"] == 2
    assert d["summary"]["skipped"] == 1
    assert d["summary"]["errors"] == 0


# ---------------------------------------------------------------------------
# ScenarioStep structure
# ---------------------------------------------------------------------------


def test_scenario_step_fields() -> None:
    step = ScenarioStep(step=1, description="test", passed=True, detail="ok")
    assert step.step == 1
    assert step.description == "test"
    assert step.passed is True
    assert step.detail == "ok"


def test_scenario_step_failed() -> None:
    step = ScenarioStep(step=5, description="sensor", passed=False, detail="count=0")
    assert step.passed is False


# ---------------------------------------------------------------------------
# Step 12 — intent classifier (no DB)
# ---------------------------------------------------------------------------


def test_step12_passes() -> None:
    step = _step12_intent_classifier()
    assert isinstance(step, ScenarioStep)
    assert step.step == 12
    assert step.passed is True


def test_step12_detail_contains_check_marks() -> None:
    step = _step12_intent_classifier()
    assert "✓" in step.detail


def test_step12_description_mentions_intent() -> None:
    step = _step12_intent_classifier()
    assert "의도 분류기" in step.description


def test_step12_watering_question_classified_correctly() -> None:
    from app.services.chat_intent_classifier import ChatIntentClassifier

    clf = ChatIntentClassifier()
    intent, _, _ = clf.classify("물 주는 시기가 언제야?")
    assert intent == "watering_question"


def test_step12_pest_question_classified_correctly() -> None:
    from app.services.chat_intent_classifier import ChatIntentClassifier

    clf = ChatIntentClassifier()
    intent, _, _ = clf.classify("잎이 노랗게 변하고 있어요. 병인가요?")
    assert intent == "pest_reference_question"


def test_step12_companion_question_classified_correctly() -> None:
    from app.services.chat_intent_classifier import ChatIntentClassifier

    clf = ChatIntentClassifier()
    intent, _, _ = clf.classify("몬스테라랑 같이 키울 수 있는 식물 추천해줘")
    assert intent == "companion_plant_question"
