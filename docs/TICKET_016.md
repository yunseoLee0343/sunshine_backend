# TICKET-016 — PromptBuilder + Fixed Answer Format

## 0. 목표

Sunshine 백엔드에서 이미 만들어진 `ForwardContext`를 LLM에 전달 가능한 deterministic prompt로 변환한다.

이 티켓은 final answer를 생성하지 않는다.  
이 티켓은 LLM을 호출하지 않는다.  
이 티켓은 Chat API orchestration을 만들지 않는다.  
이 티켓은 EvidenceBuilder를 다시 만들지 않는다.

Ticket 16의 책임은 아래까지만이다.

```text
ForwardContext
  -> PromptBuilder
  -> fixed answer format prompt
  -> PromptBuildResult
  -> prompt contract tests
```

---

## 1. Ticket Identity

### Ticket ID

```text
TICKET-016
```

### Name

```text
PromptBuilder + Fixed Answer Format
```

### Goal

```text
Convert existing ForwardContext into a deterministic prompt that forces:
[결론]
[근거]
[행동]
[주의]
```

### Core output

```text
PromptBuilder service
PromptBuildResult domain object
fixed answer format instruction
Rule Engine authority guardrail
pest/disease reference guardrail
prompt determinism tests
prompt boundary tests
```

### Strict non-goal

```text
no ForwardContext construction
no EvidenceBuilder implementation
no retrieval execution
no Rule Engine execution
no LLMPort
no Mock LLM
no vLLM adapter
no OpenAI/Anthropic adapter
no LLM call
no streaming
no final answer generation
no chat endpoint orchestration
no response persistence
no llm_runs insert
no prompt table migration
no companion ranking
no pest/disease diagnosis
no Docker topology change
no new runtime process
```

---

## 2. 주변 티켓과의 연결

Ticket 16은 Evidence와 LLM 사이의 prompt construction boundary다.

```text
Ticket 13:
  intent, selected_rule_modules, selected_rag_layers 산출

Ticket 14:
  retrieved chunks + source metadata 산출

Ticket 15:
  ForwardContext / evidence bundle 조립

Ticket 16:
  ForwardContext를 fixed-format prompt로 변환

Ticket 17:
  PromptBuilder output을 받아 LLMPort / Mock LLM 실행

Ticket 18:
  Chat Care Answer API에서 전체 pipeline orchestration

Ticket 19:
  pest/disease response-level guardrail 강화

Ticket 20/21:
  companion compatibility / recommendation ranking
```

Ticket 16의 역할:

```text
ForwardContext
  + intent
  + rule_results
  + retrieved_chunks
  + sensor_snapshot
  + care_logs
  -> deterministic prompt string
  -> required sections metadata
  -> guardrail metadata
  -> evidence refs metadata
```

금지:

```text
ForwardContext 생성
DB에서 evidence 재조회
retrieval 재실행
Rule Engine 재실행
LLM 호출
final answer 생성
response 저장
chat endpoint 생성
```

---

## 3. 수정/생성 허용 파일

### 생성 가능한 새 파일

```text
app/domain/prompt.py
app/services/prompt_builder.py

tests/test_prompt_builder.py
tests/fixtures/forward_contexts.py
```

### 조건부 수정 허용

아래 파일은 현재 repo layout상 import/package marker가 필요할 때만 수정한다.

```text
app/domain/__init__.py
app/services/__init__.py
```

아래 파일은 Ticket 15의 ForwardContext type import 정렬이 필요한 경우에만 최소 수정한다.

```text
app/domain/evidence.py
```

규칙:

```text
app/domain/evidence.py를 수정하더라도 ForwardContext 모델을 재설계하지 않는다.
EvidenceBuilder output schema를 이동하거나 변경하지 않는다.
PromptBuilder가 필요한 type alignment만 허용한다.
```

---

## 4. 금지 파일/디렉터리

아래 경로는 생성하거나 수정하지 않는다.

```text
app/api/
app/api/chat.py
app/llm/
app/retrieval/
app/vision/
app/repositories/
app/mqtt/
app/workers/

app/services/chat_orchestrator.py
app/services/chat_care_answer_service.py
app/services/evidence_builder.py
app/services/rule_engine.py
app/services/scenario_classifier.py
app/services/profile_selector.py
app/services/llm_port.py
app/services/companion_recommendation.py
app/services/pest_diagnosis_service.py

alembic/
migrations/
Dockerfile
docker-compose.yml
.env.example
.github/workflows/
```

규칙:

```text
Ticket 16 must not add API routes, persistence, LLM provider code, retrieval logic, Docker topology, readiness checks, or worker infrastructure.
```

---

## 5. Prompt Domain 계약

아래 파일을 생성한다.

```text
app/domain/prompt.py
```

필수 shape:

```python
from dataclasses import dataclass
from typing import Literal

AnswerSection = Literal["결론", "근거", "행동", "주의"]

@dataclass(frozen=True)
class PromptBuildResult:
    request_id: str
    prompt: str
    required_sections: tuple[AnswerSection, ...]
    guardrails: tuple[str, ...]
    evidence_refs: tuple[str, ...]
```

규칙:

```text
PromptBuildResult는 immutable이어야 한다.
required_sections는 항상 ("결론", "근거", "행동", "주의") 순서를 유지한다.
prompt는 deterministic string이어야 한다.
evidence_refs는 ForwardContext 안에 있는 source/chunk/rule 참조만 포함한다.
```

금지 field:

```text
final_answer
llm_response
model_name
provider
stream_id
prompt_hash persistence id
llm_run_id
```

---

## 6. PromptBuilder 계약

아래 파일을 생성한다.

```text
app/services/prompt_builder.py
```

필수 class shape:

```python
class PromptBuildError(ValueError):
    ...

class PromptBuilder:
    def build(self, context: ForwardContext) -> PromptBuildResult:
        ...
```

필수 동작:

```text
1. Validate request_id.
2. Validate user_question / question.
3. Validate intent.
4. Read rule_results from ForwardContext.
5. Read retrieved_chunks from ForwardContext.
6. Serialize species_profile, sensor_snapshot, care_logs, rule_results, retrieved_chunks into prompt.
7. Add fixed answer format instruction.
8. Add Rule Engine authority guardrail.
9. Add safety/uncertainty guardrails.
10. Return PromptBuildResult.
```

금지 동작:

```text
DB read/write
retrieval execution
Rule Engine execution
LLM call
network call
file read/write
UUID generation
wall-clock timestamp usage
ForwardContext mutation
```

---

## 7. Prompt 내용 계약

생성 prompt는 안정적인 순서로 아래 블록을 포함한다.

```text
1. assistant role boundary
2. fixed answer format rule
3. Rule Engine authority rule
4. safety / uncertainty guardrails
5. user question
6. intent
7. species profile summary, if present
8. sensor snapshot summary, if present
9. care log summary, if present
10. Rule Engine results
11. retrieved chunk summaries
12. final answer instruction
```

필수 final answer instruction:

```text
반드시 아래 4개 섹션만 사용해 답변하라.

[결론]
...

[근거]
...

[행동]
...

[주의]
...
```

금지 prompt 내용:

```text
free-form answer format
hidden chain-of-thought request
tool call instruction
DB query instruction
retrieval instruction
LLM provider instruction
streaming instruction
```

---

## 8. Guardrail 계약

Prompt는 아래 의미를 반드시 포함한다.

```text
Rule Engine 결과를 최종 관리 판단의 기준으로 삼아라.
Rule Engine 결과와 충돌하는 물주기/빛/습도/온도 행동을 제안하지 마라.
제공된 evidence 밖의 센서값, 관리 이력, 식물 상태를 지어내지 마라.
병충해/질병 관련 질문에서는 확정 진단을 하지 마라.
사진 기반 병충해 판정을 수행했다고 주장하지 마라.
농약, 약제, 치료법을 단정적으로 지시하지 마라.
근거가 부족하면 관찰, 추가 확인, 전문가 확인을 권고하라.
```

특히 watering prompt는 아래를 포함해야 한다.

```text
If Rule Engine says no_watering, the LLM must not recommend watering.
```

pest/disease prompt는 아래를 포함해야 한다.

```text
reference-only
not diagnosis
not image diagnosis
not treatment command
```

---

## 9. Intent별 최소 계약

### watering_question

필수:

```text
watering rule result 포함
soil moisture evidence 포함, available인 경우
recent watering care log 포함, available인 경우
Rule Engine no_watering override 금지 문구 포함
```

금지:

```text
generic schedule-only watering advice
Rule Engine과 충돌하는 watering action
```

### light_question

필수:

```text
light rule result 포함
light_lux 또는 light trend evidence 포함, available인 경우
```

금지:

```text
evidence 없는 relocation advice
```

### humidity_question / temperature_question

필수:

```text
corresponding rule result 포함
latest snapshot 또는 summary evidence 포함, available인 경우
```

금지:

```text
species profile/rule evidence에 없는 threshold 조작
```

### pest_reference_question

필수:

```text
reference-only caution block
retrieved pest/disease chunks를 reference material로 표현
확정 진단 금지
치료/약제 단정 지시 금지
```

금지:

```text
definitive diagnosis
image diagnosis claim
pesticide/treatment command
```

### companion_plant_question

필수:

```text
ForwardContext에 이미 있는 companion candidates만 사용
environment compatibility는 evidence-based로만 표현
```

금지:

```text
ranking algorithm
new candidate retrieval
marketplace/purchase integration
```

### unknown_question

필수:

```text
clarifying question 유도
care action 단정 금지
```

---

## 10. Runtime 계약

허용 runtime shape:

```text
backend process
  -> import PromptBuilder
  -> PromptBuilder.build(ForwardContext)
  -> PromptBuildResult 반환
```

Forbidden runtime shape:

```text
backend
  -> PromptBuilder
  -> DB query
  -> Redis enqueue
  -> retrieval call
  -> LLM call
  -> streaming response
```

Process invariant:

```text
PromptBuilder는 pure, synchronous, deterministic, side-effect-free 함수여야 한다.
```

금지 runtime behavior:

```text
connect to DB
connect to Redis
call MQTT
call vLLM
call external LLM API
read secrets
load model weights
start workers
enqueue jobs
write audit logs
mutate ForwardContext
generate UUIDs internally
depend on wall-clock time
```

---

## 11. Network / Env 계약

Ticket 16은 새 network surface를 추가하지 않는다.

```text
0 new ports
0 new external HTTP calls
0 new Docker services
0 new compose services
0 new service discovery names
```

금지 호출:

```text
OpenAI
Anthropic
vLLM
Redis
Postgres
MQTT broker
object storage
localhost LLM server
```

Ticket 16은 새 environment variable을 요구하지 않는다.

금지 env:

```text
LLM_*
VLLM_*
OPENAI_*
ANTHROPIC_*
DATABASE_*
REDIS_*
MQTT_*
PROMPT_*
```

---

## 12. Health / Readiness 계약

Ticket 16은 아래 endpoint를 수정하지 않는다.

```text
GET /healthz
```

Ticket 16은 아래 endpoint를 추가하지 않는다.

```text
GET /readyz
```

규칙:

```text
/healthz remains liveness-only.
PromptBuilder는 readiness 대상이 아니다.
PromptBuilder는 DB/Redis/MQTT/LLM/vLLM dependency가 없다.
```

---

## 13. Failure Mode 계약

PromptBuilder는 fail closed 한다.

```text
missing request_id:
  raise PromptBuildError

missing question:
  raise PromptBuildError

missing intent:
  raise PromptBuildError

care intent without rule result:
  raise PromptBuildError unless context explicitly marks rule unavailable

pest_reference_question without retrieved chunks:
  build caution-heavy limited-evidence prompt

unknown intent:
  build clarification-oriented fallback prompt

empty evidence:
  do not fabricate values
```

---

## 14. Functional Gate — Executable

아래 스크립트를 생성하거나 CI에 동일 논리를 반영한다.

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "[Gate 0] Ticket 16 required files"
for path in \
  app/domain/prompt.py \
  app/services/prompt_builder.py \
  tests/test_prompt_builder.py
do
  test -f "$path" || { echo "missing required file: $path"; exit 1; }
done

echo "[Gate 1] Forbidden future files"
for path in \
  app/services/chat_orchestrator.py \
  app/services/chat_care_answer_service.py \
  app/services/llm_port.py \
  app/llm \
  app/workers
do
  if [ -e "$path" ]; then
    echo "forbidden Ticket 16 path exists: $path"
    exit 1
  fi
done

echo "[Gate 2] Forbidden dependency leak"
if grep -R 'openai\|anthropic\|vllm\|redis\|sqlalchemy\|asyncpg\|psycopg\|paho\|requests\|httpx\|socket\|subprocess\|os.environ' \
  app/services/prompt_builder.py app/domain/prompt.py >/tmp/ticket16_forbidden_dep.txt 2>/dev/null; then
  cat /tmp/ticket16_forbidden_dep.txt
  exit 1
fi

echo "[Gate 3] Ruff"
ruff check app/domain/prompt.py app/services/prompt_builder.py tests/test_prompt_builder.py
ruff format --check app/domain/prompt.py app/services/prompt_builder.py tests/test_prompt_builder.py

echo "[Gate 4] Unit tests"
pytest -q tests/test_prompt_builder.py

echo "[Gate 5] Fixed answer format"
python - <<'PY'
from tests.fixtures.forward_contexts import make_watering_context
from app.services.prompt_builder import PromptBuilder

ctx = make_watering_context(rule_decision="no_watering")
result = PromptBuilder().build(ctx)
prompt = result.prompt

for section in ["[결론]", "[근거]", "[행동]", "[주의]"]:
    assert section in prompt, section

assert "Rule Engine" in prompt or "룰 엔진" in prompt
assert "no_watering" in prompt
print("fixed_answer_format: pass")
PY

echo "[Gate 6] Pest reference guard"
python - <<'PY'
from tests.fixtures.forward_contexts import make_pest_reference_context
from app.services.prompt_builder import PromptBuilder

ctx = make_pest_reference_context()
prompt = PromptBuilder().build(ctx).prompt

assert "확정 진단" in prompt
assert "하지 마라" in prompt or "하지 않는다" in prompt
assert "사진 기반" in prompt or "image diagnosis" in prompt

for forbidden in ["약을 뿌리세요", "치료하세요", "이 사진은 응애입니다"]:
    assert forbidden not in prompt, forbidden

print("pest_reference_guard: pass")
PY

echo "[Gate 7] /healthz regression smoke"
docker build -t sunshine-backend:ticket16 .
docker rm -f sunshine-backend-ticket16 >/dev/null 2>&1 || true
docker run -d \
  --name sunshine-backend-ticket16 \
  -p 8000:8000 \
  -e APP_NAME=sunshine-backend \
  -e APP_ENV=local \
  sunshine-backend:ticket16

cleanup() {
  docker rm -f sunshine-backend-ticket16 >/dev/null 2>&1 || true
}
trap cleanup EXIT

for i in $(seq 1 30); do
  if curl -fsS http://localhost:8000/healthz >/tmp/ticket16_healthz.json; then
    break
  fi
  sleep 1
done

test -s /tmp/ticket16_healthz.json

python - <<'PY'
import json
from pathlib import Path
body = json.loads(Path('/tmp/ticket16_healthz.json').read_text())
assert body == {"status": "ok", "service": "sunshine-backend"}, body
print("healthz_liveness_regression: pass")
PY

echo "[Gate 8] No readyz"
if grep -R "readyz" app tests; then
  echo "forbidden_readyz"
  exit 1
fi

echo "Ticket 16 Functional Gate: PASS"
```

---

## 15. Required Tests

`tests/test_prompt_builder.py`에 최소 아래 테스트를 추가한다.

```text
test_watering_prompt_contains_fixed_sections
test_watering_prompt_contains_rule_engine_decision
test_watering_prompt_does_not_override_no_watering_rule
test_light_prompt_contains_light_evidence
test_pest_reference_prompt_contains_non_diagnosis_guardrail
test_pest_reference_prompt_does_not_include_treatment_command
test_unknown_intent_prompt_asks_clarifying_question
test_prompt_build_result_is_deterministic
test_prompt_builder_does_not_mutate_context
test_missing_request_id_fails_closed
test_missing_question_fails_closed
```

---

## 16. Acceptance Criteria

```text
PromptBuilder builds prompt from existing ForwardContext.
Prompt includes fixed sections: [결론], [근거], [행동], [주의].
Prompt includes evidence from ForwardContext.
Prompt includes Rule Engine authority guardrail.
Watering prompt does not override no_watering rule.
Pest/disease prompt is reference-only and non-diagnostic.
Unknown intent prompt avoids care-action certainty.
PromptBuildResult is deterministic.
PromptBuilder does not mutate ForwardContext.
No LLM provider is implemented.
No LLM call is made.
No streaming is implemented.
No API route is added.
No DB/Redis/MQTT/vLLM dependency is introduced.
No new env vars are introduced.
/healthz remains unchanged.
/readyz is not introduced.
pytest passes.
ruff passes.
Docker health regression smoke passes.
```

---

## 17. Antigravity Execution Prompt

```text
Implement TICKET-016 only.

Use this markdown as the source of truth.

Priority:
1. Preserve Ticket 16 scope.
2. Implement PromptBuilder as a pure deterministic function.
3. Force [결론][근거][행동][주의] answer format in the generated prompt.
4. Include Rule Engine authority guardrail.
5. Include pest/disease non-diagnosis guardrail.
6. Add tests proving determinism, fixed sections, rule override prevention, and no diagnosis/treatment prompt leakage.

Do not implement LLMPort, Mock LLM, vLLM, OpenAI/Anthropic adapters, streaming, chat endpoint, retrieval, DB persistence, migrations, worker, Docker topology changes, /readyz, or final answer generation.

After implementation, run:
- ruff check .
- ruff format --check .
- pytest
- docker build -t sunshine-backend:ticket16 .
- docker run healthz smoke if Docker is available

Final report must list:
- changed files
- commands run
- passed tests/gates
- explicit non-goals preserved
- deviations, if any
```
