"""CLI: build embedding chunks for plant knowledge — TICKET-047.

Usage:
    python -m app.embedding.build_chunks [--entry-id <UUID>] [--model <name>] [--dry-run]

Builds (or rebuilds) text chunks + local embeddings for all 14A entries,
or a single entry when --entry-id is supplied. Prints a JSON summary.
Exits with code 1 if any errors occurred.

--dry-run: skip DB connection and model loading; print a confirmation that
           the CLI is reachable and exit 0.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build plant knowledge embedding chunks.")
    p.add_argument(
        "--entry-id",
        metavar="UUID",
        help="Limit rebuild to a single plant_knowledge_entries.id.",
    )
    p.add_argument(
        "--model",
        metavar="NAME",
        default=None,
        help="Local sentence-transformers model name (default: from config).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip DB and model; verify CLI is reachable.",
    )
    return p.parse_args()


async def _run(entry_id: uuid.UUID | None, model_name: str) -> int:
    from app.db.session import AsyncSessionLocal
    from app.embedding.local_embedding_service import LocalEmbeddingService
    from app.services.chunk_build_service import ChunkBuildService

    emb = LocalEmbeddingService(model_name)

    async with AsyncSessionLocal() as session:
        svc = ChunkBuildService(session, emb)
        if entry_id is not None:
            summary = await svc.build_for_entry(entry_id)
        else:
            summary = await svc.build_all()
        await session.commit()

    result = {
        "total_entries": summary.total_entries,
        "inserted": summary.inserted,
        "updated": summary.updated,
        "skipped": summary.skipped,
        "errors": summary.errors,
        "error_details": summary.error_details,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if summary.errors > 0 else 0


def main() -> None:
    args = _parse_args()

    if args.dry_run:
        from app.core.config import settings

        print(
            json.dumps(
                {
                    "dry_run": True,
                    "model": settings.EMBEDDING_MODEL_NAME,
                    "vector_dim": settings.EMBEDDING_VECTOR_DIM,
                    "normalize": settings.EMBEDDING_NORMALIZE,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        sys.exit(0)

    entry_id: uuid.UUID | None = None
    if args.entry_id:
        try:
            entry_id = uuid.UUID(args.entry_id)
        except ValueError:
            print(f"ERROR: invalid UUID: {args.entry_id}", file=sys.stderr)
            sys.exit(1)

    from app.core.config import settings

    model_name = args.model or settings.EMBEDDING_MODEL_NAME
    code = asyncio.run(_run(entry_id, model_name))
    sys.exit(code)


if __name__ == "__main__":
    main()
