"""MVP Demo Scenario Checker — TICKET-023.

Validates that the 12-step MVP demo scenario can run end-to-end.
All checks are DB reads + in-process logic; no HTTP calls, no browser.

12 scenario steps:
  1.  데모 사용자 존재
  2.  식물 "초록이" 존재 및 소유권 확인
  3.  몬스테라 종 프로필 + 임계값 설정
  4.  포토스 동반 식물 프로필 존재
  5.  필로덴드론 동반 식물 프로필 존재
  6.  센서 기록 충분 (≥ 24건)
  7.  최신 환경 스냅샷 존재 (1h window)
  8.  토양 수분 < 임계값 → 물주기 규칙 트리거 조건 충족
  9.  최근 관리 기록 존재 (≥ 1건)
  10. 식물 캐릭터 상태 존재 (primary_action = water)
  11. 지식 베이스 청크 문서 존재 (≥ 3건)
  12. 의도 분류기 정상 동작 (3개 샘플 질문)

Usage:
    python -m app.seeds.demo_scenario
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict, dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.seeds.demo_seed import (
    DEMO_KNOWLEDGE_ID,
    DEMO_MONSTERA_SPECIES_ID,
    DEMO_PHILODENDRON_SPECIES_ID,
    DEMO_PLANT_ID,
    DEMO_POTHOS_SPECIES_ID,
    DEMO_USER_ID,
)


# ---------------------------------------------------------------------------
# Step result
# ---------------------------------------------------------------------------


@dataclass
class ScenarioStep:
    step: int
    description: str
    passed: bool
    detail: str


# ---------------------------------------------------------------------------
# 12 check functions
# ---------------------------------------------------------------------------


async def _step1_user_exists(session: AsyncSession) -> ScenarioStep:
    from app.models.user import User

    user = await session.get(User, DEMO_USER_ID)
    passed = user is not None
    return ScenarioStep(
        step=1,
        description="데모 사용자 존재",
        passed=passed,
        detail=f"user_id={DEMO_USER_ID}" if passed else "데모 사용자를 찾을 수 없음. demo_seed 실행 필요.",
    )


async def _step2_plant_exists(session: AsyncSession) -> ScenarioStep:
    from app.models.plant import Plant

    plant = await session.get(Plant, DEMO_PLANT_ID)
    passed = plant is not None and plant.user_id == DEMO_USER_ID
    detail = (
        f"nickname={plant.nickname}, room={plant.room_name}"
        if passed and plant is not None
        else "초록이 식물 없음 또는 소유권 불일치."
    )
    return ScenarioStep(step=2, description='식물 "초록이" 존재 및 소유권 확인', passed=passed, detail=detail)


async def _step3_species_thresholds(session: AsyncSession) -> ScenarioStep:
    from app.models.species_profile import SpeciesProfile

    sp = await session.get(SpeciesProfile, DEMO_MONSTERA_SPECIES_ID)
    passed = (
        sp is not None
        and sp.water_min_pct is not None
        and sp.light_min_lux is not None
        and sp.humidity_min_pct is not None
        and sp.temperature_min_c is not None
    )
    detail = (
        f"water {sp.water_min_pct}–{sp.water_max_pct}%, "
        f"light {sp.light_min_lux}–{sp.light_max_lux} lux"
        if passed and sp is not None
        else "몬스테라 종 프로필 없음 또는 임계값 미설정."
    )
    return ScenarioStep(step=3, description="몬스테라 종 프로필 + 임계값 설정", passed=passed, detail=detail)


async def _step4_pothos_profile(session: AsyncSession) -> ScenarioStep:
    from app.models.species_profile import SpeciesProfile

    sp = await session.get(SpeciesProfile, DEMO_POTHOS_SPECIES_ID)
    passed = sp is not None
    return ScenarioStep(
        step=4,
        description="포토스 동반 식물 프로필 존재",
        passed=passed,
        detail=f"species={sp.korean_name}" if passed else "포토스 프로필 없음.",
    )


async def _step5_philodendron_profile(session: AsyncSession) -> ScenarioStep:
    from app.models.species_profile import SpeciesProfile

    sp = await session.get(SpeciesProfile, DEMO_PHILODENDRON_SPECIES_ID)
    passed = sp is not None
    return ScenarioStep(
        step=5,
        description="필로덴드론 동반 식물 프로필 존재",
        passed=passed,
        detail=f"species={sp.korean_name}" if passed else "필로덴드론 프로필 없음.",
    )


async def _step6_sensor_readings(session: AsyncSession) -> ScenarioStep:
    from app.models.sensor_reading import SensorReading

    count_row = await session.execute(
        select(func.count()).select_from(SensorReading).where(
            SensorReading.plant_id == DEMO_PLANT_ID
        )
    )
    count = count_row.scalar_one()
    passed = count >= 24
    return ScenarioStep(
        step=6,
        description="센서 기록 충분 (≥ 24건)",
        passed=passed,
        detail=f"count={count}",
    )


async def _step7_snapshot_exists(session: AsyncSession) -> ScenarioStep:
    from app.models.environment_snapshot import EnvironmentSnapshot

    result = await session.execute(
        select(EnvironmentSnapshot)
        .where(
            EnvironmentSnapshot.plant_id == DEMO_PLANT_ID,
            EnvironmentSnapshot.window == "1h",
        )
        .limit(1)
    )
    snap = result.scalar_one_or_none()
    passed = snap is not None
    detail = (
        f"window=1h, soil_moisture={snap.soil_moisture_avg_pct}%"
        if passed and snap is not None
        else "1h 스냅샷 없음."
    )
    return ScenarioStep(step=7, description="최신 환경 스냅샷 존재 (1h window)", passed=passed, detail=detail)


async def _step8_watering_trigger(session: AsyncSession) -> ScenarioStep:
    from app.models.environment_snapshot import EnvironmentSnapshot
    from app.models.species_profile import SpeciesProfile

    sp = await session.get(SpeciesProfile, DEMO_MONSTERA_SPECIES_ID)
    snap_result = await session.execute(
        select(EnvironmentSnapshot)
        .where(
            EnvironmentSnapshot.plant_id == DEMO_PLANT_ID,
            EnvironmentSnapshot.window == "1h",
        )
        .order_by(EnvironmentSnapshot.window_end.desc())
        .limit(1)
    )
    snap = snap_result.scalar_one_or_none()

    if sp is None or snap is None or sp.water_min_pct is None or snap.soil_moisture_avg_pct is None:
        return ScenarioStep(
            step=8,
            description="토양 수분 < 임계값 → 물주기 규칙 트리거",
            passed=False,
            detail="종 프로필 또는 스냅샷 없음.",
        )

    passed = float(snap.soil_moisture_avg_pct) < float(sp.water_min_pct)
    detail = (
        f"soil_moisture={snap.soil_moisture_avg_pct}% < water_min={sp.water_min_pct}% ✓"
        if passed
        else f"soil_moisture={snap.soil_moisture_avg_pct}% ≥ water_min={sp.water_min_pct}% — 규칙 미발동"
    )
    return ScenarioStep(step=8, description="토양 수분 < 임계값 → 물주기 규칙 트리거", passed=passed, detail=detail)


async def _step9_care_log(session: AsyncSession) -> ScenarioStep:
    from app.models.care_log import CareLog

    count_row = await session.execute(
        select(func.count()).select_from(CareLog).where(CareLog.plant_id == DEMO_PLANT_ID)
    )
    count = count_row.scalar_one()
    passed = count >= 1
    return ScenarioStep(
        step=9,
        description="최근 관리 기록 존재 (≥ 1건)",
        passed=passed,
        detail=f"count={count}",
    )


async def _step10_plant_character(session: AsyncSession) -> ScenarioStep:
    from app.models.plant_character import PlantCharacter

    result = await session.execute(
        select(PlantCharacter)
        .where(
            PlantCharacter.plant_id == DEMO_PLANT_ID,
            PlantCharacter.primary_action == "water",
        )
        .limit(1)
    )
    char = result.scalar_one_or_none()
    passed = char is not None
    detail = (
        f"mood={char.mood}, primary_action={char.primary_action}"
        if passed and char is not None
        else "water 상태의 캐릭터 없음."
    )
    return ScenarioStep(
        step=10,
        description="식물 캐릭터 상태 존재 (primary_action=water)",
        passed=passed,
        detail=detail,
    )


async def _step11_chunk_documents(session: AsyncSession) -> ScenarioStep:
    from app.models.plant_chunk_document import PlantChunkDocument

    count_row = await session.execute(
        select(func.count())
        .select_from(PlantChunkDocument)
        .where(PlantChunkDocument.plant_knowledge_id == DEMO_KNOWLEDGE_ID)
    )
    count = count_row.scalar_one()
    passed = count >= 3
    return ScenarioStep(
        step=11,
        description="지식 베이스 청크 문서 존재 (≥ 3건)",
        passed=passed,
        detail=f"count={count} (care_knowledge, species_profile, pest_disease_reference)",
    )


def _step12_intent_classifier() -> ScenarioStep:
    """Intent classifier accuracy check — pure in-process, no DB."""
    from app.services.chat_intent_classifier import ChatIntentClassifier

    clf = ChatIntentClassifier()
    cases = [
        ("물 주는 시기가 언제야?", "watering_question"),
        ("잎이 노랗게 변하고 있어요. 병인가요?", "pest_reference_question"),
        ("몬스테라랑 같이 키울 수 있는 식물 추천해줘", "companion_plant_question"),
    ]
    results: list[str] = []
    all_passed = True
    for question, expected in cases:
        intent, confidence, _ = clf.classify(question)
        ok = intent == expected
        if not ok:
            all_passed = False
        results.append(f"{'✓' if ok else '✗'} '{question[:20]}…' → {intent} (expected {expected})")

    return ScenarioStep(
        step=12,
        description="의도 분류기 정상 동작 (3개 샘플 질문)",
        passed=all_passed,
        detail="; ".join(results),
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


async def run_scenario(session: AsyncSession) -> list[ScenarioStep]:
    steps: list[ScenarioStep] = []
    for check in (
        _step1_user_exists,
        _step2_plant_exists,
        _step3_species_thresholds,
        _step4_pothos_profile,
        _step5_philodendron_profile,
        _step6_sensor_readings,
        _step7_snapshot_exists,
        _step8_watering_trigger,
        _step9_care_log,
        _step10_plant_character,
        _step11_chunk_documents,
    ):
        steps.append(await check(session))

    steps.append(_step12_intent_classifier())
    return steps


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


async def _main() -> None:
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        steps = await run_scenario(session)

    passed = sum(1 for s in steps if s.passed)
    total = len(steps)

    output = {
        "passed": passed,
        "total": total,
        "all_passed": passed == total,
        "steps": [asdict(s) for s in steps],
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))

    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(_main())
