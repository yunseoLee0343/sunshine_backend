"""Sensor Readings API router — TICKET-005."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.schemas.sensor_readings import SensorReadingRequest, SensorReadingResponse
from app.services.sensor_ingest import SensorIngestService

router = APIRouter(prefix="/sensor-readings", tags=["sensor-readings"])


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session


@router.post("", response_model=SensorReadingResponse)
async def create_sensor_reading(
    req: SensorReadingRequest,
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    svc = SensorIngestService(session)
    response, status_code = await svc.ingest(req)
    return JSONResponse(content=response.model_dump(), status_code=status_code)
