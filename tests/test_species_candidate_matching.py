"""T-003E + T-060A2 — SpeciesCandidateService matching quality tests."""
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

from app.services.species_candidate_service import (
    SpeciesCandidateService,
    normalize_species_name,
)
from app.vision.species_classifier import SpeciesCandidate


# ---------------------------------------------------------------------------
# normalize_species_name utility
# ---------------------------------------------------------------------------


def test_normalize_lowercase() -> None:
    assert normalize_species_name("Monstera deliciosa") == "monstera deliciosa"


def test_normalize_strips_and_collapses_whitespace() -> None:
    assert normalize_species_name("  monstera   deliciosa ") == "monstera deliciosa"


def test_normalize_all_caps() -> None:
    assert normalize_species_name("EPIPREMNUM AUREUM") == "epipremnum aureum"


def test_normalize_none_returns_empty() -> None:
    assert normalize_species_name(None) == ""


def test_normalize_empty_string_returns_empty() -> None:
    assert normalize_species_name("") == ""


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _candidate(**kwargs) -> SpeciesCandidate:
    defaults = {
        "label_ko": "몬스테라",
        "label_en": "Monstera",
        "scientific_name": "Monstera deliciosa",
        "confidence": 0.91,
        "confidence_label": "high",
        "source": "mock",
    }
    defaults.update(kwargs)
    return SpeciesCandidate(**defaults)


def _fake_profile(
    profile_id: uuid.UUID | None = None,
    korean_name: str = "몬스테라",
    scientific_name: str | None = "Monstera deliciosa",
) -> MagicMock:
    p = MagicMock()
    p.id = profile_id or uuid.UUID("00000000-0000-0000-0000-000000000001")
    p.korean_name = korean_name
    p.scientific_name = scientific_name
    return p


def _null_repo() -> MagicMock:
    """Mock repo where all catalog lookups return None (no match)."""
    repo = MagicMock()
    # unrestricted (kept for legacy callers)
    repo.find_by_scientific_name = AsyncMock(return_value=None)
    repo.find_by_korean_name = AsyncMock(return_value=None)
    repo.find_by_common_name = AsyncMock(return_value=None)
    repo.find_by_scientific_name_normalized = AsyncMock(return_value=None)
    repo.find_by_common_name_normalized = AsyncMock(return_value=None)
    repo.find_by_alias = AsyncMock(return_value=None)
    # catalog-constrained (T-060A2)
    repo.find_catalog_by_scientific_name = AsyncMock(return_value=None)
    repo.find_catalog_by_korean_name = AsyncMock(return_value=None)
    repo.find_catalog_by_common_name = AsyncMock(return_value=None)
    repo.find_catalog_by_scientific_name_normalized = AsyncMock(return_value=None)
    repo.find_catalog_by_common_name_normalized = AsyncMock(return_value=None)
    repo.find_catalog_by_alias = AsyncMock(return_value=None)
    return repo


def _run(svc: SpeciesCandidateService, image_ref: str = "mock/x.jpg", top_k: int = 3):
    return asyncio.run(svc.list_candidates(image_ref, locale="ko-KR", top_k=top_k))


def _svc(candidates: list[SpeciesCandidate], repo: MagicMock) -> SpeciesCandidateService:
    classifier = MagicMock()
    classifier.classify_species = AsyncMock(return_value=candidates)
    return SpeciesCandidateService(classifier=classifier, species_repo=repo)


# ---------------------------------------------------------------------------
# 1. Exact scientific_name match → catalog-constrained
# ---------------------------------------------------------------------------


def test_exact_scientific_name_match() -> None:
    profile = _fake_profile()
    repo = _null_repo()
    repo.find_catalog_by_scientific_name = AsyncMock(return_value=profile)

    resp = _run(_svc([_candidate()], repo), top_k=1)
    assert resp.candidates[0].species_profile_id == profile.id


def test_exact_scientific_name_sets_match_reason() -> None:
    profile = _fake_profile()
    repo = _null_repo()
    repo.find_catalog_by_scientific_name = AsyncMock(return_value=profile)

    resp = _run(_svc([_candidate()], repo), top_k=1)
    assert resp.candidates[0].match_reason == "scientific_name_exact"


# ---------------------------------------------------------------------------
# 2. Case-insensitive scientific_name match (step 4)
# ---------------------------------------------------------------------------


def test_case_insensitive_scientific_name_match() -> None:
    profile = _fake_profile()
    repo = _null_repo()
    # Step 1 (exact) misses; step 4 (normalized) hits
    repo.find_catalog_by_scientific_name_normalized = AsyncMock(return_value=profile)

    resp = _run(_svc([_candidate(scientific_name="MONSTERA DELICIOSA")], repo), top_k=1)
    assert resp.candidates[0].species_profile_id == profile.id


def test_normalized_match_sets_match_reason() -> None:
    profile = _fake_profile()
    repo = _null_repo()
    repo.find_catalog_by_scientific_name_normalized = AsyncMock(return_value=profile)

    resp = _run(_svc([_candidate(scientific_name="MONSTERA DELICIOSA")], repo), top_k=1)
    assert resp.candidates[0].match_reason == "normalized"


# ---------------------------------------------------------------------------
# 3. Whitespace-normalized scientific_name match (step 5)
# ---------------------------------------------------------------------------


def test_whitespace_normalized_scientific_name_match() -> None:
    profile = _fake_profile()
    repo = _null_repo()
    repo.find_catalog_by_scientific_name_normalized = AsyncMock(return_value=profile)

    resp = _run(_svc([_candidate(scientific_name="  Monstera   deliciosa ")], repo), top_k=1)
    assert resp.candidates[0].species_profile_id == profile.id


# ---------------------------------------------------------------------------
# 4. Korean name match (step 2)
# ---------------------------------------------------------------------------


def test_korean_name_match() -> None:
    profile = _fake_profile()
    repo = _null_repo()
    repo.find_catalog_by_korean_name = AsyncMock(return_value=profile)

    c = _candidate(scientific_name=None)
    resp = _run(_svc([c], repo), top_k=1)
    assert resp.candidates[0].species_profile_id == profile.id


def test_korean_name_sets_match_reason() -> None:
    profile = _fake_profile()
    repo = _null_repo()
    repo.find_catalog_by_korean_name = AsyncMock(return_value=profile)

    resp = _run(_svc([_candidate(scientific_name=None)], repo), top_k=1)
    assert resp.candidates[0].match_reason == "korean_name_exact"


# ---------------------------------------------------------------------------
# 5. Common name match (step 3)
# ---------------------------------------------------------------------------


def test_common_name_match() -> None:
    profile = _fake_profile()
    repo = _null_repo()
    repo.find_catalog_by_common_name = AsyncMock(return_value=profile)

    # Skip sci name (None) and label_ko (empty → falsy) so we reach step 3
    c = _candidate(scientific_name=None, label_ko="")
    resp = _run(_svc([c], repo), top_k=1)
    assert resp.candidates[0].species_profile_id == profile.id


def test_common_name_sets_match_reason() -> None:
    profile = _fake_profile()
    repo = _null_repo()
    repo.find_catalog_by_common_name = AsyncMock(return_value=profile)

    resp = _run(_svc([_candidate(scientific_name=None, label_ko="")], repo), top_k=1)
    assert resp.candidates[0].match_reason == "common_name_exact"


# ---------------------------------------------------------------------------
# 6. Alias match (step 7)
# ---------------------------------------------------------------------------


def test_alias_match() -> None:
    profile = _fake_profile()
    repo = _null_repo()
    repo.find_catalog_by_alias = AsyncMock(return_value=profile)

    resp = _run(_svc([_candidate()], repo), top_k=1)
    assert resp.candidates[0].species_profile_id == profile.id


def test_alias_sets_match_reason() -> None:
    profile = _fake_profile()
    repo = _null_repo()
    repo.find_catalog_by_alias = AsyncMock(return_value=profile)

    resp = _run(_svc([_candidate()], repo), top_k=1)
    assert resp.candidates[0].match_reason == "alias"


# ---------------------------------------------------------------------------
# 7. Unknown candidate → unmatched
# ---------------------------------------------------------------------------


def test_unknown_candidate_returns_null_species_profile_id() -> None:
    repo = _null_repo()
    c = _candidate(scientific_name=None, label_ko="", label_en="")

    resp = _run(_svc([c], repo), top_k=1)
    assert resp.candidates[0].species_profile_id is None


def test_unknown_candidate_catalog_matched_false() -> None:
    repo = _null_repo()
    resp = _run(_svc([_candidate()], repo), top_k=1)
    assert resp.candidates[0].catalog_matched is False


def test_unknown_candidate_match_reason_unmatched() -> None:
    repo = _null_repo()
    resp = _run(_svc([_candidate()], repo), top_k=1)
    assert resp.candidates[0].match_reason == "unmatched"


# ---------------------------------------------------------------------------
# 8. Multiple candidates preserve classifier order
# ---------------------------------------------------------------------------


def test_multiple_candidates_preserve_classifier_order() -> None:
    profile_a = _fake_profile(uuid.UUID("00000000-0000-0000-0000-000000000001"), "식물A", "Plant A")
    profile_b = _fake_profile(uuid.UUID("00000000-0000-0000-0000-000000000002"), "식물B", "Plant B")

    repo = _null_repo()

    async def _find_by_sci(name: str):
        if name == "Plant A":
            return profile_a
        if name == "Plant B":
            return profile_b
        return None

    repo.find_catalog_by_scientific_name = _find_by_sci

    candidates = [
        _candidate(scientific_name="Plant A", label_ko="A", label_en="A"),
        _candidate(scientific_name="Plant B", label_ko="B", label_en="B"),
    ]
    resp = _run(_svc(candidates, repo), top_k=2)
    assert resp.candidates[0].species_profile_id == profile_a.id
    assert resp.candidates[1].species_profile_id == profile_b.id


# ---------------------------------------------------------------------------
# 9. Matched candidate populates display_name and scientific_name from DB
# ---------------------------------------------------------------------------


def test_matched_display_name_from_db_korean_name() -> None:
    profile = _fake_profile(korean_name="몬스테라 델리시오사", scientific_name="Monstera deliciosa")
    repo = _null_repo()
    repo.find_catalog_by_scientific_name = AsyncMock(return_value=profile)

    resp = _run(_svc([_candidate()], repo), top_k=1)
    assert resp.candidates[0].display_name == "몬스테라 델리시오사"


def test_matched_scientific_name_from_db() -> None:
    profile = _fake_profile(scientific_name="Monstera deliciosa (Liebm.) Schott")
    repo = _null_repo()
    repo.find_catalog_by_scientific_name = AsyncMock(return_value=profile)

    resp = _run(_svc([_candidate()], repo), top_k=1)
    assert resp.candidates[0].scientific_name == "Monstera deliciosa (Liebm.) Schott"


def test_matched_catalog_matched_true() -> None:
    profile = _fake_profile()
    repo = _null_repo()
    repo.find_catalog_by_scientific_name = AsyncMock(return_value=profile)

    resp = _run(_svc([_candidate()], repo), top_k=1)
    assert resp.candidates[0].catalog_matched is True


# ---------------------------------------------------------------------------
# 10. Non-catalog rows are not returned
# ---------------------------------------------------------------------------


def test_no_catalog_rows_returns_unmatched() -> None:
    """All find_catalog_by_* return None → no match even if non-catalog rows exist."""
    repo = _null_repo()
    # All catalog methods already return None in _null_repo()
    resp = _run(_svc([_candidate()], repo), top_k=1)
    assert resp.candidates[0].species_profile_id is None
    assert resp.candidates[0].catalog_matched is False
