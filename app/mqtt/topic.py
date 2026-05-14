"""MQTT topic parser — TICKET-006 / TICKET-053.

Parses topics of the form:
  ``sensor/readings/{device_id}``   (original shape)
  ``sunshine/{device_id}/readings`` (backward-compatible addition)

Raises ``ValueError`` for any topic that doesn't match either pattern.
"""

_PREFIX_LEGACY = "sensor/readings/"
_PREFIX_LEGACY_LEN = len(_PREFIX_LEGACY)
_PREFIX_SUNSHINE = "sunshine/"
_SUFFIX_SUNSHINE = "/readings"


def parse_device_id(topic: str) -> str:
    """Extract device_id from a recognised MQTT sensor topic.

    Accepted shapes:
      - ``sensor/readings/{device_id}``
      - ``sunshine/{device_id}/readings``

    Raises:
        ValueError: if the topic doesn't match either pattern or the
                    extracted device_id is empty.
    """
    if not isinstance(topic, str):
        raise ValueError(f"topic must be a string, got {type(topic)!r}")

    # Shape 1: sensor/readings/{device_id}  (exactly 2 slashes)
    if topic.startswith(_PREFIX_LEGACY):
        rest = topic[_PREFIX_LEGACY_LEN:]
        if "/" in rest:
            raise ValueError(
                f"invalid topic {topic!r}: extra segments after device_id"
            )
        if not rest:
            raise ValueError(f"invalid topic {topic!r}: device_id segment must not be empty")
        return rest

    # Shape 2: sunshine/{device_id}/readings  (exactly 2 slashes)
    if topic.startswith(_PREFIX_SUNSHINE) and topic.endswith(_SUFFIX_SUNSHINE):
        inner = topic[len(_PREFIX_SUNSHINE) : -len(_SUFFIX_SUNSHINE)]
        if "/" in inner:
            raise ValueError(
                f"invalid topic {topic!r}: extra segments in device_id position"
            )
        if not inner:
            raise ValueError(f"invalid topic {topic!r}: device_id segment must not be empty")
        return inner

    raise ValueError(
        f"invalid topic {topic!r}: must match 'sensor/readings/<device_id>' "
        "or 'sunshine/<device_id>/readings'"
    )
