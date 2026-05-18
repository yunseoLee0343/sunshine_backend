"""SpeciesCandidateService — TICKET-003 + T-003E + T-060A2.

Calls a SpeciesClassifierPort (mock or, in the future, a real classifier)
and resolves each candidate exclusively to Excel-catalog rows in species_profiles
(catalog_allowed=true, source=전체식물_분류정보_v1_updated_7_2.xlsx).

Strict boundaries — this service must NOT:
  - open ``image_ref`` as a file or URL
  - decode image bytes / EXIF
  - load model weights or download models
  - call torch / tensorflow / onnxruntime / openvino / opencv / Pillow
  - perform disease, pest, or health classification
  - write to plants / plant_characters / sensor_readings / chat / llm_runs / etc.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.species_profile import SpeciesProfile
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


@dataclass
class _CatalogMatch:
    profile: SpeciesProfile
    match_reason: str


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
            match = await self._resolve_catalog_match(c)
            if match is not None:
                items.append(
                    SpeciesCandidateItem(
                        species_profile_id=match.profile.id,
                        label_ko=c.label_ko,
                        label_en=c.label_en,
                        scientific_name=match.profile.scientific_name,
                        confidence=c.confidence,
                        confidence_label=c.confidence_label,
                        source=c.source,
                        display_name=match.profile.korean_name,
                        catalog_matched=True,
                        raw_label=c.scientific_name,
                        match_reason=match.match_reason,
                    )
                )
            else:
                items.append(
                    SpeciesCandidateItem(
                        species_profile_id=None,
                        label_ko=c.label_ko,
                        label_en=c.label_en,
                        scientific_name=c.scientific_name,
                        confidence=c.confidence,
                        confidence_label=c.confidence_label,
                        source=c.source,
                        display_name=None,
                        catalog_matched=False,
                        raw_label=c.scientific_name,
                        match_reason="unmatched",
                    )
                )
        return SpeciesCandidatesResponse(candidates=items)

    async def _resolve_catalog_match(self, candidate: SpeciesCandidate) -> _CatalogMatch | None:
        """Resolve classifier output to an Excel-catalog species_profiles row.

        All lookups are restricted to rows where:
            metadata_json->>'catalog_allowed' = 'true'
            AND metadata_json->>'source' = '전체식물_분류정보_v1_updated_7_2.xlsx'

        Match order (TICKET-060A2):
          1. exact scientific_name
          2. exact korean_name
          3. exact common_name / label_en
          4+5. normalised scientific_name (case + whitespace)
          6. normalised common_name
          7. alias from metadata_json['aliases']
        """
        # Step 1: exact scientific_name
        if candidate.scientific_name:
            profile = await self.species_repo.find_catalog_by_scientific_name(candidate.scientific_name)
            if profile is not None:
                return _CatalogMatch(profile, "scientific_name_exact")

        # Step 2: exact korean_name
        if candidate.label_ko:
            profile = await self.species_repo.find_catalog_by_korean_name(candidate.label_ko)
            if profile is not None:
                return _CatalogMatch(profile, "korean_name_exact")

        # Step 3: exact common_name / label_en
        if candidate.label_en:
            profile = await self.species_repo.find_catalog_by_common_name(candidate.label_en)
            if profile is not None:
                return _CatalogMatch(profile, "common_name_exact")

        # Steps 4+5: normalised scientific_name
        norm_sci = normalize_species_name(candidate.scientific_name)
        if norm_sci:
            profile = await self.species_repo.find_catalog_by_scientific_name_normalized(norm_sci)
            if profile is not None:
                return _CatalogMatch(profile, "normalized")

        # Step 6: normalised common_name
        norm_common = normalize_species_name(candidate.label_en)
        if norm_common:
            profile = await self.species_repo.find_catalog_by_common_name_normalized(norm_common)
            if profile is not None:
                return _CatalogMatch(profile, "normalized")

        # Step 7: alias lookup — try each unique non-empty normalised term in order
        for term in dict.fromkeys(
            filter(None, [norm_sci, normalize_species_name(candidate.label_ko), norm_common])
        ):
            profile = await self.species_repo.find_catalog_by_alias(term)
            if profile is not None:
                return _CatalogMatch(profile, "alias")

        return None
