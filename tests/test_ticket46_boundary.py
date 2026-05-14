"""TICKET-046 boundary tests — ingestion only, no LLM/embedding/vector."""

from __future__ import annotations


def test_excel_loader_no_forbidden_imports() -> None:
    import app.ingestion.excel_loader as mod

    src = open(mod.__file__, encoding="utf-8").read()
    for forbidden in ("pgvector", "embedding", "openai", "anthropic", "torch", "redis"):
        assert forbidden not in src, f"Forbidden import {forbidden!r} in excel_loader"


def test_service_no_forbidden_imports() -> None:
    import app.services.plant_knowledge_ingest_service as mod

    src = open(mod.__file__, encoding="utf-8").read()
    for forbidden in ("pgvector", "embedding", "openai", "anthropic", "torch", "redis"):
        assert forbidden not in src, f"Forbidden import {forbidden!r} in service"


def test_legacy_filename_absent_from_default_config() -> None:
    from app.core.config import Settings

    s = Settings()
    assert "전체식물_농사로데이터" not in s.PLANT_KNOWLEDGE_EXCEL_PATH


def test_new_filename_is_default_config() -> None:
    from app.core.config import Settings

    s = Settings()
    assert "전체식물_분류정보_v1_updated_7_2" in s.PLANT_KNOWLEDGE_EXCEL_PATH


def test_no_chunk_or_vector_concepts_in_service() -> None:
    import app.services.plant_knowledge_ingest_service as mod

    src = open(mod.__file__, encoding="utf-8").read().lower()
    for forbidden in ("chunk", "vector_index", "retrieval", "evidence", "llm_port", "promptbuilder"):
        assert forbidden not in src, f"Forbidden concept {forbidden!r} in service"


def test_no_chunk_or_vector_concepts_in_loader() -> None:
    import app.ingestion.excel_loader as mod

    src = open(mod.__file__, encoding="utf-8").read().lower()
    for forbidden in ("chunk", "vector", "retrieval", "embedding", "llm"):
        assert forbidden not in src, f"Forbidden concept {forbidden!r} in excel_loader"


def test_plant_knowledge_excel_path_env_key_configurable() -> None:
    """PLANT_KNOWLEDGE_EXCEL_PATH must be overridable via env var."""
    import os

    from app.core.config import Settings

    os.environ["PLANT_KNOWLEDGE_EXCEL_PATH"] = "data/custom_override.xlsx"
    try:
        s = Settings()
        assert s.PLANT_KNOWLEDGE_EXCEL_PATH == "data/custom_override.xlsx"
    finally:
        del os.environ["PLANT_KNOWLEDGE_EXCEL_PATH"]
