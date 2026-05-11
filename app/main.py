from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.care_logs import router as care_logs_router
from app.api.chat import router as chat_router
from app.api.chat_evaluation import router as chat_evaluation_router
from app.api.chat_runs import router as chat_runs_router
from app.api.companion import router as companion_router
from app.api.environment import router as environment_router
from app.api.evidence import router as evidence_router
from app.api.history import router as history_router
from app.api.home import router as home_router
from app.api.plants import router as plants_router
from app.api.retrieval import router as retrieval_router
from app.api.rule_character_sync import router as rule_character_sync_router
from app.api.sensor_readings import router as sensor_readings_router
from app.db.health import check_db

_DESCRIPTION = """
Sunshine Backend — MVP API for AI-powered plant care.

## Features

- **Plant Management** — register plants, track care history, query character state
- **Sensor Ingestion** — ingest soil / light / humidity / temperature readings via REST
- **Rule Engine** — deterministic care recommendations based on sensor thresholds
- **Hybrid RAG Chat** — plant-care Q&A backed by vector + keyword retrieval and Claude
- **Companion Recommendations** — compatibility scoring across species
- **Audit Trail** — full decision evidence (evidence bundle, prompt hash) for every chat run

## Authentication

All user-scoped endpoints accept identity via **`X-User-Id: <uuid>`** header (preferred)
or **`?user_id=<uuid>`** query parameter. No JWT or session tokens in the MVP.

## Demo seed data

Run `python -m app.seeds.demo_seed` after `alembic upgrade head` to load stable demo entities:

| Entity | ID |
|--------|----|
| Demo user | `2a307656-dfbb-55f6-9054-007f2014e4a9` |
| Monstera plant (초록이) | `23d1867e-f2d0-5bf7-a4c3-f3568c06aeea` |
| Monstera species profile | `bc8ce428-d40b-539e-9fbe-f31d002d279c` |
"""

_TAGS_METADATA = [
    {
        "name": "plants",
        "description": "Plant registration, detail retrieval, species candidate scoring, "
        "and character state management.",
    },
    {
        "name": "home",
        "description": "Home-screen summary cards — aggregated character state, environment "
        "status, and daily recommended action per plant.",
    },
    {
        "name": "sensor-readings",
        "description": "Ingest raw sensor readings (soil moisture, light, humidity, temperature). "
        "Readings are aggregated into hourly environment snapshots by the snapshot service.",
    },
    {
        "name": "care-logs",
        "description": "Record manual care actions (watering, notes). Watering entries also "
        "trigger a character state update.",
    },
    {
        "name": "chat",
        "description": "Plant-care conversational Q&A powered by hybrid RAG (vector + BM25) "
        "and Claude. Includes intent classification and guardrails for pest diagnosis.",
    },
    {
        "name": "companion",
        "description": "Companion plant compatibility scoring. Returns ranked species candidates "
        "whose environmental requirements overlap with the queried plant.",
    },
    {
        "name": "environment",
        "description": "Pre-computed environment snapshot summaries and character explanation "
        "for a plant. Read-only — no model inference or rule engine invoked.",
    },
    {
        "name": "retrieval",
        "description": "Low-level hybrid retrieval endpoint (vector similarity + BM25 keyword). "
        "Primarily for integration testing; the chat endpoint calls this internally.",
    },
    {
        "name": "evidence",
        "description": "Build and cache evidence bundles — the structured context object that "
        "feeds the model prompt. Internal; called by the chat orchestrator.",
    },
    {
        "name": "audit",
        "description": "Audit trail for completed chat runs: full evidence bundle, retrieved "
        "chunks, prompt text, model response, and prompt_hash integrity verification.",
    },
    {
        "name": "evaluation",
        "description": "Chat evaluation — A/B group assignment, faithfulness / relevance / "
        "ground-truth-similarity metrics, and ground truth CRUD.",
    },
    {
        "name": "internal",
        "description": "Internal / dev-only endpoints. Not part of the public API contract. "
        "Used for manual triggering and integration testing.",
    },
]

app = FastAPI(
    title="Sunshine Backend",
    description=_DESCRIPTION,
    version="0.1.0",
    openapi_tags=_TAGS_METADATA,
    contact={
        "name": "Sunshine Team",
        "email": "plant.project090@gmail.com",
    },
    license_info={
        "name": "Private — All rights reserved",
    },
)

app.include_router(care_logs_router)
app.include_router(chat_router)
app.include_router(chat_evaluation_router)
app.include_router(chat_runs_router)
app.include_router(companion_router)
app.include_router(environment_router)
app.include_router(evidence_router)
app.include_router(history_router)
app.include_router(home_router)
app.include_router(plants_router)
app.include_router(retrieval_router)
app.include_router(sensor_readings_router)
app.include_router(rule_character_sync_router)


@app.get("/healthz", tags=["internal"], summary="Liveness probe")
def healthz() -> dict:
    """Liveness probe — does NOT check DB. Ticket 0 contract preserved."""
    return {"status": "ok", "service": "sunshine-backend"}


@app.get("/readyz", tags=["internal"], summary="Readiness probe")
async def readyz() -> JSONResponse:
    """Readiness probe — checks Postgres connectivity via SELECT 1."""
    db_ok = await check_db()
    if db_ok:
        return JSONResponse(
            content={
                "status": "ready",
                "service": "sunshine-backend",
                "checks": {"database": "ok"},
            },
            status_code=200,
        )
    return JSONResponse(
        content={
            "status": "not_ready",
            "service": "sunshine-backend",
            "checks": {"database": "error"},
        },
        status_code=503,
    )
