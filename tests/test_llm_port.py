"""TICKET-017 — LLMPort + MockLLMClient tests (no network, no DB)."""

from __future__ import annotations

import uuid

import pytest

from app.llm.mock_client import _MODEL_NAME, _PROVIDER, MockLLMClient
from app.services.llm_port import (
    LLMPort,
    LLMRequest,
    LLMResponse,
    ModelMetadata,
    StreamingNotSupportedError,
)
from app.utils.hash import prompt_hash, short_hash

# ---------------------------------------------------------------------------
# Utils
# ---------------------------------------------------------------------------


def test_prompt_hash_returns_64_char_hex() -> None:
    h = prompt_hash("hello")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_prompt_hash_is_deterministic() -> None:
    assert prompt_hash("test") == prompt_hash("test")


def test_prompt_hash_differs_for_different_inputs() -> None:
    assert prompt_hash("a") != prompt_hash("b")


def test_short_hash_default_length() -> None:
    h = short_hash("hello")
    assert len(h) == 8


def test_short_hash_custom_length() -> None:
    h = short_hash("hello", length=16)
    assert len(h) == 16


def test_short_hash_is_prefix_of_prompt_hash() -> None:
    text = "test text"
    assert prompt_hash(text).startswith(short_hash(text))


# ---------------------------------------------------------------------------
# LLMRequest / LLMResponse / ModelMetadata
# ---------------------------------------------------------------------------


def test_llm_request_defaults() -> None:
    req = LLMRequest(
        request_id=uuid.uuid4(),
        system_prompt="system",
        user_turn="question",
        prompt_hash=prompt_hash("system"),
    )
    assert req.max_tokens == 1024
    assert req.temperature == 0.0
    assert req.stream is False


def test_llm_request_is_frozen() -> None:
    req = LLMRequest(
        request_id=uuid.uuid4(),
        system_prompt="sys",
        user_turn="q",
        prompt_hash="abc",
    )
    with pytest.raises((AttributeError, TypeError)):
        req.max_tokens = 2048  # type: ignore[misc]


def test_model_metadata_is_frozen() -> None:
    m = ModelMetadata(model_name="x", provider="y")
    with pytest.raises((AttributeError, TypeError)):
        m.model_name = "z"  # type: ignore[misc]


def test_llm_response_is_frozen() -> None:
    resp = LLMResponse(
        request_id=uuid.uuid4(),
        content="content",
        prompt_hash="abc",
        model_metadata=ModelMetadata(model_name="m", provider="p"),
        input_tokens=10,
        output_tokens=20,
        finish_reason="stop",
    )
    with pytest.raises((AttributeError, TypeError)):
        resp.content = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# LLMPort structural check
# ---------------------------------------------------------------------------


def test_mock_client_satisfies_llm_port_protocol() -> None:
    client = MockLLMClient()
    assert isinstance(client, LLMPort)


# ---------------------------------------------------------------------------
# MockLLMClient: basic completion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mock_complete_returns_response() -> None:
    client = MockLLMClient()
    req = LLMRequest(
        request_id=uuid.uuid4(),
        system_prompt="식물 관리 AI",
        user_turn="물주기 알려줘",
        prompt_hash=prompt_hash("식물 관리 AI"),
    )
    resp = await client.complete(req)
    assert isinstance(resp, LLMResponse)
    assert resp.finish_reason == "stop"


@pytest.mark.asyncio
async def test_mock_complete_echoes_request_id() -> None:
    client = MockLLMClient()
    rid = uuid.uuid4()
    req = LLMRequest(
        request_id=rid,
        system_prompt="sys",
        user_turn="q",
        prompt_hash=prompt_hash("sys"),
    )
    resp = await client.complete(req)
    assert resp.request_id == rid


@pytest.mark.asyncio
async def test_mock_complete_echoes_prompt_hash() -> None:
    client = MockLLMClient()
    ph = prompt_hash("some system prompt")
    req = LLMRequest(
        request_id=uuid.uuid4(),
        system_prompt="some system prompt",
        user_turn="q",
        prompt_hash=ph,
    )
    resp = await client.complete(req)
    assert resp.prompt_hash == ph


@pytest.mark.asyncio
async def test_mock_model_metadata() -> None:
    client = MockLLMClient()
    req = LLMRequest(
        request_id=uuid.uuid4(),
        system_prompt="s",
        user_turn="q",
        prompt_hash=prompt_hash("s"),
    )
    resp = await client.complete(req)
    assert resp.model_metadata.model_name == _MODEL_NAME
    assert resp.model_metadata.provider == _PROVIDER


# ---------------------------------------------------------------------------
# MockLLMClient: fixed answer format
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mock_response_contains_결론() -> None:
    client = MockLLMClient()
    req = LLMRequest(
        request_id=uuid.uuid4(),
        system_prompt="s",
        user_turn="q",
        prompt_hash=prompt_hash("s"),
    )
    resp = await client.complete(req)
    assert "[결론]" in resp.content


@pytest.mark.asyncio
async def test_mock_response_contains_근거() -> None:
    client = MockLLMClient()
    req = LLMRequest(
        request_id=uuid.uuid4(),
        system_prompt="s",
        user_turn="q",
        prompt_hash=prompt_hash("s"),
    )
    resp = await client.complete(req)
    assert "[근거]" in resp.content


@pytest.mark.asyncio
async def test_mock_response_contains_행동() -> None:
    client = MockLLMClient()
    req = LLMRequest(
        request_id=uuid.uuid4(),
        system_prompt="s",
        user_turn="q",
        prompt_hash=prompt_hash("s"),
    )
    resp = await client.complete(req)
    assert "[행동]" in resp.content


@pytest.mark.asyncio
async def test_mock_response_contains_주의() -> None:
    client = MockLLMClient()
    req = LLMRequest(
        request_id=uuid.uuid4(),
        system_prompt="s",
        user_turn="q",
        prompt_hash=prompt_hash("s"),
    )
    resp = await client.complete(req)
    assert "[주의]" in resp.content


# ---------------------------------------------------------------------------
# MockLLMClient: determinism
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mock_is_deterministic_same_hash() -> None:
    client = MockLLMClient()
    ph = prompt_hash("identical system prompt")
    req = LLMRequest(
        request_id=uuid.uuid4(),
        system_prompt="identical system prompt",
        user_turn="q",
        prompt_hash=ph,
    )
    r1 = await client.complete(req)
    # Different request_id, same prompt_hash
    req2 = LLMRequest(
        request_id=uuid.uuid4(),
        system_prompt="identical system prompt",
        user_turn="q",
        prompt_hash=ph,
    )
    r2 = await client.complete(req2)
    assert r1.content == r2.content


@pytest.mark.asyncio
async def test_mock_varies_with_different_hash() -> None:
    """Different prompt_hashes should be able to produce different content."""
    client = MockLLMClient()
    # We need hashes that produce different variation indices
    # Try many prompts until we find two with different content
    contents: set[str] = set()
    for i in range(20):
        ph = prompt_hash(f"prompt variant {i}")
        req = LLMRequest(
            request_id=uuid.uuid4(),
            system_prompt=f"prompt variant {i}",
            user_turn="q",
            prompt_hash=ph,
        )
        resp = await client.complete(req)
        contents.add(resp.content)
    assert len(contents) > 1, "Mock should produce at least 2 distinct responses"


# ---------------------------------------------------------------------------
# MockLLMClient: streaming rejection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mock_raises_on_stream_true() -> None:
    client = MockLLMClient()
    req = LLMRequest(
        request_id=uuid.uuid4(),
        system_prompt="s",
        user_turn="q",
        prompt_hash=prompt_hash("s"),
        stream=True,
    )
    with pytest.raises(StreamingNotSupportedError):
        await client.complete(req)


# ---------------------------------------------------------------------------
# MockLLMClient: guardrail awareness
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mock_watering_ban_respected() -> None:
    client = MockLLMClient()
    system_with_ban = "식물 관리 AI\n물주기 금지: 현재 상태에서는 물을 주지 마세요."
    req = LLMRequest(
        request_id=uuid.uuid4(),
        system_prompt=system_with_ban,
        user_turn="물주기 알려줘",
        prompt_hash=prompt_hash(system_with_ban),
    )
    resp = await client.complete(req)
    # [행동] section must not recommend watering when "물주기 금지" is in prompt
    action_start = resp.content.index("[행동]")
    next_section = resp.content.find("[주의]", action_start)
    action_text = resp.content[action_start:next_section]
    assert "물주기는 권장하지 않습니다" in action_text


@pytest.mark.asyncio
async def test_mock_pest_guardrail_adds_disclaimer() -> None:
    client = MockLLMClient()
    system_with_pest = "식물 관리 AI\n참고용 지식: 병충해 정보는 참고 목적입니다."
    req = LLMRequest(
        request_id=uuid.uuid4(),
        system_prompt=system_with_pest,
        user_turn="병충해 알려줘",
        prompt_hash=prompt_hash(system_with_pest),
    )
    resp = await client.complete(req)
    assert "참고용 지식" in resp.content
    assert "전문 농업 기관" in resp.content


@pytest.mark.asyncio
async def test_mock_unknown_mode_requests_clarification() -> None:
    client = MockLLMClient()
    system_with_unknown = "식물 관리 AI\n추가 정보가 필요합니다: 질문 의도가 불명확합니다."
    req = LLMRequest(
        request_id=uuid.uuid4(),
        system_prompt=system_with_unknown,
        user_turn="뭔가 이상해",
        prompt_hash=prompt_hash(system_with_unknown),
    )
    resp = await client.complete(req)
    assert "추가 정보" in resp.content


@pytest.mark.asyncio
async def test_mock_rule_authority_mentioned_in_근거() -> None:
    client = MockLLMClient()
    system_with_rule = "식물 관리 AI\n룰 엔진의 결과를 최우선으로 반영하세요."
    req = LLMRequest(
        request_id=uuid.uuid4(),
        system_prompt=system_with_rule,
        user_turn="물주기",
        prompt_hash=prompt_hash(system_with_rule),
    )
    resp = await client.complete(req)
    assert "룰 엔진" in resp.content


# ---------------------------------------------------------------------------
# No forbidden imports
# ---------------------------------------------------------------------------


def test_llm_port_has_no_external_api_imports() -> None:
    import app.services.llm_port as mod

    src = open(mod.__file__, encoding="utf-8").read()
    # Check for "import X" patterns — avoid false-positives from class names like LLMRequest
    for forbidden in ("import openai", "import anthropic", "import requests", "import httpx", "import aiohttp"):
        assert forbidden not in src, f"Forbidden: {forbidden!r}"


def test_mock_client_has_no_external_api_imports() -> None:
    import app.llm.mock_client as mod

    src = open(mod.__file__, encoding="utf-8").read()
    for forbidden in ("import openai", "import anthropic", "import requests", "import httpx", "import aiohttp"):
        assert forbidden not in src, f"Forbidden: {forbidden!r}"
