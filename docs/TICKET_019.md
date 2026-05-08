# TICKET-019 — Pest/Disease Reference Answer Guardrail

## 0. 목표

Sunshine 백엔드의 기존 chat API에서 병충해/질병 관련 질문을 **참고용 답변(reference-only answer)** 으로만 처리한다.

이 티켓은 확정 진단을 만들지 않는다.  
이 티켓은 이미지 기반 병충해 판정을 하지 않는다.  
이 티켓은 농약/약제/치료법을 지시하지 않는다.  
이 티켓은 companion recommendation을 만들지 않는다.

Ticket 19의 책임은 아래까지만이다.

```text
pest_reference_question
  -> pest_disease_reference / species_profile RAG evidence 사용
  -> reference-only ForwardContext / prompt 경로 사용
  -> MockLLM / LLMPort 호출
  -> non-diagnostic answer validation
  -> fixed answer response 반환
```

---

## 1. Ticket Identity

### Ticket ID

```text
TICKET-019
```

### Name

```text
Pest/Disease Reference Answer Guardrail
```

### Goal

```text
Allow pest/disease-related chat questions to return safe reference-only answers without diagnosis or treatment claims.
```

### Core output

```text
pest_reference_question chat branch
pest reference guardrail service
reference-only safety policy
non-diagnostic answer validation
fixed answer format preservation
safety flags in response
pest_disease_reference RAG layer usage
```

### Strict non-goal

```text
no definitive diagnosis
no image-based disease/pest diagnosis
no pest classifier
no disease classifier
no health classifier
no pesticide recommendation
no treatment recommendation
no companion recommendation
no real LLM provider
no SSE streaming
no Redis queue
no worker
no vLLM
no new DB migration
no new RAG architecture
no reranker
no CRAG
no Self-RAG
no HyDE
no P3 execution
no Polaris
no GPU telemetry
```

---

## 2. 주변 티켓과의 연결

Ticket 19는 Ticket 18의 chat API에서 **pest_reference_question branch만 해제**한다.

```text
Ticket 13:
  pest_reference_question intent를 분류

Ticket 14:
  pest_disease_reference, species_profile chunk 검색

Ticket 15:
  retrieved chunks를 ForwardContext에 포함

Ticket 16:
  pest/disease caution prompt 생성

Ticket 17:
  MockLLM / LLMPort로 fixed-format response 생성

Ticket 18:
  POST /plants/{plant_id}/chat orchestration 제공

Ticket 19:
  pest_reference_question을 reference-only answer로 허용하고 guardrail 검증

Ticket 20/21:
  companion compatibility/recommendation은 여전히 나중
```

Ticket 19의 역할:

```text
symptom / pest / disease question
  -> reference evidence
  -> caution-heavy prompt/answer
  -> guardrail validation
  -> safe fixed-format response
```

금지:

```text
사진 보고 병명 확정
병충해 확정 진단
농약/약제/치료법 지시
companion 식물 추천
실제 vision model 호출
real LLM adapter 추가
```

---

## 3. 수정/생성 허용 파일

### 생성 가능한 새 파일

```text
app/services/pest_reference_guardrail.py
app/domain/pest_reference.py

tests/test_pest_reference_guardrail.py
tests/test_chat_pest_reference_api.py
tests/fixtures/pest_reference_fixtures.py
```

### 수정 가능한 기존 파일

```text
app/api/chat.py
app/services/chat_orchestrator.py
app/domain/chat.py
app/services/__init__.py
app/domain/__init__.py
app/main.py
```

`app/main.py` 수정은 아래까지만 허용한다.

```text
existing chat router registration 유지
/healthz 변경 금지
/readyz 생성 금지
startup dependency check 추가 금지
```

`app/api/chat.py`, `app/services/chat_orchestrator.py`, `app/domain/chat.py` 수정은 아래까지만 허용한다.

```text
pest_reference_question을 Ticket 19 path로 연결
Ticket 18에서 pest_reference_question을 unsupported 처리하던 부분만 해제
companion_plant_question은 여전히 unsupported/deferred
unknown_question은 여전히 safe fallback 또는 unsupported
기존 fixed answer response schema 유지
```

### 조건부 persistence 허용

기존 Ticket 18 persistence 경로가 있으면 재사용한다.

허용 metadata:

```text
request_id
plant_id
question
intent = pest_reference_question
selected_rag_layers = ["pest_disease_reference", "species_profile"]
retrieved_chunk_ids
prompt_hash
response_text
provider
model
safety.reference_only = true
safety.definitive_diagnosis = false
safety.image_diagnosis = false
safety.pesticide_instruction = false
```

금지:

```text
new migration
new tables
local JSON audit file
SQLite fallback
logs-only persistence
```

기존 metadata/json field가 없으면 migration을 만들지 말고 별도 schema-fix ticket으로 분리한다.

---

## 4. 금지 파일/디렉터리

아래 경로는 생성하거나 수정하지 않는다.

```text
app/vision/
app/vision/disease_classifier.py
app/vision/pest_classifier.py

app/services/companion_filter.py
app/services/companion_recommendation.py

app/retrieval/reranker.py
app/retrieval/crag.py

app/llm/vllm_client.py
app/llm/openai_client.py
app/llm/anthropic_client.py

app/workers/
app/mqtt/

alembic/
migrations/
Dockerfile
docker-compose.yml
.env.example
.github/workflows/
```

규칙:

```text
Ticket 19 must not introduce image diagnosis, treatment recommendation, production LLM, new infra, schema migration, or companion recommendation logic.
```

---

## 5. Pest Reference Policy 계약

아래 파일을 생성한다.

```text
app/domain/pest_reference.py
```

필수 개념:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class PestReferencePolicy:
    allow_definitive_diagnosis: bool = False
    allow_image_diagnosis_claim: bool = False
    allow_pesticide_instruction: bool = False
    require_reference_language: bool = True
    require_observation_or_expert_caution: bool = True


@dataclass(frozen=True)
class PestReferenceValidationResult:
    ok: bool
    violations: tuple[str, ...]
```

규칙:

```text
reference_only must be true.
definitive_diagnosis must be false.
image_diagnosis must be false.
pesticide_instruction must be false.
answer must recommend observation or expert confirmation when uncertainty remains.
```

---

## 6. Guardrail Service 계약

아래 파일을 생성한다.

```text
app/services/pest_reference_guardrail.py
```

필수 shape:

```python
class PestReferenceGuardrail:
    def validate_answer(self, answer_text: str) -> PestReferenceValidationResult:
        ...

    def assert_safe(self, answer_text: str) -> None:
        ...
```

Suggested exception:

```python
class PestReferenceGuardrailError(ValueError):
    ...
```

필수 동작:

```text
1. Reject definitive diagnosis claims.
2. Reject image diagnosis claims.
3. Reject pesticide/treatment commands.
4. Accept reference-only possibility language.
5. Require caution language.
6. Return structured violations.
```

---

## 7. 금지/허용 문장 계약

### 확정 진단 금지

금지 예시:

```text
이 사진은 응애입니다
응애입니다
진딧물입니다
흰가루병입니다
병입니다
확실히 병충해입니다
```

허용 예시:

```text
응애 피해에서 볼 수 있는 증상과 비슷할 수 있습니다
흰가루병 가능성을 참고할 수 있습니다
사진만으로는 확정할 수 없습니다
```

### 이미지 판정 주장 금지

금지 예시:

```text
사진을 보니 응애입니다
이미지 분석 결과 병입니다
사진 기반으로 진단했습니다
```

허용 예시:

```text
현재 티켓에서는 이미지 기반 진단을 수행하지 않습니다
제공된 설명과 참고 지식 기준으로만 안내합니다
```

### 약제/치료 지시 금지

금지 예시:

```text
약을 뿌리세요
살충제를 사용하세요
농약을 처리하세요
이 약제를 쓰세요
치료하세요
```

허용 예시:

```text
잎 뒷면, 점성, 번짐 여부를 추가 관찰하세요
증상이 지속되면 전문가나 지역 식물 병해충 자료를 확인하세요
상태 악화나 전염 의심 시 신중히 분리 관찰하세요
```

---

## 8. API 계약 — POST /plants/{plant_id}/chat

Ticket 19는 새 endpoint를 만들지 않는다.  
Ticket 18의 기존 endpoint에서 pest branch만 허용한다.

### Endpoint

```http
POST /plants/{plant_id}/chat
Content-Type: application/json
```

### Request

```json
{
  "request_id": "00000000-0000-0000-0000-000000001901",
  "question": "잎에 하얀 점이 있어. 병충해야?",
  "locale": "ko-KR"
}
```

### Response

```json
{
  "request_id": "00000000-0000-0000-0000-000000001901",
  "plant_id": "00000000-0000-0000-0000-000000001903",
  "intent": "pest_reference_question",
  "profile": "P2",
  "answer": {
    "text": "[결론]\n...\n\n[근거]\n...\n\n[행동]\n...\n\n[주의]\n...",
    "sections": {
      "결론": "병충해 가능성을 참고할 수 있지만 확정 진단은 아닙니다.",
      "근거": "retrieved reference evidence 기반 설명",
      "행동": "추가 관찰 포인트 안내",
      "주의": "사진 기반 판정이 아니며 증상 지속/악화 시 전문가 확인 권고"
    }
  },
  "evidence": {
    "rule_result_ids": [],
    "retrieved_chunk_ids": ["chunk-id"],
    "prompt_hash": "sha256-or-hex",
    "model": "mock-llm-v1",
    "provider": "mock"
  },
  "safety": {
    "reference_only": true,
    "definitive_diagnosis": false,
    "image_diagnosis": false,
    "pesticide_instruction": false
  }
}
```

필수 동작:

```text
Classify as pest_reference_question.
Use profile P2.
Use RAG layers pest_disease_reference and species_profile.
Build evidence through existing EvidenceBuilder path.
Build caution-heavy prompt through existing PromptBuilder path.
Call existing LLMPort / MockLLM.
Validate fixed sections.
Run PestReferenceGuardrail before returning success.
Persist through existing Ticket 18 persistence path when available.
Return safety flags.
```

금지 response behavior:

```text
diagnosis field
disease_name field as definitive label
pesticide_name
treatment_instruction
image_diagnosis_result
companion_recommendations
```

---

## 9. Prompt / Answer 계약

Required answer sections:

```text
[결론]
[근거]
[행동]
[주의]
```

Prompt must include:

```text
이 답변은 참고용이다.
확정 진단을 하지 마라.
사진 기반 병충해 판정을 했다고 말하지 마라.
농약/약제/치료법을 단정적으로 지시하지 마라.
RAG evidence에 있는 일반적 증상, 가능성, 관찰 포인트만 설명하라.
증상이 지속되거나 악화되면 전문가 확인을 권고하라.
```

`[주의]` must include:

```text
확정 진단 아님
사진 기반 판정 아님
증상 지속/악화 시 전문가 확인 또는 추가 관찰 권고
```

---

## 10. Runtime 계약

Allowed runtime topology:

```text
host
  -> backend container
      -> uvicorn app.main:app
      -> GET /healthz
      -> POST /plants/{plant_id}/chat
      -> ChatOrchestrator
      -> pest_reference_question branch
      -> Retriever / EvidenceBuilder / PromptBuilder / MockLLM
      -> PestReferenceGuardrail
      -> existing persistence path
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
pest-worker
vision-worker
generic-worker
```

Backend process invariant:

```text
exactly one existing backend process
no new worker
no scheduler
no model warmup
no image model loading
no external diagnosis API
```

Guardrail invariant:

```text
pure
deterministic
side-effect free
network-free
DB-free
filesystem-free
model-free
```

---

## 11. Network / Env 계약

Ticket 19 must introduce:

```text
0 new ports
0 new Docker services
0 new external HTTP calls
0 new service discovery names
0 new compose changes
```

Forbidden imports/usages in new Ticket 19 code:

```text
httpx
requests
aiohttp
openai
anthropic
vllm
grpc
socket
torch
tensorflow
onnx
cv2
PIL.Image
```

Forbidden new env vars:

```text
PEST_MODEL_*
DISEASE_MODEL_*
VISION_*
LLM_*
VLLM_*
OPENAI_*
ANTHROPIC_*
REDIS_*
MQTT_*
SSE_*
```

Allowed:

```text
Existing DB env only through existing persistence/repository boundary.
```

---

## 12. Health / Readiness 계약

Ticket 19 must not modify:

```http
GET /healthz
```

Ticket 19 must not add or modify:

```http
GET /readyz
```

Rules:

```text
/healthz remains liveness-only.
/readyz is not introduced by this ticket.
Ticket 19 adds no external dependency requiring readiness check.
```

---

## 13. Functional Gate — Executable

Create or run a gate equivalent to:

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "[Gate 0] Scope boundary"
git diff --name-only origin/main...HEAD | tee /tmp/ticket19_changed_files.txt || true

python - <<'PY'
from pathlib import Path

allowed = {
    "app/services/pest_reference_guardrail.py",
    "app/domain/pest_reference.py",
    "app/api/chat.py",
    "app/services/chat_orchestrator.py",
    "app/domain/chat.py",
    "app/main.py",
    "app/services/__init__.py",
    "app/domain/__init__.py",
    "tests/test_pest_reference_guardrail.py",
    "tests/test_chat_pest_reference_api.py",
    "tests/fixtures/pest_reference_fixtures.py",
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
    "app/vision/disease_classifier.py",
    "app/vision/pest_classifier.py",
    "app/services/companion_filter.py",
    "app/services/companion_recommendation.py",
    "app/retrieval/reranker.py",
    "app/retrieval/crag.py",
    "app/llm/vllm_client.py",
    "app/llm/openai_client.py",
    "app/llm/anthropic_client.py",
}

changed = [line.strip() for line in Path("/tmp/ticket19_changed_files.txt").read_text().splitlines() if line.strip()]
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

print("ticket19_scope_boundary: pass")
PY

echo "[Gate 1] Python quality"
ruff check app/services/pest_reference_guardrail.py app/domain/pest_reference.py tests/test_pest_reference_guardrail.py tests/test_chat_pest_reference_api.py
ruff format --check app/services/pest_reference_guardrail.py app/domain/pest_reference.py tests/test_pest_reference_guardrail.py tests/test_chat_pest_reference_api.py

echo "[Gate 2] Tests"
pytest -q tests/test_pest_reference_guardrail.py tests/test_chat_pest_reference_api.py

echo "[Gate 3] No future-feature leakage"
python - <<'PY'
from pathlib import Path

targets = [
    Path("app/services/pest_reference_guardrail.py"),
    Path("app/domain/pest_reference.py"),
    Path("app/api/chat.py"),
    Path("app/services/chat_orchestrator.py"),
]

for path in targets:
    if not path.exists():
        continue
    text = path.read_text()
    forbidden = [
        "httpx", "requests", "aiohttp", "openai", "anthropic", "vllm",
        "grpc", "socket", "StreamingResponse", "EventSourceResponse",
        "WebSocket", "torch", "tensorflow", "onnx", "cv2", "PIL.Image",
        "disease_classifier", "pest_classifier", "NCCL", "Polaris",
        "rerank", "CRAG", "Self-RAG",
    ]
    hits = [x for x in forbidden if x in text]
    assert not hits, f"{path}: forbidden leakage: {hits}"

print("ticket19_no_future_feature_leakage: pass")
PY

echo "[Gate 4] Guardrail rejects unsafe answers"
python - <<'PY'
from app.services.pest_reference_guardrail import PestReferenceGuardrail, PestReferenceGuardrailError

guardrail = PestReferenceGuardrail()

bad_answers = [
    "[결론]\n이 사진은 응애입니다.\n[근거]\n...\n[행동]\n...\n[주의]\n...",
    "[결론]\n흰가루병입니다.\n[근거]\n...\n[행동]\n...\n[주의]\n...",
    "[결론]\n가능성이 있습니다.\n[근거]\n...\n[행동]\n약을 뿌리세요.\n[주의]\n...",
]

for answer in bad_answers:
    try:
        guardrail.assert_safe(answer)
    except PestReferenceGuardrailError:
        continue
    raise AssertionError(f"expected rejection: {answer}")

print("unsafe_answers_rejected: pass")
PY

echo "[Gate 5] Guardrail accepts reference-only answer"
python - <<'PY'
from app.services.pest_reference_guardrail import PestReferenceGuardrail

answer = '''
[결론]
잎의 하얀 점은 일부 병해충 또는 환경 스트레스 사례에서 비슷하게 보일 수 있습니다.

[근거]
제공된 참고 문서에는 잎 표면의 점, 번짐, 잎 뒷면 흔적을 함께 관찰하라고 되어 있습니다.

[행동]
잎 뒷면, 번짐 속도, 끈적임 여부를 추가로 관찰하고 기록하세요.

[주의]
이 답변은 확정 진단이 아니며 사진 기반 판정을 수행하지 않았습니다. 증상이 지속되거나 악화되면 전문가 확인을 권장합니다.
'''

result = PestReferenceGuardrail().validate_answer(answer)
assert result.ok, result.violations

print("reference_only_answer_accepted: pass")
PY

echo "[Gate 6] Docker health regression"
docker build -t sunshine-backend:ticket19 .
docker rm -f sunshine-backend-ticket19 >/dev/null 2>&1 || true
docker run -d --name sunshine-backend-ticket19 -p 8000:8000 -e APP_NAME=sunshine-backend -e APP_ENV=local sunshine-backend:ticket19

cleanup() {
  docker rm -f sunshine-backend-ticket19 >/dev/null 2>&1 || true
}
trap cleanup EXIT

for i in $(seq 1 30); do
  if curl -fsS http://localhost:8000/healthz >/tmp/healthz.ticket19.json; then
    break
  fi
  sleep 1
done

python - <<'PY'
import json
from pathlib import Path

body = json.loads(Path("/tmp/healthz.ticket19.json").read_text())
assert body == {"status": "ok", "service": "sunshine-backend"}, body
print("healthz_liveness_regression: pass")
PY

echo "[Gate 7] /readyz boundary"
if grep -R "readyz" app tests; then
  echo "forbidden_readyz"
  exit 1
fi

echo "Ticket 19 Functional Gate: PASS"
```

---

## 14. Required Tests

Add tests for:

```text
test_guardrail_rejects_definitive_pest_diagnosis
test_guardrail_rejects_definitive_disease_diagnosis
test_guardrail_rejects_image_diagnosis_claim
test_guardrail_rejects_pesticide_or_treatment_command
test_guardrail_accepts_reference_only_answer
test_guardrail_requires_caution_language
test_pest_reference_chat_returns_fixed_format_answer
test_pest_reference_chat_uses_p2_profile
test_pest_reference_chat_uses_pest_disease_reference_layer
test_pest_reference_chat_response_has_safety_flags
test_pest_reference_chat_does_not_claim_image_diagnosis
test_pest_reference_chat_does_not_recommend_pesticide
test_companion_intent_still_deferred
test_no_vision_classifier_imported
test_healthz_contract_unchanged
test_no_readyz_added_by_ticket19
```

---

## 15. Acceptance Criteria

Ticket 19 passes only if:

```text
pest_reference_question is supported through existing chat API
answer follows [결론][근거][행동][주의]
answer is explicitly reference-only
answer does not claim definitive diagnosis
answer does not claim image-based diagnosis
answer does not recommend pesticide/treatment as command
answer uses retrieved reference evidence
answer includes caution in [주의]
safety flags are returned or persisted through existing metadata
companion_plant_question remains deferred
no image classifier is implemented
no pest/disease model is implemented
no real LLM provider is implemented
no streaming is implemented
no Redis/worker/vLLM is introduced
/healthz remains liveness-only
/readyz is not introduced or modified
pytest passes
ruff passes
Docker smoke and API tests pass
```

---

## 16. Failure Classification

```text
ticket19_scope_boundary_failure:
  changed files outside pest reference guardrail scope

future_feature_leakage:
  vision/model/provider/streaming/reranker/future feature introduced

definitive_diagnosis_guard_failure:
  answer allows certainty claims

image_diagnosis_guard_failure:
  answer claims image-based diagnosis

treatment_command_guard_failure:
  answer allows pesticide/treatment command

overblocking_reference_answer_failure:
  valid reference-only answer rejected

pest_reference_api_failure:
  API does not return safe fixed-format reference answer

companion_scope_leakage:
  companion recommendation handled too early

healthz_regression_failure:
  Docker or liveness contract broken

readiness_boundary_failure:
  /readyz introduced or modified
```
