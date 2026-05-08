# TICKET-023 — End-to-End MVP Demo Seed

## 0. 목표

Sunshine MVP를 시연하기 위한 deterministic demo seed와 재현 가능한 demo scenario를 만든다.

이 티켓은 full E2E test harness를 만들지 않는다.  
이 티켓은 frontend/mobile/browser automation을 만들지 않는다.  
이 티켓은 production seed data를 만들지 않는다.  
이 티켓은 API/domain/LLM/retrieval behavior를 변경하지 않는다.

Ticket 23의 책임은 아래까지만이다.

```text
demo seed data
  -> idempotent seed runner
  -> deterministic demo scenario definition
  -> smoke-level demo verification
```

---

## 1. Ticket Identity

### Ticket ID

```text
TICKET-023
```

### Name

```text
End-to-End MVP Demo Seed
```

### Goal

```text
Provide deterministic demo seed data and a reproducible MVP demo scenario.
```

### Core output

```text
demo species profiles
demo user
demo plant
demo sensor readings
demo RAG chunks
demo companion candidates
idempotent seed runner
demo scenario script/check
smoke-level demo verification
```

### Strict non-goal

```text
no full E2E CI harness
no browser automation
no frontend/mobile UI
no real auth
no production seed dataset
no new API behavior
no domain logic changes
no LLM provider changes
no new retrieval strategy
no marketplace integration
no Redis/worker/vLLM service
```

---

## 2. 주변 티켓과의 연결

Ticket 23은 MVP 기능을 새로 구현하지 않고, 이미 구현된 기능을 시연할 수 있는 seed와 scenario만 제공한다.

```text
Ticket 7:
  environment snapshot aggregation이 demo sensor readings를 소비

Ticket 8:
  Rule Engine이 demo species/snapshot/care data를 소비

Ticket 11:
  demo watering care log scenario에 필요

Ticket 13:
  demo chat question intent classification에 필요

Ticket 14:
  demo RAG chunks 저장/검색에 필요

Ticket 18:
  care chat answer demo path에 필요

Ticket 21:
  companion recommendation demo path에 필요

Ticket 22:
  demo chat answer evidence query에 필요

Ticket 24:
  이 seed/scenario를 full E2E harness로 검증
```

Ticket 23의 역할:

```text
stable demo records
  + fixed timestamps
  + canonical IDs
  + demo script
  -> reproducible MVP scenario
```

금지:

```text
API 구현
Rule Engine 수정
RAG retrieval 수정
PromptBuilder 수정
LLMPort 수정
companion filter 수정
full E2E test harness 구현
frontend/browser automation 구현
production seed data 생성
```

---

## 3. 수정/생성 허용 파일

### 생성 가능한 새 파일

```text
app/demo/__init__.py
app/demo/seed_data.py
app/demo/seed_runner.py
app/demo/scenario.py

scripts/seed_demo.py
scripts/run_demo_scenario.py
scripts/__init__.py

docs/demo_seed.md

tests/test_demo_seed.py
tests/test_demo_scenario.py
tests/fixtures/demo_seed_fixtures.py
```

### 조건부 생성 가능 파일

```text
app/repositories/demo_seed_repository.py
```

조건:

```text
existing repository/session helper를 호출하는 fixture adapter만 허용한다.
새 table, 새 schema, 새 business behavior를 만들지 않는다.
```

### 조건부 migration 허용

```text
alembic/versions/<ticket23_demo_seed_metadata>.py
```

원칙:

```text
Preferred: no migration.
Only if existing schema cannot represent required demo records.
If used, migration must be append-only and limited to harmless demo marker metadata.
```

금지 migration:

```text
new product behavior table
new auth table
new chat behavior table
new recommendation algorithm table
new LLM/provider table
new frontend/admin table
```

---

## 4. 금지 파일/디렉터리

아래 경로는 생성하거나 수정하지 않는다.

```text
app/api/
app/api/chat.py
app/api/companion.py
app/api/plants.py

app/services/chat_orchestrator.py
app/services/rule_engine.py
app/services/companion_filter.py
app/services/companion_recommendation.py
app/services/evidence_builder.py
app/services/prompt_builder.py

app/llm/
app/vision/
app/mqtt/
app/workers/

Dockerfile
docker-compose.yml
.env.example
.github/workflows/

frontend/
web/
mobile/
```

규칙:

```text
Ticket 23 must not modify API behavior, domain rules, infrastructure, LLM runtime, worker topology, or frontend implementation.
```

---

## 5. Demo Seed 계약

### Species profiles

정확히 아래 3개 species를 seed한다.

```text
species-monstera:
  ko: 몬스테라
  en: Monstera
  light: medium indirect
  humidity: medium-high
  temperature: warm indoor
  care: avoid overwatering

species-pothos:
  ko: 스킨답서스
  en: Pothos
  light: low-medium indirect
  humidity: medium
  temperature: warm indoor
  caution: pet/child ingestion caution if metadata supports it

species-philodendron:
  ko: 필로덴드론
  en: Philodendron
  light: medium indirect
  humidity: medium-high
  temperature: warm indoor
  caution: pet/child ingestion caution if metadata supports it
```

### Demo user

```json
{
  "user_id": "demo-user-001",
  "display_name": "Demo User"
}
```

### Demo plant

```json
{
  "plant_id": "demo-plant-chorok-001",
  "user_id": "demo-user-001",
  "species_id": "species-monstera",
  "nickname": "초록이",
  "room": "거실",
  "room_id": "demo-room-living-001"
}
```

규칙:

```text
DB/API canonical ID는 ASCII-safe여야 한다.
Korean text는 display field에만 둔다.
```

---

## 6. Sensor Reading 계약

Seed data는 snapshot과 rule demo가 가능해야 한다.

필수:

```text
at least 8 readings over 24h
at least 14 readings over 7d
3h cadence where practical
fixed measured_at timestamps
no now()
no random time
```

Anchor time:

```text
DEMO_ANCHOR_TIME = 2026-05-04T09:00:00+09:00
```

Demo watering question:

```text
물 또 줘야 해?
```

Expected rule outcome:

```text
no_watering or watering_not_needed
```

근거:

```text
recent watering log exists
soil moisture remains adequate
```

---

## 7. RAG Chunk 계약

Seed deterministic RAG chunks for:

```text
species_profile
care_knowledge
pest_disease_reference
companion_plant
```

필수 chunk id:

```text
chunk-demo-monstera-care-001
chunk-demo-monstera-watering-001
chunk-demo-pest-reference-001
chunk-demo-companion-pothos-001
chunk-demo-companion-philodendron-001
```

Example:

```json
{
  "chunk_id": "chunk-demo-monstera-watering-001",
  "rag_layer": "care_knowledge",
  "species_id": "species-monstera",
  "source": "demo_seed",
  "text": "몬스테라는 흙이 충분히 젖어 있으면 추가 물주기를 피하는 편이 안전합니다."
}
```

금지:

```text
web scraping
large public dataset ingestion
external embedding call
new retrieval strategy
reranker
CRAG
Self-RAG
HyDE
multi-query retrieval
```

---

## 8. Companion Candidate 계약

Seed companion candidates:

```text
species-pothos
species-philodendron
```

Ticket 20/21 기준 예상 결과:

```text
at least one compatible candidate returned
reasons include light / humidity / temperature / room suitability
caution notes included when metadata exists
no marketplace/purchase fields
```

금지:

```text
marketplace ranking
purchase link
affiliate link
ML ranking
LLM-generated candidate selection
```

---

## 9. Demo Scenario 계약

아래 12-step scenario를 deterministic하게 정의한다.

```text
1. register plant
2. confirm species
3. create character
4. ingest sensor reading
5. update snapshot
6. run Rule Engine
7. update mood
8. log watering
9. ask “물 또 줘야 해?”
10. receive fixed-format grounded answer
11. ask companion recommendation
12. receive compatible recommendation
```

규칙:

```text
Ticket 23 may add a demo script that calls existing APIs/services.
Ticket 23 must not implement the APIs/services themselves.
```

Scenario output should be checkable as data:

```text
step name
input summary
expected existing component
expected output marker
```

---

## 10. Seed Runner 계약

Required module:

```text
app/demo/seed_runner.py
```

Required behavior:

```text
1. Build deterministic seed records.
2. Validate canonical IDs.
3. Validate fixed timestamps.
4. Validate required species/user/plant/sensor/RAG/candidate records.
5. Apply records through existing repository/session boundary if --apply.
6. Running twice must not duplicate records.
7. Conflicting existing canonical ID must fail with controlled error.
```

Suggested modes:

```text
--check-only
--apply
--reset-demo
```

Default:

```text
--check-only
```

금지:

```text
random UUID generation
wall-clock now()
external network calls
automatic destructive reset by default
production seed insertion by default
```

---

## 11. CLI 계약

Optional CLI files:

```text
scripts/seed_demo.py
scripts/run_demo_scenario.py
```

`seed_demo.py --check-only` must return summary JSON:

```json
{
  "mode": "check-only",
  "species_count": 3,
  "user_id": "demo-user-001",
  "plant": {
    "plant_id": "demo-plant-chorok-001",
    "nickname": "초록이"
  },
  "sensor_reading_count": 14,
  "rag_chunk_count": 5,
  "companion_candidate_count": 2,
  "deterministic": true
}
```

---

## 12. Runtime 계약

Allowed runtime shape:

```text
Mode A: test fixture / in-process seed
  -> import app.demo.seed_data
  -> build deterministic records
  -> apply to test repository fixture

Mode B: one-shot local script
  -> scripts/seed_demo.py --check-only|--apply
  -> optionally call existing local backend APIs
```

Forbidden runtime shape:

```text
new long-running worker
new MQTT broker
new Redis worker
new vLLM server
new frontend dev server
new scheduler
new model loader
```

Process invariant:

```text
one-shot
deterministic
idempotent
bounded
non-daemon
```

Network invariant:

```text
0 new ports
0 new Docker services
0 external network calls
localhost HTTP to existing backend routes is allowed only in demo script mode
```

Env invariant:

```text
no new production env vars
prefer CLI flags over env vars
```

Allowed optional local-only env:

```text
DEMO_SEED_MODE=check|apply|reset
```

Forbidden env:

```text
OPENAI_*
ANTHROPIC_*
VLLM_*
MARKETPLACE_*
KAGGLE_*
REDIS_*
MQTT_*
POLARIS_*
GPU_*
```

Health invariant:

```text
Do not modify GET /healthz.
Do not add or modify GET /readyz.
```

---

## 13. Functional Gate — Executable

Create or run a local gate equivalent to:

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "[Gate 1] Python quality"
ruff check app/demo scripts tests/test_demo_seed.py tests/test_demo_scenario.py
ruff format --check app/demo scripts tests/test_demo_seed.py tests/test_demo_scenario.py

echo "[Gate 2] Demo seed tests"
pytest -q tests/test_demo_seed.py tests/test_demo_scenario.py

echo "[Gate 3] No future-feature or nondeterminism leakage"
python - <<'PY'
from pathlib import Path

targets = [
    Path("app/demo/seed_data.py"),
    Path("app/demo/seed_runner.py"),
    Path("app/demo/scenario.py"),
]

for path in targets:
    text = path.read_text()
    forbidden = [
        "httpx", "requests", "aiohttp", "openai", "anthropic", "vllm",
        "redis", "paho", "socket", "grpc", "kaggle", "marketplace",
        "purchase", "affiliate", "torch", "tensorflow", "cv2", "Polaris",
        "NCCL", "cuda", "StreamingResponse", "WebSocket",
        "datetime.now(", "uuid.uuid4(", "random.", "secrets.",
    ]
    hits = [token for token in forbidden if token in text]
    assert not hits, f"{path}: forbidden leakage or nondeterminism: {hits}"

print("ticket23_no_future_feature_or_nondeterminism_leakage: pass")
PY

echo "[Gate 4] Seed content check"
python - <<'PY'
from app.demo.seed_data import build_demo_seed

seed = build_demo_seed()

assert {s.species_id for s in seed.species} == {
    "species-monstera",
    "species-pothos",
    "species-philodendron",
}
assert seed.user.user_id == "demo-user-001"
assert seed.plant.plant_id == "demo-plant-chorok-001"
assert seed.plant.nickname == "초록이"
assert seed.plant.room == "거실"
assert seed.plant.species_id == "species-monstera"
assert len(seed.sensor_readings) >= 14
assert len(seed.rag_chunks) >= 5
assert {"species_profile", "care_knowledge", "pest_disease_reference", "companion_plant"}.issubset(
    {c.rag_layer for c in seed.rag_chunks}
)
assert {"species-pothos", "species-philodendron"}.issubset(
    {c.species_id for c in seed.companion_candidates}
)
print("demo_seed_exact_contents: pass")
PY

echo "[Gate 5] Scenario check"
python - <<'PY'
from app.demo.seed_data import build_demo_seed
from app.demo.scenario import build_demo_scenario

scenario = build_demo_scenario(build_demo_seed())
assert [s.name for s in scenario.steps] == [
    "register_plant",
    "confirm_species",
    "create_character",
    "ingest_sensor_reading",
    "update_snapshot",
    "run_rule_engine",
    "update_mood",
    "log_watering",
    "ask_watering_question",
    "receive_fixed_format_grounded_answer",
    "ask_companion_recommendation",
    "receive_compatible_recommendation",
]
assert scenario.question_watering == "물 또 줘야 해?"
assert scenario.question_companion == "같이 키우기 좋은 식물 추천해줘"
print("demo_scenario_sequence: pass")
PY

echo "[Gate 6] CLI check-only"
python scripts/seed_demo.py --check-only

echo "[Gate 7] Runtime regression"
docker build -t sunshine-backend:ticket23 .
docker run -d --name sunshine-backend-ticket23 -p 8000:8000 \
  -e APP_NAME=sunshine-backend \
  -e APP_ENV=local \
  sunshine-backend:ticket23
trap 'docker rm -f sunshine-backend-ticket23 >/dev/null 2>&1 || true' EXIT

for i in $(seq 1 30); do
  if curl -fsS http://localhost:8000/healthz >/tmp/healthz.ticket23.json; then
    break
  fi
  sleep 1
done

test -s /tmp/healthz.ticket23.json
python - <<'PY'
import json
from pathlib import Path
body = json.loads(Path("/tmp/healthz.ticket23.json").read_text())
assert body == {"status": "ok", "service": "sunshine-backend"}, body
print("healthz_liveness_regression: pass")
PY

echo "[Gate 8] No Ticket 24/browser/readiness leakage"
! grep -R "test_e2e\|Playwright\|Selenium\|Cypress\|browser\|readyz" app scripts tests
```

---

## 14. Required Tests

Add tests for:

```text
demo seed contains exactly three species
demo seed contains demo user
demo seed contains demo plant 초록이 in 거실
demo seed contains sensor readings for 24h and 7d
demo seed contains RAG chunks for required layers
demo seed contains companion candidates
demo seed uses fixed anchor time
demo seed uses canonical IDs
demo seed has no random UUID or now()
seed runner is idempotent
conflicting canonical ID fails
demo scenario has exact 12 steps
watering question is fixed
companion question is fixed
check-only CLI outputs summary JSON
no full E2E harness added
healthz contract unchanged
readyz not added
```

---

## 15. Acceptance Criteria

Ticket 23 passes only if all are true.

```text
deterministic demo seed builder exists
seed includes Monstera, Pothos, Philodendron
seed includes demo-user-001
seed includes demo-plant-chorok-001 / 초록이 / 거실
seed includes sensor readings sufficient for latest/24h/7d snapshots
seed includes RAG chunks for species_profile, care_knowledge, pest_disease_reference, companion_plant
seed includes companion candidates
seed uses fixed timestamps
seed uses stable canonical IDs
seed runner is idempotent
check-only CLI outputs summary JSON
demo scenario has exact 12-step MVP sequence
watering demo question is “물 또 줘야 해?”
companion demo question is “같이 키우기 좋은 식물 추천해줘”
no production seed data is introduced
no real auth is implemented
no full E2E test harness is implemented
no frontend/browser automation is implemented
no external network dependency is introduced
no new runtime service is introduced
/healthz remains liveness-only
/readyz is not introduced or modified
pytest passes
ruff passes
Docker smoke gate passes
```

---

## 16. Antigravity 실행 지시

```text
Implement TICKET-023 only.
Follow the allowed/forbidden file lists exactly.
Create deterministic demo seed data and demo scenario tooling only.
Do not modify API behavior or domain services.
Do not implement Ticket 24 E2E harness.
Do not add frontend, browser automation, auth, production seed data, LLM provider, worker, Redis, MQTT, vLLM, or new Docker service.
Run the functional gate and report changed files, commands, and pass/fail evidence.
```
