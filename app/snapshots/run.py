"""One-shot snapshot aggregation CLI — TICKET-007.

Usage:
    python -m app.snapshots.run --plant-id <uuid> [--now <iso8601>]

Runs once and exits. No infinite loop, no scheduler.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from datetime import datetime


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Compute environment snapshots for a plant.")
    p.add_argument("--plant-id", required=True, type=uuid.UUID, metavar="UUID")
    p.add_argument(
        "--now",
        default=None,
        metavar="ISO8601",
        help="Reference timestamp (default: current UTC time). Must be timezone-aware.",
    )
    return p.parse_args()


def _parse_now(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        print(f"ERROR: --now value {raw!r} is not timezone-aware.", file=sys.stderr)
        sys.exit(1)
    return dt


async def _run(plant_id: uuid.UUID, now: datetime | None) -> None:
    from app.db.session import AsyncSessionLocal
    from app.services.snapshot_service import SnapshotService

    async with AsyncSessionLocal() as session:
        svc = SnapshotService(session)
        summary = await svc.aggregate(plant_id, now=now)
        await session.commit()

    print(json.dumps(summary.model_dump(mode="json"), indent=2, ensure_ascii=False))


def main() -> None:
    args = _parse_args()
    now = _parse_now(args.now)
    asyncio.run(_run(args.plant_id, now))


if __name__ == "__main__":
    main()
