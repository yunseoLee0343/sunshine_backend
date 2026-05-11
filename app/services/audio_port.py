"""AudioPort Protocol and STT/TTS schemas — TICKET-031."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class AudioMetadata(BaseModel):
    audio_uri: str
    format: str  # "mp3" | "wav"
    sample_rate: int
    duration_seconds: float


class SttResult(BaseModel):
    transcript: str
    confidence: float
    language: str
    source: str


class AudioTranscriptionError(Exception):
    """Raised when speech cannot be recognized from the audio input."""


class AudioSilenceError(AudioTranscriptionError):
    """Raised when audio contains no detectable speech (silent input)."""


@runtime_checkable
class AudioPort(Protocol):
    async def stt(self, audio_uri: str, *, locale: str = "ko-KR") -> SttResult: ...
    async def tts(self, text: str, *, locale: str = "ko-KR") -> AudioMetadata: ...
