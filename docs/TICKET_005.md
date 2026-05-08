# TICKET-005 — Sensor Reading Ingestion API

## 0. 목표

Sunshine 백엔드에 HTTP 기반 센서 데이터 인제스천 API를 구현한다.

이 티켓은 센서에서 들어온 raw sensor reading을 검증하고, `reading_id` 기준 멱등성을 보장하며, `sensor_readings`에 안전하게 저장하는 기능만 담당한다.

MQTT, worker, snapshot, Rule Engine, character update, recommendation, LLM/RAG는 구현하지 않는다.

---

## 1. 핵심 요구사항

### Ticket ID

```text
TICKET-005
````

### Name

```text
Sensor Reading Ingestion API
```

### Goal

```text
Accept validated sensor readings over HTTP and store raw readings safely with reading_id idempotency.
```

### Core output

```text
POST /sensor-readings
SensorReadingCreate schema
SensorIngestService
SensorRepository
reading_id idempotency
plant ownership/link validation
raw sensor_readings persistence
```

---

## 2. 수정/생성 허용 파일

### 수정 가능한 기존 파일

```text
app/main.py
app/api/__init__.py
app/models/sensor_reading.py
app/models/plant.py
app/repositories/__init__.py
app/repositories/plant_repository.py
app/schemas/__init__.py
pyproject.toml
.github/workflows/ci.yml
```

### 생성 가능한 새 파일

```text
app/api/sensor_readings.py
app/schemas/sensor_readings.py
app/repositories/sensor_repository.py
app/services/sensor_ingest.py
tests/test_sensor_reading_schema.py
tests/test_sensor_ingest_service.py
tests/test_sensor_readings_api.py
tests/test_sensor_reading_idempotency.py
tests/test_ticket5_boundary.py
```

### 조건부 허용

Ticket 1 schema에 필요한 constraint/index가 없을 때만 Alembic migration 추가 가능.

```text
alembic/versions/<ticket5_sensor_reading_constraints>.py
```

허용되는 migration 범위:

```text
unique(reading_id)
index(plant_id, measured_at)
index(device_id, measured_at)
```

금지:

```text
snapshot/rule/care/chat/RAG 관련 schema 변경
```

---

## 3. API 계약

### Endpoint

```http
POST /sensor-readings
Content-Type: application/json
```

### Request Body

```json
{
  "reading_id": "sensor-rdg-0001",
  "device_id": "device-rpi-001",
  "plant_id": "00000000-0000-0000-0000-000000000301",
  "measured_at": "2026-05-04T10:00:00+09:00",
  "temperature_c": 24.5,
  "humidity_pct": 53.2,
  "light_lux": 820.0,
  "soil_moisture_pct": 38.5
}
```

### Response — inserted

HTTP status:

```text
201 Created
```

Body:

```json
{
  "status": "inserted",
  "reading_id": "sensor-rdg-0001",
  "plant_id": "00000000-0000-0000-0000-000000000301",
  "ignored": false
}
```

### Response — duplicate

HTTP status:

```text
200 OK
```

Body:

```json
{
  "status": "duplicate_ignored",
  "reading_id": "sensor-rdg-0001",
  "plant_id": "00000000-0000-0000-0000-000000000301",
  "ignored": true
}
```

### Error status

```text
400 or 422:
  invalid payload shape or invalid sensor value

404:
  plant_id does not exist
```

---

## 4. Payload / Schema 계약

`app/schemas/sensor_readings.py`에 `SensorReadingCreate`를 구현한다.

### Required fields

```text
reading_id: str
device_id: str
plant_id: UUID
measured_at: aware datetime
temperature_c: float
humidity_pct: float
light_lux: float
soil_moisture_pct: float
```

### String validation

```text
reading_id:
  - required
  - non-empty
  - max length: 128
  - allowed characters: alphanumeric, dash, underscore, colon, dot
  - must not be only whitespace

device_id:
  - required
  - non-empty
  - max length: 128
  - allowed characters: alphanumeric, dash, underscore, colon, dot
  - must not be only whitespace
```

권장 정규식:

```text
^[A-Za-z0-9._:-]+$
```

### Datetime validation

```text
measured_at:
  - required
  - must parse as datetime
  - must be timezone-aware
  - KST example: 2026-05-04T10:00:00+09:00
```

timezone 없는 값은 reject한다.

```text
2026-05-04T10:00:00
```

### Numeric validation

```text
temperature_c:
  - finite number
  - -40 <= value <= 80

humidity_pct:
  - finite number
  - 0 <= value <= 100

light_lux:
  - finite number
  - 0 <= value <= 200000

soil_moisture_pct:
  - finite number
  - 0 <= value <= 100
```

금지 numeric 값:

```text
NaN
Infinity
-Infinity
null
stringified numbers if schema rejects coercion
```

---

## 5. Service 계약

`app/services/sensor_ingest.py`를 생성한다.

필수 class shape:

```python
class SensorIngestService:
    async def ingest_reading(self, payload: SensorReadingCreate) -> SensorIngestResult:
        ...
```

필수 동작 순서:

```text
1. Validate payload through schema.
2. Verify plant_id exists.
3. Check reading_id idempotency.
4. If reading_id already exists:
   - do not insert
   - return duplicate_ignored / ignored=true
5. If new:
   - insert sensor_readings row
   - return inserted / ignored=false
```

중요:

```text
- duplicate reading_id must never create a second row.
- duplicate may ignore payload differences.
- duplicate response must be explicit.
- duplicate must not mutate the original row.
```

금지:

```text
publish MQTT message
start MQTT client
enqueue worker job
compute snapshot
run Rule Engine
update character state
write recommendation evidence
call LLM
call RAG
send notification
```

---

## 6. Repository 계약

`app/repositories/sensor_repository.py`를 생성한다.

필수 operations:

```text
get_by_reading_id(reading_id)
insert_reading(payload)
count_by_reading_id(reading_id)
list_by_plant_id(plant_id) only if needed for tests
```

DB invariant:

```text
sensor_readings.reading_id is unique.
```

동시성 안전성:

```text
- Service-level pre-check is allowed but not sufficient alone.
- DB uniqueness must be the final idempotency authority.
- If concurrent duplicate insert hits unique violation, convert it to duplicate_ignored.
```

---

## 7. Persistence 계약

valid insert 시 `sensor_readings` row에 아래 값이 채워져야 한다.

```text
sensor_readings.id
sensor_readings.reading_id
sensor_readings.device_id
sensor_readings.plant_id
sensor_readings.measured_at
sensor_readings.temperature_c
sensor_readings.humidity_pct
sensor_readings.light_lux
sensor_readings.soil_moisture_pct
sensor_readings.created_at
```

금지 write 대상:

```text
environment_snapshots
plant_characters
care_logs
chat_requests
llm_runs
recommendation_evidence
retrieved_chunks
```

---

## 8. API 등록 계약

`app/api/sensor_readings.py`를 생성하고, `app/main.py` 또는 router registry에 등록한다.

허용 endpoint:

```text
POST /sensor-readings
```

금지 endpoint:

```text
GET /sensor-readings/stream
POST /mqtt/sensor-readings
POST /snapshots
POST /rules/run
GET /plants/{plant_id}/environment
GET /home
POST /chat
```

---

## 9. Runtime 계약

Ticket 5 runtime topology는 아래만 허용한다.

```text
host
  -> backend container
      -> uvicorn app.main:app
      -> GET /healthz
      -> GET /readyz
      -> POST /sensor-readings
      -> SensorIngestService
      -> SensorRepository
      -> PostgreSQL sensor_readings

  -> postgres container
      -> PostgreSQL
```

허용 long-lived containers:

```text
backend
postgres
```

금지 long-lived containers:

```text
mqtt
redis
worker
nginx
vllm
model-server
```

Backend process invariant:

```text
- exactly one foreground uvicorn process
- no MQTT subscriber
- no worker
- no scheduler
- no Redis consumer
- no websocket/SSE loop
- no LLM runtime
- no model loader
```

---

## 10. Health / Readiness 계약

### `/healthz`

Ticket 0 liveness contract를 그대로 유지한다.

```http
GET /healthz
200
```

```json
{
  "status": "ok",
  "service": "sunshine-backend"
}
```

`/healthz`에서 금지:

```text
check Postgres
check sensor_readings table
count sensor rows
check MQTT
check worker
change response shape
```

### `/readyz`

Ticket 1 readiness는 DB-only로 유지한다.

```json
{
  "status": "ready",
  "service": "sunshine-backend",
  "checks": {
    "database": "ok"
  }
}
```

`/readyz`에서 금지:

```text
check MQTT
check worker
check sensor freshness
check last reading age
check snapshot availability
add "sensor_ingestion": "ok"
```

---

## 11. Dependency 계약

허용 dependency:

```text
existing FastAPI / Pydantic / SQLAlchemy / Alembic stack
pytest / httpx / ruff
```

금지 dependency:

```text
paho-mqtt
redis
celery
rq
websockets
sse-starlette
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

## 12. 테스트 요구사항

아래 테스트를 추가한다.

```text
tests/test_sensor_reading_schema.py
tests/test_sensor_ingest_service.py
tests/test_sensor_readings_api.py
tests/test_sensor_reading_idempotency.py
tests/test_ticket5_boundary.py
```

### Schema tests

필수 reject 케이스:

```text
missing reading_id
missing device_id
missing plant_id
missing measured_at
missing temperature_c
missing humidity_pct
missing light_lux
missing soil_moisture_pct

empty reading_id
whitespace-only reading_id
empty device_id
whitespace-only device_id

measured_at without timezone
temperature_c < -40 or > 80
humidity_pct < 0 or > 100
light_lux < 0 or > 200000
soil_moisture_pct < 0 or > 100

NaN
Infinity
-Infinity
null numeric field
stringified numeric field if schema rejects coercion
```

### Service tests

필수 케이스:

```text
valid payload inserts new row
unknown plant_id is rejected
duplicate reading_id returns duplicate_ignored
duplicate reading_id does not insert second row
duplicate reading_id does not mutate original row
invalid payload does not reach insert
```

### API tests

필수 케이스:

```text
POST /sensor-readings valid payload -> 201 inserted
POST /sensor-readings duplicate reading_id -> 200 duplicate_ignored
POST /sensor-readings invalid payload -> 400 or 422
POST /sensor-readings unknown plant_id -> 404
```

### Boundary tests

필수 확인:

```text
no app/mqtt/
no app/workers/
no app/rules/
no app/llm/
no app/rag/
no app/retrieval/

no MQTT dependency
no Redis dependency
no websocket/SSE dependency
no LLM/RAG/vLLM/OpenAI/Anthropic dependency

no MQTT endpoint
no snapshot endpoint
no rule endpoint
no chat endpoint
no stream endpoint

no writes to:
  environment_snapshots
  plant_characters
  care_logs
  chat_requests
  llm_runs
  recommendation_evidence
  retrieved_chunks
```

---

## 13. Functional Expectations

### Valid insert

```text
POST /sensor-readings
  reading_id = rdg-ticket5-001
  plant_id exists
  values are valid

Expected:
  HTTP 201
  status = inserted
  ignored = false
  one sensor_readings row inserted
```

### Duplicate idempotency

```text
First POST with reading_id X:
  result = inserted
  one DB row

Second POST with same reading_id X:
  result = duplicate_ignored
  still one DB row
  original row is not mutated
```

### Invalid payload

```text
humidity_pct = 153.2

Expected:
  HTTP 400 or 422
  no DB row
```

### Unknown plant

```text
plant_id does not exist

Expected:
  HTTP 404
  no DB row
```

### Timezone validation

```text
measured_at = 2026-05-04T10:00:00

Expected:
  HTTP 400 or 422
  no DB row
```

---

## 14. 구현 금지 항목

이 티켓에서 아래 기능은 구현하지 않는다.

```text
MQTT broker
MQTT subscriber
MQTT client
worker process
realtime stream
snapshot aggregation
Rule Engine
character-state auto-update
recommendations
push notification
LLM
RAG
admin page
device command topic
device ack topic
firmware update
```

---

## 15. 최종 완료 조건

Ticket 5는 아래가 모두 만족되면 완료다.

```text
POST /sensor-readings accepts valid payloads.
invalid payloads are rejected.
unknown plant_id is rejected.
reading_id idempotency is DB-enforced.
duplicate reading_id does not insert or mutate the original row.
raw sensor_readings row is persisted.
no MQTT, worker, realtime, snapshot, Rule Engine, character update, LLM, or RAG leaks into this ticket.
/healthz liveness remains unchanged.
/readyz remains DB-only.
```