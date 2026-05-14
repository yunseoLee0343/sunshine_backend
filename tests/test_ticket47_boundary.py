"""TICKET-047 boundary tests — chunk+embedding boundary only, no LLM/retrieval."""

from __future__ import annotations


def test_embedding_service_no_forbidden_imports() -> None:
    import app.embedding.local_embedding_service as mod

    src = open(mod.__file__, encoding="utf-8").read()
    for forbidden in ("openai", "anthropic", "pgvector", "torch", "redis", "requests"):
        assert forbidden not in src, f"Forbidden import {forbidden!r} in local_embedding_service"


def test_chunk_builder_no_forbidden_imports() -> None:
    import app.embedding.chunk_builder as mod

    src = open(mod.__file__, encoding="utf-8").read()
    for forbidden in ("openai", "anthropic", "pgvector", "torch", "redis"):
        assert forbidden not in src, f"Forbidden import {forbidden!r} in chunk_builder"


def test_chunk_build_service_no_forbidden_imports() -> None:
    import app.services.chunk_build_service as mod

    src = open(mod.__file__, encoding="utf-8").read()
    for forbidden in ("openai", "anthropic", "pgvector", "torch", "redis"):
        assert forbidden not in src, f"Forbidden import {forbidden!r} in chunk_build_service"


def test_no_retrieval_endpoint_in_service() -> None:
    import app.services.chunk_build_service as mod

    src = open(mod.__file__, encoding="utf-8").read().lower()
    for forbidden in ("retrieval", "retrieved_chunk", "evidence", "llm_port", "promptbuilder"):
        assert forbidden not in src, f"Forbidden concept {forbidden!r} in chunk_build_service"


def test_no_retrieval_tables_written_by_service() -> None:
    import app.services.chunk_build_service as mod

    src = open(mod.__file__, encoding="utf-8").read()
    for table in ("retrieval_runs", "retrieved_chunks", "retrieval_result_chunks"):
        assert table not in src, f"Forbidden table reference {table!r} in chunk_build_service"


def test_qwen_config_defaults() -> None:
    from app.core.config import Settings

    s = Settings()
    assert s.EMBEDDING_MODEL_NAME == "Qwen/Qwen3-Embedding-0.6B"
    assert s.EMBEDDING_VECTOR_DIM == 1024
    assert s.EMBEDDING_NORMALIZE is True


def test_old_model_name_absent_from_service() -> None:
    import app.embedding.local_embedding_service as mod

    src = open(mod.__file__, encoding="utf-8").read()
    assert "paraphrase-multilingual-MiniLM" not in src


def test_old_model_name_absent_from_build_chunks_cli() -> None:
    import app.embedding.build_chunks as mod

    src = open(mod.__file__, encoding="utf-8").read()
    assert "paraphrase-multilingual-MiniLM" not in src


def test_dry_run_flag_exists_in_build_chunks() -> None:
    import app.embedding.build_chunks as mod

    src = open(mod.__file__, encoding="utf-8").read()
    assert "dry-run" in src or "dry_run" in src


def test_embedding_model_field_in_chunk_embedding_model() -> None:
    from app.models.plant_chunk_embedding import PlantChunkEmbedding

    assert hasattr(PlantChunkEmbedding, "vector_norm")
    assert hasattr(PlantChunkEmbedding, "text_hash_at_embed")


def test_no_auto_seed_import_in_build_chunks() -> None:
    import app.embedding.build_chunks as mod

    src = open(mod.__file__, encoding="utf-8").read()
    assert "rag_knowledge_seed" not in src
    assert "import_rag_seed" not in src
