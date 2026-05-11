"""VisionPort Protocol and result schema — TICKET-030."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class VisionAnalysisResult:
    visual_symptoms: list[str]
    detected_objects: list[str]
    confidence: float
    observation_note: str
    source: str
    suggests_pest: bool = False


@runtime_checkable
class VisionPort(Protocol):
    async def analyze(
        self, image_uri: str, *, locale: str = "ko-KR"
    ) -> VisionAnalysisResult: ...
