"""TICKET-053 — MQTT topic parsing tests."""

from __future__ import annotations

import pytest

from app.mqtt.topic import parse_device_id


def test_legacy_topic_returns_device_id() -> None:
    assert parse_device_id("sensor/readings/device-001") == "device-001"


def test_sunshine_topic_returns_device_id() -> None:
    assert parse_device_id("sunshine/device-001/readings") == "device-001"


def test_legacy_topic_empty_device_id_rejected() -> None:
    with pytest.raises(ValueError, match="device_id segment must not be empty"):
        parse_device_id("sensor/readings/")


def test_sunshine_topic_empty_device_id_rejected() -> None:
    with pytest.raises(ValueError, match="device_id segment must not be empty"):
        parse_device_id("sunshine//readings")


def test_extra_segment_in_legacy_rejected() -> None:
    with pytest.raises(ValueError, match="extra segments"):
        parse_device_id("sensor/readings/device-001/extra")


def test_extra_segment_in_sunshine_rejected() -> None:
    with pytest.raises(ValueError):
        parse_device_id("sunshine/device-001/readings/extra")


def test_completely_unknown_topic_rejected() -> None:
    with pytest.raises(ValueError):
        parse_device_id("unknown/topic")


def test_non_string_topic_rejected() -> None:
    with pytest.raises(ValueError, match="topic must be a string"):
        parse_device_id(123)  # type: ignore[arg-type]


def test_legacy_device_id_with_hyphens() -> None:
    assert parse_device_id("sensor/readings/rpi-edge-node-01") == "rpi-edge-node-01"


def test_sunshine_device_id_with_hyphens() -> None:
    assert parse_device_id("sunshine/rpi-edge-node-01/readings") == "rpi-edge-node-01"
