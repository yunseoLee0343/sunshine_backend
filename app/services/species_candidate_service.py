"""SpeciesCandidateService — TICKET-003.

Calls a SpeciesClassifierPort (mock or, in the future, a real classifier)
and optionally resolves each candidate to a row in ``species_profiles``.

Strict boundaries — this service must NOT:
  - open ``image_ref`` as a file or URL
  - decode image bytes / EXIF
  - load model weights or download models
  - call torch / tensorflow / onnxruntime / openvino / opencv / Pillow
  - perform disease, pest, or health classification
  - write to plants / plant_characters / sensor_readings / chat / llm_runs / etc.
"""

from app.repositories.species_repository import SpeciesRepository
from app.schemas.plants import SpeciesCandidateItem, SpeciesCandidatesResponse
from app.vision.species_classifier import SpeciesCandidate, SpeciesClassifierPort


class SpeciesCandidateService:
    def __init__(
        self,
        classifier: SpeciesClassifierPort,
        species_repo: SpeciesRepository,
    ) -> None:
        self.classifier = classifier
        self.species_repo = species_repo

    async def list_candidates(
        self,
        image_ref: str | None,
        *,
        locale: str = "ko-KR",
        top_k: int = 3,
    ) -> SpeciesCandidatesResponse:
        # image_ref is opaque — never opened. Treat None as empty string so
        # the classifier still produces its deterministic fallback.
        ref = image_ref or ""
        candidates = await self.classifier.classify_species(ref, locale=locale, top_k=top_k)

        items: list[SpeciesCandidateItem] = []
        for c in candidates:
            profile_id = await self._resolve_species_profile_id(c)
            items.append(
                SpeciesCandidateItem(
                    species_profile_id=profile_id,
                    label_ko=c.label_ko,
                    label_en=c.label_en,
                    scientific_name=c.scientific_name,
                    confidence=c.confidence,
                    confidence_label=c.confidence_label,
                    source=c.source,
                )
            )
        return SpeciesCandidatesResponse(candidates=items)

    async def _resolve_species_profile_id(self, candidate: SpeciesCandidate):
        """Best-effort match to species_profiles. Returns None on no match.

        Lookup order: scientific_name → korean_name → common_name (label_en).
        A missing match is not an error.
        """
        if candidate.scientific_name:
            profile = await self.species_repo.find_by_scientific_name(candidate.scientific_name)
            if profile is not None:
                return profile.id

        if candidate.label_ko:
            profile = await self.species_repo.find_by_korean_name(candidate.label_ko)
            if profile is not None:
                return profile.id

        if candidate.label_en:
            profile = await self.species_repo.find_by_common_name(candidate.label_en)
            if profile is not None:
                return profile.id

        return None
