"""TICKET-053 — boundary tests: no forbidden imports in changed modules."""

from __future__ import annotations

_FORBIDDEN_LLM = (
    "LLMPort",
    "QwenLLMClient",
    "MockLLMClient",
    "PromptBuilder",
    "EvidenceBuilder",
)

_FORBIDDEN_INFRA = (
    "websocket",
    "redis",
    "scheduler",
    "push_notification",
)


def _src(module_name: str) -> str:
    import importlib

    mod = importlib.import_module(module_name)
    return open(mod.__file__, encoding="utf-8").read()


def test_mqtt_topic_no_llm_imports() -> None:
    src = _src("app.mqtt.topic")
    for forbidden in _FORBIDDEN_LLM:
        assert forbidden not in src


def test_mqtt_sensor_ingest_no_llm_imports() -> None:
    src = _src("app.services.mqtt_sensor_ingest")
    for forbidden in _FORBIDDEN_LLM:
        assert forbidden not in src


def test_environment_detail_service_no_llm_imports() -> None:
    src = _src("app.services.environment_detail_service")
    for forbidden in _FORBIDDEN_LLM:
        assert forbidden not in src


def test_environment_detail_service_no_db_write_in_fallback() -> None:
    src = _src("app.services.environment_detail_service")
    # fallback path must not call session.add / session.commit
    assert "session.add" not in src
    assert "session.commit" not in src


def test_mqtt_worker_subscribes_to_both_topics() -> None:
    src = _src("app.mqtt.worker")
    assert "sensor/readings/+" in src
    assert "sunshine/+/readings" in src


def test_sensor_ingest_no_snapshot_call() -> None:
    src = _src("app.services.sensor_ingest")
    assert "SnapshotService" not in src
    assert "aggregate(" not in src
