"""TICKET-015 — EvidenceBuilder pure-logic tests (no DB, no LLM)."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.evidence import (
    CharacterEvidence,
    ChunkEvidence,
    ForwardContext,
    SnapshotEvidence,
)
from app.schemas.evidence_bundle import EvidenceBuildRequest
from app.services.evidence_builder import _compute_coverage

# ---------------------------------------------------------------------------
# ForwardContext.build + evidence_hash
# ---------------------------------------------------------------------------


def _sample_ctx(**overrides) -> ForwardContext:
    defaults = dict(
        plant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        question="몬스테라 물주기 알려줘",
        intent="watering_question",
        rag_layers=["care_knowledge"],
        character=None,
        snapshot=None,
        recent_care_logs=[],
        rule_evidence_facts={},
        rule_reason_codes=[],
        rule_primary_action="none",
        retrieved_chunks=[],
        source_coverage={},
    )
    defaults.update(overrides)
    return ForwardContext.build(**defaults)


def test_forward_context_build_sets_evidence_hash() -> None:
    ctx = _sample_ctx()
    assert len(ctx.evidence_hash) == 64  # SHA-256 hex


def test_evidence_hash_is_sha256_of_json() -> None:
    ctx = _sample_ctx()
    d = asdict(ctx)
    d.pop("evidence_hash")
    canonical = json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    assert ctx.evidence_hash == expected


def test_same_inputs_produce_same_hash() -> None:
    pid = uuid.uuid4()
    uid = uuid.uuid4()
    h1 = _sample_ctx(plant_id=pid, user_id=uid).evidence_hash
    h2 = _sample_ctx(plant_id=pid, user_id=uid).evidence_hash
    assert h1 == h2


def test_different_question_produces_different_hash() -> None:
    pid = uuid.uuid4()
    uid = uuid.uuid4()
    h1 = _sample_ctx(plant_id=pid, user_id=uid, question="물주기").evidence_hash
    h2 = _sample_ctx(plant_id=pid, user_id=uid, question="빛 얼마나 필요해?").evidence_hash
    assert h1 != h2


def test_rag_layers_are_sorted_in_context() -> None:
    ctx = _sample_ctx(rag_layers=["pest_disease_reference", "care_knowledge", "species_profile"])
    assert ctx.rag_layers == sorted(ctx.rag_layers)


def test_to_dict_is_json_serialisable() -> None:
    chunk = ChunkEvidence(
        chunk_document_id=str(uuid.uuid4()),
        plant_knowledge_id=str(uuid.uuid4()),
        chunk_kind="care_requirement",
        chunk_text="몬스테라 관리 방법.",
        similarity_score=0.91,
        rank=1,
    )
    ctx = _sample_ctx(retrieved_chunks=[chunk])
    d = ctx.to_dict()
    assert json.dumps(d)  # must not raise


# ---------------------------------------------------------------------------
# CharacterEvidence
# ---------------------------------------------------------------------------


def test_character_evidence_is_frozen() -> None:
    c = CharacterEvidence(
        mood="happy",
        expression="😊",
        status_message="Good",
        primary_action="none",
        reason_code="good",
    )
    with pytest.raises((AttributeError, TypeError)):
        c.mood = "sad"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SnapshotEvidence
# ---------------------------------------------------------------------------


def test_snapshot_evidence_preserves_none_metrics() -> None:
    s = SnapshotEvidence(
        window="latest",
        temperature_avg_c=None,
        humidity_avg_pct=None,
        light_avg_lux=None,
        soil_moisture_avg_pct=None,
    )
    assert s.temperature_avg_c is None


# ---------------------------------------------------------------------------
# ChunkEvidence
# ---------------------------------------------------------------------------


def test_chunk_evidence_ids_are_strings() -> None:
    cid = uuid.uuid4()
    kid = uuid.uuid4()
    c = ChunkEvidence(
        chunk_document_id=str(cid),
        plant_knowledge_id=str(kid),
        chunk_kind="identity",
        chunk_text="some text",
        similarity_score=0.75,
        rank=2,
    )
    assert isinstance(c.chunk_document_id, str)
    assert isinstance(c.plant_knowledge_id, str)


# ---------------------------------------------------------------------------
# _compute_coverage
# ---------------------------------------------------------------------------


def test_compute_coverage_true_when_chunk_kind_matches() -> None:
    chunks = [
        ChunkEvidence(
            chunk_document_id=str(uuid.uuid4()),
            plant_knowledge_id=str(uuid.uuid4()),
            chunk_kind="care_requirement",
            chunk_text="",
            similarity_score=0.8,
            rank=1,
        )
    ]
    cov = _compute_coverage(["care_knowledge"], chunks)
    assert cov["care_knowledge"] is True


def test_compute_coverage_false_when_no_matching_chunk() -> None:
    cov = _compute_coverage(["pest_disease_reference"], [])
    assert cov["pest_disease_reference"] is False


def test_compute_coverage_covers_all_requested_layers() -> None:
    from app.domain.retrieval import ALL_RAG_LAYERS

    cov = _compute_coverage(list(ALL_RAG_LAYERS), [])
    assert set(cov.keys()) == set(ALL_RAG_LAYERS)
    assert all(v is False for v in cov.values())


def test_compute_coverage_partial() -> None:
    chunks = [
        ChunkEvidence(
            chunk_document_id=str(uuid.uuid4()),
            plant_knowledge_id=str(uuid.uuid4()),
            chunk_kind="pest_reference",
            chunk_text="",
            similarity_score=0.9,
            rank=1,
        )
    ]
    cov = _compute_coverage(["care_knowledge", "pest_disease_reference"], chunks)
    assert cov["pest_disease_reference"] is True
    assert cov["care_knowledge"] is False


# ---------------------------------------------------------------------------
# EvidenceBuildRequest schema
# ---------------------------------------------------------------------------


def test_evidence_build_request_defaults_rag_layers() -> None:
    from app.domain.retrieval import ALL_RAG_LAYERS

    req = EvidenceBuildRequest(
        plant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        question="물주기 알려줘",
        intent="watering_question",
    )
    assert set(req.rag_layers) == set(ALL_RAG_LAYERS)


def test_evidence_build_request_rejects_extra_fields() -> None:
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        EvidenceBuildRequest(
            plant_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            question="test",
            intent="watering_question",
            unknown="bad",
        )


def test_evidence_build_request_accepts_retrieval_run_id() -> None:
    rid = uuid.uuid4()
    req = EvidenceBuildRequest(
        plant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        question="test",
        intent="watering_question",
        retrieval_run_id=rid,
    )
    assert req.retrieval_run_id == rid


# ---------------------------------------------------------------------------
# EvidenceBuilderService: plant not found
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_raises_when_plant_not_found() -> None:
    from app.services.evidence_builder import EvidenceBuilderService, PlantNotFoundError

    session = AsyncMock()
    session.get = AsyncMock(return_value=None)

    svc = EvidenceBuilderService(session)
    req = EvidenceBuildRequest(
        plant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        question="test",
        intent="watering_question",
    )
    with pytest.raises(PlantNotFoundError):
        await svc.build(req)


# ---------------------------------------------------------------------------
# EvidenceBuilderService: returns from_cache=True on duplicate hash
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_returns_from_cache_true_on_duplicate() -> None:
    from app.models.evidence_bundle import EvidenceBundle
    from app.models.plant import Plant
    from app.services.evidence_builder import EvidenceBuilderService

    plant_id = uuid.uuid4()
    fake_plant = MagicMock(spec=Plant)
    fake_plant.id = plant_id
    fake_plant.species_profile_id = None

    fake_bundle = MagicMock(spec=EvidenceBundle)

    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    get_calls = []

    async def fake_get(model, key):
        get_calls.append(model)
        if model is Plant:
            return fake_plant
        return None

    session.get = fake_get

    # execute returns empty scalars for all queries
    empty_scalars = MagicMock()
    empty_scalars.scalars.return_value.all.return_value = []
    empty_scalars.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=empty_scalars)

    svc = EvidenceBuilderService(session)

    # Patch the rule engine to return an empty result
    with patch.object(
        svc,
        "_run_rules",
        new=AsyncMock(
            return_value={
                "evidence_facts": {},
                "reason_codes": [],
                "primary_action": "none",
            }
        ),
    ):
        # Patch evidence_repo to simulate "already exists"
        with patch.object(svc._evidence_repo, "get_by_hash", new=AsyncMock(return_value=fake_bundle)):
            req = EvidenceBuildRequest(
                plant_id=plant_id,
                user_id=uuid.uuid4(),
                question="test",
                intent="watering_question",
            )
            ctx, from_cache = await svc.build(req)

    assert from_cache is True
    assert len(ctx.evidence_hash) == 64


# ---------------------------------------------------------------------------
# EvidenceBuilderService: fresh build inserts bundle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_fresh_saves_bundle() -> None:
    from app.models.plant import Plant
    from app.services.evidence_builder import EvidenceBuilderService

    plant_id = uuid.uuid4()
    fake_plant = MagicMock(spec=Plant)
    fake_plant.id = plant_id
    fake_plant.species_profile_id = None

    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    async def fake_get(model, key):
        if model is Plant:
            return fake_plant
        return None

    session.get = fake_get

    empty_scalars = MagicMock()
    empty_scalars.scalars.return_value.all.return_value = []
    empty_scalars.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=empty_scalars)

    svc = EvidenceBuilderService(session)

    save_mock = AsyncMock(return_value=MagicMock())
    with (
        patch.object(
            svc,
            "_run_rules",
            new=AsyncMock(
                return_value={
                    "evidence_facts": {},
                    "reason_codes": [],
                    "primary_action": "none",
                }
            ),
        ),
        patch.object(svc._evidence_repo, "get_by_hash", new=AsyncMock(return_value=None)),
        patch.object(svc._evidence_repo, "save", save_mock),
    ):
        req = EvidenceBuildRequest(
            plant_id=plant_id,
            user_id=uuid.uuid4(),
            question="test",
            intent="watering_question",
        )
        ctx, from_cache = await svc.build(req)

    assert from_cache is False
    save_mock.assert_called_once()


# ---------------------------------------------------------------------------
# No forbidden imports
# ---------------------------------------------------------------------------


def test_evidence_builder_has_no_llm_or_prompt_imports() -> None:
    import app.services.evidence_builder as mod

    src = open(mod.__file__, encoding="utf-8").read()
    for forbidden in ("openai", "anthropic", "PromptBuilder", "torch"):
        assert forbidden not in src, f"Forbidden: {forbidden!r}"


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------


def test_migration_0006_exists() -> None:
    from pathlib import Path

    assert Path("alembic/versions/0006_ticket15_evidence_bundles.py").exists()


def test_migration_0006_has_evidence_bundles() -> None:
    from pathlib import Path

    src = Path("alembic/versions/0006_ticket15_evidence_bundles.py").read_text(encoding="utf-8")
    assert "evidence_bundles" in src
    assert "def upgrade" in src
    assert "def downgrade" in src
