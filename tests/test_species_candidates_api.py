"""TICKET-003 — POST /plants/species-candidates API tests.

Uses FastAPI dependency overrides for the classifier port and patches the
SpeciesRepository so no live DB is required.
"""

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.plants import get_session, get_species_classifier
from app.main import app
from app.vision.mock_species_classifier import MockSpeciesClassifier


async def _post(path: str, body: dict) -> tuple[int, dict]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post(path, json=body)
    return r.status_code, r.json()


async def _fake_session_dep():
    # The endpoint passes the session into SpeciesRepository(session); we
    # patch the repo methods so the session is never actually used.
    yield MagicMock()


def _setup_overrides() -> None:
    app.dependency_overrides[get_species_classifier] = lambda: MockSpeciesClassifier()
    app.dependency_overrides[get_session] = _fake_session_dep


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _patch_new_repo_methods():
    """Patch the T-003E repo methods so existing tests don't break."""
    base = "app.services.species_candidate_service.SpeciesRepository"
    with (
        patch(f"{base}.find_by_scientific_name_normalized", new=AsyncMock(return_value=None)),
        patch(f"{base}.find_by_common_name_normalized", new=AsyncMock(return_value=None)),
        patch(f"{base}.find_by_alias", new=AsyncMock(return_value=None)),
    ):
        yield


# ---------------------------------------------------------------------------
# Known species
# ---------------------------------------------------------------------------


def test_monstera_returns_candidates() -> None:
    _setup_overrides()
    try:
        with (
            patch(
                "app.services.species_candidate_service.SpeciesRepository.find_by_scientific_name",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.services.species_candidate_service.SpeciesRepository.find_by_korean_name",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.services.species_candidate_service.SpeciesRepository.find_by_common_name",
                new=AsyncMock(return_value=None),
            ),
        ):
            status, body = asyncio.run(
                _post(
                    "/plants/species-candidates",
                    {
                        "user_id": str(uuid.uuid4()),
                        "image_ref": "uploads/mock/monstera.jpg",
                        "locale": "ko-KR",
                        "top_k": 3,
                    },
                )
            )
    finally:
        _clear_overrides()

    assert status == 200
    assert "candidates" in body
    assert len(body["candidates"]) >= 1
    first = body["candidates"][0]
    assert first["label_ko"] == "몬스테라"
    assert first["label_en"] == "Monstera"
    assert first["scientific_name"] == "Monstera deliciosa"
    assert first["confidence"] == 0.91
    assert first["confidence_label"] == "high"
    assert first["source"] == "mock"
    assert "species_profile_id" in first
    assert first["species_profile_id"] is None  # no DB match


def test_same_request_same_response() -> None:
    _setup_overrides()
    payload = {
        "user_id": str(uuid.uuid4()),
        "image_ref": "uploads/mock/monstera.jpg",
        "locale": "ko-KR",
        "top_k": 3,
    }
    try:
        with (
            patch(
                "app.services.species_candidate_service.SpeciesRepository.find_by_scientific_name",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.services.species_candidate_service.SpeciesRepository.find_by_korean_name",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.services.species_candidate_service.SpeciesRepository.find_by_common_name",
                new=AsyncMock(return_value=None),
            ),
        ):
            _, body_a = asyncio.run(_post("/plants/species-candidates", payload))
            _, body_b = asyncio.run(_post("/plants/species-candidates", payload))
    finally:
        _clear_overrides()

    assert body_a == body_b


def test_unknown_image_ref_returns_fallback() -> None:
    _setup_overrides()
    try:
        with (
            patch(
                "app.services.species_candidate_service.SpeciesRepository.find_by_scientific_name",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.services.species_candidate_service.SpeciesRepository.find_by_korean_name",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.services.species_candidate_service.SpeciesRepository.find_by_common_name",
                new=AsyncMock(return_value=None),
            ),
        ):
            status, body = asyncio.run(
                _post(
                    "/plants/species-candidates",
                    {
                        "user_id": str(uuid.uuid4()),
                        "image_ref": "uploads/mock/unrecognized-plant.jpg",
                        "locale": "ko-KR",
                        "top_k": 3,
                    },
                )
            )
    finally:
        _clear_overrides()

    assert status == 200
    first = body["candidates"][0]
    assert first["label_ko"] == "잘 모르겠어요"
    assert first["label_en"] == "Unknown"
    assert first["scientific_name"] is None
    assert first["confidence"] == 0.0
    assert first["confidence_label"] == "low"
    assert first["species_profile_id"] is None


def test_response_excludes_diagnosis_fields() -> None:
    _setup_overrides()
    try:
        with (
            patch(
                "app.services.species_candidate_service.SpeciesRepository.find_by_scientific_name",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.services.species_candidate_service.SpeciesRepository.find_by_korean_name",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.services.species_candidate_service.SpeciesRepository.find_by_common_name",
                new=AsyncMock(return_value=None),
            ),
        ):
            _, body = asyncio.run(
                _post(
                    "/plants/species-candidates",
                    {
                        "user_id": str(uuid.uuid4()),
                        "image_ref": "uploads/mock/monstera.jpg",
                    },
                )
            )
    finally:
        _clear_overrides()

    forbidden = {
        "disease",
        "disease_prediction",
        "pest",
        "pest_prediction",
        "health",
        "health_prediction",
        "diagnosis",
        "treatment",
        "pesticide",
        "severity",
        "recommended_action",
    }
    for c in body["candidates"]:
        leaked = set(c.keys()) & forbidden
        assert not leaked, f"Forbidden response field: {leaked}"


def test_species_profile_id_populated_when_db_matches() -> None:
    """Optional resolution: if scientific_name matches a row, return its id."""
    _setup_overrides()
    matched = MagicMock()
    matched.id = uuid.UUID("00000000-0000-0000-0000-000000000201")
    try:
        with (
            patch(
                "app.services.species_candidate_service.SpeciesRepository.find_by_scientific_name",
                new=AsyncMock(return_value=matched),
            ),
            patch(
                "app.services.species_candidate_service.SpeciesRepository.find_by_korean_name",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.services.species_candidate_service.SpeciesRepository.find_by_common_name",
                new=AsyncMock(return_value=None),
            ),
        ):
            _, body = asyncio.run(
                _post(
                    "/plants/species-candidates",
                    {
                        "user_id": str(uuid.uuid4()),
                        "image_ref": "uploads/mock/monstera.jpg",
                        "top_k": 1,
                    },
                )
            )
    finally:
        _clear_overrides()

    assert body["candidates"][0]["species_profile_id"] == str(matched.id)


def test_endpoint_does_not_create_plant_or_character() -> None:
    """The endpoint must not invoke any onboarding write paths."""
    _setup_overrides()
    try:
        with (
            patch(
                "app.services.species_candidate_service.SpeciesRepository.find_by_scientific_name",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.services.species_candidate_service.SpeciesRepository.find_by_korean_name",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.services.species_candidate_service.SpeciesRepository.find_by_common_name",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.services.plant_onboarding.PlantOnboardingService.create_plant",
                new=AsyncMock(),
            ) as create_plant_mock,
            patch(
                "app.repositories.plant_repository.PlantRepository.create",
                new=AsyncMock(),
            ) as plant_create_mock,
            patch(
                "app.repositories.character_repository.CharacterRepository.create",
                new=AsyncMock(),
            ) as char_create_mock,
        ):
            status, _ = asyncio.run(
                _post(
                    "/plants/species-candidates",
                    {
                        "user_id": str(uuid.uuid4()),
                        "image_ref": "uploads/mock/monstera.jpg",
                    },
                )
            )
    finally:
        _clear_overrides()

    assert status == 200
    create_plant_mock.assert_not_called()
    plant_create_mock.assert_not_called()
    char_create_mock.assert_not_called()


def test_response_keys_exactly_allowed_set() -> None:
    _setup_overrides()
    try:
        with (
            patch(
                "app.services.species_candidate_service.SpeciesRepository.find_by_scientific_name",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.services.species_candidate_service.SpeciesRepository.find_by_korean_name",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.services.species_candidate_service.SpeciesRepository.find_by_common_name",
                new=AsyncMock(return_value=None),
            ),
        ):
            _, body = asyncio.run(
                _post(
                    "/plants/species-candidates",
                    {
                        "user_id": str(uuid.uuid4()),
                        "image_ref": "uploads/mock/monstera.jpg",
                        "top_k": 1,
                    },
                )
            )
    finally:
        _clear_overrides()

    expected = {
        "species_profile_id",
        "label_ko",
        "label_en",
        "scientific_name",
        "confidence",
        "confidence_label",
        "source",
    }
    for c in body["candidates"]:
        assert set(c.keys()) == expected
