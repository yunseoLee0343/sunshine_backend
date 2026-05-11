"""TICKET-021 — CompanionRecommendationService + format_companion_answer + API tests."""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.chat_answer import ParsedAnswer
from app.schemas.companion_recommendation import (
    CompanionRecommendationItem,
    CompanionRecommendationResponse,
)
from app.services.companion_recommendation_service import (
    PlantOwnershipError,
    companion_prompt_hash,
    format_companion_answer,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session() -> MagicMock:
    session = MagicMock()
    session.get = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


def _species_mock(
    sid: uuid.UUID | None = None,
    korean_name: str = "테스트 식물",
    common_name: str | None = "Test Plant",
    scientific_name: str | None = "Testus plantus",
    light_min: Decimal | None = Decimal("500"),
    light_max: Decimal | None = Decimal("2000"),
    humi_min: Decimal | None = Decimal("40"),
    humi_max: Decimal | None = Decimal("70"),
    temp_min: Decimal | None = Decimal("18"),
    temp_max: Decimal | None = Decimal("28"),
    metadata_json: dict | None = None,
) -> MagicMock:
    row = MagicMock()
    row.id = sid or uuid.uuid4()
    row.korean_name = korean_name
    row.common_name = common_name
    row.scientific_name = scientific_name
    row.light_min_lux = light_min
    row.light_max_lux = light_max
    row.humidity_min_pct = humi_min
    row.humidity_max_pct = humi_max
    row.temperature_min_c = temp_min
    row.temperature_max_c = temp_max
    row.metadata_json = metadata_json or {}
    return row


def _snapshot_mock(
    light: Decimal | None = Decimal("1000"),
    humidity: Decimal | None = Decimal("55"),
    temperature: Decimal | None = Decimal("23"),
) -> MagicMock:
    snap = MagicMock()
    snap.light_avg_lux = light
    snap.humidity_avg_pct = humidity
    snap.temperature_avg_c = temperature
    return snap


def _plant_mock(
    plant_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    species_profile_id: uuid.UUID | None = None,
) -> MagicMock:
    plant = MagicMock()
    plant.id = plant_id or uuid.uuid4()
    plant.user_id = user_id or uuid.uuid4()
    plant.species_profile_id = species_profile_id
    return plant


def _make_recommendation_response(
    plant_id: uuid.UUID | None = None,
    n_recs: int = 2,
    with_cautions: bool = False,
) -> CompanionRecommendationResponse:
    plant_id = plant_id or uuid.uuid4()
    recs = []
    for i in range(n_recs):
        sid = uuid.uuid4()
        recs.append(
            CompanionRecommendationItem(
                species_id=sid,
                common_name=f"추천 식물{i + 1}",
                scientific_name=f"Plantus {i + 1}",
                compatibility_score=round(1.0 - i * 0.1, 2),
                assessed_dimensions=3,
                match_reasons=["광요구도 적합", "온도 조건 적합"],
                caution_notes=["독성 식물 — 취급 주의 필요"] if with_cautions else [],
                is_compatible=True,
            )
        )
    return CompanionRecommendationResponse(
        plant_id=plant_id,
        current_species_id=None,
        environment_available=True,
        candidates_assessed=5,
        recommendations=recs,
        source_species_ids=[r.species_id for r in recs],
    )


# ---------------------------------------------------------------------------
# format_companion_answer — no recommendations
# ---------------------------------------------------------------------------


def test_format_none_response_returns_fallback() -> None:
    parsed = format_companion_answer(None)
    assert isinstance(parsed, ParsedAnswer)
    assert "찾지 못했습니다" in parsed.결론


def test_format_empty_recommendations_returns_fallback() -> None:
    resp = CompanionRecommendationResponse(
        plant_id=uuid.uuid4(),
        current_species_id=None,
        environment_available=False,
        candidates_assessed=0,
        recommendations=[],
        source_species_ids=[],
    )
    parsed = format_companion_answer(resp)
    assert "찾지 못했습니다" in parsed.결론


def test_format_fallback_has_all_sections() -> None:
    parsed = format_companion_answer(None)
    assert parsed.결론
    assert parsed.근거
    assert parsed.행동
    assert parsed.주의


# ---------------------------------------------------------------------------
# format_companion_answer — with recommendations
# ---------------------------------------------------------------------------


def test_format_결론_mentions_count_and_top_plant() -> None:
    resp = _make_recommendation_response(n_recs=3)
    parsed = format_companion_answer(resp)
    assert "3가지" in parsed.결론
    assert "추천 식물1" in parsed.결론


def test_format_결론_includes_score() -> None:
    resp = _make_recommendation_response(n_recs=1)
    parsed = format_companion_answer(resp)
    assert "1.00" in parsed.결론


def test_format_근거_lists_top_3() -> None:
    resp = _make_recommendation_response(n_recs=5)
    parsed = format_companion_answer(resp)
    assert "추천 식물1" in parsed.근거
    assert "추천 식물2" in parsed.근거
    assert "추천 식물3" in parsed.근거


def test_format_행동_lists_all_recommendations() -> None:
    resp = _make_recommendation_response(n_recs=3)
    parsed = format_companion_answer(resp)
    assert "추천 식물1" in parsed.행동
    assert "추천 식물2" in parsed.행동
    assert "추천 식물3" in parsed.행동


def test_format_주의_includes_caution_notes() -> None:
    resp = _make_recommendation_response(with_cautions=True)
    parsed = format_companion_answer(resp)
    assert "독성" in parsed.주의


def test_format_주의_no_cautions_safe_message() -> None:
    resp = _make_recommendation_response(with_cautions=False)
    parsed = format_companion_answer(resp)
    assert "독성" not in parsed.주의


def test_format_duplicate_cautions_deduplicated() -> None:
    sid1, sid2 = uuid.uuid4(), uuid.uuid4()
    recs = [
        CompanionRecommendationItem(
            species_id=sid1,
            common_name="A",
            scientific_name="A",
            compatibility_score=0.9,
            assessed_dimensions=3,
            match_reasons=[],
            caution_notes=["독성 식물 — 취급 주의 필요"],
            is_compatible=True,
        ),
        CompanionRecommendationItem(
            species_id=sid2,
            common_name="B",
            scientific_name="B",
            compatibility_score=0.8,
            assessed_dimensions=3,
            match_reasons=[],
            caution_notes=["독성 식물 — 취급 주의 필요"],
            is_compatible=True,
        ),
    ]
    resp = CompanionRecommendationResponse(
        plant_id=uuid.uuid4(),
        current_species_id=None,
        environment_available=True,
        candidates_assessed=2,
        recommendations=recs,
        source_species_ids=[sid1, sid2],
    )
    parsed = format_companion_answer(resp)
    assert parsed.주의.count("독성 식물 — 취급 주의 필요") == 1


# ---------------------------------------------------------------------------
# companion_prompt_hash
# ---------------------------------------------------------------------------


def test_companion_prompt_hash_64_chars() -> None:
    h = companion_prompt_hash(uuid.uuid4(), "동반 식물 추천")
    assert len(h) == 64


def test_companion_prompt_hash_deterministic() -> None:
    pid = uuid.uuid4()
    assert companion_prompt_hash(pid, "q") == companion_prompt_hash(pid, "q")


def test_companion_prompt_hash_varies_by_plant() -> None:
    q = "질문"
    assert companion_prompt_hash(uuid.uuid4(), q) != companion_prompt_hash(uuid.uuid4(), q)


# ---------------------------------------------------------------------------
# CompanionRecommendationService — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_service_returns_response() -> None:
    from app.services.companion_recommendation_service import CompanionRecommendationService

    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    species_id = uuid.uuid4()

    session = _make_session()
    plant = _plant_mock(plant_id=plant_id, user_id=user_id, species_profile_id=species_id)
    session.get = AsyncMock(return_value=plant)

    snap = _snapshot_mock()
    species = _species_mock(sid=uuid.uuid4())  # different species — compatible

    snap_result = MagicMock()
    snap_result.scalar_one_or_none.return_value = snap
    species_result = MagicMock()
    species_result.scalars.return_value.all.return_value = [species]

    session.execute = AsyncMock(side_effect=[snap_result, species_result])

    svc = CompanionRecommendationService(session)
    resp = await svc.recommend(plant_id, user_id)

    assert isinstance(resp, CompanionRecommendationResponse)
    assert resp.plant_id == plant_id
    assert resp.environment_available is True


@pytest.mark.asyncio
async def test_service_excludes_current_species() -> None:
    from app.services.companion_recommendation_service import CompanionRecommendationService

    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    own_species_id = uuid.uuid4()

    session = _make_session()
    plant = _plant_mock(plant_id=plant_id, user_id=user_id, species_profile_id=own_species_id)
    session.get = AsyncMock(return_value=plant)

    snap = _snapshot_mock()
    # Only candidate is the current species
    current_species = _species_mock(sid=own_species_id)

    snap_result = MagicMock()
    snap_result.scalar_one_or_none.return_value = snap
    species_result = MagicMock()
    species_result.scalars.return_value.all.return_value = [current_species]

    session.execute = AsyncMock(side_effect=[snap_result, species_result])

    svc = CompanionRecommendationService(session)
    resp = await svc.recommend(plant_id, user_id)

    assert resp.recommendations == []


@pytest.mark.asyncio
async def test_service_only_returns_compatible() -> None:
    from app.services.companion_recommendation_service import CompanionRecommendationService

    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    session = _make_session()
    plant = _plant_mock(plant_id=plant_id, user_id=user_id)
    session.get = AsyncMock(return_value=plant)

    snap = _snapshot_mock(light=Decimal("100"), humidity=Decimal("55"), temperature=Decimal("23"))
    # Candidate needs 5000+ lux — incompatible
    bad_species = _species_mock(light_min=Decimal("5000"), light_max=Decimal("10000"))

    snap_result = MagicMock()
    snap_result.scalar_one_or_none.return_value = snap
    species_result = MagicMock()
    species_result.scalars.return_value.all.return_value = [bad_species]

    session.execute = AsyncMock(side_effect=[snap_result, species_result])

    svc = CompanionRecommendationService(session)
    resp = await svc.recommend(plant_id, user_id)

    assert resp.recommendations == []


@pytest.mark.asyncio
async def test_service_no_snapshot_env_not_available() -> None:
    from app.services.companion_recommendation_service import CompanionRecommendationService

    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    session = _make_session()
    plant = _plant_mock(plant_id=plant_id, user_id=user_id)
    session.get = AsyncMock(return_value=plant)

    snap_result = MagicMock()
    snap_result.scalar_one_or_none.return_value = None  # no snapshot
    species_result = MagicMock()
    species_result.scalars.return_value.all.return_value = []

    session.execute = AsyncMock(side_effect=[snap_result, species_result])

    svc = CompanionRecommendationService(session)
    resp = await svc.recommend(plant_id, user_id)

    assert resp.environment_available is False


@pytest.mark.asyncio
async def test_service_source_species_ids_match_recommendations() -> None:
    from app.services.companion_recommendation_service import CompanionRecommendationService

    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    session = _make_session()
    plant = _plant_mock(plant_id=plant_id, user_id=user_id)
    session.get = AsyncMock(return_value=plant)

    snap = _snapshot_mock()
    species = _species_mock(sid=uuid.uuid4())

    snap_result = MagicMock()
    snap_result.scalar_one_or_none.return_value = snap
    species_result = MagicMock()
    species_result.scalars.return_value.all.return_value = [species]

    session.execute = AsyncMock(side_effect=[snap_result, species_result])

    svc = CompanionRecommendationService(session)
    resp = await svc.recommend(plant_id, user_id)

    assert resp.source_species_ids == [r.species_id for r in resp.recommendations]


# ---------------------------------------------------------------------------
# CompanionRecommendationService — errors
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_service_plant_not_found_raises() -> None:
    from app.services.companion_recommendation_service import CompanionRecommendationService
    from app.services.evidence_builder import PlantNotFoundError

    session = _make_session()
    session.get = AsyncMock(return_value=None)

    svc = CompanionRecommendationService(session)
    with pytest.raises(PlantNotFoundError):
        await svc.recommend(uuid.uuid4(), uuid.uuid4())


@pytest.mark.asyncio
async def test_service_wrong_owner_raises_ownership_error() -> None:
    from app.services.companion_recommendation_service import CompanionRecommendationService

    plant_id = uuid.uuid4()
    real_owner = uuid.uuid4()
    other_user = uuid.uuid4()

    session = _make_session()
    plant = _plant_mock(plant_id=plant_id, user_id=real_owner)
    session.get = AsyncMock(return_value=plant)

    svc = CompanionRecommendationService(session)
    with pytest.raises(PlantOwnershipError):
        await svc.recommend(plant_id, other_user)


# ---------------------------------------------------------------------------
# metadata_json toxicity flags propagated
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_service_toxicity_flags_in_caution_notes() -> None:
    from app.services.companion_recommendation_service import CompanionRecommendationService

    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    session = _make_session()
    plant = _plant_mock(plant_id=plant_id, user_id=user_id)
    session.get = AsyncMock(return_value=plant)

    snap = _snapshot_mock()
    toxic_species = _species_mock(metadata_json={"is_toxic": True, "toxic_to_pets": True})

    snap_result = MagicMock()
    snap_result.scalar_one_or_none.return_value = snap
    species_result = MagicMock()
    species_result.scalars.return_value.all.return_value = [toxic_species]

    session.execute = AsyncMock(side_effect=[snap_result, species_result])

    svc = CompanionRecommendationService(session)
    resp = await svc.recommend(plant_id, user_id)

    # If compatible, caution notes should mention toxicity
    if resp.recommendations:
        all_cautions = " ".join(resp.recommendations[0].caution_notes)
        assert "독성" in all_cautions


# ---------------------------------------------------------------------------
# ChatOrchestrator — companion branch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_companion_intent_returns_response() -> None:
    from app.schemas.chat_answer import ChatAnswerResponse
    from app.services.chat_orchestrator import ChatOrchestrator

    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    request_id = uuid.uuid4()
    question = "같이 키울 식물 추천해줘"

    orchestrator = ChatOrchestrator()
    session = _make_session()
    session.get = AsyncMock(return_value=None)  # no cached ChatRequest

    rec_resp = _make_recommendation_response(plant_id=plant_id)

    with (
        patch("app.services.chat_orchestrator._CLASSIFIER") as mock_cls,
        patch("app.services.chat_orchestrator.CompanionRecommendationService") as mock_svc_cls,
    ):
        mock_cls.classify.return_value = ("companion_plant_question", 0.9, "rule")
        mock_svc_cls.return_value.recommend = AsyncMock(return_value=rec_resp)

        resp = await orchestrator.run(
            session,
            plant_id=plant_id,
            user_id=user_id,
            question=question,
            request_id=request_id,
        )

    assert isinstance(resp, ChatAnswerResponse)
    assert resp.intent == "companion_plant_question"
    assert resp.model_name == "companion-filter-v1"
    assert resp.from_cache is False


@pytest.mark.asyncio
async def test_orchestrator_companion_persists_with_companion_profile() -> None:
    from app.models.llm_run import LlmRun
    from app.services.chat_orchestrator import ChatOrchestrator

    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    request_id = uuid.uuid4()

    orchestrator = ChatOrchestrator()
    session = _make_session()
    session.get = AsyncMock(return_value=None)

    rec_resp = _make_recommendation_response()

    with (
        patch("app.services.chat_orchestrator._CLASSIFIER") as mock_cls,
        patch("app.services.chat_orchestrator.CompanionRecommendationService") as mock_svc_cls,
    ):
        mock_cls.classify.return_value = ("companion_plant_question", 0.9, "rule")
        mock_svc_cls.return_value.recommend = AsyncMock(return_value=rec_resp)

        await orchestrator.run(
            session,
            plant_id=plant_id,
            user_id=user_id,
            question="추천해줘",
            request_id=request_id,
        )

    added_profiles = [call.args[0].profile for call in session.add.call_args_list if isinstance(call.args[0], LlmRun)]
    assert "companion_orchestrator" in added_profiles


@pytest.mark.asyncio
async def test_orchestrator_companion_answer_has_4_sections() -> None:
    from app.services.chat_orchestrator import ChatOrchestrator

    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    request_id = uuid.uuid4()

    orchestrator = ChatOrchestrator()
    session = _make_session()
    session.get = AsyncMock(return_value=None)

    rec_resp = _make_recommendation_response()

    with (
        patch("app.services.chat_orchestrator._CLASSIFIER") as mock_cls,
        patch("app.services.chat_orchestrator.CompanionRecommendationService") as mock_svc_cls,
    ):
        mock_cls.classify.return_value = ("companion_plant_question", 0.9, "rule")
        mock_svc_cls.return_value.recommend = AsyncMock(return_value=rec_resp)

        resp = await orchestrator.run(
            session,
            plant_id=plant_id,
            user_id=user_id,
            question="추천해줘",
            request_id=request_id,
        )

    assert resp.answer.결론
    assert resp.answer.근거
    assert resp.answer.행동
    assert resp.answer.주의


@pytest.mark.asyncio
async def test_orchestrator_companion_service_error_returns_fallback() -> None:
    from app.services.chat_orchestrator import ChatOrchestrator
    from app.services.evidence_builder import PlantNotFoundError

    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    request_id = uuid.uuid4()

    orchestrator = ChatOrchestrator()
    session = _make_session()
    session.get = AsyncMock(return_value=None)

    with (
        patch("app.services.chat_orchestrator._CLASSIFIER") as mock_cls,
        patch("app.services.chat_orchestrator.CompanionRecommendationService") as mock_svc_cls,
    ):
        mock_cls.classify.return_value = ("companion_plant_question", 0.9, "rule")
        mock_svc_cls.return_value.recommend = AsyncMock(side_effect=PlantNotFoundError("not found"))

        resp = await orchestrator.run(
            session,
            plant_id=plant_id,
            user_id=user_id,
            question="추천해줘",
            request_id=request_id,
        )

    # Fallback answer, not a raised exception
    assert resp.intent == "companion_plant_question"
    assert "찾지 못했습니다" in resp.answer.결론


@pytest.mark.asyncio
async def test_orchestrator_companion_input_tokens_zero() -> None:
    from app.services.chat_orchestrator import ChatOrchestrator

    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    request_id = uuid.uuid4()

    orchestrator = ChatOrchestrator()
    session = _make_session()
    session.get = AsyncMock(return_value=None)

    rec_resp = _make_recommendation_response()

    with (
        patch("app.services.chat_orchestrator._CLASSIFIER") as mock_cls,
        patch("app.services.chat_orchestrator.CompanionRecommendationService") as mock_svc_cls,
    ):
        mock_cls.classify.return_value = ("companion_plant_question", 0.9, "rule")
        mock_svc_cls.return_value.recommend = AsyncMock(return_value=rec_resp)

        resp = await orchestrator.run(
            session,
            plant_id=plant_id,
            user_id=user_id,
            question="추천해줘",
            request_id=request_id,
        )

    assert resp.input_tokens == 0
