"""TICKET-003 — Boundary tests.

Verifies that vision-related heavy libraries, forbidden directories, and
disease/pest/health classifier code are absent from the project.
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
    # app/rules is implemented in TICKET-008.
    # app/llm is implemented in TICKET-013.
    "app/rag",
    # app/retrieval is implemented in TICKET-014C
    "app/workers",
    "models",
    "weights",
    "checkpoints",
    "deploy",
]


@pytest.mark.parametrize("forbidden_dir", FORBIDDEN_DIRS)
def test_forbidden_directory_absent(forbidden_dir: str) -> None:
    assert not (ROOT / forbidden_dir).exists(), f"Forbidden directory exists: {forbidden_dir}"


# ---------------------------------------------------------------------------
# app/vision is allowed but only with the port + mock files
# ---------------------------------------------------------------------------


def test_vision_dir_exists_for_ticket3() -> None:
    assert (APP_DIR / "vision").is_dir()


def test_vision_dir_only_contains_allowed_modules() -> None:
    # plant_id_species_classifier.py added by T-003C
    allowed = {
        "__init__.py",
        "species_classifier.py",
        "mock_species_classifier.py",
        "plant_id_species_classifier.py",
    }
    actual = {p.name for p in (APP_DIR / "vision").iterdir() if p.is_file() and p.suffix == ".py"}
    extra = actual - allowed
    assert not extra, f"Unexpected files under app/vision: {extra}"


# ---------------------------------------------------------------------------
# Forbidden classifier / orchestrator modules — must not exist
# ---------------------------------------------------------------------------

FORBIDDEN_FILES = [
    "app/services/health_classifier.py",
    "app/services/disease_classifier.py",
    "app/services/pest_classifier.py",
    # evidence_builder.py implemented in TICKET-015
    # prompt_builder.py implemented in TICKET-016
    # chat_orchestrator.py implemented in TICKET-018
    # audit_repository.py implemented in TICKET-022 — no longer forbidden.
    # chunk_repository.py implemented in TICKET-014B
    "app/models/vision_model.py",
]


@pytest.mark.parametrize("forbidden_file", FORBIDDEN_FILES)
def test_forbidden_file_absent(forbidden_file: str) -> None:
    assert not (ROOT / forbidden_file).exists(), f"Forbidden file exists: {forbidden_file}"


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
    "cv2",
    "PIL",
    "transformers",
    "timm",
    "ultralytics",
    # sentence_transformers allowed from TICKET-014B (local embedding)
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
    assert lib not in _APP_IMPORTS, f"Forbidden library '{lib}' is imported in app source"


def test_forbidden_libs_not_in_sys_modules_after_app_import() -> None:
    """Importing app must not pull in any heavy ML / image library."""
    # Force a fresh import of app.main and then check sys.modules.
    import app.main  # noqa: F401

    leaked = {
        "torch",
        "torchvision",
        "tensorflow",
        "cv2",
        "PIL",
        "onnxruntime",
        "openvino",
        "transformers",
        "ultralytics",
        "vllm",
        "openai",
        "anthropic",
        # paho is introduced in TICKET-006 — not leaked by app.main import.
    } & set(sys.modules.keys())
    assert not leaked, f"Forbidden libs leaked into sys.modules: {leaked}"


# ---------------------------------------------------------------------------
# Forbidden image-IO call patterns inside app/
# ---------------------------------------------------------------------------

FORBIDDEN_IO_PATTERNS = [
    "Image.open",
    "cv2.imread",
    "requests.get",
    "httpx.get",
    "urlopen",
    "exifread",
]


@pytest.mark.parametrize("pattern", FORBIDDEN_IO_PATTERNS)
def test_no_image_io_call_patterns(pattern: str) -> None:
    assert pattern not in _APP_SOURCE, f"Forbidden image-IO call pattern '{pattern}' found in app source"


# ---------------------------------------------------------------------------
# Disease / pest / health classifier names must not appear as public symbols
# ---------------------------------------------------------------------------

FORBIDDEN_SYMBOLS = [
    "DiseaseClassifier",
    "PestClassifier",
    "HealthClassifier",
    "DiseasePrediction",
    "PestPrediction",
    "HealthPrediction",
]


@pytest.mark.parametrize("symbol", FORBIDDEN_SYMBOLS)
def test_no_forbidden_symbol(symbol: str) -> None:
    assert symbol not in _APP_SOURCE, f"Forbidden symbol '{symbol}' found in app source"


# ---------------------------------------------------------------------------
# pyproject.toml — forbidden dependencies must not be declared
# ---------------------------------------------------------------------------


def test_pyproject_does_not_declare_forbidden_deps() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()
    forbidden_deps = [
        "torch",
        "torchvision",
        "tensorflow",
        "keras",
        "onnxruntime",
        "openvino",
        "opencv-python",
        "pillow",
        "transformers",
        "timm",
        "ultralytics",
        "sentence-transformers",
        "vllm",
        "openai",
        "anthropic",
        "redis",
        # paho-mqtt is added in TICKET-006.
        "pgvector",
    ]
    for dep in forbidden_deps:
        # Match as a quoted dependency entry (e.g. "torch>=" or "torch")
        assert f'"{dep}' not in pyproject, f"Forbidden dependency '{dep}' declared in pyproject.toml"


# ---------------------------------------------------------------------------
# /healthz and /readyz contracts unchanged
# ---------------------------------------------------------------------------


def test_healthz_unchanged_no_vision_or_db_check() -> None:
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
    for forbidden in ("check_db", "classifier", "vision", "model"):
        assert forbidden not in body, f"/healthz must not reference '{forbidden}'"


def test_readyz_does_not_check_vision_or_model() -> None:
    main_src = (APP_DIR / "main.py").read_text(encoding="utf-8").lower()
    for forbidden in ("classifier", "vision", "model_files", '"model":', '"vision":'):
        assert forbidden not in main_src, f"/readyz / main.py must not reference '{forbidden}'"
