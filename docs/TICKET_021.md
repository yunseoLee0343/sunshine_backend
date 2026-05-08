# TICKET-021 — Companion Plant Recommendation API

## 0. 목표

Sunshine 백엔드에 반려 식물 추천 결과를 노출하는 최소 API와 chat 경로를 구현한다.

이 티켓은 새로운 추천 알고리즘을 만들지 않는다.  
이 티켓은 Ticket 20의 deterministic compatibility filter를 재사용한다.  
이 티켓은 marketplace, purchase link, ML ranking, real LLM provider를 만들지 않는다.

Ticket 21의 책임은 아래까지만이다.

```text
current plant species
  + latest room/environment snapshot
  + companion candidates
  -> Ticket 20 CompanionCompatibilityFilter
  -> direct recommendation API response
  -> optional companion chat explanation through existing MockLLM path
```

---

## 1. Ticket Identity

### Ticket ID

```text
TICKET-021
```

### Name

```text
Companion Plant Recommendation API
```

### Goal

```text
Expose companion plant recommendations through a direct endpoint and supported chat path using Ticket 20's deterministic compatibility filter.
```

### Core output

```text
GET /plants/{plant_id}/companion-recommendations
CompanionRecommendationService
CompanionRecommendationBundle
companion_plant_question chat branch
recommendation response schema
fixed-format companion chat answer
source/reason/caution metadata
```

### Strict non-goal

```text
no new compatibility algorithm
no reimplemented scoring
no ML ranking
no marketplace integration
no purchase links
no affiliate links
no real vLLM/OpenAI/Anthropic adapter
no SSE streaming
no Redis queue
no worker process
no schema migration
no audit query endpoint
no admin UI
no mobile UI
```

---

## 2. 주변 티켓과의 연결

Ticket 21은 Ticket 20의 deterministic filter를 user-facing boundary로 노출한다.

```text
Ticket 7:
  latest room/environment snapshot 제공

Ticket 13:
  companion_plant_question intent 분류

Ticket 14:
  companion_plant / species_profile candidate evidence 제공

Ticket 15:
  chat path에서 recommendation evidence를 ForwardContext로 조립

Ticket 16:
  companion chat explanation prompt 생성

Ticket 17:
  MockLLM을 통해 fixed-format response 생성

Ticket 18/19:
  기존 care/pest chat behavior 유지

Ticket 20:
  compatibility filter 제공

Ticket 21:
  direct API + companion chat path로 추천 노출

Ticket 22:
  audit query API는 나중에 담당
```

Ticket 21의 역할:

```text
plant_id
  -> current species profile
  -> latest environment snapshot
  -> companion candidates
  -> CompanionCompatibilityFilter
  -> recommendation list with reasons/cautions
```

금지:

```text
filter scoring 재구현
LLM이 candidate 선택
marketplace ranking
purchase link 생성
new DB schema 생성
real LLM 호출
streaming
```

---

## 3. 수정/생성 허용 파일

### 생성 가능한 새 파일

```text
app/api/companion.py
app/services/companion_recommendation.py
app/domain/companion_recommendation.py

tests/test_companion_recommendation_api.py
tests/test_companion_recommendation_service.py
tests/fixtures/companion_recommendation_fixtures.py
```

### 수정 가능한 기존 파일

```text
app/api/__init__.py
app/services/__init__.py
app/domain/__init__.py
app/main.py
app/api/chat.py
app/services/chat_orchestrator.py
app/domain/chat.py
app/repositories/companion_repository.py
```

수정 제한:

```text
app/main.py:
  - companion router include만 허용
  - /healthz 변경 금지
  - /readyz 생성 금지
  - startup dependency check 금지

app/api/chat.py / app/services/chat_orchestrator.py / app/domain/chat.py:
  - companion_plant_question branch 연결만 허용
  - care question behavior 보존
  - pest_reference_question behavior 보존
  - fixed answer response schema 보존

app/repositories/companion_repository.py:
  - 기존 table/chunk에서 current species, snapshot, candidates를 읽는 경계만 허용
  - 새 schema/migration 금지
```

---

## 4. 금지 파일/디렉터리

아래 경로는 생성하거나 수정하지 않는다.

```text
app/services/marketplace.py
app/services/purchase_links.py
app/services/ml_ranker.py

app/retrieval/reranker.py
app/retrieval/crag.py

app/llm/vllm_client.py
app/llm/openai_client.py
app/llm/anthropic_client.py

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

규칙:

```text
Ticket 21 must expose deterministic companion recommendations only.
It must not introduce marketplace, ML ranking, production LLM, streaming, worker, or schema migration.
```

---

## 5. Direct API 계약 — GET /plants/{plant_id}/companion-recommendations

### Endpoint

```http
GET /plants/{plant_id}/companion-recommendations
```

### Query params

```text
limit: int = 5
include_borderline: bool = true
```

### Response

```json
{
  "plant_id": "uuid",
  "room_id": "uuid | null",
  "recommendations": [
    {
      "species_id": "str",
      "common_name": "str",
      "decision": "compatible",
      "score": 90,
      "reasons": [
        {
          "dimension": "light",
          "decision": "compatible",
          "message": "현재 거실 조도 평균이 후보 식물의 권장 범위 안에 있습니다."
        }
      ],
      "caution_notes": ["반려동물이 잎을 먹지 않도록 주의하세요."],
      "source_chunk_ids": ["chunk-companion-pothos-001"]
    }
  ],
  "evidence": {
    "current_species_id": "str",
    "snapshot_id": "str | null",
    "candidate_count": 12,
    "filter_version": "companion-compatibility-v1"
  }
}
```

필수 동작:

```text
Validate plant_id and limit.
Load current plant/species profile.
Load latest room/environment snapshot.
Load companion candidates.
Run Ticket 20 CompanionCompatibilityFilter.
Return compatible/borderline recommendations.
Include reasons, caution_notes, source_chunk_ids.
Exclude incompatible candidates.
Exclude current plant species.
```

Error behavior:

```text
400 invalid_request
404 plant_not_found
409 environment_snapshot_unavailable
409 companion_candidates_unavailable
500 companion_recommendation_failure
```

금지 response fields:

```text
purchase_url
buy_url
marketplace
affiliate
price
checkout
ml_rank_score
llm_selected_candidate
```

---

## 6. Chat Integration 계약 — companion_plant_question

Ticket 21은 기존 chat endpoint의 companion branch만 연다.

```http
POST /plants/{plant_id}/chat
```

Supported input:

```json
{
  "request_id": "uuid | optional",
  "question": "같이 키우기 좋은 식물 추천해줘",
  "locale": "ko-KR"
}
```

Required chat flow:

```text
POST /plants/{plant_id}/chat
  -> classify companion_plant_question
  -> profile = P2
  -> run CompanionRecommendationService
  -> build evidence from compatibility results
  -> build prompt
  -> call MockLLM through LLMPort
  -> validate [결론][근거][행동][주의]
  -> return fixed-format explanation + recommendation list
```

Required response additions:

```json
{
  "request_id": "uuid",
  "plant_id": "uuid",
  "intent": "companion_plant_question",
  "profile": "P2",
  "answer": {
    "text": "str",
    "sections": {
      "결론": "str",
      "근거": "str",
      "행동": "str",
      "주의": "str"
    }
  },
  "recommendations": [
    {
      "species_id": "str",
      "common_name": "str",
      "score": 90,
      "decision": "compatible",
      "caution_notes": []
    }
  ],
  "evidence": {
    "prompt_hash": "str",
    "provider": "mock",
    "model": "mock-llm-v1",
    "recommendation_source": "deterministic_compatibility_filter"
  }
}
```

금지:

```text
LLM이 후보를 새로 고르기
LLM이 Ticket 20 score를 override하기
marketplace/purchase 정보 포함
streaming response
real LLM provider 호출
```

---

## 7. CompanionRecommendationService 계약

생성:

```text
app/services/companion_recommendation.py
```

필수 class shape:

```python
class CompanionRecommendationService:
    def recommend_for_plant(
        self,
        *,
        plant_id: str,
        limit: int = 5,
        include_borderline: bool = True,
    ) -> CompanionRecommendationBundle:
        ...
```

필수 동작:

```text
1. Validate limit.
2. Load current plant/species profile through existing repository boundary.
3. Load latest room/environment snapshot.
4. Load companion candidates.
5. Call CompanionCompatibilityFilter from Ticket 20.
6. Do not reimplement compatibility scoring.
7. Apply include_borderline filter.
8. Return deterministic recommendation bundle.
```

금지 동작:

```text
new scoring formula
ML ranker
LLM candidate selection
marketplace ranking
external API call
DB schema creation
```

---

## 8. Domain Schema 계약

생성:

```text
app/domain/companion_recommendation.py
```

필수 shape:

```python
from dataclasses import dataclass
from app.domain.companion import CompanionCompatibilityResult


@dataclass(frozen=True)
class CompanionRecommendationBundle:
    plant_id: str
    room_id: str | None
    recommendations: tuple[CompanionCompatibilityResult, ...]
    current_species_id: str
    snapshot_id: str | None
    candidate_count: int
    filter_version: str = "companion-compatibility-v1"
```

규칙:

```text
recommendations must come from Ticket 20 filter results.
filter_version must be stable.
candidate_count must describe loaded candidate count before filtering.
source_chunk_ids must be preserved.
caution notes must be preserved.
```

---

## 9. Recommendation Rules 보존

Ticket 21은 Ticket 20의 결과를 노출할 뿐이다.

Required:

```text
light compatibility reason appears.
humidity compatibility reason appears.
temperature compatibility reason appears.
room suitability reason appears.
caution notes appear when available.
source_chunk_ids appear when available.
incompatible candidates are excluded.
current plant species is excluded.
output order remains stable.
```

Forbidden:

```text
generic-only recommendation without environment reason
LLM-generated candidate selection
LLM override of deterministic filter result
marketplace-based ranking
popularity-based ranking
purchase-link ordering
```

---

## 10. Persistence 계약

Direct API:

```text
GET /companion-recommendations does not need to persist a chat run.
```

Chat path:

```text
May use existing Ticket 18 persistence path if available.
```

Persist if existing schema supports:

```text
request_id
plant_id
question
intent = companion_plant_question
selected_rag_layers = ["companion_plant", "species_profile"]
recommendation_candidate_ids
compatibility_reasons
caution_notes
prompt
prompt_hash
response_text
provider
model
```

금지:

```text
new DB schema in this ticket
new migration
local JSON audit file
local SQLite fallback
writing recommendation evidence only to logs
```

If required fields are missing:

```text
Do not add migration in Ticket 21.
Create a separate schema-fix ticket.
```

---

## 11. Runtime 계약

허용 runtime topology:

```text
FastAPI backend
  -> GET /plants/{plant_id}/companion-recommendations
  -> CompanionRecommendationService
  -> CompanionCompatibilityFilter
  -> JSON recommendation list
```

Chat path:

```text
FastAPI backend
  -> POST /plants/{plant_id}/chat
  -> companion_plant_question branch
  -> CompanionRecommendationService
  -> EvidenceBuilder / PromptBuilder
  -> LLMPort / MockLLM
  -> fixed-format answer
```

Forbidden runtime topology:

```text
backend
  -> marketplace API
  -> ML ranker model
  -> vLLM server
  -> Redis worker
  -> SSE stream
  -> external recommendation service
```

Process invariants:

```text
no new long-running process
request-scoped recommendation only
no background worker
no scheduler
no model warmup
no marketplace polling
no startup dependency check
```

Network contract:

```text
Allowed new route:
  GET /plants/{plant_id}/companion-recommendations

Allowed existing route extension:
  POST /plants/{plant_id}/chat

Forbidden:
  new port
  new Docker service
  SSE endpoint
  WebSocket endpoint
  marketplace endpoint
  admin/debug endpoint
  external network call
```

Env contract:

```text
No new env vars.
```

Forbidden env vars:

```text
MARKETPLACE_*
PURCHASE_*
AFFILIATE_*
COMPANION_MODEL_*
RANKER_*
LLM_*
VLLM_*
OPENAI_*
ANTHROPIC_*
REDIS_*
MQTT_*
SSE_*
```

Health/readiness:

```text
Do not modify GET /healthz.
Do not add or modify GET /readyz.
```

---

## 12. Functional Gate — Executable

Create or run a gate equivalent to:

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "[Gate 1] Python quality"
ruff check app/api/companion.py app/services/companion_recommendation.py app/domain/companion_recommendation.py tests/test_companion_recommendation_api.py tests/test_companion_recommendation_service.py
ruff format --check app/api/companion.py app/services/companion_recommendation.py app/domain/companion_recommendation.py tests/test_companion_recommendation_api.py tests/test_companion_recommendation_service.py

echo "[Gate 2] Unit and API tests"
pytest -q tests/test_companion_recommendation_service.py tests/test_companion_recommendation_api.py

echo "[Gate 3] No marketplace/ML/provider/streaming leakage"
python - <<'PY'
from pathlib import Path

for path in [
    Path("app/api/companion.py"),
    Path("app/services/companion_recommendation.py"),
    Path("app/domain/companion_recommendation.py"),
]:
    text = path.read_text()
    forbidden = [
        "httpx", "requests", "aiohttp", "openai", "anthropic", "vllm",
        "StreamingResponse", "WebSocket", "marketplace", "purchase",
        "affiliate", "price", "torch", "tensorflow", "sklearn",
        "ranker", "rerank", "CRAG", "Self-RAG", "Polaris", "NCCL",
    ]
    hits = [x for x in forbidden if x in text]
    assert not hits, f"{path}: forbidden leakage: {hits}"
PY

echo "[Gate 4] Service uses Ticket 20 filter"
python - <<'PY'
from pathlib import Path
text = Path("app/services/companion_recommendation.py").read_text()
assert "CompanionCompatibilityFilter" in text
for forbidden in ["+25", "+10", "score >=", "score <"]:
    assert forbidden not in text, f"must not reimplement scoring: {forbidden}"
PY

echo "[Gate 5] Docker health regression"
docker build -t sunshine-backend:ticket21 .
docker rm -f sunshine-backend-ticket21 >/dev/null 2>&1 || true
docker run -d --name sunshine-backend-ticket21 -p 8000:8000 \
  -e APP_NAME=sunshine-backend \
  -e APP_ENV=local \
  sunshine-backend:ticket21
trap 'docker rm -f sunshine-backend-ticket21 >/dev/null 2>&1 || true' EXIT

for i in $(seq 1 30); do
  if curl -fsS http://localhost:8000/healthz >/tmp/healthz.ticket21.json; then
    break
  fi
  sleep 1
done

test -s /tmp/healthz.ticket21.json
python - <<'PY'
import json
from pathlib import Path
body = json.loads(Path("/tmp/healthz.ticket21.json").read_text())
assert body == {"status": "ok", "service": "sunshine-backend"}, body
PY

echo "[Gate 6] Direct API happy path"
curl -fsS "http://localhost:8000/plants/plant-001/companion-recommendations?limit=3&include_borderline=true" > /tmp/companion21.response.json
python - <<'PY'
import json
from pathlib import Path
body = json.loads(Path("/tmp/companion21.response.json").read_text())
assert body["plant_id"] == "plant-001"
assert "recommendations" in body
assert body["evidence"]["filter_version"] == "companion-compatibility-v1"
assert len(body["recommendations"]) <= 3
for item in body["recommendations"]:
    assert item["decision"] in {"compatible", "borderline"}
    assert item["score"] >= 50
    dims = {r["dimension"] for r in item["reasons"]}
    assert {"light", "humidity", "temperature", "room"}.issubset(dims)
PY

echo "[Gate 7] Companion chat happy path"
curl -fsS -X POST "http://localhost:8000/plants/plant-001/chat" \
  -H "Content-Type: application/json" \
  -d '{"request_id":"req-companion-001","question":"같이 키우기 좋은 식물 추천해줘","locale":"ko-KR"}' \
  > /tmp/chat21.companion.response.json
python - <<'PY'
import json
from pathlib import Path
body = json.loads(Path("/tmp/chat21.companion.response.json").read_text())
assert body["intent"] == "companion_plant_question"
assert body["profile"] == "P2"
for section in ["[결론]", "[근거]", "[행동]", "[주의]"]:
    assert section in body["answer"]["text"]
assert body["recommendations"]
assert body["evidence"]["recommendation_source"] == "deterministic_compatibility_filter"
assert body["evidence"]["provider"] == "mock"
assert body["evidence"]["model"] == "mock-llm-v1"
PY

echo "[Gate 8] No marketplace fields"
python - <<'PY'
from pathlib import Path
for file in ["/tmp/companion21.response.json", "/tmp/chat21.companion.response.json"]:
    text = Path(file).read_text().lower()
    for token in ["purchase", "marketplace", "affiliate", "price", "checkout", "buy_url"]:
        assert token not in text, f"{file}: {token}"
PY

echo "[Gate 9] No readyz"
if grep -R "readyz" app tests; then
  echo "forbidden_readyz"
  exit 1
fi

echo "Ticket 21 Functional Gate: PASS"
```

---

## 13. Required Tests

Add tests for:

```text
test_companion_recommendation_service_loads_current_species_snapshot_candidates
test_companion_recommendation_service_uses_ticket20_filter
test_companion_recommendation_service_returns_reasons_and_cautions
test_companion_recommendation_service_excludes_incompatible_candidates
test_companion_recommendation_service_respects_limit
test_companion_recommendation_api_happy_path
test_companion_recommendation_api_invalid_limit_returns_400
test_companion_recommendation_api_plant_not_found_returns_404
test_companion_recommendation_api_missing_snapshot_returns_409
test_companion_chat_intent_returns_fixed_format_answer
test_companion_chat_uses_p2_profile
test_companion_chat_returns_recommendations
test_companion_chat_uses_mock_provider_metadata
test_companion_chat_does_not_include_marketplace_fields
test_care_question_behavior_preserved
test_pest_reference_behavior_preserved
test_no_real_llm_provider_imported
test_no_streaming_added
test_healthz_contract_unchanged
test_no_readyz_added_by_ticket21
```

---

## 14. Acceptance Criteria

Ticket 21 passes only if:

```text
GET /plants/{plant_id}/companion-recommendations exists.
Direct endpoint returns deterministic recommendations.
companion_plant_question is supported through chat.
Chat answer follows [결론][근거][행동][주의].
Recommendation uses current species profile.
Recommendation uses environment snapshot.
Recommendation uses companion candidates.
Ticket 20 CompanionCompatibilityFilter is used.
Compatibility scoring is not reimplemented.
Incompatible candidates are excluded.
Current plant species is excluded.
Reasons include light/humidity/temperature/room suitability.
Caution notes are included when available.
source_chunk_ids are preserved.
Chat response includes prompt_hash/provider/model metadata.
No marketplace/purchase/affiliate fields exist.
No ML ranking is implemented.
No real LLM provider is implemented.
No streaming is implemented.
No Redis/worker/vLLM is introduced.
No schema migration is introduced.
Existing care and pest chat paths remain valid.
/healthz remains liveness-only.
/readyz is not introduced or modified.
pytest passes.
ruff passes.
Docker smoke and curl API gates pass.
```
