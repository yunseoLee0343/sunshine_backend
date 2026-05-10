"""TICKET-020 — CompanionFilterService unit tests (no network, no DB)."""

from __future__ import annotations

import uuid

import pytest

from app.domain.companion import CompanionCandidate, CompatibilityResult, RoomEnvironment
from app.services.companion_filter_service import filter_companions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cand(
    name: str = "테스트 식물",
    scientific: str = "Testus plantus",
    light_min: float | None = 500.0,
    light_max: float | None = 2000.0,
    humi_min: float | None = 40.0,
    humi_max: float | None = 70.0,
    temp_min: float | None = 18.0,
    temp_max: float | None = 28.0,
    placement_tags: tuple[str, ...] = (),
    is_toxic: bool = False,
    toxic_to_pets: bool = False,
    toxic_to_children: bool = False,
    species_id: uuid.UUID | None = None,
) -> CompanionCandidate:
    return CompanionCandidate(
        species_id=species_id or uuid.uuid4(),
        scientific_name=scientific,
        common_name=name,
        light_min_lux=light_min,
        light_max_lux=light_max,
        humidity_min_pct=humi_min,
        humidity_max_pct=humi_max,
        temperature_min_c=temp_min,
        temperature_max_c=temp_max,
        placement_tags=placement_tags,
        is_toxic=is_toxic,
        toxic_to_pets=toxic_to_pets,
        toxic_to_children=toxic_to_children,
    )


def _env(
    light: float | None = 1000.0,
    humidity: float | None = 55.0,
    temperature: float | None = 23.0,
    room: str | None = "거실",
) -> RoomEnvironment:
    return RoomEnvironment(
        light_avg_lux=light,
        humidity_avg_pct=humidity,
        temperature_avg_c=temperature,
        room_name=room,
    )


# ---------------------------------------------------------------------------
# Domain object construction
# ---------------------------------------------------------------------------


def test_companion_candidate_is_frozen() -> None:
    c = _cand()
    with pytest.raises((AttributeError, TypeError)):
        c.common_name = "변경"  # type: ignore[misc]


def test_room_environment_is_frozen() -> None:
    e = _env()
    with pytest.raises((AttributeError, TypeError)):
        e.room_name = "침실"  # type: ignore[misc]


def test_compatibility_result_is_frozen() -> None:
    results = filter_companions([_cand()], _env())
    r = results[0]
    with pytest.raises((AttributeError, TypeError)):
        r.score = 0.0  # type: ignore[misc]


def test_candidate_defaults_all_none_thresholds() -> None:
    c = CompanionCandidate(
        species_id=uuid.uuid4(),
        scientific_name="X",
        common_name="X",
    )
    assert c.light_min_lux is None
    assert c.is_toxic is False


def test_room_environment_all_none() -> None:
    e = RoomEnvironment()
    assert e.light_avg_lux is None
    assert e.room_name is None


# ---------------------------------------------------------------------------
# Perfect match — all 3 dimensions within range
# ---------------------------------------------------------------------------


def test_perfect_match_score_is_1() -> None:
    c = _cand(light_min=500, light_max=2000, humi_min=40, humi_max=70,
              temp_min=18, temp_max=28)
    env = _env(light=1000, humidity=55, temperature=23)
    results = filter_companions([c], env)
    assert results[0].score == 1.0


def test_perfect_match_assessed_3() -> None:
    results = filter_companions([_cand()], _env())
    assert results[0].assessed_dimensions == 3


def test_perfect_match_is_compatible_true() -> None:
    results = filter_companions([_cand()], _env())
    assert results[0].is_compatible is True


def test_perfect_match_reasons_contain_적합() -> None:
    results = filter_companions([_cand()], _env())
    reasons_text = " ".join(results[0].reasons)
    assert "적합" in reasons_text


# ---------------------------------------------------------------------------
# Partial match — 2/3 dimensions match
# ---------------------------------------------------------------------------


def test_partial_match_two_thirds_score() -> None:
    # Light and humidity match, temperature out of range
    c = _cand(temp_min=25, temp_max=35)          # room is 23°C → too cold
    env = _env(light=1000, humidity=55, temperature=23)
    results = filter_companions([c], env)
    assert abs(results[0].score - 2 / 3) < 0.001


def test_partial_match_is_compatible_true() -> None:
    c = _cand(temp_min=25, temp_max=35)
    results = filter_companions([c], _env(temperature=23))
    assert results[0].is_compatible is True


# ---------------------------------------------------------------------------
# Zero match — all 3 dimensions fail
# ---------------------------------------------------------------------------


def test_no_match_score_is_0() -> None:
    c = _cand(light_min=5000, light_max=10000,   # current: 1000 lux — too low
              humi_min=80, humi_max=100,           # current: 55% — too low
              temp_min=30, temp_max=40)            # current: 23°C — too cold
    results = filter_companions([c], _env(light=1000, humidity=55, temperature=23))
    assert results[0].score == 0.0


def test_no_match_is_compatible_false() -> None:
    c = _cand(light_min=5000, light_max=10000,
              humi_min=80, humi_max=100,
              temp_min=30, temp_max=40)
    results = filter_companions([c], _env(light=1000, humidity=55, temperature=23))
    assert results[0].is_compatible is False


# ---------------------------------------------------------------------------
# Light dimension
# ---------------------------------------------------------------------------


def test_light_too_low_reason_mentions_부족() -> None:
    c = _cand(light_min=3000, light_max=6000, humi_min=None, humi_max=None,
              temp_min=None, temp_max=None)
    results = filter_companions([c], _env(light=500, humidity=None, temperature=None))
    assert any("부족" in r for r in results[0].reasons)


def test_light_too_high_reason_mentions_과다() -> None:
    c = _cand(light_min=100, light_max=300, humi_min=None, humi_max=None,
              temp_min=None, temp_max=None)
    results = filter_companions([c], _env(light=5000, humidity=None, temperature=None))
    assert any("과다" in r for r in results[0].reasons)


def test_light_at_lower_boundary_matches() -> None:
    c = _cand(light_min=1000, light_max=2000, humi_min=None, humi_max=None,
              temp_min=None, temp_max=None)
    results = filter_companions([c], _env(light=1000, humidity=None, temperature=None))
    assert results[0].score == 1.0


def test_light_at_upper_boundary_matches() -> None:
    c = _cand(light_min=1000, light_max=2000, humi_min=None, humi_max=None,
              temp_min=None, temp_max=None)
    results = filter_companions([c], _env(light=2000, humidity=None, temperature=None))
    assert results[0].score == 1.0


def test_light_reason_contains_lux_values() -> None:
    c = _cand(light_min=500, light_max=2000, humi_min=None, humi_max=None,
              temp_min=None, temp_max=None)
    results = filter_companions([c], _env(light=1000, humidity=None, temperature=None))
    reasons_text = " ".join(results[0].reasons)
    assert "lux" in reasons_text


# ---------------------------------------------------------------------------
# Humidity dimension
# ---------------------------------------------------------------------------


def test_humidity_too_low_reason_mentions_부족() -> None:
    c = _cand(light_min=None, light_max=None, humi_min=80, humi_max=100,
              temp_min=None, temp_max=None)
    results = filter_companions([c], _env(light=None, humidity=40, temperature=None))
    assert any("부족" in r for r in results[0].reasons)


def test_humidity_too_high_reason_mentions_과다() -> None:
    c = _cand(light_min=None, light_max=None, humi_min=20, humi_max=40,
              temp_min=None, temp_max=None)
    results = filter_companions([c], _env(light=None, humidity=80, temperature=None))
    assert any("과다" in r for r in results[0].reasons)


def test_humidity_match_reason_contains_percent() -> None:
    c = _cand(light_min=None, light_max=None, humi_min=40, humi_max=70,
              temp_min=None, temp_max=None)
    results = filter_companions([c], _env(light=None, humidity=55, temperature=None))
    reasons_text = " ".join(results[0].reasons)
    assert "%" in reasons_text


# ---------------------------------------------------------------------------
# Temperature dimension
# ---------------------------------------------------------------------------


def test_temperature_too_low_reason_mentions_부족() -> None:
    c = _cand(light_min=None, light_max=None, humi_min=None, humi_max=None,
              temp_min=25, temp_max=35)
    results = filter_companions([c], _env(light=None, humidity=None, temperature=15))
    assert any("부족" in r for r in results[0].reasons)


def test_temperature_too_high_reason_mentions_과다() -> None:
    c = _cand(light_min=None, light_max=None, humi_min=None, humi_max=None,
              temp_min=15, temp_max=20)
    results = filter_companions([c], _env(light=None, humidity=None, temperature=35))
    assert any("과다" in r for r in results[0].reasons)


def test_temperature_reason_contains_celsius_symbol() -> None:
    c = _cand(light_min=None, light_max=None, humi_min=None, humi_max=None,
              temp_min=18, temp_max=28)
    results = filter_companions([c], _env(light=None, humidity=None, temperature=23))
    reasons_text = " ".join(results[0].reasons)
    assert "°C" in reasons_text


# ---------------------------------------------------------------------------
# Missing environment / sensor data
# ---------------------------------------------------------------------------


def test_no_environment_score_neutral() -> None:
    results = filter_companions([_cand()], environment=None)
    assert results[0].score == 0.5


def test_no_environment_assessed_zero() -> None:
    results = filter_companions([_cand()], environment=None)
    assert results[0].assessed_dimensions == 0


def test_no_environment_is_compatible_false() -> None:
    results = filter_companions([_cand()], environment=None)
    assert results[0].is_compatible is False


def test_no_environment_reason_mentions_스냅샷() -> None:
    results = filter_companions([_cand()], environment=None)
    assert any("스냅샷" in r for r in results[0].reasons)


def test_missing_light_sensor_skipped() -> None:
    c = _cand(light_min=500, light_max=2000, humi_min=None, humi_max=None,
              temp_min=None, temp_max=None)
    env = _env(light=None, humidity=None, temperature=None)
    results = filter_companions([c], env)
    assert results[0].assessed_dimensions == 0
    assert results[0].score == 0.5


def test_candidate_no_thresholds_assessed_zero() -> None:
    c = _cand(light_min=None, light_max=None, humi_min=None, humi_max=None,
              temp_min=None, temp_max=None)
    results = filter_companions([c], _env())
    assert results[0].assessed_dimensions == 0
    assert results[0].score == 0.5


def test_partial_env_data_only_available_dims_assessed() -> None:
    # Only temperature sensor available; candidate has all thresholds
    c = _cand(light_min=500, light_max=2000, humi_min=40, humi_max=70,
              temp_min=18, temp_max=28)
    env = _env(light=None, humidity=None, temperature=23)  # only temp available
    results = filter_companions([c], env)
    assert results[0].assessed_dimensions == 1
    assert results[0].score == 1.0  # temp matches


# ---------------------------------------------------------------------------
# Self-exclusion
# ---------------------------------------------------------------------------


def test_current_species_excluded() -> None:
    own_id = uuid.uuid4()
    c = _cand(species_id=own_id)
    results = filter_companions([c], _env(), current_species_id=own_id)
    assert len(results) == 0


def test_other_species_not_excluded() -> None:
    own_id = uuid.uuid4()
    c = _cand(species_id=uuid.uuid4())  # different id
    results = filter_companions([c], _env(), current_species_id=own_id)
    assert len(results) == 1


def test_no_current_species_all_candidates_included() -> None:
    candidates = [_cand(name=f"식물{i}") for i in range(5)]
    results = filter_companions(candidates, _env())
    assert len(results) == 5


# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------


def test_sorted_by_score_descending() -> None:
    good = _cand(name="좋은 식물", light_min=500, light_max=2000,
                 humi_min=40, humi_max=70, temp_min=18, temp_max=28)
    bad = _cand(name="나쁜 식물", light_min=5000, light_max=10000,
                humi_min=80, humi_max=100, temp_min=30, temp_max=40)
    env = _env(light=1000, humidity=55, temperature=23)
    results = filter_companions([bad, good], env)
    assert results[0].candidate.common_name == "좋은 식물"
    assert results[1].candidate.common_name == "나쁜 식물"


def test_tie_broken_by_name_ascending() -> None:
    # Two candidates with identical conditions → identical score → sort by name
    c_z = _cand(name="Zzz 식물")
    c_a = _cand(name="Aaa 식물")
    results = filter_companions([c_z, c_a], _env())
    assert results[0].candidate.common_name == "Aaa 식물"
    assert results[1].candidate.common_name == "Zzz 식물"


def test_sorted_result_is_deterministic() -> None:
    candidates = [_cand(name=f"식물{c}") for c in "DCBA"]
    r1 = filter_companions(candidates, _env())
    r2 = filter_companions(candidates, _env())
    assert [r.candidate.common_name for r in r1] == [r.candidate.common_name for r in r2]


# ---------------------------------------------------------------------------
# top_k limit
# ---------------------------------------------------------------------------


def test_top_k_limits_results() -> None:
    candidates = [_cand(name=f"식물{i}") for i in range(20)]
    results = filter_companions(candidates, _env(), top_k=5)
    assert len(results) == 5


def test_top_k_default_is_10() -> None:
    candidates = [_cand(name=f"식물{i}") for i in range(15)]
    results = filter_companions(candidates, _env())
    assert len(results) == 10


def test_top_k_exceeding_candidates_returns_all() -> None:
    candidates = [_cand(name=f"식물{i}") for i in range(3)]
    results = filter_companions(candidates, _env(), top_k=10)
    assert len(results) == 3


def test_top_k_zero_returns_empty() -> None:
    results = filter_companions([_cand()], _env(), top_k=0)
    assert len(results) == 0


# ---------------------------------------------------------------------------
# Caution notes — safety flags
# ---------------------------------------------------------------------------


def test_toxic_plant_caution_note() -> None:
    c = _cand(is_toxic=True)
    results = filter_companions([c], _env())
    assert any("독성" in note for note in results[0].caution_notes)


def test_toxic_to_pets_caution_note() -> None:
    c = _cand(toxic_to_pets=True)
    results = filter_companions([c], _env())
    assert any("반려동물" in note for note in results[0].caution_notes)


def test_toxic_to_children_caution_note() -> None:
    c = _cand(toxic_to_children=True)
    results = filter_companions([c], _env())
    assert any("어린이" in note for note in results[0].caution_notes)


def test_all_safety_flags_generate_separate_notes() -> None:
    c = _cand(is_toxic=True, toxic_to_pets=True, toxic_to_children=True)
    results = filter_companions([c], _env())
    assert len(results[0].caution_notes) == 3


def test_no_safety_flags_empty_cautions() -> None:
    c = _cand(is_toxic=False, toxic_to_pets=False, toxic_to_children=False)
    results = filter_companions([c], _env())
    assert results[0].caution_notes == ()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_candidates_returns_empty() -> None:
    assert filter_companions([], _env()) == []


def test_single_candidate_always_returned() -> None:
    results = filter_companions([_cand()], _env())
    assert len(results) == 1


def test_result_candidate_matches_input() -> None:
    c = _cand(name="산세베리아")
    results = filter_companions([c], _env())
    assert results[0].candidate is c


def test_score_rounded_to_4_decimal_places() -> None:
    # 2/3 ≈ 0.6667
    c = _cand(temp_min=25, temp_max=35)  # temp fails
    results = filter_companions([c], _env(temperature=23))
    # score should be rounded
    assert results[0].score == round(results[0].score, 4)


def test_reasons_is_tuple() -> None:
    results = filter_companions([_cand()], _env())
    assert isinstance(results[0].reasons, tuple)


def test_caution_notes_is_tuple() -> None:
    results = filter_companions([_cand()], _env())
    assert isinstance(results[0].caution_notes, tuple)
