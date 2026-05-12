"""SpeciesCandidateService — TICKET-003 + T-003E.

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


def normalize_species_name(value: str | None) -> str:
    """Lowercase and collapse all internal whitespace.

    Examples:
        "Monstera deliciosa"       -> "monstera deliciosa"
        "  monstera   deliciosa "  -> "monstera deliciosa"
        "EPIPREMNUM AUREUM"        -> "epipremnum aureum"
    """
    if not value:
        return ""
    return " ".join(value.strip().lower().split())


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

        Lookup order (T-003E):
          1. exact scientific_name
          2. exact korean_name
          3. exact common_name / label_en
          4+5. case-insensitive + whitespace-normalised scientific_name
          6. case-insensitive common_name
          7. alias from metadata_json['aliases']
        """
        # Steps 1–3: exact matches
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

        # Steps 4+5: normalised scientific_name (case-insensitive + whitespace-collapsed)
        norm_sci = normalize_species_name(candidate.scientific_name)
        if norm_sci:
            profile = await self.species_repo.find_by_scientific_name_normalized(norm_sci)
            if profile is not None:
                return profile.id

        # Step 6: normalised common_name (case-insensitive)
        norm_common = normalize_species_name(candidate.label_en)
        if norm_common:
            profile = await self.species_repo.find_by_common_name_normalized(norm_common)
            if profile is not None:
                return profile.id

        # Step 7: alias lookup — try each unique non-empty normalised term in order
        for term in dict.fromkeys(
            filter(None, [norm_sci, normalize_species_name(candidate.label_ko), norm_common])
        ):
            profile = await self.species_repo.find_by_alias(term)
            if profile is not None:
                return profile.id

        return None
