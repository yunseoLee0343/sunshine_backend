"""MVP Demo Seed — TICKET-023.

Injects deterministic demo data for the 12-step MVP scenario.
All entities use stable UUID5 keys so repeated runs are idempotent.

Usage:
    python -m app.seeds.demo_seed        # seed DB, print result JSON
    python -m app.seeds.demo_seed --check  # dry-check what is already present

Demo universe:
  User        demo-user-001
  Plants      초록이 (몬스테라) — watering scenario
  Species     몬스테라, 포토스, 필로덴드론, 스파티필룸, 산세베리아
  Env         soil moisture 18 % < threshold 20 % → watering rule fires
  Knowledge   몬스테라 RAG chunks (care_knowledge, species_profile,
               pest_disease_reference) with mock embeddings
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Stable demo IDs (uuid5, reproducible across runs)
# ---------------------------------------------------------------------------

_NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # URL namespace


def demo_id(name: str) -> uuid.UUID:
    """Return a stable UUID5 for a demo entity name."""
    return uuid.uuid5(_NS, f"sunshine-demo:{name}")


DEMO_USER_ID = demo_id("user-001")
DEMO_PLANT_ID = demo_id("plant-monstera-001")
DEMO_MONSTERA_SPECIES_ID = demo_id("species-monstera")
DEMO_POTHOS_SPECIES_ID = demo_id("species-pothos")
DEMO_PHILODENDRON_SPECIES_ID = demo_id("species-philodendron")
DEMO_SPATHIPHYLLUM_SPECIES_ID = demo_id("species-spathiphyllum")
DEMO_SANSEVIERIA_SPECIES_ID = demo_id("species-sansevieria")
DEMO_KNOWLEDGE_ID = demo_id("knowledge-monstera")
DEMO_SOIL_DEVICE_ID = demo_id("device-esp32-soil-01")
DEMO_LEAF_DEVICE_ID = demo_id("device-esp32-leaf-01")

# Fixed base timestamp — keeps snapshots and readings deterministic
_BASE = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class SeedResult:
    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def record(self, action: str, label: str) -> None:
        if action == "created":
            self.created.append(label)
        elif action == "skipped":
            self.skipped.append(label)
        else:
            self.errors.append(label)

    def to_dict(self) -> dict:
        return {
            "created": self.created,
            "skipped": self.skipped,
            "errors": self.errors,
            "summary": {
                "created": len(self.created),
                "skipped": len(self.skipped),
                "errors": len(self.errors),
            },
        }


# ---------------------------------------------------------------------------
# Vector helper (deterministic mock embedding)
# ---------------------------------------------------------------------------


def make_vector(seed_str: str, dim: int = 384) -> list[float]:
    """Produce a deterministic unit-ish vector seeded from seed_str."""
    values: list[float] = []
    for i in range(dim):
        h = hashlib.md5(f"{seed_str}:{i}".encode()).hexdigest()
        v = (int(h[:8], 16) / 0xFFFFFFFF) * 2 - 1
        values.append(round(v, 6))
    return values


# ---------------------------------------------------------------------------
# Per-entity idempotent helpers
# ---------------------------------------------------------------------------


async def _ensure_user(session: AsyncSession, result: SeedResult) -> None:
    from app.models.user import User

    if await session.get(User, DEMO_USER_ID) is not None:
        result.record("skipped", "user:demo-user-001")
        return
    now = datetime.now(UTC)
    row = User(
        id=DEMO_USER_ID,
        display_name="데모 사용자 (demo-user-001)",
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    result.record("created", "user:demo-user-001")


async def _ensure_species(
    session: AsyncSession,
    result: SeedResult,
    *,
    species_id: uuid.UUID,
    label: str,
    korean_name: str,
    scientific_name: str,
    common_name: str,
    water_min: Decimal,
    water_max: Decimal,
    light_min: Decimal,
    light_max: Decimal,
    humidity_min: Decimal,
    humidity_max: Decimal,
    temp_min: Decimal,
    temp_max: Decimal,
    metadata: dict,
) -> None:
    from app.models.species_profile import SpeciesProfile

    if await session.get(SpeciesProfile, species_id) is not None:
        result.record("skipped", f"species:{label}")
        return
    now = datetime.now(UTC)
    row = SpeciesProfile(
        id=species_id,
        korean_name=korean_name,
        scientific_name=scientific_name,
        common_name=common_name,
        care_level="medium",
        water_min_pct=water_min,
        water_max_pct=water_max,
        light_min_lux=light_min,
        light_max_lux=light_max,
        humidity_min_pct=humidity_min,
        humidity_max_pct=humidity_max,
        temperature_min_c=temp_min,
        temperature_max_c=temp_max,
        metadata_json=metadata,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    result.record("created", f"species:{label}")


async def _ensure_plant(session: AsyncSession, result: SeedResult) -> None:
    from app.models.plant import Plant

    if await session.get(Plant, DEMO_PLANT_ID) is not None:
        result.record("skipped", "plant:초록이")
        return
    now = datetime.now(UTC)
    row = Plant(
        id=DEMO_PLANT_ID,
        user_id=DEMO_USER_ID,
        species_profile_id=DEMO_MONSTERA_SPECIES_ID,
        nickname="초록이",
        room_name="거실",
        external_plant_id="plant-001",
        device_id="rpi-edge-node-01",
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    result.record("created", "plant:초록이")


async def _ensure_sensor_devices(session: AsyncSession, result: SeedResult) -> None:
    from app.models.plant_sensor_device import PlantSensorDevice

    _DEVICES = [
        (DEMO_SOIL_DEVICE_ID, "esp32-soil-01", "soil", "soil"),
        (DEMO_LEAF_DEVICE_ID, "esp32-leaf-01", "leaf_env", "leaf"),
    ]
    now = datetime.now(UTC)
    for did, device_id, role, label in _DEVICES:
        if await session.get(PlantSensorDevice, did) is not None:
            result.record("skipped", f"device:{device_id}")
            continue
        row = PlantSensorDevice(
            id=did,
            plant_id=DEMO_PLANT_ID,
            device_id=device_id,
            device_role=role,
            location_label=label,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        result.record("created", f"device:{device_id}")


async def _ensure_sensor_readings(session: AsyncSession, result: SeedResult) -> None:
    from app.models.sensor_reading import SensorReading

    # 48 readings at 30-min intervals covering the 24 h before _BASE
    readings_to_create: list[SensorReading] = []
    for i in range(48):
        rid = f"demo-reading-monstera-{i:03d}"
        existing = await session.execute(select(SensorReading).where(SensorReading.reading_id == rid).limit(1))
        if existing.scalar_one_or_none() is not None:
            continue
        measured_at = _BASE - timedelta(hours=24) + timedelta(minutes=30 * i)
        # Slight variation to look realistic; soil moisture stays below threshold
        temp = Decimal("22.0") + Decimal(str(round((i % 4) * 0.2, 1)))
        humidity = Decimal("58.0") + Decimal(str(round((i % 6) * 0.5, 1)))
        light = Decimal("1200") + Decimal(str((i % 8) * 50))
        soil = Decimal("18.0") - Decimal(str(round((i % 3) * 0.3, 1)))
        row = SensorReading(
            id=uuid.uuid4(),
            reading_id=rid,
            device_id="demo-sensor-001",
            plant_id=DEMO_PLANT_ID,
            measured_at=measured_at,
            temperature_c=temp,
            humidity_pct=humidity,
            light_lux=light,
            soil_moisture_pct=soil,
            created_at=measured_at,
        )
        readings_to_create.append(row)

    for row in readings_to_create:
        session.add(row)
    if readings_to_create:
        result.record("created", f"sensor_readings:{len(readings_to_create)} readings")
    else:
        result.record("skipped", "sensor_readings:all present")


async def _ensure_snapshot(
    session: AsyncSession,
    result: SeedResult,
    *,
    window: str,
    window_start: datetime,
    window_end: datetime,
    soil_moisture_avg: Decimal,
) -> None:
    from app.models.environment_snapshot import EnvironmentSnapshot

    existing = await session.execute(
        select(EnvironmentSnapshot)
        .where(
            EnvironmentSnapshot.plant_id == DEMO_PLANT_ID,
            EnvironmentSnapshot.window == window,
            EnvironmentSnapshot.window_start == window_start,
            EnvironmentSnapshot.window_end == window_end,
        )
        .limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        result.record("skipped", f"snapshot:{window}")
        return

    row = EnvironmentSnapshot(
        id=uuid.uuid4(),
        plant_id=DEMO_PLANT_ID,
        window=window,
        window_start=window_start,
        window_end=window_end,
        temperature_avg_c=Decimal("22.0"),
        temperature_min_c=Decimal("21.0"),
        temperature_max_c=Decimal("23.0"),
        humidity_avg_pct=Decimal("58.0"),
        humidity_min_pct=Decimal("55.0"),
        humidity_max_pct=Decimal("62.0"),
        light_avg_lux=Decimal("1200"),
        light_min_lux=Decimal("800"),
        light_max_lux=Decimal("1600"),
        soil_moisture_avg_pct=soil_moisture_avg,
        soil_moisture_min_pct=Decimal("15.0"),
        soil_moisture_max_pct=Decimal("20.0"),
        created_at=datetime.now(UTC),
    )
    session.add(row)
    result.record("created", f"snapshot:{window}")


async def _ensure_care_log(session: AsyncSession, result: SeedResult) -> None:
    from app.models.care_log import CareLog

    acted_at = _BASE - timedelta(days=3, hours=3)
    existing = await session.execute(
        select(CareLog)
        .where(
            CareLog.plant_id == DEMO_PLANT_ID,
            CareLog.action_type == "water",
            CareLog.acted_at == acted_at,
        )
        .limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        result.record("skipped", "care_log:water")
        return
    row = CareLog(
        id=uuid.uuid4(),
        plant_id=DEMO_PLANT_ID,
        action_type="water",
        note="데모 시나리오 — 마지막 물주기",
        acted_at=acted_at,
        created_at=acted_at,
    )
    session.add(row)
    result.record("created", "care_log:water")


async def _ensure_plant_character(session: AsyncSession, result: SeedResult) -> None:
    from app.models.plant_character import PlantCharacter

    existing = await session.execute(
        select(PlantCharacter)
        .where(
            PlantCharacter.plant_id == DEMO_PLANT_ID,
            PlantCharacter.reason_code == "demo_soil_dry",
        )
        .limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        result.record("skipped", "plant_character:thirsty")
        return
    row = PlantCharacter(
        id=uuid.uuid4(),
        plant_id=DEMO_PLANT_ID,
        mood="thirsty",
        expression="😔",
        status_message="흙이 말랐어요. 물이 필요해요!",
        primary_action="water",
        reason_code="demo_soil_dry",
        created_at=_BASE - timedelta(hours=1),
    )
    session.add(row)
    result.record("created", "plant_character:thirsty")


# ---------------------------------------------------------------------------
# Knowledge base
# ---------------------------------------------------------------------------


async def _ensure_knowledge_entry(session: AsyncSession, result: SeedResult) -> None:
    from app.models.plant_knowledge_entry import PlantKnowledgeEntry

    existing = await session.execute(
        select(PlantKnowledgeEntry).where(PlantKnowledgeEntry.nongsaro_id == "DEMO-MONSTERA-001").limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        result.record("skipped", "knowledge_entry:monstera")
        return
    now = datetime.now(UTC)
    row = PlantKnowledgeEntry(
        id=DEMO_KNOWLEDGE_ID,
        nongsaro_id="DEMO-MONSTERA-001",
        korean_name="몬스테라",
        scientific_name="Monstera deliciosa",
        common_name="Swiss Cheese Plant",
        family="천남성과",
        origin="중앙아메리카",
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    result.record("created", "knowledge_entry:monstera")


async def _ensure_care_requirement(session: AsyncSession, result: SeedResult) -> None:
    from app.models.plant_care_requirement import PlantCareRequirement

    existing = await session.execute(
        select(PlantCareRequirement).where(PlantCareRequirement.entry_id == DEMO_KNOWLEDGE_ID).limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        result.record("skipped", "care_requirement:monstera")
        return
    now = datetime.now(UTC)
    row = PlantCareRequirement(
        id=uuid.uuid4(),
        entry_id=DEMO_KNOWLEDGE_ID,
        growth_temp_text="18–28°C (최적 20–25°C)",
        light_requirement="간접광 선호, 직사광선 회피. 500–3000 lux 적합.",
        watering_frequency=("봄·여름: 흙 표면 1–2 cm 마르면 충분히 관수. 가을·겨울: 2주에 1회 정도로 줄임."),
        soil_type="배수 좋은 혼합 배양토 (펄라이트 20% 혼합 권장)",
        fertilizer_info="생육기(봄~여름) 월 1회 액체 비료",
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    result.record("created", "care_requirement:monstera")


async def _ensure_pest_reference(session: AsyncSession, result: SeedResult) -> None:
    from app.models.plant_pest_reference import PlantPestReference

    existing = await session.execute(
        select(PlantPestReference).where(PlantPestReference.entry_id == DEMO_KNOWLEDGE_ID).limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        result.record("skipped", "pest_reference:monstera")
        return
    now = datetime.now(UTC)
    row = PlantPestReference(
        id=uuid.uuid4(),
        entry_id=DEMO_KNOWLEDGE_ID,
        pest_text=("응애: 건조한 환경에서 발생하기 쉬움. 잎 뒷면에 거미줄 형태 관찰. 진딧물: 새 잎 주변에 군집 형성."),
        disease_text=("탄저병: 잎에 갈색 반점 발생. 과습 시 악화. 뿌리 썩음병: 과습·배수 불량 환경에서 발생."),
        parsed_pest_terms=["응애", "진딧물", "탄저병", "뿌리 썩음병"],
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    result.record("created", "pest_reference:monstera")


async def _ensure_seasonal_watering(session: AsyncSession, result: SeedResult) -> None:
    from app.models.plant_seasonal_watering import PlantSeasonalWatering

    existing = await session.execute(
        select(PlantSeasonalWatering).where(PlantSeasonalWatering.entry_id == DEMO_KNOWLEDGE_ID).limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        result.record("skipped", "seasonal_watering:monstera")
        return
    now = datetime.now(UTC)
    row = PlantSeasonalWatering(
        id=uuid.uuid4(),
        entry_id=DEMO_KNOWLEDGE_ID,
        spring="7–10일마다 흙 표면 건조 확인 후 관수",
        summer="5–7일마다 관수, 고온 시 잎 분무 병행",
        autumn="10–14일마다로 간격 늘림",
        winter="2–3주에 1회, 과습 주의",
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    result.record("created", "seasonal_watering:monstera")


async def _ensure_chunk(
    session: AsyncSession,
    result: SeedResult,
    *,
    chunk_id: uuid.UUID,
    chunk_kind: str,
    chunk_text: str,
) -> None:
    from app.models.plant_chunk_document import PlantChunkDocument
    from app.models.plant_chunk_embedding import PlantChunkEmbedding

    existing = await session.execute(
        select(PlantChunkDocument)
        .where(
            PlantChunkDocument.plant_knowledge_id == DEMO_KNOWLEDGE_ID,
            PlantChunkDocument.chunk_kind == chunk_kind,
        )
        .limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        result.record("skipped", f"chunk:{chunk_kind}")
        return

    text_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
    now = datetime.now(UTC)
    doc = PlantChunkDocument(
        id=chunk_id,
        plant_knowledge_id=DEMO_KNOWLEDGE_ID,
        chunk_kind=chunk_kind,
        chunk_text=chunk_text,
        text_hash=text_hash,
        created_at=now,
        updated_at=now,
    )
    session.add(doc)

    emb = PlantChunkEmbedding(
        id=uuid.uuid4(),
        chunk_document_id=chunk_id,
        model_name="demo-embedding-v1",
        vector_dim=384,
        vector=make_vector(f"{chunk_kind}:{chunk_id}"),
        created_at=now,
        updated_at=now,
    )
    session.add(emb)
    result.record("created", f"chunk:{chunk_kind}")


# ---------------------------------------------------------------------------
# Main seed runner
# ---------------------------------------------------------------------------

_SPECIES_DEFS = [
    dict(
        species_id=DEMO_MONSTERA_SPECIES_ID,
        label="monstera",
        korean_name="몬스테라",
        scientific_name="Monstera deliciosa",
        common_name="Swiss Cheese Plant",
        water_min=Decimal("20"),
        water_max=Decimal("60"),
        light_min=Decimal("500"),
        light_max=Decimal("3000"),
        humidity_min=Decimal("50"),
        humidity_max=Decimal("80"),
        temp_min=Decimal("18"),
        temp_max=Decimal("28"),
        metadata={"is_toxic": True, "toxic_to_pets": True, "toxic_to_children": False},
    ),
    dict(
        species_id=DEMO_POTHOS_SPECIES_ID,
        label="pothos",
        korean_name="포토스",
        scientific_name="Epipremnum aureum",
        common_name="Pothos",
        water_min=Decimal("25"),
        water_max=Decimal("65"),
        light_min=Decimal("300"),
        light_max=Decimal("2000"),
        humidity_min=Decimal("40"),
        humidity_max=Decimal("70"),
        temp_min=Decimal("18"),
        temp_max=Decimal("28"),
        metadata={"is_toxic": True, "toxic_to_pets": True, "toxic_to_children": False},
    ),
    dict(
        species_id=DEMO_PHILODENDRON_SPECIES_ID,
        label="philodendron",
        korean_name="필로덴드론",
        scientific_name="Philodendron hederaceum",
        common_name="Philodendron",
        water_min=Decimal("30"),
        water_max=Decimal("60"),
        light_min=Decimal("500"),
        light_max=Decimal("2500"),
        humidity_min=Decimal("50"),
        humidity_max=Decimal("80"),
        temp_min=Decimal("18"),
        temp_max=Decimal("28"),
        metadata={"is_toxic": False, "toxic_to_pets": False, "toxic_to_children": False},
    ),
    dict(
        species_id=DEMO_SPATHIPHYLLUM_SPECIES_ID,
        label="spathiphyllum",
        korean_name="스파티필룸",
        scientific_name="Spathiphyllum wallisii",
        common_name="Peace Lily",
        water_min=Decimal("40"),
        water_max=Decimal("70"),
        light_min=Decimal("200"),
        light_max=Decimal("1000"),
        humidity_min=Decimal("50"),
        humidity_max=Decimal("80"),
        temp_min=Decimal("18"),
        temp_max=Decimal("28"),
        metadata={"is_toxic": False, "toxic_to_pets": False, "toxic_to_children": False},
    ),
    dict(
        species_id=DEMO_SANSEVIERIA_SPECIES_ID,
        label="sansevieria",
        korean_name="산세베리아",
        scientific_name="Dracaena trifasciata",
        common_name="Snake Plant",
        water_min=Decimal("10"),
        water_max=Decimal("30"),
        light_min=Decimal("500"),
        light_max=Decimal("2500"),
        humidity_min=Decimal("20"),
        humidity_max=Decimal("50"),
        temp_min=Decimal("15"),
        temp_max=Decimal("35"),
        metadata={"is_toxic": True, "toxic_to_pets": True, "toxic_to_children": False},
    ),
]

_CHUNKS = [
    (
        demo_id("chunk-care_knowledge"),
        "care_knowledge",
        (
            "몬스테라(Monstera deliciosa) 물주기: 봄·여름 성장기에는 흙 표면 1–2 cm가 "
            "마르면 충분히 관수합니다. 가을·겨울에는 2주에 한 번으로 줄여 과습을 방지하세요. "
            "화분 아래로 물이 흘러나올 만큼 충분히 주되, 물받이의 고인 물은 즉시 제거합니다. "
            "광량: 간접광이 최적이며 500–3000 lux 범위를 유지하세요."
        ),
    ),
    (
        demo_id("chunk-species_profile"),
        "species_profile",
        (
            "몬스테라 종 프로필: 천남성과 다년생 상록 덩굴 식물. "
            "원산지 중앙아메리카. 성장 온도 18–28°C, 습도 50–80%. "
            "토양 수분 20–60% 유지 권장. 직사광선 회피, 간접광 선호. "
            "성장 속도: 봄·여름 빠름, 겨울 느림. 최대 수고 약 2 m."
        ),
    ),
    (
        demo_id("chunk-pest_disease_reference"),
        "pest_disease_reference",
        (
            "몬스테라 병충해 참고 정보: "
            "응애(Spider Mite) — 건조한 환경에서 발생. 잎 뒷면 거미줄 형태 확인. "
            "진딧물(Aphid) — 새 잎 주변 군집 형성. 알코올 솜으로 닦아내거나 원예용 비누수 살포. "
            "탄저병 — 잎 갈색 반점, 과습 환경에서 악화. "
            "본 정보는 참고용이며 정확한 진단은 전문가 확인이 필요합니다."
        ),
    ),
]


async def run_seed(session: AsyncSession) -> SeedResult:
    """Insert all demo entities. Idempotent — safe to call repeatedly."""
    result = SeedResult()

    # 1. User
    await _ensure_user(session, result)

    # 2. Species profiles (monstera + companion candidates)
    for spec in _SPECIES_DEFS:
        await _ensure_species(session, result, **spec)

    # 3. Demo plant
    await _ensure_plant(session, result)

    # 3b. ESP32 device mappings (TICKET-066)
    await _ensure_sensor_devices(session, result)

    # 4. Sensor readings
    await _ensure_sensor_readings(session, result)

    # 5. Environment snapshots (latest, 24h, 7d)
    await _ensure_snapshot(
        session,
        result,
        window="latest",
        window_start=_BASE,
        window_end=_BASE,
        soil_moisture_avg=Decimal("18.0"),
    )
    await _ensure_snapshot(
        session,
        result,
        window="24h",
        window_start=_BASE - timedelta(hours=24),
        window_end=_BASE,
        soil_moisture_avg=Decimal("18.5"),
    )
    await _ensure_snapshot(
        session,
        result,
        window="7d",
        window_start=_BASE - timedelta(days=7),
        window_end=_BASE,
        soil_moisture_avg=Decimal("24.0"),
    )

    # 6. Care log (last watering 3 days ago → triggers watering rule)
    await _ensure_care_log(session, result)

    # 7. Plant character state
    await _ensure_plant_character(session, result)

    # 8. Knowledge base
    await _ensure_knowledge_entry(session, result)
    await _ensure_care_requirement(session, result)
    await _ensure_pest_reference(session, result)
    await _ensure_seasonal_watering(session, result)

    # 9. Chunk documents + embeddings
    for chunk_id, chunk_kind, chunk_text in _CHUNKS:
        await _ensure_chunk(
            session,
            result,
            chunk_id=chunk_id,
            chunk_kind=chunk_kind,
            chunk_text=chunk_text,
        )

    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


async def _main() -> None:
    from app.db.session import AsyncSessionLocal

    check_only = "--check" in sys.argv

    if check_only:
        print("ℹ️  --check mode: nothing will be written to the database.")
        print(
            json.dumps(
                {
                    "demo_ids": {
                        "user_id": str(DEMO_USER_ID),
                        "plant_id": str(DEMO_PLANT_ID),
                        "monstera_species_id": str(DEMO_MONSTERA_SPECIES_ID),
                        "pothos_species_id": str(DEMO_POTHOS_SPECIES_ID),
                        "philodendron_species_id": str(DEMO_PHILODENDRON_SPECIES_ID),
                        "knowledge_id": str(DEMO_KNOWLEDGE_ID),
                    }
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await run_seed(session)

    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(_main())
