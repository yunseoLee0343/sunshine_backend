"""One-shot Rule → Character sync CLI — TICKET-008.5.

Usage:
    python -m app.rules.character_sync --plant-id <uuid> --now <iso8601>

Runs RuleEngine for the plant, maps the result to a Condition, and
appends a new plant_characters row. Prints the saved row as JSON.
No infinite loop, no scheduler, no LLM.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from datetime import datetime, timedelta


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Sync Rule Engine result to character state for a single plant."
    )
    p.add_argument("--plant-id", required=True, type=uuid.UUID, metavar="UUID")
    p.add_argument("--now", required=True, metavar="ISO8601",
                   help="Reference timestamp (timezone-aware).")
    return p.parse_args()


def _parse_now(raw: str) -> datetime:
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        print(f"ERROR: --now value {raw!r} is not timezone-aware.", file=sys.stderr)
        sys.exit(1)
    return dt


async def _run(plant_id: uuid.UUID, now: datetime) -> None:
    from sqlalchemy import select

    from app.db.session import AsyncSessionLocal
    from app.models.plant import Plant
    from app.repositories.rule_input_repository import RuleInputRepository
    from app.rules.types import LatestSnapshot, SpeciesThresholds
    from app.services.rule_character_sync import RuleCharacterSyncService
    from app.services.rule_engine import RuleEngine

    async with AsyncSessionLocal() as session:
        plant = await session.get(Plant, plant_id)
        if plant is None:
            print(f"ERROR: plant {plant_id} not found.", file=sys.stderr)
            sys.exit(1)

        repo = RuleInputRepository(session)

        thresholds = (
            await repo.get_thresholds(plant.species_profile_id)
            if plant.species_profile_id
            else None
        ) or SpeciesThresholds()

        snapshot = await repo.get_latest_snapshot(plant_id, before=now) or LatestSnapshot()

        since = now - timedelta(days=7)
        care_logs = await repo.get_recent_care_logs(plant_id, since=since, now=now)

        rule_result = RuleEngine().evaluate(
            plant_id=plant_id,
            thresholds=thresholds,
            snapshot=snapshot,
            care_logs=care_logs,
            now=now,
        )

        svc = RuleCharacterSyncService(session)
        row = await svc.sync(rule_result, now=now)
        await session.commit()

    print(json.dumps({
        "id": str(row.id),
        "plant_id": str(row.plant_id),
        "mood": row.mood,
        "expression": row.expression,
        "status_message": row.status_message,
        "primary_action": row.primary_action,
        "reason_code": row.reason_code,
        "created_at": row.created_at.isoformat(),
    }, ensure_ascii=False, indent=2))


def main() -> None:
    args = _parse_args()
    now = _parse_now(args.now)
    asyncio.run(_run(args.plant_id, now))


if __name__ == "__main__":
    main()
