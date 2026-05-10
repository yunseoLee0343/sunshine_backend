"""Plant Knowledge domain types — TICKET-014A.

Pure data containers. No DB I/O, no file I/O, no LLM.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PlantKnowledgeRow:
    """One parsed row from the Excel source file."""

    # --- identifiers
    nongsaro_id: str
    korean_name: str
    scientific_name: str | None
    common_name: str | None
    family: str | None
    origin: str | None

    # --- care requirements
    growth_temp_text: str | None     # raw text e.g. "18~24℃"
    light_requirement: str | None
    watering_frequency: str | None
    soil_type: str | None
    fertilizer_info: str | None

    # --- seasonal watering
    spring_watering: str | None
    summer_watering: str | None
    autumn_watering: str | None
    winter_watering: str | None

    # --- pests / diseases
    pest_text: str | None
    disease_text: str | None

    # --- visual traits
    leaf_color: str | None
    leaf_shape: str | None
    flower_color: str | None
    flower_season: str | None
    height_text: str | None          # raw text e.g. "30~60cm"

    # --- placement
    placement_locations: str | None
    is_toxic: bool | None
    toxicity_detail: str | None
    fragrance: str | None

    # --- source provenance
    source_row_number: int
    source_row_hash: str             # SHA-256 of the raw row


@dataclass
class IngestSummary:
    """Aggregated result of one ingestion run."""

    source_file: str
    total_rows: int = 0
    inserted: int = 0
    updated: int = 0
    ignored: int = 0
    errors: int = 0
    error_details: list[str] = field(default_factory=list)
