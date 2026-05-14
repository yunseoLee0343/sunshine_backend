"""TICKET-047 — RAG seed import contract tests."""

from __future__ import annotations

from pathlib import Path


def test_import_script_exists() -> None:
    assert Path("scripts/import_rag_seed.sh").exists()


def test_import_script_contains_docker_psql_command() -> None:
    src = Path("scripts/import_rag_seed.sh").read_text(encoding="utf-8")
    assert "docker compose exec -T postgres psql -U sunshine sunshine" in src


def test_import_script_fails_fast_on_missing_file() -> None:
    src = Path("scripts/import_rag_seed.sh").read_text(encoding="utf-8")
    assert "exit 1" in src
    assert "not found" in src.lower() or "ERROR" in src


def test_import_script_does_not_run_migrations() -> None:
    src = Path("scripts/import_rag_seed.sh").read_text(encoding="utf-8")
    assert "alembic" not in src
    assert "upgrade" not in src


def test_import_script_does_not_start_services() -> None:
    src = Path("scripts/import_rag_seed.sh").read_text(encoding="utf-8")
    assert "docker compose up" not in src
    assert "docker-compose up" not in src


def test_validate_sql_script_exists() -> None:
    assert Path("scripts/validate_rag_seed_sql.py").exists()


def test_validate_db_script_exists() -> None:
    assert Path("scripts/validate_rag_seed_db.py").exists()


def test_validate_db_script_is_read_only() -> None:
    """DB validation script must contain only SELECT statements, no DML."""
    src = Path("scripts/validate_rag_seed_db.py").read_text(encoding="utf-8")
    for forbidden in ("INSERT INTO", "UPDATE ", "DELETE FROM", "DROP TABLE", "CREATE TABLE"):
        assert forbidden not in src, f"Write operation found in validate_rag_seed_db.py: {forbidden!r}"


def test_seed_import_not_called_at_app_startup() -> None:
    """App startup modules must not reference the seed import script."""
    startup_files = [
        Path("app/main.py"),
        Path("app/db/session.py"),
    ]
    for p in startup_files:
        if p.exists():
            src = p.read_text(encoding="utf-8")
            assert "import_rag_seed" not in src
            assert "rag_knowledge_seed" not in src


def test_seed_command_documented() -> None:
    """The exact import command must appear in TICKET_047.md."""
    doc = Path("docs/TICKET_047.md")
    if doc.exists():
        src = doc.read_text(encoding="utf-8")
        assert "docker compose exec -T postgres psql -U sunshine sunshine" in src
