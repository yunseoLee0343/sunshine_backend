"""EnvironmentDetailService — TICKET-010.

Assembles EnvironmentDetailResponse by reading pre-computed snapshots from
environment_snapshots and the latest character row.

Rules:
  - No aggregation of raw sensor_readings (use stored snapshots only).
  - No Rule Engine invocation.
  - No DB writes.
  - Character explanation is a hardcoded template keyed on reason_code.
"""

from __future__ import annotations

import uuid
from datetime import UTC

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.environment_snapshot import EnvironmentSnapshot
from app.models.sensor_reading import SensorReading
from app.repositories.environment_detail_repository import EnvironmentDetailRepository
from app.schemas.environment_detail import (
    CharacterExplanation,
    EnvironmentDetailResponse,
    MetricStats,
    WindowSnapshot,
)

# ---------------------------------------------------------------------------
# Hardcoded explanation templates (no LLM)
# ---------------------------------------------------------------------------

_EXPLANATIONS: dict[str, str] = {
    "good": "식물이 건강한 환경에 있어요. 센서 데이터가 안정적으로 유지되고 있습니다.",
    "low_soil_moisture": ("현재 캐릭터 상태는 최근 환경 요약의 토양 수분 부족과 연결됩니다."),
    "low_light": ("현재 캐릭터 상태는 최근 환경 요약의 빛 부족과 연결됩니다."),
    "unstable_humidity": ("현재 캐릭터 상태는 최근 환경 요약의 습도 또는 온도 불안정과 연결됩니다."),
    "after_watering": ("최근 물 주기 이후 식물이 회복 중이에요. 토양 수분이 안정될 때까지 지켜봐 주세요."),
    "onboarding_created": ("식물이 새로 등록되었어요. 센서 데이터가 쌓이면 더 자세한 환경 분석을 제공할 수 있어요."),
}

_FALLBACK_EXPLANATION = "환경 데이터를 분석 중이에요."


def _raw_to_window_snapshot(row: SensorReading) -> WindowSnapshot:
    """Build a synthetic 'latest' WindowSnapshot from a single raw reading."""

    def _f(v: object) -> float | None:
        return float(v) if v is not None else None

    ts = row.measured_at
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)

    def _stat(v: object) -> MetricStats:
        fv = _f(v)
        return MetricStats(avg=fv, min=fv, max=fv)

    return WindowSnapshot(
        window="latest",
        window_start=ts,
        window_end=ts,
        temperature_c=_stat(row.temperature_c),
        humidity_pct=_stat(row.humidity_pct),
        light_lux=_stat(row.light_lux),
        soil_moisture_pct=_stat(row.soil_moisture_pct),
        source="raw_sensor_reading_fallback",
        sample_count=1,
    )


def _to_window_snapshot(row: EnvironmentSnapshot) -> WindowSnapshot:
    def _f(v: object) -> float | None:
        return float(v) if v is not None else None

    return WindowSnapshot(
        window=row.window,
        window_start=row.window_start,
        window_end=row.window_end,
        temperature_c=MetricStats(
            avg=_f(row.temperature_avg_c),
            min=_f(row.temperature_min_c),
            max=_f(row.temperature_max_c),
        ),
        humidity_pct=MetricStats(
            avg=_f(row.humidity_avg_pct),
            min=_f(row.humidity_min_pct),
            max=_f(row.humidity_max_pct),
        ),
        light_lux=MetricStats(
            avg=_f(row.light_avg_lux),
            min=_f(row.light_min_lux),
            max=_f(row.light_max_lux),
        ),
        soil_moisture_pct=MetricStats(
            avg=_f(row.soil_moisture_avg_pct),
            min=_f(row.soil_moisture_min_pct),
            max=_f(row.soil_moisture_max_pct),
        ),
        source="snapshot",
    )


class EnvironmentDetailService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = EnvironmentDetailRepository(session)

    async def get_detail(self, plant_id: uuid.UUID, user_id: uuid.UUID) -> EnvironmentDetailResponse | None:
        """Return None when the plant doesn't exist or belongs to another user."""
        plant = await self._repo.get_plant_for_user(plant_id, user_id)
        if plant is None:
            return None

        # Fetch the three pre-computed window snapshots (read-only)
        latest_row, row_24h, row_7d = (
            await self._repo.get_snapshot_by_window(plant_id, "latest"),
            await self._repo.get_snapshot_by_window(plant_id, "24h"),
            await self._repo.get_snapshot_by_window(plant_id, "7d"),
        )

        # Always fetch latest raw reading to detect stale snapshot.
        raw = await self._repo.get_latest_sensor_reading(plant_id)

        latest_ws: WindowSnapshot | None = None
        if latest_row is not None:
            snap_end = latest_row.window_end
            if snap_end.tzinfo is None:
                snap_end = snap_end.replace(tzinfo=UTC)
            raw_ts = raw.measured_at if raw is not None else None
            if raw_ts is not None and raw_ts.tzinfo is None:
                raw_ts = raw_ts.replace(tzinfo=UTC)
            # If the latest raw reading is newer than the snapshot, use it.
            if raw is not None and raw_ts > snap_end:
                latest_ws = _raw_to_window_snapshot(raw)
            else:
                latest_ws = _to_window_snapshot(latest_row)
        elif raw is not None:
            latest_ws = _raw_to_window_snapshot(raw)

        # Character explanation from hardcoded templates
        char_row = await self._repo.get_latest_character(plant_id)
        character_explanation: CharacterExplanation | None = None
        if char_row is not None:
            reason_code = char_row.reason_code
            character_explanation = CharacterExplanation(
                reason_code=reason_code,
                explanation=_EXPLANATIONS.get(reason_code, _FALLBACK_EXPLANATION),
            )

        return EnvironmentDetailResponse(
            plant_id=plant.id,
            nickname=plant.nickname,
            room_name=plant.room_name,
            latest=latest_ws,
            summary_24h=_to_window_snapshot(row_24h) if row_24h else None,
            summary_7d=_to_window_snapshot(row_7d) if row_7d else None,
            character_explanation=character_explanation,
        )
