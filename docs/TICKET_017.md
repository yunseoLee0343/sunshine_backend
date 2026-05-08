# TICKET-017 — LLMPort + Mock LLM

## 0. 목표

Sunshine 백엔드에 provider-neutral LLM boundary를 추가하고, 외부 LLM 없이 테스트 가능한 deterministic Mock LLM을 구현한다.

이 티켓은 real LLM을 호출하지 않는다.  
이 티켓은 chat endpoint를 만들지 않는다.  
이 티켓은 streaming이나 persistence를 만들지 않는다.

Ticket 17의 책임은 아래까지만이다.

```text
PromptBuildResult / prompt string
  -> LLMRequest
  -> LLMPort.generate(...)
  -> MockLLM deterministic response
  -> LLMResponse
  -> stable prompt_hash
```

---

## 1. Ticket Identity

### Ticket ID

```text
TICKET-017
```

### Name

```text
LLMPort + Mock LLM
```

### Goal

```text
Introduce an LLM boundary and deterministic mock runtime without external network dependency.
```

### Core output

```text
LLMPort Protocol
LLMRequest schema
LLMResponse schema
MockLLMClient
stable prompt_hash utility
provider/model metadata shape
fixed-format mock answer
```

### Strict non-goal

```text
no real vLLM adapter
no OpenAI adapter
no Anthropic adapter
no external HTTP call
no streaming
no SSE
no Redis queue
no DB persistence
no llm_runs insert
no chat endpoint
no chat orchestration
no EvidenceBuilder changes
no PromptBuilder logic changes
no retrieval
no rule execution
no pest/disease diagnosis
no companion ranking
no P3 execution
no Polaris
no NCCL
no GPU telemetry
```

---

## 2. 주변 티켓과의 연결

Ticket 17은 PromptBuilder 이후, Chat API 이전의 LLM boundary다.

```text
Ticket 15:
  ForwardContext를 만든다.

Ticket 16:
  ForwardContext를 deterministic prompt로 변환한다.

Ticket 17:
  prompt를 LLMPort에 전달하고 MockLLM 응답을 만든다.

Ticket 18:
  classify / evidence / prompt / LLM을 묶는 Chat Care Answer API를 만든다.

Ticket 19:
  pest/disease response-level guardrail을 강화한다.

Ticket 22:
  prompt / response / evidence persistence와 audit query를 만든다.
```

Ticket 17의 역할:

```text
prompt
  + request_id
  + profile P1/P2
  + max_tokens
  -> deterministic mock LLMResponse
```

금지:

```text
POST /chat 생성
real LLM provider 연결
streaming 구현
DB 저장
Redis enqueue
vLLM 호출
OpenAI/Anthropic 호출
Docker topology 변경
```

---

## 3. 수정/생성 허용 파일

### 생성 가능한 새 파일

```text
app/llm/__init__.py
app/llm/base.py
app/llm/mock_client.py
app/llm/hash.py
app/domain/llm.py

tests/test_llm_contract.py
tests/test_mock_llm.py
```

### 조건부 수정 허용

```text
app/domain/__init__.py
app/domain/prompt.py
```

조건:

```text
app/domain/prompt.py는 Ticket 16의 PromptBuildResult import compatibility를 맞추는 용도로만 수정한다.
PromptBuilder 구조를 재설계하지 않는다.
```

---

## 4. 금지 파일/디렉터리

아래 경로는 생성하거나 수정하지 않는다.

```text
app/api/
app/api/chat.py
app/services/chat_orchestrator.py
app/services/evidence_builder.py
app/services/prompt_builder.py
app/services/rule_engine.py
app/services/scenario_classifier.py
app/services/profile_selector.py
app/retrieval/
app/vision/
app/repositories/
app/mqtt/
app/workers/
alembic/
migrations/
Dockerfile
docker-compose.yml
.env.example
.github/workflows/
```

규칙:

```text
Ticket 17 must not create a user-facing chat route, persistence layer, production LLM runtime, Docker service, queue, or worker.
```

---

## 5. LLM Domain 계약

아래 파일을 생성한다.

```text
app/domain/llm.py
```

필수 타입:

```python
from dataclasses import dataclass
from typing import Literal

LLMProvider = Literal["mock"]
LLMProfile = Literal["P1", "P2"]

@dataclass(frozen=True)
class LLMRequest:
    request_id: str
    prompt: str
    profile: LLMProfile
    max_tokens: int
    stream: bool = False

@dataclass(frozen=True)
class LLMResponse:
    request_id: str
    text: str
    provider: LLMProvider
    model: str
    prompt_hash: str
    tokens_in: int | None
    tokens_out: int | None
    latency_ms: int | None
```

규칙:

```text
request_id must be non-empty.
prompt must be non-empty.
profile must be P1 or P2.
P3 is forbidden in Ticket 17.
stream must be false.
```

---

## 6. LLMPort 계약

아래 파일을 생성한다.

```text
app/llm/base.py
```

필수 port:

```python
from typing import Protocol
from app.domain.llm import LLMRequest, LLMResponse

class LLMPort(Protocol):
    async def generate(self, request: LLMRequest) -> LLMResponse:
        ...
```

규칙:

```text
LLMPort is provider-neutral.
Ticket 17 provides only MockLLMClient.
Future real providers must implement this port in later tickets.
```

금지:

```text
vLLM client
OpenAI client
Anthropic client
HTTP client
stream token iterator
provider selection by env var
```

---

## 7. Prompt Hash 계약

아래 파일을 생성한다.

```text
app/llm/hash.py
```

필수 함수:

```python
def stable_prompt_hash(prompt: str) -> str:
    ...
```

필수 동작:

```text
SHA-256
same prompt -> same hash
different prompt -> different hash
lowercase hex string
length 64
no silent whitespace normalization unless explicitly tested
```

금지:

```text
Python object repr hash
random salt
wall-clock timestamp
process-dependent hash()
```

---

## 8. MockLLMClient 계약

아래 파일을 생성한다.

```text
app/llm/mock_client.py
```

필수 shape:

```python
from app.llm.base import LLMPort
from app.domain.llm import LLMRequest, LLMResponse

class LLMContractError(ValueError):
    ...

class MockLLMClient(LLMPort):
    async def generate(self, request: LLMRequest) -> LLMResponse:
        ...
```

필수 동작:

```text
no network
no DB
no filesystem read/write
no env var dependency
deterministic output for same input
provider="mock"
model="mock-llm-v1"
prompt_hash=stable_prompt_hash(request.prompt)
latency_ms is None or 0
stream=True is rejected
profile=P3 is rejected
unsupported profile is rejected
```

---

## 9. Mock Response 계약

Mock response는 실제 식물 조언이 아니라 pipeline contract 검증용 응답이다.

기본 응답 skeleton:

```text
[결론]
테스트용 모의 응답입니다.

[근거]
제공된 프롬프트의 근거를 바탕으로 생성된 모의 응답입니다.

[행동]
실제 LLM 호출 없이 다음 파이프라인 검증을 위한 응답을 반환합니다.

[주의]
이 응답은 MockLLM 결과이며 실제 식물 진단이나 최종 권고가 아닙니다.
```

필수 섹션:

```text
[결론]
[근거]
[행동]
[주의]
```

Pest/disease prompt일 때:

```text
확정 진단이 아님을 명시한다.
추가 관찰 또는 전문가 확인이 필요함을 명시한다.
```

No-watering prompt일 때 금지 문구:

```text
물을 주세요
즉시 물을 주세요
일주일에 한 번 물을 주세요
무조건 물을 주세요
```

허용 문구:

```text
Rule Engine 결과가 물주기 불필요라면 추가 급수는 피해야 합니다.
```

---

## 10. Validation 계약

`MockLLMClient.generate()`는 fail closed로 동작한다.

에러 class:

```python
class LLMContractError(ValueError):
    ...
```

실패 조건:

```text
empty request_id
empty prompt
profile not in P1/P2
profile is P3
max_tokens <= 0
max_tokens exceeds profile cap
stream=True
```

Profile token cap:

```text
P1: max_tokens <= 256
P2: max_tokens <= 768
P3: forbidden
```

---

## 11. Runtime 계약

허용 runtime shape:

```text
backend Python process
  -> import LLMPort
  -> import MockLLMClient
  -> await MockLLMClient.generate(LLMRequest)
  -> return LLMResponse
```

금지 runtime shape:

```text
backend
  -> HTTP call to vLLM/OpenAI/Anthropic
  -> DB write
  -> Redis enqueue
  -> SSE stream
  -> worker process
  -> model loading
```

Process invariant:

```text
MockLLMClient is async-compatible.
MockLLMClient is deterministic.
MockLLMClient is side-effect free.
MockLLMClient does not depend on wall-clock time for response text.
```

---

## 12. Network / Env 계약

Ticket 17은 새 네트워크 의존성을 만들지 않는다.

금지 network:

```text
external HTTP
localhost LLM server
OpenAI
Anthropic
vLLM
Redis
Postgres
MQTT
object storage
gRPC
socket
```

금지 dependency/import:

```text
httpx
requests
aiohttp
openai
anthropic
vllm
grpc
socket
sqlalchemy
asyncpg
psycopg
redis
paho
```

Ticket 17은 새 env var를 요구하지 않는다.

금지 env:

```text
LLM_*
VLLM_*
OPENAI_*
ANTHROPIC_*
MODEL_*
PROVIDER_*
DATABASE_*
REDIS_*
MQTT_*
```

---

## 13. Health / Readiness 계약

Ticket 17은 아래 endpoint를 수정하지 않는다.

```http
GET /healthz
```

Ticket 17은 아래 endpoint를 추가하지 않는다.

```http
GET /readyz
```

규칙:

```text
/healthz remains liveness-only.
MockLLM has no external dependency, so Ticket 17 has no readiness check to expose.
```

---

## 14. Functional Gate

Antigravity는 구현 후 최소 아래 명령을 통과시켜야 한다.

```bash
ruff check app/llm app/domain/llm.py tests/test_llm_contract.py tests/test_mock_llm.py
ruff format --check app/llm app/domain/llm.py tests/test_llm_contract.py tests/test_mock_llm.py
pytest -q tests/test_llm_contract.py tests/test_mock_llm.py
```

### Boundary grep

```bash
python - <<'PY'
from pathlib import Path

targets = [
    Path("app/llm/base.py"),
    Path("app/llm/mock_client.py"),
    Path("app/llm/hash.py"),
    Path("app/domain/llm.py"),
]

for path in targets:
    text = path.read_text()
    forbidden = [
        "httpx", "requests", "aiohttp", "openai", "anthropic", "vllm",
        "sqlalchemy", "asyncpg", "psycopg", "redis", "paho", "socket",
        "subprocess", "os.environ", "dotenv", "Path(", "open(",
    ]
    hits = [token for token in forbidden if token in text]
    assert not hits, f"{path}: forbidden imports/usages: {hits}"

print("ticket17_external_dependency_boundary: pass")
PY
```

### Prompt hash gate

```bash
python - <<'PY'
from app.llm.hash import stable_prompt_hash

prompt = "hello sunshine"
h1 = stable_prompt_hash(prompt)
h2 = stable_prompt_hash(prompt)

assert h1 == h2
assert len(h1) == 64
assert h1.lower() == h1
assert h1 != stable_prompt_hash(prompt + " ")
print("stable_prompt_hash_contract: pass")
PY
```

### Mock response gate

```bash
python - <<'PY'
import asyncio
from app.domain.llm import LLMRequest
from app.llm.mock_client import MockLLMClient

async def main() -> None:
    response = await MockLLMClient().generate(
        LLMRequest(
            request_id="req-001",
            prompt="테스트 프롬프트",
            profile="P1",
            max_tokens=128,
            stream=False,
        )
    )
    assert response.provider == "mock"
    assert response.model == "mock-llm-v1"
    assert response.prompt_hash
    for section in ["[결론]", "[근거]", "[행동]", "[주의]"]:
        assert section in response.text

asyncio.run(main())
print("mock_llm_fixed_answer_format: pass")
PY
```

### P3 / streaming blocked gate

```bash
python - <<'PY'
import asyncio
from app.domain.llm import LLMRequest
from app.llm.mock_client import MockLLMClient, LLMContractError

async def expect_error(req: LLMRequest) -> None:
    try:
        await MockLLMClient().generate(req)
    except LLMContractError:
        return
    raise AssertionError("expected LLMContractError")

async def main() -> None:
    await expect_error(LLMRequest(request_id="r1", prompt="p", profile="P3", max_tokens=128))  # type: ignore[arg-type]
    await expect_error(LLMRequest(request_id="r2", prompt="p", profile="P1", max_tokens=128, stream=True))

asyncio.run(main())
print("p3_and_streaming_blocked: pass")
PY
```

### Docker regression smoke

```bash
docker build -t sunshine-backend:ticket17 .
docker rm -f sunshine-backend-ticket17 >/dev/null 2>&1 || true

docker run -d \
  --name sunshine-backend-ticket17 \
  -p 8000:8000 \
  -e APP_NAME=sunshine-backend \
  -e APP_ENV=local \
  sunshine-backend:ticket17

for i in $(seq 1 30); do
  if curl -fsS http://localhost:8000/healthz >/tmp/healthz.ticket17.json; then
    break
  fi
  sleep 1
done

test -s /tmp/healthz.ticket17.json

python - <<'PY'
import json
from pathlib import Path
body = json.loads(Path("/tmp/healthz.ticket17.json").read_text())
assert body == {"status": "ok", "service": "sunshine-backend"}, body
print("healthz_liveness_regression: pass")
PY

docker rm -f sunshine-backend-ticket17 >/dev/null 2>&1 || true
```

---

## 15. Required Tests

`tests/test_llm_contract.py`:

```text
test_llm_port_protocol_shape
test_llm_request_requires_request_id
test_llm_request_requires_prompt
test_stable_prompt_hash_is_deterministic
test_stable_prompt_hash_changes_when_prompt_changes
```

`tests/test_mock_llm.py`:

```text
test_mock_llm_returns_llm_response
test_mock_llm_returns_fixed_answer_sections
test_mock_llm_is_deterministic
test_mock_llm_sets_provider_and_model_metadata
test_mock_llm_sets_prompt_hash
test_mock_llm_rejects_stream_true
test_mock_llm_rejects_p3_profile
test_mock_llm_rejects_max_tokens_over_p1_limit
test_mock_llm_rejects_max_tokens_over_p2_limit
test_mock_llm_no_watering_prompt_does_not_recommend_watering
test_mock_llm_pest_prompt_contains_caution
```

---

## 16. Acceptance Criteria

```text
LLMPort Protocol exists.
LLMRequest and LLMResponse exist.
MockLLMClient implements LLMPort.
MockLLMClient is deterministic.
MockLLMClient requires no network.
MockLLMClient requires no DB.
MockLLMClient requires no env vars.
Mock response contains [결론][근거][행동][주의].
Response includes provider="mock".
Response includes model="mock-llm-v1".
Response includes stable prompt_hash.
stream=True is rejected.
P3 is rejected.
P1/P2 max_tokens caps are enforced.
No real LLM provider is implemented.
No chat endpoint is implemented.
No persistence is implemented.
/healthz remains unchanged and liveness-only.
/readyz is not introduced.
pytest passes.
ruff passes.
Docker health regression smoke passes.
```
