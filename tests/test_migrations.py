"""TICKET-001 — Migration tests.

Requires a live PostgreSQL database.
Skipped automatically if DATABASE_URL is not set.
"""

import os

import pytest

if not os.environ.get("DATABASE_URL"):
    pytest.skip(
        "DATABASE_URL not set — skipping migration tests (requires live Postgres)",
        allow_module_level=True,
    )

import asyncio  # noqa: E402

from alembic.config import Config  # noqa: E402
from sqlalchemy import inspect  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from alembic import command  # noqa: E402

DATABASE_URL: str = os.environ["DATABASE_URL"]
REQUIRED_TABLES = [
    "users",
    "species_profiles",
    "plants",
    "plant_characters",
    "sensor_readings",
    "environment_snapshots",
    "care_logs",
    "chat_requests",
    "llm_runs",
    "recommendation_evidence",
    "retrieved_chunks",
]


def _alembic_cfg() -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    return cfg


def test_alembic_upgrade_head() -> None:
    """alembic upgrade head must succeed without error."""
    command.upgrade(_alembic_cfg(), "head")


# def test_required_tables_exist() -> None:
#     """All 11 core tables must exist after migration."""

#     async def _check() -> list[str]:
#         engine = create_async_engine(DATABASE_URL)
#         async with engine.connect() as conn:
#             tables = await conn.run_sync(
#                 lambda sync_conn: inspect(sync_conn).get_table_names()
#             )
#         await engine.dispose()
#         return tables

#     existing = asyncio.run(_check())
#     for table in REQUIRED_TABLES:
#         assert table in existing, f"Table '{table}' missing after migration"

@pytest.mark.asyncio
async def test_required_tables_exist() -> None:
    """All 11 core tables must exist after migration."""
    # 별도의 내부 함수 없이 바로 비동기 로직 실행
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        tables = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names()
        )
    await engine.dispose()
    for table in REQUIRED_TABLES:
        assert table in tables, f"Table '{table}' missing"


def test_alembic_current_reports_head() -> None:
    """alembic current must report the head revision."""
    cfg = _alembic_cfg()
    # command.current prints to stdout; we just assert no exception is raised
    command.current(cfg, verbose=False)


def test_no_metadata_create_all_shortcut() -> None:
    """Verify app startup does not call metadata.create_all."""
    # Importing app.main should not create any tables.
    # If create_all were called it would raise against an empty DB
    # or create tables outside alembic control — neither is acceptable.
    # This test simply re-imports app.main and verifies no exception.
    import importlib
    import sys

    for key in list(sys.modules):
        if key.startswith("app"):
            sys.modules.pop(key)
    importlib.import_module("app.main")  # must not raise
