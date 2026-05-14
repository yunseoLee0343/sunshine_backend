"""TICKET-048 — boundary and contract tests."""

from __future__ import annotations

import uuid

# ---------------------------------------------------------------------------
# EmbeddingContract invariants
# ---------------------------------------------------------------------------


def test_qwen_contract_model_name() -> None:
    from app.domain.rag import QWEN_CONTRACT

    assert QWEN_CONTRACT.model_name == "Qwen/Qwen3-Embedding-0.6B"


def test_qwen_contract_vector_dim() -> None:
    from app.domain.rag import QWEN_CONTRACT

    assert QWEN_CONTRACT.vector_dim == 1024


def test_qwen_contract_normalize_true() -> None:
    from app.domain.rag import QWEN_CONTRACT

    assert QWEN_CONTRACT.normalize is True


def test_incompatible_embedding_error_is_runtime_error() -> None:
    from app.domain.rag import IncompatibleEmbeddingError

    err = IncompatibleEmbeddingError("test")
    assert isinstance(err, RuntimeError)


# ---------------------------------------------------------------------------
# Config aligns with QWEN_CONTRACT
# ---------------------------------------------------------------------------


def test_config_model_name_matches_qwen_contract() -> None:
    from app.core.config import settings
    from app.domain.rag import QWEN_CONTRACT

    assert settings.EMBEDDING_MODEL_NAME == QWEN_CONTRACT.model_name


def test_config_vector_dim_matches_qwen_contract() -> None:
    from app.core.config import settings
    from app.domain.rag import QWEN_CONTRACT

    assert settings.EMBEDDING_VECTOR_DIM == QWEN_CONTRACT.vector_dim


# ---------------------------------------------------------------------------
# No forbidden imports in production modules
# ---------------------------------------------------------------------------


def test_hybrid_retriever_no_llm_imports() -> None:
    import app.retrieval.hybrid_retriever as mod

    src = open(mod.__file__, encoding="utf-8").read()
    for forbidden in ("openai", "anthropic", "torch", "PromptBuilder", "EvidenceBuilder"):
        assert forbidden not in src


def test_retrieval_service_no_llm_imports() -> None:
    import app.services.retrieval_service as mod

    src = open(mod.__file__, encoding="utf-8").read()
    for forbidden in ("openai", "anthropic", "torch", "PromptBuilder", "EvidenceBuilder", "final_answer"):
        assert forbidden not in src


# ---------------------------------------------------------------------------
# Migration chain is intact
# ---------------------------------------------------------------------------


def test_migration_0012_revises_0011() -> None:
    from pathlib import Path

    src = Path("alembic/versions/0012_ticket48_retrieval_qwen_fields.py").read_text(encoding="utf-8")
    assert 'down_revision: str | None = "0011"' in src


# ---------------------------------------------------------------------------
# RetrievalRequest: query alias is idempotent with question
# ---------------------------------------------------------------------------


def test_query_alias_idempotent_with_question() -> None:
    from app.schemas.retrieval import RetrievalRequest

    rid = uuid.uuid4()
    uid = uuid.uuid4()

    req_via_question = RetrievalRequest(request_id=rid, user_id=uid, question="test")
    req_via_query = RetrievalRequest(request_id=rid, user_id=uid, query="test")  # type: ignore[call-arg]

    assert req_via_question.question == req_via_query.question


# ---------------------------------------------------------------------------
# Chunk kinds covered by RAG layers
# ---------------------------------------------------------------------------


def test_all_chunk_kinds_reachable_via_rag_layers() -> None:
    from app.domain.chunk import CHUNK_KINDS
    from app.domain.retrieval import RAG_LAYER_TO_CHUNK_KINDS

    covered: set[str] = set()
    for kinds in RAG_LAYER_TO_CHUNK_KINDS.values():
        covered.update(kinds)
    assert covered == set(CHUNK_KINDS)
