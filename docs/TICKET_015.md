# TICKET-015 — EvidenceBuilder / ForwardContext

## 0. 목표

Sunshine 백엔드에서 LLM 호출 전에 사용할 구조화된 evidence bundle을 생성한다.

이 티켓은 final answer를 생성하지 않는다.  
이 티켓은 prompt를 만들지 않는다.  
이 티켓은 LLM을 호출하지 않는다.  
이 티켓은 retrieval ranking이나 Rule Engine semantics를 바꾸지 않는다.

Ticket 15의 책임은 아래까지만이다.

```text
chat intent metadata
  + plant/species profile
  + latest/24h/7d sensor snapshots
  + recent care logs
  + Rule Engine result
  + Ticket 14 retrieved chunks
  -> strict ForwardContext
  -> source_coverage
  -> deterministic evidence_hash
  -> evidence_bundles persistence
  -> later PromptBuilder가 소비할 수 있는 evidence bundle 반환
```

---

## 1. Ticket Identity

### Ticket ID

```text
TICKET-015
```

### Name

```text
EvidenceBuilder / ForwardContext
```

### Goal

```text
Build a structured evidence bundle before any LLM call.
```

### Core output

```text
ForwardContext schema
EvidenceBuilder service
EvidenceRepository
evidence bundle persistence
source coverage validation
Rule Engine result inclusion
retrieved chunks inclusion when RAG is used
stable evidence_hash
internal evidence build API
```

### Strict non-goal

```text
no final prompt formatting
no PromptBuilder
no fixed final answer format
no LLM provider implementation
no LLMPort
no final answer generation
no streaming
no vLLM
no Redis queue
no Nginx
no companion ranking execution
no pest/disease diagnosis
no RAG retrieval implementation changes
no reranker
no CRAG
no Self-RAG
no HyDE
```

---

## 2. 주변 티켓과의 연결

Ticket 15는 deterministic/data retrieval 단계와 future LLM 단계 사이의 evidence boundary다.

```text
Ticket 7:
  latest / 24h / 7d environment snapshots를 제공

Ticket 8:
  Rule Engine result를 제공

Ticket 11:
  recent care logs를 제공

Ticket 13:
  chat intent classification과 selected_rule_modules / selected_rag_layers를 제공

Ticket 14:
  retrieval_runs / retrieved_chunks metadata를 제공

Ticket 15:
  위 입력들을 ForwardContext / evidence bundle로 조립

Ticket 16:
  evidence bundle을 final answer prompt로 변환

Ticket 17:
  LLMPort 도입

Ticket 18:
  Chat Care Answer API에서 최종 답변 생성

Ticket 19:
  pest/disease reference answer guardrail

Ticket 20/21:
  companion compatibility/recommendation
```

Ticket 15의 역할:

```text
request_id
  + user_id
  + plant_id
  -> verify ownership
  -> load chat intent metadata
  -> load plant/species/sensor/care/retrieval/rule facts
  -> build ForwardContext
  -> persist evidence bundle
  -> return evidence bundle id + hash + source coverage
```

금지:

```text
final answer 생성
PromptBuilder 생성
LLMPort 생성
LLM 호출
streaming 구현
retrieval ranking 변경
Rule Engine decision override
pest/disease diagnosis 생성
companion ranking 생성
```

---

## 3. 수정/생성 허용 파일

### 수정 가능한 기존 파일

```text
app/main.py
app/api/__init__.py
app/models/chat_request.py
app/models/environment_snapshot.py
app/models/care_log.py
app/repositories/__init__.py
app/repositories/plant_repository.py
app/repositories/rule_input_repository.py
app/repositories/snapshot_repository.py
app/repositories/care_log_repository.py
app/repositories/chunk_repository.py
app/repositories/retrieval_repository.py
app/services/rule_engine.py
app/core/config.py
pyproject.toml
.github/workflows/ci.yml
```

### 생성 가능한 새 파일

```text
app/domain/evidence.py
app/schemas/evidence.py
app/api/evidence.py
app/services/evidence_builder.py
app/repositories/evidence_repository.py

tests/test_forward_context_schema.py
tests/test_evidence_builder.py
tests/test_evidence_api.py
tests/test_evidence_persistence.py
tests/test_evidence_hash.py
tests/test_ticket15_boundary.py
```

### 조건부 migration 허용

```text
alembic/versions/<ticket15_evidence_bundle>.py
```

허용 table:

```text
evidence_bundles
evidence_bundle_sources
```

허용 columns — `evidence_bundles`:

```text
evidence_bundle_id
request_id
user_id
plant_id
intent
forward_context_json
evidence_hash
source_coverage_json
created_at
```

허용 columns — `evidence_bundle_sources`:

```text
id
evidence_bundle_id
source_type
source_id
source_ref
included
created_at
```

금지 migration:

```text
prompt tables
llm_runs prompt/response columns
final answer table
vector index tables
companion ranking tables
chat transcript tables
Redis/job queue tables
```

---

## 4. 금지 파일/디렉터리

아래 경로는 생성하거나 수정하지 않는다.

```text
app/services/prompt_builder.py
app/services/chat_orchestrator.py
app/services/chat_care_answer_service.py
app/services/llm_port.py
app/services/companion_recommendation.py
app/services/pest_diagnosis_service.py

app/api/chat.py
app/api/chat_runs.py
app/api/companion.py
app/api/diagnosis.py

app/llm/
deploy/
```

이미 이전 티켓에서 존재할 수 있는 경로:

```text
app/rules/
app/retrieval/
app/api/chat_intent.py
app/api/retrieval.py
app/api/home.py
app/api/environment.py
app/api/history.py
app/api/care_logs.py
```

규칙:

```text
Ticket 15 may read Rule Engine and retrieval outputs.
Ticket 15 must not modify Rule Engine semantics.
Ticket 15 must not modify retrieval ranking/scoring semantics.
Ticket 15 must not create prompt, LLM, final chat answer, companion recommendation, or diagnosis logic.
```

---

## 5. ForwardContext 계약

ForwardContext는 LLM 이전 단계의 단일 정규화 payload다.

필수 top-level fields:

```text
request_id
user_question
intent
selected_rule_modules
selected_rag_layers
species_profile
sensor_snapshot
care_logs
rule_results
retrieved_chunks
companion_candidates
metadata
```

필수 metadata:

```json
{
  "built_at": "2026-05-04T12:00:00+09:00",
  "builder_version": "evidence_builder_v1",
  "source_request_id": "uuid"
}
```

규칙:

```text
ForwardContext must be strict JSON-serializable.
Field names must be stable.
Missing optional list sections must be [] not omitted.
Missing optional object sections may be null.
No final prompt is allowed.
No final answer is allowed.
No raw LLM response is allowed.
No model/provider metadata is allowed.
```

금지 ForwardContext field:

```text
prompt
prompt_hash
final_answer
chat_answer
llm_response
model_name
provider
streaming_chunks
diagnosis
treatment
companion_ranking
```

---

## 6. Source Inclusion 계약

### Chat intent

Must include:

```text
request_id
user_question
intent
selected_rule_modules
selected_rag_layers
```

Source:

```text
chat_requests or chat_intent_classifications
```

Missing behavior:

```text
missing chat intent metadata -> 400 or 422
```

### Species profile

Must include:

```text
species_profile_id
korean_name
scientific_name
common_name
care thresholds if present
```

Missing behavior:

```text
missing plant/species profile -> 403 or 404
```

### Sensor snapshot

Must include:

```text
latest environment snapshot if available
24h summary if available
7d summary if available
```

If missing:

```json
{
  "latest": null,
  "summary_24h": null,
  "summary_7d": null
}
```

### Care logs

Must include:

```text
last 10 care logs by acted_at desc
action_type
acted_at
note
```

If missing:

```json
[]
```

### Rule results

Must include Rule Engine result.

Required shape:

```json
{
  "care_status": "needs_action",
  "primary_action": "water",
  "severity": "medium",
  "reason_codes": ["soil_moisture_below_min"],
  "rule_results": [
    {
      "rule_id": "watering",
      "care_status": "needs_action",
      "primary_action": "water",
      "severity": "medium",
      "reason_codes": ["soil_moisture_below_min"],
      "evidence_facts": []
    }
  ]
}
```

규칙:

```text
EvidenceBuilder may invoke RuleEngine to produce current rule result.
If selected_rule_modules is non-empty, corresponding rule results must exist.
Rule Engine result must not be overridden.
Rule Engine evidence_facts must be preserved.
LLM must not decide care_status or primary_action.
```

### Retrieved chunks

Definition of “RAG used”:

```text
selected_rag_layers is non-empty
```

Allowed source:

```text
latest retrieval_run for request_id
retrieved_chunks joined with knowledge_chunks
```

Required fields:

```text
chunk_id
rank
score
layer
text
source_metadata
```

규칙:

```text
If selected_rag_layers is non-empty, retrieved_chunks must come from Ticket 14 persistence.
Preferred default: require existing retrieval_run for request_id.
If selected_rag_layers is non-empty and no retrieval_run exists, return 400 or 422.
Do not re-rank chunks.
Do not modify retrieval scoring.
Do not call external retrieval services.
```

### Companion candidates

For `intent = companion_plant_question`:

```json
{
  "companion_candidates": []
}
```

규칙:

```text
Ticket 15 may include candidate chunks from companion_plant RAG layer.
Ticket 15 must not rank companion plants.
Ticket 15 must not execute compatibility filter.
Ticket 20/21 own companion filtering and recommendation.
```

---

## 7. EvidenceBuilder Service 계약

아래 파일을 생성한다.

```text
app/services/evidence_builder.py
```

필수 class shape:

```python
from uuid import UUID

class EvidenceBuilder:
    async def build(
        self,
        *,
        request_id: UUID,
        user_id: UUID,
        plant_id: UUID,
    ) -> EvidenceBundle:
        ...
```

필수 동작:

```text
1. Verify plant belongs to user_id.
2. Load chat intent classification by request_id.
3. Verify classification plant_id/user_id match request.
4. Load plant + species profile.
5. Load latest/24h/7d environment snapshots.
6. Load recent care logs.
7. Run or load Rule Engine result.
8. Load retrieved chunks metadata for request_id if selected_rag_layers is non-empty.
9. Build strict ForwardContext.
10. Build source_coverage.
11. Compute deterministic evidence_hash.
12. Persist evidence bundle.
13. Return persisted evidence bundle.
```

금지 behavior:

```text
PromptBuilder 호출
prompt template 생성
[결론][근거][행동][주의] final answer section 생성
LLMPort 호출
LLM 호출
streaming dispatch
Redis dispatch
vLLM call
companion compatibility ranking
disease/pest diagnosis
retrieval ranking mutation
Rule Engine decision override
```

---

## 8. Evidence Hash 계약

Hash input:

```text
canonical_json(ForwardContext)
```

Hash format:

```text
sha256:<hex>
```

규칙:

```text
JSON keys sorted.
Datetimes normalized to ISO-8601 strings.
Lists preserve deterministic order.
Same inputs produce same evidence_hash.
Different rule result changes evidence_hash.
Different retrieved chunk set changes evidence_hash.
For deterministic gates, built_at must be injectable.
```

금지:

```text
Python object repr
nondeterministic dict order
random UUID inside hashed payload
current timestamp inside hashed payload unless injected/stabilized in tests
```

---

## 9. Evidence Persistence 계약

Persist `evidence_bundles`:

```text
evidence_bundle_id
request_id
user_id
plant_id
intent
forward_context_json
source_coverage_json
evidence_hash
created_at
```

Optional persist `evidence_bundle_sources`:

```text
evidence_bundle_id
source_type
source_id
source_ref
included
```

Idempotency:

```text
request_id is unique.
Repeated build for same request_id/user_id/plant_id returns existing evidence_bundle by default.
Duplicate request_id with different user_id or plant_id returns 409.
```

금지 persistence:

```text
prompt
prompt_hash
final answer
LLM response
model/provider metadata
streaming chunks
llm_runs
companion ranking
```

---

## 10. API 계약 — POST /evidence/build

### Endpoint

```http
POST /evidence/build
Content-Type: application/json
```

### Request

```json
{
  "request_id": "00000000-0000-0000-0000-000000001501",
  "user_id": "00000000-0000-0000-0000-000000001502",
  "plant_id": "00000000-0000-0000-0000-000000001503"
}
```

### Response

```json
{
  "evidence_bundle_id": "uuid",
  "request_id": "00000000-0000-0000-0000-000000001501",
  "plant_id": "00000000-0000-0000-0000-000000001503",
  "intent": "watering_question",
  "forward_context": {
    "request_id": "00000000-0000-0000-0000-000000001501",
    "user_question": "물 줘야 해?",
    "intent": "watering_question",
    "selected_rule_modules": ["watering"],
    "selected_rag_layers": ["species_profile", "care_knowledge"],
    "species_profile": {
      "species_profile_id": "uuid",
      "korean_name": "몬스테라",
      "scientific_name": "Monstera deliciosa",
      "common_name": "Monstera"
    },
    "sensor_snapshot": {
      "latest": {},
      "summary_24h": {},
      "summary_7d": {}
    },
    "care_logs": [],
    "rule_results": [],
    "retrieved_chunks": [],
    "companion_candidates": [],
    "metadata": {
      "built_at": "2026-05-04T12:00:00+09:00",
      "builder_version": "evidence_builder_v1",
      "source_request_id": "00000000-0000-0000-0000-000000001501"
    }
  },
  "source_coverage": {
    "chat_intent": true,
    "species_profile": true,
    "sensor_snapshot": true,
    "care_logs": true,
    "rule_results": true,
    "retrieved_chunks": true,
    "companion_candidates": false
  },
  "evidence_hash": "sha256:..."
}
```

Required status behavior:

```text
200:
  evidence bundle exists already for request_id and matches inputs

201:
  evidence bundle created

400 or 422:
  invalid request_id/user_id/plant_id
  request_id not found in chat intent metadata
  inconsistent selected layers/rule modules
  selected_rag_layers non-empty but retrieval_run missing

403 or 404:
  plant does not exist or does not belong to user

409:
  evidence exists for request_id but input plant/user does not match
```

금지 response fields:

```text
prompt
prompt_hash
final_answer
chat_answer
llm_response
model
provider
streaming
companion_ranking
diagnosis
treatment
```

---

## 11. Source Coverage 계약

`source_coverage`는 각 입력 source의 포함 여부를 machine-readable하게 기록한다.

Required shape:

```json
{
  "chat_intent": true,
  "species_profile": true,
  "sensor_snapshot": true,
  "care_logs": true,
  "rule_results": true,
  "retrieved_chunks": true,
  "companion_candidates": false
}
```

Missing reason example:

```json
{
  "retrieved_chunks": false,
  "retrieved_chunks_reason": "missing_retrieval_run_for_request_id"
}
```

규칙:

```text
Missing required chat intent fails.
Missing plant/species fails.
Missing environment snapshots is allowed but represented as null.
Missing care logs is allowed but represented as [].
Missing retrieved chunks when selected_rag_layers is non-empty fails with 400 or 422.
Missing companion candidates is allowed unless later companion tickets require it.
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
      -> POST /evidence/build
      -> EvidenceBuilder
      -> RuleEngine
      -> Postgres reads/writes

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
redis
nginx
vllm
model-server
llm
evidence-worker
chat-worker
generic-worker
```

Backend process invariant:

```text
exactly one foreground uvicorn process
no evidence worker
no chat worker
no Redis consumer
no vLLM/LLM process
no SSE stream process
```

Startup allowed:

```text
import app.main
create FastAPI app
register /evidence/build route
import EvidenceBuilder definitions
```

Startup forbidden:

```text
build evidence for all pending requests
run Rule Engine automatically for all plants
call retrieval for all requests
build prompts
call LLM
connect to Redis/vLLM
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
external LLM API call
vLLM call
Redis call
vector DB service call
external web search
```

Allowed backend env:

```env
APP_NAME=sunshine-backend
APP_ENV=local
DATABASE_URL=postgresql+asyncpg://sunshine:change-me-local-only@postgres:5432/sunshine
EVIDENCE_BUILDER_VERSION=evidence_builder_v1
```

Allowed if prior tickets exist:

```env
MQTT_HOST=mqtt
MQTT_PORT=1883
MQTT_TOPIC=sunshine/+/readings
RETRIEVAL_TOP_K_DEFAULT=5
RETRIEVAL_TOP_K_MAX=10
```

Forbidden env:

```text
REDIS_URL
LLM_BASE_URL
VLLM_BASE_URL
OPENAI_API_KEY
ANTHROPIC_API_KEY
FINAL_ANSWER_MODEL
PROMPT_TEMPLATE_PATH
JINJA_TEMPLATE_DIR
SSE_ENABLED
```

---

## 14. Health / Readiness 계약

### `/healthz`

Ticket 0 liveness remains unchanged.

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

`/healthz` must not:

```text
build evidence
query evidence_bundles
query Postgres
run Rule Engine
check retrieved chunks
check PromptBuilder/LLM/RAG
change response shape
```

### `/readyz`

For Ticket 15, `/readyz` remains dependency readiness.

```json
{
  "status": "ready",
  "service": "sunshine-backend",
  "checks": {
    "database": "ok"
  }
}
```

`/readyz` must not:

```text
require evidence bundles to exist
build evidence
check prompt builder
check LLMPort
check Redis/vLLM
```

---

## 15. Dependency 계약

Allowed dependencies:

```text
existing FastAPI / Pydantic / SQLAlchemy / Alembic / Postgres stack
pytest
httpx
ruff
Python stdlib json/hashlib/dataclasses
```

Forbidden dependencies:

```text
openai
anthropic
vllm
sentence-transformers
torch
tensorflow
onnxruntime
openvino
redis
celery
rq
apscheduler
faiss
chromadb
langchain
llama-index
jinja2
```

주의:

```text
jinja2 is forbidden because prompt templating belongs to Ticket 16.
```

---

## 16. Functional Gate — Executable

Functional Gate는 실행 가능한 절차여야 하며, pass/fail evidence와 failure classification을 남겨야 한다.

Create or update CI/local gate so the following checks are covered.

```bash
#!/usr/bin/env bash
set -euo pipefail

PROJECT="sunshine-ticket15-gate"
IMAGE="sunshine-backend:test"
SERVICES_TXT="/tmp/sunshine_t15_services.txt"

fail() {
  echo
  echo "Ticket 15 Functional Gate: FAIL"
  echo "Failure Classification: $1"
  echo "Evidence: $2"
  docker compose -p "$PROJECT" logs --no-color || true
  docker compose -p "$PROJECT" down -v || true
  exit 1
}

cleanup() {
  docker compose -p "$PROJECT" down -v >/dev/null 2>&1 || true
}
trap cleanup EXIT

printf "[Gate 0] Compose Config Gate\n"
docker compose -p "$PROJECT" config >/tmp/sunshine_t15_compose.yml \
  || fail "compose_config_failure" "docker compose config failed"

printf "[Gate 1] Compose Service Scope Gate\n"
docker compose -p "$PROJECT" config --services | sort | tee "$SERVICES_TXT"
python - <<'PY' || fail "compose_scope_failure" "Ticket 15 may use backend/postgres and existing mqtt services only"
from pathlib import Path
services = set(Path('/tmp/sunshine_t15_services.txt').read_text().splitlines())
allowed = {'backend', 'postgres', 'mqtt', 'mqtt-ingest'}
forbidden = {'redis', 'nginx', 'vllm', 'model-server', 'llm', 'evidence-worker', 'chat-worker', 'generic-worker'}
assert services <= allowed, f'services={services}, allowed={allowed}'
assert {'backend', 'postgres'} <= services, f'backend and postgres are required, got {services}'
assert not services.intersection(forbidden), f'forbidden services: {services.intersection(forbidden)}'
PY

printf "[Gate 2] Required Evidence Files Gate\n"
for path in \
  app/domain/evidence.py \
  app/schemas/evidence.py \
  app/api/evidence.py \
  app/services/evidence_builder.py \
  app/repositories/evidence_repository.py
do
  test -f "$path" || fail "missing_evidence_file" "Required file missing: $path"
done

printf "[Gate 3] Forbidden Future File Gate\n"
for path in \
  app/services/prompt_builder.py \
  app/services/chat_orchestrator.py \
  app/services/chat_care_answer_service.py \
  app/services/llm_port.py \
  app/services/companion_recommendation.py \
  app/services/pest_diagnosis_service.py \
  app/llm
do
  if [ -e "$path" ]; then
    fail "forbidden_future_file" "Forbidden Ticket 15 path exists: $path"
  fi
done

printf "[Gate 4] Forbidden Future Dependency Gate\n"
if grep -R 'openai\|anthropic\|vllm\|sentence_transformers\|torch\|tensorflow\|onnxruntime\|openvino\|redis\|celery\|rq\|apscheduler\|faiss\|chromadb\|langchain\|llama-index\|jinja2' app pyproject.toml >/tmp/sunshine_t15_forbidden_dep.txt 2>/dev/null; then
  cat /tmp/sunshine_t15_forbidden_dep.txt
  fail "forbidden_future_dependency" "Ticket 15 must not include LLM/vector/model/Redis/scheduler/PromptBuilder dependencies"
fi

printf "[Gate 5] Python Quality Gate\n"
ruff check . || fail "lint_failure" "ruff check failed"
ruff format --check . || fail "format_failure" "ruff format --check failed"

printf "[Gate 6] Unit / Contract Test Gate\n"
pytest || fail "test_failure" "pytest failed"

printf "[Gate 7] Docker Build Gate\n"
docker build -t "$IMAGE" . || fail "docker_build_failure" "docker build failed"

printf "[Gate 8] Docker Import Side-Effect Gate\n"
docker run --rm \
  -e APP_NAME=sunshine-backend \
  -e APP_ENV=local \
  "$IMAGE" \
  python -c "import app.main; import app.services.evidence_builder" \
  || fail "docker_import_failure" "imports failed or startup side effect occurred"

printf "[Gate 9] Direct Evidence Hash Gate\n"
docker run --rm "$IMAGE" python - <<'PY' \
  || fail "evidence_hash_failure" "ForwardContext canonical hash must be deterministic"
from app.domain.evidence import compute_evidence_hash

ctx1 = {
    "request_id": "00000000-0000-0000-0000-000000001501",
    "intent": "watering_question",
    "selected_rule_modules": ["watering"],
    "selected_rag_layers": ["species_profile", "care_knowledge"],
    "retrieved_chunks": [{"chunk_id": "a", "rank": 1, "score": 2.0}],
}
ctx2 = {
    "selected_rag_layers": ["species_profile", "care_knowledge"],
    "retrieved_chunks": [{"score": 2.0, "rank": 1, "chunk_id": "a"}],
    "selected_rule_modules": ["watering"],
    "intent": "watering_question",
    "request_id": "00000000-0000-0000-0000-000000001501",
}
assert compute_evidence_hash(ctx1) == compute_evidence_hash(ctx2)
assert compute_evidence_hash(ctx1).startswith("sha256:")
PY

printf "Ticket 15 Functional Gate: PASS\n"
```

---

## 17. Required Tests

Add tests for:

```text
ForwardContext schema requires stable top-level fields.
ForwardContext is strict JSON-serializable.
Missing optional sections are [] or null, not omitted.
EvidenceBuilder verifies plant ownership.
EvidenceBuilder loads chat intent metadata by request_id.
EvidenceBuilder rejects request_id not found.
EvidenceBuilder rejects user_id/plant_id mismatch.
EvidenceBuilder includes species profile.
EvidenceBuilder includes latest/24h/7d sensor snapshots or nulls.
EvidenceBuilder includes last 10 care logs.
EvidenceBuilder includes Rule Engine output and preserves evidence_facts.
EvidenceBuilder loads retrieved chunks when selected_rag_layers is non-empty.
EvidenceBuilder rejects missing retrieval_run when selected_rag_layers is non-empty.
EvidenceBuilder produces deterministic evidence_hash.
Same inputs produce same evidence_hash.
Different retrieved chunks change evidence_hash.
Different rule result changes evidence_hash.
Repeated build for same request_id/user_id/plant_id is idempotent.
Duplicate request_id with different user_id/plant_id returns 409.
POST /evidence/build returns 201 on create.
POST /evidence/build returns 200 on idempotent existing bundle.
POST /evidence/build never returns prompt/final_answer/llm_response fields.
Ticket 15 boundary test blocks PromptBuilder/LLM/final chat/diagnosis/companion leakage.
```

---

## 18. Acceptance Criteria

```text
ruff check . passes
ruff format --check . passes
pytest passes
docker build passes
app.main import has no PromptBuilder/LLM side effects
/evidence/build route exists
/evidence/build persists evidence_bundles
ForwardContext includes required sections
source_coverage is returned and persisted
evidence_hash is deterministic
selected_rag_layers non-empty requires existing Ticket 14 retrieval output
Rule Engine facts are preserved
no prompt is created
no LLM is called
no final answer is generated
no Redis/vLLM/nginx/worker is added
no companion ranking or pest/disease diagnosis is implemented
```

---

## 19. Antigravity 작업 지시 요약

```text
Implement TICKET-015 only.
Follow allowed files exactly.
Create EvidenceBuilder / ForwardContext / EvidenceRepository / POST /evidence/build.
Read existing outputs from Ticket 7/8/11/13/14.
Persist evidence_bundles.
Compute deterministic sha256 evidence_hash from canonical ForwardContext JSON.
Return source_coverage.
Add tests and boundary gates.
Do not implement PromptBuilder, LLMPort, final answer, streaming, Redis, vLLM, companion ranking, or diagnosis.
```
