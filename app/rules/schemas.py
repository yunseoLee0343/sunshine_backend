"""Rule Engine output DTO — TICKET-008."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.rules.types import CareStatus, PrimaryAction, Severity


class RuleEngineResult(BaseModel):
    plant_id: uuid.UUID
    evaluated_at: datetime
    care_status: CareStatus
    primary_action: PrimaryAction
    severity: Severity
    reason_codes: list[str]
    evidence_facts: dict[str, object]
    rule_results: list[dict]  # per-rule breakdown for traceability
