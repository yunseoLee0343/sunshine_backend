"""Dynamic LLM endpoint registry — TICKET-055.

Resolves the current Qwen vLLM endpoint from one of three sources:
  env  — static config (QWEN_LLM_BASE_URL), default
  file — JSON file at QWEN_ENDPOINT_REGISTRY_FILE, fallback to env if missing
  db   — runtime_endpoints table, fallback to env if no active row
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_VALID_SCHEMES = ("http://", "https://")


def _validate_url(url: str) -> str:
    url = url.rstrip("/")
    if not any(url.startswith(s) for s in _VALID_SCHEMES):
        raise ValueError(f"Invalid endpoint URL (must start with http:// or https://): {url!r}")
    return url


@dataclass(frozen=True)
class LLMEndpoint:
    provider: str
    model: str
    base_url: str
    api_key: str | None
    timeout_seconds: float
    source: str
    updated_at: datetime | None = None


class EndpointRegistry:
    """Resolves the active Qwen LLM endpoint without making network calls."""

    def __init__(self, settings, session_factory=None) -> None:
        self._settings = settings
        self._session_factory = session_factory  # required for db mode only

    async def resolve_qwen_endpoint(self) -> LLMEndpoint:
        mode = self._settings.QWEN_ENDPOINT_REGISTRY_MODE
        if mode == "file":
            return await self._resolve_from_file()
        if mode == "db":
            return await self._resolve_from_db()
        return self._resolve_from_env()

    # ------------------------------------------------------------------
    # Env mode
    # ------------------------------------------------------------------

    def _resolve_from_env(self) -> LLMEndpoint:
        return LLMEndpoint(
            provider="qwen",
            model=self._settings.QWEN_LLM_MODEL,
            base_url=_validate_url(self._settings.QWEN_LLM_BASE_URL),
            api_key=self._settings.QWEN_LLM_API_KEY or None,
            timeout_seconds=float(self._settings.QWEN_LLM_TIMEOUT_SECONDS),
            source="env",
        )

    # ------------------------------------------------------------------
    # File mode
    # ------------------------------------------------------------------

    async def _resolve_from_file(self) -> LLMEndpoint:
        path = Path(self._settings.QWEN_ENDPOINT_REGISTRY_FILE)
        if not path.exists():
            base = self._resolve_from_env()
            return LLMEndpoint(
                provider=base.provider,
                model=base.model,
                base_url=base.base_url,
                api_key=base.api_key,
                timeout_seconds=base.timeout_seconds,
                source="env_fallback",
            )

        data = json.loads(path.read_text(encoding="utf-8"))
        if "base_url" not in data:
            raise ValueError(f"Missing 'base_url' in endpoint file: {path}")

        updated_at: datetime | None = None
        raw_ts = data.get("updated_at")
        if raw_ts:
            try:
                updated_at = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        return LLMEndpoint(
            provider=data.get("provider", "qwen"),
            model=data.get("model", self._settings.QWEN_LLM_MODEL),
            base_url=_validate_url(data["base_url"]),
            api_key=data.get("api_key") or self._settings.QWEN_LLM_API_KEY or None,
            timeout_seconds=float(
                data.get("timeout_seconds", self._settings.QWEN_LLM_TIMEOUT_SECONDS)
            ),
            source="file",
            updated_at=updated_at,
        )

    # ------------------------------------------------------------------
    # DB mode
    # ------------------------------------------------------------------

    async def _resolve_from_db(self) -> LLMEndpoint:
        if self._session_factory is None:
            raise RuntimeError("EndpointRegistry: session_factory required for db mode")

        from app.repositories.runtime_endpoint_repository import RuntimeEndpointRepository

        async with self._session_factory() as session:
            repo = RuntimeEndpointRepository(session)
            row = await repo.get_active("qwen_llm")

        if row is None:
            base = self._resolve_from_env()
            return LLMEndpoint(
                provider=base.provider,
                model=base.model,
                base_url=base.base_url,
                api_key=base.api_key,
                timeout_seconds=base.timeout_seconds,
                source="env_fallback",
            )

        return LLMEndpoint(
            provider=row.provider,
            model=row.model,
            base_url=_validate_url(row.base_url),
            api_key=self._settings.QWEN_LLM_API_KEY or None,
            timeout_seconds=float(self._settings.QWEN_LLM_TIMEOUT_SECONDS),
            source="db",
            updated_at=row.updated_at,
        )
