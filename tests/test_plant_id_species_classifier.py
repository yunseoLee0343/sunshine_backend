"""T-003C — PlantIdSpeciesClassifier tests (mocked HTTP, no real Plant.id calls)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.vision.plant_id_species_classifier import PlantIdSpeciesClassifier

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

_FAKE_BYTES = b"\xFF\xD8\xFF\xE0" + b"\x00" * 100  # minimal JPEG magic


def _patch_resolve(image_bytes: bytes = _FAKE_BYTES):
    return patch(
        "app.vision.plant_id_species_classifier._resolve_image_bytes",
        return_value=image_bytes,
    )


def _patch_http(response_data: dict | None = None, side_effect: Exception | None = None):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = response_data or {}

    mock_client = AsyncMock()
    if side_effect is not None:
        mock_client.post = AsyncMock(side_effect=side_effect)
    else:
        mock_client.post = AsyncMock(return_value=mock_response)

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    return patch(
        "app.vision.plant_id_species_classifier.httpx.AsyncClient",
        return_value=mock_ctx,
    )


def _run(
    image_ref: str = "uploads/plant-images/test.jpg",
    locale: str = "ko-KR",
    top_k: int = 3,
    response_data: dict | None = None,
    http_side_effect: Exception | None = None,
):
    classifier = PlantIdSpeciesClassifier()
    with _patch_resolve(), _patch_http(response_data, http_side_effect):
        return asyncio.run(classifier.classify_species(image_ref, locale=locale, top_k=top_k))


def _suggestion(
    name: str,
    probability: float,
    common_names: list[str] | None = None,
) -> dict:
    s: dict = {"name": name, "probability": probability}
    if common_names is not None:
        s["details"] = {"common_names": common_names}
    return s


_THREE_SUGGESTIONS = {
    "result": {
        "classification": {
            "suggestions": [
                _suggestion("Monstera deliciosa", 0.91, ["몬스테라", "Swiss Cheese Plant"]),
                _suggestion("Epipremnum aureum", 0.72, ["스킨답서스", "Pothos"]),
                _suggestion("Philodendron hederaceum", 0.45, ["필로덴드론"]),
            ]
        }
    }
}


# ---------------------------------------------------------------------------
# 1. Successful response with 3 suggestions
# ---------------------------------------------------------------------------


def test_three_suggestions_returns_three_candidates() -> None:
    result = _run(response_data=_THREE_SUGGESTIONS)
    assert len(result) == 3


def test_candidates_have_correct_scientific_names() -> None:
    result = _run(response_data=_THREE_SUGGESTIONS)
    assert result[0].scientific_name == "Monstera deliciosa"
    assert result[1].scientific_name == "Epipremnum aureum"
    assert result[2].scientific_name == "Philodendron hederaceum"


def test_candidates_source_is_plant_id() -> None:
    result = _run(response_data=_THREE_SUGGESTIONS)
    assert all(c.source == "plant.id" for c in result)


def test_korean_locale_uses_common_names_as_label_ko() -> None:
    result = _run(response_data=_THREE_SUGGESTIONS, locale="ko-KR")
    assert result[0].label_ko == "몬스테라"
    assert result[1].label_ko == "스킨답서스"


# ---------------------------------------------------------------------------
# 2. Confidence label mapping high / medium / low
# ---------------------------------------------------------------------------


def test_confidence_high_at_091() -> None:
    resp = {"result": {"classification": {"suggestions": [_suggestion("A", 0.91, [])]}}}
    assert _run(response_data=resp)[0].confidence_label == "high"


def test_confidence_high_at_boundary_080() -> None:
    resp = {"result": {"classification": {"suggestions": [_suggestion("A", 0.80, [])]}}}
    assert _run(response_data=resp)[0].confidence_label == "high"


def test_confidence_medium_at_072() -> None:
    resp = {"result": {"classification": {"suggestions": [_suggestion("A", 0.72, [])]}}}
    assert _run(response_data=resp)[0].confidence_label == "medium"


def test_confidence_medium_at_boundary_050() -> None:
    resp = {"result": {"classification": {"suggestions": [_suggestion("A", 0.50, [])]}}}
    assert _run(response_data=resp)[0].confidence_label == "medium"


def test_confidence_low_at_045() -> None:
    resp = {"result": {"classification": {"suggestions": [_suggestion("A", 0.45, [])]}}}
    assert _run(response_data=resp)[0].confidence_label == "low"


def test_confidence_low_at_zero() -> None:
    resp = {"result": {"classification": {"suggestions": [_suggestion("A", 0.0, [])]}}}
    assert _run(response_data=resp)[0].confidence_label == "low"


# ---------------------------------------------------------------------------
# 3. Missing scientific_name still returns candidate
# ---------------------------------------------------------------------------


def test_missing_name_field_returns_candidate() -> None:
    resp = {"result": {"classification": {"suggestions": [{"probability": 0.60}]}}}
    result = _run(response_data=resp)
    assert len(result) == 1
    assert result[0].scientific_name is None
    assert result[0].source == "plant.id"
    assert result[0].confidence == pytest.approx(0.60)


def test_missing_details_field_does_not_crash() -> None:
    resp = {"result": {"classification": {"suggestions": [{"name": "Rosa canina", "probability": 0.55}]}}}
    result = _run(response_data=resp)
    assert result[0].scientific_name == "Rosa canina"


# ---------------------------------------------------------------------------
# 4. Timeout returns fallback
# ---------------------------------------------------------------------------


def test_timeout_returns_fallback() -> None:
    result = _run(http_side_effect=httpx.TimeoutException("timed out"))
    assert len(result) == 1
    assert result[0].label_ko == "잘 모르겠어요"
    assert result[0].confidence_label == "low"
    assert result[0].source == "plant.id"


def test_connect_error_returns_fallback() -> None:
    result = _run(http_side_effect=httpx.ConnectError("refused"))
    assert result[0].label_ko == "잘 모르겠어요"


# ---------------------------------------------------------------------------
# 5. Invalid / unexpected response returns fallback
# ---------------------------------------------------------------------------


def test_empty_response_returns_fallback() -> None:
    result = _run(response_data={})
    assert result[0].label_ko == "잘 모르겠어요"


def test_missing_result_key_returns_fallback() -> None:
    result = _run(response_data={"status": "COMPLETED"})
    assert result[0].label_ko == "잘 모르겠어요"


def test_empty_suggestions_list_returns_fallback() -> None:
    result = _run(response_data={"result": {"classification": {"suggestions": []}}})
    assert result[0].label_ko == "잘 모르겠어요"


def test_unresolvable_image_ref_returns_fallback() -> None:
    classifier = PlantIdSpeciesClassifier()
    with patch(
        "app.vision.plant_id_species_classifier._resolve_image_bytes",
        side_effect=FileNotFoundError("no file"),
    ):
        result = asyncio.run(classifier.classify_species("uploads/plant-images/ghost.jpg"))
    assert result[0].label_ko == "잘 모르겠어요"


# ---------------------------------------------------------------------------
# 6. top_k is respected
# ---------------------------------------------------------------------------


def test_top_k_1_returns_one_candidate() -> None:
    result = _run(response_data=_THREE_SUGGESTIONS, top_k=1)
    assert len(result) == 1
    assert result[0].scientific_name == "Monstera deliciosa"


def test_top_k_2_returns_two_candidates() -> None:
    result = _run(response_data=_THREE_SUGGESTIONS, top_k=2)
    assert len(result) == 2


def test_top_k_exceeds_suggestions_returns_all_available() -> None:
    result = _run(response_data=_THREE_SUGGESTIONS, top_k=10)
    assert len(result) == 3
