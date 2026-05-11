"""TICKET-026 — API contract / schema drift-detection tests (no DB, no HTTP).

Verifies:
  - Required fields are present on each key response schema
  - ParsedAnswer has EXACTLY the four Korean section fields
  - Forbidden marketplace / ad / diagnosis fields are absent
  - Every key route is bound to its expected response_model
  - Key schemas carry json_schema_extra examples
"""

from __future__ import annotations

from fastapi.routing import APIRoute

from app.main import app
from app.schemas.care_logs import CareLogCreateResponse, CareLogListResponse
from app.schemas.character_state import CharacterStateResponse
from app.schemas.chat_answer import ChatAnswerResponse, ParsedAnswer
from app.schemas.companion_recommendation import (
    CompanionRecommendationItem,
    CompanionRecommendationResponse,
)
from app.schemas.home import HomeResponse, PlantHomeCard
from app.schemas.plants import (
    CreatePlantResponse,
    GetPlantResponse,
    ListPlantsResponse,
    PlantCard,
    SpeciesCandidateItem,
    SpeciesCandidatesResponse,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _route(method: str, path: str) -> APIRoute:
    for r in app.routes:
        if isinstance(r, APIRoute) and r.path == path and method.upper() in r.methods:
            return r
    raise AssertionError(f"Route {method.upper()} {path} not found in app.routes")


def _fields(schema) -> set[str]:
    return set(schema.model_fields.keys())


# ---------------------------------------------------------------------------
# PlantHomeCard / HomeResponse
# ---------------------------------------------------------------------------


def test_plant_home_card_required_fields() -> None:
    expected = {
        "plant_id",
        "nickname",
        "room_name",
        "species_name",
        "character",
        "environment",
        "today_recommended_action",
        "care_status",
    }
    assert expected <= _fields(PlantHomeCard)


def test_home_response_required_fields() -> None:
    assert {"user_id", "plants"} <= _fields(HomeResponse)


# ---------------------------------------------------------------------------
# PlantCard / Create / List / Get
# ---------------------------------------------------------------------------


def test_plant_card_required_fields() -> None:
    expected = {"plant_id", "user_id", "species_profile_id", "nickname", "room_name", "species", "character"}
    assert expected <= _fields(PlantCard)


def test_create_plant_response_has_plant() -> None:
    assert "plant" in _fields(CreatePlantResponse)


def test_list_plants_response_has_plants() -> None:
    assert "plants" in _fields(ListPlantsResponse)


def test_get_plant_response_has_plant() -> None:
    assert "plant" in _fields(GetPlantResponse)


def test_species_candidate_item_required_fields() -> None:
    expected = {"label_ko", "label_en", "scientific_name", "confidence", "confidence_label", "source"}
    assert expected <= _fields(SpeciesCandidateItem)


# ---------------------------------------------------------------------------
# ParsedAnswer — EXACT four Korean sections (critical contract)
# ---------------------------------------------------------------------------


def test_parsed_answer_has_exactly_four_sections() -> None:
    assert _fields(ParsedAnswer) == {"결론", "근거", "행동", "주의"}


def test_parsed_answer_no_extra_fields() -> None:
    forbidden = {"conclusion", "basis", "action", "caution", "summary", "recommendation"}
    assert not (forbidden & _fields(ParsedAnswer)), "ParsedAnswer must use Korean field names only"


# ---------------------------------------------------------------------------
# ChatAnswerResponse — required fields + forbidden fields
# ---------------------------------------------------------------------------


def test_chat_answer_response_required_fields() -> None:
    expected = {
        "request_id",
        "plant_id",
        "intent",
        "answer",
        "guardrails_applied",
        "prompt_hash",
        "model_name",
        "input_tokens",
        "output_tokens",
        "from_cache",
        "created_at",
        "is_reference_only",
        "diagnosis_allowed",
    }
    assert expected <= _fields(ChatAnswerResponse)


def test_chat_answer_response_no_diagnosis_fields() -> None:
    forbidden = {"pest_diagnosis", "diagnosis_result", "disease_name", "diagnosis"}
    assert not (forbidden & _fields(ChatAnswerResponse)), "ChatAnswerResponse must not expose raw diagnosis data"


# ---------------------------------------------------------------------------
# CompanionRecommendationItem — fields + forbidden commercial fields
# ---------------------------------------------------------------------------


def test_companion_item_required_fields() -> None:
    expected = {
        "species_id",
        "common_name",
        "scientific_name",
        "compatibility_score",
        "assessed_dimensions",
        "match_reasons",
        "caution_notes",
        "is_compatible",
    }
    assert expected <= _fields(CompanionRecommendationItem)


def test_companion_item_no_marketplace_fields() -> None:
    fields = _fields(CompanionRecommendationItem)
    for f in fields:
        assert "marketplace" not in f, f"Forbidden field: {f}"
        assert "purchase" not in f, f"Forbidden field: {f}"
        assert f.startswith("ad_") is False, f"Forbidden ad_ field: {f}"


def test_companion_response_required_fields() -> None:
    expected = {
        "plant_id",
        "current_species_id",
        "environment_available",
        "candidates_assessed",
        "recommendations",
        "source_species_ids",
    }
    assert expected <= _fields(CompanionRecommendationResponse)


# ---------------------------------------------------------------------------
# CareLog schemas
# ---------------------------------------------------------------------------


def test_care_log_create_response_fields() -> None:
    assert {"log", "character"} <= _fields(CareLogCreateResponse)


def test_care_log_list_response_fields() -> None:
    assert {"plant_id", "logs"} <= _fields(CareLogListResponse)


# ---------------------------------------------------------------------------
# Route → response_model bindings
# ---------------------------------------------------------------------------


def test_route_get_home_response_model() -> None:
    r = _route("GET", "/home")
    assert r.response_model is HomeResponse


def test_route_list_plants_response_model() -> None:
    r = _route("GET", "/plants")
    assert r.response_model is ListPlantsResponse


def test_route_get_plant_response_model() -> None:
    r = _route("GET", "/plants/{plant_id}")
    assert r.response_model is GetPlantResponse


def test_route_create_plant_response_model() -> None:
    r = _route("POST", "/plants")
    assert r.response_model is CreatePlantResponse


def test_route_species_candidates_response_model() -> None:
    r = _route("POST", "/plants/species-candidates")
    assert r.response_model is SpeciesCandidatesResponse


def test_route_character_state_response_model() -> None:
    r = _route("POST", "/plants/{plant_id}/character-state")
    assert r.response_model is CharacterStateResponse


def test_route_chat_response_model() -> None:
    r = _route("POST", "/plants/{plant_id}/chat")
    assert r.response_model is ChatAnswerResponse


def test_route_companion_response_model() -> None:
    r = _route("GET", "/plants/{plant_id}/companion-recommendations")
    assert r.response_model is CompanionRecommendationResponse


def test_route_care_log_create_response_model() -> None:
    r = _route("POST", "/plants/{plant_id}/care-logs")
    assert r.response_model is CareLogCreateResponse


def test_route_care_log_list_response_model() -> None:
    r = _route("GET", "/plants/{plant_id}/care-logs")
    assert r.response_model is CareLogListResponse


# ---------------------------------------------------------------------------
# OpenAPI example presence
# ---------------------------------------------------------------------------


def test_plant_home_card_has_example() -> None:
    extra = PlantHomeCard.model_config.get("json_schema_extra", {})
    assert "example" in extra, "PlantHomeCard must declare an OpenAPI example"


def test_parsed_answer_has_example() -> None:
    extra = ParsedAnswer.model_config.get("json_schema_extra", {})
    assert "example" in extra, "ParsedAnswer must declare an OpenAPI example"
    example = extra["example"]
    assert set(example.keys()) == {"결론", "근거", "행동", "주의"}


def test_companion_item_has_example() -> None:
    extra = CompanionRecommendationItem.model_config.get("json_schema_extra", {})
    assert "example" in extra, "CompanionRecommendationItem must declare an OpenAPI example"
    example = extra["example"]
    assert "marketplace_url" not in example
    assert "purchase_link" not in example
