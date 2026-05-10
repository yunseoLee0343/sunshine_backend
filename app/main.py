from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.care_logs import router as care_logs_router
from app.api.chat import router as chat_router
from app.api.companion import router as companion_router
from app.api.environment import router as environment_router
from app.api.evidence import router as evidence_router
from app.api.home import router as home_router
from app.api.plants import router as plants_router
from app.api.retrieval import router as retrieval_router
from app.api.rule_character_sync import router as rule_character_sync_router
from app.api.sensor_readings import router as sensor_readings_router
from app.core.config import settings
from app.db.health import check_db

app = FastAPI(title=settings.APP_NAME)

app.include_router(care_logs_router)
app.include_router(chat_router)
app.include_router(companion_router)
app.include_router(environment_router)
app.include_router(evidence_router)
app.include_router(home_router)
app.include_router(plants_router)
app.include_router(retrieval_router)
app.include_router(sensor_readings_router)
app.include_router(rule_character_sync_router)


@app.get("/healthz")
def healthz() -> dict:
    """Liveness probe — does NOT check DB. Ticket 0 contract preserved."""
    return {"status": "ok", "service": "sunshine-backend"}


@app.get("/readyz")
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
