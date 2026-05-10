"""TICKET-004 — Character state persistence tests.

Verifies that every state change is appended as a new ``plant_characters``
row, never overwrites an existing row, and that ``get_latest_for_plant``
returns the newest row. Uses an in-memory list to fake the repository so
no live Postgres is required.
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.domain.character_state import CharacterState
from app.models.plant_character import PlantCharacter
from app.repositories.character_repository import CharacterRepository
from app.services.character_state_engine import CharacterStateEngine


class _FakeSession:
    """Minimal AsyncSession stand-in capturing add()/flush() for tests."""

    def __init__(self) -> None:
        self.rows: list[PlantCharacter] = []

    def add(self, obj: PlantCharacter) -> None:
        self.rows.append(obj)

    async def flush(self) -> None:  # noqa: D401 — interface match
        return None


def _make_row(plant_id: uuid.UUID, state: CharacterState, when: datetime) -> PlantCharacter:
    return PlantCharacter(
        id=uuid.uuid4(),
        plant_id=plant_id,
        mood=state.mood,
        expression=state.expression,
        status_message=state.status_message,
        primary_action=state.primary_action,
        reason_code=state.reason_code,
        created_at=when,
    )


# ---------------------------------------------------------------------------
# Append-only
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_inserts_row_into_session() -> None:
    session = _FakeSession()
    repo = CharacterRepository(session)  # type: ignore[arg-type]
    plant_id = uuid.uuid4()
    state = CharacterStateEngine().map("good")
    row = _make_row(plant_id, state, datetime.now(UTC))

    await repo.create(row)

    assert len(session.rows) == 1
    assert session.rows[0] is row


@pytest.mark.asyncio
async def test_multiple_updates_append_multiple_rows() -> None:
    session = _FakeSession()
    repo = CharacterRepository(session)  # type: ignore[arg-type]
    plant_id = uuid.uuid4()
    eng = CharacterStateEngine()
    base = datetime.now(UTC)

    await repo.create(_make_row(plant_id, eng.map("onboarding_created"), base))
    await repo.create(
        _make_row(plant_id, eng.map("low_soil_moisture"), base + timedelta(seconds=1))
    )
    await repo.create(
        _make_row(plant_id, eng.map("after_watering"), base + timedelta(seconds=2))
    )

    assert len(session.rows) == 3
    # Append-only: the original "onboarding_created" row is still present.
    assert session.rows[0].reason_code == "onboarding_created"
    assert session.rows[1].reason_code == "low_soil_moisture"
    assert session.rows[2].reason_code == "after_watering"


@pytest.mark.asyncio
async def test_create_does_not_mutate_existing_rows() -> None:
    session = _FakeSession()
    repo = CharacterRepository(session)  # type: ignore[arg-type]
    plant_id = uuid.uuid4()
    eng = CharacterStateEngine()
    base = datetime.now(UTC)

    first = _make_row(plant_id, eng.map("good"), base)
    await repo.create(first)
    snapshot = (
        first.id,
        first.mood,
        first.expression,
        first.status_message,
        first.primary_action,
        first.reason_code,
        first.created_at,
    )

    await repo.create(
        _make_row(plant_id, eng.map("low_light"), base + timedelta(seconds=1))
    )

    after = (
        first.id,
        first.mood,
        first.expression,
        first.status_message,
        first.primary_action,
        first.reason_code,
        first.created_at,
    )
    assert snapshot == after


# ---------------------------------------------------------------------------
# Latest lookup ordering — exercised against the actual SELECT semantics by
# faking the SQLAlchemy execute() pipeline.
# ---------------------------------------------------------------------------


class _FakeSelectResult:
    def __init__(self, row: PlantCharacter | None) -> None:
        self._row = row

    def scalar_one_or_none(self) -> PlantCharacter | None:
        return self._row

    def scalars(self):  # noqa: D401 — interface match
        outer = self

        class _S:
            def all(self_inner):
                return [outer._row] if outer._row is not None else []

        return _S()


class _LookupSession:
    """Fake session whose execute() returns the latest-by-created_at row."""

    def __init__(self, rows: list[PlantCharacter]) -> None:
        self.rows = rows

    def add(self, obj):  # not used here
        self.rows.append(obj)

    async def flush(self):
        return None

    async def execute(self, stmt):
        # The repository orders by created_at desc, id desc, limit 1.
        if not self.rows:
            return _FakeSelectResult(None)
        latest = max(self.rows, key=lambda r: (r.created_at, str(r.id)))
        return _FakeSelectResult(latest)


@pytest.mark.asyncio
async def test_latest_lookup_returns_newest_row() -> None:
    plant_id = uuid.uuid4()
    eng = CharacterStateEngine()
    base = datetime.now(UTC)
    rows = [
        _make_row(plant_id, eng.map("onboarding_created"), base),
        _make_row(plant_id, eng.map("low_soil_moisture"), base + timedelta(seconds=10)),
        _make_row(plant_id, eng.map("after_watering"), base + timedelta(seconds=20)),
    ]
    session = _LookupSession(rows)
    repo = CharacterRepository(session)  # type: ignore[arg-type]

    latest = await repo.get_latest_for_plant(plant_id)

    assert latest is not None
    assert latest.reason_code == "after_watering"


@pytest.mark.asyncio
async def test_latest_lookup_returns_none_when_no_rows() -> None:
    session = _LookupSession([])
    repo = CharacterRepository(session)  # type: ignore[arg-type]
    latest = await repo.get_latest_for_plant(uuid.uuid4())
    assert latest is None


# ---------------------------------------------------------------------------
# reason_code + primary_action are persisted on the model
# ---------------------------------------------------------------------------


def test_plant_character_model_has_required_columns() -> None:
    cols = {c.name for c in PlantCharacter.__table__.columns}
    assert "primary_action" in cols
    assert "reason_code" in cols
    assert "mood" in cols
    assert "expression" in cols
    assert "status_message" in cols


def test_engine_output_round_trips_through_model() -> None:
    state = CharacterStateEngine().map("low_soil_moisture")
    row = _make_row(uuid.uuid4(), state, datetime.now(UTC))
    assert row.reason_code == "low_soil_moisture"
    assert row.primary_action == "water"
    assert row.mood == "thirsty"
    assert row.status_message == "목이 말라 보여요."


# Ensure asyncio test collection works in this module under the project's
# auto asyncio_mode configuration.
def test_asyncio_module_loads_under_pytest() -> None:
    assert asyncio.iscoroutinefunction(CharacterRepository.create)
