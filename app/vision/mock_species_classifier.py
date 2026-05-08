"""MockSpeciesClassifier — deterministic, dependency-free species mock.

The mock returns a fixed candidate list based on simple substring matching
against the opaque ``image_ref`` string. No randomness, no time-dependence,
no file I/O, no network access, no model loading.

Mapping (case-insensitive substring match):
  monstera / 몬스테라     -> Monstera deliciosa
  pothos / 스킨답서스      -> Epipremnum aureum
  philodendron / 필로덴드론 -> Philodendron hederaceum
  otherwise                -> "잘 모르겠어요" fallback
"""

from app.vision.species_classifier import SpeciesCandidate

_FALLBACK = SpeciesCandidate(
    label_ko="잘 모르겠어요",
    label_en="Unknown",
    scientific_name=None,
    confidence=0.0,
    confidence_label="low",
    source="mock",
)

_MONSTERA = SpeciesCandidate(
    label_ko="몬스테라",
    label_en="Monstera",
    scientific_name="Monstera deliciosa",
    confidence=0.91,
    confidence_label="high",
    source="mock",
)

_POTHOS = SpeciesCandidate(
    label_ko="스킨답서스",
    label_en="Pothos",
    scientific_name="Epipremnum aureum",
    confidence=0.88,
    confidence_label="high",
    source="mock",
)

_PHILODENDRON = SpeciesCandidate(
    label_ko="필로덴드론",
    label_en="Philodendron",
    scientific_name="Philodendron hederaceum",
    confidence=0.84,
    confidence_label="medium",
    source="mock",
)

# Order matters: the first matching keyword wins for the primary candidate.
_RULES: tuple[tuple[tuple[str, ...], SpeciesCandidate], ...] = (
    (("monstera", "몬스테라"), _MONSTERA),
    (("pothos", "스킨답서스"), _POTHOS),
    (("philodendron", "필로덴드론"), _PHILODENDRON),
)


class MockSpeciesClassifier:
    """Deterministic mock implementation of SpeciesClassifierPort."""

    async def classify_species(
        self,
        image_ref: str,
        *,
        locale: str = "ko-KR",
        top_k: int = 3,
    ) -> list[SpeciesCandidate]:
        haystack = image_ref.lower()
        primary: SpeciesCandidate | None = None
        for keywords, candidate in _RULES:
            if any(kw.lower() in haystack for kw in keywords):
                primary = candidate
                break

        if primary is None:
            return [_FALLBACK][: max(1, top_k)]

        # Deterministic ordering: matched candidate first, then the others
        # in declaration order. Ensures stable output for the same image_ref.
        ordered: list[SpeciesCandidate] = [primary]
        for _, candidate in _RULES:
            if candidate is not primary:
                ordered.append(candidate)
        return ordered[: max(1, top_k)]
