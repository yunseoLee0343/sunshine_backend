"""validate_rag_seed_db.py — TICKET-047.

Post-import DB validation. Executes read-only SQL checks against the live DB.
All queries are SELECT only — no INSERT, UPDATE, or DELETE.

Usage:
    python scripts/validate_rag_seed_db.py
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

EXPECTED_MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
EXPECTED_VECTOR_DIM = 1024

ALLOWED_CHUNK_KINDS = frozenset(
    [
        "identity",
        "visual_trait",
        "placement",
        "care_requirement",
        "seasonal_watering",
        "pest_reference",
    ]
)


@dataclass
class ValidationReport:
    entry_count: int = 0
    chunk_document_count: int = 0
    chunk_embedding_count: int = 0
    dim_mismatch_count: int = 0
    chunk_kind_distribution: dict[str, int] = field(default_factory=dict)
    model_distribution: dict[tuple[str, int], int] = field(default_factory=dict)
    max_chunks_per_plant: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0


async def run_validation(session: AsyncSession) -> ValidationReport:
    report = ValidationReport()

    row = await session.execute(text("SELECT COUNT(*) FROM plant_knowledge_entries"))
    report.entry_count = row.scalar_one()

    row = await session.execute(text("SELECT COUNT(*) FROM plant_chunk_documents"))
    report.chunk_document_count = row.scalar_one()

    row = await session.execute(text("SELECT COUNT(*) FROM plant_chunk_embeddings"))
    report.chunk_embedding_count = row.scalar_one()

    row = await session.execute(
        text("SELECT COUNT(*) FROM plant_chunk_embeddings WHERE vector_dim <> :dim"),
        {"dim": EXPECTED_VECTOR_DIM},
    )
    report.dim_mismatch_count = row.scalar_one()
    if report.dim_mismatch_count > 0:
        report.errors.append(
            f"{report.dim_mismatch_count} embeddings have vector_dim != {EXPECTED_VECTOR_DIM}"
        )

    rows = await session.execute(
        text(
            "SELECT chunk_kind, COUNT(*) AS cnt "
            "FROM plant_chunk_documents "
            "GROUP BY chunk_kind ORDER BY chunk_kind"
        )
    )
    for kind, cnt in rows.fetchall():
        report.chunk_kind_distribution[kind] = int(cnt)
        if kind not in ALLOWED_CHUNK_KINDS:
            report.errors.append(f"Unexpected chunk_kind in DB: '{kind}'")

    rows = await session.execute(
        text(
            "SELECT model_name, vector_dim, COUNT(*) AS cnt "
            "FROM plant_chunk_embeddings "
            "GROUP BY model_name, vector_dim ORDER BY model_name, vector_dim"
        )
    )
    for model_name, vector_dim, cnt in rows.fetchall():
        report.model_distribution[(model_name, int(vector_dim))] = int(cnt)
        if model_name != EXPECTED_MODEL_NAME:
            report.errors.append(f"Unexpected model_name in DB: '{model_name}'")
        if int(vector_dim) != EXPECTED_VECTOR_DIM:
            report.errors.append(
                f"Unexpected vector_dim in DB: {vector_dim} (expected {EXPECTED_VECTOR_DIM})"
            )

    row = await session.execute(
        text(
            "SELECT COALESCE(MAX(cnt), 0) FROM ("
            "  SELECT COUNT(*) AS cnt FROM plant_chunk_documents "
            "  GROUP BY plant_knowledge_id"
            ") sub"
        )
    )
    report.max_chunks_per_plant = int(row.scalar_one())
    if report.max_chunks_per_plant > 6:
        report.errors.append(
            f"Some plant has {report.max_chunks_per_plant} chunk documents (max allowed: 6)"
        )

    return report


async def _main() -> int:
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        report = await run_validation(session)

    print(f"plant_knowledge_entries:   {report.entry_count}")
    print(f"plant_chunk_documents:     {report.chunk_document_count}")
    print(f"plant_chunk_embeddings:    {report.chunk_embedding_count}")
    print(f"dim_mismatch:              {report.dim_mismatch_count}")
    print(f"max_chunks_per_plant:      {report.max_chunks_per_plant}")
    print("chunk_kind distribution:")
    for k, v in sorted(report.chunk_kind_distribution.items()):
        print(f"  {k}: {v}")
    print("model distribution:")
    for (m, d), v in sorted(report.model_distribution.items()):
        print(f"  {m} dim={d}: {v}")

    if report.errors:
        print("\nFAILURES:")
        for err in report.errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
