# TICKET-018 — Chat Care Answer API

## 0. 목표

Sunshine 백엔드에 MVP care-question chat API를 연결한다.

이 티켓은 real LLM을 붙이지 않는다.  
이 티켓은 streaming을 만들지 않는다.  
이 티켓은 pest/disease 답변 정책이나 companion recommendation을 만들지 않는다.

Ticket 18의 책임은 아래까지만이다.

```text
POST /plants/{plant_id}/chat
  -> intent classification
  -> selected Rule Engine execution
  -> selected RAG retrieval
  -> EvidenceBuilder
  -> PromptBuilder
  -> LLMPort(MockLLM)
  -> prompt/evidence/response persistence
  -> fixed-format answer response
```

---

## 1. Ticket Identity

### Ticket ID

```text
TICKET-018
```

### Name

```text
Chat Care Answer API
```

### Goal

```text
Expose a minimal care-question chat API that orchestrates existing MVP components and returns a fixed-format grounded answer through MockLLM/LLMPort.
```

### Core output

```text
POST /plants/{plant_id}/chat
ChatOrchestrator
care-question pipeline orchestration
fixed answer format validation
answer section parser
prompt/evidence/response persistence call
MockLLM-backed response
```

### Strict non-goal

```text
no real vLLM adapter
no OpenAI adapter
no Anthropic adapter
no SSE streaming
no Redis queue
no worker process
no pest/disease final answer policy
no companion recommendation
no image diagnosis
no reranker
no CRAG
no Self-RAG
no HyDE
no multi-query retrieval
no P3 execution
no NCCL
no Polaris
no GPU telemetry
no mobile UI
```

---

## 2. 주변 티켓과의 연결

Ticket 18은 이전 티켓들을 처음으로 user-facing care answer API로 묶는 vertical slice다.

```text
Ticket 8:
  Rule Engine baseline care decision 제공

Ticket 13:
  intent + selected_rule_modules + selected_rag_layers 산출

Ticket 14:
  selected RAG layer 기반 retrieved chunks 제공

Ticket 15:
  ForwardContext / evidence bundle 생성

Ticket 16:
  ForwardContext를 fixed-format prompt로 변환

Ticket 17:
  LLMPort + MockLLM으로 deterministic response 생성

Ticket 18:
  위 단계들을 POST /plants/{plant_id}/chat에서 순서대로 orchestration

Ticket 19:
  pest/disease reference answer guardrail

Ticket 20/21:
  companion compatibility/recommendation

Ticket 22:
  evidence audit query API
```

Ticket 18의 역할:

```text
care question
  + plant_id
  + existing MVP components
  -> fixed-format grounded answer
  -> persisted prompt/evidence/response metadata
```

금지:

```text
real LLM provider 구현
streaming 구현
pest/disease 답변 생성
companion 추천 생성
새 DB schema/migration 생성
새 runtime service 추가
```

---

## 3. 수정/생성 허용 파일

### 수정 가능한 기존 파일

```text
app/main.py
app/api/__init__.py
app/services/__init__.py
app/domain/__init__.py
```

`app/main.py` 수정은 아래만 허용한다.

```text
include chat router
/healthz behavior unchanged
no /readyz creation
no startup dependency check
```

### 생성 가능한 새 파일

```text
app/api/chat.py
app/services/chat_orchestrator.py
app/domain/chat.py

 tests/test_chat_care_api.py
 tests/test_chat_orchestrator.py
 tests/fixtures/chat_fixtures.py
```

### 조건부 허용 파일

```text
app/repositories/chat_repository.py
```

조건:

```text
이미 이전 티켓에서 필요한 persistence schema가 존재할 때만 허용한다.
새 table을 만들기 위한 파일이 아니다.
기존 chat_requests / llm_runs / recommendation_evidence / retrieved_chunks linkage를 호출하는 얇은 boundary여야 한다.
```

금지:

```text
alembic/versions/<ticket18_*.py>
migrations/
새 persistence schema 추가
local JSON audit file
SQLite fallback
```

---

## 4. 금지 파일/디렉터리

아래 경로는 생성하거나 수정하지 않는다.

```text
app/llm/vllm_client.py
app/llm/openai_client.py
app/llm/anthropic_client.py
app/retrieval/reranker.py
app/retrieval/crag.py
app/vision/
app/mqtt/
app/workers/
app/services/companion_filter.py
app/services/pest_guardrail.py
app/services/streaming.py

alembic/
migrations/
Dockerfile
docker-compose.yml
.env.example
.github/workflows/
```

규칙:

```text
Ticket 18 must not introduce production LLM providers, streaming, new infra, pest/disease policy, companion recommendation, or schema expansion.
```

---

## 5. API 계약 — POST /plants/{plant_id}/chat

### Endpoint

```http
POST /plants/{plant_id}/chat
Content-Type: application/json
```

### Request

```json
{
  "request_id": "00000000-0000-0000-0000-000000001801",
  "question": "물 줘야 해?",
  "locale": "ko-KR"
}
```

규칙:

```text
request_id may be omitted and generated if project convention already allows it.
question must be non-empty.
locale defaults to ko-KR if project convention allows defaults.
plant_id comes from path.
```

### Response

```json
{
  "request_id": "00000000-0000-0000-0000-000000001801",
  "plant_id": "00000000-0000-0000-0000-000000001803",
  "intent": "watering_question",
  "profile": "P1",
  "answer": {
    "text": "[결론]\n...\n\n[근거]\n...\n\n[행동]\n...\n\n[주의]\n...",
    "sections": {
      "결론": "...",
      "근거": "...",
      "행동": "...",
      "주의": "..."
    }
  },
  "evidence": {
    "rule_result_ids": ["watering"],
    "retrieved_chunk_ids": ["uuid"],
    "prompt_hash": "sha256-or-hex",
    "model": "mock-llm-v1",
    "provider": "mock"
  }
}
```

필수 status behavior:

```text
200:
  care answer created and persisted

400 invalid_request:
  missing or empty question

404 plant_not_found:
  plant does not exist or does not belong to user if ownership exists

409 evidence_unavailable:
  required rule/evidence/retrieval stage failed before LLM

422 unsupported_intent_for_ticket18:
  pest_reference_question, companion_plant_question, unknown_question

500 chat_pipeline_failure:
  prompt/LLM response fixed sections missing or persistence failed
```

금지 response fields:

```text
stream
sse_url
websocket_url
real_provider_payload
diagnosis
treatment
companion_ranking
polaris_trace
gpu_telemetry
```

---

## 6. 지원 Intent 계약

Ticket 18에서 지원하는 MVP intent:

```text
watering_question
light_question
humidity_question
temperature_question
species_care_question
```

Routing:

```text
watering_question:
  rule_modules = [watering]
  rag_layers = [species_profile, care_knowledge]
  profile = P1

light_question:
  rule_modules = [light]
  rag_layers = [species_profile, care_knowledge]
  profile = P1

humidity_question:
  rule_modules = [humidity]
  rag_layers = [species_profile, care_knowledge]
  profile = P1

temperature_question:
  rule_modules = [temperature]
  rag_layers = [species_profile, care_knowledge]
  profile = P1

species_care_question:
  rule_modules = optional care rules
  rag_layers = [species_profile, care_knowledge]
  profile = P2
```

Ticket 18에서 막아야 하는 intent:

```text
pest_reference_question
companion_plant_question
unknown_question
```

반환:

```text
422 unsupported_intent_for_ticket18
```

---

## 7. ChatOrchestrator 계약

아래 파일을 생성한다.

```text
app/services/chat_orchestrator.py
```

필수 class shape:

```python
class ChatOrchestrator:
    async def answer_care_question(
        self,
        *,
        plant_id: str,
        question: str,
        locale: str = "ko-KR",
        request_id: str | None = None,
    ) -> ChatAnswerResult:
        ...
```

필수 orchestration order:

```text
1. Validate request.
2. Load plant context.
3. Classify intent.
4. Reject unsupported intent for Ticket 18.
5. Run selected Rule Engine modules.
6. Retrieve selected RAG layers.
7. Build ForwardContext through EvidenceBuilder.
8. Build prompt through PromptBuilder.
9. Call LLMPort using MockLLM boundary.
10. Validate fixed answer format.
11. Persist chat request / prompt / response / evidence links.
12. Return structured response.
```

Hard invariant:

```text
No LLMPort call before Rule Engine and EvidenceBuilder.
```

금지 behavior:

```text
no real LLM call
no direct HTTP provider call
no streaming
no background task dispatch
no Redis enqueue
no worker startup
no pest/disease answer generation
no companion recommendation
no schema migration
```

---

## 8. Fixed Answer Format 계약

LLM response는 반드시 아래 4개 섹션을 포함해야 한다.

```text
[결론]
[근거]
[행동]
[주의]
```

API는 다음 둘 다 반환할 수 있다.

```text
answer.text
answer.sections
```

Parser rules:

```text
all 4 sections required.
missing section -> fail closed.
extra user-visible sections should be rejected unless existing project parser explicitly permits them.
empty section should be rejected unless tests define an allowed fallback.
```

금지:

```text
returning raw MockLLM text without validation
returning success before persistence
returning success if fixed sections are missing
```

---

## 9. Persistence 계약

Ticket 18은 기존 persistence boundary를 통해 아래 정보를 저장해야 한다.

```text
request_id
plant_id
question
intent
selected_rule_modules
selected_rag_layers
rule_results
retrieved_chunks
prompt
prompt_hash
response_text
provider
model
tokens_in
tokens_out
latency_ms
```

규칙:

```text
Persistence must happen before success response.
If persistence fails, return 500 chat_pipeline_failure.
Use existing schema/repository boundary.
Do not introduce new migrations in this ticket.
```

금지 persistence:

```text
local JSON file audit
local SQLite fallback
logs as storage
new audit table without explicit migration ticket
```

---

## 10. Runtime 계약

허용 runtime topology:

```text
host
  -> backend container
      -> uvicorn app.main:app
      -> GET /healthz unchanged
      -> POST /plants/{plant_id}/chat
      -> ChatOrchestrator
      -> existing classifier/rules/retriever/evidence/prompt/mock LLM/persistence
      -> JSON response
```

Allowed long-lived containers:

```text
backend
postgres
mqtt
mqtt-ingest
```

금지 new long-lived containers:

```text
redis
nginx
vllm
model-server
llm
chat-worker
generic-worker
```

Backend process invariant:

```text
exactly one foreground uvicorn process
no worker process
no Redis consumer
no MQTT subscriber introduced here
no vLLM process
no SSE stream process
no model warmup
```

Startup forbidden:

```text
run chat pipeline at startup
run Rule Engine at startup
call retrieval at startup
call LLMPort at startup
connect to real LLM provider
start workers
run migrations
```

---

## 11. Network / Env 계약

Required network:

```text
backend listens on 0.0.0.0:8000
POST /plants/{plant_id}/chat served by backend only
```

Forbidden network behavior:

```text
external LLM API call
vLLM HTTP call
OpenAI call
Anthropic call
Redis call introduced by this ticket
SSE route
WebSocket route
```

Forbidden production imports/usages:

```text
httpx
requests
aiohttp
openai
anthropic
vllm
grpc
socket
StreamingResponse
EventSourceResponse
WebSocket
```

Forbidden new env vars:

```text
LLM_*
VLLM_*
OPENAI_*
ANTHROPIC_*
REDIS_*
MQTT_*
SSE_*
P3_*
```

Allowed:

```text
Use existing DB/session/repository configuration if already introduced by previous tickets.
Do not add new DB configuration.
```

---

## 12. Health / Readiness 계약

Ticket 18 must not modify:

```http
GET /healthz
```

Ticket 18 must not add or modify:

```http
GET /readyz
```

규칙:

```text
/healthz remains liveness-only.
/readyz, if it exists from previous DB ticket, remains unchanged.
If /readyz does not exist, Ticket 18 must not create it.
Chat correctness is verified by functional gates, not readiness checks.
```

---

## 13. Functional Gate — Executable

아래 gate는 Ticket 18이 care-question API만 구현했는지 확인한다.

```bash
#!/usr/bin/env bash
set -euo pipefail

PROJECT="sunshine-ticket18-gate"
IMAGE="sunshine-backend:ticket18"

fail() {
  echo
  echo "Ticket 18 Functional Gate: FAIL"
  echo "Failure Classification: $1"
  echo "Evidence: $2"
  docker compose -p "$PROJECT" logs --no-color || true
  docker compose -p "$PROJECT" down -v || true
  exit 1
}

cleanup() {
  docker compose -p "$PROJECT" down -v >/dev/null 2>&1 || true
  docker rm -f sunshine-backend-ticket18 >/dev/null 2>&1 || true
}
trap cleanup EXIT

# Gate 0: Scope boundary
git diff --name-only origin/main...HEAD | tee /tmp/ticket18_changed_files.txt || true
python - <<'PY' || exit 41
from pathlib import Path

allowed = {
    "app/api/__init__.py",
    "app/api/chat.py",
    "app/services/__init__.py",
    "app/services/chat_orchestrator.py",
    "app/domain/__init__.py",
    "app/domain/chat.py",
    "app/main.py",
    "app/repositories/chat_repository.py",
    "tests/test_chat_care_api.py",
    "tests/test_chat_orchestrator.py",
    "tests/fixtures/chat_fixtures.py",
}

forbidden_prefixes = (
    "app/vision/",
    "app/mqtt/",
    "app/workers/",
    "alembic/",
    "migrations/",
    ".github/workflows/",
)

forbidden_exact = {
    "Dockerfile",
    "docker-compose.yml",
    ".env.example",
    "app/llm/vllm_client.py",
    "app/llm/openai_client.py",
    "app/llm/anthropic_client.py",
    "app/retrieval/reranker.py",
    "app/retrieval/crag.py",
    "app/services/companion_filter.py",
    "app/services/pest_guardrail.py",
    "app/services/streaming.py",
}

changed = [p.strip() for p in Path("/tmp/ticket18_changed_files.txt").read_text().splitlines() if p.strip()]
violations = []
for file in changed:
    if file in forbidden_exact:
        violations.append(("forbidden_exact_file", file))
    if file.startswith(forbidden_prefixes):
        violations.append(("forbidden_prefix", file))
    if file not in allowed and not file.startswith("tests/"):
        violations.append(("not_in_allowed_files", file))

if violations:
    for kind, file in violations:
        print(f"{kind}: {file}")
    raise SystemExit(1)
PY
if [ "$?" = "41" ]; then
  fail "ticket18_scope_boundary_failure" "Changed files outside Ticket 18 care-chat scope"
fi

# Gate 1: Python quality
ruff check app/api/chat.py app/services/chat_orchestrator.py app/domain/chat.py tests/test_chat_care_api.py tests/test_chat_orchestrator.py \
  || fail "lint_failure" "ruff check failed"
ruff format --check app/api/chat.py app/services/chat_orchestrator.py app/domain/chat.py tests/test_chat_care_api.py tests/test_chat_orchestrator.py \
  || fail "format_failure" "ruff format --check failed"

# Gate 2: Unit/API tests
pytest -q tests/test_chat_orchestrator.py tests/test_chat_care_api.py \
  || fail "chat_unit_or_api_test_failure" "chat orchestrator or API tests failed"

# Gate 3: Forbidden future leakage
python - <<'PY' || exit 42
from pathlib import Path

targets = [
    Path("app/api/chat.py"),
    Path("app/services/chat_orchestrator.py"),
    Path("app/domain/chat.py"),
]
for path in targets:
    text = path.read_text()
    forbidden_tokens = [
        "httpx", "requests", "aiohttp", "openai", "anthropic", "vllm",
        "grpc", "socket", "StreamingResponse", "EventSourceResponse", "WebSocket",
        "redis", "paho", "NCCL", "Polaris", "rerank", "CRAG", "Self-RAG",
    ]
    hits = [token for token in forbidden_tokens if token in text]
    assert not hits, f"{path}: forbidden leakage: {hits}"
PY
if [ "$?" = "42" ]; then
  fail "future_feature_leakage" "Real provider, streaming, Redis, Polaris, reranker, or future feature introduced"
fi

# Gate 4: Orchestration order
python - <<'PY' || exit 43
import asyncio
from tests.fixtures.chat_fixtures import make_recording_orchestrator_dependencies

async def main() -> None:
    orchestrator, calls = make_recording_orchestrator_dependencies()
    response = await orchestrator.answer_care_question(
        plant_id="plant-001",
        question="물 줘야 해?",
        locale="ko-KR",
        request_id="req-order-001",
    )
    expected_order = [
        "load_plant",
        "classify_intent",
        "run_rules",
        "retrieve_chunks",
        "build_evidence",
        "build_prompt",
        "llm_generate",
        "validate_answer_format",
        "persist_chat_run",
    ]
    assert calls == expected_order, calls
    assert response.request_id == "req-order-001"

asyncio.run(main())
PY
if [ "$?" = "43" ]; then
  fail "orchestration_order_failure" "LLM must not run before rules/evidence/prompt"
fi

# Gate 5: Docker build + health smoke
docker build -t "$IMAGE" . \
  || fail "docker_build_failure" "docker build failed"

docker run -d \
  --name sunshine-backend-ticket18 \
  -p 8000:8000 \
  -e APP_NAME=sunshine-backend \
  -e APP_ENV=local \
  "$IMAGE" \
  || fail "docker_start_failure" "backend failed to start"

for i in $(seq 1 30); do
  if curl -fsS http://localhost:8000/healthz >/tmp/healthz.ticket18.json; then
    break
  fi
  sleep 1
done

test -s /tmp/healthz.ticket18.json \
  || fail "healthz_regression_failure" "healthz not reachable"

python - <<'PY' || exit 44
import json
from pathlib import Path
body = json.loads(Path("/tmp/healthz.ticket18.json").read_text())
assert body == {"status": "ok", "service": "sunshine-backend"}, body
PY
if [ "$?" = "44" ]; then
  fail "healthz_contract_failure" "/healthz exact JSON changed"
fi

# Gate 6: Unsupported intent boundary should be covered by tests
pytest -q tests/test_chat_care_api.py -k "unsupported or pest or companion" \
  || fail "unsupported_intent_boundary_failure" "pest/companion intent must be blocked in Ticket 18"

# Gate 7: No direct LLM before evidence
python - <<'PY' || exit 45
import asyncio
from tests.fixtures.chat_fixtures import make_missing_evidence_orchestrator

async def main() -> None:
    orchestrator, calls = make_missing_evidence_orchestrator()
    try:
        await orchestrator.answer_care_question(
            plant_id="plant-001",
            question="물 줘야 해?",
            locale="ko-KR",
            request_id="req-missing-evidence",
        )
    except Exception:
        pass
    assert "llm_generate" not in calls, calls
    assert "persist_chat_run" not in calls, calls

asyncio.run(main())
PY
if [ "$?" = "45" ]; then
  fail "llm_before_evidence_failure" "LLM called despite missing evidence"
fi

# Gate 8: Readiness boundary
if grep -R "readyz" app tests; then
  fail "readiness_boundary_failure" "Ticket 18 must not introduce or modify /readyz"
fi

cat <<'REPORT'
Ticket 18 Functional Gate Report

Scope:
- Chat Care API only: pass
- no pest/disease answer implementation: pass
- no companion recommendation implementation: pass
- no real LLM provider: pass
- no streaming: pass
- no Docker topology change: pass

Pipeline:
- classify intent before rules: pass
- rules before evidence: pass
- evidence before prompt: pass
- prompt before LLMPort: pass
- fixed answer format validated: pass
- persist before success response: pass

Runtime:
- /healthz remains liveness-only: pass
- /readyz not introduced by this ticket: pass
- Docker smoke passed: pass

Result:
- pass
REPORT
```

---

## 14. Required Tests

최소 테스트:

```text
test_chat_api_watering_question_returns_fixed_format_answer
test_chat_api_light_question_returns_fixed_format_answer
test_chat_api_humidity_question_returns_fixed_format_answer
test_chat_api_temperature_question_returns_fixed_format_answer
test_chat_api_species_care_question_uses_p2
test_chat_api_unsupported_pest_intent_returns_422
test_chat_api_companion_intent_returns_422
test_chat_orchestrator_runs_rule_before_llm
test_chat_orchestrator_builds_evidence_before_prompt
test_chat_orchestrator_does_not_call_llm_when_evidence_missing
test_chat_orchestrator_persists_prompt_response_evidence
test_chat_response_contains_prompt_hash_provider_model
test_chat_response_parser_rejects_missing_sections
test_healthz_contract_unchanged
test_no_readyz_added_by_ticket18
```

---

## 15. Acceptance Criteria

```text
POST /plants/{plant_id}/chat exists.
watering/light/humidity/temperature/species-care questions are supported.
pest/disease and companion intents are rejected or deferred.
intent classification runs before rules.
selected Rule Engine modules run before LLM.
RAG retrieval runs before EvidenceBuilder.
EvidenceBuilder runs before PromptBuilder.
PromptBuilder runs before LLMPort.
LLMPort uses MockLLM only.
response includes [결론][근거][행동][주의].
response includes parsed sections.
response includes prompt_hash.
response includes provider/model metadata.
prompt/evidence/response are persisted through existing persistence boundary.
no real LLM provider is implemented.
no streaming is implemented.
no Redis/worker/vLLM is introduced.
/healthz remains liveness-only.
/readyz is not introduced or modified by this ticket.
pytest passes.
ruff passes.
Docker smoke and API gate pass.
```

---

## 16. Antigravity 작업 지시 요약

Antigravity에게 줄 때 핵심은 아래다.

```text
Implement Ticket 18 only.
Create the minimal POST /plants/{plant_id}/chat path for MVP care questions.
Use existing Ticket 13/14/15/16/17 boundaries.
Use MockLLM only.
Persist through existing persistence boundary.
Return fixed [결론][근거][행동][주의] answer.
Reject pest/disease, companion, and unknown intents with 422.
Do not add real LLM, streaming, Redis, worker, vLLM, migrations, or new infra.
```
