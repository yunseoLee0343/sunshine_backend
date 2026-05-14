"""TICKET-047 — ChunkKind schema tests."""

from __future__ import annotations

from app.domain.chunk import CHUNK_KINDS, ChunkKind

_EXPECTED_KINDS = frozenset(
    [
        "identity",
        "visual_trait",
        "placement",
        "care_requirement",
        "seasonal_watering",
        "pest_reference",
    ]
)


def test_chunk_kinds_tuple_equals_allowed_set() -> None:
    assert set(CHUNK_KINDS) == _EXPECTED_KINDS


def test_chunk_kinds_has_exactly_six() -> None:
    assert len(CHUNK_KINDS) == 6


def test_chunk_kinds_no_duplicates() -> None:
    assert len(CHUNK_KINDS) == len(set(CHUNK_KINDS))


def test_chunk_kind_literal_contains_all_six() -> None:
    import typing

    args = typing.get_args(ChunkKind)
    assert set(args) == _EXPECTED_KINDS


def test_no_extra_chunk_kind_added() -> None:
    """Guard against accidentally adding a 7th kind."""
    unexpected = set(CHUNK_KINDS) - _EXPECTED_KINDS
    assert not unexpected, f"Unexpected chunk kinds: {unexpected}"
