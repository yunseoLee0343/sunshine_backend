# TICKET-002 — Plant Onboarding API

## 0. 목표

Sunshine 백엔드에 식물 등록 온보딩 API를 구현한다.

이 티켓은 사용자가 식물 종 후보를 확인한 뒤, 특정 species를 선택해서 plant profile을 생성하고 조회할 수 있게 만드는 첫 user-visible vertical slice다.

이 티켓은 실제 vision inference, VisionPort, sensor ingestion, MQTT, Rule Engine, LLM, RAG, companion recommendation을 구현하지 않는다.

---

## 1. 핵심 요구사항

### Ticket ID

```text
TICKET-002
````

### Name

```text
Plant Onboarding API
```

### Goal

```text
Allow a user to create and retrieve a plant profile after confirming a species candidate.
```

### Core output

```text
POST /plants/species-candidates
POST /plants
GET /plants
GET /plants/{plant_id}
confirmed species stored
nickname stored
room stored
initial character state stored
plant card payload returned
```

---

## 2. 주변 티켓과의 경계

Ticket 2는 온보딩 API만 담당한다.

```text
Ticket 2:
  user selects species candidate
    -> POST /plants
    -> plants row inserted
    -> initial plant_characters row inserted
    -> plant card payload returned
```

다른 티켓의 책임:

```text
Ticket 3:
  SpeciesClassifierPort + deterministic mock classifier

Ticket 4:
  Character State Engine

Ticket 5:
  Sensor Reading Ingestion API

Ticket 6:
  MQTT Sensor Ingestion

Ticket 7:
  Environment Snapshot Aggregation

Ticket 8:
  Rule Engine Baseline

Ticket 9:
  Home Plant Card API with latest environment and recommended action

Ticket 10:
  Plant Environment Detail API

Ticket 11:
  Care Action Logging API

Ticket 12:
  Growth History API

Ticket 13+:
  Chat / RAG / LLM pipeline
```

Ticket 2에서 금지:

```text
real image classifier
VisionPort
mock vision classifier
disease/pest/health diagnosis
sensor ingestion
MQTT
snapshot aggregation
Rule Engine
care recommendation
chat
LLM
RAG
companion recommendation
frontend
```

---

## 3. 수정/생성 허용 파일

### 수정 가능한 기존 파일

```text
app/main.py
app/core/config.py
app/db/session.py
app/models/plant.py
app/models/plant_character.py
app/models/species_profile.py
app/models/user.py
app/repositories/__init__.py
pyproject.toml
.github/workflows/ci.yml
```

### 생성 가능한 새 파일

```text
app/api/__init__.py
app/api/plants.py
app/schemas/__init__.py
app/schemas/plants.py
app/repositories/plant_repository.py
app/repositories/species_repository.py
app/repositories/character_repository.py
app/services/__init__.py
app/services/plant_onboarding.py
tests/test_plant_onboarding_api.py
tests/test_plant_onboarding_service.py
tests/test_species_candidates_contract.py
tests/test_ticket2_boundary.py
```

### 조건부 migration 허용

Ticket 1 schema에 온보딩에 필요한 column이 없을 때만 허용한다.

```text
alembic/versions/<ticket2_small_fix>.py
```

조건:

```text
only additive onboarding-required schema repair
no new AI/RAG/sensor tables
```

---

## 4. 금지 파일/디렉터리

아래 파일/디렉터리는 만들거나 수정하지 않는다.

```text
app/mqtt/
app/llm/
app/rag/
app/retrieval/
app/vision/
app/workers/
app/rules/
app/services/rule_engine.py
app/services/snapshot_service.py
app/services/evidence_builder.py
app/services/prompt_builder.py
app/services/chat_orchestrator.py
app/repositories/audit_repository.py
app/repositories/sensor_repository.py
app/repositories/chunk_repository.py
deploy/
```

주의:

```text
Ticket 2에서는 app/api, app/services, app/repositories, app/schemas 계층을 시작할 수 있다.
하지만 AI/runtime/sensor/worker 계층은 만들면 안 된다.
```

---

## 5. API 계약 — POST /plants/species-candidates

### Endpoint

```http
POST /plants/species-candidates
Content-Type: application/json
```

### 목적

```text
온보딩 중 사용자가 선택할 수 있는 species candidate를 반환한다.
이 endpoint는 image inference가 아니다.
image_ref를 받을 수 있지만 opaque reference로만 취급한다.
```

### Request

```json
{
  "user_id": "00000000-0000-0000-0000-000000000101",
  "image_ref": "uploads/mock/monstera.jpg"
}
```

### Response

```json
{
  "candidates": [
    {
      "species_profile_id": "00000000-0000-0000-0000-000000000201",
      "korean_name": "몬스테라",
      "scientific_name": "Monstera deliciosa",
      "common_name": "Monstera",
      "confidence_label": "mock_or_catalog_match"
    }
  ]
}
```

### 규칙

```text
existing species_profiles row만 반환한다.
species_profiles가 없으면 empty candidates list를 반환한다.
fallback candidate는 이미 DB에 있는 경우에만 가능하다.
image content를 classify하지 않는다.
image bytes를 inspect하지 않는다.
ML model을 load하지 않는다.
disease/pest/health/diagnosis field를 반환하지 않는다.
```

허용 구현:

```text
first N species_profiles from DB
simple catalog lookup
optional simple text hint filtering
```

금지 구현:

```text
VisionPort
MockSpeciesClassifier
real image classifier
image file open
URL fetch
image decoding
model loading
diagnosis fields
```

---

## 6. API 계약 — POST /plants

### Endpoint

```http
POST /plants
Content-Type: application/json
```

### 목적

```text
사용자가 species candidate를 확정한 뒤 plant profile을 생성한다.
```

### Request

```json
{
  "user_id": "00000000-0000-0000-0000-000000000101",
  "species_profile_id": "00000000-0000-0000-0000-000000000201",
  "nickname": "초록이",
  "room_name": "거실"
}
```

### Response

```json
{
  "plant": {
    "plant_id": "00000000-0000-0000-0000-000000000301",
    "user_id": "00000000-0000-0000-0000-000000000101",
    "species_profile_id": "00000000-0000-0000-0000-000000000201",
    "nickname": "초록이",
    "room_name": "거실",
    "species": {
      "korean_name": "몬스테라",
      "scientific_name": "Monstera deliciosa",
      "common_name": "Monstera"
    },
    "character": {
      "mood": "neutral",
      "expression": "normal",
      "status_message": "새 식물이 등록되었어요.",
      "reason_code": "onboarding_created"
    }
  }
}
```

### 필수 동작

```text
user_id must exist.
species_profile_id must exist.
nickname is required and non-empty.
room_name is optional.
plant row is inserted.
initial plant_character row is inserted in the same transaction.
response includes plant card payload.
```

### Error

```text
422:
  missing species_profile_id
  missing nickname
  empty nickname
  invalid UUID shape

404:
  user_id does not exist
  species_profile_id does not exist
```

---

## 7. API 계약 — GET /plants

### Endpoint

```http
GET /plants?user_id=<uuid>
```

### Response

```json
{
  "plants": [
    {
      "plant_id": "00000000-0000-0000-0000-000000000301",
      "nickname": "초록이",
      "room_name": "거실",
      "species": {
        "species_profile_id": "00000000-0000-0000-0000-000000000201",
        "korean_name": "몬스테라",
        "scientific_name": "Monstera deliciosa",
        "common_name": "Monstera"
      },
      "character": {
        "mood": "neutral",
        "expression": "normal",
        "status_message": "새 식물이 등록되었어요.",
        "reason_code": "onboarding_created"
      }
    }
  ]
}
```

### 규칙

```text
given user_id의 plant만 반환한다.
다른 사용자의 plant를 노출하지 않는다.
sensor readings를 포함하지 않는다.
environment snapshot을 포함하지 않는다.
rule recommendation을 포함하지 않는다.
chat history를 포함하지 않는다.
RAG evidence를 포함하지 않는다.
```

---

## 8. API 계약 — GET /plants/{plant_id}

### Endpoint

```http
GET /plants/{plant_id}?user_id=<uuid>
```

### Response

```json
{
  "plant": {
    "plant_id": "00000000-0000-0000-0000-000000000301",
    "user_id": "00000000-0000-0000-0000-000000000101",
    "species_profile_id": "00000000-0000-0000-0000-000000000201",
    "nickname": "초록이",
    "room_name": "거실",
    "species": {
      "korean_name": "몬스테라",
      "scientific_name": "Monstera deliciosa",
      "common_name": "Monstera"
    },
    "character": {
      "mood": "neutral",
      "expression": "normal",
      "status_message": "새 식물이 등록되었어요.",
      "reason_code": "onboarding_created"
    }
  }
}
```

### 규칙

```text
404 if plant does not exist.
404 or 403 if plant exists but user_id does not own it.
Do not expose other user's plant.
```

주의:

```text
full user isolation은 Ticket 25에서 formalize된다.
하지만 Ticket 2도 user_id 기반의 obvious cross-user leakage는 막아야 한다.
```

---

## 9. Service 계약

`app/services/plant_onboarding.py`를 생성한다.

책임:

```text
validate user exists
validate species exists
create plant
create initial character state
assemble plant card DTO
```

필수 동작:

```text
POST /plants request 수신
  -> user exists 확인
  -> species_profile exists 확인
  -> nickname validation
  -> transaction 시작
  -> plants row insert
  -> plant_characters initial row insert
  -> transaction commit
  -> plant card DTO 반환
```

금지:

```text
sensor aggregation
Rule Engine call
LLM call
RAG retrieval
vision inference
audit persistence beyond normal DB transaction
background job enqueue
```

---

## 10. Repository 계약

### SpeciesRepository

`app/repositories/species_repository.py`

책임:

```text
list candidate species from existing species_profiles
get species by id
```

금지:

```text
image classification
model inference
disease/pest/health lookup
```

### PlantRepository

`app/repositories/plant_repository.py`

책임:

```text
create plant
list plants by user
get plant by id and user
```

금지:

```text
cross-user plant read
sensor snapshot join
recommendation join
chat/RAG join
```

### CharacterRepository

`app/repositories/character_repository.py`

책임:

```text
create initial character state
get latest character state for plant
```

금지:

```text
CharacterStateEngine mapping
Rule Engine mapping
sensor-derived mood
LLM-generated mood
```

---

## 11. Initial Character State 계약

`POST /plants` 성공 시 `plant_characters` row를 정확히 1개 생성한다.

Initial character state:

```json
{
  "mood": "neutral",
  "expression": "normal",
  "status_message": "새 식물이 등록되었어요.",
  "reason_code": "onboarding_created"
}
```

규칙:

```text
plant insert와 initial character insert는 같은 transaction 안에서 수행한다.
plant insert 실패 시 character row가 남으면 안 된다.
character insert 실패 시 plant row가 남으면 안 된다.
initial state는 deterministic해야 한다.
```

금지:

```text
LLM-generated mood
sensor-derived mood
Rule Engine-derived mood
random expression
species-specific care recommendation
```

주의:

```text
character evolution은 Ticket 4 Character State Engine이 담당한다.
Ticket 2는 onboarding_created initial state만 생성한다.
```

---

## 12. Transaction 계약

`POST /plants`는 atomic해야 한다.

```text
create plant
  + create initial character state
  + return plant card
```

필수 invariant:

```text
if plant insert fails, no character row remains.
if character insert fails, no plant row remains.
if species does not exist, no plant row is inserted.
if user does not exist, no plant row is inserted.
```

---

## 13. Runtime 계약

허용 runtime topology:

```text
host
  -> backend container
      -> uvicorn app.main:app
      -> GET /healthz
      -> GET /readyz
      -> POST /plants/species-candidates
      -> POST /plants
      -> GET /plants
      -> GET /plants/{plant_id}
      -> SQLAlchemy DB access

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
```

Backend process invariant:

```text
exactly one foreground uvicorn process
no worker
no scheduler
no MQTT subscriber
no Redis consumer
no model loader
no LLM runtime
```

Network invariant:

```text
backend listens on 0.0.0.0:8000
host maps localhost:8000 -> backend:8000
postgres reachable from backend by DATABASE_URL
compose service name remains postgres
```

금지:

```text
backend binds to 127.0.0.1 only
alternate backend port
external gateway/Nginx
Redis/MQTT/vLLM network dependency
external API calls for onboarding
```

---

## 14. Health / Readiness 계약

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
check onboarding tables
check species data
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

Failure shape:

```json
{
  "status": "not_ready",
  "service": "sunshine-backend",
  "checks": {
    "database": "error"
  }
}
```

`/readyz`에서 금지:

```text
check species seed presence
check plant count
check image storage
check model availability
check RAG index
check Redis
check MQTT
check LLM
```

---

## 15. Data Access 계약

허용 DB operations:

```text
read users by id
read species_profiles
insert plants
insert plant_characters
read plants by user_id
read plant by plant_id + user_id
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

Ticket 1에서 해당 table이 이미 있어도 Ticket 2는 사용하면 안 된다.

---

## 16. Species Candidate Runtime 계약

`POST /plants/species-candidates`는 image inference가 아니다.

규칙:

```text
may accept image_ref
must not dereference image_ref
must not fetch remote image
must not open local file
must not run model inference
must not return diagnosis fields
```

허용:

```text
return first N species_profiles from DB
optionally filter by simple text if explicit species hint exists
return empty list if no candidates exist
```

---

## 17. Dependency 계약

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
openai
anthropic
vllm
pgvector
sentence-transformers
torch
torchvision
transformers
tensorflow
onnxruntime
openvino
opencv-python
Pillow
```

---

## 18. 테스트 요구사항

아래 테스트를 추가한다.

```text
tests/test_plant_onboarding_api.py
tests/test_plant_onboarding_service.py
tests/test_species_candidates_contract.py
tests/test_ticket2_boundary.py
```

### Species candidates tests

필수 케이스:

```text
POST /plants/species-candidates returns candidates list
candidate includes species_profile_id, korean_name, scientific_name, common_name, confidence_label
image_ref is treated as opaque string
no image file open
no URL fetch
no model inference
no disease/pest/health/diagnosis fields
empty species table returns empty list or DB-backed fallback only
```

### Plant onboarding service tests

필수 케이스:

```text
valid user + valid species + nickname creates plant
initial character row is created
plant and character are created atomically
unknown user_id returns 404
unknown species_profile_id returns 404
missing species_profile_id is rejected
missing nickname is rejected
empty nickname is rejected
room_name is optional
```

### Plant API tests

필수 케이스:

```text
POST /plants valid payload -> plant card response
POST /plants response includes species block
POST /plants response includes initial character block
GET /plants?user_id=<uuid> returns only user's plants
GET /plants/{plant_id}?user_id=<uuid> returns plant detail
GET /plants/{plant_id}?user_id=<other_user> returns 403 or 404
```

### Boundary tests

필수 확인:

```text
no app/mqtt/
no app/llm/
no app/rag/
no app/retrieval/
no app/vision/
no app/workers/
no app/rules/

no MQTT/Redis/LLM/RAG/Vision dependency
no chat endpoint
no sensor ingestion endpoint
no companion endpoint
no extra readiness endpoint

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

## 19. Functional Expectations

### Species candidates

Input:

```json
{
  "user_id": "00000000-0000-0000-0000-000000000101",
  "image_ref": "uploads/mock/monstera.jpg"
}
```

Expected:

```text
response includes candidates list
first candidate contains species_profile_id
no disease/pest/health/diagnosis fields
no image inference occurred
```

### Create plant

Input:

```json
{
  "user_id": "00000000-0000-0000-0000-000000000101",
  "species_profile_id": "00000000-0000-0000-0000-000000000201",
  "nickname": "초록이",
  "room_name": "거실"
}
```

Expected:

```text
plants row created
plant_characters initial row created
response includes plant_id, user_id, species_profile_id, nickname, room_name
response includes species block
response includes character block
```

Expected character:

```json
{
  "mood": "neutral",
  "expression": "normal",
  "status_message": "새 식물이 등록되었어요.",
  "reason_code": "onboarding_created"
}
```

### List plants

Expected:

```text
GET /plants?user_id=<uuid>
returns only that user's plants
includes species block
includes character block
does not include sensor_snapshot
does not include today_recommended_action
does not include chat/RAG data
```

### Get plant detail

Expected:

```text
GET /plants/{plant_id}?user_id=<uuid>
returns plant detail for owner
non-owner request returns 403 or 404
```

### Negative cases

```text
POST /plants without species_profile_id -> 422
POST /plants with unknown species_profile_id -> 404
POST /plants with unknown user_id -> 404
POST /plants with empty nickname -> 400 or 422
cross-user GET /plants/{plant_id} -> 403 or 404
```

---

## 20. 구현 금지 항목

이 티켓에서 아래 기능은 구현하지 않는다.

```text
disease diagnosis
pest diagnosis
health classification
real ML vision model
VisionPort
mock vision classifier
model loading
image byte parsing
POST /sensor-readings
MQTT broker
MQTT subscriber
snapshot aggregation
latest environment summary
24h/7d environment details
Rule Engine
watering recommendation
light/humidity/temperature recommendation
today's recommended action
care log
growth history
/chat
/chat/intent
LLMPort
PromptBuilder
EvidenceBuilder
RAG retriever
pgvector retrieval
companion plant recommendation
redis
mqtt
worker
nginx
vllm
multi-container additions beyond backend + postgres
```

---

## 21. 최종 완료 조건

Ticket 2는 아래가 모두 만족되면 완료다.

```text
POST /plants/species-candidates returns DB-backed species candidates.
species-candidates treats image_ref as opaque string.
POST /plants creates plant after confirmed species.
POST /plants requires valid user_id and species_profile_id.
POST /plants creates initial character state atomically.
GET /plants returns only user's plants.
GET /plants/{plant_id} blocks obvious cross-user leakage.
plant payload includes species block.
plant payload includes initial character block.
no disease/pest/health diagnosis fields leak into responses.
no VisionPort, mock classifier, real model, sensor, MQTT, Rule Engine, LLM, or RAG leaks into this ticket.
/healthz liveness remains unchanged.
/readyz remains DB-only.
```
