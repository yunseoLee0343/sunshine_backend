"""MQTT ingestion result schema — TICKET-006."""

from dataclasses import dataclass
from enum import StrEnum


class IngestOutcome(StrEnum):
    inserted = "inserted"
    duplicate_ignored = "duplicate_ignored"
    device_id_mismatch = "device_id_mismatch"
    invalid_topic = "invalid_topic"
    invalid_payload = "invalid_payload"
    plant_not_found = "plant_not_found"
    error = "error"


@dataclass(frozen=True)
class MqttIngestResult:
    outcome: IngestOutcome
    reading_id: str | None = None
    detail: str | None = None
