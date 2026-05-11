"""MockAudioClient — deterministic keyword-based mock — TICKET-031.

STT: maps audio_uri substrings (case-insensitive) to fixed Korean transcripts.
TTS: generates a stable mock URI from a hash of the text, with duration
     proportional to character count (~70 ms per character).

No external API calls, no file I/O, no audio libraries.
"""

from __future__ import annotations

import hashlib

from app.services.audio_port import (
    AudioMetadata,
    AudioSilenceError,
    AudioTranscriptionError,
    SttResult,
)

_STT_RULES: list[tuple[set[str], str]] = [
    (
        {"water", "물", "watering", "물주기"},
        "몬스테라에 물을 얼마나 자주 줘야 해?",
    ),
    (
        {"light", "빛", "조도", "light_lux"},
        "몬스테라에 빛이 얼마나 필요해?",
    ),
    (
        {"humidity", "습도", "humid"},
        "실내 습도는 얼마나 유지해야 해?",
    ),
    (
        {"temperature", "온도", "temp"},
        "몬스테라 적정 온도가 어떻게 돼?",
    ),
    (
        {"pest", "병충해", "벌레", "mite", "응애"},
        "잎에 점이 생겼는데 병충해인가요?",
    ),
    (
        {"companion", "같이", "함께", "추천"},
        "몬스테라와 함께 키우면 좋은 식물은 뭐가 있어?",
    ),
]

_SILENCE_KEYWORDS = {"silence", "무음", "silent", "quiet"}
_NOISE_KEYWORDS = {"noise", "소음", "unrecognizable", "unclear"}

_TTS_SAMPLE_RATE = 22050
_TTS_SECONDS_PER_CHAR = 0.07  # rough: 70 ms per character


class MockAudioClient:
    """Stateless mock implementing AudioPort.

    Priority order for STT: silence > noise > keyword rules > generic.
    TTS output is fully deterministic: same text → same URI and duration.
    """

    async def stt(self, audio_uri: str, *, locale: str = "ko-KR") -> SttResult:
        key = audio_uri.lower()

        if any(kw in key for kw in _SILENCE_KEYWORDS):
            raise AudioSilenceError(f"no speech detected in audio: {audio_uri!r}")

        if any(kw in key for kw in _NOISE_KEYWORDS):
            raise AudioTranscriptionError(
                f"audio too noisy to transcribe: {audio_uri!r}"
            )

        for keywords, transcript in _STT_RULES:
            if any(kw in key for kw in keywords):
                return SttResult(
                    transcript=transcript,
                    confidence=0.92,
                    language=locale,
                    source="mock_stt",
                )

        return SttResult(
            transcript="식물 관리 방법을 알려줘",
            confidence=0.75,
            language=locale,
            source="mock_stt",
        )

    async def tts(self, text: str, *, locale: str = "ko-KR") -> AudioMetadata:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
        audio_uri = f"mock://tts/{digest}.mp3"
        duration = round(len(text) * _TTS_SECONDS_PER_CHAR, 3)
        return AudioMetadata(
            audio_uri=audio_uri,
            format="mp3",
            sample_rate=_TTS_SAMPLE_RATE,
            duration_seconds=max(duration, 0.5),
        )
