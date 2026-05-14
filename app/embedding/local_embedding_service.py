"""Local embedding service — TICKET-047.

Loads a sentence-transformers model on first call (lazy, not at import time).
Produces L2-normalised float vectors. No external API calls.
Model: Qwen/Qwen3-Embedding-0.6B, vector_dim=1024.
"""

from __future__ import annotations

import math
from typing import Any


class LocalEmbeddingService:
    DEFAULT_MODEL = "Qwen/Qwen3-Embedding-0.6B"
    DEFAULT_REVISION = "main"
    DEFAULT_DIM = 1024

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        model_rev: str = DEFAULT_REVISION,
        embedding_dim: int = DEFAULT_DIM,
        normalize_embeddings: bool = True,
    ) -> None:
        self.model_name = model_name
        self.model_rev = model_rev
        self.embedding_dim = embedding_dim
        self.normalize_embeddings = normalize_embeddings
        self._model: Any = None

    def _load(self) -> None:
        if self._model is not None:
            return
        from sentence_transformers import SentenceTransformer  # loaded on demand

        self._model = SentenceTransformer(self.model_name, revision=self.model_rev)

    def embed(self, text: str) -> list[float]:
        self._load()
        raw = self._model.encode(text, normalize_embeddings=False)
        vec = _l2_normalize(raw.tolist())
        if len(vec) != self.embedding_dim:
            raise ValueError(f"Expected {self.embedding_dim} dims, got {len(vec)}")
        return vec

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self._load()
        raw = self._model.encode(texts, normalize_embeddings=False, batch_size=64)
        result: list[list[float]] = []
        for v in raw:
            vec = _l2_normalize(v.tolist())
            if len(vec) != self.embedding_dim:
                raise ValueError(f"Expected {self.embedding_dim} dims, got {len(vec)}")
            result.append(vec)
        return result

    @property
    def dim(self) -> int:
        return self.embedding_dim


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return vec
    return [x / norm for x in vec]
