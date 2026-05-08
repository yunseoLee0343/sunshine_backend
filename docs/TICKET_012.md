# TICKET-011 — Care Action Logging

## 0. 목표

Sunshine 백엔드에 사용자의 수동 관리 행동 기록 API를 구현한다.

이 티켓은 사용자가 식물에 대해 `watering` 또는 `note`를 기록하고, 기록된 care log를 다시 조회할 수 있게 한다.

`watering` action은 Ticket 4의 `CharacterStateEngine`을 사용해 `after_watering` 캐릭터 상태를 append-only로 저장한다.

`note` action은 care log만 저장하고 캐릭터 상태를 변경하지 않는다.

이 티켓은 Rule Engine을 실행하지 않는다.  
이 티켓은 Growth History timeline을 만들지 않는다.  
이 티켓은 reminder, notification, chat, LLM, RAG를 구현하지 않는다.

---

## 1. Ticket Identity

### Ticket ID

```text
TICKET-011
````

### Name

```text
Care Action Logging
```

### Goal

```text
Allow the user to record watering and notes, then expose those logs to the user and to Rule Engine input.
```

### Core output

```text
POST /plants/{plant_id}/care-logs
GET /plants/{plant_id}/care-logs
CareLogCreate schema
CareLogService
CareLogRepository
supported MVP actions:
  - watering
  - note
timestamp persistence
after_watering character-state append on watering
care logs become readable by Rule Engine
```

### Strict non-goal

```text
no pruning
no repotting
no fertilizing
no reminders
no push notification
no growth history timeline
no chat answer generation
no LLM
no RAG
no EvidenceBuilder
no PromptBuilder
no recommendation ranking
```

---

## 2. 주변 티켓과의 연결

Ticket 11은 첫 manual care-action write path다.

```text
Ticket 4:
  CharacterStateEngine
  after_watering -> happy / smile
  plant_characters append-only history

Ticket 8:
  Rule Engine
  recent care_logs를 input으로 읽음
  단, Ticket 11에서 Rule Engine을 실행하지 않음

Ticket 12:
  Growth History API
  care logs + character states + environment events를 timeline으로 조합
  단, Ticket 11에서 timeline을 만들지 않음
```

Ticket 11의 역할:

```text
user action
  -> validate action_type / acted_at / ownership
  -> insert care_logs row
  -> if watering: append after_watering character state
  -> return care_log response
```

금지:

```text
Rule Engine execution
snapshot generation
Home Card recomputation
Growth History materialization
reminder scheduling
push notification
LLM/RAG call
final answer generation
```

---

## 3. 수정/생성 허용 파일

### 수정 가능한 기존 파일

```text
app/main.py
app/api/__init__.py
app/models/care_log.py
app/repositories/__init__.py
app/repositories/plant_repository.py
app/repositories/character_repository.py
app/services/character_state_engine.py
app/schemas/home.py
pyproject.toml
.github/workflows/ci.yml
```

### 생성 가능한 새 파일

```text
app/api/care_logs.py
app/schemas/care_logs.py
app/repositories/care_log_repository.py
app/services/care_log_service.py
tests/test_care_log_schema.py
tests/test_care_log_service.py
tests/test_care_log_api.py
tests/test_care_log_character_update.py
tests/test_care_log_rule_engine_visibility.py
tests/test_ticket11_boundary.py
```

### 조건부 허용

```text
app/schemas/character_state.py
```

조건:

```text
기존 CharacterState DTO 재사용이 필요할 때만 허용한다.
새 character-state mapping을 추가하면 안 된다.
```

### Migration policy

기본값:

```text
No migration required if care_logs already exists from Ticket 1.
```

필요할 때만 허용:

```text
add/repair care_logs columns:
  id
  plant_id
  action_type
  note
  acted_at
  created_at

add index:
  care_logs(plant_id, acted_at desc)

optional check constraint:
  action_type in ('watering', 'note')
```

금지 migration:

```text
reminder tables
notification tables
growth history materialized table
chat/RAG/prompt tables
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
app/services/reminder_service.py
app/services/notification_service.py
app/services/companion_recommendation.py
app/repositories/chunk_repository.py
app/repositories/audit_repository.py
app/api/chat.py
app/api/history.py
app/api/reminders.py
app/api/notifications.py
app/api/companion.py
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
Ticket 11 must not modify MQTT, Vision, Snapshot generation, Environment Detail, Home Card, or Rule Engine logic except for import/type compatibility.
```

---

## 5. API 계약 — POST /plants/{plant_id}/care-logs

### Endpoint

```http
POST /plants/{plant_id}/care-logs
Content-Type: application/json
```

### Request — watering

```json
{
  "user_id": "uuid",
  "action_type": "watering",
  "acted_at": "2026-05-04T13:00:00+09:00",
  "note": "물을 줬어요."
}
```

### Request — note

```json
{
  "user_id": "uuid",
  "action_type": "note",
  "acted_at": "2026-05-04T13:10:00+09:00",
  "note": "새 잎이 올라오는 중."
}
```

### Response — watering

```json
{
  "care_log": {
    "care_log_id": "uuid",
    "plant_id": "uuid",
    "action_type": "watering",
    "acted_at": "2026-05-04T13:00:00+09:00",
    "note": "물을 줬어요."
  },
  "character": {
    "mood": "happy",
    "expression": "smile",
    "status_message": "물을 마시고 기분이 좋아졌어요.",
    "primary_action": "none",
    "reason_code": "after_watering"
  }
}
```

### Response — note

```json
{
  "care_log": {
    "care_log_id": "uuid",
    "plant_id": "uuid",
    "action_type": "note",
    "acted_at": "2026-05-04T13:10:00+09:00",
    "note": "새 잎이 올라오는 중."
  },
  "character": null
}
```

### Status behavior

```text
201:
  care log created

400 or 422:
  invalid action_type
  invalid timestamp
  note required for action_type=note if strict note semantics are used

404 or 403:
  plant does not exist or does not belong to user
```

---

## 6. API 계약 — GET /plants/{plant_id}/care-logs

### Endpoint

```http
GET /plants/{plant_id}/care-logs?user_id=<uuid>&limit=20
```

### Response

```json
{
  "care_logs": [
    {
      "care_log_id": "uuid",
      "plant_id": "uuid",
      "action_type": "watering",
      "acted_at": "2026-05-04T13:00:00+09:00",
      "note": "물을 줬어요."
    },
    {
      "care_log_id": "uuid",
      "plant_id": "uuid",
      "action_type": "note",
      "acted_at": "2026-05-04T13:10:00+09:00",
      "note": "새 잎이 올라오는 중."
    }
  ]
}
```

### 규칙

```text
Return only logs for the requested plant.
Verify plant belongs to user_id.
Sort by acted_at descending, then created_at descending.
Default limit = 20.
Max limit = 100.
Do not return timeline items.
Do not join environment snapshots.
Do not include Rule Engine result.
Do not include chat or LLM fields.
```

---

## 7. CareLog Schema 계약

`app/schemas/care_logs.py`에 `CareLogCreate`와 response DTO를 구현한다.

### Required fields

```text
plant_id: UUID from path
user_id: UUID from request/query
action_type: watering | note
acted_at: timezone-aware datetime
note: string | null
```

### Validation rules

```text
action_type:
  - must be exactly watering or note

acted_at:
  - required
  - must be timezone-aware

note:
  - max length 1000
  - may be null for watering
  - should be non-empty for note unless product explicitly permits empty note
```

### Forbidden action types

```text
pruning
repotting
fertilizing
mist
rotate
reminder
photo
diagnosis
```

---

## 8. CareLogService 계약

아래 파일을 생성한다.

```text
app/services/care_log_service.py
```

필수 class shape:

```python
from uuid import UUID

class CareLogService:
    async def create_care_log(
        self,
        *,
        plant_id: UUID,
        user_id: UUID,
        payload: CareLogCreate,
    ) -> CareLogCreateResult:
        ...

    async def list_care_logs(
        self,
        *,
        plant_id: UUID,
        user_id: UUID,
        limit: int = 20,
    ) -> list[CareLogDTO]:
        ...
```

### Create behavior

```text
1. Verify plant belongs to user_id.
2. Validate action_type and acted_at.
3. Insert care_logs row.
4. If action_type == watering:
   - call CharacterStateEngine with condition = after_watering
   - append plant_characters row
   - return character block
5. If action_type == note:
   - do not update character
   - return character = null
```

### Transaction behavior

```text
care_log insert and watering character update must be atomic.

If care_log insert fails:
  no character row is created.

If character row insert fails for watering:
  care_log insert is rolled back.

note action:
  inserts care_log only.
```

금지:

```text
Rule Engine execution
snapshot generation
Home Card recomputation
Growth History materialization
reminder scheduling
push notification
LLM/RAG call
final answer generation
```

---

## 9. CareLogRepository 계약

아래 파일을 생성한다.

```text
app/repositories/care_log_repository.py
```

허용 operation:

```text
insert_care_log
list_care_logs_for_plant
list_recent_care_logs_for_rule_engine
```

`list_recent_care_logs_for_rule_engine`는 여기에서 구현하거나 Ticket 8의 `RuleInputRepository`와 호환되게 둔다.

규칙:

```text
Persisted watering log must be visible to Rule Engine input.
Do not run Rule Engine in Ticket 11.
Do not persist Rule Engine output.
```

금지 write:

```text
sensor_readings
environment_snapshots
chat_requests
llm_runs
recommendation_evidence
retrieved_chunks
```

---

## 10. Character Update 계약

Watering action은 반드시 아래 condition을 사용한다.

```text
condition = after_watering
```

Expected character state:

```json
{
  "mood": "happy",
  "expression": "smile",
  "status_message": "물을 마시고 기분이 좋아졌어요.",
  "primary_action": "none",
  "reason_code": "after_watering"
}
```

규칙:

```text
Use Ticket 4 CharacterStateEngine mapping.
Append a new plant_characters row.
Do not mutate previous character state in place.
Do not update character for note action.
Do not use LLM-generated mood or message.
```

---

## 11. Rule Engine Visibility 계약

Ticket 8은 recent care logs를 Rule Engine input으로 사용한다.
Ticket 11은 watering logs를 query 가능하게 저장해야 한다.

필수:

```text
care_logs.action_type = watering
care_logs.acted_at is persisted as timezone-aware timestamp
list_recent_care_logs_for_rule_engine can return the saved watering event
```

금지:

```text
direct Rule Engine invocation on care-log creation
precomputed recommendation write
recommendation_evidence write
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
      -> POST /plants/{plant_id}/care-logs
      -> GET /plants/{plant_id}/care-logs
      -> CareLogService
      -> CharacterStateEngine for watering only
      -> Postgres writes/reads

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
care-log-worker
reminder-worker
notification-worker
redis
nginx
vllm
model-server
generic-worker
```

Backend process invariant:

```text
exactly one foreground uvicorn process
no reminder scheduler
no notification worker
no care-log worker
no LLM/vLLM process
```

Startup allowed:

```text
import app.main
create FastAPI app
register care-log routes
import CareLogService definitions
```

Startup forbidden:

```text
scan care logs
precompute growth history
run Rule Engine
schedule reminders
start notification workers
call LLM/RAG
run migrations
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
push notification service call
LLM/vLLM call
RAG/vector DB call
Redis call
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
REMINDER_ENABLED
PUSH_PROVIDER_KEY
NOTIFICATION_WORKER_ENABLED
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
query care_logs
check reminder scheduler
check notification worker
check Postgres
check Rule Engine
check LLM/RAG
change response shape
```

---

## 15. `/readyz` 계약

Ticket 11에서 `/readyz`는 DB readiness만 확인한다.

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
require at least one care log
check latest character state
run Rule Engine
check reminders
check notification worker
check LLM/RAG
add "care_logs": "ok"
add "reminders": "ok"
add "notifications": "ok"
```

Care-log correctness는 `/readyz`가 아니라 functional tests/gates에서 검증한다.

---

## 16. Ownership / Data Access 계약

모든 care-log write/read는 `plant_id`가 `user_id` 소유인지 확인해야 한다.

Cross-user behavior:

```text
POST must reject.
GET must reject.
```

Allowed DB operations:

```text
read plant by plant_id + user_id
insert care_logs
read care_logs for plant
insert plant_characters for watering only
read care_logs for Rule Engine input tests
```

Forbidden DB operations:

```text
insert/update sensor_readings
insert/update environment_snapshots
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
```

주의:

```text
Ticket 11에서는 scheduler/reminder dependency를 추가하지 않는다.
```

---

## 18. 테스트 요구사항

아래 테스트를 추가한다.

```text
tests/test_care_log_schema.py
tests/test_care_log_service.py
tests/test_care_log_api.py
tests/test_care_log_character_update.py
tests/test_care_log_rule_engine_visibility.py
tests/test_ticket11_boundary.py
```

### Schema tests

필수 확인:

```text
action_type allows watering.
action_type allows note.
action_type rejects pruning.
action_type rejects repotting.
action_type rejects fertilizing.
action_type rejects reminder.
acted_at must be timezone-aware.
note max length is enforced.
note action requires non-empty note if strict note semantics are used.
```

### Service tests

필수 케이스:

```text
valid watering inserts care_log.
valid watering appends after_watering character row.
watering response includes character block.
valid note inserts care_log.
note response has character = null.
note does not append character row.
unknown plant returns 404 or 403.
cross-user plant access is rejected.
invalid action_type is rejected.
naive acted_at is rejected.
watering care_log insert and character append are atomic.
```

### API tests

필수 케이스:

```text
POST /plants/{plant_id}/care-logs watering -> 201.
POST watering returns care_log + after_watering character.
POST /plants/{plant_id}/care-logs note -> 201.
POST note returns care_log + character=null.
GET /plants/{plant_id}/care-logs returns logs.
GET care logs sorted by acted_at desc, created_at desc.
GET care logs applies default limit 20.
GET care logs caps limit at 100.
cross-user POST is 403 or 404.
cross-user GET is 403 or 404.
```

### Rule Engine visibility tests

필수 확인:

```text
saved watering log can be loaded by list_recent_care_logs_for_rule_engine.
watering log has timezone-aware acted_at.
Ticket 11 does not run Rule Engine.
Ticket 11 does not persist Rule Engine output.
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
no app/services/reminder_service.py
no app/services/notification_service.py

no Chat API
no Growth History API
no Reminder API
no Notification API
no Companion API

no LLM/RAG/Vision/Redis/scheduler dependency

no forbidden action types:
  pruning
  repotting
  fertilizing
  reminder
  diagnosis
  photo

no writes to:
  sensor_readings
  environment_snapshots
  chat_requests
  llm_runs
  recommendation_evidence
  retrieved_chunks
```

---

## 19. Functional Expectations

### Watering create

Input:

```http
POST /plants/00000000-0000-0000-0000-000000001103/care-logs
```

```json
{
  "user_id": "00000000-0000-0000-0000-000000001101",
  "action_type": "watering",
  "acted_at": "2026-05-04T13:00:00+09:00",
  "note": "물을 줬어요."
}
```

Expected:

```json
{
  "care_log": {
    "plant_id": "00000000-0000-0000-0000-000000001103",
    "action_type": "watering",
    "acted_at": "2026-05-04T13:00:00+09:00",
    "note": "물을 줬어요."
  },
  "character": {
    "mood": "happy",
    "expression": "smile",
    "status_message": "물을 마시고 기분이 좋아졌어요.",
    "primary_action": "none",
    "reason_code": "after_watering"
  }
}
```

Expected DB effect:

```text
one care_logs row inserted
one plant_characters row appended with reason_code = after_watering
previous plant_characters rows are not mutated
```

### Note create

Input:

```json
{
  "user_id": "00000000-0000-0000-0000-000000001101",
  "action_type": "note",
  "acted_at": "2026-05-04T13:10:00+09:00",
  "note": "새 잎이 올라오는 중."
}
```

Expected:

```json
{
  "care_log": {
    "action_type": "note",
    "note": "새 잎이 올라오는 중."
  },
  "character": null
}
```

Expected DB effect:

```text
one care_logs row inserted
no plant_characters row inserted
```

### Care log list

Input:

```http
GET /plants/00000000-0000-0000-0000-000000001103/care-logs?user_id=00000000-0000-0000-0000-000000001101&limit=20
```

Expected:

```text
returns care_logs sorted by acted_at desc, created_at desc
does not include timeline/history/environment/chat fields
```

### Invalid action

Input:

```json
{
  "action_type": "fertilizing",
  "acted_at": "2026-05-04T13:20:00+09:00",
  "note": "비료 줌"
}
```

Expected:

```text
400 or 422
no care_logs row inserted
```

### Naive timestamp

Input:

```json
{
  "action_type": "watering",
  "acted_at": "2026-05-04T13:20:00",
  "note": "timezone 없음"
}
```

Expected:

```text
400 or 422
no care_logs row inserted
no character row inserted
```

### Cross-user access

Expected:

```text
cross-user POST -> 403 or 404
cross-user GET -> 403 or 404
no plant/care-log data leaked
```

---

## 20. 구현 금지 항목

이 티켓에서 아래 기능은 구현하지 않는다.

```text
pruning
repotting
fertilizing
custom care actions
reminder scheduling
reminder table
push notification
notification worker

GET /plants/{plant_id}/history
timeline items
environment history
character-state timeline
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

Rule Engine execution on care-log creation
precomputed recommendation write
recommendation_evidence write
snapshot generation
Home Card recomputation
```

---

## 21. 최종 완료 조건

Ticket 11은 아래가 모두 만족되면 완료다.

```text
POST /plants/{plant_id}/care-logs exists.
GET /plants/{plant_id}/care-logs exists.
CareLogCreate schema exists.
CareLogService exists.
CareLogRepository exists.

Only watering and note actions are accepted.
pruning/repotting/fertilizing/reminder/diagnosis/photo are rejected.

POST watering creates care_log.
POST watering appends after_watering character state through Ticket 4 CharacterStateEngine.
POST watering is atomic across care_log insert and character append.
POST note creates care_log.
POST note does not update character state.

GET care logs returns only logs for the requested plant.
GET care logs verifies user ownership.
GET care logs sorts by acted_at desc, created_at desc.
GET care logs supports limit with max 100.

Watering logs are readable as Rule Engine input.
Ticket 11 does not run Rule Engine.
Ticket 11 does not persist Rule Engine output.

No Growth History API, reminder, notification, chat, LLM, RAG, EvidenceBuilder, PromptBuilder, companion recommendation, Redis, scheduler, worker, vLLM, or Nginx leaks into this ticket.

/healthz liveness remains unchanged.
/readyz remains DB-only.
```
