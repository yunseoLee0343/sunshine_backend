# TICKET-024 — MVP E2E Test Harness

## 0. 목표

Sunshine 백엔드 MVP가 deterministic demo data와 MockLLM만으로 end-to-end로 동작하는지 검증하는 E2E test harness를 만든다.

이 티켓은 product behavior를 추가하지 않는다.  
이 티켓은 새 API를 만들지 않는다.  
이 티켓은 frontend/mobile/browser automation을 만들지 않는다.  
이 티켓은 release gate가 아니다.

Ticket 24의 책임은 아래까지만이다.

```text
Ticket 23 demo seed
  -> backend E2E test client
  -> MVP API flow execution
  -> fixed answer / guardrail / evidence assertions
  -> CI-friendly local gate
```

---

## 1. Ticket Identity

### Ticket ID

```text
TICKET-024
```

### Name

```text
MVP E2E Test Harness
```

### Goal

```text
Prove the complete backend MVP flow works end-to-end using deterministic demo data and MockLLM.
```

### Core output

```text
backend E2E pytest harness
deterministic E2E fixtures
Ticket 23 demo seed setup/teardown
MVP API flow assertions
fixed answer format assertions
pest/reference safety assertions
companion recommendation assertions
evidence query assertions
optional E2E runner script
```

### Strict non-goal

```text
no new product API
no new service behavior
no new domain logic
no new DB schema
no migration
no frontend
no mobile UI
no browser automation
no Playwright/Cypress/Selenium
no real auth implementation
no real external LLM
no vLLM/OpenAI/Anthropic adapter
no new Redis/MQTT/Nginx/worker requirement
no release gate
no manual QA checklist
```

---

## 2. 주변 티켓과의 연결

Ticket 24는 backend MVP 전체 흐름을 검증하는 harness다.

```text
Ticket 23:
  deterministic demo seed 제공

Ticket 18:
  care chat answer API 제공

Ticket 19:
  pest/disease reference guardrail 제공

Ticket 21:
  companion recommendation API/chat path 제공

Ticket 22:
  evidence query API 제공

Ticket 24:
  위 흐름들이 하나의 backend E2E flow로 연결되는지 검증

Ticket 25:
  auth/user scope minimal

Ticket 26:
  API response schema stabilization

Ticket 27+:
  frontend/mobile implementation

Ticket 34:
  final release gate
```

Ticket 24의 역할:

```text
seed demo data
  + call existing backend endpoints/services
  + assert MVP flow behavior
  + assert evidence exists
  + assert safety boundaries
```

금지:

```text
새 기능 구현
API behavior 수정
DB schema 수정
frontend/browser test 구현
release blocking policy 구현
real external provider 붙이기
```

---

## 3. 수정/생성 허용 파일

### 생성 가능한 새 파일

```text
tests/e2e/__init__.py
tests/e2e/conftest.py
tests/e2e/test_mvp_flow.py
tests/e2e/test_mvp_guardrails.py

tests/fixtures/e2e_client.py
tests/fixtures/e2e_assertions.py
tests/fixtures/e2e_seed.py

scripts/run_mvp_e2e.py
docs/mvp_e2e_harness.md
```

### 조건부 수정 가능 파일

```text
pyproject.toml
```

허용 수정:

```text
pytest marker 추가:
- e2e
- mvp
```

조건부:

```text
.github/workflows/ci.yml
```

허용 조건:

```text
기존 CI convention이 e2e marker 실행을 요구하는 경우에만 pytest -m e2e 추가.
기본적으로는 수정하지 않는다.
```

---

## 4. 금지 파일/디렉터리

아래 경로는 생성하거나 수정하지 않는다.

```text
app/api/
app/services/
app/domain/
app/repositories/
app/llm/
app/retrieval/
app/vision/
app/mqtt/
app/workers/

alembic/
migrations/
Dockerfile
docker-compose.yml
.env.example

frontend/
web/
mobile/
playwright.config.*
cypress.config.*
selenium.*
```

규칙:

```text
Ticket 24 must verify existing MVP behavior only.
It must not change application implementation.
```

---

## 5. E2E Harness 계약

필수 실행 모드:

```text
Mode A: pytest in-process client
  - required
  - FastAPI TestClient 또는 AsyncClient 사용

Mode B: docker/localhost smoke
  - optional or script-level
  - localhost:8000 against existing backend
```

필수 구조:

```text
Ticket 23 demo seed
  -> E2E client fixture
  -> MVP API flow execution
  -> response assertions
  -> guardrail assertions
  -> evidence query assertions
```

금지:

```text
external HTTP
real LLM call
browser driver
mobile simulator
real production auth
random IDs
wall-clock based expected values
time.sleep for correctness
```

---

## 6. 필수 E2E Flow Coverage

Ticket 24는 아래 backend MVP flow를 검증한다.

```text
1. onboarding
2. plant card
3. sensor reading
4. snapshot
5. rule result
6. watering log
7. care chat answer
8. pest reference guardrail
9. companion recommendation
10. growth history
11. evidence query for chat answer
```

각 flow는 기존 API/service를 호출해야 한다.

금지:

```text
테스트 통과를 위해 app 코드를 수정하지 않는다.
테스트 전용 product endpoint를 만들지 않는다.
테스트 안에서 business logic을 재구현하지 않는다.
```

---

## 7. Demo Data 계약

Ticket 23 seed를 사용한다.

필수 canonical data:

```text
user_id: demo-user-001
plant_id: demo-plant-chorok-001
nickname: 초록이
room: 거실
species:
  - Monstera
  - Pothos
  - Philodendron
watering question:
  - 물 또 줘야 해?
companion question:
  - 같이 키우기 좋은 식물 추천해줘
```

규칙:

```text
Ticket 24 must import or reuse Ticket 23 demo seed.
Ticket 24 must not define a conflicting seed dataset.
```

---

## 8. Assertion 계약

### Fixed answer format

모든 chat answer는 아래 section을 포함해야 한다.

```text
[결론]
[근거]
[행동]
[주의]
```

### Care answer

질문:

```text
물 또 줘야 해?
```

검증:

```text
response has request_id
answer has fixed sections
answer reflects Rule Engine evidence
answer does not override no-watering rule
evidence endpoint returns prompt/evidence/response
```

### Pest reference

질문 예시:

```text
잎에 하얀 점이 있어. 병충해야?
```

검증:

```text
answer has fixed sections
answer is reference-only
answer does not claim definitive diagnosis
answer does not claim image-based diagnosis
answer does not command pesticide/treatment
```

금지 phrase 예시:

```text
이 사진은 응애입니다
흰가루병입니다
약을 뿌리세요
살충제를 사용하세요
```

### Companion recommendation

질문:

```text
같이 키우기 좋은 식물 추천해줘
```

검증:

```text
direct recommendation endpoint returns compatible recommendations
chat answer has fixed sections
recommendation includes light/humidity/temperature/room reasons
caution notes appear when metadata exists
no marketplace/purchase/affiliate fields exist
```

### Evidence query

검증:

```text
request_id exists
prompt_hash exists
retrieved_chunks exists
rule_results exists
response_text exists
provider/model metadata exists
```

---

## 9. Runtime 계약

허용 runtime topology:

```text
pytest process
  -> deterministic demo seed fixture
  -> in-process backend test client
  -> existing app routes/services
  -> assertions
```

Optional smoke:

```text
host
  -> backend container
  -> curl /healthz
  -> run existing MVP endpoint checks
```

Forbidden runtime topology:

```text
pytest
  -> frontend browser
  -> mobile simulator
  -> external LLM
  -> vLLM server
  -> Redis worker
  -> new MQTT broker requirement
  -> Nginx gateway
```

Process invariant:

```text
0 production processes added
0 long-running test daemons
0 worker loops
0 model loaders
0 browser drivers
```

---

## 10. Network / Env 계약

Allowed network:

```text
in-process TestClient / AsyncClient
localhost:8000 only for docker smoke mode
```

Forbidden network:

```text
external HTTP
OpenAI
Anthropic
vLLM endpoint
Kaggle download
marketplace API
remote object storage
browser driver server
mobile emulator
```

Allowed test-only env:

```env
SUNSHINE_E2E_MODE=inprocess|docker
SUNSHINE_E2E_BASE_URL=http://localhost:8000
```

Forbidden env:

```text
OPENAI_*
ANTHROPIC_*
VLLM_*
BROWSER_*
PLAYWRIGHT_*
CYPRESS_*
SELENIUM_*
MOBILE_*
MARKETPLACE_*
POLARIS_*
GPU_*
```

---

## 11. `/healthz` / `/readyz` 계약

Ticket 24는 아래 endpoint를 수정하지 않는다.

```http
GET /healthz
```

Ticket 24는 아래 endpoint를 생성하거나 수정하지 않는다.

```http
GET /readyz
```

규칙:

```text
Ticket 24 may assert existing /healthz behavior.
Ticket 24 must not change /healthz.
Ticket 24 must not introduce readiness behavior.
```

---

## 12. Functional Gate — 간단 실행 계약

Antigravity는 최소 아래 명령이 통과하도록 구현한다.

```bash
ruff check tests/e2e tests/fixtures/e2e_client.py tests/fixtures/e2e_assertions.py tests/fixtures/e2e_seed.py scripts/run_mvp_e2e.py
ruff format --check tests/e2e tests/fixtures/e2e_client.py tests/fixtures/e2e_assertions.py tests/fixtures/e2e_seed.py scripts/run_mvp_e2e.py
pytest -q -m e2e tests/e2e
python scripts/run_mvp_e2e.py --mode inprocess --check-only
```

Optional Docker smoke:

```bash
docker build -t sunshine-backend:ticket24 .
docker run -d --name sunshine-backend-ticket24 -p 8000:8000 -e APP_NAME=sunshine-backend -e APP_ENV=local sunshine-backend:ticket24
curl -fsS http://localhost:8000/healthz
python scripts/run_mvp_e2e.py --mode docker --base-url http://localhost:8000 --check-only
```

Boundary check:

```bash
# app/ must not be changed by this ticket
# no frontend/browser/mobile files
# no migration
# no Docker topology change
# no /readyz
```

---

## 13. Required Tests

추가할 테스트:

```text
test_e2e_onboarding_flow
test_e2e_home_plant_card_flow
test_e2e_sensor_reading_flow
test_e2e_snapshot_flow
test_e2e_rule_result_flow
test_e2e_watering_log_flow
test_e2e_growth_history_flow
test_e2e_care_chat_fixed_answer_and_evidence
test_e2e_pest_reference_has_no_unsupported_diagnosis
test_e2e_companion_recommendation_has_environment_reasons
test_e2e_chat_answers_use_mock_llm_only
test_e2e_evidence_query_exists_for_care_chat
test_e2e_evidence_query_exists_for_pest_reference
test_e2e_evidence_query_exists_for_companion_chat
test_e2e_no_marketplace_fields
test_e2e_no_external_llm_required
test_e2e_healthz_contract_unchanged
test_e2e_no_readyz_added_by_ticket24
```

---

## 14. Acceptance Criteria

```text
E2E tests cover onboarding.
E2E tests cover plant card.
E2E tests cover sensor reading.
E2E tests cover snapshot.
E2E tests cover rule result.
E2E tests cover watering log.
E2E tests cover chat answer.
E2E tests cover pest reference guardrail.
E2E tests cover companion recommendation.
E2E tests cover growth history.
E2E tests verify evidence exists for chat answers.
E2E uses deterministic Ticket 23 data.
E2E uses MockLLM only.
No external LLM is required.
No unsupported diagnosis appears.
No marketplace/purchase fields appear.
No frontend/browser/mobile automation is added.
No new app product code is added.
No DB migration is added.
No real MQTT requirement is added unless already provided by earlier CI stage.
/healthz remains liveness-only.
/readyz is not introduced or modified.
pytest -m e2e passes.
ruff passes.
Optional Docker smoke passes.
```

---

## 15. 최종 금지 목록

```text
Do not implement Ticket 25 auth/user scope.
Do not implement Ticket 26 schema stabilization.
Do not implement frontend/mobile.
Do not implement browser automation.
Do not implement product guardrail suite.
Do not implement final release gate.
Do not add real external LLM.
Do not add vLLM.
Do not add Redis worker.
Do not add Nginx gateway.
Do not add new MQTT requirement.
Do not add DB migration.
Do not change app product code.
Do not change /healthz.
Do not add /readyz.
```
