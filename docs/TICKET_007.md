# TICKET-007 — Environment Snapshot Aggregation

## 0. 목표

Sunshine 백엔드에 환경 snapshot aggregation 기능을 구현한다.

이 티켓은 기존 `sensor_readings` raw 데이터를 읽어서 `latest`, `24h`, `7d` 환경 요약 snapshot을 생성하고 `environment_snapshots`에 저장하는 기능만 담당한다.

Rule Engine, care decision, recommendation, Home Card API, Environment Detail API, Growth History API, LLM/RAG는 구현하지 않는다.

---

## 1. 핵심 요구사항

### Ticket ID

```text
TICKET-007
````

### Name

```text
Environment Snapshot Aggregation
```

### Goal

```text
Aggregate raw sensor_readings into latest, 24h, and 7d environment snapshots.
```

### Core output

```text
SnapshotService
SnapshotRepository
EnvironmentSnapshot DTO/schema
one-shot snapshot generation command
latest / 24h / 7d window computation
avg/min/max metrics
persisted environment_snapshots rows
```

---

## 2. 수정/생성 허용 파일

### 수정 가능한 기존 파일

```text
app/main.py
app/models/environment_snapshot.py
app/models/sensor_reading.py
app/repositories/__init__.py
app/core/config.py
pyproject.toml
.github/workflows/ci.yml
```

### 생성 가능한 새 파일

```text
app/schemas/environment_snapshots.py
app/repositories/snapshot_repository.py
app/services/snapshot_service.py
app/snapshots/__init__.py
app/snapshots/run.py
tests/test_snapshot_service.py
tests/test_snapshot_repository.py
tests/test_snapshot_command.py
tests/test_ticket7_boundary.py
```

### 조건부 허용

내부 수동 실행 API가 필요할 때만 생성 가능:

```text
app/api/environment_snapshots.py
```

단, 허용 endpoint는 아래 하나만 가능하다.

```http
POST /internal/snapshots/run
```

금지 endpoint:

```text
GET /plants/{plant_id}/environment
GET /home
GET /plants/{plant_id}/card
GET /plants/{plant_id}/history
POST /rules/run
POST /chat
```

### 조건부 migration 허용

필요한 index/unique constraint가 없을 때만 Alembic migration 추가 가능.

```text
alembic/versions/<ticket7_snapshot_indexes>.py
```

허용 범위:

```text
index(sensor_readings.plant_id, sensor_readings.measured_at)
unique(environment_snapshots.plant_id, window, window_start, window_end)
index(environment_snapshots.plant_id, window, window_end)
```

금지:

```text
Rule Engine table 추가
recommendation/evidence schema 추가
care/chat/RAG 관련 schema 변경
```

---

## 3. Snapshot Service 계약

`app/services/snapshot_service.py`를 생성한다.

필수 class shape:

```python
from datetime import datetime
from uuid import UUID

class SnapshotService:
    async def generate_for_plant(
        self,
        plant_id: UUID,
        *,
        now: datetime,
    ) -> list[EnvironmentSnapshotDTO]:
        ...

    async def generate_for_all_plants(
        self,
        *,
        now: datetime,
    ) -> list[EnvironmentSnapshotDTO]:
        ...
```

필수 동작:

```text
1. raw sensor_readings를 읽는다.
2. latest snapshot을 계산한다.
3. 24h snapshot을 계산한다.
4. 7d snapshot을 계산한다.
5. environment_snapshots에 저장한다.
6. deterministic window_start/window_end를 사용한다.
7. 같은 plant_id + window + window_start + window_end는 upsert한다.
8. 생성 결과를 DTO로 반환한다.
```

금지:

```text
Rule Engine 호출
CharacterStateEngine 호출
care recommendation 생성
primary_action 선택
severity/reason_code 생성
LLM 호출
RAG retrieval
push notification
SSE/websocket
```

---

## 4. Snapshot Repository 계약

`app/repositories/snapshot_repository.py`를 생성한다.

필수 operations:

```text
list_readings_for_window(plant_id, start, end)
get_latest_reading(plant_id, at_or_before)
upsert_snapshot(snapshot)
get_snapshot(plant_id, window, window_start, window_end)
list_snapshots_for_plant(plant_id)
```

DB invariant:

```text
environment_snapshots는 아래 deterministic key 기준으로 append/upsert한다.

plant_id
window
window_start
window_end
```

금지 DB write:

```text
plant_characters
care_logs
chat_requests
llm_runs
recommendation_evidence
retrieved_chunks
```

---

## 5. Snapshot Window 계약

지원 window는 정확히 아래 3개만 허용한다.

```text
latest
24h
7d
```

### latest

```text
selected reading:
  plant_id 기준 measured_at <= now 인 가장 최신 sensor_reading

window_start:
  selected_reading.measured_at

window_end:
  selected_reading.measured_at

avg/min/max:
  각 metric 모두 selected reading 값과 동일
```

reading이 없으면:

```text
latest snapshot row를 만들지 않는다.
status = missing_data 로 반환한다.
```

### 24h

```text
window_start = now - 24 hours
window_end = now

포함 조건:
  window_start <= measured_at <= window_end

계산:
  각 metric의 avg/min/max
```

### 7d

```text
window_start = now - 7 days
window_end = now

포함 조건:
  window_start <= measured_at <= window_end

계산:
  각 metric의 avg/min/max
```

### 시간 처리

```text
now는 timezone-aware datetime이어야 한다.
measured_at도 timezone-aware datetime이어야 한다.
naive datetime은 reject한다.
계산은 UTC normalize 또는 timestamptz semantics를 보존한다.
```

---

## 6. Metric 계약

각 window마다 아래 metric을 계산한다.

```text
temperature:
  temperature_avg_c
  temperature_min_c
  temperature_max_c

humidity:
  humidity_avg_pct
  humidity_min_pct
  humidity_max_pct

light:
  light_avg_lux
  light_min_lux
  light_max_lux

soil moisture:
  soil_moisture_avg_pct
  soil_moisture_min_pct
  soil_moisture_max_pct
```

계산 규칙:

```text
avg는 arithmetic mean
min/max는 포함된 reading만 사용
interpolation 금지
smoothing 금지
outlier filtering 금지
species-specific thresholding 금지
care decision 금지
```

---

## 7. Missing Data 계약

특정 window에 reading이 없으면 fake snapshot row를 만들지 않는다.

반환 예시:

```json
{
  "plant_id": "00000000-0000-0000-0000-000000000703",
  "window": "24h",
  "status": "missing_data",
  "created": false
}
```

금지:

```text
zero fill 금지
이전 값 carry-forward 금지
species profile에서 추론 금지
LLM 호출 금지
fake environment_snapshots row 생성 금지
```

---

## 8. EnvironmentSnapshot DTO 계약

`app/schemas/environment_snapshots.py`에 DTO/schema를 생성한다.

예시 shape:

```json
{
  "plant_id": "00000000-0000-0000-0000-000000000703",
  "window": "latest | 24h | 7d",
  "window_start": "2026-05-04T09:00:00+09:00",
  "window_end": "2026-05-04T12:00:00+09:00",
  "reading_count": 3,
  "temperature_avg_c": 24.5,
  "temperature_min_c": 23.0,
  "temperature_max_c": 26.0,
  "humidity_avg_pct": 54.0,
  "humidity_min_pct": 50.0,
  "humidity_max_pct": 58.0,
  "light_avg_lux": 810.0,
  "light_min_lux": 700.0,
  "light_max_lux": 900.0,
  "soil_moisture_avg_pct": 37.0,
  "soil_moisture_min_pct": 32.0,
  "soil_moisture_max_pct": 42.0
}
```

주의:

```text
reading_count는 있으면 좋다.
DB schema에 없으면 service return DTO에만 포함해도 된다.
recommendation/evidence/decision field는 추가하지 않는다.
```

---

## 9. One-shot Command 계약

`app/snapshots/run.py`를 생성한다.

필수 command:

```bash
python -m app.snapshots.run
```

지원 인자:

```text
--plant-id <uuid>
--now <ISO-8601 datetime>
--all
```

필수 동작:

```text
snapshot generation을 한 번만 실행한다.
결과를 stdout에 JSON으로 출력한다.
성공 시 exit 0.
validation/runtime failure 시 non-zero exit.
```

예시:

```bash
python -m app.snapshots.run \
  --plant-id 00000000-0000-0000-0000-000000000703 \
  --now 2026-05-04T12:00:00+09:00
```

출력 예시:

```json
{
  "snapshots": [
    {
      "window": "latest",
      "status": "created"
    },
    {
      "window": "24h",
      "status": "created"
    },
    {
      "window": "7d",
      "status": "created"
    }
  ]
}
```

금지:

```text
infinite loop
scheduler
cron-like behavior
MQTT subscription
Redis queue consumption
worker daemon
```

---

## 10. Runtime 계약

Ticket 7은 새로운 long-lived worker를 만들지 않는다.

허용 runtime topology:

```text
host
  -> backend container
      -> uvicorn app.main:app
      -> GET /healthz
      -> GET /readyz
      -> existing APIs

  -> postgres container
      -> PostgreSQL

  -> one-shot snapshot command
      docker compose run --rm backend python -m app.snapshots.run
```

Ticket 6이 이미 존재하는 branch에서는 아래 container가 남아 있어도 된다.

```text
mqtt
mqtt-ingest
```

하지만 Ticket 7에서 새로 추가하면 안 되는 container:

```text
snapshot-worker
redis
nginx
vllm
model-server
generic-worker
```

Backend process invariant:

```text
exactly one foreground uvicorn process
no snapshot scheduler inside backend
no background aggregation loop inside backend
```

Snapshot command invariant:

```text
one-shot process
python -m app.snapshots.run
generation 이후 종료
```

---

## 11. Health / Readiness 계약

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
check environment_snapshots
check snapshot freshness
check scheduler
check MQTT
check Rule Engine
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
check snapshot freshness
require latest snapshot
require 24h/7d rows
check Rule Engine
check LLM/RAG
```

Snapshot correctness는 `/readyz`가 아니라 Ticket 7 functional tests/gates에서 검증한다.

---

## 12. Determinism / Idempotency 계약

같은 reading set과 같은 `now`가 주어지면 output은 항상 같아야 한다.

금지:

```text
--now가 제공됐는데 내부에서 current time 사용
random sampling
smoothing
outlier removal
threshold-based care interpretation
```

같은 deterministic window key에 대해 command를 두 번 실행해도 row가 중복 생성되면 안 된다.

window key:

```text
plant_id
window
window_start
window_end
```

필수 동작:

```text
first run:
  latest / 24h / 7d snapshot 생성

second run with same now:
  upsert 또는 no-op
  row count stable
```

---

## 13. Dependency 계약

허용 dependency:

```text
existing FastAPI / Pydantic / SQLAlchemy / Alembic / Postgres stack
pytest / httpx / ruff
```

금지 dependency:

```text
redis
celery
rq
apscheduler
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

## 14. 테스트 요구사항

아래 테스트를 추가한다.

```text
tests/test_snapshot_service.py
tests/test_snapshot_repository.py
tests/test_snapshot_command.py
tests/test_ticket7_boundary.py
```

### Service tests

필수 케이스:

```text
latest snapshot equals newest reading
24h snapshot computes correct avg/min/max
7d snapshot computes correct avg/min/max
window_start/window_end are deterministic
naive now is rejected
missing data returns missing_data
missing data does not create fake row
same now + same readings produces identical output
```

### Repository tests

필수 케이스:

```text
list_readings_for_window returns only included readings
get_latest_reading returns newest measured_at <= now
upsert_snapshot inserts first row
upsert_snapshot updates or no-ops same deterministic key
same key does not create duplicate rows
list_snapshots_for_plant returns persisted snapshots
```

### Command tests

필수 케이스:

```text
python -m app.snapshots.run --plant-id <uuid> --now <aware-datetime> exits 0
stdout is valid JSON
output includes snapshots
output includes latest / 24h / 7d
invalid --now exits non-zero
missing plant or no readings handled explicitly
```

### Boundary tests

필수 확인:

```text
no app/rules/
no app/llm/
no app/rag/
no app/retrieval/

no Redis dependency
no scheduler dependency
no LLM/RAG/vLLM/OpenAI/Anthropic dependency

no Rule Engine call
no CharacterStateEngine call
no Home Card API
no Environment Detail API
no Growth History API
no chat endpoint
no push notification

no writes to:
  plant_characters
  care_logs
  chat_requests
  llm_runs
  recommendation_evidence
  retrieved_chunks
```

---

## 15. Functional Expectations

### Seed readings

예시 기준:

```text
now = 2026-05-04T12:00:00+09:00

readings:
  2026-05-04T09:00:00+09:00
    temperature=20, humidity=40, light=100, soil=30

  2026-05-04T10:00:00+09:00
    temperature=22, humidity=50, light=200, soil=40

  2026-05-04T11:00:00+09:00
    temperature=24, humidity=60, light=300, soil=50

  2026-05-01T12:00:00+09:00
    temperature=18, humidity=30, light=50, soil=20
```

### latest expected

```text
latest reading = 2026-05-04T11:00:00+09:00

temperature_avg/min/max = 24 / 24 / 24
humidity_avg/min/max = 60 / 60 / 60
light_avg/min/max = 300 / 300 / 300
soil_moisture_avg/min/max = 50 / 50 / 50
```

### 24h expected

Uses readings at 09:00, 10:00, 11:00.

```text
temperature_avg/min/max = 22 / 20 / 24
humidity_avg/min/max = 50 / 40 / 60
light_avg/min/max = 200 / 100 / 300
soil_moisture_avg/min/max = 40 / 30 / 50
```

### 7d expected

Uses readings at 05-01 12:00, 05-04 09:00, 10:00, 11:00.

```text
temperature_avg/min/max = 21 / 18 / 24
humidity_avg/min/max = 45 / 30 / 60
light_avg/min/max = 162.5 / 50 / 300
soil_moisture_avg/min/max = 35 / 20 / 50
```

### Idempotent upsert expected

```text
First run:
  creates latest / 24h / 7d rows

Second run with same now:
  no duplicate rows
  row count remains stable
```

### Missing data expected

```text
plant has no sensor_readings

Result:
  status = missing_data for each window

DB:
  no fake environment_snapshots row
  no zero-filled row
```

---

## 16. 구현 금지 항목

이 티켓에서 아래 기능은 구현하지 않는다.

```text
Rule Engine
watering/light/humidity/temperature care decision
primary_action
severity
reason_code
recommendation
character-state auto-update
Home Plant Card API
Plant Environment Detail API
Growth History API
Care Log API
LLM
RAG
PromptBuilder
EvidenceBuilder
push notification
realtime stream
SSE
websocket
Redis queue
scheduler
snapshot-worker daemon
```

---

## 17. 최종 완료 조건

Ticket 7은 아래가 모두 만족되면 완료다.

```text
SnapshotService exists.
SnapshotRepository exists.
EnvironmentSnapshot DTO/schema exists.
python -m app.snapshots.run works as one-shot command.
latest snapshot equals newest reading.
24h snapshot computes correct avg/min/max.
7d snapshot computes correct avg/min/max.
same now + same readings is deterministic.
same window key is upserted without duplicate rows.
missing data is explicit and creates no fake row.
environment_snapshots rows are persisted.
no Rule Engine, recommendation, character update, Home Card, Environment Detail, Growth History, LLM, RAG, push notification, or realtime feature leaks into this ticket.
/healthz liveness remains unchanged.
/readyz remains DB-only.
```