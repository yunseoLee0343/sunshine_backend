"""TICKET-002 — Boundary tests.

Verifies that forbidden directories, endpoints, and library imports are absent.
No live DB required.
"""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Forbidden directories
# ---------------------------------------------------------------------------

FORBIDDEN_DIRS = [
    "app/mqtt",
    "app/llm",
    "app/rag",
    "app/retrieval",
    # app/vision is allowed from TICKET-003 onward (port + mock only).
    "app/workers",
    "app/rules",
]


@pytest.mark.parametrize("forbidden_dir", FORBIDDEN_DIRS)
def test_forbidden_directory_absent(forbidden_dir: str) -> None:
    assert not (ROOT / forbidden_dir).exists(), f"Forbidden directory exists: {forbidden_dir}"


# ---------------------------------------------------------------------------
# Forbidden endpoints in main.py / api layer
# ---------------------------------------------------------------------------

FORBIDDEN_ENDPOINTS = [
    # /sensor-readings is implemented in TICKET-005 — no longer forbidden.
    "/chat",
    "/rules",
    "/companion",
    "/snapshots",
]


def _collect_py_source(base: Path) -> str:
    parts: list[str] = []
    for path in base.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


_APP_SOURCE = _collect_py_source(ROOT / "app")


@pytest.mark.parametrize("endpoint", FORBIDDEN_ENDPOINTS)
def test_forbidden_endpoint_absent(endpoint: str) -> None:
    assert endpoint not in _APP_SOURCE, f"Forbidden endpoint '{endpoint}' found in app source"


# ---------------------------------------------------------------------------
# Forbidden library imports
# ---------------------------------------------------------------------------

FORBIDDEN_LIBS = [
    "torch",
    "torchvision",
    "tensorflow",
    "cv2",
    "PIL",
    "openai",
    "anthropic",
    "vllm",
    "paho",
    "redis",
    "celery",
    "rq",
    "pgvector",
    "sentence_transformers",
    "onnxruntime",
    "openvino",
    "transformers",
]


def _collect_imports(source: str) -> set[str]:
    """Extract top-level module names from import statements via AST."""
    imported: set[str] = []
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


_APP_IMPORTS = _collect_imports(_APP_SOURCE)


@pytest.mark.parametrize("lib", FORBIDDEN_LIBS)
def test_forbidden_library_not_imported(lib: str) -> None:
    assert lib not in _APP_IMPORTS, f"Forbidden library '{lib}' is imported in app source"


# ---------------------------------------------------------------------------
# /healthz and /readyz shape unchanged
# ---------------------------------------------------------------------------


def test_healthz_not_checking_db() -> None:
    """healthz() must not call check_db or any DB function."""
    main_src = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    healthz_lines = []
    in_healthz = False
    for line in main_src.splitlines():
        if "def healthz" in line:
            in_healthz = True
        elif in_healthz and line and not line.startswith(" ") and not line.startswith("\t"):
            break
        if in_healthz:
            healthz_lines.append(line)
    healthz_body = "\n".join(healthz_lines)
    assert "check_db" not in healthz_body
    assert "database" not in healthz_body


def test_readyz_not_checking_extra_services() -> None:
    """readyz must only reference check_db, nothing else."""
    main_src = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert "redis" not in main_src.lower()
    assert "mqtt" not in main_src.lower()
    assert "llm" not in main_src.lower()
