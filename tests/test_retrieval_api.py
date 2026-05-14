"""TICKET-048 — /retrieval/query API layer tests."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.domain.rag import IncompatibleEmbeddingError
from app.domain.retrieval import RetrievalRunResult, RetrievedChunkResult


def _make_app():
    from fastapi import FastAPI

    from app.api.retrieval import router

    app = FastAPI()
    app.include_router(router)
    return app


def _valid_body(**kwargs) -> dict:
    return {
        "request_id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "question": "몬스테라 여름 관리",
        **kwargs,
    }


# ---------------------------------------------------------------------------
# 503 on IncompatibleEmbeddingError
# ---------------------------------------------------------------------------


def test_503_on_incompatible_embedding() -> None:
    app = _make_app()
    client = TestClient(app, raise_server_exceptions=False)

    with patch("app.api.retrieval.AsyncSessionLocal") as mock_session_ctx:
        mock_session = AsyncMock()
        mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_session.commit = AsyncMock()

        with patch("app.api.retrieval.RetrievalService") as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.query = AsyncMock(side_effect=IncompatibleEmbeddingError("stale"))
            mock_svc_cls.return_value = mock_svc

            resp = client.post("/retrieval/query", json=_valid_body())

    assert resp.status_code == 503
    body = resp.json()
    assert body["error"] == "incompatible_embedding"


# ---------------------------------------------------------------------------
# layer field in response
# ---------------------------------------------------------------------------


def test_response_includes_layer_field() -> None:
    app = _make_app()
    client = TestClient(app, raise_server_exceptions=False)

    chunk = RetrievedChunkResult(
        chunk_document_id=uuid.uuid4(),
        plant_knowledge_id=uuid.uuid4(),
        chunk_kind="seasonal_watering",
        chunk_text="여름엔 많이 주세요.",
        similarity_score=0.85,
        rank=1,
        rag_layer="care_knowledge",
    )
    run_result = RetrievalRunResult(
        request_id=uuid.UUID(_valid_body()["request_id"]),
        question="몬스테라 여름 관리",
        results=[chunk],
        from_cache=False,
    )

    with patch("app.api.retrieval.AsyncSessionLocal") as mock_session_ctx:
        mock_session = AsyncMock()
        mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_session.commit = AsyncMock()

        with patch("app.api.retrieval.RetrievalService") as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.query = AsyncMock(return_value=run_result)
            mock_svc_cls.return_value = mock_svc

            body = _valid_body()
            body["request_id"] = str(run_result.request_id)
            resp = client.post("/retrieval/query", json=body)

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["layer"] == "care_knowledge"


# ---------------------------------------------------------------------------
# pest_disease_reference → reference_only=true in structured_metadata
# ---------------------------------------------------------------------------


def test_pest_chunk_has_reference_only_true() -> None:
    app = _make_app()
    client = TestClient(app, raise_server_exceptions=False)

    chunk = RetrievedChunkResult(
        chunk_document_id=uuid.uuid4(),
        plant_knowledge_id=uuid.uuid4(),
        chunk_kind="pest_reference",
        chunk_text="진딧물 관리.",
        similarity_score=0.72,
        rank=1,
        rag_layer="pest_disease_reference",
    )
    run_result = RetrievalRunResult(
        request_id=uuid.uuid4(),
        question="해충",
        results=[chunk],
        from_cache=False,
    )

    with patch("app.api.retrieval.AsyncSessionLocal") as mock_session_ctx:
        mock_session = AsyncMock()
        mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_session.commit = AsyncMock()

        with patch("app.api.retrieval.RetrievalService") as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.query = AsyncMock(return_value=run_result)
            mock_svc_cls.return_value = mock_svc

            resp = client.post(
                "/retrieval/query",
                json={
                    "request_id": str(run_result.request_id),
                    "user_id": str(uuid.uuid4()),
                    "question": "해충",
                },
            )

    assert resp.status_code == 200
    result = resp.json()["results"][0]
    assert result["structured_metadata"]["reference_only"] is True


# ---------------------------------------------------------------------------
# No forbidden fields in response
# ---------------------------------------------------------------------------


def test_response_has_no_final_answer() -> None:
    app = _make_app()
    client = TestClient(app, raise_server_exceptions=False)

    run_result = RetrievalRunResult(
        request_id=uuid.uuid4(),
        question="test",
        results=[],
        from_cache=False,
    )

    with patch("app.api.retrieval.AsyncSessionLocal") as mock_session_ctx:
        mock_session = AsyncMock()
        mock_session_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_session.commit = AsyncMock()

        with patch("app.api.retrieval.RetrievalService") as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc.query = AsyncMock(return_value=run_result)
            mock_svc_cls.return_value = mock_svc

            resp = client.post(
                "/retrieval/query",
                json={
                    "request_id": str(run_result.request_id),
                    "user_id": str(uuid.uuid4()),
                    "question": "test",
                },
            )

    data = resp.json()
    for forbidden in ("final_answer", "prompt", "evidence_bundle", "diagnosis", "treatment", "companion_ranking"):
        assert forbidden not in data
