"""TICKET-047 — LocalEmbeddingPort Protocol tests."""

from __future__ import annotations

from app.embedding.local_embedding_port import LocalEmbeddingPort
from app.embedding.local_embedding_service import LocalEmbeddingService


def test_local_embedding_service_satisfies_port_protocol() -> None:
    svc = LocalEmbeddingService.__new__(LocalEmbeddingService)
    svc.model_name = "Qwen/Qwen3-Embedding-0.6B"
    svc.model_rev = "main"
    svc.embedding_dim = 1024
    svc.normalize_embeddings = True
    assert isinstance(svc, LocalEmbeddingPort)


def test_port_requires_model_name() -> None:
    assert "model_name" in LocalEmbeddingPort.__protocol_attrs__


def test_port_requires_model_rev() -> None:
    assert "model_rev" in LocalEmbeddingPort.__protocol_attrs__


def test_port_requires_embedding_dim() -> None:
    assert "embedding_dim" in LocalEmbeddingPort.__protocol_attrs__


def test_port_requires_normalize_embeddings() -> None:
    assert "normalize_embeddings" in LocalEmbeddingPort.__protocol_attrs__


def test_port_requires_embed_method() -> None:
    assert "embed" in LocalEmbeddingPort.__protocol_attrs__


def test_port_requires_embed_batch_method() -> None:
    assert "embed_batch" in LocalEmbeddingPort.__protocol_attrs__
