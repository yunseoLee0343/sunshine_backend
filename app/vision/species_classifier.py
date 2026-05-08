"""SpeciesClassifierPort — replaceable boundary for plant species recognition.

This module defines:
  - SpeciesCandidate: identification-only DTO. No disease/pest/health fields.
  - SpeciesClassifierPort: async Protocol that any concrete classifier must
    satisfy. Implementations may be a deterministic mock (Ticket 3) or, in a
    future ticket, a real vision model — the call site never changes.
"""

from typing import Protocol

from pydantic import BaseModel


class SpeciesCandidate(BaseModel):
    """A single species-identification result.

    Only species-identification fields are permitted. Any disease, pest,
    health, diagnosis, treatment, severity, or recommended-action field is
    out of scope for this port and must not be added.
    """

    label_ko: str
    label_en: str
    scientific_name: str | None
    confidence: float
    confidence_label: str
    source: str


class SpeciesClassifierPort(Protocol):
    """Port for species classification.

    image_ref is an opaque string. Implementations must NOT open files,
    fetch URLs, decode image bytes, or load model weights as a result of
    this call.
    """

    async def classify_species(
        self,
        image_ref: str,
        *,
        locale: str = "ko-KR",
        top_k: int = 3,
    ) -> list[SpeciesCandidate]: ...
