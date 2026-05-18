"""TICKET-063 — FastPathAnswerService unit tests.

Pure text-generation helpers are tested directly (no DB mock needed).
Async answer() dispatch is tested with mock repos.
No LLM client is invoked in any test.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.question_router import QuestionRouteDecision
from app.rules.schemas import RuleEngineResult
from app.schemas.chat_answer import ParsedAnswer
from app.services.fast_path_answer_service import (
    FastPathAnswerService,
    _no_sensor_data,
    _needs_more_data,
    care_logs_to_answer,
    rule_result_to_answer,
    sensor_reading_to_answer,
    snapshot_to_answer,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC)


def _decision(route: str) -> QuestionRouteDecision:
    return QuestionRouteDecision.make(route=route, confidence=0.9, reason_codes=["test"])  # type: ignore[arg-type]


def _rule_result(
    care_status: str = "good",
    primary_action: str = "none",
    reason_codes: list[str] | None = None,
) -> RuleEngineResult:
    return RuleEngineResult(
        plant_id=uuid.uuid4(),
        evaluated_at=_NOW,
        care_status=care_status,  # type: ignore[arg-type]
        primary_action=primary_action,  # type: ignore[arg-type]
        severity="none",  # type: ignore[arg-type]
        reason_codes=reason_codes or [],
        evidence_facts={},
        rule_results=[],
    )


def _snapshot(
    soil: float | None = 42.0,
    temp: float | None = 22.5,
    hum: float | None = 60.0,
    lux: float | None = 1500.0,
    window: str = "latest",
) -> MagicMock:
    s = MagicMock()
    s.soil_moisture_avg_pct = Decimal(str(soil)) if soil is not None else None
    s.temperature_avg_c = Decimal(str(temp)) if temp is not None else None
    s.humidity_avg_pct = Decimal(str(hum)) if hum is not None else None
    s.light_avg_lux = Decimal(str(lux)) if lux is not None else None
    s.window = window
    return s


def _reading(
    soil: float | None = 38.0,
    temp: float | None = 21.0,
    hum: float | None = 55.0,
    lux: float | None = 800.0,
) -> MagicMock:
    r = MagicMock()
    r.soil_moisture_pct = Decimal(str(soil)) if soil is not None else None
    r.temperature_c = Decimal(str(temp)) if temp is not None else None
    r.humidity_pct = Decimal(str(hum)) if hum is not None else None
    r.light_lux = Decimal(str(lux)) if lux is not None else None
    r.measured_at = _NOW
    return r


def _care_log(action_type: str = "water", hours_ago: float = 24.0) -> MagicMock:
    log = MagicMock()
    log.action_type = action_type
    log.acted_at = _NOW - timedelta(hours=hours_ago)
    return log


# ---------------------------------------------------------------------------
# rule_result_to_answer — pure helper
# ---------------------------------------------------------------------------


def test_rule_good_status() -> None:
    a = rule_result_to_answer(_rule_result("good", "none"))
    assert isinstance(a, ParsedAnswer)
    assert "양호" in a.결론


def test_rule_needs_action_water() -> None:
    a = rule_result_to_answer(_rule_result("needs_action", "water"))
    assert "물" in a.결론
    assert "물" in a.행동
    assert "과습" in a.주의


def test_rule_needs_action_light() -> None:
    a = rule_result_to_answer(_rule_result("needs_action", "increase_light"))
    assert "빛" in a.결론


def test_rule_needs_action_humidity() -> None:
    a = rule_result_to_answer(_rule_result("needs_action", "stabilize_humidity"))
    assert "습도" in a.결론


def test_rule_watch_status() -> None:
    a = rule_result_to_answer(_rule_result("watch", "watch"))
    assert "주의" in a.결론


def test_rule_insufficient_data() -> None:
    a = rule_result_to_answer(_rule_result("insufficient_data", "none"))
    assert "데이터" in a.결론


def test_rule_reason_codes_in_근거() -> None:
    a = rule_result_to_answer(_rule_result("needs_action", "water", ["low_soil_moisture"]))
    assert "low_soil_moisture" in a.근거


# ---------------------------------------------------------------------------
# snapshot_to_answer — pure helper
# ---------------------------------------------------------------------------


def test_snapshot_includes_soil_moisture() -> None:
    a = snapshot_to_answer(_snapshot(soil=42.0))
    assert "42.0%" in a.결론


def test_snapshot_includes_temperature() -> None:
    a = snapshot_to_answer(_snapshot(temp=22.5))
    assert "22.5°C" in a.결론


def test_snapshot_includes_humidity() -> None:
    a = snapshot_to_answer(_snapshot(hum=60.0))
    assert "60.0%" in a.결론


def test_snapshot_includes_window_in_근거() -> None:
    a = snapshot_to_answer(_snapshot(window="24h"))
    assert "24h" in a.근거


def test_snapshot_all_none_returns_no_data() -> None:
    a = snapshot_to_answer(_snapshot(soil=None, temp=None, hum=None, lux=None))
    assert "없어요" in a.결론 or "데이터" in a.결론


# ---------------------------------------------------------------------------
# sensor_reading_to_answer — pure helper
# ---------------------------------------------------------------------------


def test_reading_includes_soil_moisture() -> None:
    a = sensor_reading_to_answer(_reading(soil=38.0))
    assert "38.0%" in a.결론


def test_reading_all_none_returns_no_data() -> None:
    a = sensor_reading_to_answer(_reading(soil=None, temp=None, hum=None, lux=None))
    assert "없어요" in a.결론 or "데이터" in a.결론


# ---------------------------------------------------------------------------
# care_logs_to_answer — pure helper
# ---------------------------------------------------------------------------


def test_care_log_shows_last_water_hours() -> None:
    logs = [_care_log("water", hours_ago=5.0)]
    a = care_logs_to_answer(logs, _NOW)
    assert "5시간 전" in a.결론


def test_care_log_shows_last_water_days() -> None:
    logs = [_care_log("water", hours_ago=49.0)]
    a = care_logs_to_answer(logs, _NOW)
    assert "2일 전" in a.결론


def test_care_log_no_water_entry() -> None:
    logs = [_care_log("fertilise", hours_ago=10.0)]
    a = care_logs_to_answer(logs, _NOW)
    assert "물주기" in a.결론


def test_care_log_empty_list() -> None:
    a = care_logs_to_answer([], _NOW)
    assert "없어요" in a.결론


def test_care_log_action_types_in_주의() -> None:
    logs = [_care_log("water"), _care_log("fertilise")]
    a = care_logs_to_answer(logs, _NOW)
    assert "water" in a.주의


# ---------------------------------------------------------------------------
# _no_sensor_data / _needs_more_data helpers
# ---------------------------------------------------------------------------


def test_no_sensor_data_returns_parsed_answer() -> None:
    a = _no_sensor_data()
    assert isinstance(a, ParsedAnswer)
    assert "없어요" in a.결론


def test_needs_more_data_returns_parsed_answer() -> None:
    a = _needs_more_data()
    assert isinstance(a, ParsedAnswer)
    assert "데이터" in a.결론 or "어려워요" in a.결론


# ---------------------------------------------------------------------------
# FastPathAnswerService.answer() — dispatch routing
# ---------------------------------------------------------------------------


def _make_service_with_mocks(
    snapshot_latest=None,
    snapshot_24h=None,
    raw_reading=None,
    care_logs=None,
    plant=None,
    rule_result=None,
) -> tuple[FastPathAnswerService, MagicMock]:
    session = MagicMock()
    session.get = AsyncMock(return_value=plant)

    svc = FastPathAnswerService(session)

    svc._env_repo = MagicMock()
    svc._env_repo.get_snapshot_by_window = AsyncMock(
        side_effect=lambda pid, w: snapshot_latest if w == "latest" else snapshot_24h
    )
    svc._env_repo.get_latest_sensor_reading = AsyncMock(return_value=raw_reading)

    svc._rule_repo = MagicMock()
    svc._rule_repo.get_thresholds = AsyncMock(return_value=None)
    svc._rule_repo.get_latest_snapshot = AsyncMock(return_value=None)
    svc._rule_repo.get_recent_care_logs = AsyncMock(return_value=[])

    svc._care_repo = MagicMock()
    svc._care_repo.list_for_plant = AsyncMock(return_value=care_logs or [])

    if rule_result is not None:
        svc._engine = MagicMock()
        svc._engine.evaluate = MagicMock(return_value=rule_result)

    return svc, session


def _run(coro) -> ParsedAnswer:
    return asyncio.run(coro)


PLANT_ID = uuid.uuid4()
USER_ID = uuid.uuid4()


# sql_sensor: snapshot present
def test_dispatch_sql_sensor_with_snapshot() -> None:
    svc, _ = _make_service_with_mocks(snapshot_latest=_snapshot())
    a = _run(svc.answer(PLANT_ID, USER_ID, "현재 습도?", _decision("sql_sensor"), now=_NOW))
    assert isinstance(a, ParsedAnswer)
    assert "42.0%" in a.결론  # soil moisture from _snapshot()


# sql_sensor: no snapshot, use raw reading
def test_dispatch_sql_sensor_falls_back_to_reading() -> None:
    svc, _ = _make_service_with_mocks(raw_reading=_reading(soil=38.0))
    a = _run(svc.answer(PLANT_ID, USER_ID, "현재 토양 수분?", _decision("sql_sensor"), now=_NOW))
    assert "38.0%" in a.결론


# sql_sensor: no data at all
def test_dispatch_sql_sensor_no_data() -> None:
    svc, _ = _make_service_with_mocks()
    a = _run(svc.answer(PLANT_ID, USER_ID, "현재 센서?", _decision("sql_sensor"), now=_NOW))
    assert "없어요" in a.결론


# sql_care_log: recent water log
def test_dispatch_sql_care_log_with_logs() -> None:
    logs = [_care_log("water", hours_ago=6.0)]
    svc, _ = _make_service_with_mocks(care_logs=logs)
    a = _run(svc.answer(PLANT_ID, USER_ID, "마지막 물은?", _decision("sql_care_log"), now=_NOW))
    assert "6시간 전" in a.결론


# sql_care_log: empty
def test_dispatch_sql_care_log_empty() -> None:
    svc, _ = _make_service_with_mocks(care_logs=[])
    a = _run(svc.answer(PLANT_ID, USER_ID, "관리 기록?", _decision("sql_care_log"), now=_NOW))
    assert "없어요" in a.결론


# rule_only: plant not found → needs_more_data
def test_dispatch_rule_only_no_plant() -> None:
    svc, _ = _make_service_with_mocks(plant=None)
    a = _run(svc.answer(PLANT_ID, USER_ID, "물 줘야?", _decision("rule_only"), now=_NOW))
    assert isinstance(a, ParsedAnswer)
    assert "데이터" in a.결론 or "어려워요" in a.결론


# rule_only: good result
def test_dispatch_rule_only_good() -> None:
    fake_plant = MagicMock()
    fake_plant.species_profile_id = None
    rr = _rule_result("good", "none")
    svc, _ = _make_service_with_mocks(plant=fake_plant, rule_result=rr)
    a = _run(svc.answer(PLANT_ID, USER_ID, "상태 어때?", _decision("rule_only"), now=_NOW))
    assert "양호" in a.결론


# rule_only: needs water
def test_dispatch_rule_only_needs_water() -> None:
    fake_plant = MagicMock()
    fake_plant.species_profile_id = None
    rr = _rule_result("needs_action", "water")
    svc, _ = _make_service_with_mocks(plant=fake_plant, rule_result=rr)
    a = _run(svc.answer(PLANT_ID, USER_ID, "물 줘야?", _decision("rule_only"), now=_NOW))
    assert "물" in a.결론


# unknown route → needs_more_data
def test_dispatch_unknown_route() -> None:
    svc, _ = _make_service_with_mocks()
    a = _run(svc.answer(PLANT_ID, USER_ID, "???", _decision("unknown"), now=_NOW))
    assert isinstance(a, ParsedAnswer)


# ---------------------------------------------------------------------------
# No LLM client invoked (structural guard)
# ---------------------------------------------------------------------------


def test_service_does_not_import_llm() -> None:
    from pathlib import Path
    src = Path("app/services/fast_path_answer_service.py").read_text(encoding="utf-8")
    for forbidden in ("openai", "anthropic", "httpx", "QwenLLM"):
        assert forbidden not in src, f"LLM reference found: {forbidden!r}"
