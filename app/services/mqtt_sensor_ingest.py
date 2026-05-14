"""MqttSensorIngestService — TICKET-006 / TICKET-053.

Pipeline:
  1. Parse topic → device_id via topic.parse_device_id()
  2. JSON-decode payload bytes
  3. Validate with SensorReadingRequest (re-uses Ticket-005 schema)
  4. Check topic device_id == payload device_id
  5. Call SensorIngestService.ingest() — all DB logic lives there
  6. On inserted outcome: call SnapshotService.aggregate(plant_id)
     — snapshot failure is logged but does not roll back the reading
"""

import json
import logging

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.mqtt.schemas import IngestOutcome, MqttIngestResult
from app.mqtt.topic import parse_device_id
from app.schemas.sensor_readings import SensorReadingRequest
from app.services.sensor_ingest import SensorIngestService

logger = logging.getLogger(__name__)


class MqttSensorIngestService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def process(self, topic: str, payload_bytes: bytes) -> MqttIngestResult:
        # 1. Parse topic.
        try:
            topic_device_id = parse_device_id(topic)
        except ValueError as exc:
            logger.warning("invalid topic %r: %s", topic, exc)
            return MqttIngestResult(outcome=IngestOutcome.invalid_topic, detail=str(exc))

        # 2. JSON decode.
        try:
            raw = json.loads(payload_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning("json decode failed for topic %r: %s", topic, exc)
            return MqttIngestResult(outcome=IngestOutcome.invalid_payload, detail=str(exc))

        # 3. Pydantic validation.
        try:
            req = SensorReadingRequest.model_validate(raw)
        except ValidationError as exc:
            logger.warning("payload validation failed for topic %r: %s", topic, exc)
            return MqttIngestResult(outcome=IngestOutcome.invalid_payload, detail=str(exc))

        # 4. device_id cross-check.
        if req.device_id != topic_device_id:
            logger.warning(
                "device_id mismatch on topic %r: topic=%r payload=%r",
                topic,
                topic_device_id,
                req.device_id,
            )
            return MqttIngestResult(
                outcome=IngestOutcome.device_id_mismatch,
                reading_id=req.reading_id,
                detail=(f"topic device_id {topic_device_id!r} != payload device_id {req.device_id!r}"),
            )

        # 5. Delegate to existing service (all plant-lookup + idempotency logic).
        try:
            svc = SensorIngestService(self._session)
            response, _ = await svc.ingest(req)
            outcome = IngestOutcome(response.status)
            resolved_plant_id = svc.resolved_plant_id
        except Exception as exc:  # includes HTTPException(404)
            from fastapi import HTTPException as _HTTPExc

            if isinstance(exc, _HTTPExc) and exc.status_code == 404:
                return MqttIngestResult(
                    outcome=IngestOutcome.plant_not_found,
                    reading_id=req.reading_id,
                    detail=exc.detail,
                )
            logger.exception("unexpected error ingesting %r", topic)
            return MqttIngestResult(
                outcome=IngestOutcome.error,
                reading_id=getattr(req, "reading_id", None),
                detail=str(exc),
            )

        # 6. Refresh snapshots only for fresh inserts.
        snapshot_refreshed = False
        if outcome == IngestOutcome.inserted and resolved_plant_id is not None:
            try:
                from app.services.snapshot_service import SnapshotService

                snap_svc = SnapshotService(self._session)
                await snap_svc.aggregate(resolved_plant_id)
                snapshot_refreshed = True
            except Exception as exc:
                logger.error(
                    "snapshot refresh failed for plant_id=%s reading_id=%s: %s",
                    resolved_plant_id,
                    req.reading_id,
                    exc,
                )

        return MqttIngestResult(
            outcome=outcome,
            reading_id=req.reading_id,
            plant_id=str(resolved_plant_id) if resolved_plant_id is not None else None,
            snapshot_refreshed=snapshot_refreshed,
        )
