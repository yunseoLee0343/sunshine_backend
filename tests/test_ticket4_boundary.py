"""TICKET-004 — Boundary tests.

Verifies the absence of Rule Engine, sensor ingestion, snapshot, care-log,
growth-history, home/card, chat, RAG, LLM, MQTT, Redis, vision-runtime
features and dependencies that this ticket forbids.
"""

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
APP_DIR = ROOT / "app"


# ---------------------------------------------------------------------------
# Forbidden directories — must not exist
# ---------------------------------------------------------------------------

FORBIDDEN_DIRS = [
    # app/mqtt is implemented in TICKET-006.
    "app/llm",
    "app/rag",
    "app/retrieval",
    "app/workers",
    "app/rules",
    "deploy",
]


@pytest.mark.parametrize("forbidden_dir", FORBIDDEN_DIRS)
def test_forbidden_directory_absent(forbidden_dir: str) -> None:
    assert not (ROOT / forbidden_dir).exists(), (
        f"Forbidden directory exists: {forbidden_dir}"
    )


# ---------------------------------------------------------------------------
# Forbidden service / repository modules — must not exist
# ---------------------------------------------------------------------------

FORBIDDEN_FILES = [
    "app/services/rule_engine.py",
    # snapshot_service.py and snapshot_repository.py are implemented in TICKET-007.
    # sensor_ingest.py and sensor_repository.py are implemented in TICKET-005.
    "app/services/care_log_service.py",
    "app/services/growth_history_service.py",
    "app/services/home_card_service.py",
    "app/services/evidence_builder.py",
    "app/services/prompt_builder.py",
    "app/services/chat_orchestrator.py",
    # snapshot_repository.py is implemented in TICKET-007.
    "app/repositories/care_log_repository.py",
    "app/repositories/audit_repository.py",
]


@pytest.mark.parametrize("forbidden_file", FORBIDDEN_FILES)
def test_forbidden_file_absent(forbidden_file: str) -> None:
    assert not (ROOT / forbidden_file).exists(), (
        f"Forbidden file exists: {forbidden_file}"
    )


# ---------------------------------------------------------------------------
# Forbidden library imports — must not appear anywhere under app/
# ---------------------------------------------------------------------------

FORBIDDEN_LIBS = [
    "torch",
    "torchvision",
    "tensorflow",
    "keras",
    "onnxruntime",
    "openvino",
    "transformers",
    "sentence_transformers",
    "vllm",
    "openai",
    "anthropic",
    "redis",
    # paho is introduced in TICKET-006 for the mqtt-ingest worker.
    "pgvector",
    "celery",
    "rq",
]


def _collect_imports(source: str) -> set[str]:
    imported: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.append(node.module.split(".")[0])
    return set(imported)


def _collect_app_source() -> str:
    parts: list[str] = []
    for path in APP_DIR.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


_APP_SOURCE = _collect_app_source()
_APP_IMPORTS = _collect_imports(_APP_SOURCE)


@pytest.mark.parametrize("lib", FORBIDDEN_LIBS)
def test_forbidden_library_not_imported(lib: str) -> None:
    assert lib not in _APP_IMPORTS, (
        f"Forbidden library '{lib}' is imported in app source"
    )


def test_forbidden_libs_not_in_sys_modules_after_app_import() -> None:
    """Importing app must not pull in any heavy ML / queue / LLM library."""
    import app.main  # noqa: F401

    leaked = {
        "torch",
        "torchvision",
        "tensorflow",
        "onnxruntime",
        "openvino",
        "transformers",
        "vllm",
        "openai",
        "anthropic",
        # paho is introduced in TICKET-006 — not leaked by app.main import.
        "redis",
    } & set(sys.modules.keys())
    assert not leaked, f"Forbidden libs leaked into sys.modules: {leaked}"


# ---------------------------------------------------------------------------
# Forbidden API routes
# ---------------------------------------------------------------------------


def test_forbidden_routes_not_registered() -> None:
    from app.main import app

    paths = {route.path for route in app.routes}  # type: ignore[attr-defined]
    forbidden_substrings = [
        # /sensor-readings is implemented in TICKET-005 — no longer forbidden.
        "/care-logs",
        "/history",
        "/home",
        "/card",
        "/chat",
    ]
    for needle in forbidden_substrings:
        for p in paths:
            assert needle not in p, f"Forbidden route registered: {p}"


# ---------------------------------------------------------------------------
# Forbidden DB writes — no INSERT into reserved tables anywhere in app/
# ---------------------------------------------------------------------------

FORBIDDEN_DB_WRITES = [
    "sensor_readings",
    "environment_snapshots",
    "care_logs",
    "chat_requests",
    "llm_runs",
    "recommendation_evidence",
    "retrieved_chunks",
]


@pytest.mark.parametrize("table", FORBIDDEN_DB_WRITES)
def test_no_inserts_into_forbidden_tables(table: str) -> None:
    """Forbidden tables may exist as ORM models (legacy) but no service in
    Ticket 4 should write to them. Detect by searching for ``session.add(<Model>``
    patterns referencing the table-backed model class names."""
    forbidden_models = {
        "sensor_readings": "SensorReading",
        "environment_snapshots": "EnvironmentSnapshot",
        "care_logs": "CareLog",
        "chat_requests": "ChatRequest",
        "llm_runs": "LlmRun",
        "recommendation_evidence": "RecommendationEvidence",
        "retrieved_chunks": "RetrievedChunk",
    }
    model = forbidden_models[table]
    # Any service or repository file should not call .add(<Model>(...)).
    for path in APP_DIR.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        # Allow the model file itself.
        if path.name.endswith(f"{table}.py") or path.parent.name == "models":
            continue
        text = path.read_text(encoding="utf-8")
        # Strict pattern: ``add(ModelName(`` indicates a write.
        assert f"add({model}(" not in text, (
            f"Forbidden write to {table} via {model} found in {path}"
        )


# ---------------------------------------------------------------------------
# /healthz and /readyz contracts unchanged
# ---------------------------------------------------------------------------


def test_healthz_unchanged_no_character_or_db_check() -> None:
    main_src = (APP_DIR / "main.py").read_text(encoding="utf-8")
    healthz_lines: list[str] = []
    in_healthz = False
    for line in main_src.splitlines():
        if "def healthz" in line:
            in_healthz = True
        elif in_healthz and line and not line.startswith(" ") and not line.startswith("\t"):
            break
        if in_healthz:
            healthz_lines.append(line)
    body = "\n".join(healthz_lines)
    for forbidden in ("check_db", "character", "rule_engine", "vision", "model"):
        assert forbidden not in body, (
            f"/healthz must not reference '{forbidden}'"
        )


def test_readyz_does_not_check_character_or_rule_engine() -> None:
    main_src = (APP_DIR / "main.py").read_text(encoding="utf-8").lower()
    for forbidden in (
        "character_state",
        "rule_engine",
        "classifier",
        "vision",
        '"character_state":',
        '"rule_engine":',
    ):
        assert forbidden not in main_src, (
            f"/readyz / main.py must not reference '{forbidden}'"
        )


# ---------------------------------------------------------------------------
# pyproject.toml — forbidden dependencies must not be declared
# ---------------------------------------------------------------------------


def test_pyproject_does_not_declare_forbidden_deps() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()
    forbidden_deps = [
        "openai",
        "anthropic",
        "vllm",
        "torch",
        "tensorflow",
        "onnxruntime",
        "openvino",
        "redis",
        # paho-mqtt is added in TICKET-006.
        "pgvector",
        "sentence-transformers",
    ]
    for dep in forbidden_deps:
        assert f'"{dep}' not in pyproject, (
            f"Forbidden dependency '{dep}' declared in pyproject.toml"
        )


# ---------------------------------------------------------------------------
# Domain layer is pure — no SQLAlchemy / FastAPI imports
# ---------------------------------------------------------------------------


def test_domain_character_state_is_pure() -> None:
    src = (APP_DIR / "domain" / "character_state.py").read_text(encoding="utf-8")
    forbidden = ["sqlalchemy", "fastapi", "httpx", "requests"]
    for needle in forbidden:
        assert needle not in src, f"app/domain/character_state.py imports {needle}"
