"""TICKET-048 — RAG layer ↔ chunk kind mapping tests."""

from __future__ import annotations

from app.domain.retrieval import ALL_RAG_LAYERS, RAG_LAYER_TO_CHUNK_KINDS
from app.retrieval.hybrid_retriever import _chunk_kind_to_rag_layer


def test_all_rag_layers_present_in_mapping() -> None:
    for layer in ALL_RAG_LAYERS:
        assert layer in RAG_LAYER_TO_CHUNK_KINDS


def test_species_profile_maps_to_identity() -> None:
    assert "identity" in RAG_LAYER_TO_CHUNK_KINDS["species_profile"]


def test_care_knowledge_maps_to_seasonal_watering() -> None:
    assert "seasonal_watering" in RAG_LAYER_TO_CHUNK_KINDS["care_knowledge"]


def test_pest_disease_reference_maps_to_pest_reference() -> None:
    assert RAG_LAYER_TO_CHUNK_KINDS["pest_disease_reference"] == ("pest_reference",)


def test_chunk_kind_to_rag_layer_identity() -> None:
    assert _chunk_kind_to_rag_layer("identity") == "species_profile"


def test_chunk_kind_to_rag_layer_seasonal_watering() -> None:
    assert _chunk_kind_to_rag_layer("seasonal_watering") == "care_knowledge"


def test_chunk_kind_to_rag_layer_pest_reference() -> None:
    assert _chunk_kind_to_rag_layer("pest_reference") == "pest_disease_reference"


def test_chunk_kind_to_rag_layer_unknown_returns_none() -> None:
    assert _chunk_kind_to_rag_layer("nonexistent_kind") is None


def test_no_chunk_kind_belongs_to_multiple_layers() -> None:
    seen: dict[str, str] = {}
    for layer, kinds in RAG_LAYER_TO_CHUNK_KINDS.items():
        for kind in kinds:
            assert kind not in seen, f"{kind!r} appears in both {seen[kind]!r} and {layer!r}"
            seen[kind] = layer
