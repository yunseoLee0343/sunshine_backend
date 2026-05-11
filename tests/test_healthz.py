"""TICKET-000 — /healthz contract tests (maintained through Ticket 1)."""

import asyncio
import importlib
import sys
import types

from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import app

EXPECTED_BODY = {"status": "ok", "service": "sunshine-backend"}

# ---------------------------------------------------------------------------
# /healthz endpoint tests
# ---------------------------------------------------------------------------


def test_healthz_status_200() -> None:
    """GET /healthz must return HTTP 200."""

    async def _run() -> int:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/healthz")
        return response.status_code

    assert asyncio.run(_run()) == 200


def test_healthz_exact_json() -> None:
    """GET /healthz must return exactly the specified JSON body."""

    async def _run() -> dict:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/healthz")
        return response.json()

    assert asyncio.run(_run()) == EXPECTED_BODY


# test_readyz_returns_404 removed: /readyz is now implemented in Ticket 1.
# See tests/test_readyz_contract.py for Ticket 1 /readyz contract tests.


# ---------------------------------------------------------------------------
# Settings defaults
# ---------------------------------------------------------------------------


def test_settings_default_app_name() -> None:
    """Default APP_NAME must equal 'sunshine-backend'."""
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.APP_NAME == "sunshine-backend"


def test_settings_default_app_env() -> None:
    """Default APP_ENV must equal 'local'."""
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.APP_ENV == "local"


# ---------------------------------------------------------------------------
# Import side-effect gate
# ---------------------------------------------------------------------------


def test_import_app_main_no_side_effects() -> None:
    """
    Importing app.main must not trigger DB/Redis/MQTT/LLM/network connections.

    Strategy: remove cached app modules, then install lightweight sentinels for
    known external packages that MUST NOT be imported at startup.  The sentinel
    records access only when Python's import machinery actually calls attributes
    on the module (i.e. when the package is truly used), not when the sentinel
    object is merely constructed and stored in sys.modules.
    """
    # sqlalchemy and asyncpg removed from forbidden list: they are now
    # allowed runtime dependencies introduced in Ticket 1.
    forbidden = [
        "psycopg",
        "redis",
        "paho",
        "paho.mqtt",
        "openai",
        "anthropic",
        "vllm",
        "sentence_transformers",
        "torch",
        "torchvision",
        "transformers",
        "tensorflow",
        "onnxruntime",
        "openvino",
        "cv2",
        "PIL",
    ]

    # Record which forbidden packages are actually *accessed* during import.
    accessed: list[str] = []

    def _make_sentinel(pkg_name: str) -> types.ModuleType:
        """Return a module whose attribute access records the package name."""

        class _Sentinel(types.ModuleType):
            def __getattr__(self, item: str) -> "_Sentinel":  # noqa: ANN401
                accessed.append(pkg_name)
                return _make_sentinel(f"{pkg_name}.{item}")

        return _Sentinel(pkg_name)

    # Back up and remove cached app modules so re-import is clean.
    backup = {k: sys.modules.pop(k) for k in list(sys.modules) if k.startswith("app")}
    sentinel_backup: dict[str, types.ModuleType | None] = {}
    try:
        for pkg in forbidden:
            sentinel_backup[pkg] = sys.modules.get(pkg)
            sys.modules[pkg] = _make_sentinel(pkg)

        importlib.import_module("app.main")

        unique = list(dict.fromkeys(accessed))
        assert not accessed, f"app.main import triggered forbidden package(s): {unique}"
    finally:
        sys.modules.update(backup)
        for pkg, orig in sentinel_backup.items():
            if orig is None:
                sys.modules.pop(pkg, None)
            else:
                sys.modules[pkg] = orig
