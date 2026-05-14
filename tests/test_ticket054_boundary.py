"""TICKET-054 — boundary tests: transaction ownership and no forbidden imports."""

from __future__ import annotations


def _src(module_name: str) -> str:
    import importlib

    mod = importlib.import_module(module_name)
    return open(mod.__file__, encoding="utf-8").read()


# ---------------------------------------------------------------------------
# Transaction ownership
# ---------------------------------------------------------------------------


def test_sensor_ingest_service_does_not_commit() -> None:
    src = _src("app.services.sensor_ingest")
    assert "session.commit" not in src


def test_sensor_ingest_service_relies_on_autoflush() -> None:
    src = _src("app.services.sensor_ingest")
    # Explicit flush removed — relies on SQLAlchemy autoflush before SELECTs.
    assert "session.flush" not in src


def test_rest_endpoint_commits_after_ingest() -> None:
    src = _src("app.api.sensor_readings")
    assert "session.commit" in src


def test_rest_endpoint_rolls_back_on_exception() -> None:
    src = _src("app.api.sensor_readings")
    assert "session.rollback" in src


def test_mqtt_ingest_commits_after_aggregate() -> None:
    src = _src("app.services.mqtt_sensor_ingest")
    assert "_session.commit" in src


def test_mqtt_ingest_rolls_back_on_failure() -> None:
    src = _src("app.services.mqtt_sensor_ingest")
    assert "_session.rollback" in src


# ---------------------------------------------------------------------------
# No forbidden imports
# ---------------------------------------------------------------------------


def test_sensor_ingest_no_llm() -> None:
    src = _src("app.services.sensor_ingest")
    for forbidden in ("LLMPort", "QwenLLMClient", "PromptBuilder", "EvidenceBuilder"):
        assert forbidden not in src


def test_mqtt_ingest_no_llm() -> None:
    src = _src("app.services.mqtt_sensor_ingest")
    for forbidden in ("LLMPort", "QwenLLMClient", "PromptBuilder", "EvidenceBuilder"):
        assert forbidden not in src


def test_environment_detail_service_no_db_write() -> None:
    src = _src("app.services.environment_detail_service")
    assert "session.add" not in src
    assert "session.commit" not in src


def test_snapshot_service_does_not_commit() -> None:
    src = _src("app.services.snapshot_service")
    assert "session.commit" not in src
    assert "commit" not in src
