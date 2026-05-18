"""FastPathAnswerService — TICKET-063.

Answers sensor/rule/care-log questions without a second LLM call.
Routes based on QuestionRouteDecision.route:
  rule_only    → RuleEngine evaluation → templated ParsedAnswer
  sql_sensor   → latest EnvironmentSnapshot (or raw SensorReading) → templated ParsedAnswer
  sql_care_log → recent CareLog list → templated ParsedAnswer

No LLM, no hallucination of missing values.
Pure text-generation helpers are module-level functions for easy unit testing.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.question_router import QuestionRouteDecision
from app.models.care_log import CareLog
from app.models.environment_snapshot import EnvironmentSnapshot
from app.models.plant import Plant
from app.models.sensor_reading import SensorReading
from app.repositories.care_log_repository import CareLogRepository
from app.repositories.environment_detail_repository import EnvironmentDetailRepository
from app.repositories.rule_input_repository import RuleInputRepository
from app.rules.schemas import RuleEngineResult
from app.rules.types import LatestSnapshot, SpeciesThresholds
from app.schemas.chat_answer import ParsedAnswer
from app.services.rule_engine import RuleEngine

# ---------------------------------------------------------------------------
# Pure text-generation helpers (no I/O — easy to unit test)
# ---------------------------------------------------------------------------

_ACTION_TEXT: dict[str, str] = {
    "water": "지금 바로 물을 충분히 주세요. 화분 아래로 물이 흘러나올 때까지 주는 것이 좋아요.",
    "increase_light": "더 밝은 곳으로 이동하거나 커튼을 열어 빛을 늘려 주세요.",
    "stabilize_humidity": "주변 습도를 안정적으로 유지해 주세요. 가습기나 물 트레이를 활용할 수 있어요.",
    "adjust_temperature": "적정 온도 범위로 식물을 이동해 주세요.",
    "watch": "당분간 상태를 주의 깊게 관찰해 주세요.",
    "none": "현재 관리 방식을 그대로 유지해 주세요.",
}

_CAUTION_TEXT: dict[str, str] = {
    "water": "과습을 피하기 위해 화분 받침에 물이 고이지 않도록 해주세요.",
    "increase_light": "직사광선은 잎 화상의 원인이 될 수 있으니 주의하세요.",
    "stabilize_humidity": "급격한 온도·습도 변화는 식물에 스트레스를 줄 수 있어요.",
    "adjust_temperature": "에어컨·난방 바람이 직접 닿지 않는 곳에 두세요.",
    "watch": "이상 징후가 심해지면 전문가의 도움을 구하세요.",
    "none": "환경 변화에 주의해 주세요.",
}


def _fmt(val: Decimal | float | None, unit: str, digits: int = 1) -> str | None:
    if val is None:
        return None
    return f"{float(val):.{digits}f}{unit}"


def rule_result_to_answer(result: RuleEngineResult) -> ParsedAnswer:
    """Map a RuleEngineResult to a ParsedAnswer without LLM."""
    status = result.care_status
    action = result.primary_action

    if status == "good":
        결론 = "현재 환경이 양호해요. 물을 줄 필요가 없어요."
        근거 = "환경 데이터와 관수 이력을 종합한 결과, 현재 상태가 적절합니다."
    elif status == "needs_action":
        action_map = {
            "water": "지금 물을 줘야 할 것 같아요.",
            "increase_light": "빛이 부족한 상태예요.",
            "stabilize_humidity": "습도가 불안정한 상태예요.",
            "adjust_temperature": "온도가 적정 범위를 벗어났어요.",
        }
        결론 = action_map.get(action, "조치가 필요한 상태예요.")
        reason_str = ", ".join(result.reason_codes) if result.reason_codes else "측정값이 기준치를 벗어남"
        근거 = f"규칙 엔진 평가 결과 '{action}' 조치가 필요합니다. 근거 코드: {reason_str}."
    elif status == "watch":
        결론 = "지금 당장은 괜찮지만 주의가 필요한 상태예요."
        근거 = f"환경이 경계 수준에 있습니다. 근거 코드: {', '.join(result.reason_codes) or 'watch'}."
    else:  # insufficient_data
        결론 = "데이터가 부족해서 정확한 판단이 어려워요."
        근거 = "센서 측정값이나 관리 기록이 충분하지 않아요. 직접 토양 상태를 확인해 주세요."

    return ParsedAnswer(
        결론=결론,
        근거=근거,
        행동=_ACTION_TEXT.get(action, _ACTION_TEXT["none"]),
        주의=_CAUTION_TEXT.get(action, _CAUTION_TEXT["none"]),
    )


def snapshot_to_answer(snapshot: EnvironmentSnapshot) -> ParsedAnswer:
    """Format sensor snapshot values into a ParsedAnswer."""
    parts: list[str] = []
    soil = _fmt(snapshot.soil_moisture_avg_pct, "%")
    temp = _fmt(snapshot.temperature_avg_c, "°C")
    hum = _fmt(snapshot.humidity_avg_pct, "%")
    lux = _fmt(snapshot.light_avg_lux, " lux", digits=0)

    if soil is not None:
        parts.append(f"토양 수분 {soil}")
    if temp is not None:
        parts.append(f"온도 {temp}")
    if hum is not None:
        parts.append(f"습도 {hum}")
    if lux is not None:
        parts.append(f"조도 {lux}")

    if not parts:
        return _no_sensor_data()

    values_str = ", ".join(parts)
    결론 = f"현재 측정값: {values_str}입니다."
    근거 = f"최근 환경 스냅샷(window: {snapshot.window})에서 집계된 평균값입니다."
    행동 = "측정값이 적정 범위 안에 있다면 현재 관리를 유지하고, 벗어났다면 조치를 취해 주세요."
    주의 = "센서 값은 실제 환경과 다소 차이가 있을 수 있어요."

    return ParsedAnswer(결론=결론, 근거=근거, 행동=행동, 주의=주의)


def sensor_reading_to_answer(reading: SensorReading) -> ParsedAnswer:
    """Format a raw SensorReading into a ParsedAnswer."""
    parts: list[str] = []
    soil = _fmt(reading.soil_moisture_pct, "%")
    temp = _fmt(reading.temperature_c, "°C")
    hum = _fmt(reading.humidity_pct, "%")
    lux = _fmt(reading.light_lux, " lux", digits=0)

    if soil is not None:
        parts.append(f"토양 수분 {soil}")
    if temp is not None:
        parts.append(f"온도 {temp}")
    if hum is not None:
        parts.append(f"습도 {hum}")
    if lux is not None:
        parts.append(f"조도 {lux}")

    if not parts:
        return _no_sensor_data()

    values_str = ", ".join(parts)
    결론 = f"가장 최근 측정값: {values_str}입니다."
    근거 = f"센서 직접 측정값 기준 ({reading.measured_at.strftime('%Y-%m-%d %H:%M')})입니다."
    행동 = "값이 적정 범위 밖이라면 환경을 조정해 주세요."
    주의 = "순간 측정값이므로 평균값과 다를 수 있어요."

    return ParsedAnswer(결론=결론, 근거=근거, 행동=행동, 주의=주의)


def care_logs_to_answer(logs: list[CareLog], now: datetime) -> ParsedAnswer:
    """Summarise recent care logs into a ParsedAnswer."""
    if not logs:
        return ParsedAnswer(
            결론="최근 관리 기록이 없어요.",
            근거="등록된 관리 기록(물주기, 메모 등)을 찾지 못했어요.",
            행동="식물 상태를 직접 확인하고 필요하다면 물을 주세요.",
            주의="관리 기록을 남기면 더 정확한 안내가 가능해요.",
        )

    last_water = next((l for l in logs if l.action_type == "water"), None)
    if last_water is not None:
        delta = now - last_water.acted_at
        total_hours = delta.total_seconds() / 3600
        if total_hours < 24:
            when = f"약 {int(total_hours)}시간 전"
        else:
            days = int(total_hours // 24)
            when = f"약 {days}일 전"
        결론 = f"마지막으로 물을 준 것은 {when}이에요."
        근거 = f"관리 기록 기준: {last_water.acted_at.strftime('%Y-%m-%d %H:%M')}에 물을 줬어요."
    else:
        결론 = "최근 물주기 기록이 없어요."
        근거 = f"최근 {len(logs)}건의 관리 기록에서 물주기를 찾지 못했어요."

    recent_types = list(dict.fromkeys(l.action_type for l in logs[:5]))
    types_str = ", ".join(recent_types)
    행동 = "물주기 주기에 맞게 다음 관수를 계획하세요."
    주의 = f"최근 관리 이력: {types_str}. 계절과 날씨에 따라 주기가 달라질 수 있어요."

    return ParsedAnswer(결론=결론, 근거=근거, 행동=행동, 주의=주의)


def _no_sensor_data() -> ParsedAnswer:
    return ParsedAnswer(
        결론="현재 센서 데이터가 없어요.",
        근거="연결된 센서가 없거나 아직 측정값이 수집되지 않았어요.",
        행동="직접 토양 상태를 손으로 확인해 주세요.",
        주의="센서가 연결되면 더 정확한 안내를 드릴 수 있어요.",
    )


def _needs_more_data() -> ParsedAnswer:
    return ParsedAnswer(
        결론="충분한 데이터가 없어서 답변을 드리기 어려워요.",
        근거="필요한 데이터(센서값, 관리 기록 등)를 찾지 못했어요.",
        행동="직접 식물 상태를 확인해 주세요.",
        주의="-",
    )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class FastPathAnswerService:
    """Answers SQL/rule-routable questions without an LLM call.

    Instantiate once per request with the active AsyncSession.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._env_repo = EnvironmentDetailRepository(session)
        self._rule_repo = RuleInputRepository(session)
        self._care_repo = CareLogRepository(session)
        self._engine = RuleEngine()

    async def answer(
        self,
        plant_id: uuid.UUID,
        user_id: uuid.UUID,
        question: str,
        decision: QuestionRouteDecision,
        *,
        now: datetime | None = None,
    ) -> ParsedAnswer:
        """Return a ParsedAnswer for the given route without calling an LLM."""
        _now = now or datetime.now(UTC)

        if decision.route == "rule_only":
            return await self._answer_rule_only(plant_id, _now)
        if decision.route == "sql_sensor":
            return await self._answer_sql_sensor(plant_id)
        if decision.route == "sql_care_log":
            return await self._answer_sql_care_log(plant_id, _now)

        return _needs_more_data()

    # ------------------------------------------------------------------
    # Private handlers
    # ------------------------------------------------------------------

    async def _answer_rule_only(self, plant_id: uuid.UUID, now: datetime) -> ParsedAnswer:
        plant: Plant | None = await self._session.get(Plant, plant_id)
        if plant is None:
            return _needs_more_data()

        thresholds = (
            await self._rule_repo.get_thresholds(plant.species_profile_id)
            if plant.species_profile_id else None
        ) or SpeciesThresholds()

        snapshot = await self._rule_repo.get_latest_snapshot(plant_id, before=now) or LatestSnapshot()
        since = now - timedelta(days=7)
        care_logs = await self._rule_repo.get_recent_care_logs(plant_id, since=since, now=now)

        result = self._engine.evaluate(
            plant_id=plant_id,
            thresholds=thresholds,
            snapshot=snapshot,
            care_logs=care_logs,
            now=now,
        )
        return rule_result_to_answer(result)

    async def _answer_sql_sensor(self, plant_id: uuid.UUID) -> ParsedAnswer:
        snapshot = await self._env_repo.get_snapshot_by_window(plant_id, "latest")
        if snapshot is not None:
            return snapshot_to_answer(snapshot)

        # Try "24h" window as secondary
        snapshot = await self._env_repo.get_snapshot_by_window(plant_id, "24h")
        if snapshot is not None:
            return snapshot_to_answer(snapshot)

        # Fall back to raw sensor reading
        reading = await self._env_repo.get_latest_sensor_reading(plant_id)
        if reading is not None:
            return sensor_reading_to_answer(reading)

        return _no_sensor_data()

    async def _answer_sql_care_log(self, plant_id: uuid.UUID, now: datetime) -> ParsedAnswer:
        logs = await self._care_repo.list_for_plant(plant_id, limit=20)
        return care_logs_to_answer(logs, now)
