# TICKET-008 — Rule Engine Baseline

## 0. 목표

Sunshine 백엔드에 deterministic Rule Engine baseline을 구현한다.

이 티켓은 식물 관리 판단을 LLM이 아니라 명시적 rule로 계산하는 첫 단계다.

입력은 기존 데이터만 사용한다.

```text
species_profiles
latest environment_snapshot
recent care_logs
now
````

출력은 machine-readable rule result만 생성한다.

```text
care_status
primary_action
severity
reason_codes
evidence_facts
```

이 티켓은 사용자-facing API, 채팅 답변, RAG, LLM, 추천 랭킹을 구현하지 않는다.

---

## 1. 핵심 요구사항

### Ticket ID

```text
TICKET-008
```

### Name

```text
Rule Engine Baseline
```

### Goal

```text
Make baseline plant-care decisions deterministic using species profile, latest environment snapshot, and recent care logs.
```

### Core output

```text
RuleEngine
watering rule
light rule
humidity rule
temperature rule
RuleInput / RuleResult schemas
machine-readable evidence facts
severity
reason codes
one-shot rule command
```

---

## 2. Ticket 7과의 정합성

Ticket 7은 `sensor_readings`를 읽어서 `environment_snapshots`를 생성한다.

Ticket 8은 `environment_snapshots` 중 `latest` snapshot을 읽어서 rule 판단에 사용한다.

```text
Ticket 7:
  sensor_readings
    -> latest / 24h / 7d environment_snapshots

Ticket 8:
  species_profile + latest environment_snapshot + recent_care_logs
    -> deterministic RuleResult
```

Ticket 8에서 금지:

```text
environment_snapshots 생성
environment_snapshots 수정
sensor_readings insert
snapshot aggregation 재구현
```

Ticket 8에서 허용:

```text
latest environment_snapshot read
species_profile read
recent care_logs read
RuleResult 계산
```

---

## 3. 수정/생성 허용 파일

### 수정 가능한 기존 파일

```text
app/main.py
app/models/species_profile.py
app/models/environment_snapshot.py
app/models/care_log.py
app/repositories/__init__.py
app/repositories/snapshot_repository.py
app/repositories/plant_repository.py
app/core/config.py
pyproject.toml
.github/workflows/ci.yml
```

### 생성 가능한 새 파일

```text
app/rules/__init__.py
app/rules/types.py
app/rules/watering.py
app/rules/light.py
app/rules/humidity.py
app/rules/temperature.py
app/services/rule_engine.py
app/repositories/rule_input_repository.py
app/schemas/rule_engine.py
app/rules/run.py
tests/test_rule_engine_types.py
tests/test_watering_rule.py
tests/test_light_rule.py
tests/test_humidity_rule.py
tests/test_temperature_rule.py
tests/test_rule_engine_integration.py
tests/test_rule_engine_command.py
tests/test_ticket8_boundary.py
```

### 조건부 허용 migration

기본값은 rule result를 저장하지 않는 것이다.

```text
Preferred default:
  Do not persist rule results yet.
  Return rule output from command/service.
```

정말 rule result persistence가 필요할 때만 migration 추가 가능.

```text
alembic/versions/<ticket8_rule_result_table>.py
```

조건:

```text
table name: rule_results
machine-readable rule output only
no prompt
no RAG
no chat
no recommendation ranking
no llm_runs
```

---

## 4. 금지 파일/디렉터리

아래는 생성/수정하지 않는다.

```text
app/llm/
app/rag/
app/retrieval/
app/services/evidence_builder.py
app/services/prompt_builder.py
app/services/chat_orchestrator.py
app/services/home_card_service.py
app/services/environment_detail_service.py
app/services/growth_history_service.py
app/services/companion_recommendation.py
app/repositories/audit_repository.py
app/repositories/chunk_repository.py
app/api/chat.py
app/api/home.py
app/api/environment.py
app/api/companion.py
deploy/
```

이전 티켓에서 이미 존재할 수 있는 아래 경로는 유지 가능하다.

```text
app/mqtt/
app/vision/
app/snapshots/
app/services/sensor_ingest.py
app/services/snapshot_service.py
app/services/character_state_engine.py
```

단, Ticket 8에서는 import compatibility가 아닌 이상 위 경로들을 수정하지 않는다.

---

## 5. Rule Module 계약

아래 rule module을 생성한다.

```text
app/rules/watering.py
app/rules/light.py
app/rules/humidity.py
app/rules/temperature.py
```

각 module은 하나의 pure deterministic function을 제공한다.

```python
def evaluate(input: RuleInput) -> RuleResult:
    ...
```

규칙:

```text
DB access 금지
network access 금지
LLM 호출 금지
RAG 호출 금지
current time 직접 조회 금지
random 금지
input mutation 금지
```

`now`가 필요하면 반드시 `RuleInput.now`로 전달받는다.

---

## 6. RuleInput 계약

`app/rules/types.py` 또는 `app/schemas/rule_engine.py`에 RuleInput 타입/schema를 정의한다.

예시:

```json
{
  "plant_id": "00000000-0000-0000-0000-000000000803",
  "species_profile": {
    "species_profile_id": "00000000-0000-0000-0000-000000000802",
    "korean_name": "몬스테라",
    "water_min_pct": 35.0,
    "water_max_pct": 70.0,
    "light_min_lux": 500.0,
    "light_max_lux": 3000.0,
    "humidity_min_pct": 40.0,
    "humidity_max_pct": 70.0,
    "temperature_min_c": 18.0,
    "temperature_max_c": 30.0
  },
  "latest_snapshot": {
    "soil_moisture_avg_pct": 25.0,
    "light_avg_lux": 250.0,
    "humidity_avg_pct": 35.0,
    "temperature_avg_c": 22.0,
    "window": "latest",
    "window_end": "2026-05-04T12:00:00+09:00"
  },
  "recent_care_logs": [
    {
      "action_type": "watering",
      "acted_at": "2026-05-04T08:00:00+09:00"
    }
  ],
  "now": "2026-05-04T12:00:00+09:00"
}
```

필수 입력 source:

```text
species profile
latest environment snapshot
recent care logs
now
```

규칙:

```text
now는 timezone-aware datetime
latest_snapshot은 해당 plant의 latest environment snapshot
recent_care_logs는 read-only context
missing species threshold는 insufficient_data
missing latest_snapshot은 insufficient_data
fake value 생성 금지
zero fill 금지
```

---

## 7. RuleResult 계약

각 rule은 아래 shape를 반환한다.

```json
{
  "rule_id": "watering",
  "care_status": "needs_action",
  "primary_action": "water",
  "severity": "high",
  "reason_codes": ["soil_moisture_below_min"],
  "evidence_facts": [
    {
      "fact_id": "soil_moisture.current_vs_min",
      "metric": "soil_moisture_avg_pct",
      "operator": "<",
      "observed": 25.0,
      "threshold": 35.0,
      "source": "latest_snapshot"
    }
  ]
}
```

허용 enum:

```text
care_status:
  needs_action
  ok
  watch
  insufficient_data

primary_action:
  water
  no_watering
  increase_light
  stabilize_humidity
  adjust_temperature
  none

severity:
  none
  low
  medium
  high
```

규칙:

```text
evidence_facts는 machine-readable이어야 함
reason_codes는 finite known string만 허용
primary_action은 finite known string만 허용
severity는 finite known string만 허용
natural-language LLM answer 금지
prompt 금지
retrieved_chunks 금지
```

---

## 8. RuleEngine Aggregation 계약

`app/services/rule_engine.py`에 `RuleEngine`을 구현한다.

필수 동작:

```text
1. watering rule 실행
2. light rule 실행
3. humidity rule 실행
4. temperature rule 실행
5. rule results를 stable order로 aggregate
6. aggregate RuleEngine output 반환
```

출력 shape:

```json
{
  "plant_id": "00000000-0000-0000-0000-000000000803",
  "care_status": "needs_action",
  "primary_action": "water",
  "severity": "high",
  "reason_codes": ["soil_moisture_below_min", "light_below_min"],
  "rule_results": [],
  "evidence_facts": []
}
```

Aggregation 규칙:

```text
rule 실행 순서:
  1. watering
  2. light
  3. humidity
  4. temperature

reason_codes 결합 순서:
  1. watering
  2. light
  3. humidity
  4. temperature

aggregate severity:
  highest severity wins

primary_action priority:
  1. water
  2. increase_light
  3. stabilize_humidity
  4. adjust_temperature
  5. no_watering
  6. none

aggregate care_status:
  if any rule needs_action -> needs_action
  else if any rule watch -> watch
  else if all ok/no issue -> ok
  else if critical input missing -> insufficient_data
```

---

## 9. Watering Rule 계약

입력:

```text
species_profile.water_min_pct
species_profile.water_max_pct
latest_snapshot.soil_moisture_avg_pct
recent care logs where action_type = watering
now
```

동작:

```text
If soil_moisture_avg_pct < water_min_pct:
  care_status = needs_action
  primary_action = water
  severity = high if observed < water_min_pct - 10
  severity = medium otherwise
  reason_codes includes soil_moisture_below_min

If water_min_pct <= soil_moisture_avg_pct <= water_max_pct:
  care_status = ok
  primary_action = no_watering
  severity = none
  reason_codes includes soil_moisture_within_range

If soil_moisture_avg_pct > water_max_pct:
  care_status = watch
  primary_action = no_watering
  severity = medium
  reason_codes includes soil_moisture_above_max
```

Recent watering guard:

```text
If recent watering exists within last 6 hours:
  do not return primary_action = water
  if soil moisture is low, return care_status = watch
  reason_codes includes recently_watered
```

주의:

```text
care log API 구현 금지
watering 기록 생성 금지
character state update 금지
```

---

## 10. Light Rule 계약

입력:

```text
species_profile.light_min_lux
species_profile.light_max_lux
latest_snapshot.light_avg_lux
```

동작:

```text
If light_avg_lux < light_min_lux:
  care_status = needs_action
  primary_action = increase_light
  severity = medium
  reason_codes includes light_below_min

If light_min_lux <= light_avg_lux <= light_max_lux:
  care_status = ok
  primary_action = none
  severity = none
  reason_codes includes light_within_range

If light_avg_lux > light_max_lux:
  care_status = watch
  primary_action = none
  severity = low
  reason_codes includes light_above_max
```

---

## 11. Humidity Rule 계약

입력:

```text
species_profile.humidity_min_pct
species_profile.humidity_max_pct
latest_snapshot.humidity_avg_pct
```

동작:

```text
If humidity_avg_pct < humidity_min_pct:
  care_status = watch
  primary_action = stabilize_humidity
  severity = low or medium
  reason_codes includes humidity_below_min

If humidity_min_pct <= humidity_avg_pct <= humidity_max_pct:
  care_status = ok
  primary_action = none
  severity = none
  reason_codes includes humidity_within_range

If humidity_avg_pct > humidity_max_pct:
  care_status = watch
  primary_action = stabilize_humidity
  severity = low
  reason_codes includes humidity_above_max
```

권장:

```text
humidity below min severity:
  medium if observed < humidity_min_pct - 10
  low otherwise
```

---

## 12. Temperature Rule 계약

입력:

```text
species_profile.temperature_min_c
species_profile.temperature_max_c
latest_snapshot.temperature_avg_c
```

동작:

```text
If temperature_avg_c < temperature_min_c:
  care_status = watch
  primary_action = adjust_temperature
  severity = medium
  reason_codes includes temperature_below_min

If temperature_min_c <= temperature_avg_c <= temperature_max_c:
  care_status = ok
  primary_action = none
  severity = none
  reason_codes includes temperature_within_range

If temperature_avg_c > temperature_max_c:
  care_status = watch
  primary_action = adjust_temperature
  severity = medium
  reason_codes includes temperature_above_max
```

---

## 13. RuleInputRepository 계약

`app/repositories/rule_input_repository.py`를 생성한다.

필수 responsibility:

```text
plant_id 기준 plant 조회
species_profile 조회
latest environment_snapshot 조회
recent care_logs 조회
RuleInput 구성
```

필수 operation 예시:

```text
load_rule_input(plant_id, now) -> RuleInput
```

읽기 허용:

```text
plants
species_profiles
environment_snapshots
care_logs
```

쓰기 금지:

```text
sensor_readings
environment_snapshots
plant_characters
chat_requests
llm_runs
recommendation_evidence
retrieved_chunks
```

Missing data 처리:

```text
missing plant -> runtime/validation error or explicit not found
missing species threshold -> insufficient_data
missing latest_snapshot -> insufficient_data
missing care_logs -> empty list
```

---

## 14. One-shot Command 계약

`app/rules/run.py`를 생성한다.

명령:

```bash
python -m app.rules.run
```

지원 인자:

```text
--plant-id <uuid>
--now <ISO-8601 datetime>
```

예시:

```bash
python -m app.rules.run \
  --plant-id 00000000-0000-0000-0000-000000000803 \
  --now 2026-05-04T12:00:00+09:00
```

필수 동작:

```text
DB에서 RuleInput load
RuleEngine 1회 실행
RuleEngine output을 stdout JSON으로 출력
성공 시 exit 0
invalid args/runtime failure 시 non-zero exit
```

금지:

```text
infinite loop
scheduler
worker process
Redis queue
LLM call
RAG retrieval
prompt generation
natural-language answer generation
```

---

## 15. Optional Internal API 계약

필요할 때만 아래 endpoint를 구현할 수 있다.

```http
POST /internal/rules/run
```

Request:

```json
{
  "plant_id": "00000000-0000-0000-0000-000000000803",
  "now": "2026-05-04T12:00:00+09:00"
}
```

Response:

```text
RuleEngine output과 동일
```

금지 public/user-facing API:

```text
GET /home
GET /plants/{plant_id}/card
GET /plants/{plant_id}/environment
GET /plants/{plant_id}/history
POST /plants/{plant_id}/chat
POST /chat
POST /chat/intent
GET /plants/{plant_id}/companion-recommendations
```

---

## 16. Runtime 계약

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

  -> one-shot rule command
      docker compose run --rm backend python -m app.rules.run
```

Ticket 6이 이미 존재하는 branch에서는 아래 container가 있어도 된다.

```text
mqtt
mqtt-ingest
```

Ticket 8에서 새로 추가하면 안 되는 long-lived container:

```text
rule-worker
redis
nginx
vllm
model-server
generic-worker
```

Backend process invariant:

```text
exactly one foreground uvicorn process
no Rule Engine scheduler inside backend
no background care-decision loop inside backend
```

Rule command invariant:

```text
one-shot process
python -m app.rules.run
evaluation 이후 종료
```

---

## 17. Health / Readiness 계약

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
run Rule Engine
check latest snapshot
check care logs
check LLM/RAG
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
run Rule Engine
require recent snapshot
require care logs
check LLM/RAG
add "rule_engine": "ok"
```

Rule correctness는 `/readyz`가 아니라 Ticket 8 functional tests/gates에서 검증한다.

---

## 18. Determinism 계약

같은 `RuleInput`이면 같은 `RuleEngine` output이 나와야 한다.

금지:

```text
random severity
now가 제공됐는데 current time 직접 조회
LLM-generated explanation
RAG retrieval
mutable global thresholds
environment-dependent rule behavior
```

---

## 19. LLM Override 금지 계약

Rule Engine이 baseline care decision의 source of truth다.

나중에 LLM이 붙더라도 아래 값을 override하면 안 된다.

```text
care_status
primary_action
severity
reason_codes
evidence_facts
```

Ticket 8에서는 아래가 전부 금지다.

```text
LLM dependency
prompt generation
RAG retrieval
natural-language final answer
chat answer generation
```

---

## 20. Dependency 계약

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

## 21. 테스트 요구사항

아래 테스트를 추가한다.

```text
tests/test_rule_engine_types.py
tests/test_watering_rule.py
tests/test_light_rule.py
tests/test_humidity_rule.py
tests/test_temperature_rule.py
tests/test_rule_engine_integration.py
tests/test_rule_engine_command.py
tests/test_ticket8_boundary.py
```

### Rule type tests

필수 확인:

```text
care_status enum 제한
primary_action enum 제한
severity enum 제한
reason_codes finite known strings
evidence_facts machine-readable
no natural-language final answer field
```

### Watering rule tests

필수 케이스:

```text
soil_moisture_avg_pct < water_min_pct -> needs_action / water
soil_moisture_avg_pct very low -> severity high
soil_moisture within range -> ok / no_watering
soil_moisture > water_max_pct -> watch / no_watering
recent watering within 6h suppresses water action
missing water threshold -> insufficient_data
missing soil_moisture -> insufficient_data
```

### Light rule tests

필수 케이스:

```text
light_avg_lux < light_min_lux -> needs_action / increase_light
light within range -> ok / none
light_avg_lux > light_max_lux -> watch / none
missing light threshold -> insufficient_data
missing light metric -> insufficient_data
```

### Humidity rule tests

필수 케이스:

```text
humidity_avg_pct < humidity_min_pct -> watch / stabilize_humidity
humidity within range -> ok / none
humidity_avg_pct > humidity_max_pct -> watch / stabilize_humidity
missing humidity threshold -> insufficient_data
missing humidity metric -> insufficient_data
```

### Temperature rule tests

필수 케이스:

```text
temperature_avg_c < temperature_min_c -> watch / adjust_temperature
temperature within range -> ok / none
temperature_avg_c > temperature_max_c -> watch / adjust_temperature
missing temperature threshold -> insufficient_data
missing temperature metric -> insufficient_data
```

### RuleEngine integration tests

필수 케이스:

```text
runs all four rules
combines reason_codes in stable order
highest severity wins
primary_action priority is respected
any needs_action -> aggregate needs_action
any watch and no needs_action -> aggregate watch
all ok -> aggregate ok
missing latest_snapshot -> insufficient_data
same RuleInput -> same output
```

### Command tests

필수 케이스:

```text
python -m app.rules.run --plant-id <uuid> --now <aware-datetime> exits 0
stdout is valid JSON
output includes care_status, primary_action, severity, reason_codes, rule_results, evidence_facts
invalid --now exits non-zero
missing latest_snapshot returns insufficient_data, not crash
```

### Boundary tests

필수 확인:

```text
no app/llm/
no app/rag/
no app/retrieval/

no OpenAI/Anthropic/vLLM/RAG/vector dependency
no Redis dependency
no scheduler dependency

no Home Card API
no Environment Detail API
no Growth History API
no Chat API
no Companion API

no EvidenceBuilder
no PromptBuilder
no ChatOrchestrator

no writes to:
  plant_characters
  sensor_readings
  environment_snapshots
  chat_requests
  llm_runs
  recommendation_evidence
  retrieved_chunks
```

---

## 22. Functional Expectations

### Low soil moisture

Input:

```text
water_min_pct = 35
soil_moisture_avg_pct = 25
recent watering = none
```

Expected:

```text
watering rule:
  care_status = needs_action
  primary_action = water
  severity = medium or high
  reason_codes includes soil_moisture_below_min
  evidence_facts includes observed 25 < threshold 35

aggregate:
  care_status = needs_action
  primary_action = water
```

### Adequate soil moisture

Input:

```text
water_min_pct = 35
water_max_pct = 70
soil_moisture_avg_pct = 45
```

Expected:

```text
watering rule:
  care_status = ok
  primary_action = no_watering
  severity = none
  reason_codes includes soil_moisture_within_range
```

### Low light

Input:

```text
light_min_lux = 500
light_avg_lux = 250
```

Expected:

```text
light rule:
  care_status = needs_action
  primary_action = increase_light
  severity = medium
  reason_codes includes light_below_min
```

### Recent watering guard

Input:

```text
soil_moisture_avg_pct = 25
water_min_pct = 35
recent watering within last 6h = true
```

Expected:

```text
watering rule:
  primary_action != water
  care_status = watch
  reason_codes includes recently_watered
```

### Missing latest snapshot

Input:

```text
latest_snapshot = missing
```

Expected:

```text
care_status = insufficient_data
reason_codes includes missing_latest_snapshot
evidence_facts explains missing latest_snapshot
no crash
no fake values
```

---

## 23. 구현 금지 항목

이 티켓에서 아래 기능은 구현하지 않는다.

```text
LLM decision-making
LLM explanation
RAG retrieval
disease diagnosis
pest diagnosis
full recommendation ranking
chat answer generation
Home Plant Card API
Plant Environment Detail API
Growth History API
Care Log API
companion recommendation
push notification
realtime stream
SSE
websocket
Redis queue
scheduler
rule-worker daemon
EvidenceBuilder
PromptBuilder
ChatOrchestrator
natural-language final answer
```

---

## 24. 최종 완료 조건

Ticket 8은 아래가 모두 만족되면 완료다.

```text
RuleInput schema exists.
RuleResult schema exists.
watering/light/humidity/temperature rule modules exist.
RuleEngine exists.
RuleInputRepository exists.
python -m app.rules.run works as one-shot command.
low soil moisture produces water action.
adequate soil produces no_watering.
low light produces increase_light.
recent watering suppresses immediate water action.
missing latest snapshot returns insufficient_data.
outputs include machine-readable evidence_facts.
same RuleInput produces same output.
no prompt, LLM, RAG, retrieved_chunks, or final answer text leaks into output.
no Home Card, Environment Detail, Growth History, Chat, EvidenceBuilder, PromptBuilder, LLMPort, RAG, companion recommendation, Redis, vLLM, or scheduler leaks into this ticket.
/healthz liveness remains unchanged.
/readyz remains DB-only.
```