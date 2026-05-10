from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.plants import router as plants_router
from app.api.sensor_readings import router as sensor_readings_router
from app.core.config import settings
from app.db.health import check_db

app = FastAPI(title=settings.APP_NAME)

app.include_router(plants_router)
app.include_router(sensor_readings_router)


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
