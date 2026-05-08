# TICKET-006 — MQTT Sensor Ingestion

## 0. 목표

Sunshine 백엔드에 MQTT 기반 센서 데이터 인제스천 경로를 추가한다.

이 티켓은 raw sensor reading을 MQTT로 받아서 저장하는 기능을 추가한다. 단, 저장/검증/멱등성 처리는 새로 만들지 말고 기존 Ticket 5의 `SensorIngestService` 경로를 반드시 재사용한다.

MQTT 전용 DB insert 경로를 새로 만들지 않는다.

---

## 1. 핵심 요구사항

### 목표

MQTT로 들어온 센서 데이터를 기존 Ticket 5와 동일한 멱등성 ingestion path를 통해 저장한다.

### 필수 산출물

- `docker-compose.yml`에 `mqtt` service 추가
- `docker-compose.yml`에 `mqtt-ingest` service 추가
- MQTT 설정 추가
- MQTT client / worker process 추가
- MQTT topic 구독: `sensor/readings/+`
- 실제 허용 topic: `sensor/readings/{device_id}`
- `topic_device_id == payload.device_id` 검증
- 기존 `SensorReadingCreate` schema로 payload 검증
- 기존 Ticket 5 경로를 통한 `reading_id` 멱등성 유지
- `sensor_readings` 저장은 기존 `SensorIngestService`를 통해서만 수행

### Topic 계약

이 티켓에서는 아래 topic 계약을 사용한다.

```text
구독 topic:
sensor/readings/+

실제 허용 topic:
sensor/readings/{device_id}
````

아래 topic은 사용하지 않는다.

```text
sunshine/{device_id}/readings
sunshine/+/readings
```

---

## 2. 수정/생성 허용 파일

### 수정 가능한 기존 파일

```text
docker-compose.yml
.env.example
pyproject.toml
app/core/config.py
app/main.py
app/services/sensor_ingest.py
app/repositories/sensor_repository.py
app/schemas/sensor_readings.py
.github/workflows/ci.yml
```

### 생성 가능한 새 파일

```text
app/mqtt/__init__.py
app/mqtt/client.py
app/mqtt/schemas.py
app/mqtt/worker.py
app/mqtt/topic.py
app/mqtt/settings.py
app/services/mqtt_sensor_ingest.py
tests/test_mqtt_topic_contract.py
tests/test_mqtt_payload_contract.py
tests/test_mqtt_sensor_ingest_service.py
tests/test_mqtt_idempotency.py
tests/test_ticket6_boundary.py
```

위 목록에 없는 파일은 수정하거나 생성하지 않는다.

---

## 3. Docker Compose 계약

`docker-compose.yml`에 아래 MQTT service를 추가한다.

```yaml
mqtt:
  image: eclipse-mosquitto:2
  ports:
    - "1883:1883"

mqtt-ingest:
  build: .
  command: ["python", "-m", "app.mqtt.worker"]
  environment:
    APP_NAME: sunshine-backend
    APP_ENV: local
    DATABASE_URL: postgresql+asyncpg://sunshine:change-me-local-only@postgres:5432/sunshine
    MQTT_HOST: mqtt
    MQTT_PORT: "1883"
    MQTT_TOPIC: sensor/readings/+
  depends_on:
    - postgres
    - mqtt
```

규칙:

* service 이름은 반드시 `mqtt`여야 한다.
* service 이름은 반드시 `mqtt-ingest`여야 한다.
* `mqtt-ingest`를 `worker`, `mqtt-worker`, `sensor-worker` 등으로 바꾸지 않는다.
* MQTT ingestion을 `backend` container 안에서 실행하지 않는다.
* 하나의 container command에서 FastAPI와 MQTT worker를 동시에 실행하지 않는다.
* Redis, nginx, vLLM, model-server, llm, cache, generic worker service를 추가하지 않는다.

---

## 4. MQTT 설정 계약

아래 설정을 지원한다.

```env
MQTT_HOST=mqtt
MQTT_PORT=1883
MQTT_TOPIC=sensor/readings/+
MQTT_QOS=1
MQTT_CLIENT_ID=sunshine-mqtt-ingest
MQTT_USERNAME=
MQTT_PASSWORD=
```

규칙:

* local MVP에서는 빈 username/password를 허용한다.
* production secret을 commit하지 않는다.
* 아래 env는 추가하지 않는다.

  * `REDIS_URL`
  * `LLM_BASE_URL`
  * `VLLM_BASE_URL`
  * `OPENAI_API_KEY`
  * `ANTHROPIC_API_KEY`
  * `RAG_INDEX_URL`
  * `PGVECTOR_*`

---

## 5. MQTT Topic 계약

Topic parser를 아래 파일에 구현한다.

```text
app/mqtt/topic.py
```

필수 함수:

```python
def parse_sensor_reading_topic(topic: str) -> str:
    ...
```

허용 topic:

```text
sensor/readings/{device_id}
```

예시:

```text
sensor/readings/rpi-edge-node-01
sensor/readings/device-rpi-001
```

Parser 규칙:

* topic은 정확히 3개 segment여야 한다.
* `segment[0] == "sensor"`
* `segment[1] == "readings"`
* `segment[2]`는 `topic_device_id`
* `topic_device_id`는 비어 있으면 안 된다.

기대 동작:

```python
parse_sensor_reading_topic("sensor/readings/rpi-edge-node-01")
# returns "rpi-edge-node-01"
```

잘못된 topic은 `ValueError("invalid_topic")` 또는 동등한 `ValueError`를 발생시킨다.

Invalid topic 예시:

```text
sensor/readings
sensor/readings/
sensor/readings/device-1/extra
sensor/device-1/readings
sunshine/device-1/readings
sunshine/readings/device-1
other/readings/device-1
sensor/status/device-1
```

---

## 6. MQTT Payload 계약

Payload는 UTF-8 JSON이다.

예시:

```json
{
  "reading_id": "rdg-rpi-edge-node-01-20260507T153000",
  "device_id": "rpi-edge-node-01",
  "plant_id": "00000000-0000-0000-0000-000000000301",
  "measured_at": "2026-05-07T15:30:00+09:00",
  "temperature_c": 24.5,
  "humidity_pct": 55.2,
  "light_lux": 850.0,
  "soil_moisture_pct": 42.0
}
```

규칙:

* 기존 Ticket 5의 `SensorReadingCreate` schema를 재사용한다.
* `topic_device_id`는 `payload.device_id`와 같아야 한다.
* invalid JSON은 reject한다.
* invalid payload는 reject한다.
* 존재하지 않는 `plant_id`는 `SensorIngestService` 경로에서 reject한다.
* 중복 `reading_id`는 `SensorIngestService` 경로에서 duplicate로 처리한다.
* numeric field는 string, `null`, `NaN`, `Infinity`, `-Infinity`이면 안 된다.
* `measured_at`은 timezone을 포함해야 한다.

Field 제약:

```text
reading_id:
  - required string
  - pattern: ^[A-Za-z0-9._:\-]+$
  - 권장 형식: rdg-{device_id}-{YYYYMMDDTHHMMSS}
  - 새 측정값이면 새 reading_id
  - 같은 측정값 재전송이면 같은 reading_id

device_id:
  - required string
  - topic device_id와 같아야 함

plant_id:
  - required
  - backend/project owner가 제공한 값을 사용
  - MQTT path에서는 그대로 pass-through

measured_at:
  - ISO 8601
  - timezone-aware
  - KST 예시: 2026-05-07T15:30:00+09:00

temperature_c:
  - number
  - -40 <= value <= 80

humidity_pct:
  - number
  - 0 <= value <= 100

light_lux:
  - number
  - 0 <= value <= 200000

soil_moisture_pct:
  - number
  - 0 <= value <= 100
```

측정 실패 정책:

* 센서값으로 `null`을 받지 않는다.
* 측정 실패 시 sensor device 쪽에서 해당 publish를 skip하거나 retry한다.

---

## 7. MQTT Ingestion Result 계약

Result schema를 아래 파일에 생성한다.

```text
app/mqtt/schemas.py
```

필수 result shape:

```json
{
  "status": "inserted | duplicate_ignored | rejected",
  "reading_id": "rdg-rpi-edge-node-01-20260507T153000 | null",
  "topic": "sensor/readings/rpi-edge-node-01",
  "topic_device_id": "rpi-edge-node-01",
  "payload_device_id": "rpi-edge-node-01 | null",
  "ignored": false,
  "error_code": null
}
```

필수 rejection code:

```text
invalid_topic
invalid_json
invalid_payload
device_id_mismatch
unknown_plant
storage_error
```

---

## 8. Service 계약

아래 파일을 생성한다.

```text
app/services/mqtt_sensor_ingest.py
```

필수 class shape:

```python
class MqttSensorIngestService:
    async def ingest_mqtt_message(
        self,
        *,
        topic: str,
        payload_bytes: bytes,
    ) -> MqttIngestResult:
        ...
```

필수 처리 순서:

1. `parse_sensor_reading_topic`으로 topic을 parse한다.
2. payload bytes를 UTF-8 JSON으로 decode한다.
3. 기존 Ticket 5 `SensorReadingCreate`로 payload를 validate한다.
4. `topic_device_id == payload.device_id`를 확인한다.
5. 기존 `SensorIngestService.ingest_reading(payload)`를 호출한다.
6. inserted / duplicate_ignored / rejected result를 반환한다.

금지:

* `SensorIngestService`를 우회한 direct DB insert
* Ticket 5와 달라질 수 있는 별도 idempotency 로직
* snapshot aggregation
* Rule Engine 호출
* character-state update
* care recommendation
* Redis enqueue
* LLM/RAG 호출

중요:

* MQTT path와 HTTP path는 `SensorIngestService`에서 합류해야 한다.
* MQTT 전용 repository insert path를 만들지 않는다.
* `reading_id` idempotency는 기존 `SensorIngestService` / repository path가 소유해야 한다.

---

## 9. MQTT Client / Worker 계약

아래 파일을 생성한다.

```text
app/mqtt/client.py
app/mqtt/worker.py
```

Worker command:

```bash
python -m app.mqtt.worker
```

Worker 책임:

* `MQTT_HOST`, `MQTT_PORT`로 MQTT broker에 연결한다.
* `MQTT_TOPIC`을 subscribe한다.
* 메시지를 받으면 `MqttSensorIngestService.ingest_mqtt_message`를 호출한다.
* inserted / duplicate_ignored / rejected 결과를 stdout/stderr에 log한다.
* invalid message가 들어와도 process가 crash되면 안 된다.
* SIGTERM/SIGINT에서 clean shutdown한다.

금지:

* FastAPI server 실행
* migration 실행
* snapshot worker 실행
* Rule Engine 실행
* Redis consumer 실행
* LLM/vLLM 실행
* local file persistence 작성

---

## 10. Dependency 계약

허용되는 새 dependency:

```text
paho-mqtt
```

허용되는 기존 dependency:

```text
FastAPI / Pydantic / SQLAlchemy / Alembic / Postgres stack
pytest / httpx / ruff
```

금지 dependency:

```text
redis
celery
rq
openai
anthropic
vllm
pgvector
sentence-transformers
torch
tensorflow
onnxruntime
openvino
```

---

## 11. 테스트 요구사항

아래 테스트를 추가 또는 수정한다.

```text
tests/test_mqtt_topic_contract.py
tests/test_mqtt_payload_contract.py
tests/test_mqtt_sensor_ingest_service.py
tests/test_mqtt_idempotency.py
tests/test_ticket6_boundary.py
```

필수 테스트 범위:

### Topic tests

* `sensor/readings/rpi-edge-node-01`은 `rpi-edge-node-01`을 반환해야 한다.
* 아래 invalid topic은 reject되어야 한다.

```text
sensor/readings
sensor/readings/
sensor/readings/device-1/extra
sensor/device-1/readings
sunshine/device-1/readings
sunshine/readings/device-1
other/readings/device-1
sensor/status/device-1
```

### Service tests

* valid MQTT message는 `SensorIngestService`를 호출해야 한다.
* invalid topic은 `SensorIngestService`를 호출하지 않아야 한다.
* invalid JSON은 `invalid_json`을 반환해야 한다.
* invalid payload는 `invalid_payload`를 반환해야 한다.
* topic/payload device mismatch는 `device_id_mismatch`를 반환해야 한다.
* `SensorIngestService`의 duplicate 결과는 `duplicate_ignored`로 매핑되어야 한다.
* storage failure는 `storage_error`로 매핑되어야 한다.
* invalid message가 service path를 crash시키면 안 된다.

### Boundary tests

* Redis dependency 없음
* LLM/RAG/vLLM/OpenAI/Anthropic dependency 없음
* snapshot/rule/chat/companion endpoint 없음
* `MqttSensorIngestService` 안에 direct DB insert 없음
* backend container command에서 FastAPI와 MQTT worker를 동시에 실행하지 않음

---

## 12. Functional Expectations

구현 후 아래 흐름이 동작해야 한다.

```text
Sensor publish:
  topic = sensor/readings/rpi-edge-node-01
  payload.device_id = rpi-edge-node-01

mqtt broker:
  receives publish on port 1883

mqtt-ingest:
  subscribed to sensor/readings/+
  receives message
  parses topic_device_id
  validates JSON payload
  verifies topic_device_id == payload.device_id
  calls SensorIngestService.ingest_reading(payload)

SensorIngestService:
  validates plant/readings through existing path
  enforces reading_id idempotency
  inserts or ignores duplicate
```

Duplicate behavior:

```text
First publish with reading_id X:
  result = inserted

Second publish with same reading_id X:
  result = duplicate_ignored
  database row remains one
```

Mismatch behavior:

```text
topic = sensor/readings/rpi-edge-node-99
payload.device_id = rpi-edge-node-01

result:
  rejected
  error_code = device_id_mismatch
  no insert
```

---

## 13. 구현 금지 항목

이 티켓에서 아래 기능은 구현하지 않는다.

```textv
environment snapshots
Rule Engine
character mood/state update
care recommendation
push notification
realtime stream
Redis queue
LLM/RAG
companion recommendation
admin page
production MQTT auth/TLS
device command topic
device ack topic
firmware update
```