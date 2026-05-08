# TICKET-010 — Plant Environment Detail API

## 0. 목표

Sunshine 백엔드에 식물 환경 상세 API를 구현한다.

이 티켓은 기존 Ticket 7이 생성한 `environment_snapshots`와 Ticket 4가 저장한 최신 `plant_character`를 읽어서, 식물 상세 화면에 필요한 환경 데이터를 반환한다.

Ticket 10은 read-only detail API다.

이 티켓은 snapshot을 생성하지 않는다.  
이 티켓은 raw sensor reading을 집계하지 않는다.  
이 티켓은 Rule Engine을 실행하지 않는다.  
이 티켓은 LLM/RAG/Chat/Report/Graph 기능을 구현하지 않는다.

---

## 1. Ticket Identity

### Ticket ID

```text
TICKET-010
````

### Name

```text
Plant Environment Detail API
```

### Goal

```text
Expose detailed environment data for the plant detail screen using existing environment snapshots and character state.
```

### Core output

```text
GET /plants/{plant_id}/environment
EnvironmentDetailService
EnvironmentDetail DTO/schema
latest environment values
24h summary
7d summary
character explanation aligned with latest character state
```

### Strict non-goal

```text
no graph rendering
no chart/image generation
no timelapse
no long report
no growth history timeline
no care-log API
no snapshot generation
no Rule Engine execution
no chat answer generation
no LLM
no RAG
no EvidenceBuilder
no PromptBuilder
no companion recommendation
```

---

## 2. 주변 티켓과의 연결

Ticket 10은 prior ticket output을 읽는 상세 API다.

```text
Ticket 2:
  plant ownership
  plant identity
  nickname
  room_name

Ticket 4:
  latest plant character state
  mood
  expression
  status_message
  reason_code

Ticket 7:
  latest / 24h / 7d environment_snapshots
  temperature/humidity/light/soil moisture avg/min/max

Ticket 8:
  Rule Engine care decision
  단, Ticket 10에서는 실행하지 않음
```

Ticket 10의 역할:

```text
plant identity
  + latest environment snapshot
  + 24h environment snapshot
  + 7d environment snapshot
  + latest character state
  -> environment detail response
```

금지:

```text
snapshot generation
raw sensor aggregation
Rule Engine execution
care recommendation calculation
LLM/RAG explanation
graph rendering
growth history timeline
```

---

## 3. 수정/생성 허용 파일

### 수정 가능한 기존 파일

```text
app/main.py
app/api/__init__.py
app/repositories/plant_repository.py
app/repositories/character_repository.py
app/repositories/snapshot_repository.py
app/schemas/home.py
pyproject.toml
.github/workflows/ci.yml
```

### 생성 가능한 새 파일

```text
app/api/environment.py
app/schemas/environment_detail.py
app/services/environment_detail_service.py
app/repositories/environment_detail_repository.py
tests/test_environment_detail_schema.py
tests/test_environment_detail_service.py
tests/test_environment_detail_api.py
tests/test_ticket10_boundary.py
```

### 조건부 허용

```text
app/schemas/environment_snapshots.py
```

조건:

```text
기존 snapshot schema에서 response DTO 분리가 필요한 경우에만 허용한다.
aggregation logic은 변경하지 않는다.
```

### Migration policy

기본값:

```text
No migration required.
```

정말 필요한 경우에만 허용:

```text
index for environment_snapshots(plant_id, window, window_end)
index for plant_characters(plant_id, created_at)
```

금지 migration:

```text
chat tables
RAG tables
prompt tables
report tables
graph/timelapse tables
recommendation ranking tables
```

---

## 4. 금지 파일/디렉터리

아래 경로는 생성하거나 수정하지 않는다.

```text
app/llm/
app/rag/
app/retrieval/
app/services/evidence_builder.py
app/services/prompt_builder.py
app/services/chat_orchestrator.py
app/services/growth_history_service.py
app/services/care_log_service.py
app/services/companion_recommendation.py
app/services/report_service.py
app/services/timelapse_service.py
app/repositories/chunk_repository.py
app/repositories/audit_repository.py
app/api/chat.py
app/api/history.py
app/api/care_logs.py
app/api/companion.py
app/api/reports.py
deploy/
```

이미 이전 티켓에서 존재할 수 있는 경로:

```text
app/rules/
app/snapshots/
app/mqtt/
app/vision/
```

규칙:

```text
Ticket 10에서는 snapshot generation, MQTT ingestion, Vision, Rule Engine logic을 수정하지 않는다.
import/type compatibility 수준의 수정만 허용한다.
```

---

## 5. API 계약 — GET /plants/{plant_id}/environment

### Endpoint

```http
GET /plants/{plant_id}/environment?user_id=<uuid>
```

### Response

```json
{
  "plant_id": "uuid",
  "nickname": "초록이",
  "room_name": "거실",
  "latest": {
    "measured_at": "2026-05-04T12:00:00+09:00",
    "temperature_c": 22.0,
    "humidity_pct": 50.0,
    "light_lux": 1000.0,
    "soil_moisture_pct": 25.0,
    "source_window": "latest"
  },
  "summary_24h": {
    "window_start": "2026-05-03T12:00:00+09:00",
    "window_end": "2026-05-04T12:00:00+09:00",
    "temperature_avg_c": 22.0,
    "temperature_min_c": 20.0,
    "temperature_max_c": 24.0,
    "humidity_avg_pct": 50.0,
    "humidity_min_pct": 40.0,
    "humidity_max_pct": 60.0,
    "light_avg_lux": 200.0,
    "light_min_lux": 100.0,
    "light_max_lux": 300.0,
    "soil_moisture_avg_pct": 40.0,
    "soil_moisture_min_pct": 30.0,
    "soil_moisture_max_pct": 50.0
  },
  "summary_7d": {
    "window_start": "2026-04-27T12:00:00+09:00",
    "window_end": "2026-05-04T12:00:00+09:00",
    "temperature_avg_c": 21.0,
    "temperature_min_c": 18.0,
    "temperature_max_c": 24.0,
    "humidity_avg_pct": 45.0,
    "humidity_min_pct": 30.0,
    "humidity_max_pct": 60.0,
    "light_avg_lux": 162.5,
    "light_min_lux": 50.0,
    "light_max_lux": 300.0,
    "soil_moisture_avg_pct": 35.0,
    "soil_moisture_min_pct": 20.0,
    "soil_moisture_max_pct": 50.0
  },
  "character_explanation": {
    "mood": "thirsty",
    "expression": "droop",
    "reason_code": "low_soil_moisture",
    "message": "현재 캐릭터 상태는 최근 환경 요약의 토양 수분 부족과 연결됩니다.",
    "source": "character_state"
  }
}
```

### Status behavior

```text
200:
  plant exists and belongs to user

404 or 403:
  plant does not exist or does not belong to user

200 with null summaries:
  plant exists but one or more snapshots are missing
```

---

## 6. Response Field 계약

### Required top-level fields

```text
plant_id
nickname
room_name
latest
summary_24h
summary_7d
character_explanation
```

### Required `latest` fields

```text
measured_at
temperature_c
humidity_pct
light_lux
soil_moisture_pct
source_window
```

### Required `summary_24h` / `summary_7d` fields

```text
window_start
window_end
temperature_avg_c
temperature_min_c
temperature_max_c
humidity_avg_pct
humidity_min_pct
humidity_max_pct
light_avg_lux
light_min_lux
light_max_lux
soil_moisture_avg_pct
soil_moisture_min_pct
soil_moisture_max_pct
```

### Required `character_explanation` fields

```text
mood
expression
reason_code
message
source
```

### Forbidden fields

```text
graph_data
chart_config
rendered_graph_url
image_url
timelapse_url
history
timeline
care_logs
chat_answer
final_answer
prompt
retrieved_chunks
evidence_bundle
llm_response
long_report
companion_recommendations
```

---

## 7. EnvironmentDetailService 계약

아래 파일을 생성한다.

```text
app/services/environment_detail_service.py
```

필수 class shape:

```python
from uuid import UUID

class EnvironmentDetailService:
    async def get_environment_detail(
        self,
        *,
        plant_id: UUID,
        user_id: UUID,
    ) -> EnvironmentDetailResponse:
        ...
```

필수 동작:

```text
1. Verify plant belongs to user_id.
2. Load plant identity.
3. Load latest environment snapshot where window = latest.
4. Load 24h environment snapshot where window = 24h.
5. Load 7d environment snapshot where window = 7d.
6. Load latest character state.
7. Build character explanation from deterministic template.
8. Return read-only environment detail response.
```

금지:

```text
snapshot generation
raw sensor aggregation
Rule Engine execution
threshold comparison
care recommendation calculation
LLM call
RAG retrieval
prompt generation
report generation
graph rendering
```

---

## 8. Repository 계약

아래 파일을 생성한다.

```text
app/repositories/environment_detail_repository.py
```

허용 read:

```text
get plant by plant_id + user_id
get latest snapshot where window = latest
get latest snapshot where window = 24h
get latest snapshot where window = 7d
get latest character state
```

금지 write:

```text
sensor_readings
environment_snapshots
plant_characters
care_logs
chat_requests
llm_runs
recommendation_evidence
retrieved_chunks
```

중요:

```text
Ticket 10 is read-only.
```

---

## 9. Snapshot Selection 계약

각 window별 snapshot 선택 규칙:

```text
latest:
  choose newest environment_snapshots row where window = latest

24h:
  choose newest environment_snapshots row where window = 24h

7d:
  choose newest environment_snapshots row where window = 7d

ordering:
  window_end desc, created_at desc
```

금지:

```text
aggregate raw sensor_readings in this endpoint
call app.snapshots.run
choose arbitrary old snapshot when newer exists
synthesize 24h/7d from latest
fill missing windows with zero
carry-forward old windows unless explicitly selected as latest by window_end
```

---

## 10. Character Explanation 계약

Character explanation은 deterministic template text다.
LLM output이 아니다.

Mapping:

```text
reason_code = low_soil_moisture
=> message = "현재 캐릭터 상태는 최근 환경 요약의 토양 수분 부족과 연결됩니다."

reason_code = low_light
=> message = "현재 캐릭터 상태는 최근 환경 요약의 빛 부족과 연결됩니다."

reason_code = unstable_humidity
=> message = "현재 캐릭터 상태는 최근 환경 요약의 습도 변화와 연결됩니다."

reason_code = good
=> message = "현재 캐릭터 상태는 안정적인 환경 요약과 연결됩니다."

reason_code = after_watering
=> message = "현재 캐릭터 상태는 최근 물주기 이후 상태와 연결됩니다."

missing character state
=> message = "캐릭터 상태 설명에 필요한 상태 정보가 아직 없습니다."
```

규칙:

```text
character_explanation.reason_code must equal latest plant_character.reason_code.
character_explanation.source must be "character_state" or "fallback".
No LLM generation.
No free-form explanation.
No Rule Engine rerun.
No snapshot inference beyond reading existing summary values.
No character state mutation.
```

---

## 11. Missing Data 계약

### Missing latest snapshot

```json
{
  "latest": null
}
```

### Missing 24h snapshot

```json
{
  "summary_24h": null
}
```

### Missing 7d snapshot

```json
{
  "summary_7d": null
}
```

### Missing character state

```json
{
  "character_explanation": {
    "mood": "neutral",
    "expression": "normal",
    "reason_code": "missing_character_state",
    "message": "캐릭터 상태 설명에 필요한 상태 정보가 아직 없습니다.",
    "source": "fallback"
  }
}
```

규칙:

```text
Do not create fake snapshot values.
Do not call snapshot command automatically.
Do not fill zeros.
Do not carry forward old windows unless explicitly selected as latest by window_end.
Do not call LLM to explain missing data.
Do not create character rows automatically.
```

---

## 12. Runtime 계약

허용 runtime topology:

```text
host
  -> backend container
      -> uvicorn app.main:app
      -> GET /healthz
      -> GET /readyz
      -> GET /plants/{plant_id}/environment
      -> EnvironmentDetailService
      -> Postgres reads

  -> postgres container
      -> PostgreSQL

  -> optional mqtt/mqtt-ingest from Ticket 6
```

Allowed long-lived containers:

```text
backend
postgres
mqtt
mqtt-ingest
```

Forbidden new long-lived containers:

```text
environment-worker
report-worker
redis
nginx
vllm
model-server
generic-worker
```

Backend process invariant:

```text
exactly one foreground uvicorn process
no environment detail worker
no report generator process
no chart renderer process
no LLM/vLLM process
```

Startup allowed:

```text
import app.main
create FastAPI app
register /plants/{plant_id}/environment route
import EnvironmentDetailService definitions
```

Startup forbidden:

```text
precompute environment detail for all plants
scan all snapshots
generate graphs
run snapshot aggregation
run Rule Engine
call LLM/RAG
run migrations
start workers
```

---

## 13. Network / Env 계약

Required network:

```text
backend listens on 0.0.0.0:8000
postgres reachable by DATABASE_URL
```

Forbidden network behavior:

```text
external HTTP API call
LLM/vLLM call
RAG/vector DB call
Redis call
graph rendering service call
object storage/timelapse call
```

Allowed backend env:

```env
APP_NAME=sunshine-backend
APP_ENV=local
DATABASE_URL=postgresql+asyncpg://sunshine:change-me-local-only@postgres:5432/sunshine
```

Allowed if Ticket 6 exists:

```env
MQTT_HOST=mqtt
MQTT_PORT=1883
MQTT_TOPIC=sensor/readings/+
```

Forbidden env:

```text
REDIS_URL
LLM_BASE_URL
VLLM_BASE_URL
OPENAI_API_KEY
ANTHROPIC_API_KEY
RAG_INDEX_URL
PGVECTOR_URL
GRAPH_RENDERER_URL
TIMELAPSE_BUCKET
LONG_REPORT_ENABLED
```

---

## 14. `/healthz` 계약

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
query environment detail
query snapshots
check latest/24h/7d rows
check character state
check Postgres
run Rule Engine
change response shape
```

---

## 15. `/readyz` 계약

Ticket 10에서 `/readyz`는 DB readiness만 확인한다.
Data-completeness readiness가 아니다.

Expected response:

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
require latest snapshot
require 24h summary
require 7d summary
require character state
run EnvironmentDetailService
run Rule Engine
check LLM/RAG
add "environment_detail": "ok"
add "snapshots": "ok"
```

Environment detail correctness는 `/readyz`가 아니라 functional tests/gates에서 검증한다.

---

## 16. Read-only 계약

Ticket 10 API calls는 read-only여야 한다.

Allowed DB operations:

```text
read plants
read latest environment_snapshots by window
read latest plant_character
```

Forbidden DB operations:

```text
insert/update sensor_readings
insert/update environment_snapshots
insert/update plant_characters
insert care_logs
insert chat_requests
insert llm_runs
insert recommendation_evidence
insert retrieved_chunks
```

---

## 17. Dependency 계약

허용 dependency:

```text
existing FastAPI / Pydantic / SQLAlchemy / Alembic / Postgres stack
pytest / httpx / ruff
```

금지 dependency:

```text
openai
anthropic
vllm
pgvector
sentence-transformers
torch
tensorflow
onnxruntime
openvino
redis
celery
rq
apscheduler
matplotlib
plotly
altair
```

주의:

```text
Ticket 10에서는 graph rendering dependency를 추가하지 않는다.
```

---

## 18. 테스트 요구사항

아래 테스트를 추가한다.

```text
tests/test_environment_detail_schema.py
tests/test_environment_detail_service.py
tests/test_environment_detail_api.py
tests/test_ticket10_boundary.py
```

### Schema tests

필수 확인:

```text
EnvironmentDetail DTO includes plant_id, nickname, room_name, latest, summary_24h, summary_7d, character_explanation.
latest allows only measured_at, temperature_c, humidity_pct, light_lux, soil_moisture_pct, source_window.
summary_24h and summary_7d include avg/min/max metrics.
character_explanation allows only mood, expression, reason_code, message, source.
forbidden fields do not appear.
```

### Service tests

필수 케이스:

```text
get_environment_detail verifies plant ownership.
loads latest snapshot where window = latest.
loads 24h snapshot where window = 24h.
loads 7d snapshot where window = 7d.
loads latest character state.
uses deterministic character explanation template.
does not generate snapshots.
does not aggregate sensor_readings.
does not run Rule Engine.
missing latest snapshot returns latest = null.
missing 24h snapshot returns summary_24h = null.
missing 7d snapshot returns summary_7d = null.
missing character returns fallback explanation.
```

### API tests

필수 케이스:

```text
GET /plants/{plant_id}/environment?user_id=<uuid> returns 200 for owner.
GET /plants/{plant_id}/environment blocks cross-user access with 403 or 404.
response includes latest values.
response includes 24h summary.
response includes 7d summary.
response includes character_explanation.
missing snapshots still return 200 with null summary fields.
```

### Boundary tests

필수 확인:

```text
no app/llm/
no app/rag/
no app/retrieval/

no app/services/evidence_builder.py
no app/services/prompt_builder.py
no app/services/chat_orchestrator.py
no app/services/growth_history_service.py
no app/services/care_log_service.py
no app/services/report_service.py
no app/services/timelapse_service.py

no Chat API
no Companion API
no Growth History API
no Care Log API
no Report API

no LLM/RAG/Vision/Redis/scheduler/graph dependency

no forbidden fields in response:
  graph_data
  chart_config
  rendered_graph_url
  image_url
  timelapse_url
  history
  timeline
  care_logs
  chat_answer
  final_answer
  prompt
  retrieved_chunks
  evidence_bundle
  llm_response
  long_report
  companion_recommendations

no writes to:
  sensor_readings
  environment_snapshots
  plant_characters
  care_logs
  chat_requests
  llm_runs
  recommendation_evidence
  retrieved_chunks
```

---

## 19. Functional Expectations

### Environment detail success

Input:

```http
GET /plants/00000000-0000-0000-0000-000000001003/environment?user_id=00000000-0000-0000-0000-000000001001
```

Expected:

```json
{
  "plant_id": "00000000-0000-0000-0000-000000001003",
  "nickname": "초록이",
  "room_name": "거실",
  "latest": {
    "temperature_c": 22.0,
    "humidity_pct": 50.0,
    "light_lux": 1000.0,
    "soil_moisture_pct": 25.0,
    "source_window": "latest"
  },
  "summary_24h": {
    "temperature_avg_c": 22.0,
    "temperature_min_c": 20.0,
    "temperature_max_c": 24.0,
    "humidity_avg_pct": 50.0,
    "humidity_min_pct": 40.0,
    "humidity_max_pct": 60.0,
    "light_avg_lux": 200.0,
    "soil_moisture_avg_pct": 40.0
  },
  "summary_7d": {
    "temperature_avg_c": 21.0,
    "temperature_min_c": 18.0,
    "temperature_max_c": 24.0,
    "humidity_avg_pct": 45.0,
    "light_avg_lux": 162.5,
    "soil_moisture_avg_pct": 35.0
  },
  "character_explanation": {
    "mood": "thirsty",
    "expression": "droop",
    "reason_code": "low_soil_moisture",
    "message": "현재 캐릭터 상태는 최근 환경 요약의 토양 수분 부족과 연결됩니다.",
    "source": "character_state"
  }
}
```

### Cross-user block

Input:

```http
GET /plants/{plant_id}/environment?user_id=<other_user_id>
```

Expected:

```text
403 or 404
no plant data leaked
```

### Missing snapshots

If plant has no environment snapshots:

```json
{
  "latest": null,
  "summary_24h": null,
  "summary_7d": null
}
```

Expected:

```text
HTTP 200
no fake values
no zero-filled values
no snapshot generation
```

### Missing character

If plant has no character state:

```json
{
  "character_explanation": {
    "mood": "neutral",
    "expression": "normal",
    "reason_code": "missing_character_state",
    "message": "캐릭터 상태 설명에 필요한 상태 정보가 아직 없습니다.",
    "source": "fallback"
  }
}
```

Expected:

```text
no plant_characters row is created automatically
```

---

## 20. 구현 금지 항목

이 티켓에서 아래 기능은 구현하지 않는다.

```text
POST /plants/{plant_id}/care-logs
GET /plants/{plant_id}/care-logs
watering/note action logging
character update after watering

GET /plants/{plant_id}/history
timeline items
growth history
photo timeline
timelapse

chat intent classifier
POST /chat
POST /plants/{plant_id}/chat
LLMPort
PromptBuilder
EvidenceBuilder
RAG retrieval
retrieved_chunks
final answer sections [결론][근거][행동][주의]

chat care answer
pest/disease reference answer
diagnosis language

companion recommendation
compatibility filter
recommendation ranking

graph rendering
chart config
chart/image generation
long report
report generation
push notification
realtime stream
SSE
websocket
Redis queue
scheduler
environment-worker
report-worker
```

---

## 21. 최종 완료 조건

Ticket 10은 아래가 모두 만족되면 완료다.

```text
GET /plants/{plant_id}/environment exists.
EnvironmentDetailService exists.
EnvironmentDetailRepository exists.
EnvironmentDetail DTO/schema exists.

GET /plants/{plant_id}/environment returns plant identity.
GET /plants/{plant_id}/environment verifies user ownership.
Cross-user environment access is blocked.

Response includes latest environment values from existing latest snapshot.
Response includes 24h summary from existing 24h snapshot.
Response includes 7d summary from existing 7d snapshot.
Response includes character_explanation from latest character reason_code.

Missing latest snapshot returns latest = null.
Missing 24h snapshot returns summary_24h = null.
Missing 7d snapshot returns summary_7d = null.
Missing character returns deterministic fallback explanation.

API is read-only.
No fake environment values are synthesized.
No snapshot generation runs automatically.
No raw sensor aggregation is performed.
No Rule Engine execution occurs.
No character state is mutated.

No graph rendering, timelapse, long report, care log, growth history, chat, LLM, RAG, EvidenceBuilder, PromptBuilder, companion recommendation, Redis, scheduler, worker, vLLM, or Nginx leaks into this ticket.

/healthz liveness remains unchanged.
/readyz remains DB-only.
```

