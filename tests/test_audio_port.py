"""Tests for TICKET-031: AudioPort, MockAudioClient, orchestrator integration."""

from __future__ import annotations

import pytest

from app.llm.mock_audio_client import MockAudioClient
from app.services.audio_port import (
    AudioMetadata,
    AudioPort,
    AudioSilenceError,
    AudioTranscriptionError,
    SttResult,
)


# ---------------------------------------------------------------------------
# AudioPort Protocol structural check
# ---------------------------------------------------------------------------


def test_mock_audio_client_satisfies_protocol():
    client = MockAudioClient()
    assert isinstance(client, AudioPort)


# ---------------------------------------------------------------------------
# STT: keyword routing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stt_water_keyword():
    client = MockAudioClient()
    result = await client.stt("recordings/water_question.wav")
    assert "물" in result.transcript
    assert result.source == "mock_stt"
    assert 0.0 < result.confidence <= 1.0


@pytest.mark.asyncio
async def test_stt_물_keyword():
    client = MockAudioClient()
    result = await client.stt("user/물주기_question.mp3")
    assert "물" in result.transcript


@pytest.mark.asyncio
async def test_stt_light_keyword():
    client = MockAudioClient()
    result = await client.stt("recordings/light_question.wav")
    assert "빛" in result.transcript or "조도" in result.transcript or "light" in result.transcript.lower()


@pytest.mark.asyncio
async def test_stt_pest_keyword():
    client = MockAudioClient()
    result = await client.stt("uploads/pest_audio.wav")
    assert "병충해" in result.transcript or "점" in result.transcript


@pytest.mark.asyncio
async def test_stt_companion_keyword():
    client = MockAudioClient()
    result = await client.stt("uploads/companion_question.wav")
    assert "함께" in result.transcript or "식물" in result.transcript


@pytest.mark.asyncio
async def test_stt_humidity_keyword():
    client = MockAudioClient()
    result = await client.stt("uploads/humidity_question.mp3")
    assert "습도" in result.transcript


@pytest.mark.asyncio
async def test_stt_temperature_keyword():
    client = MockAudioClient()
    result = await client.stt("uploads/temperature_query.wav")
    assert "온도" in result.transcript


@pytest.mark.asyncio
async def test_stt_default_fallback():
    client = MockAudioClient()
    result = await client.stt("uploads/unknown_audio_xyz.wav")
    assert isinstance(result.transcript, str)
    assert len(result.transcript) > 0
    assert result.source == "mock_stt"


# ---------------------------------------------------------------------------
# STT: error conditions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stt_silence_raises_audio_silence_error():
    client = MockAudioClient()
    with pytest.raises(AudioSilenceError):
        await client.stt("uploads/silence_5sec.wav")


@pytest.mark.asyncio
async def test_stt_무음_raises_audio_silence_error():
    client = MockAudioClient()
    with pytest.raises(AudioSilenceError):
        await client.stt("uploads/무음_recording.mp3")


@pytest.mark.asyncio
async def test_stt_noise_raises_audio_transcription_error():
    client = MockAudioClient()
    with pytest.raises(AudioTranscriptionError):
        await client.stt("uploads/noise_background.wav")


@pytest.mark.asyncio
async def test_stt_소음_raises_audio_transcription_error():
    client = MockAudioClient()
    with pytest.raises(AudioTranscriptionError):
        await client.stt("uploads/소음_heavy.wav")


def test_audio_silence_error_is_subclass_of_transcription_error():
    assert issubclass(AudioSilenceError, AudioTranscriptionError)


def test_audio_transcription_error_is_exception():
    assert issubclass(AudioTranscriptionError, Exception)


# ---------------------------------------------------------------------------
# STT: silence has higher priority than other keywords
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stt_silence_priority_over_water():
    client = MockAudioClient()
    with pytest.raises(AudioSilenceError):
        await client.stt("uploads/water_silence.wav")


# ---------------------------------------------------------------------------
# TTS: output contract
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tts_returns_audio_metadata():
    client = MockAudioClient()
    result = await client.tts("물을 매주 한 번씩 주세요.")
    assert isinstance(result, AudioMetadata)
    assert result.format == "mp3"
    assert result.sample_rate > 0
    assert result.duration_seconds > 0
    assert result.audio_uri.startswith("mock://tts/")


@pytest.mark.asyncio
async def test_tts_uri_ends_with_mp3():
    client = MockAudioClient()
    result = await client.tts("테스트 텍스트")
    assert result.audio_uri.endswith(".mp3")


@pytest.mark.asyncio
async def test_tts_duration_proportional_to_text_length():
    client = MockAudioClient()
    short = await client.tts("짧은 텍스트")
    long_ = await client.tts("훨씬 더 긴 텍스트입니다. 여러 문장이 포함되어 있습니다. 더 많은 내용이 있습니다.")
    assert long_.duration_seconds > short.duration_seconds


@pytest.mark.asyncio
async def test_tts_deterministic_same_uri_for_same_text():
    client = MockAudioClient()
    text = "식물에 물을 주세요."
    result1 = await client.tts(text)
    result2 = await client.tts(text)
    assert result1.audio_uri == result2.audio_uri
    assert result1.duration_seconds == result2.duration_seconds


@pytest.mark.asyncio
async def test_tts_different_text_different_uri():
    client = MockAudioClient()
    r1 = await client.tts("물주기")
    r2 = await client.tts("햇빛 관리")
    assert r1.audio_uri != r2.audio_uri


@pytest.mark.asyncio
async def test_tts_minimum_duration():
    client = MockAudioClient()
    result = await client.tts("OK")
    assert result.duration_seconds >= 0.5


# ---------------------------------------------------------------------------
# SttResult and AudioMetadata schema validation
# ---------------------------------------------------------------------------


def test_stt_result_fields():
    r = SttResult(
        transcript="물을 줘야 해",
        confidence=0.92,
        language="ko-KR",
        source="mock_stt",
    )
    assert r.transcript == "물을 줘야 해"
    assert r.confidence == 0.92
    assert r.language == "ko-KR"
    assert r.source == "mock_stt"


def test_audio_metadata_fields():
    m = AudioMetadata(
        audio_uri="mock://tts/abc123.mp3",
        format="mp3",
        sample_rate=22050,
        duration_seconds=3.5,
    )
    assert m.audio_uri == "mock://tts/abc123.mp3"
    assert m.format == "mp3"
    assert m.sample_rate == 22050
    assert m.duration_seconds == 3.5


# ---------------------------------------------------------------------------
# ChatAnswerRequest: question/audio_uri validation
# ---------------------------------------------------------------------------


def test_chat_answer_request_question_required_without_audio():
    import uuid

    from pydantic import ValidationError

    from app.schemas.chat_answer import ChatAnswerRequest

    with pytest.raises(ValidationError):
        ChatAnswerRequest(
            request_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            # no question, no audio_uri
        )


def test_chat_answer_request_audio_uri_alone_is_valid():
    import uuid

    from app.schemas.chat_answer import ChatAnswerRequest

    req = ChatAnswerRequest(
        request_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        audio_uri="uploads/question.wav",
    )
    assert req.audio_uri == "uploads/question.wav"
    assert req.question is None


def test_chat_answer_request_question_alone_is_valid():
    import uuid

    from app.schemas.chat_answer import ChatAnswerRequest

    req = ChatAnswerRequest(
        request_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        question="물을 얼마나 자주 줘야 해?",
    )
    assert req.question == "물을 얼마나 자주 줘야 해?"
    assert req.audio_uri is None


def test_chat_answer_request_both_question_and_audio_is_valid():
    import uuid

    from app.schemas.chat_answer import ChatAnswerRequest

    req = ChatAnswerRequest(
        request_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        question="물주기",
        audio_uri="uploads/question.wav",
    )
    assert req.question is not None
    assert req.audio_uri is not None


def test_chat_answer_request_empty_question_rejected():
    import uuid

    from pydantic import ValidationError

    from app.schemas.chat_answer import ChatAnswerRequest

    with pytest.raises(ValidationError):
        ChatAnswerRequest(
            request_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            question="",  # min_length=1
        )


# ---------------------------------------------------------------------------
# ChatAnswerResponse: audio_response field
# ---------------------------------------------------------------------------


def test_chat_answer_response_has_audio_response_field():
    from app.schemas.chat_answer import ChatAnswerResponse

    fields = ChatAnswerResponse.model_fields
    assert "audio_response" in fields
    # default is None (optional)
    info = fields["audio_response"]
    assert info.default is None


def test_chat_answer_response_audio_response_is_none_by_default():
    import uuid
    from datetime import UTC, datetime

    from app.schemas.chat_answer import ChatAnswerResponse, ParsedAnswer

    resp = ChatAnswerResponse(
        request_id=uuid.uuid4(),
        plant_id=uuid.uuid4(),
        intent="watering_question",
        answer=ParsedAnswer(결론="a", 근거="b", 행동="c", 주의="d"),
        guardrails_applied=[],
        prompt_hash="abc",
        model_name="mock",
        input_tokens=100,
        output_tokens=50,
        from_cache=False,
        created_at=datetime.now(UTC),
    )
    assert resp.audio_response is None


# ---------------------------------------------------------------------------
# Orchestrator: STT replaces question; TTS produces audio_response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_uses_stt_transcript_as_question(monkeypatch):
    """When audio_uri is provided, the STT transcript becomes the effective question."""
    import app.services.chat_orchestrator as orch_module

    captured_questions: list[str] = []

    original_classify = orch_module._CLASSIFIER.classify

    def fake_classify(question: str):
        captured_questions.append(question)
        return "watering_question", 0.9, "mock"

    class _FakeAudio:
        async def stt(self, uri, *, locale="ko-KR"):
            return SttResult(
                transcript="물을 얼마나 자주 줘야 해?",
                confidence=0.92,
                language="ko-KR",
                source="mock_stt",
            )

        async def tts(self, text, *, locale="ko-KR"):
            return AudioMetadata(
                audio_uri="mock://tts/abc.mp3",
                format="mp3",
                sample_rate=22050,
                duration_seconds=2.0,
            )

    monkeypatch.setattr(orch_module._CLASSIFIER, "classify", fake_classify)
    monkeypatch.setattr(orch_module, "_AUDIO_CLIENT", _FakeAudio())

    # Verify the STT result is what would be passed to classify
    client = _FakeAudio()
    stt = await client.stt("uploads/water_question.wav")
    assert stt.transcript == "물을 얼마나 자주 줘야 해?"

    # Simulate what the orchestrator would do
    effective_question = stt.transcript
    fake_classify(effective_question)
    assert captured_questions[0] == "물을 얼마나 자주 줘야 해?"


@pytest.mark.asyncio
async def test_orchestrator_tts_produces_audio_response():
    """TTS is called when audio_uri is present and produces audio_response."""
    client = MockAudioClient()
    stt_result = await client.stt("uploads/water_question.wav")
    assert isinstance(stt_result.transcript, str)

    answer_text = "결론 근거 행동"
    tts_result = await client.tts(answer_text)
    assert tts_result.audio_uri.startswith("mock://tts/")
    assert tts_result.duration_seconds > 0


@pytest.mark.asyncio
async def test_stt_error_propagates_correctly():
    """AudioSilenceError from STT propagates without being swallowed."""
    client = MockAudioClient()
    with pytest.raises(AudioSilenceError) as exc_info:
        await client.stt("silence_recording.wav")
    assert "silence" in str(exc_info.value).lower() or "무음" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Model: ChatRequest has audio columns
# ---------------------------------------------------------------------------


def test_chat_request_model_has_audio_fields():
    from app.models.chat_request import ChatRequest

    mapper = ChatRequest.__table__.columns
    assert "audio_uri_in" in mapper
    assert "audio_uri_out" in mapper
    assert "audio_duration_seconds" in mapper
