"""TICKET-024 — E2E test fixtures.

Requires a live PostgreSQL database (DATABASE_URL env var).
Seeds demo data once per module and deletes it after all module tests finish.
"""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.main import app
from app.seeds.demo_seed import (
    DEMO_KNOWLEDGE_ID,
    DEMO_MONSTERA_SPECIES_ID,
    DEMO_PHILODENDRON_SPECIES_ID,
    DEMO_PLANT_ID,
    DEMO_POTHOS_SPECIES_ID,
    DEMO_SANSEVIERIA_SPECIES_ID,
    DEMO_SPATHIPHYLLUM_SPECIES_ID,
    DEMO_USER_ID,
    run_seed,
)

_DEMO_SPECIES_IDS = [
    DEMO_MONSTERA_SPECIES_ID,
    DEMO_POTHOS_SPECIES_ID,
    DEMO_PHILODENDRON_SPECIES_ID,
    DEMO_SPATHIPHYLLUM_SPECIES_ID,
    DEMO_SANSEVIERIA_SPECIES_ID,
]


# ---------------------------------------------------------------------------
# Seed / teardown
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module", autouse=True)
async def seed_demo_data() -> None:
    """Insert all demo entities before the module; delete them after."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        pytest.skip("DATABASE_URL not set — skipping E2E tests")

    engine = create_async_engine(url, poolclass=NullPool)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        async with session.begin():
            await run_seed(session)

    yield

    async with AsyncSession(engine, expire_on_commit=False) as session:
        async with session.begin():
            await _cleanup_demo(session)

    await engine.dispose()


async def _cleanup_demo(session: AsyncSession) -> None:
    from app.models.care_log import CareLog
    from app.models.chat_request import ChatRequest
    from app.models.environment_snapshot import EnvironmentSnapshot
    from app.models.evidence_bundle import EvidenceBundle
    from app.models.plant import Plant
    from app.models.plant_character import PlantCharacter
    from app.models.plant_knowledge_entry import PlantKnowledgeEntry
    from app.models.retrieval_run import RetrievalRun
    from app.models.sensor_reading import SensorReading
    from app.models.species_profile import SpeciesProfile
    from app.models.user import User

    # chat run children (no CASCADE on FKs to chat_requests)
    await session.execute(
        text(
            "DELETE FROM recommendation_evidence WHERE request_id IN "
            "(SELECT id FROM chat_requests WHERE plant_id = :pid)"
        ),
        {"pid": DEMO_PLANT_ID},
    )
    await session.execute(
        text("DELETE FROM retrieved_chunks WHERE request_id IN (SELECT id FROM chat_requests WHERE plant_id = :pid)"),
        {"pid": DEMO_PLANT_ID},
    )
    await session.execute(
        text("DELETE FROM llm_runs WHERE request_id IN (SELECT id FROM chat_requests WHERE plant_id = :pid)"),
        {"pid": DEMO_PLANT_ID},
    )
    await session.execute(delete(ChatRequest).where(ChatRequest.plant_id == DEMO_PLANT_ID))

    # evidence bundles
    await session.execute(delete(EvidenceBundle).where(EvidenceBundle.plant_id == DEMO_PLANT_ID))

    # retrieval runs — CASCADE removes retrieval_result_chunks
    await session.execute(delete(RetrievalRun).where(RetrievalRun.user_id == DEMO_USER_ID))

    # knowledge entry — CASCADE removes all knowledge children and chunk docs/embeddings
    await session.execute(delete(PlantKnowledgeEntry).where(PlantKnowledgeEntry.id == DEMO_KNOWLEDGE_ID))

    # plant data
    await session.execute(delete(PlantCharacter).where(PlantCharacter.plant_id == DEMO_PLANT_ID))
    await session.execute(delete(CareLog).where(CareLog.plant_id == DEMO_PLANT_ID))
    await session.execute(delete(EnvironmentSnapshot).where(EnvironmentSnapshot.plant_id == DEMO_PLANT_ID))
    await session.execute(delete(SensorReading).where(SensorReading.plant_id == DEMO_PLANT_ID))
    await session.execute(delete(Plant).where(Plant.id == DEMO_PLANT_ID))

    # species then user
    await session.execute(delete(SpeciesProfile).where(SpeciesProfile.id.in_(_DEMO_SPECIES_IDS)))
    await session.execute(delete(User).where(User.id == DEMO_USER_ID))


# ---------------------------------------------------------------------------
# HTTP client (module-scoped, no dependency overrides)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module")
async def client(seed_demo_data) -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
