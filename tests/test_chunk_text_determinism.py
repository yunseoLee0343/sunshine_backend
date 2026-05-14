"""TICKET-047 — Chunk text determinism tests."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from app.domain.chunk import CHUNK_KINDS
from app.embedding.chunk_builder import _hash, build_all_chunks
from app.models.plant_knowledge_entry import PlantKnowledgeEntry


def _entry(**kwargs) -> PlantKnowledgeEntry:
    e = MagicMock(spec=PlantKnowledgeEntry)
    e.id = kwargs.get("id", uuid.uuid4())
    e.korean_name = kwargs.get("korean_name", "몬스테라")
    e.scientific_name = kwargs.get("scientific_name", "Monstera deliciosa")
    e.common_name = kwargs.get("common_name", None)
    e.family = kwargs.get("family", None)
    e.origin = kwargs.get("origin", None)
    return e


def test_same_input_produces_same_chunks() -> None:
    eid = uuid.uuid4()
    e = _entry(id=eid)
    chunks1 = build_all_chunks(e, None, None, None, None, None)
    chunks2 = build_all_chunks(e, None, None, None, None, None)
    for c1, c2 in zip(chunks1, chunks2):
        assert c1.text == c2.text
        assert c1.text_hash == c2.text_hash


def test_text_hash_is_sha256_of_text() -> None:
    e = _entry()
    chunks = build_all_chunks(e, None, None, None, None, None)
    for chunk in chunks:
        assert chunk.text_hash == _hash(chunk.text)


def test_at_most_six_chunks_per_plant() -> None:
    e = _entry()
    chunks = build_all_chunks(e, None, None, None, None, None)
    assert len(chunks) <= 6


def test_exactly_six_chunks_produced() -> None:
    e = _entry()
    chunks = build_all_chunks(e, None, None, None, None, None)
    assert len(chunks) == 6


def test_all_chunk_kinds_present() -> None:
    e = _entry()
    chunks = build_all_chunks(e, None, None, None, None, None)
    kinds = {c.chunk_kind for c in chunks}
    assert kinds == set(CHUNK_KINDS)


def test_text_changes_when_korean_name_changes() -> None:
    e1 = _entry(korean_name="몬스테라")
    e2 = _entry(korean_name="산세비에리아")
    chunks1 = build_all_chunks(e1, None, None, None, None, None)
    chunks2 = build_all_chunks(e2, None, None, None, None, None)
    for c1, c2 in zip(chunks1, chunks2):
        assert c1.text != c2.text


def test_plant_knowledge_id_propagated() -> None:
    eid = uuid.uuid4()
    e = _entry(id=eid)
    chunks = build_all_chunks(e, None, None, None, None, None)
    for chunk in chunks:
        assert chunk.plant_knowledge_id == eid
