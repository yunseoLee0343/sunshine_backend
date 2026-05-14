"""MQTT ingest worker — TICKET-006.

Runs as a standalone process (``python -m app.mqtt.worker``).
Subscribes to ``sensor/readings/+`` and delegates each message to
``MqttSensorIngestService``, which re-uses the existing Ticket-005
``SensorIngestService`` for all DB logic.

Environment variables (all optional, sensible defaults for local docker):
  MQTT_HOST         broker host (default: mqtt)
  MQTT_PORT         broker port (default: 1883)
  MQTT_KEEPALIVE    keepalive seconds (default: 60)
  MQTT_CLIENT_ID    client id (default: sunshine-mqtt-ingest)
"""

import asyncio
import logging
import os
import signal
import sys

import paho.mqtt.client as mqtt

from app.db.session import AsyncSessionLocal
from app.mqtt.schemas import IngestOutcome
from app.services.mqtt_sensor_ingest import MqttSensorIngestService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("mqtt.worker")

SUBSCRIBE_TOPICS = ["sensor/readings/+", "sunshine/+/readings"]

_MQTT_HOST = os.getenv("MQTT_HOST", "mqtt")
_MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
_MQTT_KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "60"))
_MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "sunshine-mqtt-ingest")


def _on_connect(client: mqtt.Client, userdata, flags, rc, properties=None) -> None:
    if rc == 0:
        logger.info("connected to MQTT broker %s:%s", _MQTT_HOST, _MQTT_PORT)
        for topic in SUBSCRIBE_TOPICS:
            client.subscribe(topic)
            logger.info("subscribed to %s", topic)
    else:
        logger.error("MQTT connect failed, rc=%s", rc)


def _on_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage) -> None:
    loop: asyncio.AbstractEventLoop = userdata["loop"]
    asyncio.run_coroutine_threadsafe(_handle(msg.topic, msg.payload), loop)


async def _handle(topic: str, payload: bytes) -> None:
    async with AsyncSessionLocal() as session:
        svc = MqttSensorIngestService(session)
        result = await svc.process(topic, payload)

    if result.outcome == IngestOutcome.inserted:
        logger.info("inserted reading_id=%s topic=%s", result.reading_id, topic)
    elif result.outcome == IngestOutcome.duplicate_ignored:
        logger.debug("duplicate reading_id=%s topic=%s", result.reading_id, topic)
    else:
        logger.warning(
            "outcome=%s reading_id=%s topic=%s detail=%s",
            result.outcome,
            result.reading_id,
            topic,
            result.detail,
        )


def _on_disconnect(client: mqtt.Client, userdata, disconnect_flags, rc, properties=None) -> None:
    logger.warning("disconnected from broker rc=%s", rc)


def main() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    client = mqtt.Client(
        client_id=_MQTT_CLIENT_ID,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        userdata={"loop": loop},
    )
    client.on_connect = _on_connect
    client.on_message = _on_message
    client.on_disconnect = _on_disconnect

    def _shutdown(sig, frame):
        logger.info("shutting down (signal %s)", sig)
        client.disconnect()
        client.loop_stop()
        loop.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    logger.info("connecting to %s:%s", _MQTT_HOST, _MQTT_PORT)
    client.connect(_MQTT_HOST, _MQTT_PORT, _MQTT_KEEPALIVE)
    client.loop_start()

    try:
        loop.run_forever()
    finally:
        loop.close()


if __name__ == "__main__":
    main()
