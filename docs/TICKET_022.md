# TICKET-022 — Evidence Persistence + Audit Query API

## 0. 목표

Sunshine 백엔드에서 생성된 chat answer가 어떤 근거로 만들어졌는지 나중에 조회할 수 있도록 evidence를 저장하고, 내부 디버그용 조회 API를 제공한다.

이 티켓은 새로운 답변을 생성하지 않는다.  
이 티켓은 새로운 RAG/LLM/prompt 정책을 만들지 않는다.  
이 티켓은 Polaris, GPU telemetry, public admin dashboard를 만들지 않는다.

Ticket 22의 책임은 아래까지만이다.

```text
successful chat answer
  -> request/question/intent 저장
  -> selected rules/RAG layers 저장
  -> sensor snapshot/rule results/retrieved chunks 저장
  -> prompt/prompt_hash/response 저장
  -> GET /chat-runs/{request_id}/evidence 로 조회
```

---

## 1. Ticket Identity

### Ticket ID

```text
TICKET-022
```

### Name

```text
Evidence Persistence + Audit Query API
```

### Goal

```text
Persist and expose a read-only internal evidence view explaining why a chat answer was generated.
```

### Core output

```text
AuditChatRunRecord
ChatRunEvidenceView
AuditRepository
AuditQueryService
GET /chat-runs/{request_id}/evidence
chat success audit persistence hook
prompt_hash integrity check
```

### Strict non-goal

```text
no new answer generation
no new retrieval strategy
no new prompt policy
no new LLM provider
no new recommendation algorithm
no Polaris/MIR tracing
no GPU/KV/NCCL telemetry
no system_facts emitter
no public admin dashboard
no auth redesign
no streaming
no Redis worker
```

---

## 2. 주변 티켓과의 연결

Ticket 22는 이전 chat answer pipeline의 결과를 저장하고 조회하는 내부 audit/read-model boundary다.

```text
Ticket 13:
  intent, selected_rule_modules, selected_rag_layers 산출

Ticket 14:
  retrieved chunks와 source metadata 제공

Ticket 15:
  ForwardContext/evidence bundle 생성

Ticket 16:
  prompt/prompt_hash 입력 제공

Ticket 17:
  LLMResponse provider/model/tokens/latency metadata 제공

Ticket 18:
  care answer chat path 생성

Ticket 19:
  pest_reference answer chat path 생성

Ticket 21:
  companion recommendation chat path 생성

Ticket 22:
  위 successful chat answer의 evidence를 저장하고 request_id로 조회
```

Ticket 22의 역할:

```text
request_id
  -> persisted chat run evidence
  -> replay/debug payload
```

금지:

```text
새 답변 생성
새 검색 수행
prompt 재생성
LLM 재호출
GPU telemetry 수집
Polaris 추적
public dashboard 생성
```

---

## 3. 수정/생성 허용 파일

### 수정 가능한 기존 파일

```text
app/services/chat_orchestrator.py
app/domain/chat.py
app/main.py
```

`app/services/chat_orchestrator.py`와 `app/domain/chat.py`는 successful chat answer가 audit persistence boundary를 호출하도록 하는 범위에서만 수정한다.

`app/main.py`는 아래만 허용한다.

```text
include chat-runs evidence router
/healthz 변경 금지
/readyz 생성 금지
startup dependency check 추가 금지
```

### 생성 가능한 새 파일

```text
app/api/chat_runs.py
app/services/audit_query_service.py
app/repositories/audit_repository.py
app/domain/audit.py

tests/test_audit_persistence.py
tests/test_audit_query_api.py
tests/fixtures/audit_fixtures.py
```

### 조건부 migration 허용

```text
alembic/versions/<ticket22_audit_fields>.py
```

허용 조건:

```text
기존 schema가 Ticket 22 최소 audit 필드를 저장할 수 없을 때만 허용
append-only audit field 추가만 허용
unrelated schema expansion 금지
```

허용 대상:

```text
chat_requests
llm_runs
recommendation_evidence
retrieved_chunks linkage
```

금지 migration:

```text
Polaris/system_facts tables
GPU/KV/NCCL telemetry tables
new retrieval index tables
new prompt policy tables
admin dashboard tables
auth redesign tables
```

---

## 4. 금지 파일/디렉터리

아래 경로는 생성하거나 수정하지 않는다.

```text
app/services/polaris_auditor.py
app/services/gpu_telemetry.py
app/services/system_facts_emitter.py
app/services/kv_cache_telemetry.py

app/llm/vllm_client.py
app/llm/openai_client.py
app/llm/anthropic_client.py

app/retrieval/reranker.py
app/retrieval/crag.py

app/vision/
app/mqtt/
app/workers/

Dockerfile
docker-compose.yml
.env.example
.github/workflows/
```

규칙:

```text
Ticket 22 must not introduce real LLM providers, GPU/runtime telemetry, Polaris, new retrieval methods, workers, or deployment topology.
```

---

## 5. Audit Domain 계약

`app/domain/audit.py`를 생성한다.

필수 개념:

```python
ChatRunKind = Literal[
    "care_answer",
    "pest_reference",
    "companion_recommendation",
]
```

필수 record:

```text
AuditChatRunRecord:
  request_id
  plant_id
  question
  intent
  profile
  run_kind
  selected_rule_modules
  selected_rag_layers
  sensor_snapshot
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

필수 view:

```text
ChatRunEvidenceView:
  request_id
  plant_id
  question
  intent
  profile
  run_kind
  selected_rule_modules
  selected_rag_layers
  sensor_snapshot
  rule_results
  retrieved_chunks
  prompt_hash
  prompt
  response_text
  provider
  model
  tokens_in
  tokens_out
  latency_ms
```

규칙:

```text
prompt_hash must match prompt.
response_text must match returned answer.
retrieved_chunks must preserve chunk_id and score.
rule_results must preserve rule_name and evidence.
selected layers/modules must match the branch that generated the answer.
```

금지:

```text
fresh retrieval at read time
prompt regeneration at read time
LLM recall at read time
fabricating missing evidence
summary-only storage that discards prompt/response/evidence
```

---

## 6. Audit Repository 계약

`app/repositories/audit_repository.py`를 생성한다.

필수 shape:

```python
class AuditRepository:
    async def save_chat_run(self, record: AuditChatRunRecord) -> None:
        ...

    async def get_chat_run_evidence(
        self,
        request_id: str,
    ) -> ChatRunEvidenceView | None:
        ...
```

필수 동작:

```text
1. Save exactly one audit run per request_id.
2. request_id is unique.
3. Duplicate identical request_id is idempotent.
4. Duplicate conflicting request_id raises conflict.
5. get by request_id returns complete evidence view.
6. Missing request_id returns None.
```

금지 동작:

```text
local JSON file audit
local SQLite fallback
log-only audit storage
background persistence worker
external audit service call
```

---

## 7. Audit Query Service 계약

`app/services/audit_query_service.py`를 생성한다.

필수 책임:

```text
request_id validation
repository read
missing request -> not found error
incomplete evidence -> controlled failure
prompt_hash integrity validation
ChatRunEvidenceView 반환
```

금지 책임:

```text
새 답변 생성
retrieval 재실행
PromptBuilder 재실행
LLMPort 호출
Polaris/GPU telemetry 조회
cross-user auth policy redesign
```

---

## 8. API 계약 — GET /chat-runs/{request_id}/evidence

### Endpoint

```http
GET /chat-runs/{request_id}/evidence
```

### Response

```json
{
  "request_id": "uuid",
  "plant_id": "uuid",
  "question": "물 줘야 해?",
  "intent": "watering_question",
  "profile": "P1",
  "run_kind": "care_answer",
  "selected_rule_modules": ["watering"],
  "selected_rag_layers": ["species_profile", "care_knowledge"],
  "sensor_snapshot": {
    "snapshot_id": "snapshot-001",
    "soil_moisture_pct": 72,
    "light_lux": 420
  },
  "rule_results": [
    {
      "rule_name": "watering",
      "decision": "no_watering",
      "evidence": {
        "soil_moisture_pct": 72
      }
    }
  ],
  "retrieved_chunks": [
    {
      "chunk_id": "chunk-care-001",
      "score": 0.82,
      "source": "species_profile",
      "text": "..."
    }
  ],
  "prompt_hash": "sha256hex",
  "prompt": "full prompt text",
  "response_text": "[결론]...",
  "provider": "mock",
  "model": "mock-llm-v1",
  "tokens_in": null,
  "tokens_out": null,
  "latency_ms": 0
}
```

### Error responses

```text
400 invalid_request
404 chat_run_not_found
500 audit_query_failure
500 audit_integrity_failure
```

규칙:

```text
Endpoint is internal/debug only.
It may return full prompt and full response.
It must return persisted evidence, not freshly generated evidence.
If user/auth scoping already exists, reuse it.
If user/auth scoping does not exist, do not redesign auth in Ticket 22.
Ticket 25 owns user scope.
```

---

## 9. Persistence Coverage 계약

아래 successful chat answer는 모두 evidence 조회가 가능해야 한다.

```text
Ticket 18 care answer:
  watering_question
  light_question
  humidity_question
  temperature_question
  species_care_question

Ticket 19 pest reference:
  pest_reference_question

Ticket 21 companion recommendation:
  companion_plant_question
```

필수 저장 필드:

```text
request_id
plant_id
question
intent
profile
run_kind
selected_rule_modules
selected_rag_layers
sensor_snapshot
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

성공 조건:

```text
successful chat response를 반환하기 전에 audit persistence가 성공해야 한다.
Persistence failure 시 성공 응답을 반환하지 않는다.
```

---

## 10. Runtime 계약

허용 runtime topology:

```text
FastAPI backend
  -> chat path persists AuditChatRunRecord
  -> GET /chat-runs/{request_id}/evidence
  -> AuditQueryService
  -> AuditRepository
  -> JSON evidence view
```

Allowed long-lived containers:

```text
existing backend
existing postgres if already introduced
existing mqtt/mqtt-ingest if already introduced
```

Forbidden new long-lived containers:

```text
redis
auditor-worker
gpu-telemetry-worker
polaris
vllm
model-server
nginx
```

Process invariant:

```text
no background auditor process
no GPU telemetry collector
no Redis consumer
no vLLM event subscriber
no Polaris MIR tracing
no streaming audit feed
```

Network invariant:

```text
May expose exactly one new route:
  GET /chat-runs/{request_id}/evidence

Must not expose:
  SSE endpoint
  WebSocket endpoint
  admin dashboard route
  telemetry endpoint
  Polaris endpoint
```

Env invariant:

```text
No new env vars required.
```

Forbidden env:

```text
AUDIT_SERVICE_URL
POLARIS_*
GPU_TELEMETRY_*
SYSTEM_FACTS_*
VLLM_*
OPENAI_*
ANTHROPIC_*
REDIS_*
MQTT_*
SSE_*
```

`/healthz` rule:

```text
Do not modify GET /healthz.
Do not add or modify GET /readyz.
If /readyz already exists from prior DB ticket, leave it unchanged.
```

---

## 11. Functional Gate — Executable

### Required local gate script

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "[Gate 0] Scope boundary"
for path in \
  app/services/polaris_auditor.py \
  app/services/gpu_telemetry.py \
  app/services/system_facts_emitter.py \
  app/services/kv_cache_telemetry.py \
  app/llm/vllm_client.py \
  app/llm/openai_client.py \
  app/llm/anthropic_client.py \
  app/retrieval/reranker.py \
  app/retrieval/crag.py \
  app/workers
 do
  if [ -e "$path" ]; then
    echo "forbidden_path: $path"
    exit 1
  fi
 done

echo "[Gate 1] Python quality"
ruff check \
  app/api/chat_runs.py \
  app/services/audit_query_service.py \
  app/repositories/audit_repository.py \
  app/domain/audit.py \
  tests/test_audit_persistence.py \
  tests/test_audit_query_api.py

ruff format --check \
  app/api/chat_runs.py \
  app/services/audit_query_service.py \
  app/repositories/audit_repository.py \
  app/domain/audit.py \
  tests/test_audit_persistence.py \
  tests/test_audit_query_api.py

echo "[Gate 2] Unit and API tests"
pytest -q tests/test_audit_persistence.py tests/test_audit_query_api.py

echo "[Gate 3] No future feature leakage"
python - <<'PY'
from pathlib import Path

targets = [
    Path("app/api/chat_runs.py"),
    Path("app/services/audit_query_service.py"),
    Path("app/repositories/audit_repository.py"),
    Path("app/domain/audit.py"),
]

for path in targets:
    text = path.read_text()
    forbidden = [
        "openai", "anthropic", "vllm", "StreamingResponse",
        "WebSocket", "redis", "Polaris", "MIR", "state_ownership",
        "progress_killed_at", "block_reuse_provenance", "kv_cache",
        "NCCL", "cuda", "gpu_telemetry", "system_facts_emitter",
        "rerank", "CRAG", "Self-RAG",
    ]
    hits = [x for x in forbidden if x in text]
    assert not hits, f"{path}: forbidden leakage: {hits}"

print("future_feature_leakage_check: pass")
PY

echo "[Gate 4] Audit round-trip"
python - <<'PY'
import asyncio
from tests.fixtures.audit_fixtures import make_in_memory_audit_repository, make_care_audit_record

async def main() -> None:
    repo = make_in_memory_audit_repository()
    record = make_care_audit_record(request_id="req-audit-roundtrip-001")
    await repo.save_chat_run(record)
    view = await repo.get_chat_run_evidence("req-audit-roundtrip-001")
    assert view is not None
    assert view.request_id == record.request_id
    assert view.prompt == record.prompt
    assert view.prompt_hash == record.prompt_hash
    assert view.response_text == record.response_text
    assert view.rule_results == record.rule_results
    assert view.retrieved_chunks == record.retrieved_chunks

asyncio.run(main())
print("audit_roundtrip: pass")
PY

echo "[Gate 5] Prompt hash integrity"
python - <<'PY'
from tests.fixtures.audit_fixtures import make_care_audit_record
from app.llm.hash import stable_prompt_hash

record = make_care_audit_record(request_id="req-hash-001")
assert record.prompt_hash == stable_prompt_hash(record.prompt)
assert record.prompt_hash != stable_prompt_hash(record.prompt + " tampered")
print("prompt_hash_integrity: pass")
PY

echo "[Gate 6] Docker health regression"
docker build -t sunshine-backend:ticket22 .
docker rm -f sunshine-backend-ticket22 >/dev/null 2>&1 || true
docker run -d \
  --name sunshine-backend-ticket22 \
  -p 8000:8000 \
  -e APP_NAME=sunshine-backend \
  -e APP_ENV=local \
  sunshine-backend:ticket22

cleanup() { docker rm -f sunshine-backend-ticket22 >/dev/null 2>&1 || true; }
trap cleanup EXIT

for i in $(seq 1 30); do
  if curl -fsS http://localhost:8000/healthz >/tmp/healthz.ticket22.json; then
    break
  fi
  sleep 1
done

test -s /tmp/healthz.ticket22.json
python - <<'PY'
import json
from pathlib import Path
body = json.loads(Path("/tmp/healthz.ticket22.json").read_text())
assert body == {"status": "ok", "service": "sunshine-backend"}, body
print("healthz_liveness_regression: pass")
PY

echo "[Gate 7] Audit query API"
curl -fsS \
  -X POST "http://localhost:8000/plants/plant-001/chat" \
  -H "Content-Type: application/json" \
  -d '{"request_id":"req-audit-api-001","question":"물 줘야 해?","locale":"ko-KR"}' \
  > /tmp/ticket22.chat.response.json

curl -fsS \
  "http://localhost:8000/chat-runs/req-audit-api-001/evidence" \
  > /tmp/ticket22.audit.response.json

python - <<'PY'
import json
from pathlib import Path
from app.llm.hash import stable_prompt_hash

body = json.loads(Path("/tmp/ticket22.audit.response.json").read_text())
assert body["request_id"] == "req-audit-api-001"
assert body["plant_id"] == "plant-001"
assert body["prompt"]
assert body["response_text"]
assert body["prompt_hash"] == stable_prompt_hash(body["prompt"])
assert body["provider"] == "mock"
assert body["model"] == "mock-llm-v1"
for section in ["[결론]", "[근거]", "[행동]", "[주의]"]:
    assert section in body["response_text"]
print("audit_query_api: pass")
PY

echo "[Gate 8] Missing request_id returns 404"
curl -sS \
  -o /tmp/ticket22.audit.missing.json \
  -w "%{http_code}" \
  "http://localhost:8000/chat-runs/does-not-exist/evidence" \
  > /tmp/ticket22.audit.missing.status

python - <<'PY'
from pathlib import Path
import json
status = Path("/tmp/ticket22.audit.missing.status").read_text().strip()
body = json.loads(Path("/tmp/ticket22.audit.missing.json").read_text())
assert status == "404", (status, body)
assert body["error"] == "chat_run_not_found"
print("missing_request_404: pass")
PY

echo "[Gate 9] Readiness boundary"
if grep -R "readyz" app tests; then
  echo "forbidden_readyz"
  exit 1
fi

echo "Ticket 22 Functional Gate: PASS"
```

---

## 12. Required Tests

```text
test_audit_repository_saves_chat_run
test_audit_repository_gets_chat_run_by_request_id
test_audit_repository_missing_request_returns_none
test_audit_repository_duplicate_identical_request_is_idempotent
test_audit_repository_duplicate_conflicting_request_fails
test_audit_record_preserves_question_intent_profile
test_audit_record_preserves_selected_rule_modules
test_audit_record_preserves_selected_rag_layers
test_audit_record_preserves_sensor_snapshot
test_audit_record_preserves_rule_results
test_audit_record_preserves_retrieved_chunks
test_audit_record_preserves_prompt_and_prompt_hash
test_audit_record_preserves_response_text
test_audit_query_api_happy_path
test_audit_query_api_missing_request_id_returns_404
test_audit_query_api_prompt_hash_matches_prompt
test_chat_success_requires_audit_persistence
test_no_polaris_or_gpu_telemetry_imported
test_healthz_contract_unchanged
test_no_readyz_added_by_ticket22
```

---

## 13. Acceptance Criteria

```text
GET /chat-runs/{request_id}/evidence exists.
Every successful chat answer has request_id.
Audit persistence stores question, intent, selected rules, selected RAG layers.
Audit persistence stores sensor snapshot when available.
Audit persistence stores rule results.
Audit persistence stores retrieved chunks.
Audit persistence stores prompt and prompt_hash.
Audit persistence stores response_text.
Audit persistence stores provider/model metadata.
Audit endpoint returns complete evidence by request_id.
Missing request_id returns 404.
prompt_hash matches persisted prompt.
response_text matches returned answer.
No Polaris/MIR tracing is implemented.
No GPU/KV/NCCL telemetry is implemented.
No real LLM provider is implemented.
No streaming is implemented.
No Redis/worker/vLLM is introduced.
No retrieval strategy is changed.
/healthz remains liveness-only.
/readyz is not introduced or modified by this ticket.
pytest passes.
ruff passes.
Docker smoke and curl audit API gates pass.
```
