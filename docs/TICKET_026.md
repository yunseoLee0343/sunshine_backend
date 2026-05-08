# TICKET-026 — API Response Schemas + Frontend Contract

## 0. 목표

Sunshine MVP의 기존 백엔드 응답을 프론트엔드가 안정적으로 사용할 수 있도록 명시적 response schema, OpenAPI example, schema drift test로 고정한다.

이 티켓은 프론트엔드를 만들지 않는다.  
이 티켓은 새 API 기능을 만들지 않는다.  
이 티켓은 비즈니스 로직을 바꾸지 않는다.

Ticket 26의 책임은 아래까지만이다.

```text
existing MVP endpoint responses
  -> explicit Pydantic response models
  -> OpenAPI examples
  -> frontend-facing contract documentation
  -> schema drift tests
```

---

## 1. Ticket Identity

### Ticket ID

```text
TICKET-026
```

### Name

```text
API Response Schemas + Frontend Contract
```

### Goal

```text
Stabilize backend response schemas for frontend/mobile implementation.
```

### Core output

```text
response schema models
OpenAPI examples
schema contract tests
frontend API contract document
route response_model bindings
forbidden-field drift checks
```

### Strict non-goal

```text
no frontend implementation
no mobile app
no new endpoint behavior
no business logic change
no service/domain rewrite
no DB migration
no SDK generation pipeline
no browser automation
no production auth redesign
no real LLM provider
no streaming
no marketplace/purchase fields
```

---

## 2. 주변 티켓과의 연결

Ticket 26은 MVP API를 frontend가 사용할 수 있는 안정된 계약으로 고정하는 티켓이다.

```text
Ticket 2/3:
  plant onboarding and species candidate outputs

Ticket 9/10:
  home card and environment detail outputs

Ticket 11/12:
  care log and growth history outputs

Ticket 18/21:
  chat answer and companion recommendation outputs

Ticket 25:
  user-scoped API behavior must remain preserved

Ticket 26:
  existing outputs -> explicit schemas + OpenAPI examples + drift tests

Ticket 27+:
  frontend/mobile implementation consumes these contracts
```

Ticket 26의 역할:

```text
existing API route
  + existing service result
  -> stable response_model
  -> documented OpenAPI example
  -> schema drift test
```

금지:

```text
new endpoint creation
new orchestration
new service behavior
new retrieval behavior
new LLM behavior
frontend screen implementation
schema generation service
SDK pipeline
```

---

## 3. 수정/생성 허용 파일

### 생성 가능한 새 파일

```text
app/schemas/__init__.py
app/schemas/common.py
app/schemas/plants.py
app/schemas/home.py
app/schemas/environment.py
app/schemas/care_logs.py
app/schemas/chat.py
app/schemas/companion.py
app/schemas/history.py
app/schemas/openapi_examples.py

tests/test_api_response_schemas.py
tests/test_openapi_examples.py
tests/test_schema_contract_snapshots.py
tests/fixtures/schema_contract_fixtures.py

docs/frontend_api_contract.md
```

### 수정 가능한 기존 API 파일

```text
app/api/plants.py
app/api/home.py
app/api/environment.py
app/api/care_logs.py
app/api/chat.py
app/api/companion.py
app/api/history.py
```

수정은 아래로만 제한한다.

```text
- response_model 연결
- 기존 응답을 명시된 schema shape로 serialize
- OpenAPI example metadata 추가
- 기존 path/status code/user scoping 유지
```

### 조건부 수정 가능

```text
app/main.py
pyproject.toml
```

`app/main.py` 허용 범위:

```text
- OpenAPI title/version/tags 정리
- 기존 router registration 보존
- /healthz 변경 금지
- /readyz 추가 금지
- startup dependency check 추가 금지
```

`pyproject.toml` 허용 범위:

```text
- schema/snapshot test marker 추가
- runtime dependency 추가 금지
```

---

## 4. 금지 파일/디렉터리

아래 경로는 생성하거나 수정하지 않는다.

```text
frontend/
web/
mobile/

app/services/
app/domain/
app/repositories/
app/llm/
app/vision/
app/mqtt/
app/workers/

alembic/
migrations/
Dockerfile
docker-compose.yml
.env.example
.github/workflows/
```

금지 구현:

```text
React / React Native UI
frontend shell
browser test
SDK generator
new service logic
new domain model behavior
new DB table
migration
real LLM provider
streaming
marketplace / purchase / affiliate fields
```

---

## 5. Schema Family 계약

Ticket 26은 아래 frontend-facing response family를 명시적 schema로 고정한다.

```text
1. Species Candidate Response
2. Plant Created Response
3. Home Plant Card Response
4. Environment Detail Response
5. Care Log Feedback Response
6. Chat Answer Response
7. Companion Recommendation Response
8. Growth History Response
9. Common Error / Evidence / Fixed Answer Sections
```

---

## 6. Common Schema 계약

생성 파일:

```text
app/schemas/common.py
```

필수 개념:

```python
class ErrorResponse(BaseModel):
    error: str
    message: str

class EvidenceRef(BaseModel):
    kind: str
    ref_id: str
    summary: str | None = None

class FixedAnswerSections(BaseModel):
    conclusion: str = Field(alias="결론")
    evidence: str = Field(alias="근거")
    action: str = Field(alias="행동")
    caution: str = Field(alias="주의")
```

규칙:

```text
IDs are strings.
Timestamps are ISO 8601 strings.
Nullable fields are explicit.
Public field names are stable.
answer.sections must expose exactly Korean keys: 결론 / 근거 / 행동 / 주의.
/healthz response must not gain schema decorations or unstable timestamp fields.
```

---

## 7. Endpoint Response 계약

### 7.1 Species Candidate Response

필수 shape:

```json
{
  "request_id": "req-species-001",
  "image_ref": "image-demo-001",
  "candidates": [
    {
      "species_id": "species-monstera",
      "common_name_ko": "몬스테라",
      "common_name_en": "Monstera",
      "confidence_label": "high"
    }
  ],
  "fallback": null
}
```

금지 field:

```text
disease diagnosis
pest diagnosis
health diagnosis
treatment
pesticide
```

### 7.2 Plant Created Response

필수 field:

```text
plant_id
user_id
nickname
species_id
species_name
room
character.mood
character.expression
character.status_message
character.primary_action
character.reason_code
```

### 7.3 Home Plant Card Response

필수 field:

```text
plant_id
nickname
species_name
room
character
latest_environment
today_action
```

`latest_environment` must include:

```text
temperature_c
humidity_pct
light_lux
soil_moisture_pct
measured_at
```

### 7.4 Environment Detail Response

필수 field:

```text
plant_id
latest
summary_24h
summary_7d
explanation
```

### 7.5 Care Log Feedback Response

필수 field:

```text
care_log_id
plant_id
action
recorded_at
feedback.character_mood
feedback.message
```

### 7.6 Chat Answer Response

필수 shape:

```json
{
  "request_id": "req-chat-001",
  "plant_id": "demo-plant-chorok-001",
  "intent": "watering_question",
  "profile": "P1",
  "answer": {
    "text": "[결론]\n...\n[근거]\n...\n[행동]\n...\n[주의]\n...",
    "sections": {
      "결론": "지금은 물을 더 주지 않아도 됩니다.",
      "근거": "최근 토양 수분과 물주기 기록이 충분합니다.",
      "행동": "오늘은 추가 물주기를 피하세요.",
      "주의": "센서가 건조 상태로 바뀌면 다시 확인하세요."
    }
  },
  "evidence": {
    "prompt_hash": "sha256hex",
    "provider": "mock",
    "model": "mock-llm-v1",
    "rule_result_ids": ["rule-watering-001"],
    "retrieved_chunk_ids": ["chunk-demo-monstera-watering-001"]
  }
}
```

규칙:

```text
answer.sections keys must be exactly: 결론, 근거, 행동, 주의.
provider/model metadata must remain present.
prompt_hash must remain present.
```

### 7.7 Companion Recommendation Response

필수 field:

```text
plant_id
room_id
recommendations[].species_id
recommendations[].common_name
recommendations[].decision
recommendations[].score
recommendations[].reasons
recommendations[].caution_notes
recommendations[].source_chunk_ids
evidence.current_species_id
evidence.snapshot_id
evidence.candidate_count
evidence.filter_version
```

금지 field:

```text
marketplace
purchase
purchase_url
affiliate
price
checkout
buy_url
```

### 7.8 Growth History Response

필수 field:

```text
plant_id
items[].type
items[].timestamp
items[].title
items[].summary
```

허용 item type:

```text
care_log
environment_summary
character_state
```

---

## 8. OpenAPI Example 계약

모든 schema family는 OpenAPI에 example을 가져야 한다.

필수:

```text
- route에 response_model 연결
- success response example 추가
- 기존 error response가 있는 route는 ErrorResponse example 추가
- docs/frontend_api_contract.md에 frontend-facing response shape 정리
```

금지:

```text
new endpoint semantics
new status code behavior unless existing implementation already returns it
business logic 변경
```

---

## 9. Schema Drift Test 계약

필수 테스트:

```text
required fields exist
nullable fields are explicit
answer.sections has exactly 결론/근거/행동/주의
species candidate has no disease/pest/treatment fields
companion response has no marketplace/purchase/affiliate fields
OpenAPI includes examples for every schema family
/healthz exact liveness response remains unchanged
/readyz is not introduced by this ticket
```

테스트 파일:

```text
tests/test_api_response_schemas.py
tests/test_openapi_examples.py
tests/test_schema_contract_snapshots.py
```

---

## 10. Runtime 계약

허용 runtime shape:

```text
FastAPI backend
  -> existing route handler
  -> existing service result
  -> response schema serialization
  -> JSON response
```

금지 runtime shape:

```text
backend
  -> frontend server
  -> schema generation daemon
  -> SDK generator process
  -> external schema registry
  -> background OpenAPI publisher
```

Ticket 26은 아래를 추가하지 않는다.

```text
new process
new worker
new scheduler
new Docker service
new port
new external HTTP call
new environment variable
```

---

## 11. `/healthz` / `/readyz` 계약

Ticket 26은 아래를 수정하지 않는다.

```http
GET /healthz
```

Ticket 26은 아래를 추가하거나 수정하지 않는다.

```http
GET /readyz
```

규칙:

```text
/healthz remains liveness-only.
/readyz remains dependency-readiness only if already present.
Schema stabilization is not a readiness dependency.
```

---

## 12. Functional Gate

Antigravity가 최종적으로 아래 명령을 통과시켜야 한다.

```bash
set -euo pipefail

ruff check app/schemas tests/test_api_response_schemas.py tests/test_openapi_examples.py tests/test_schema_contract_snapshots.py
ruff format --check app/schemas tests/test_api_response_schemas.py tests/test_openapi_examples.py tests/test_schema_contract_snapshots.py
pytest -q tests/test_api_response_schemas.py tests/test_openapi_examples.py tests/test_schema_contract_snapshots.py

docker build -t sunshine-backend:ticket26 .
docker rm -f sunshine-backend-ticket26 >/dev/null 2>&1 || true
docker run -d \
  --name sunshine-backend-ticket26 \
  -p 8000:8000 \
  -e APP_NAME=sunshine-backend \
  -e APP_ENV=local \
  sunshine-backend:ticket26

for i in $(seq 1 30); do
  if curl -fsS http://localhost:8000/healthz >/tmp/healthz.ticket26.json; then
    break
  fi
  sleep 1
done

test -s /tmp/healthz.ticket26.json

python - <<'PY'
import json
from pathlib import Path
body = json.loads(Path('/tmp/healthz.ticket26.json').read_text())
assert body == {"status": "ok", "service": "sunshine-backend"}, body
PY

curl -fsS http://localhost:8000/openapi.json >/tmp/ticket26.openapi.json

python - <<'PY'
import json
from pathlib import Path
schema = json.loads(Path('/tmp/ticket26.openapi.json').read_text())
text = json.dumps(schema, ensure_ascii=False)
required = [
    'SpeciesCandidate',
    'PlantCreated',
    'HomePlantCard',
    'EnvironmentDetail',
    'CareLogFeedback',
    'ChatAnswer',
    'CompanionRecommendation',
    'GrowthHistory',
]
missing = [x for x in required if x not in text]
assert not missing, missing
assert 'example' in text or 'examples' in text
PY

docker rm -f sunshine-backend-ticket26 >/dev/null 2>&1 || true
```

---

## 13. Required Tests

Antigravity는 최소 아래 테스트를 추가한다.

```text
test_species_candidate_response_schema
test_species_candidate_response_has_no_disease_or_pest_fields
test_plant_created_response_schema
test_home_plant_card_response_schema
test_environment_detail_response_schema
test_care_log_feedback_response_schema
test_chat_answer_response_schema
test_chat_answer_sections_exactly_four_korean_keys
test_companion_recommendation_response_schema
test_companion_response_has_no_marketplace_fields
test_growth_history_response_schema
test_openapi_has_species_candidate_example
test_openapi_has_plant_created_example
test_openapi_has_home_card_example
test_openapi_has_environment_detail_example
test_openapi_has_care_log_example
test_openapi_has_chat_answer_example
test_openapi_has_companion_example
test_openapi_has_growth_history_example
test_healthz_contract_unchanged
test_no_readyz_added_by_ticket26
```

---

## 14. Acceptance Criteria

Ticket 26은 아래를 모두 만족해야 한다.

```text
- response schema exists for species candidate flow
- response schema exists for plant created flow
- response schema exists for home plant card
- response schema exists for environment detail
- response schema exists for care log feedback
- response schema exists for chat answer
- response schema exists for companion recommendation
- response schema exists for growth history
- OpenAPI examples exist for all frontend-facing schemas
- schema tests block required-field drift
- chat answer sections remain exactly 결론/근거/행동/주의
- species candidate schema has no disease/pest diagnosis fields
- companion schema has no marketplace/purchase/affiliate fields
- existing user scoping behavior is preserved
- no new endpoint is introduced
- no business logic is changed
- no frontend/mobile code is added
- no DB migration is added
- /healthz remains liveness-only
- /readyz is not introduced or modified by this ticket
- pytest passes
- ruff passes
- Docker health and OpenAPI smoke gates pass
```

---

## 15. Do Not Implement

```text
frontend UI
mobile UI
React Native
browser automation
OpenAPI SDK generation
new endpoint
new business logic
new service layer
new domain behavior
new DB table
migration
real LLM provider
streaming
OAuth/JWT redesign
marketplace fields
purchase links
Polaris
GPU telemetry
NCCL
```
