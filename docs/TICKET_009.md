# TICKET-009 — Home Plant Card API

## 0. 목표

Sunshine 백엔드에 Home Plant Card API를 구현한다.

이 티켓은 기존 티켓들의 산출물을 조합해서 사용자가 홈 화면에서 볼 수 있는 one-screen plant status card를 반환한다.

Ticket 9는 새로운 care logic을 만들지 않는다.  
Rule Engine 결과를 읽어 `today_recommended_action`으로 노출할 뿐이다.

---

## 1. Ticket Identity

### Ticket ID

```text
TICKET-009
````

### Name

```text
Home Plant Card API
```

### Goal

```text
Return one-screen plant status by composing plant identity, latest character state, latest environment summary, and Rule Engine primary action.
```

### Core output

```text
GET /home
GET /plants/{plant_id}/card
HomeCardService
PlantCard DTO/schema
latest character state
latest environment summary
one primary care action from Rule Engine output
```

### Strict non-goal

```text
no detailed environment page
no 24h/7d graph/detail endpoint
no growth history timeline
no care-log API
no chat answer generation
no LLM
no RAG
no EvidenceBuilder
no PromptBuilder
no companion recommendation
no pest/disease answer
```

---

## 2. 주변 티켓과의 연결

Ticket 9는 composition ticket이다.

입력 소유권:

```text
Ticket 2:
  plant profile
  nickname
  room
  confirmed species

Ticket 4:
  latest character state
  mood / expression / status_message

Ticket 7:
  latest environment snapshot

Ticket 8:
  Rule Engine output
  primary_action
  care_status
  severity
  reason_codes
  evidence_facts
```

Ticket 9의 역할:

```text
plant identity
  + latest character state
  + latest environment summary
  + Rule Engine primary action
  -> one-screen plant card
```

중요:

```text
Ticket 9 may call Rule Engine.
Ticket 9 must not override Rule Engine.
Ticket 9 must not implement threshold/care decision logic.
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
app/repositories/rule_input_repository.py
app/services/rule_engine.py
app/schemas/plants.py
pyproject.toml
.github/workflows/ci.yml
```

### 생성 가능한 새 파일

```text
app/api/home.py
app/schemas/home.py
app/services/home_card_service.py
app/repositories/home_card_repository.py
tests/test_home_card_schema.py
tests/test_home_card_service.py
tests/test_home_api.py
tests/test_plant_card_api.py
tests/test_ticket9_boundary.py
```

### 조건부 허용

```text
app/schemas/plant_card.py
```

조건:

```text
home schema가 너무 커지는 경우에만 생성한다.
Ticket 9 card response 전용 schema여야 한다.
```

### Migration policy

기본값:

```text
No migration required.
```

정말 필요한 경우에만 허용:

```text
index for latest character lookup
index for latest environment snapshot lookup
```

금지 migration:

```text
chat tables
RAG tables
prompt tables
notification tables
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
app/services/environment_detail_service.py
app/services/growth_history_service.py
app/services/care_log_service.py
app/services/companion_recommendation.py
app/repositories/chunk_repository.py
app/repositories/audit_repository.py
app/api/chat.py
app/api/environment.py
app/api/history.py
app/api/care_logs.py
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
Ticket 9 must not modify MQTT, Vision, or Snapshot generation logic except for import/type compatibility.
```

---

## 5. API 계약 — GET /home

### Endpoint

```http
GET /home?user_id=<uuid>
```

### Response

```json
{
  "plants": [
    {
      "plant_id": "uuid",
      "nickname": "초록이",
      "room_name": "거실",
      "species": {
        "species_profile_id": "uuid",
        "korean_name": "몬스테라",
        "scientific_name": "Monstera deliciosa",
        "common_name": "Monstera"
      },
      "character": {
        "mood": "thirsty",
        "expression": "droop",
        "status_message": "목이 말라 보여요.",
        "primary_action": "water",
        "reason_code": "low_soil_moisture"
      },
      "latest_environment": {
        "measured_at": "2026-05-04T12:00:00+09:00",
        "temperature_c": 22.0,
        "humidity_pct": 50.0,
        "light_lux": 1000.0,
        "soil_moisture_pct": 25.0,
        "source_window": "latest"
      },
      "today_recommended_action": {
        "primary_action": "water",
        "care_status": "needs_action",
        "severity": "medium",
        "reason_codes": ["soil_moisture_below_min"],
        "source": "rule_engine"
      }
    }
  ]
}
```

### 규칙

```text
Must return only plants belonging to user_id.
Must return one card per plant.
Must include latest character state.
Must include latest environment summary if available.
Must include exactly one today_recommended_action object.
today_recommended_action must be derived from Rule Engine output.
Must not include detailed 24h/7d history.
Must not include chat answer text.
```

---

## 6. API 계약 — GET /plants/{plant_id}/card

### Endpoint

```http
GET /plants/{plant_id}/card?user_id=<uuid>
```

### Response

```json
{
  "plant": {
    "plant_id": "uuid",
    "nickname": "초록이",
    "room_name": "거실",
    "species": {
      "species_profile_id": "uuid",
      "korean_name": "몬스테라",
      "scientific_name": "Monstera deliciosa",
      "common_name": "Monstera"
    },
    "character": {
      "mood": "thirsty",
      "expression": "droop",
      "status_message": "목이 말라 보여요.",
      "primary_action": "water",
      "reason_code": "low_soil_moisture"
    },
    "latest_environment": {
      "measured_at": "2026-05-04T12:00:00+09:00",
      "temperature_c": 22.0,
      "humidity_pct": 50.0,
      "light_lux": 1000.0,
      "soil_moisture_pct": 25.0,
      "source_window": "latest"
    },
    "today_recommended_action": {
      "primary_action": "water",
      "care_status": "needs_action",
      "severity": "medium",
      "reason_codes": ["soil_moisture_below_min"],
      "source": "rule_engine"
    }
  }
}
```

### Status behavior

```text
200:
  plant exists and belongs to user

404 or 403:
  plant does not exist or does not belong to user

200 with insufficient_data:
  plant exists but latest snapshot or thresholds are missing
```

---

## 7. HomeCardService 계약

아래 파일을 생성한다.

```text
app/services/home_card_service.py
```

필수 class shape:

```python
from datetime import datetime
from uuid import UUID

class HomeCardService:
    async def get_home(
        self,
        user_id: UUID,
        *,
        now: datetime,
    ) -> HomeResponse:
        ...

    async def get_plant_card(
        self,
        plant_id: UUID,
        user_id: UUID,
        *,
        now: datetime,
    ) -> PlantCardResponse:
        ...
```

필수 동작:

```text
1. Verify user/plant ownership.
2. Load plant identity and species profile.
3. Load latest character state.
4. Load latest environment snapshot.
5. Load recent care logs only as Rule Engine input.
6. Invoke RuleEngine for recommended action.
7. Compose stable card response.
```

금지:

```text
new rule logic inside HomeCardService
threshold comparisons outside Rule Engine
LLM call
RAG retrieval
prompt generation
evidence persistence
chat response
detailed history traversal
```

---

## 8. Repository 계약

아래 파일을 생성한다.

```text
app/repositories/home_card_repository.py
```

허용 read:

```text
list plants by user_id
get plant by plant_id + user_id
get species profile for plant
get latest plant_character
get latest environment_snapshot where window = latest
get recent care_logs for Rule Engine input
```

금지 write:

```text
plant_characters
sensor_readings
environment_snapshots
care_logs
chat_requests
llm_runs
recommendation_evidence
retrieved_chunks
```

중요:

```text
Ticket 9 is read/compose only.
```

---

## 9. Card Field 계약

Required card fields:

```text
plant_id
nickname
room_name
species
character
latest_environment
today_recommended_action
```

Allowed `character` fields:

```text
mood
expression
status_message
primary_action
reason_code
```

Allowed `latest_environment` fields:

```text
measured_at
temperature_c
humidity_pct
light_lux
soil_moisture_pct
source_window
```

Allowed `today_recommended_action` fields:

```text
primary_action
care_status
severity
reason_codes
source
```

Forbidden fields:

```text
chat_answer
final_answer
prompt
retrieved_chunks
evidence_bundle
llm_response
diagnosis
pest_prediction
disease_prediction
companion_recommendations
history
timeline
24h_series
7d_series
graph_data
```

---

## 10. Rule Engine Integration 계약

Ticket 9는 Rule Engine을 care action의 source of truth로 사용한다.

필수:

```text
today_recommended_action.source = "rule_engine"
today_recommended_action.primary_action == RuleEngine.primary_action
today_recommended_action.care_status == RuleEngine.care_status
today_recommended_action.severity == RuleEngine.severity
today_recommended_action.reason_codes == RuleEngine.reason_codes
```

금지:

```text
HomeCardService choosing primary_action independently
HomeCardService overriding RuleEngine output
LLM overriding RuleEngine output
hardcoded watering action in card layer
threshold comparison in HomeCardService
```

Invalid implementation:

```python
if soil_moisture < threshold:
    primary_action = "water"
```

Valid implementation:

```python
rule_result = RuleEngine.evaluate(input)
today_recommended_action = RuleActionDTO.from_rule_result(rule_result)
```

---

## 11. Missing Data 계약

### No latest environment snapshot

If no latest environment snapshot exists:

```json
{
  "latest_environment": null,
  "today_recommended_action": {
    "primary_action": "none",
    "care_status": "insufficient_data",
    "severity": "none",
    "reason_codes": ["missing_latest_snapshot"],
    "source": "rule_engine"
  }
}
```

### No character state

If no character state exists:

```json
{
  "character": {
    "mood": "neutral",
    "expression": "normal",
    "status_message": "상태 정보가 아직 없어요.",
    "primary_action": "none",
    "reason_code": "missing_character_state"
  }
}
```

규칙:

```text
Do not synthesize fake environment numbers.
Do not create character rows automatically.
Do not run snapshot generation automatically.
Do not call LLM for missing data.
Do not fail /readyz because card data is missing.
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
      -> GET /home
      -> GET /plants/{plant_id}/card
      -> HomeCardService
      -> RuleEngine
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
home-worker
card-worker
redis
nginx
vllm
model-server
generic-worker
```

Backend process invariant:

```text
exactly one foreground uvicorn process
no card scheduler
no recommendation worker
no chat orchestrator
no LLM/vLLM process
```

Startup allowed:

```text
import app.main
create FastAPI app
register /home and /plants/{plant_id}/card routes
import HomeCardService definitions
```

Startup forbidden:

```text
precompute cards for all plants
run Rule Engine for all plants
generate snapshots
update character states
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
external HTTP APIs
LLM/vLLM calls
RAG/vector DB calls
Redis calls
push notification calls
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
HOME_CARD_LLM_MODE
```

Note:

```text
If legacy Ticket 6 text says MQTT_TOPIC=sunshine/+/readings, use the updated project contract: MQTT_TOPIC=sensor/readings/+.
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
query home cards
query plants
query snapshots
run Rule Engine
check Postgres
check MQTT
check LLM/RAG
change response shape
```

---

## 15. `/readyz` 계약

Ticket 9에서 `/readyz`는 DB readiness만 확인한다.
Product-data readiness가 아니다.

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
require at least one plant
require latest environment snapshot
require latest character state
run Rule Engine
check LLM/RAG
add "home_card": "ok"
add "rule_engine": "ok"
```

Home card correctness는 `/readyz`가 아니라 functional tests/gates에서 검증한다.

---

## 16. Read-only Composition 계약

Ticket 9 API calls는 read-only여야 한다.

Allowed DB operations:

```text
read plants
read species_profiles
read latest plant_characters
read latest environment_snapshots
read recent care_logs
```

Forbidden DB operations:

```text
insert/update plant_characters
insert sensor_readings
insert/update environment_snapshots
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
```

---

## 18. 테스트 요구사항

아래 테스트를 추가한다.

```text
tests/test_home_card_schema.py
tests/test_home_card_service.py
tests/test_home_api.py
tests/test_plant_card_api.py
tests/test_ticket9_boundary.py
```

### Schema tests

필수 확인:

```text
PlantCard DTO includes plant_id, nickname, room_name, species, character, latest_environment, today_recommended_action.
character allows only mood, expression, status_message, primary_action, reason_code.
latest_environment allows only measured_at, temperature_c, humidity_pct, light_lux, soil_moisture_pct, source_window.
today_recommended_action allows only primary_action, care_status, severity, reason_codes, source.
forbidden fields do not appear.
```

### HomeCardService tests

필수 케이스:

```text
get_home returns one card per user-owned plant.
get_home excludes plants owned by other users.
get_plant_card verifies plant ownership.
loads latest character state.
loads latest environment snapshot where window = latest.
calls RuleEngine.
today_recommended_action copies RuleEngine output.
does not compute threshold logic directly.
missing latest snapshot returns insufficient_data.
missing character returns neutral fallback without DB write.
```

### API tests

필수 케이스:

```text
GET /home?user_id=<uuid> returns 200.
GET /home returns plants list.
GET /home includes one card per user plant.
GET /plants/{plant_id}/card?user_id=<uuid> returns 200 for owner.
GET /plants/{plant_id}/card blocks cross-user access with 403 or 404.
GET /plants/{plant_id}/card returns 200 with insufficient_data when snapshot is missing.
```

### Rule Engine source tests

필수 확인:

```text
today_recommended_action.source == "rule_engine"
primary_action equals RuleEngine output.
care_status equals RuleEngine output.
severity equals RuleEngine output.
reason_codes equals RuleEngine output.
HomeCardService does not override primary_action.
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

no Chat API
no Companion API
no Growth History API
no Care Log API
no Environment Detail API

no LLM/RAG/Vision/Redis/scheduler dependency

no forbidden fields in response:
  chat_answer
  final_answer
  prompt
  retrieved_chunks
  evidence_bundle
  llm_response
  diagnosis
  pest_prediction
  disease_prediction
  companion_recommendations
  history
  timeline
  24h_series
  7d_series
  graph_data

no writes to:
  plant_characters
  sensor_readings
  environment_snapshots
  care_logs
  chat_requests
  llm_runs
  recommendation_evidence
  retrieved_chunks
```

---

## 19. Functional Expectations

### Plant card success

Input:

```http
GET /plants/00000000-0000-0000-0000-000000000903/card?user_id=00000000-0000-0000-0000-000000000901
```

Expected:

```json
{
  "plant": {
    "plant_id": "00000000-0000-0000-0000-000000000903",
    "nickname": "초록이",
    "room_name": "거실",
    "species": {
      "korean_name": "몬스테라",
      "scientific_name": "Monstera deliciosa",
      "common_name": "Monstera"
    },
    "character": {
      "mood": "thirsty",
      "expression": "droop",
      "status_message": "목이 말라 보여요.",
      "primary_action": "water",
      "reason_code": "low_soil_moisture"
    },
    "latest_environment": {
      "temperature_c": 22.0,
      "humidity_pct": 50.0,
      "light_lux": 1000.0,
      "soil_moisture_pct": 25.0,
      "source_window": "latest"
    },
    "today_recommended_action": {
      "primary_action": "water",
      "care_status": "needs_action",
      "severity": "medium",
      "reason_codes": ["soil_moisture_below_min"],
      "source": "rule_engine"
    }
  }
}
```

### Home success

Input:

```http
GET /home?user_id=00000000-0000-0000-0000-000000000901
```

Expected:

```text
returns {"plants": [...]}
includes only plants owned by user_id
each plant card includes species, character, latest_environment, today_recommended_action
```

### Cross-user block

Input:

```http
GET /plants/{plant_id}/card?user_id=<other_user_id>
```

Expected:

```text
403 or 404
no plant data leaked
```

### Missing snapshot

If plant has no latest environment snapshot:

```json
{
  "latest_environment": null,
  "today_recommended_action": {
    "primary_action": "none",
    "care_status": "insufficient_data",
    "severity": "none",
    "reason_codes": ["missing_latest_snapshot"],
    "source": "rule_engine"
  }
}
```

### Missing character

If plant has no character state:

```json
{
  "character": {
    "mood": "neutral",
    "expression": "normal",
    "status_message": "상태 정보가 아직 없어요.",
    "primary_action": "none",
    "reason_code": "missing_character_state"
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
GET /plants/{plant_id}/environment
24h/7d detail response
graph rendering data
environment explanation page

POST /plants/{plant_id}/care-logs
GET /plants/{plant_id}/care-logs
watering log action
character update after watering

GET /plants/{plant_id}/history
timeline items
growth history

chat intent classifier
POST /chat
POST /plants/{plant_id}/chat
LLMPort
PromptBuilder
EvidenceBuilder
RAG retrieval
retrieved_chunks
final answer sections [결론][근거][행동][주의]

companion recommendation
compatibility filter
recommendation ranking

LLM explanation
pest/disease diagnosis
push notification
realtime stream
SSE
websocket
Redis queue
scheduler
home-worker
card-worker
```

---

## 21. 최종 완료 조건

Ticket 9는 아래가 모두 만족되면 완료다.

```text
GET /home exists.
GET /plants/{plant_id}/card exists.
HomeCardService exists.
HomeCardRepository exists.
PlantCard DTO/schema exists.
GET /home returns one card per user-owned plant.
GET /plants/{plant_id}/card returns one plant card for owner.
Cross-user card access is blocked.
Card includes plant identity and species.
Card includes latest character state or neutral fallback.
Card includes latest environment summary or null.
Card includes exactly one today_recommended_action.
today_recommended_action is copied from RuleEngine output.
today_recommended_action.source == "rule_engine".
Missing latest snapshot degrades to insufficient_data.
Home/card APIs are read-only.
No fake environment values are synthesized.
No character rows are auto-created for missing character.
No snapshot generation runs automatically.
No threshold/care decision logic is implemented in HomeCardService.
No detailed environment, 24h/7d graph, growth history, care-log API, chat, LLM, RAG, EvidenceBuilder, PromptBuilder, companion recommendation, Redis, scheduler, worker, vLLM, or Nginx leaks into this ticket.
/healthz liveness remains unchanged.
/readyz remains DB-only.
```
