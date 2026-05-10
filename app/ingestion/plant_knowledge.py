"""One-shot Plant Knowledge ingestion CLI — TICKET-014A.

Usage:
    python -m app.ingestion.plant_knowledge --file <path.xlsx>

Reads the Excel file, upserts rows into the 7 knowledge tables, and
prints a JSON summary. Exits with code 1 if any rows errored.
No LLM, no embeddings, no vector index.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Ingest plant knowledge from an Excel workbook."
    )
    p.add_argument("--file", required=True, metavar="PATH",
                   help="Path to the .xlsx source file.")
    return p.parse_args()


async def _run(file_path: Path) -> int:
    from app.db.session import AsyncSessionLocal
    from app.services.plant_knowledge_ingest_service import PlantKnowledgeIngestService

    async with AsyncSessionLocal() as session:
        svc = PlantKnowledgeIngestService(session)
        summary = await svc.ingest_file(file_path)
        await session.commit()

    result = {
        "source_file": summary.source_file,
        "total_rows": summary.total_rows,
        "inserted": summary.inserted,
        "updated": summary.updated,
        "ignored": summary.ignored,
        "errors": summary.errors,
        "error_details": summary.error_details,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if summary.errors > 0 else 0


def main() -> None:
    args = _parse_args()
    path = Path(args.file)
    if not path.exists():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    code = asyncio.run(_run(path))
    sys.exit(code)


if __name__ == "__main__":
    main()
