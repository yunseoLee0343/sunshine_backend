"""MqttSensorIngestService — TICKET-006.

Pipeline:
  1. Parse topic → device_id via topic.parse_device_id()
  2. JSON-decode payload bytes
  3. Validate with SensorReadingRequest (re-uses Ticket-005 schema)
  4. Check topic device_id == payload device_id
  5. Call SensorIngestService.ingest() — all DB logic lives there

No new DB logic, no snapshot, no character update, no Rule Engine.
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
            return MqttIngestResult(
                outcome=IngestOutcome.invalid_payload, detail=str(exc)
            )

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
                detail=(
                    f"topic device_id {topic_device_id!r} != "
                    f"payload device_id {req.device_id!r}"
                ),
            )

        # 5. Delegate to existing service (all plant-lookup + idempotency logic).
        try:
            from fastapi import HTTPException

            svc = SensorIngestService(self._session)
            response, _ = await svc.ingest(req)
            outcome = IngestOutcome(response.status)
            return MqttIngestResult(outcome=outcome, reading_id=req.reading_id)
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
