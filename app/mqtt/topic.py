"""MQTT topic parser — TICKET-006.

Parses topics of the form ``sensor/readings/{device_id}``.
Raises ``ValueError`` for any topic that doesn't match this pattern.
"""

_PREFIX = "sensor/readings/"
_PREFIX_LEN = len(_PREFIX)
_EXPECTED_SLASHES = 2  # "sensor", "readings", "{device_id}"


def parse_device_id(topic: str) -> str:
    """Extract device_id from a ``sensor/readings/{device_id}`` topic.

    Raises:
        ValueError: if the topic doesn't match the expected pattern or the
                    extracted device_id is empty.
    """
    if not isinstance(topic, str):
        raise ValueError(f"topic must be a string, got {type(topic)!r}")

    if topic.count("/") != _EXPECTED_SLASHES:
        raise ValueError(
            f"invalid topic {topic!r}: expected exactly {_EXPECTED_SLASHES} "
            "slashes (pattern: sensor/readings/<device_id>)"
        )

    if not topic.startswith(_PREFIX):
        raise ValueError(f"invalid topic {topic!r}: must start with {_PREFIX!r}")

    device_id = topic[_PREFIX_LEN:]
    if not device_id:
        raise ValueError(f"invalid topic {topic!r}: device_id segment must not be empty")

    return device_id
