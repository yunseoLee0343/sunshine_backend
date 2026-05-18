"""TICKET-061 — validate_rag_seed_db.py unit tests.

Tests run_validation() against a mock DB session without any live DB.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from scripts.validate_rag_seed_db import (
    EXPECTED_CHUNK_DOC_COUNT,
    EXPECTED_CHUNK_EMB_COUNT,
    EXPECTED_CHUNKS_PER_KIND,
    EXPECTED_ENTRY_COUNT,
    EXPECTED_MODEL_NAME,
    EXPECTED_VECTOR_DIM,
    run_validation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session(
    entry_count: int = EXPECTED_ENTRY_COUNT,
    chunk_doc_count: int = EXPECTED_CHUNK_DOC_COUNT,
    chunk_emb_count: int = EXPECTED_CHUNK_EMB_COUNT,
    dim_mismatch_count: int = 0,
    chunk_kinds: list[tuple[str, int]] | None = None,
    model_rows: list[tuple[str, int, int]] | None = None,
    max_chunks_per_plant: int = 6,
) -> MagicMock:
    """Build a mock AsyncSession whose execute() returns canned results."""
    if chunk_kinds is None:
        chunk_kinds = [
            ("care_requirement", EXPECTED_CHUNKS_PER_KIND),
            ("identity", EXPECTED_CHUNKS_PER_KIND),
            ("pest_reference", EXPECTED_CHUNKS_PER_KIND),
            ("placement", EXPECTED_CHUNKS_PER_KIND),
            ("seasonal_watering", EXPECTED_CHUNKS_PER_KIND),
            ("visual_trait", EXPECTED_CHUNKS_PER_KIND),
        ]
    if model_rows is None:
        model_rows = [(EXPECTED_MODEL_NAME, EXPECTED_VECTOR_DIM, EXPECTED_CHUNK_EMB_COUNT)]

    scalar_sequence = [
        entry_count,
        chunk_doc_count,
        chunk_emb_count,
        dim_mismatch_count,
        max_chunks_per_plant,
    ]
    scalar_iter = iter(scalar_sequence)

    fetchall_sequence = [chunk_kinds, model_rows]
    fetchall_iter = iter(fetchall_sequence)

    def _make_result(is_fetchall: bool):
        result = MagicMock()
        if is_fetchall:
            result.fetchall.return_value = next(fetchall_iter)
        else:
            result.scalar_one.return_value = next(scalar_iter)
        return result

    call_count = [0]

    async def _execute(query, *args, **kwargs):
        call_count[0] += 1
        # Calls 1-4 are scalar (entry, chunk_doc, chunk_emb, dim_mismatch)
        # Call 5 is fetchall (chunk_kinds)
        # Call 6 is fetchall (model_rows)
        # Call 7 is scalar (max_chunks_per_plant)
        idx = call_count[0]
        return _make_result(is_fetchall=(idx in (5, 6)))

    session = MagicMock()
    session.execute = _execute
    return session


def _run(session) -> object:
    return asyncio.run(run_validation(session))


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_correct_counts_passes() -> None:
    report = _run(_make_session())
    assert report.passed
    assert not report.errors


def test_correct_counts_fields() -> None:
    report = _run(_make_session())
    assert report.entry_count == EXPECTED_ENTRY_COUNT
    assert report.chunk_document_count == EXPECTED_CHUNK_DOC_COUNT
    assert report.chunk_embedding_count == EXPECTED_CHUNK_EMB_COUNT


# ---------------------------------------------------------------------------
# Count failures
# ---------------------------------------------------------------------------


def test_wrong_entry_count_fails() -> None:
    report = _run(_make_session(entry_count=100))
    assert not report.passed
    assert any("plant_knowledge_entries" in e for e in report.errors)


def test_wrong_chunk_doc_count_fails() -> None:
    report = _run(_make_session(chunk_doc_count=700))
    assert not report.passed
    assert any("plant_chunk_documents" in e for e in report.errors)


def test_wrong_chunk_emb_count_fails() -> None:
    report = _run(_make_session(chunk_emb_count=700))
    assert not report.passed
    assert any("plant_chunk_embeddings" in e for e in report.errors)


# ---------------------------------------------------------------------------
# Per-kind count
# ---------------------------------------------------------------------------


def test_wrong_kind_count_fails() -> None:
    kinds = [
        ("care_requirement", 100),  # wrong — should be 121
        ("identity", EXPECTED_CHUNKS_PER_KIND),
        ("pest_reference", EXPECTED_CHUNKS_PER_KIND),
        ("placement", EXPECTED_CHUNKS_PER_KIND),
        ("seasonal_watering", EXPECTED_CHUNKS_PER_KIND),
        ("visual_trait", EXPECTED_CHUNKS_PER_KIND),
    ]
    report = _run(_make_session(chunk_kinds=kinds))
    assert not report.passed
    assert any("care_requirement" in e for e in report.errors)


def test_unknown_chunk_kind_fails() -> None:
    kinds = [("unknown_kind", 121)]
    report = _run(_make_session(chunk_kinds=kinds))
    assert not report.passed
    assert any("unknown_kind" in e for e in report.errors)


# ---------------------------------------------------------------------------
# Model / dim failures
# ---------------------------------------------------------------------------


def test_wrong_model_name_fails() -> None:
    model_rows = [("wrong-model", EXPECTED_VECTOR_DIM, EXPECTED_CHUNK_EMB_COUNT)]
    report = _run(_make_session(model_rows=model_rows))
    assert not report.passed
    assert any("wrong-model" in e for e in report.errors)


def test_wrong_vector_dim_fails() -> None:
    report = _run(_make_session(dim_mismatch_count=5))
    assert not report.passed
    assert any(str(EXPECTED_VECTOR_DIM) in e for e in report.errors)


def test_dim_distribution_wrong_dim_fails() -> None:
    model_rows = [(EXPECTED_MODEL_NAME, 512, EXPECTED_CHUNK_EMB_COUNT)]
    report = _run(_make_session(model_rows=model_rows))
    assert not report.passed


# ---------------------------------------------------------------------------
# max_chunks_per_plant
# ---------------------------------------------------------------------------


def test_too_many_chunks_per_plant_fails() -> None:
    report = _run(_make_session(max_chunks_per_plant=7))
    assert not report.passed
    assert any("7" in e for e in report.errors)


def test_exactly_six_chunks_per_plant_passes() -> None:
    report = _run(_make_session(max_chunks_per_plant=6))
    assert report.passed
