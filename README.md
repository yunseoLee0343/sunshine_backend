# Sunshine Backend

AI-powered plant care API — hybrid RAG chat, deterministic rule engine, and sensor-driven character state.

**Stack:** FastAPI · SQLAlchemy (async) · PostgreSQL 16 · Claude LLM · MQTT

---

## Table of Contents

1. [Quick Start (Docker)](#quick-start-docker)
2. [Local Development Setup](#local-development-setup)
3. [Environment Variables](#environment-variables)
4. [Database Migrations & Seed Data](#database-migrations--seed-data)
5. [Golden Path Demo (12 Steps)](#golden-path-demo-12-steps)
6. [API Reference](#api-reference)
7. [Quality Gate](#quality-gate)
8. [Architecture Notes](#architecture-notes)

---

## Quick Start (Docker)

```bash
# 1. Copy env template
cp .env.example .env

# 2. Start all services (backend + postgres + mqtt)
docker compose up --build -d

# 3. Run migrations
docker compose exec backend alembic upgrade head

# 4. Load demo seed data
docker compose exec backend python -m app.seeds.demo_seed

# 5. Confirm health
curl http://localhost:8000/healthz
# → {"status":"ok","service":"sunshine-backend"}

# 6. Open interactive API docs
open http://localhost:8000/docs
```

---

## Local Development Setup

**Prerequisites:** Python 3.12+, PostgreSQL 16, (optional) MQTT broker

```bash
# Clone and enter the project
cd sunshine_backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Install runtime + dev dependencies
pip install -e ".[dev]"

# Set environment variables
cp .env.example .env
# Edit .env: set DATABASE_URL to your local Postgres instance

# Run migrations
alembic upgrade head

# Load demo seed data
python -m app.seeds.demo_seed

# Start the server
uvicorn app.main:app --reload --port 8000
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | _(required)_ | `postgresql+asyncpg://user:pass@host:5432/db` |
| `APP_ENV` | `local` | Runtime environment label (`local`, `production`) |
| `APP_NAME` | `sunshine-backend` | Service name included in health responses |
| `DATABASE_HOST` | `localhost` | Ignored when `DATABASE_URL` is set directly |
| `DATABASE_PORT` | `5432` | Ignored when `DATABASE_URL` is set directly |
| `DATABASE_NAME` | `sunshine` | Ignored when `DATABASE_URL` is set directly |
| `DATABASE_USER` | `sunshine` | Ignored when `DATABASE_URL` is set directly |
| `DATABASE_PASSWORD` | `change-me-local-only` | **Change before any shared deployment** |
| `MQTT_HOST` | `localhost` | MQTT broker host for the sensor ingest worker |
| `MQTT_PORT` | `1883` | MQTT broker port |

---

## Database Migrations & Seed Data

```bash
# Apply all migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Generate a new migration (after model changes)
alembic revision --autogenerate -m "describe_change"

# Load demo seed (idempotent — safe to run multiple times)
python -m app.seeds.demo_seed
```

### Demo Seed Entities

All demo entities use **stable UUID5 keys** — re-running the seed is safe.

| Entity | ID |
|--------|----|
| Demo user | `2a307656-dfbb-55f6-9054-007f2014e4a9` |
| Plant: 초록이 (Monstera) | `23d1867e-f2d0-5bf7-a4c3-f3568c06aeea` |
| Species: Monstera deliciosa | `bc8ce428-d40b-539e-9fbe-f31d002d279c` |
| Species: Pothos | `a8223861-98c6-517a-a0ff-673f7b2ca316` |

---

## Golden Path Demo (12 Steps)

All commands below use the stable demo UUIDs. Set these shell variables first:

```bash
BASE=http://localhost:8000
USER_ID=2a307656-dfbb-55f6-9054-007f2014e4a9
PLANT_ID=23d1867e-f2d0-5bf7-a4c3-f3568c06aeea
SPECIES_ID=bc8ce428-d40b-539e-9fbe-f31d002d279c
```

---

### Step 1 — Verify seed data: home screen

```bash
curl -s "$BASE/home" \
  -H "X-User-Id: $USER_ID" | jq .
```

Expected: `plants` array contains 초록이 with `care_status` and `character` fields.

---

### Step 2 — Retrieve plant detail

```bash
curl -s "$BASE/plants/$PLANT_ID" \
  -H "X-User-Id: $USER_ID" | jq .
```

Expected: `plant.nickname = "초록이"`, species Korean name is `"몬스테라"`.

---

### Step 3 — List all plants for user

```bash
curl -s "$BASE/plants" \
  -H "X-User-Id: $USER_ID" | jq .
```

---

### Step 4 — Inject sensor reading (trigger watering rule)

```bash
curl -s -X POST "$BASE/sensor-readings" \
  -H "Content-Type: application/json" \
  -d "{
    \"plant_id\": \"$PLANT_ID\",
    \"metric\": \"soil_moisture_pct\",
    \"value\": 18.5,
    \"recorded_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
  }" | jq .
```

A value below the Monstera threshold (25%) will trigger the watering rule when
the rule engine is evaluated.

---

### Step 5 — Run rule engine sync (internal dev trigger)

```bash
curl -s -X POST "$BASE/internal/rule-character-sync/$PLANT_ID" | jq .
```

Expected: `condition` reflects low soil moisture → character mood shifts to
indicate watering is needed.

---

### Step 6 — Check environment snapshot & character explanation

```bash
curl -s "$BASE/plants/$PLANT_ID/environment" \
  -H "X-User-Id: $USER_ID" | jq .
```

Expected: `snapshots` array with soil moisture stats; `character_explanation`
describes the current mood reasoning.

---

### Step 7 — Log a manual watering action

```bash
curl -s -X POST "$BASE/plants/$PLANT_ID/care-logs" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $USER_ID" \
  -d "{
    \"action_type\": \"watering\",
    \"acted_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
  }" | jq .
```

Expected 201: `log.action_type = "watering"` and `character` block showing
updated mood (watered_recently).

---

### Step 8 — Chat: watering question

```bash
REQUEST_ID=$(python -c "import uuid; print(uuid.uuid4())")

curl -s -X POST "$BASE/plants/$PLANT_ID/chat" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $USER_ID" \
  -d "{
    \"request_id\": \"$REQUEST_ID\",
    \"question\": \"몬스테라에 물을 얼마나 자주 줘야 해?\"
  }" | jq '{intent, answer, from_cache}'
```

Expected: `intent = "watering_question"`, `answer` has 결론/근거/행동/주의 sections.
Save `$REQUEST_ID` for Step 12.

---

### Step 9 — Chat idempotency check (replay same request_id)

```bash
curl -s -X POST "$BASE/plants/$PLANT_ID/chat" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $USER_ID" \
  -d "{
    \"request_id\": \"$REQUEST_ID\",
    \"question\": \"몬스테라에 물을 얼마나 자주 줘야 해?\"
  }" | jq '.from_cache'
```

Expected: `true` — cached response returned without LLM call.

---

### Step 10 — Chat: pest reference question (guardrail)

```bash
PEST_REQUEST_ID=$(python -c "import uuid; print(uuid.uuid4())")

curl -s -X POST "$BASE/plants/$PLANT_ID/chat" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $USER_ID" \
  -d "{
    \"request_id\": \"$PEST_REQUEST_ID\",
    \"question\": \"잎에 점이 생겼는데 병충해인가요?\"
  }" | jq '{intent, is_reference_only, diagnosis_allowed}'
```

Expected: `is_reference_only = true`, `diagnosis_allowed = false` — guardrail
returns reference information without issuing a diagnosis.

---

### Step 11 — Companion plant recommendations

```bash
curl -s "$BASE/plants/$PLANT_ID/companion-recommendations" \
  -H "X-User-Id: $USER_ID" | jq '{candidates_assessed, recommendations: [.recommendations[] | {common_name, compatibility_score}]}'
```

Expected: ranked list of compatible species with `compatibility_score >= 0.5`.

---

### Step 12 — Audit trail: inspect evidence bundle for chat run

```bash
curl -s "$BASE/chat-runs/$REQUEST_ID/evidence" | jq '{
  intent,
  prompt_hash,
  rag_layers,
  retrieved_chunks: (.retrieved_chunks | length),
  rule_primary_action,
  answer_결론: .answer.결론
}'
```

Expected: full decision evidence — which RAG layers were used, which knowledge
chunks were retrieved, the rule engine outcome, and the final answer with its
`prompt_hash` for integrity verification.

---

## API Reference

Interactive docs: **`GET /docs`** (Swagger UI) · **`GET /redoc`** (ReDoc)

| Tag | Endpoints |
|-----|-----------|
| **plants** | `POST /plants/species-candidates` · `POST /plants` · `GET /plants` · `GET /plants/{id}` · `POST /plants/{id}/character-state` · `POST /plants/{id}/chat` |
| **home** | `GET /home` · `GET /plants/{id}/card` |
| **sensor-readings** | `POST /sensor-readings` |
| **care-logs** | `POST /plants/{id}/care-logs` · `GET /plants/{id}/care-logs` |
| **companion** | `GET /plants/{id}/companion-recommendations` |
| **environment** | `GET /plants/{id}/environment` |
| **chat** | `POST /chat/intent` |
| **retrieval** | `POST /retrieval/query` |
| **evidence** | `POST /evidence/build` |
| **audit** | `GET /chat-runs/{request_id}/evidence` |
| **internal** | `POST /internal/rule-character-sync/{plant_id}` · `GET /healthz` · `GET /readyz` |

### User Identity

All user-scoped endpoints accept identity in order of precedence:

1. **`X-User-Id: <uuid>`** header — preferred
2. **`?user_id=<uuid>`** query parameter (GET routes) or **`user_id`** in request body (POST routes)

Missing identity returns `422`. Wrong user on an owned resource returns `403`.

---

## Quality Gate

```bash
# Run all checks (lint + format + tests + coverage ≥ 80%)
bash scripts/check_gate.sh

# Lint + format only (no tests)
SKIP_TESTS=1 bash scripts/check_gate.sh

# Tests with coverage report
python -m pytest --ignore=tests/e2e -q --cov --cov-report=term-missing

# E2E tests (requires live DATABASE_URL)
DATABASE_URL=postgresql+asyncpg://... python -m pytest tests/e2e -v -m e2e
```

---

## Architecture Notes

```
Request
  └─► FastAPI router
        ├─ Auth: X-User-Id header → CurrentUser
        ├─ POST /plants/{id}/chat
        │    ├─ Intent classification (regex mock / lightweight classifier)
        │    ├─ Evidence builder
        │    │    ├─ Character state (latest PlantCharacter row)
        │    │    ├─ Environment snapshot (latest EnvironmentSnapshot)
        │    │    ├─ Rule engine (RuleEngine.evaluate → facts + reason_codes)
        │    │    └─ Hybrid retrieval (vector cosine + BM25 → top-k chunks)
        │    ├─ Prompt builder (assembles context → prompt text + hash)
        │    ├─ LLM port (Claude API / mock) → ParsedAnswer {결론,근거,행동,주의}
        │    ├─ Pest guardrail (is_reference_only / diagnosis_allowed flags)
        │    └─ Persist: ChatRequest + LlmRun + EvidenceBundle
        └─ GET /chat-runs/{id}/evidence
             └─ AuditQueryService → ChatRunEvidenceView
```

**Idempotency:** All chat and retrieval endpoints accept a caller-supplied `request_id` (UUID).
Re-submitting the same `request_id` returns the cached result without re-invoking the LLM.

**Seed data stability:** Demo entities use UUID5 (namespace + name) so the same IDs are
reproduced on every fresh database without coordination.
