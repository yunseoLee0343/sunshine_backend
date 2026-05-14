"""TICKET-047 — Static SQL shape validator tests."""

from __future__ import annotations

import pytest

from scripts.validate_rag_seed_sql import (
    ALLOWED_CHUNK_KINDS,
    ALLOWED_INSERT_TABLES,
    QWEN_MODEL_MARKER,
    VECTOR_DIM_MARKER,
    SqlValidationError,
    validate_sql,
)

_MINIMAL_VALID_SQL = (
    "INSERT INTO plant_knowledge_entries (id, korean_name) VALUES ('uuid1', '몬스테라');\n"
    "INSERT INTO plant_chunk_documents (id, chunk_kind) VALUES ('uuid2', 'identity');\n"
    f"INSERT INTO plant_chunk_embeddings (id, model_name, vector_dim)"
    f" VALUES ('uuid3', '{QWEN_MODEL_MARKER}', {VECTOR_DIM_MARKER});\n"
)


def test_valid_sql_passes() -> None:
    validate_sql(_MINIMAL_VALID_SQL)


def test_rejected_create_table() -> None:
    sql = _MINIMAL_VALID_SQL + "\nCREATE TABLE foo (id INT);"
    with pytest.raises(SqlValidationError, match="CREATE"):
        validate_sql(sql)


def test_rejected_create_index() -> None:
    sql = _MINIMAL_VALID_SQL + "\nCREATE INDEX idx_foo ON foo (id);"
    with pytest.raises(SqlValidationError, match="CREATE"):
        validate_sql(sql)


def test_rejected_create_extension() -> None:
    sql = _MINIMAL_VALID_SQL + "\nCREATE EXTENSION vector;"
    with pytest.raises(SqlValidationError, match="CREATE"):
        validate_sql(sql)


def test_rejected_unexpected_insert_table() -> None:
    sql = _MINIMAL_VALID_SQL + "\nINSERT INTO retrieval_runs (id) VALUES ('uuid9');"
    with pytest.raises(SqlValidationError, match="retrieval_runs"):
        validate_sql(sql)


def test_rejected_missing_qwen_marker() -> None:
    sql = """
INSERT INTO plant_knowledge_entries (id) VALUES ('uuid1');
INSERT INTO plant_chunk_embeddings (id, model_name, vector_dim) VALUES ('uuid3', 'old-model', 1024);
"""
    with pytest.raises(SqlValidationError, match="Qwen"):
        validate_sql(sql)


def test_rejected_missing_vector_dim_marker() -> None:
    sql = f"""
INSERT INTO plant_knowledge_entries (id) VALUES ('uuid1');
INSERT INTO plant_chunk_embeddings (id, model_name, vector_dim) VALUES ('uuid3', '{QWEN_MODEL_MARKER}', 384);
"""
    with pytest.raises(SqlValidationError, match="vector_dim"):
        validate_sql(sql)


def test_allowed_insert_tables_constant() -> None:
    assert "plant_knowledge_entries" in ALLOWED_INSERT_TABLES
    assert "plant_chunk_documents" in ALLOWED_INSERT_TABLES
    assert "plant_chunk_embeddings" in ALLOWED_INSERT_TABLES
    assert "retrieval_runs" not in ALLOWED_INSERT_TABLES
    assert "retrieved_chunks" not in ALLOWED_INSERT_TABLES


def test_allowed_chunk_kinds_constant() -> None:
    expected = {"identity", "visual_trait", "placement", "care_requirement", "seasonal_watering", "pest_reference"}
    assert ALLOWED_CHUNK_KINDS == expected


def test_all_allowed_tables_in_valid_sql() -> None:
    """Positive: each allowed table can appear in valid SQL."""
    for table in ALLOWED_INSERT_TABLES:
        sql = (
            f"INSERT INTO {table} (id) VALUES ('uuid1');\n"
            f"INSERT INTO plant_chunk_embeddings (id, model_name, vector_dim) "
            f"VALUES ('u', '{QWEN_MODEL_MARKER}', {VECTOR_DIM_MARKER});"
        )
        validate_sql(sql)


@pytest.mark.skipif(
    not __import__("pathlib").Path("rag_knowledge_seed_20260513.sql").exists(),
    reason="seed file not present in workspace",
)
def test_actual_seed_file_passes_validation() -> None:
    from pathlib import Path

    from scripts.validate_rag_seed_sql import validate_file

    validate_file(Path("rag_knowledge_seed_20260513.sql"))
