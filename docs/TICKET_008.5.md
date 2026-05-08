# TICKET-008.5 — Rule Result to Character State Mapper

## 0. 목표

Ticket 8의 `RuleEngine` 결과를 Ticket 4의 `CharacterStateEngine`이 이해할 수 있는 단일 character condition으로 변환하는 bridge layer를 구현한다.

이 티켓은 care decision을 새로 계산하지 않는다.  
이 티켓은 character state mapping을 새로 만들지 않는다.  
이 티켓은 `RuleEngine output -> CharacterStateEngine input` 변환만 담당한다.

---

## 1. 핵심 역할

### Ticket ID

```text
TICKET-008.5
````

### Name

```text
Rule Result to Character State Mapper
```

### Goal

```text
Map deterministic RuleEngine output into a bounded CharacterStateEngine condition and optionally persist the resulting character state through the existing CharacterStateEngine/CharacterRepository path.
```

### Core output

```text
RuleToCharacterConditionMapper
RuleCharacterSyncService
RuleResult -> character condition mapping
optional one-shot sync command
optional internal sync endpoint
append-only plant_characters update through Ticket 4 path
```

---

## 2. 왜 필요한가

Ticket 8의 RuleEngine output은 복잡하다.

```json
{
  "care_status": "needs_action",
  "primary_action": "water",
  "severity": "high",
  "reason_codes": [
    "soil_moisture_below_min",
    "light_below_min"
  ],
  "evidence_facts": []
}
```

하지만 Ticket 4의 `CharacterStateEngine`은 아래처럼 단일 condition을 받는다.

```text
good
low_soil_moisture
low_light
unstable_humidity
after_watering
onboarding_created
```

따라서 중간에서 아래 변환이 필요하다.

```text
RuleEngine output
  -> RuleToCharacterConditionMapper
  -> character condition
  -> CharacterStateEngine
  -> plant_characters append-only row
```

---

## 3. 주변 티켓과의 정합성

### Ticket 4와의 관계

Ticket 4는 이미 정해진 condition을 받아 deterministic character state를 만든다.

```text
condition = low_soil_moisture
  -> mood = thirsty
  -> expression = droop
  -> primary_action = water
  -> reason_code = low_soil_moisture
```

Ticket 8.5는 Ticket 4의 mapping을 재구현하지 않는다.

허용:

```text
CharacterStateEngine 호출
CharacterRepository를 통한 append-only character history 저장
```

금지:

```text
CharacterStateEngine mapping 복사/중복 구현
free-form mood/expression/status_message 생성
LLM-generated character message
```

### Ticket 8과의 관계

Ticket 8은 RuleEngine baseline care decision을 만든다.

```text
species_profile + latest_snapshot + recent_care_logs
  -> RuleEngine
  -> care_status / primary_action / severity / reason_codes / evidence_facts
```

Ticket 8.5는 RuleEngine 판단을 새로 하지 않는다.

허용:

```text
RuleEngine output 읽기
RuleEngine output을 character condition으로 압축
```

금지:

```text
watering/light/humidity/temperature rule 재계산
species threshold 직접 비교
environment_snapshot 직접 해석
care_status / severity / primary_action override
```

---

## 4. 입력 계약

Mapper 입력은 Ticket 8의 aggregate RuleEngine output이다.

예시:

```json
{
  "plant_id": "00000000-0000-0000-0000-000000000803",
  "care_status": "needs_action",
  "primary_action": "water",
  "severity": "high",
  "reason_codes": [
    "soil_moisture_below_min",
    "light_below_min"
  ],
  "rule_results": [],
  "evidence_facts": []
}
```

필수 입력 field:

```text
plant_id
care_status
primary_action
severity
reason_codes
```

읽기 가능 field:

```text
rule_results
evidence_facts
```

주의:

```text
evidence_facts는 디버깅/검증 근거로만 사용한다.
evidence_facts를 기반으로 새 care decision을 계산하지 않는다.
```

---

## 5. 출력 계약

Mapper 출력은 Ticket 4가 허용하는 character condition 하나여야 한다.

허용 output:

```text
good
low_soil_moisture
low_light
unstable_humidity
```

특수 condition은 mapper가 직접 만들지 않는다.

```text
after_watering:
  Ticket 11 care action logging flow에서 사용

onboarding_created:
  Ticket 2 onboarding flow에서 사용
```

Mapper result shape:

```json
{
  "plant_id": "00000000-0000-0000-0000-000000000803",
  "condition": "low_soil_moisture",
  "source": "rule_engine",
  "rule_primary_action": "water",
  "rule_care_status": "needs_action",
  "rule_severity": "high",
  "matched_reason_code": "soil_moisture_below_min"
}
```

---

## 6. Mapping 규칙

`app/services/rule_to_character_mapper.py`에 mapper를 구현한다.

필수 class/function shape:

```python
class RuleToCharacterConditionMapper:
    def map_rule_result(
        self,
        rule_result: RuleEngineResult,
    ) -> CharacterConditionMapping:
        ...
```

### 우선순위

RuleEngine의 aggregate `primary_action`과 `reason_codes`를 사용해 단일 condition을 고른다.

우선순위는 아래로 고정한다.

```text
1. water / soil_moisture_below_min
   -> low_soil_moisture

2. increase_light / light_below_min
   -> low_light

3. stabilize_humidity / humidity_below_min / humidity_above_max
   -> unstable_humidity

4. adjust_temperature / temperature_below_min / temperature_above_max
   -> unstable_humidity

5. ok / no_watering / none
   -> good

6. watch without specific supported reason
   -> good
```

### 구체 규칙

```text
If primary_action == water:
  condition = low_soil_moisture

Else if reason_codes contains soil_moisture_below_min:
  condition = low_soil_moisture

Else if primary_action == increase_light:
  condition = low_light

Else if reason_codes contains light_below_min:
  condition = low_light

Else if primary_action == stabilize_humidity:
  condition = unstable_humidity

Else if reason_codes contains humidity_below_min or humidity_above_max:
  condition = unstable_humidity

Else if primary_action == adjust_temperature:
  condition = unstable_humidity

Else if reason_codes contains temperature_below_min or temperature_above_max:
  condition = unstable_humidity

Else if care_status == ok:
  condition = good

Else if care_status == watch and no supported specific reason exists:
  condition = good

Else if care_status == insufficient_data:
  condition = good

Else:
  condition = good
```

주의:

```text
Ticket 4에 temperature-specific character condition이 없으므로 temperature issue는 unstable_humidity와 같은 stressed/sweat 계열로 임시 압축한다.
새 condition을 추가하지 않는다.
```

---

## 7. Character Sync Service 계약

`app/services/rule_character_sync.py`를 생성한다.

필수 class shape:

```python
class RuleCharacterSyncService:
    async def sync_from_rule_result(
        self,
        *,
        rule_result: RuleEngineResult,
        observed_at: datetime | None = None,
    ) -> CharacterSyncResult:
        ...
```

필수 동작:

```text
1. RuleToCharacterConditionMapper로 rule_result를 condition으로 변환한다.
2. CharacterStateEngine에 condition을 전달한다.
3. CharacterRepository를 통해 plant_characters row를 append-only로 저장한다.
4. 생성된 character state와 mapping metadata를 반환한다.
```

금지:

```text
RuleEngine 재실행
environment_snapshots 직접 조회
species_profiles 직접 조회
care_logs 직접 조회
sensor_readings 직접 조회
LLM/RAG 호출
status_message 직접 생성
mood/expression 직접 생성
기존 plant_characters row overwrite
```

---

## 8. 저장 계약

이 티켓은 새 table을 만들지 않는다.

허용 write:

```text
plant_characters append-only insert
```

금지 write:

```text
rule_results
sensor_readings
environment_snapshots
care_logs
chat_requests
llm_runs
recommendation_evidence
retrieved_chunks
```

저장 규칙:

```text
- CharacterStateEngine output을 그대로 저장한다.
- 기존 character row를 수정하지 않는다.
- 같은 rule_result를 여러 번 sync하면 append row가 생길 수 있다.
- dedup/idempotency는 이 티켓의 기본 범위가 아니다.
```

선택적으로 중복 방지가 필요하면 후속 티켓으로 분리한다.

```text
TICKET-0XX — Character State Sync Idempotency
```

---

## 9. Allowed Files

### 수정 가능한 기존 파일

```text
app/services/character_state_engine.py
app/repositories/character_repository.py
app/services/rule_engine.py
app/schemas/rule_engine.py
app/schemas/character_state.py
app/main.py
pyproject.toml
.github/workflows/ci.yml
```

### 생성 가능한 새 파일

```text
app/services/rule_to_character_mapper.py
app/services/rule_character_sync.py
app/schemas/rule_character_sync.py
app/rules/character_sync.py
tests/test_rule_to_character_mapper.py
tests/test_rule_character_sync_service.py
tests/test_ticket8_5_boundary.py
```

### 조건부 허용

내부 수동 실행 API가 필요한 경우에만 허용한다.

```text
app/api/rule_character_sync.py
```

허용 endpoint:

```http
POST /internal/rules/character-sync
```

---

## 10. Forbidden Files / Directories

아래는 생성/수정하지 않는다.

```text
app/llm/
app/rag/
app/retrieval/
app/services/prompt_builder.py
app/services/evidence_builder.py
app/services/chat_orchestrator.py
app/services/home_card_service.py
app/services/environment_detail_service.py
app/services/growth_history_service.py
app/api/chat.py
app/api/home.py
app/api/environment.py
app/api/companion.py
app/mqtt/
app/workers/
deploy/
```

---

## 11. Optional Internal API 계약

필요할 때만 구현한다.

```http
POST /internal/rules/character-sync
```

Request:

```json
{
  "rule_result": {
    "plant_id": "00000000-0000-0000-0000-000000000803",
    "care_status": "needs_action",
    "primary_action": "water",
    "severity": "high",
    "reason_codes": [
      "soil_moisture_below_min"
    ],
    "rule_results": [],
    "evidence_facts": []
  },
  "observed_at": "2026-05-04T12:00:00+09:00"
}
```

Response:

```json
{
  "plant_id": "00000000-0000-0000-0000-000000000803",
  "condition": "low_soil_moisture",
  "character": {
    "mood": "thirsty",
    "expression": "droop",
    "status_message": "목이 말라 보여요.",
    "primary_action": "water",
    "reason_code": "low_soil_moisture"
  },
  "source": "rule_engine",
  "matched_reason_code": "soil_moisture_below_min"
}
```

금지 public/user-facing API:

```text
GET /home
GET /plants/{plant_id}/card
GET /plants/{plant_id}/environment
GET /plants/{plant_id}/history
POST /chat
POST /chat/intent
```

---

## 12. One-shot Command 계약

필요할 때만 구현한다.

```bash
python -m app.rules.character_sync
```

지원 인자:

```text
--plant-id <uuid>
--now <ISO-8601 datetime>
```

필수 동작:

```text
1. 기존 RuleInputRepository / RuleEngine을 사용해 RuleEngine output을 얻는다.
2. RuleCharacterSyncService로 character state를 append한다.
3. stdout에 JSON 결과를 출력한다.
4. 성공 시 exit 0.
5. invalid input/runtime failure 시 non-zero exit.
```

주의:

```text
이 command는 one-shot이다.
scheduler/worker/daemon이 아니다.
```

금지:

```text
infinite loop
cron-like behavior
background worker
Redis queue
MQTT subscription
LLM/RAG call
```

---

## 13. Runtime 계약

허용 runtime topology:

```text
host
  -> backend container
      -> uvicorn app.main:app
      -> existing APIs
      -> optional POST /internal/rules/character-sync

  -> postgres container
      -> PostgreSQL

  -> optional one-shot command
      docker compose run --rm backend python -m app.rules.character_sync
```

금지 long-lived container:

```text
rule-character-worker
character-sync-worker
redis
nginx
vllm
model-server
generic-worker
```

Backend process invariant:

```text
exactly one foreground uvicorn process
no background rule-character sync loop
no scheduler inside backend
no Redis consumer
no LLM runtime
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
check RuleCharacterSyncService
check CharacterStateEngine
check RuleEngine
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
run RuleEngine
run CharacterStateEngine
check latest character sync
add "rule_character_sync": "ok"
add "character_state": "ok"
add "rule_engine": "ok"
```

---

## 15. Dependency 계약

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
paho-mqtt
```

---

## 16. 테스트 요구사항

아래 테스트를 추가한다.

```text
tests/test_rule_to_character_mapper.py
tests/test_rule_character_sync_service.py
tests/test_ticket8_5_boundary.py
```

### Mapper tests

필수 케이스:

```text
primary_action = water -> low_soil_moisture
reason_codes contains soil_moisture_below_min -> low_soil_moisture

primary_action = increase_light -> low_light
reason_codes contains light_below_min -> low_light

primary_action = stabilize_humidity -> unstable_humidity
reason_codes contains humidity_below_min -> unstable_humidity
reason_codes contains humidity_above_max -> unstable_humidity

primary_action = adjust_temperature -> unstable_humidity
reason_codes contains temperature_below_min -> unstable_humidity
reason_codes contains temperature_above_max -> unstable_humidity

care_status = ok -> good
care_status = watch with unknown reason -> good
care_status = insufficient_data -> good

multiple reasons:
  water/soil issue wins over light issue
  light issue wins over humidity issue
  humidity issue wins over temperature issue
```

### Sync service tests

필수 케이스:

```text
valid rule_result with water maps to low_soil_moisture and appends thirsty character row
valid rule_result with low light maps to low_light and appends sleepy character row
valid rule_result with humidity issue maps to unstable_humidity and appends stressed character row
valid rule_result with ok maps to good and appends happy character row

sync calls CharacterStateEngine
sync does not duplicate CharacterStateEngine mapping logic
sync appends plant_characters row
sync does not overwrite previous character row
sync returns character state and mapping metadata
```

### Boundary tests

필수 확인:

```text
no app/llm/
no app/rag/
no app/retrieval/
no worker/daemon
no scheduler dependency
no Redis dependency
no LLM/RAG/vLLM/OpenAI/Anthropic dependency

no Home Card API
no Environment Detail API
no Growth History API
no Chat API
no Companion API

RuleToCharacterConditionMapper does not query DB
RuleToCharacterConditionMapper does not call RuleEngine
RuleToCharacterConditionMapper does not call CharacterRepository

RuleCharacterSyncService does not:
  read sensor_readings
  read environment_snapshots directly
  read species_profiles directly
  read care_logs directly
  call LLM/RAG
  generate free-form status message
  mutate old plant_characters row
```

---

## 17. Functional Expectations

### Low soil moisture

Input:

```json
{
  "care_status": "needs_action",
  "primary_action": "water",
  "severity": "high",
  "reason_codes": ["soil_moisture_below_min"]
}
```

Expected mapper output:

```text
condition = low_soil_moisture
matched_reason_code = soil_moisture_below_min
```

Expected character output through Ticket 4:

```json
{
  "mood": "thirsty",
  "expression": "droop",
  "status_message": "목이 말라 보여요.",
  "primary_action": "water",
  "reason_code": "low_soil_moisture"
}
```

### Low light

Input:

```json
{
  "care_status": "needs_action",
  "primary_action": "increase_light",
  "severity": "medium",
  "reason_codes": ["light_below_min"]
}
```

Expected mapper output:

```text
condition = low_light
```

Expected character output:

```json
{
  "mood": "sleepy",
  "expression": "normal",
  "status_message": "빛이 조금 부족해 보여요.",
  "primary_action": "move_to_brighter_place",
  "reason_code": "low_light"
}
```

### Humidity / temperature instability

Input:

```json
{
  "care_status": "watch",
  "primary_action": "adjust_temperature",
  "severity": "medium",
  "reason_codes": ["temperature_above_max"]
}
```

Expected mapper output:

```text
condition = unstable_humidity
```

Expected character output:

```json
{
  "mood": "stressed",
  "expression": "sweat",
  "status_message": "습도 변화가 커서 스트레스를 받은 것 같아요.",
  "primary_action": "stabilize_humidity",
  "reason_code": "unstable_humidity"
}
```

Note:

```text
Ticket 4에 temperature-specific condition이 없으므로 temperature issue는 unstable_humidity/stressed 표현으로 압축한다.
```

### Good state

Input:

```json
{
  "care_status": "ok",
  "primary_action": "none",
  "severity": "none",
  "reason_codes": []
}
```

Expected mapper output:

```text
condition = good
```

Expected character output:

```json
{
  "mood": "happy",
  "expression": "smile",
  "status_message": "상태가 좋아 보여요.",
  "primary_action": "none",
  "reason_code": "good"
}
```

---

## 18. 구현 금지 항목

이 티켓에서 아래 기능은 구현하지 않는다.

```text
new Rule Engine logic
watering/light/humidity/temperature threshold comparison
species_profile threshold parsing
environment snapshot aggregation
sensor ingestion
MQTT ingestion
care log API
after_watering trigger
Home Card API
Plant Environment Detail API
Growth History API
Chat API
LLM explanation
RAG retrieval
PromptBuilder
EvidenceBuilder
recommendation ranking
push notification
realtime stream
SSE
websocket
Redis queue
scheduler
worker daemon
new character mood/expression templates
free-form character state
```

---

## 19. 최종 완료 조건

Ticket 8.5는 아래가 모두 만족되면 완료다.

```text
RuleToCharacterConditionMapper exists.
RuleCharacterSyncService exists.
RuleEngine output maps to exactly one Ticket 4 character condition.
water / soil_moisture_below_min maps to low_soil_moisture.
increase_light / light_below_min maps to low_light.
humidity issue maps to unstable_humidity.
temperature issue maps to unstable_humidity.
ok maps to good.
sync path calls CharacterStateEngine instead of duplicating character mapping.
sync path appends plant_characters history row.
old character state is not overwritten.
no Rule Engine logic is recalculated.
no snapshot/sensor/care-log data is directly read.
no Home Card, Chat, LLM, RAG, PromptBuilder, EvidenceBuilder, Redis, scheduler, or worker leaks into this ticket.
/healthz liveness remains unchanged.
/readyz remains DB-only.
```