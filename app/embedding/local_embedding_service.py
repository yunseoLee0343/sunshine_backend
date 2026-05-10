"""Local embedding service — TICKET-014B.

Loads a sentence-transformers model on first call (lazy, not at import time).
Produces L2-normalised float vectors. No external API calls.
"""

from __future__ import annotations

import math
from typing import Any


class LocalEmbeddingService:
    DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        self.model_name = model_name
        self._model: Any = None

    def _load(self) -> None:
        if self._model is not None:
            return
        from sentence_transformers import SentenceTransformer  # loaded on demand
        self._model = SentenceTransformer(self.model_name)

    def embed(self, text: str) -> list[float]:
        self._load()
        raw = self._model.encode(text, normalize_embeddings=False)
        return _l2_normalize(raw.tolist())

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self._load()
        raw = self._model.encode(texts, normalize_embeddings=False, batch_size=64)
        return [_l2_normalize(v.tolist()) for v in raw]

    @property
    def dim(self) -> int:
        self._load()
        return int(self._model.get_sentence_embedding_dimension())


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return vec
    return [x / norm for x in vec]
