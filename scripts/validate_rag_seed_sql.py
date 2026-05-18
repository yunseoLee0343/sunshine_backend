"""validate_rag_seed_sql.py — TICKET-047.

Static SQL shape validator for rag_knowledge_seed_20260513.sql.
Reads the file and asserts structural contracts WITHOUT connecting to a DB.

Usage:
    python scripts/validate_rag_seed_sql.py [path/to/rag_knowledge_seed_20260513.sql]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ALLOWED_INSERT_TABLES: frozenset[str] = frozenset(
    [
        "plant_knowledge_entries",
        "plant_chunk_documents",
        "plant_chunk_embeddings",
    ]
)

FORBIDDEN_DDL_PATTERNS: tuple[str, ...] = (
    r"\bCREATE\s+TABLE\b",
    r"\bCREATE\s+INDEX\b",
    r"\bCREATE\s+EXTENSION\b",
)

ALLOWED_CHUNK_KINDS: frozenset[str] = frozenset(
    [
        "identity",
        "visual_trait",
        "placement",
        "care_requirement",
        "seasonal_watering",
        "pest_reference",
    ]
)

QWEN_MODEL_MARKER = "Qwen/Qwen3-Embedding-0.6B"
VECTOR_DIM_MARKER = "1024"

_INSERT_RE = re.compile(r"\bINSERT\s+INTO\s+(\w+)\b", re.IGNORECASE)
_CHUNK_KIND_RE = re.compile(
    r"'(" + "|".join(re.escape(k) for k in ALLOWED_CHUNK_KINDS) + r"|[^']+)'",
    re.IGNORECASE,
)


class SqlValidationError(ValueError):
    """Raised when the SQL file fails a shape constraint."""


def validate_sql(sql: str) -> None:
    """Validate *sql* string against the TICKET-047 shape contract.

    Raises SqlValidationError on first violation.
    """
    # 1. No forbidden DDL
    for pattern in FORBIDDEN_DDL_PATTERNS:
        if re.search(pattern, sql, re.IGNORECASE):
            keyword = pattern.split(r"\b")[1].replace(r"\s+", " ")
            raise SqlValidationError(f"Forbidden DDL found: {keyword}")

    # 2. Only allowed INSERT tables
    for match in _INSERT_RE.finditer(sql):
        table = match.group(1)
        if table not in ALLOWED_INSERT_TABLES:
            raise SqlValidationError(
                f"INSERT into unexpected table '{table}'. "
                f"Allowed: {sorted(ALLOWED_INSERT_TABLES)}"
            )

    # 3. Qwen model marker
    if QWEN_MODEL_MARKER not in sql:
        raise SqlValidationError(
            f"SQL does not contain expected model marker: {QWEN_MODEL_MARKER!r}"
        )

    # 4. vector_dim 1024 marker
    if VECTOR_DIM_MARKER not in sql:
        raise SqlValidationError(
            f"SQL does not contain expected vector_dim marker: {VECTOR_DIM_MARKER!r}"
        )

    # 5. No unexpected chunk_kind values
    chunk_kind_re = re.compile(r"'([a-z_]+)'\s*(?:,|\))")
    for match in chunk_kind_re.finditer(sql):
        candidate = match.group(1)
        if (
            candidate not in ALLOWED_CHUNK_KINDS
            and re.search(
                r"chunk_kind",
                sql[max(0, match.start() - 200) : match.start()],
                re.IGNORECASE,
            )
        ):
            raise SqlValidationError(
                f"Unexpected chunk_kind value: '{candidate}'. "
                f"Allowed: {sorted(ALLOWED_CHUNK_KINDS)}"
            )


def validate_file(path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    validate_sql(sql)


def main() -> None:
    sql_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/rag_knowledge_seed_20260513.sql")

    if not sql_path.exists():
        print(f"ERROR: file not found: {sql_path}", file=sys.stderr)
        sys.exit(1)

    try:
        validate_file(sql_path)
        print(f"OK: {sql_path} passes all shape checks.")
        sys.exit(0)
    except SqlValidationError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
