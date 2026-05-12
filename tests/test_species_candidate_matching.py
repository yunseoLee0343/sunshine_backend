"""T-003E — SpeciesCandidateService matching quality tests."""
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


def _fake_profile(profile_id: uuid.UUID | None = None) -> MagicMock:
    p = MagicMock()
    p.id = profile_id or uuid.UUID("00000000-0000-0000-0000-000000000001")
    return p


def _null_repo() -> MagicMock:
    repo = MagicMock()
    repo.find_by_scientific_name = AsyncMock(return_value=None)
    repo.find_by_korean_name = AsyncMock(return_value=None)
    repo.find_by_common_name = AsyncMock(return_value=None)
    repo.find_by_scientific_name_normalized = AsyncMock(return_value=None)
    repo.find_by_common_name_normalized = AsyncMock(return_value=None)
    repo.find_by_alias = AsyncMock(return_value=None)
    return repo


def _run(svc: SpeciesCandidateService, image_ref: str = "mock/x.jpg", top_k: int = 3):
    return asyncio.run(svc.list_candidates(image_ref, locale="ko-KR", top_k=top_k))


def _svc(candidates: list[SpeciesCandidate], repo: MagicMock) -> SpeciesCandidateService:
    classifier = MagicMock()
    classifier.classify_species = AsyncMock(return_value=candidates)
    return SpeciesCandidateService(classifier=classifier, species_repo=repo)


# ---------------------------------------------------------------------------
# 1. Exact scientific_name match
# ---------------------------------------------------------------------------


def test_exact_scientific_name_match() -> None:
    profile = _fake_profile()
    repo = _null_repo()
    repo.find_by_scientific_name = AsyncMock(return_value=profile)

    resp = _run(_svc([_candidate()], repo), top_k=1)
    assert resp.candidates[0].species_profile_id == profile.id


# ---------------------------------------------------------------------------
# 2. Case-insensitive scientific_name match (step 4)
# ---------------------------------------------------------------------------


def test_case_insensitive_scientific_name_match() -> None:
    profile = _fake_profile()
    repo = _null_repo()
    # Step 1 (exact) misses; step 4 (normalized) hits
    repo.find_by_scientific_name_normalized = AsyncMock(return_value=profile)

    resp = _run(_svc([_candidate(scientific_name="MONSTERA DELICIOSA")], repo), top_k=1)
    assert resp.candidates[0].species_profile_id == profile.id


# ---------------------------------------------------------------------------
# 3. Whitespace-normalized scientific_name match (step 5)
# ---------------------------------------------------------------------------


def test_whitespace_normalized_scientific_name_match() -> None:
    profile = _fake_profile()
    repo = _null_repo()
    repo.find_by_scientific_name_normalized = AsyncMock(return_value=profile)

    resp = _run(_svc([_candidate(scientific_name="  Monstera   deliciosa ")], repo), top_k=1)
    assert resp.candidates[0].species_profile_id == profile.id


# ---------------------------------------------------------------------------
# 4. Korean name match (step 2)
# ---------------------------------------------------------------------------


def test_korean_name_match() -> None:
    profile = _fake_profile()
    repo = _null_repo()
    repo.find_by_korean_name = AsyncMock(return_value=profile)

    c = _candidate(scientific_name=None)
    resp = _run(_svc([c], repo), top_k=1)
    assert resp.candidates[0].species_profile_id == profile.id


# ---------------------------------------------------------------------------
# 5. Common name match (step 3)
# ---------------------------------------------------------------------------


def test_common_name_match() -> None:
    profile = _fake_profile()
    repo = _null_repo()
    repo.find_by_common_name = AsyncMock(return_value=profile)

    # Skip sci name (None) and label_ko (empty → falsy) so we reach step 3
    c = _candidate(scientific_name=None, label_ko="")
    resp = _run(_svc([c], repo), top_k=1)
    assert resp.candidates[0].species_profile_id == profile.id


# ---------------------------------------------------------------------------
# 6. Alias match (step 7)
# ---------------------------------------------------------------------------


def test_alias_match() -> None:
    profile = _fake_profile()
    repo = _null_repo()
    repo.find_by_alias = AsyncMock(return_value=profile)

    resp = _run(_svc([_candidate()], repo), top_k=1)
    assert resp.candidates[0].species_profile_id == profile.id


# ---------------------------------------------------------------------------
# 7. Unknown candidate → species_profile_id = null
# ---------------------------------------------------------------------------


def test_unknown_candidate_returns_null_species_profile_id() -> None:
    repo = _null_repo()
    c = _candidate(scientific_name=None, label_ko="", label_en="")

    resp = _run(_svc([c], repo), top_k=1)
    assert resp.candidates[0].species_profile_id is None


# ---------------------------------------------------------------------------
# 8. Multiple candidates preserve classifier order
# ---------------------------------------------------------------------------


def test_multiple_candidates_preserve_classifier_order() -> None:
    profile_a = _fake_profile(uuid.UUID("00000000-0000-0000-0000-000000000001"))
    profile_b = _fake_profile(uuid.UUID("00000000-0000-0000-0000-000000000002"))

    repo = _null_repo()

    async def _find_by_sci(name: str):
        if name == "Plant A":
            return profile_a
        if name == "Plant B":
            return profile_b
        return None

    repo.find_by_scientific_name = _find_by_sci

    candidates = [
        _candidate(scientific_name="Plant A", label_ko="A", label_en="A"),
        _candidate(scientific_name="Plant B", label_ko="B", label_en="B"),
    ]
    resp = _run(_svc(candidates, repo), top_k=2)
    assert resp.candidates[0].species_profile_id == profile_a.id
    assert resp.candidates[1].species_profile_id == profile_b.id
