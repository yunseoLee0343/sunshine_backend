"""TICKET-047 — LocalEmbeddingService tests (model not loaded)."""

from __future__ import annotations

import math
from unittest.mock import MagicMock

import pytest

from app.embedding.local_embedding_service import LocalEmbeddingService, _l2_normalize

# ---------------------------------------------------------------------------
# Config defaults
# ---------------------------------------------------------------------------


def test_default_model_is_qwen() -> None:
    assert LocalEmbeddingService.DEFAULT_MODEL == "Qwen/Qwen3-Embedding-0.6B"


def test_default_dim_is_1024() -> None:
    assert LocalEmbeddingService.DEFAULT_DIM == 1024


def test_config_default_model_name_matches_service() -> None:
    from app.core.config import settings

    assert settings.EMBEDDING_MODEL_NAME == LocalEmbeddingService.DEFAULT_MODEL


def test_config_default_vector_dim_matches_service() -> None:
    from app.core.config import settings

    assert settings.EMBEDDING_VECTOR_DIM == LocalEmbeddingService.DEFAULT_DIM


# ---------------------------------------------------------------------------
# Constructor / attributes
# ---------------------------------------------------------------------------


def test_constructor_sets_model_name() -> None:
    svc = LocalEmbeddingService(model_name="test-model", embedding_dim=4)
    assert svc.model_name == "test-model"


def test_constructor_sets_embedding_dim() -> None:
    svc = LocalEmbeddingService(embedding_dim=512)
    assert svc.embedding_dim == 512


def test_constructor_sets_normalize_embeddings() -> None:
    svc = LocalEmbeddingService(normalize_embeddings=False)
    assert svc.normalize_embeddings is False


def test_dim_property_returns_embedding_dim() -> None:
    svc = LocalEmbeddingService(embedding_dim=256)
    assert svc.dim == 256


def test_model_not_loaded_at_construction() -> None:
    """No SentenceTransformer import should happen at construction time."""
    svc = LocalEmbeddingService()
    assert svc._model is None


# ---------------------------------------------------------------------------
# embed / embed_batch with mocked model
# ---------------------------------------------------------------------------


def _make_svc_with_mock_model(dim: int = 1024) -> LocalEmbeddingService:
    svc = LocalEmbeddingService(embedding_dim=dim)
    mock_model = MagicMock()
    import numpy as np

    mock_model.encode = MagicMock(
        side_effect=lambda text, **kw: np.array([1.0 / math.sqrt(dim)] * dim)
        if isinstance(text, str)
        else np.array([[1.0 / math.sqrt(dim)] * dim] * len(text)),
    )
    svc._model = mock_model
    return svc


def test_embed_returns_1024_floats() -> None:
    svc = _make_svc_with_mock_model(dim=1024)
    vec = svc.embed("테스트 텍스트")
    assert len(vec) == 1024


def test_embed_vector_is_normalized() -> None:
    svc = _make_svc_with_mock_model(dim=1024)
    vec = svc.embed("테스트 텍스트")
    norm = math.sqrt(sum(x * x for x in vec))
    assert abs(norm - 1.0) < 1e-6


def test_embed_batch_returns_correct_count() -> None:
    svc = _make_svc_with_mock_model(dim=1024)
    vecs = svc.embed_batch(["텍스트1", "텍스트2", "텍스트3"])
    assert len(vecs) == 3


def test_embed_batch_each_vector_is_1024_floats() -> None:
    svc = _make_svc_with_mock_model(dim=1024)
    vecs = svc.embed_batch(["텍스트1", "텍스트2"])
    for vec in vecs:
        assert len(vec) == 1024


def test_embed_raises_on_dim_mismatch() -> None:
    svc = LocalEmbeddingService(embedding_dim=512)
    mock_model = MagicMock()
    import numpy as np

    mock_model.encode = MagicMock(return_value=np.array([0.1] * 1024))
    svc._model = mock_model
    with pytest.raises(ValueError, match="512"):
        svc.embed("텍스트")


# ---------------------------------------------------------------------------
# _l2_normalize helper
# ---------------------------------------------------------------------------


def test_l2_normalize_unit_vector() -> None:
    vec = [3.0, 4.0]
    result = _l2_normalize(vec)
    assert abs(result[0] - 0.6) < 1e-9
    assert abs(result[1] - 0.8) < 1e-9


def test_l2_normalize_zero_vector_returns_unchanged() -> None:
    vec = [0.0, 0.0, 0.0]
    assert _l2_normalize(vec) == [0.0, 0.0, 0.0]


def test_l2_normalize_already_unit_unchanged() -> None:
    vec = [1.0, 0.0, 0.0]
    result = _l2_normalize(vec)
    assert abs(result[0] - 1.0) < 1e-9
