"""TICKET-006 — MQTT topic parser tests."""

import pytest

from app.mqtt.topic import parse_device_id


@pytest.mark.parametrize("topic,expected", [
    ("sensor/readings/dev-001", "dev-001"),
    ("sensor/readings/sensor_42", "sensor_42"),
    ("sensor/readings/abc:123.xyz", "abc:123.xyz"),
])
def test_valid_topics(topic: str, expected: str) -> None:
    assert parse_device_id(topic) == expected


@pytest.mark.parametrize("bad", [
    "sensor/readings/",          # empty device_id
    "sensor/readings",           # missing device_id segment
    "readings/dev-001",          # wrong prefix
    "sensor/readings/a/b",       # too many segments
    "",                          # empty
    "sensor/readings/dev/extra", # extra slash
])
def test_invalid_topics_raise(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_device_id(bad)
