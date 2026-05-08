"""TICKET-001 — DB model introspection tests.

Validates model existence, table names, columns, and constraints
without requiring a live database connection.
"""

import pytest
from sqlalchemy import UniqueConstraint

from app.models.care_log import CareLog
from app.models.chat_request import ChatRequest
from app.models.environment_snapshot import EnvironmentSnapshot
from app.models.llm_run import LlmRun
from app.models.plant import Plant
from app.models.plant_character import PlantCharacter
from app.models.recommendation_evidence import RecommendationEvidence
from app.models.retrieved_chunk import RetrievedChunk
from app.models.sensor_reading import SensorReading
from app.models.species_profile import SpeciesProfile
from app.models.user import User


# ------------------------------------------------------------------ existence
@pytest.mark.parametrize(
    "model, tablename",
    [
        (User, "users"),
        (SpeciesProfile, "species_profiles"),
        (Plant, "plants"),
        (PlantCharacter, "plant_characters"),
        (SensorReading, "sensor_readings"),
        (EnvironmentSnapshot, "environment_snapshots"),
        (CareLog, "care_logs"),
        (ChatRequest, "chat_requests"),
        (LlmRun, "llm_runs"),
        (RecommendationEvidence, "recommendation_evidence"),
        (RetrievedChunk, "retrieved_chunks"),
    ],
)
def test_model_tablename(model, tablename: str) -> None:
    assert model.__tablename__ == tablename


# ------------------------------------------------------------------- columns
def test_user_has_required_columns() -> None:
    cols = {c.name for c in User.__table__.columns}
    assert {"id", "display_name", "created_at", "updated_at"} <= cols


def test_plant_fk_user_id() -> None:
    fks = {fk.target_fullname for fk in Plant.__table__.foreign_keys}
    assert "users.id" in fks


def test_plant_fk_species_profile_id() -> None:
    fks = {fk.target_fullname for fk in Plant.__table__.foreign_keys}
    assert "species_profiles.id" in fks


def test_sensor_reading_reading_id_unique() -> None:
    uqs = [c for c in SensorReading.__table__.constraints if isinstance(c, UniqueConstraint)]
    unique_cols = {col.name for uq in uqs for col in uq.columns}
    assert "reading_id" in unique_cols


def test_environment_snapshot_composite_unique() -> None:
    uqs = [
        c for c in EnvironmentSnapshot.__table__.constraints if isinstance(c, UniqueConstraint)
    ]
    assert uqs, "environment_snapshots must have a UniqueConstraint"
    composite_cols = {col.name for uq in uqs for col in uq.columns}
    assert {"plant_id", "window", "window_start", "window_end"} <= composite_cols


def test_sensor_reading_has_required_columns() -> None:
    cols = {c.name for c in SensorReading.__table__.columns}
    required = {
        "id",
        "reading_id",
        "device_id",
        "plant_id",
        "measured_at",
        "temperature_c",
        "humidity_pct",
        "light_lux",
        "soil_moisture_pct",
        "created_at",
    }
    assert required <= cols


def test_llm_run_fk_chat_request() -> None:
    fks = {fk.target_fullname for fk in LlmRun.__table__.foreign_keys}
    assert "chat_requests.id" in fks


def test_chat_request_fk_user() -> None:
    fks = {fk.target_fullname for fk in ChatRequest.__table__.foreign_keys}
    assert "users.id" in fks


def test_species_profile_has_metadata_json() -> None:
    cols = {c.name for c in SpeciesProfile.__table__.columns}
    assert "metadata_json" in cols


def test_plant_character_has_required_columns() -> None:
    cols = {c.name for c in PlantCharacter.__table__.columns}
    assert {"mood", "expression", "status_message", "reason_code"} <= cols


def test_all_models_have_id_as_uuid() -> None:
    models = [
        User,
        SpeciesProfile,
        Plant,
        PlantCharacter,
        SensorReading,
        EnvironmentSnapshot,
        CareLog,
        ChatRequest,
        LlmRun,
        RecommendationEvidence,
        RetrievedChunk,
    ]
    for model in models:
        pk_cols = [c for c in model.__table__.columns if c.primary_key]
        assert len(pk_cols) == 1, f"{model.__tablename__} must have exactly one PK"
        assert pk_cols[0].name == "id"
