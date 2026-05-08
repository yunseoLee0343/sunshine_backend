# TICKET-020 — Companion Plant Compatibility Filter

## 0. 목표

Sunshine 백엔드에 동반 식물 후보를 **결정론적으로 필터링하는 코어 서비스**를 구현한다.

이 티켓은 API를 만들지 않는다.  
이 티켓은 채팅 답변을 만들지 않는다.  
이 티켓은 LLM을 호출하지 않는다.  
이 티켓은 추천 결과를 DB에 저장하지 않는다.

Ticket 20의 책임은 아래까지만이다.

```text
current_species_profile
  + room_environment_snapshot
  + companion_candidate_records
  -> deterministic compatibility filter
  -> compatible / borderline candidates
  -> score + reasons + caution notes 반환
```

---

## 1. Ticket Identity

### Ticket ID

```text
TICKET-020
```

### Name

```text
Companion Plant Compatibility Filter
```

### Goal

```text
Build a deterministic compatibility filter for companion plant candidates using plant profile, room environment, and candidate metadata.
```

### Core output

```text
companion domain objects
compatibility filter service
light compatibility check
humidity compatibility check
temperature compatibility check
room suitability check
deterministic score
machine-readable reasons
caution notes
stable sorted result
unit tests
```

### Strict non-goal

```text
no companion recommendation API
no chat integration
no LLM explanation
no PromptBuilder change
no LLMPort change
no MockLLM change
no DB migration
no new table
no persistence
no RAG ingestion
no reranker
no CRAG
no Self-RAG
no HyDE
no marketplace integration
no purchase/affiliate link
no ML ranking
no worker
no Redis
no streaming
```

---

## 2. 주변 티켓과의 연결

Ticket 20은 companion recommendation의 **계산 코어**다.

```text
Ticket 7:
  room/environment snapshot을 제공

Ticket 13:
  companion_plant_question intent를 분류

Ticket 14:
  companion_plant 후보 지식 chunk를 제공할 수 있음

Ticket 20:
  후보 식물을 deterministic compatibility 기준으로 필터링

Ticket 21:
  Ticket 20 결과를 API/chat recommendation으로 노출

Ticket 22:
  추천/evidence audit 조회를 담당
```

Ticket 20의 역할:

```text
current plant species
  + room snapshot
  + companion candidates
  -> compatible candidates with score/reasons/cautions
```

금지:

```text
HTTP endpoint 생성
chat answer 생성
LLM 설명 생성
후보 검색/RAG 구현 변경
DB 저장
marketplace 연동
ML ranking
```

---

## 3. 수정/생성 허용 파일

### 생성 가능한 새 파일

```text
app/domain/companion.py
app/services/companion_filter.py
tests/test_companion_filter.py
tests/fixtures/companion_fixtures.py
```

### 조건부 수정 가능 파일

```text
app/domain/__init__.py
app/services/__init__.py
```

조건:

```text
패키지 import marker가 필요한 경우에만 수정한다.
```

### 조건부 repository 파일

```text
app/repositories/companion_repository.py
```

조건:

```text
이미 repository port 패턴이 존재하고 타입 정렬이 필요한 경우에만 허용한다.
이 파일은 Protocol/interface 또는 fixture adapter boundary로만 사용한다.
새 DB schema 구현은 금지한다.
```

---

## 4. 금지 파일/디렉터리

아래 경로는 생성하거나 수정하지 않는다.

```text
app/api/
app/api/companion.py
app/api/chat.py
app/services/chat_orchestrator.py
app/services/prompt_builder.py
app/services/evidence_builder.py
app/llm/
app/vision/
app/mqtt/
app/workers/
app/retrieval/reranker.py
app/retrieval/crag.py
alembic/
migrations/
Dockerfile
docker-compose.yml
.env.example
.github/workflows/
```

규칙:

```text
Ticket 20 must not expose recommendation through API or chat.
Ticket 20 must not modify prompt, LLM, retrieval, evidence, persistence, Docker, CI, or runtime topology.
```

---

## 5. Domain Schema 계약

아래 파일을 생성한다.

```text
app/domain/companion.py
```

필수 개념:

```text
EnvironmentRange
SpeciesCareProfile
RoomEnvironmentSnapshot
CompanionCandidate
CompatibilityReason
CompanionCompatibilityResult
CompatibilityDecision
```

필수 decision 값:

```text
compatible
borderline
incompatible
```

필수 입력 필드:

```text
current species:
  species_id
  common_name
  light_lux range
  humidity_pct range
  temperature_c range
  room_tags
  toxicity_notes
  pet_child_caution

room snapshot:
  room_id
  light_lux_avg
  humidity_pct_avg
  temperature_c_avg
  room_tags

candidate:
  species_id
  common_name
  profile
  source_chunk_ids
```

필수 출력 필드:

```text
candidate
decision
score
reasons
caution_notes
source_chunk_ids
```

금지 필드:

```text
final_answer
prompt
llm_response
marketplace_url
purchase_url
affiliate_url
ml_rank_score
embedding_score
diagnosis
treatment
```

---

## 6. CompanionCompatibilityFilter 계약

아래 파일을 생성한다.

```text
app/services/companion_filter.py
```

필수 class shape:

```python
class CompanionCompatibilityFilter:
    def filter(
        self,
        *,
        current_species: SpeciesCareProfile,
        room_snapshot: RoomEnvironmentSnapshot,
        candidates: tuple[CompanionCandidate, ...],
        limit: int = 5,
    ) -> tuple[CompanionCompatibilityResult, ...]:
        ...
```

필수 동작:

```text
1. Validate limit > 0.
2. Exclude candidate if species_id equals current_species.species_id.
3. De-duplicate candidates by species_id deterministically.
4. Evaluate light compatibility.
5. Evaluate humidity compatibility.
6. Evaluate temperature compatibility.
7. Evaluate room suitability.
8. Reject incompatible candidates.
9. Attach score and machine-readable reasons.
10. Attach toxicity/pet/child caution notes.
11. Sort results deterministically.
12. Return at most limit results.
```

금지 동작:

```text
DB query
network call
LLM call
PromptBuilder call
retrieval call
marketplace lookup
file read/write
input mutation
wall-clock dependent scoring
random scoring
```

---

## 7. Compatibility Rule 계약

### Light

```text
Input:
room_snapshot.light_lux_avg
candidate.profile.light_lux

compatible:
  room light is inside candidate range

borderline:
  room light is outside candidate range but within ±15% tolerance

incompatible:
  room light is far outside candidate range or range is invalid
```

### Humidity

```text
Input:
room_snapshot.humidity_pct_avg
candidate.profile.humidity_pct

compatible:
  room humidity is inside candidate range

borderline:
  outside range but within ±10 percentage points

incompatible:
  far outside candidate range or range is invalid
```

### Temperature

```text
Input:
room_snapshot.temperature_c_avg
candidate.profile.temperature_c

compatible:
  room temperature is inside candidate range

borderline:
  outside range but within ±2°C

incompatible:
  far outside candidate range or range is invalid
```

### Room suitability

```text
Input:
room_snapshot.room_tags
candidate.profile.room_tags

compatible:
  room tag overlaps or candidate has no strict room tag

borderline:
  no overlap but candidate is generally indoor-suitable

incompatible:
  candidate requires clearly excluded condition such as full-sun balcony while room is low-light indoor
```

Missing snapshot value rule:

```text
If a room metric is missing, mark that dimension as borderline.
Do not fabricate sensor values.
```

---

## 8. Score 계약

Dimension score:

```text
compatible: +25
borderline: +10
incompatible: reject candidate
```

Final score:

```text
max 100
min 0
```

Final decision:

```text
compatible:
  score >= 80 and no incompatible dimension

borderline:
  score >= 50 and no incompatible dimension

incompatible:
  any incompatible dimension or score < 50
```

Sorting:

```text
1. compatible before borderline
2. higher score first
3. common_name ascending
4. species_id ascending
```

---

## 9. Caution Notes 계약

후보 metadata에 아래 정보가 있으면 결과에 보존한다.

```text
toxicity_notes
pet_child_caution
```

예시:

```json
{
  "candidate": "스킨답서스",
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
```

---

## 10. Runtime 계약

Ticket 20은 새 runtime process를 추가하지 않는다.

허용 runtime shape:

```text
backend Python process
  -> import CompanionCompatibilityFilter
  -> filter(current_species, room_snapshot, candidates)
  -> return result objects
```

금지 runtime shape:

```text
backend
  -> expose companion API
  -> call LLM
  -> call vector DB
  -> query marketplace
  -> write audit row
  -> start worker
  -> start Redis consumer
```

Process invariant:

```text
pure
synchronous
deterministic
side-effect free
network-free
DB-free
filesystem-free
model-free
```

---

## 11. Network / Env 계약

Ticket 20 must introduce:

```text
0 new routes
0 new ports
0 new Docker services
0 external HTTP calls
0 WebSocket/SSE endpoints
0 new env vars
```

금지 env:

```text
COMPANION_MODEL_*
MARKETPLACE_*
LLM_*
VLLM_*
OPENAI_*
ANTHROPIC_*
REDIS_*
MQTT_*
```

금지 imports/usages:

```text
FastAPI
APIRouter
httpx
requests
aiohttp
openai
anthropic
vllm
sqlalchemy
asyncpg
psycopg
redis
paho
socket
grpc
StreamingResponse
EventSourceResponse
WebSocket
torch
tensorflow
sklearn
```

---

## 12. `/healthz` / `/readyz` 계약

Ticket 20은 아래를 수정하지 않는다.

```http
GET /healthz
```

Ticket 20은 아래를 추가하거나 수정하지 않는다.

```http
GET /readyz
```

이유:

```text
Ticket 20은 pure in-process filter다.
새 external dependency가 없으므로 readiness check 대상이 없다.
```

---

## 13. Functional Gate

Antigravity는 아래 검증을 통과해야 한다.

```bash
ruff check app/domain/companion.py app/services/companion_filter.py tests/test_companion_filter.py
ruff format --check app/domain/companion.py app/services/companion_filter.py tests/test_companion_filter.py
pytest -q tests/test_companion_filter.py
```

Boundary grep:

```bash
! grep -R "FastAPI\|APIRouter\|httpx\|requests\|openai\|anthropic\|vllm\|sqlalchemy\|redis\|paho\|StreamingResponse\|WebSocket\|marketplace\|purchase\|affiliate\|torch\|tensorflow\|sklearn" app/domain/companion.py app/services/companion_filter.py
! grep -R "companion-recommendations" app tests
! grep -R "readyz" app tests
```

Docker regression smoke:

```bash
docker build -t sunshine-backend:ticket20 .
docker run -d --name sunshine-backend-ticket20 -p 8000:8000 -e APP_NAME=sunshine-backend -e APP_ENV=local sunshine-backend:ticket20
curl -fsS http://localhost:8000/healthz
```

Expected `/healthz`:

```json
{
  "status": "ok",
  "service": "sunshine-backend"
}
```

---

## 14. Required Tests

추가할 테스트:

```text
test_filter_returns_compatible_candidates
test_filter_excludes_current_species
test_filter_excludes_incompatible_light_candidate
test_filter_excludes_incompatible_humidity_candidate
test_filter_excludes_incompatible_temperature_candidate
test_filter_uses_room_suitability
test_filter_attaches_light_reason
test_filter_attaches_humidity_reason
test_filter_attaches_temperature_reason
test_filter_attaches_room_reason
test_filter_attaches_toxicity_caution
test_filter_attaches_pet_child_caution
test_filter_is_deterministic
test_filter_has_stable_tie_break_order
test_filter_respects_limit
test_filter_empty_candidates_returns_empty_tuple
test_filter_missing_snapshot_values_do_not_fabricate_evidence
test_filter_rejects_non_positive_limit
test_no_companion_api_added
test_healthz_contract_unchanged
test_no_readyz_added_by_ticket20
```

---

## 15. Acceptance Criteria

Ticket 20 pass 조건:

```text
CompanionCompatibilityFilter exists.
Domain objects exist.
Filter evaluates light compatibility.
Filter evaluates humidity compatibility.
Filter evaluates temperature compatibility.
Filter evaluates room suitability.
Filter returns deterministic score.
Filter returns machine-readable reasons.
Filter excludes incompatible candidates.
Filter excludes current plant species.
Filter attaches toxicity notes when available.
Filter attaches pet/child caution when available.
Output order is stable.
Limit is respected.
Missing snapshot values do not fabricate evidence.
No API endpoint is added.
No chat integration is added.
No LLM explanation is added.
No ML ranking is added.
No marketplace integration is added.
No schema migration is added.
/healthz remains liveness-only.
/readyz is not introduced or modified.
pytest passes.
ruff passes.
Docker smoke gate passes.
```

---

## 16. Antigravity 실행 지시

```text
Implement TICKET-020 only.
Follow the allowed file list strictly.
Create the deterministic companion compatibility filter core.
Do not expose an API.
Do not integrate with chat.
Do not call LLM.
Do not add persistence or migrations.
Do not add Docker/CI/env changes.
Return a final report with changed files, tests run, and boundary non-goals confirmed.
```
