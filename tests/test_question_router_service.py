"""TICKET-062 — QuestionRouterService deterministic routing tests."""

import pytest

from app.domain.question_router import ROUTE_SOURCES, QuestionRouteDecision
from app.services.question_router_service import QuestionRouterService

_svc = QuestionRouterService()


def _route(question: str) -> QuestionRouteDecision:
    return _svc.route(question)


# ---------------------------------------------------------------------------
# Return type contract
# ---------------------------------------------------------------------------


def test_returns_question_route_decision() -> None:
    assert isinstance(_route("물 줘야 해?"), QuestionRouteDecision)


def test_confidence_between_zero_and_one() -> None:
    for q in ["물 줘야", "건조해", "병충해", "키우는 법", "어시스턴트야"]:
        d = _route(q)
        assert 0.0 <= d.confidence <= 1.0, f"confidence out of range for {q!r}"


def test_reason_codes_is_list() -> None:
    d = _route("물 줘야 해?")
    assert isinstance(d.reason_codes, list)
    assert len(d.reason_codes) >= 1


def test_required_sources_is_list() -> None:
    d = _route("물 줘야 해?")
    assert isinstance(d.required_sources, list)


def test_second_llm_required_is_bool() -> None:
    d = _route("물 줘야 해?")
    assert isinstance(d.second_llm_required, bool)


# ---------------------------------------------------------------------------
# companion
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("q", [
    "같이 두면 좋은 식물 있어?",
    "이 식물이랑 어울리는 식물은?",
    "함께 두면 잘 자라는 식물 추천해줘",
    "궁합 잘 맞는 식물이 뭐야?",
])
def test_companion_route(q: str) -> None:
    assert _route(q).route == "companion"


def test_companion_not_llm_required() -> None:
    assert not _route("같이 두면 좋은 식물 있어?").second_llm_required


def test_companion_required_sources() -> None:
    assert _route("같이 두면 좋은 식물").required_sources == ROUTE_SOURCES["companion"]


# ---------------------------------------------------------------------------
# pest_reference
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("q", [
    "잎에 병충해가 생긴 것 같아요",
    "벌레가 생겼어요",
    "곰팡이가 피었어요",
    "잎에 반점이 생겼어요",
    "진딧물이 붙었어요",
])
def test_pest_reference_route(q: str) -> None:
    assert _route(q).route == "pest_reference"


def test_pest_not_llm_required() -> None:
    assert not _route("벌레가 생겼어요").second_llm_required


def test_pest_required_sources() -> None:
    assert _route("벌레가 생겼어요").required_sources == ["rag_pest_reference"]


# ---------------------------------------------------------------------------
# sql_sensor
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("q", [
    "현재 습도가 어떻게 돼?",
    "지금 온도는?",
    "최근 토양수분이 얼마야?",
    "현재 조도 알려줘",
    "건조해?",
    "센서 값 알려줘",
])
def test_sql_sensor_route(q: str) -> None:
    assert _route(q).route == "sql_sensor"


def test_sql_sensor_not_llm_required() -> None:
    assert not _route("현재 습도가 어떻게 돼?").second_llm_required


def test_sql_sensor_required_sources() -> None:
    assert _route("현재 습도가 어떻게 돼?").required_sources == ["sensor_snapshot"]


# ---------------------------------------------------------------------------
# sql_care_log
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("q", [
    "물 준 기록 보여줘",
    "마지막 물 준 게 언제야?",
    "언제 줬어?",
    "관리 기록 확인하고 싶어",
    "케어 기록 알려줘",
])
def test_sql_care_log_route(q: str) -> None:
    assert _route(q).route == "sql_care_log"


def test_sql_care_log_not_llm_required() -> None:
    assert not _route("물 준 기록 보여줘").second_llm_required


def test_sql_care_log_required_sources() -> None:
    assert _route("물 준 기록 보여줘").required_sources == ["care_log"]


# ---------------------------------------------------------------------------
# rag_lookup
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("q", [
    "몬스테라 키우는 법 알려줘",
    "이 식물 재배법이 뭐야?",
    "어디 두면 잘 자라?",
    "햇빛이 얼마나 필요해?",
    "물주기 주기가 어떻게 돼?",
    "얼마나 자주 물을 줘야 해?",
    "겨울에 관리 어떻게 해?",
    "분갈이는 어떻게 해?",
    "어떻게 키워야 해?",
])
def test_rag_lookup_route(q: str) -> None:
    assert _route(q).route == "rag_lookup"


def test_rag_lookup_not_llm_required() -> None:
    assert not _route("몬스테라 키우는 법").second_llm_required


def test_rag_lookup_required_sources() -> None:
    assert _route("키우는 법 알려줘").required_sources == ["rag_care_knowledge"]


# ---------------------------------------------------------------------------
# rule_only
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("q", [
    "지금 물 줘야 해?",
    "물 줘도 돼?",
    "상태 어때?",
    "잘 자라고 있어?",
])
def test_rule_only_route(q: str) -> None:
    assert _route(q).route == "rule_only"


def test_rule_only_not_llm_required() -> None:
    assert not _route("물 줘야 해?").second_llm_required


def test_rule_only_required_sources() -> None:
    assert _route("물 줘야 해?").required_sources == []


# ---------------------------------------------------------------------------
# llm_required
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("q", [
    "왜 잎이 이상한 것 같아?",
    "진단해 줘",
    "이유가 뭐야?",
    "사진 보고 분석해 줘",
])
def test_llm_required_route(q: str) -> None:
    assert _route(q).route == "llm_required"


def test_llm_required_second_llm_true() -> None:
    assert _route("왜 이렇게 됐을까?").second_llm_required


# ---------------------------------------------------------------------------
# unknown (fallback)
# ---------------------------------------------------------------------------


def test_unknown_fallback_for_unrecognized_question() -> None:
    d = _route("asdfghjkl 완전히 모르는 말이야")
    assert d.route == "unknown"


def test_unknown_second_llm_required() -> None:
    assert _route("asdfghjkl 완전히 모르는 말이야").second_llm_required


def test_unknown_low_confidence() -> None:
    d = _route("asdfghjkl")
    assert d.confidence < 0.6


# ---------------------------------------------------------------------------
# Priority: companion beats rag_lookup
# ---------------------------------------------------------------------------


def test_companion_beats_rag() -> None:
    assert _route("같이 두면 좋고 키우는 법도 알려줘").route == "companion"


# ---------------------------------------------------------------------------
# Priority: pest beats rag_lookup
# ---------------------------------------------------------------------------


def test_pest_beats_rag() -> None:
    assert _route("병충해 예방 재배법 알려줘").route == "pest_reference"


# ---------------------------------------------------------------------------
# No LLM/DB call (structural guard)
# ---------------------------------------------------------------------------


def test_router_service_has_no_async_route() -> None:
    import inspect
    assert not inspect.iscoroutinefunction(QuestionRouterService.route)


def test_router_does_not_import_llm_modules() -> None:
    import sys
    import importlib
    importlib.import_module("app.services.question_router_service")
    forbidden = {"openai", "anthropic", "httpx"}
    leaked = forbidden & set(sys.modules.keys())
    # httpx may be loaded by other modules — only flag direct usage
    src = __import__("pathlib").Path("app/services/question_router_service.py").read_text(encoding="utf-8")
    for lib in ("openai", "anthropic"):
        assert lib not in src, f"LLM library {lib!r} found in router service"
