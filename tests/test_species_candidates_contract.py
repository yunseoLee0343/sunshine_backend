"""TICKET-002 — Species candidates contract tests.

No live DB required — mocks the SpeciesRepository.
"""

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient

from app.main import app


async def _post(path: str, body: dict) -> tuple[int, dict]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post(path, json=body)
    return r.status_code, r.json()


def _make_mock_species(n: int = 2):
    rows = []
    for i in range(n):
        s = MagicMock()
        s.id = uuid.uuid4()
        s.korean_name = f"식물{i}"
        s.scientific_name = f"Species {i}"
        s.common_name = f"Plant {i}"
        rows.append(s)
    return rows


# ---------------------------------------------------------------------------
# Species candidates
# ---------------------------------------------------------------------------


def test_species_candidates_returns_list() -> None:
    mock_rows = _make_mock_species(3)
    with patch(
        "app.api.plants.SpeciesRepository.list_candidates",
        new=AsyncMock(return_value=mock_rows),
    ):
        status, body = asyncio.run(
            _post("/plants/species-candidates", {"user_id": str(uuid.uuid4())})
        )
    assert status == 200
    assert "candidates" in body
    assert len(body["candidates"]) == 3


def test_species_candidates_item_fields() -> None:
    mock_rows = _make_mock_species(1)
    with patch(
        "app.api.plants.SpeciesRepository.list_candidates",
        new=AsyncMock(return_value=mock_rows),
    ):
        _, body = asyncio.run(
            _post("/plants/species-candidates", {"user_id": str(uuid.uuid4())})
        )
    item = body["candidates"][0]
    assert "species_profile_id" in item
    assert "korean_name" in item
    assert "scientific_name" in item
    assert "common_name" in item
    assert "confidence_label" in item


def test_species_candidates_no_diagnosis_fields() -> None:
    mock_rows = _make_mock_species(1)
    with patch(
        "app.api.plants.SpeciesRepository.list_candidates",
        new=AsyncMock(return_value=mock_rows),
    ):
        _, body = asyncio.run(
            _post("/plants/species-candidates", {"user_id": str(uuid.uuid4())})
        )
    item = body["candidates"][0]
    forbidden = {"disease", "pest", "health", "diagnosis", "confidence_score"}
    assert not forbidden.intersection(item.keys()), (
        f"Forbidden fields found: {forbidden.intersection(item.keys())}"
    )


def test_species_candidates_image_ref_is_opaque() -> None:
    """image_ref is accepted but never causes file I/O or inference."""
    mock_rows = _make_mock_species(1)
    with patch(
        "app.api.plants.SpeciesRepository.list_candidates",
        new=AsyncMock(return_value=mock_rows),
    ):
        status, body = asyncio.run(
            _post(
                "/plants/species-candidates",
                {
                    "user_id": str(uuid.uuid4()),
                    "image_ref": "uploads/mock/monstera.jpg",
                },
            )
        )
    assert status == 200
    assert len(body["candidates"]) == 1


def test_species_candidates_empty_db_returns_empty_list() -> None:
    with patch(
        "app.api.plants.SpeciesRepository.list_candidates",
        new=AsyncMock(return_value=[]),
    ):
        status, body = asyncio.run(
            _post("/plants/species-candidates", {"user_id": str(uuid.uuid4())})
        )
    assert status == 200
    assert body["candidates"] == []
