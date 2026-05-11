"""Companion plant domain objects — TICKET-020.

All objects are frozen dataclasses (immutable). No DB, no LLM, no I/O.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class CompanionCandidate:
    """A plant species that is a candidate for companion planting.

    Thresholds define the plant's acceptable growing conditions.
    Any threshold field may be None when the data is unavailable.
    """

    species_id: uuid.UUID
    scientific_name: str
    common_name: str

    # Growing-condition thresholds (all optional — None = data unavailable)
    light_min_lux: float | None = None
    light_max_lux: float | None = None
    humidity_min_pct: float | None = None
    humidity_max_pct: float | None = None
    temperature_min_c: float | None = None
    temperature_max_c: float | None = None

    # Placement descriptors (informational, does not affect score)
    placement_tags: tuple[str, ...] = ()

    # Safety flags
    is_toxic: bool = False
    toxic_to_pets: bool = False
    toxic_to_children: bool = False


@dataclass(frozen=True)
class RoomEnvironment:
    """Observed growing environment in the user's room.

    Derived from the latest EnvironmentSnapshot. Each field may be None
    when the corresponding sensor reading is unavailable.
    """

    light_avg_lux: float | None = None
    humidity_avg_pct: float | None = None
    temperature_avg_c: float | None = None
    room_name: str | None = None  # free-form label, e.g. "거실", "창가"


@dataclass(frozen=True)
class CompatibilityResult:
    """Compatibility assessment between a candidate and the room environment."""

    candidate: CompanionCandidate
    score: float  # 0.0 – 1.0 (matched / assessed dimensions)
    assessed_dimensions: int  # how many dimensions had enough data to compare
    reasons: tuple[str, ...]  # human-readable match/mismatch explanations
    caution_notes: tuple[str, ...]  # safety warnings (toxicity, pets, children)
    is_compatible: bool  # True when assessed_dimensions > 0 and score >= 0.5
