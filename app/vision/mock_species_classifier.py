"""MockSpeciesClassifier — catalog-aligned deterministic mock.

Returns a fixed set of catalog candidate guesses for *any* image_ref,
regardless of its content. No substring matching, no file I/O, no network.

Candidates are chosen so they resolve through the Excel-only catalog resolver
(TICKET-060A2) once the species catalog has been imported (TICKET-060A0).

This prevents UUID upload refs from producing a fallback-only response during
MVP, without performing any real image inference.
"""

from app.vision.species_classifier import SpeciesCandidate

_CATALOG_CANDIDATES: tuple[SpeciesCandidate, ...] = (
    SpeciesCandidate(
        label_ko="몬스테라 델리시오사",
        label_en="Monstera",
        scientific_name="Monstera deliciosa",
        confidence=0.60,
        confidence_label="medium",
        source="catalog_mock",
    ),
    SpeciesCandidate(
        label_ko="스킨답서스",
        label_en="Pothos",
        scientific_name="Epipremnum aureum",
        confidence=0.50,
        confidence_label="medium",
        source="catalog_mock",
    ),
    SpeciesCandidate(
        label_ko="스파티필름",
        label_en="Peace Lily",
        scientific_name="Spathiphyllum wallisii",
        confidence=0.45,
        confidence_label="low",
        source="catalog_mock",
    ),
)


class MockSpeciesClassifier:
    """Deterministic mock implementation of SpeciesClassifierPort.

    Returns the same catalog-aligned candidate list for any image_ref.
    """

    async def classify_species(
        self,
        image_ref: str,
        *,
        locale: str = "ko-KR",
        top_k: int = 3,
    ) -> list[SpeciesCandidate]:
        return list(_CATALOG_CANDIDATES[: max(1, top_k)])
