"""LocalEmbeddingPort — TICKET-047.

Structural Protocol for local embedding adapters.
Concrete implementations must expose model metadata and embed/embed_batch.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LocalEmbeddingPort(Protocol):
    model_name: str
    model_rev: str
    embedding_dim: int
    normalize_embeddings: bool

    def embed(self, text: str) -> list[float]:
        """Embed a single text string. Returns exactly embedding_dim floats."""
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of text strings. Each inner list is embedding_dim floats."""
        ...
