"""RAG domain types — TICKET-048.

Defines the embedding contract and hard invariants for query/chunk alignment.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddingContract:
    """Describes the required embedding model configuration."""

    model_name: str
    vector_dim: int
    normalize: bool


QWEN_CONTRACT = EmbeddingContract(
    model_name="Qwen/Qwen3-Embedding-0.6B",
    vector_dim=1024,
    normalize=True,
)


class IncompatibleEmbeddingError(RuntimeError):
    """Raised when all candidate embeddings are incompatible with the current model/dim.

    The embedding store must be rebuilt with the current model settings before
    retrieval can proceed. This maps to HTTP 503 at the API layer.
    """
