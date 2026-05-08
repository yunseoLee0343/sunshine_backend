# TICKET-004 — Character State Engine

## 0. 목표

Sunshine 백엔드에 deterministic Character State Engine을 구현한다.

이 티켓은 이미 알려진 plant condition을 companion character state로 변환하고, 그 결과를 `plant_characters` history에 append-only로 저장하는 기능만 담당한다.

이 티켓은 care decision engine이 아니다.  
즉 물을 줘야 하는지, 빛이 부족한지 같은 판단 로직을 계산하지 않는다. 그런 baseline care decision은 Ticket 8 Rule Engine이 담당한다.

---

## 1. 핵심 요구사항

### Ticket ID

```text
TICKET-004
````

### Name

```text
Character State Engine
```

### Goal

```text
Map deterministic plant condition signals into companion character state and persist character state history.
```

### Core output

```text
CharacterState schema
CharacterStateEngine
deterministic condition -> character state mapping
plant_characters append-only history
latest character state included in plant payload
```

---

## 2. 주변 티켓과의 경계

Ticket 4는 character state만 담당한다.

```text
Ticket 4:
  condition
    -> CharacterStateEngine
    -> CharacterState
    -> plant_characters history
    -> latest character block in plant response
```

다른 티켓의 책임:

```text
Ticket 5:
  sensor reading ingestion

Ticket 7:
  environment snapshot aggregation

Ticket 8:
  Rule Engine baseline care decision

Ticket 9:
  Home Plant Card API with recommendation

Ticket 11:
  care action logging API

Ticket 12:
  growth history API
```

Ticket 4에서 금지:

```text
sensor_readings 생성
environment_snapshots 생성
Rule Engine 판단
care_logs 생성
growth history 생성
home/card recommendation 생성
LLM/RAG 호출
```

---

## 3. 수정/생성 허용 파일

### 수정 가능한 기존 파일

```text
app/api/plants.py
app/schemas/plants.py
app/models/plant_character.py
app/repositories/character_repository.py
app/repositories/plant_repository.py
app/services/plant_onboarding.py
app/main.py
pyproject.toml
.github/workflows/ci.yml
```

### 생성 가능한 새 파일

```text
app/domain/__init__.py
app/domain/character_state.py
app/services/character_state_engine.py
app/schemas/character_state.py
tests/test_character_state_engine.py
tests/test_character_state_persistence.py
tests/test_character_state_api_integration.py
tests/test_ticket4_boundary.py
```

### 조건부 migration 허용

Ticket 1 schema에 Ticket 4 필드가 없을 때만 migration 추가 가능.

```text
alembic/versions/<ticket4_character_state_fields>.py
```

허용 범위:

```text
plant_characters.primary_action 추가
latest character state lookup에 필요한 index 추가
```

금지:

```text
sensor table 추가
snapshot table 추가
rule table 추가
chat/RAG/LLM table 추가
care log table 추가
```

---

## 4. 금지 파일/디렉터리

아래 파일/디렉터리는 만들거나 수정하지 않는다.

```text
app/mqtt/
app/llm/
app/rag/
app/retrieval/
app/workers/
app/rules/
app/services/rule_engine.py
app/services/snapshot_service.py
app/services/sensor_ingest.py
app/services/care_log_service.py
app/services/growth_history_service.py
app/services/home_card_service.py
app/services/evidence_builder.py
app/services/prompt_builder.py
app/services/chat_orchestrator.py
app/repositories/sensor_repository.py
app/repositories/snapshot_repository.py
app/repositories/care_log_repository.py
app/repositories/audit_repository.py
deploy/
```

---

## 5. CharacterState Domain Schema 계약

`app/domain/character_state.py`에 strict `CharacterState` domain schema를 정의한다.

필수 shape:

```json
{
  "mood": "happy | thirsty | sleepy | stressed | neutral",
  "expression": "smile | droop | normal | sweat",
  "status_message": "str",
  "primary_action": "none | water | move_to_brighter_place | stabilize_humidity",
  "reason_code": "good | low_soil_moisture | low_light | unstable_humidity | after_watering | onboarding_created"
}
```

허용 enum:

```text
mood:
  happy
  thirsty
  sleepy
  stressed
  neutral

expression:
  smile
  droop
  normal
  sweat

primary_action:
  none
  water
  move_to_brighter_place
  stabilize_humidity

reason_code:
  good
  low_soil_moisture
  low_light
  unstable_humidity
  after_watering
  onboarding_created
```

규칙:

```text
모든 field는 finite enum 또는 deterministic template 기반이어야 한다.
status_message는 한국어 text 가능.
status_message는 deterministic template에서만 선택한다.
reason_code는 state 선택 이유를 설명해야 한다.
primary_action은 display hint일 뿐, Rule Engine care decision이 아니다.
```

금지:

```text
free-form mood
free-form expression
free-form reason_code
LLM-generated status_message
user-provided arbitrary state injection
random/probabilistic state choice
```

---

## 6. Character State Input 계약

CharacterStateEngine input은 내부 DTO여야 한다.

예시 shape:

```json
{
  "plant_id": "00000000-0000-0000-0000-000000000401",
  "condition": "low_soil_moisture",
  "source": "manual_test",
  "observed_at": "2026-05-04T12:00:00+09:00"
}
```

허용 condition:

```text
good
low_soil_moisture
low_light
unstable_humidity
after_watering
onboarding_created
```

허용 source:

```text
onboarding
manual_test
future_snapshot
future_care_log
```

중요:

```text
Ticket 4는 future_snapshot / future_care_log source label을 받아도 된다.
하지만 snapshot aggregation이나 care log API를 구현하면 안 된다.
```

---

## 7. CharacterStateEngine Mapping 계약

`app/services/character_state_engine.py`에 `CharacterStateEngine`을 구현한다.

필수 동작:

```text
condition을 받아 deterministic CharacterState를 반환한다.
같은 condition이면 항상 같은 CharacterState를 반환한다.
unknown/free-form condition은 reject한다.
```

필수 mapping:

```text
condition: good
=> mood: happy
=> expression: smile
=> primary_action: none
=> reason_code: good
=> status_message: "상태가 좋아 보여요."

condition: low_soil_moisture
=> mood: thirsty
=> expression: droop
=> primary_action: water
=> reason_code: low_soil_moisture
=> status_message: "목이 말라 보여요."

condition: low_light
=> mood: sleepy
=> expression: normal
=> primary_action: move_to_brighter_place
=> reason_code: low_light
=> status_message: "빛이 조금 부족해 보여요."

condition: unstable_humidity
=> mood: stressed
=> expression: sweat
=> primary_action: stabilize_humidity
=> reason_code: unstable_humidity
=> status_message: "습도 변화가 커서 스트레스를 받은 것 같아요."

condition: after_watering
=> mood: happy
=> expression: smile
=> primary_action: none
=> reason_code: after_watering
=> status_message: "물을 마시고 기분이 좋아졌어요."

condition: onboarding_created
=> mood: neutral
=> expression: normal
=> primary_action: none
=> reason_code: onboarding_created
=> status_message: "새 식물이 등록되었어요."
```

금지:

```text
LLM 호출
Rule Engine 호출
sensor/snapshot/care log 조회
random mood 선택
current time 기반 state 변경
user 입력 mood/expression/status_message passthrough
```

---

## 8. Persistence 계약

모든 새 character state는 `plant_characters`에 새 row로 저장한다.

필수 DB row fields:

```text
id: UUID
plant_id: UUID
mood: enum-backed string
expression: enum-backed string
status_message: text
primary_action: enum-backed string
reason_code: enum-backed string
created_at: timestamptz
```

규칙:

```text
old character row를 overwrite하지 않는다.
history는 append-only다.
latest state는 created_at/id 기준 newest row다.
state 변화 이유는 reason_code로 설명 가능해야 한다.
```

금지:

```text
기존 row in-place update
이전 character history 삭제
JSON blob만으로 state 저장
local file persistence
process memory-only history
audit/evidence table write
llm_runs write
care_logs write
sensor_readings write
environment_snapshots write
```

---

## 9. CharacterRepository 계약

`app/repositories/character_repository.py`를 사용 또는 보강한다.

필수 operations:

```text
insert_character_state(plant_id, character_state)
get_latest_character_state(plant_id)
list_character_states(plant_id) only if needed for tests
```

허용 DB operations:

```text
read plant by plant_id/user_id
insert plant_characters row
read latest plant_characters row
list plant_characters rows for tests
```

금지 DB operations:

```text
insert sensor_readings
insert environment_snapshots
insert care_logs
insert chat_requests
insert llm_runs
insert recommendation_evidence
insert retrieved_chunks
```

---

## 10. API Integration 계약

Ticket 4는 기존 plant onboarding/read response에 latest character block을 포함할 수 있다.

허용 response shape:

```json
{
  "character": {
    "mood": "happy",
    "expression": "smile",
    "status_message": "상태가 좋아 보여요.",
    "primary_action": "none",
    "reason_code": "good"
  }
}
```

### Onboarding compatibility

Ticket 2에서 식물 등록 시 initial character state가 필요하다면 `onboarding_created` mapping을 사용한다.

Expected initial character:

```json
{
  "character": {
    "mood": "neutral",
    "expression": "normal",
    "status_message": "새 식물이 등록되었어요.",
    "primary_action": "none",
    "reason_code": "onboarding_created"
  }
}
```

### Optional internal/dev endpoint

필요할 때만 아래 endpoint를 구현할 수 있다.

```http
POST /plants/{plant_id}/character-state
```

Request:

```json
{
  "user_id": "00000000-0000-0000-0000-000000000401",
  "condition": "low_soil_moisture"
}
```

Response:

```json
{
  "character": {
    "mood": "thirsty",
    "expression": "droop",
    "status_message": "목이 말라 보여요.",
    "primary_action": "water",
    "reason_code": "low_soil_moisture"
  }
}
```

규칙:

```text
이 endpoint는 MVP internal/dev deterministic state update 용도다.
caller가 mood/expression/status_message를 직접 지정할 수 없어야 한다.
caller는 condition만 전달한다.
```

금지 API:

```text
POST /sensor-readings
POST /plants/{plant_id}/care-logs
GET /plants/{plant_id}/history
GET /home
GET /plants/{plant_id}/card
POST /chat
POST /chat/intent
```

---

## 11. Runtime 계약

허용 runtime topology:

```text
host
  -> backend container
      -> uvicorn app.main:app
      -> existing plant onboarding/read APIs
      -> optional POST /plants/{plant_id}/character-state
      -> CharacterStateEngine
      -> CharacterRepository

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
redis
mqtt
worker
nginx
vllm
model-server
```

Backend process invariant:

```text
exactly one foreground uvicorn process
no background character updater
no scheduler
no worker
no MQTT subscriber
no Redis consumer
no LLM runtime
no model loader
```

Startup invariant:

```text
Allowed:
  import app.main
  create FastAPI app
  register routes
  instantiate pure CharacterStateEngine object

Forbidden:
  query existing plants
  recompute character states
  run migrations
  start scheduler
  start worker
  subscribe to MQTT
  connect to Redis
  call LLM
  call external APIs
```

---

## 12. Health / Readiness 계약

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
check CharacterStateEngine
check plant_characters table
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
check CharacterStateEngine
check whether plant_characters has rows
add "character_state": "ok"
add "rule_engine": "ok"
```

---

## 13. Dependency 계약

허용 dependency:

```text
existing FastAPI / Pydantic / SQLAlchemy / Alembic stack
pytest / httpx / ruff
```

금지 dependency:

```text
openai
anthropic
vllm
torch
tensorflow
onnxruntime
openvino
redis
paho-mqtt
pgvector
sentence-transformers
```

---

## 14. 테스트 요구사항

아래 테스트를 추가한다.

```text
tests/test_character_state_engine.py
tests/test_character_state_persistence.py
tests/test_character_state_api_integration.py
tests/test_ticket4_boundary.py
```

### CharacterStateEngine tests

필수 케이스:

```text
good -> happy / smile / none / good
low_soil_moisture -> thirsty / droop / water / low_soil_moisture
low_light -> sleepy / normal / move_to_brighter_place / low_light
unstable_humidity -> stressed / sweat / stabilize_humidity / unstable_humidity
after_watering -> happy / smile / none / after_watering
onboarding_created -> neutral / normal / none / onboarding_created

same condition -> same output
unknown/free-form condition -> reject
status_message comes from deterministic template
no arbitrary mood/expression accepted
```

### Persistence tests

필수 케이스:

```text
new state inserts plant_characters row
old row is not overwritten
multiple updates append multiple rows
latest lookup returns newest row
reason_code is persisted
primary_action is persisted
```

### API integration tests

필수 케이스:

```text
plant onboarding returns initial character block
initial condition is onboarding_created
plant detail/read response includes latest character block
POST /plants/{plant_id}/character-state with condition updates character state if endpoint is implemented
free-form mood/expression/status_message in request is rejected
```

### Boundary tests

필수 확인:

```text
no app/mqtt/
no app/llm/
no app/rag/
no app/retrieval/
no app/workers/
no app/rules/

no MQTT dependency
no Redis dependency
no LLM/RAG/vLLM/OpenAI/Anthropic dependency
no vision/runtime dependency

no sensor ingestion endpoint
no care-log endpoint
no growth-history endpoint
no home/card recommendation endpoint
no chat endpoint

no writes to:
  sensor_readings
  environment_snapshots
  care_logs
  chat_requests
  llm_runs
  recommendation_evidence
  retrieved_chunks
```

---

## 15. Functional Expectations

### Deterministic mapping

Input:

```text
condition = low_soil_moisture
```

Expected:

```text
mood = thirsty
expression = droop
primary_action = water
reason_code = low_soil_moisture
status_message = "목이 말라 보여요."
```

### Append-only history

Expected:

```text
first state update:
  plant_characters count = N + 1

second state update:
  plant_characters count = N + 2

latest lookup:
  returns second state
```

### Onboarding state

When plant is created:

```text
condition = onboarding_created
```

Expected character:

```text
mood = neutral
expression = normal
primary_action = none
reason_code = onboarding_created
status_message = "새 식물이 등록되었어요."
```

### Free-form rejection

Invalid request example:

```json
{
  "condition": "make_it_super_cute_by_llm",
  "mood": "whatever",
  "expression": "sparkle"
}
```

Expected:

```text
HTTP 400 or 422
no character row inserted
```

---

## 16. 구현 금지 항목

이 티켓에서 아래 기능은 구현하지 않는다.

```text
LLM-generated mood
arbitrary free-form character state
Rule Engine baseline care decision
watering/light/humidity/temperature thresholds
recommendation severity
evidence facts
sensor reading ingestion
MQTT subscription
snapshot aggregation
environment detail endpoint
care-log API
growth-history API
home/card recommendation API
chat API
RAG retrieval
PromptBuilder
EvidenceBuilder
LLMPort
worker
scheduler
push notification
vision diagnosis
```

---

## 17. 최종 완료 조건

Ticket 4는 아래가 모두 만족되면 완료다.

```text
CharacterState schema exists.
CharacterStateEngine exists.
All required condition mappings are deterministic.
Unknown/free-form condition is rejected.
status_message uses deterministic template.
Every state update appends plant_characters row.
Latest character lookup returns newest state.
Plant onboarding/read payload includes latest character block where required.
No old character row is overwritten.
No sensor, MQTT, snapshot, Rule Engine, care-log, growth-history, Home Card, Chat, LLM, or RAG feature leaks into this ticket.
/healthz liveness remains unchanged.
/readyz remains DB-only.
```