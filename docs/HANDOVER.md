# Sunshine Backend — Project Handover Guide

**Status:** MVP Complete  
**Completed Tickets:** TICKET-001 through TICKET-029  
**Test Coverage:** 83% (gate ≥ 80%)  
**Python:** 3.12 · **DB:** PostgreSQL 16 · **Framework:** FastAPI + SQLAlchemy (async)

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Component Map](#2-component-map)
3. [Data Flow Diagrams](#3-data-flow-diagrams)
4. [Database Schema](#4-database-schema)
5. [Architecture Decision Records (ADR)](#5-architecture-decision-records-adr)
6. [Tech Debt Register](#6-tech-debt-register)
7. [Operations Manual](#7-operations-manual)
8. [Extension Roadmap](#8-extension-roadmap)
9. [Key People & References](#9-key-people--references)

---

## 1. System Overview

Sunshine is an AI-powered plant care assistant. The backend provides:

- **Plant management** — registration, care history, character state (mood/expression)
- **Sensor monitoring** — ingest raw readings (soil moisture, light, humidity, temperature) via REST or MQTT; aggregate into hourly snapshots
- **Deterministic rule engine** — compare sensor snapshots against per-species thresholds to derive care status and recommended action (no LLM involved)
- **Hybrid RAG chat** — classify question intent → retrieve relevant plant knowledge (vector + BM25) → assemble evidence bundle → call Claude → parse structured answer
- **Companion recommendations** — compatibility scoring across species environmental profiles
- **Audit trail** — every chat run persists its full evidence bundle and `prompt_hash` for transparency

### High-Level Architecture

```
┌─────────────┐   REST/MQTT   ┌──────────────────────────────────────────┐
│  Frontend   │──────────────►│           FastAPI Router Layer            │
│  / Devices  │               │  auth: X-User-Id header (MVP, no JWT)     │
└─────────────┘               └───────────┬──────────────────────────────┘
                                           │
           ┌───────────────────────────────┼──────────────────────────┐
           │                               │                          │
    ┌──────▼──────┐              ┌─────────▼────────┐       ┌────────▼───────┐
    │  Rule Engine │              │ Chat Orchestrator │       │ Companion Svc  │
    │  (pure fn)  │              │  (7-step pipeline)│       │ (filter+score) │
    └──────┬──────┘              └─────────┬────────┘       └────────────────┘
           │                               │
    ┌──────▼──────┐              ┌─────────▼────────┐
    │  Character   │              │ Evidence Builder  │
    │  State Eng. │              │ (aggregates ctx)  │
    └─────────────┘              └────┬──────────────┘
                                      │
                         ┌────────────┼────────────┐
                         │            │            │
               ┌─────────▼──┐  ┌──────▼───┐  ┌────▼──────────┐
               │  Retrieval  │  │  Rules   │  │  Env Snapshot │
               │  Service    │  │  Engine  │  │  + Care Logs  │
               │(vector+BM25)│  └──────────┘  └───────────────┘
               └─────────────┘
                         │
               ┌─────────▼──────────┐
               │  PostgreSQL 16     │
               │  (SQLAlchemy async)│
               └────────────────────┘
```

---

## 2. Component Map

### API Layer (`app/api/`)

| File | Prefix | Tag | Responsibility |
|------|--------|-----|----------------|
| `plants.py` | `/plants` | plants | Plant CRUD, species candidates, character state, chat |
| `home.py` | `/home` `/plants/{id}/card` | home | Home-screen summary cards |
| `sensor_readings.py` | `/sensor-readings` | sensor-readings | Raw sensor ingest (REST) |
| `care_logs.py` | `/plants/{id}/care-logs` | care-logs | Manual care logging |
| `companion.py` | `/plants/{id}/companion-recommendations` | companion | Compatibility scoring |
| `environment.py` | `/plants/{id}/environment` | environment | Snapshot summaries |
| `chat.py` | `/chat/intent` | chat | Intent classification only |
| `retrieval.py` | `/retrieval/query` | retrieval | Hybrid retrieval (debug) |
| `evidence.py` | `/evidence/build` | evidence | Evidence bundle (debug) |
| `chat_runs.py` | `/chat-runs/{id}/evidence` | audit | Full decision audit |
| `rule_character_sync.py` | `/internal/...` | internal | Dev trigger for rule sync |

### Service Layer (`app/services/`)

| Service | Purpose | Pure? |
|---------|---------|-------|
| `chat_orchestrator.py` | 7-step RAG pipeline; companion branch | No (I/O) |
| `evidence_builder.py` | Aggregate plant state → ForwardContext | No (I/O) |
| `rule_engine.py` | Evaluate 4 rules → RuleEngineResult | **Yes** |
| `character_state_engine.py` | Map Condition → CharacterState | **Yes** |
| `prompt_builder.py` | ForwardContext → prompt text + hash | **Yes** |
| `hybrid_retriever.py` → `retrieval_service.py` | Vector + BM25 search | No (I/O) |
| `companion_recommendation_service.py` | Rank species compatibility | No (I/O) |
| `companion_filter_service.py` | Filter compatible candidates | **Yes** |
| `pest_reference_guardrail.py` | Block diagnosis; flag reference-only | **Yes** |
| `response_parser.py` | Parse [결론][근거][행동][주의] | **Yes** |
| `plant_onboarding.py` | Create plant + initial character | No (I/O) |
| `care_log_service.py` | Log care + optional character update | No (I/O) |
| `snapshot_service.py` | Aggregate readings → hourly snapshot | No (I/O) |
| `home_card_service.py` | Assemble home-screen card per plant | No (I/O) |
| `audit_query_service.py` | Fetch and format chat run evidence | No (I/O) |

### Embedding & Retrieval (`app/embedding/`, `app/retrieval/`)

| Component | Model | Notes |
|-----------|-------|-------|
| `LocalEmbeddingService` | `paraphrase-multilingual-MiniLM-L12-v2` | Lazy-loaded; L2-normalized; ~117MB |
| `HybridRetriever` | — | Stage 1: relational pre-filter; Stage 2: dot-product over JSONB vectors |
| `ChunkBuildService` | — | Build/update `plant_chunk_documents` + `plant_chunk_embeddings` |

### Rules Module (`app/rules/`)

Four independent pure functions, no I/O:

| Rule | Trigger Condition |
|------|------------------|
| `watering.py` | `soil_moisture_pct < water_min_pct` AND no watering in last N days |
| `light.py` | `light_lux` outside `[light_min, light_max]` |
| `humidity.py` | `humidity_pct` outside `[humidity_min, humidity_max]` |
| `temperature.py` | `temperature_c` outside `[temp_min, temp_max]` |

Aggregation (in `RuleEngine`):
- `care_status`: any `needs_action` wins; else any `watch`; else `good`; else `insufficient_data`
- `primary_action`: water > other actions > watch > none
- `severity`: `high` > `medium` > `low` > `none`

### Data Access Layer (`app/repositories/`)

All repositories follow the Repository Pattern over SQLAlchemy `AsyncSession`. `BaseRepository[T]` provides `add()`, `get(id)`, `delete()`. Specialized repositories add query methods specific to their entity.

---

## 3. Data Flow Diagrams

### 3.1 Sensor → Character State Pipeline

```
IoT Device
  │ MQTT topic: sunshine/{device_id}/sensor
  │ REST:       POST /sensor-readings
  ▼
SensorIngestService
  └─ validate metric name
  └─ write SensorReading row
         │
         ▼ (async, separate trigger)
SnapshotService
  └─ aggregate readings in 1h window
  └─ upsert EnvironmentSnapshot
         │
         ▼ (manual trigger: POST /internal/rule-character-sync/{plant_id})
RuleInputRepository
  └─ get SpeciesThresholds (species_profiles.metadata_json)
  └─ get LatestSnapshot
  └─ get recent CareLog rows
         │
         ▼
RuleEngine.evaluate()              ← pure, no I/O
  └─ watering / light / humidity / temperature rules
  └─ aggregate → RuleEngineResult
         │
         ▼
RuleCharacterSyncService
  └─ map RuleEngineResult.condition → CharacterState
  └─ write PlantCharacter row
```

### 3.2 Chat Pipeline (7 Steps)

```
POST /plants/{plant_id}/chat
  │  {request_id, question}  +  X-User-Id header
  ▼
1. ChatIntentClassifier.classify(question)
   └─ regex → intent label (watering_question, pest_reference_question, …)
   └─ intent → rag_layers mapping
         │
         ▼
2. RetrievalService.query()                 [skipped if rag_layers empty]
   └─ HybridRetriever.retrieve()
      ├─ resolve species_profile → plant_knowledge_entries
      ├─ filter chunks by chunk_kind (from rag_layers)
      └─ dot-product(query_embedding, chunk_embeddings) → top-k
         │
         ▼
3. EvidenceBuilderService.build()
   ├─ PlantCharacter (latest mood / expression)
   ├─ EnvironmentSnapshot (latest sensor averages)
   ├─ CareLog (last 14 days, up to 5)
   ├─ RuleEngine.evaluate() (pure)
   └─ RetrievalResultChunk rows
         │
         ▼
4. PromptBuilder.build(ForwardContext)
   └─ assemble prompt text
   └─ compute prompt_hash (SHA-256)
         │
         ▼
5. MockLLMClient.complete()               ← real Claude in production
   └─ returns raw text with [결론][근거][행동][주의] sections
         │
         ▼
6. ResponseParser.parse()
   └─ extract ParsedAnswer {결론, 근거, 행동, 주의}

   6b. PestReferenceGuardrail                [pest_reference_question only]
       └─ set is_reference_only=True, diagnosis_allowed=False
         │
         ▼
7. Persist: ChatRequest + LlmRun + EvidenceBundle
   └─ return ChatAnswerResponse (idempotent on request_id)
```

### 3.3 Plant Knowledge Build Pipeline (Offline)

```
Excel / structured data
  └─ python -m app.ingestion.plant_knowledge
        │
        ▼
PlantKnowledgeIngestService
  └─ upsert PlantKnowledgeEntry (idempotent on source_row_hash)
  └─ upsert sub-tables:
       PlantCareRequirement, PlantSeasonalWatering, PlantPestReference,
       PlantVisualTrait, PlantPlacement
        │
        ▼
ChunkBuildService.build_all()
  └─ for each PlantKnowledgeEntry:
       └─ build_all_chunks() → deterministic text per chunk_kind
       └─ compare text_hash → skip/insert/update PlantChunkDocument
       └─ LocalEmbeddingService.embed_batch() → vectors
       └─ upsert PlantChunkEmbedding (JSONB)
```

---

## 4. Database Schema

### Migration History

| Migration | Ticket | Key Tables |
|-----------|--------|-----------|
| `0001_core_domain_models` | TICKET-001/002/005 | `users`, `plants`, `species_profiles`, `sensor_readings`, `environment_snapshots`, `care_logs`, `plant_characters` |
| `0002_ticket4_character_state_fields` | TICKET-004 | Adds columns to `plant_characters` |
| `0003_ticket14a_plant_knowledge_tables` | TICKET-014A | `plant_knowledge_entries`, `plant_knowledge_sources`, `plant_care_requirements`, `plant_seasonal_watering`, `plant_pest_references`, `plant_visual_traits`, `plant_placements` |
| `0004_ticket14b_chunk_tables` | TICKET-014B | `plant_chunk_documents`, `plant_chunk_embeddings` (JSONB vector column) |
| `0005_ticket14c_retrieval_tables` | TICKET-014C | `retrieval_runs`, `retrieval_result_chunks` |
| `0006_ticket15_evidence_bundles` | TICKET-015 | `evidence_bundles`, `chat_requests`, `llm_runs` |

### Core FK Relationships

```
users (id)
  └─► plants.user_id
        └─► plant_characters.plant_id
        └─► care_logs.plant_id
        └─► sensor_readings.plant_id
        └─► environment_snapshots.plant_id
        └─► chat_requests.plant_id

species_profiles (id)
  └─► plants.species_profile_id
  └─► plant_knowledge_entries.species_profile_id
        └─► plant_care_requirements.entry_id
        └─► plant_chunk_documents.plant_knowledge_id
              └─► plant_chunk_embeddings.chunk_document_id

chat_requests (id)
  └─► llm_runs.request_id
  └─► evidence_bundles.request_id (via evidence_hash)

retrieval_runs (id)
  └─► retrieval_result_chunks.run_id (CASCADE)
```

---

## 5. Architecture Decision Records (ADR)

### ADR-001: Header-Only Auth (no JWT in MVP)

**Decision:** User identity is passed as `X-User-Id: <uuid>` header (or `?user_id=` query param). No JWT, OAuth2, or sessions.

**Rationale:** MVP timebox; the primary consumers are a single trusted mobile client and internal testers. The auth layer (`app/core/auth.py`) is isolated so a real auth mechanism can be dropped in without changing business logic.

**Consequence:** No token revocation, no multi-device identity verification. Any caller who knows a user's UUID can act as that user. **Must be replaced before public launch.**

---

### ADR-002: Mock LLM Client (no live Claude in MVP)

**Decision:** `MockLLMClient` returns deterministic structured answers; the real Claude API client is not wired in.

**Rationale:** Avoid API cost and latency during development. The `LLMPort` interface makes the swap trivial.

**How to wire real Claude:**
1. Implement `app/services/llm_port.py → LLMPort` with actual `anthropic` SDK calls.
2. In `chat_orchestrator.py`, replace `MockLLMClient()` with your real implementation.
3. Add `ANTHROPIC_API_KEY` to environment variables and `.env.example`.

---

### ADR-003: JSONB Vector Storage (no pgvector)

**Decision:** Embeddings are stored as `JSONB` arrays in `plant_chunk_embeddings.vector`. Similarity is computed in Python using dot-product.

**Rationale:** Avoids pgvector extension dependency, which requires PostgreSQL compile-time options or managed hosting with pgvector support.

**Consequence:** Full vector scan per query — acceptable for MVP with tens of species. For production at scale (>1,000 species), migrate to pgvector's `ivfflat` or `hnsw` index.

---

### ADR-004: Deterministic Rule Engine (no ML for care status)

**Decision:** Care status (needs_action / watch / good) is computed by pure threshold comparisons, not an ML model.

**Rationale:** Explainability and testability. Every rule has a reason_code that appears in the chat evidence bundle; users can see exactly why an action was recommended.

**Consequence:** Rules require per-species threshold calibration in `species_profiles.metadata_json`. A generic rule applies when no threshold is configured.

---

### ADR-005: UUID5 Seed Data (idempotent demo)

**Decision:** Demo entities use `uuid.uuid5(NS, name)` — deterministic keys from a fixed namespace.

**Rationale:** Re-running `python -m app.seeds.demo_seed` on a fresh DB produces the same UUIDs every time. Documentation, HTTP collection files, and test fixtures can hardcode these IDs safely.

---

### ADR-006: `request_id` Idempotency (caller-supplied UUID)

**Decision:** Chat and retrieval endpoints accept a caller-supplied `request_id` UUID. Re-submitting returns the cached result.

**Rationale:** Mobile clients may retry on network failure. Idempotency prevents duplicate LLM charges and duplicate DB rows.

**Consequence:** Callers must generate UUIDs client-side. If the same `request_id` is reused with a different question, the original answer is silently returned.

---

## 6. Tech Debt Register

Priority: 🔴 Critical before public launch · 🟡 Important · 🟢 Nice to have

### 🔴 TD-001: Real Authentication

**Current state:** `X-User-Id` header. Any caller knowing a UUID can impersonate any user.

**Required:**
- Implement JWT RS256 or OAuth2 PKCE flow
- Replace `get_current_user()` in `app/core/auth.py` — the interface is already clean
- Add token introspection / revocation

**Estimate:** 3–5 days (backend) + frontend changes

---

### 🔴 TD-002: Real Claude API Integration

**Current state:** `MockLLMClient` returns a hardcoded structured response regardless of the question.

**Required:**
- Implement `anthropic.AsyncAnthropic` client in `app/services/llm_port.py`
- Handle rate limits, retries, token counting
- Wire `ANTHROPIC_API_KEY` from environment
- Add cost tracking per `LlmRun` (already has `input_tokens` / `output_tokens` columns)

**Estimate:** 2–3 days

---

### 🟡 TD-003: pgvector Migration

**Current state:** Embeddings stored as JSONB arrays; similarity computed by full Python scan.

**Required when:** Species count exceeds ~500 or query latency becomes unacceptable.

**Migration path:**
1. Add `pgvector` extension to PostgreSQL
2. Add `vector(384)` column to `plant_chunk_embeddings`
3. Back-fill from existing JSONB
4. Create `ivfflat` index (`lists ≈ sqrt(row_count)`)
5. Rewrite `HybridRetriever` to use `<=>` operator
6. Drop old JSONB column

---

### 🟡 TD-004: Automated Snapshot Aggregation

**Current state:** `SnapshotService` is called manually from tests / seed data. No scheduler triggers it on new sensor readings.

**Required:**
- Add a background task (FastAPI `BackgroundTasks` or Celery beat) that calls `SnapshotService.build()` after each sensor ingest, or on a fixed schedule (e.g., every 30 min).

---

### 🟡 TD-005: Streaming Chat Responses

**Current state:** Full response returned after LLM completes (blocking).

**Required for good UX:**
- Use `anthropic` streaming API
- FastAPI `StreamingResponse` with Server-Sent Events (SSE)
- Frontend must handle incremental chunks

---

### 🟢 TD-006: BM25 Keyword Retrieval

**Current state:** Hybrid retrieval currently uses only vector cosine similarity. BM25 is noted in the architecture but not implemented.

**Required:**
- Integrate `rank_bm25` (Python) or `pg_bm25` (PostgreSQL extension)
- Combine BM25 and vector scores with a configurable weight (e.g., 0.7 vector + 0.3 BM25)

---

### 🟢 TD-007: Pest Diagnosis (Image-Based)

**Current state:** `MockSpeciesClassifier` accepts an opaque `image_ref` string; no actual image processing.

**Required:**
- Integrate a real species/pest classification model (port already defined: `app/vision/species_classifier.py → SpeciesClassifierPort`)
- Or call an external vision API (e.g., PlantNet, Pl@ntNet API)
- Update guardrail logic to conditionally allow diagnosis after user consent

---

### 🟢 TD-008: Multi-Language Support (i18n)

**Current state:** All character state messages and chat answers are Korean-only, hardcoded in seeds and prompt templates.

**Required:**
- Accept `Accept-Language` header in API
- Localized message templates for character state (`status_message`, `reason_code` descriptions)
- Language-aware prompt construction

---

## 7. Operations Manual

### 7.1 Starting Services

```bash
# Full stack (recommended)
docker compose up -d

# Check all services are healthy
docker compose ps

# View logs
docker compose logs -f backend
docker compose logs -f postgres
```

### 7.2 Database Operations

```bash
# Apply all pending migrations
docker compose exec backend alembic upgrade head

# Check current migration
docker compose exec backend alembic current

# Rollback one step
docker compose exec backend alembic downgrade -1

# Load demo seed (idempotent)
docker compose exec backend python -m app.seeds.demo_seed

# Run demo scenario health check
docker compose exec backend python -m app.seeds.demo_scenario
```

**Backup:**
```bash
# Dump (run from host)
docker compose exec postgres pg_dump -U sunshine sunshine > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore
docker compose exec -T postgres psql -U sunshine sunshine < backup.sql
```

### 7.3 Embedding Model

The model (`paraphrase-multilingual-MiniLM-L12-v2`) is loaded from the Hugging Face cache on first use.

**Location:** `~/.cache/huggingface/hub/` (default)

**Pre-download for offline/production use:**
```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"
```

**Updating the model:**
1. Change `LocalEmbeddingService.DEFAULT_MODEL` in `app/embedding/local_embedding_service.py`
2. Pre-download the new model
3. **Rebuild all embeddings:** `python -m app.embedding.build_chunks` (this is slow — plan for downtime or blue/green)
4. Existing `plant_chunk_embeddings` rows will be back-filled on the next `ChunkBuildService.build_all()` run

### 7.4 Plant Knowledge Ingestion

```bash
# Ingest from Excel file
python -m app.ingestion.plant_knowledge --file data/species.xlsx

# Build/update chunk embeddings after ingestion
python -m app.embedding.build_chunks

# Verify via API
curl http://localhost:8000/retrieval/query \
  -H "Content-Type: application/json" \
  -d '{"request_id":"...", "plant_id":"...", "user_id":"...", "question":"몬스테라 물주기"}'
```

### 7.5 Monitoring Checklist

| Check | How |
|-------|-----|
| Service alive | `GET /healthz` → `{"status":"ok"}` |
| DB connected | `GET /readyz` → `{"status":"ready"}` |
| Chat pipeline working | Send a chat request; verify `from_cache: false` on first call |
| Embeddings built | `SELECT COUNT(*) FROM plant_chunk_embeddings;` — expect > 0 |
| Snapshots generating | `SELECT MAX(window_end) FROM environment_snapshots;` — should be recent |
| Rule engine firing | `POST /internal/rule-character-sync/{plant_id}` returns a condition |

### 7.6 Log Inspection

```bash
# Application logs (structured JSON when APP_ENV=production)
docker compose logs backend --since 1h

# Slow query detection
docker compose exec postgres psql -U sunshine sunshine \
  -c "SELECT query, mean_exec_time, calls FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Active connections
docker compose exec postgres psql -U sunshine sunshine \
  -c "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"
```

### 7.7 Quality Gate

```bash
# Full gate: lint + format + tests + coverage ≥ 80%
bash scripts/check_gate.sh

# Quick gate (lint + format only, no tests)
SKIP_TESTS=1 bash scripts/check_gate.sh

# E2E tests (requires live DATABASE_URL)
DATABASE_URL=postgresql+asyncpg://... \
  python -m pytest tests/e2e -v -m e2e
```

---

## 8. Extension Roadmap

### Phase 2 — Production Readiness

| Item | Effort | Depends On |
|------|--------|-----------|
| Real Claude API (TD-002) | 2–3 days | ANTHROPIC_API_KEY |
| JWT authentication (TD-001) | 3–5 days | Auth provider decision |
| Automated snapshot scheduler (TD-004) | 1–2 days | — |
| pgvector migration (TD-003) | 2–3 days | Managed PG with pgvector |
| Streaming chat (TD-005) | 2–3 days | Real Claude (TD-002) |

### Phase 3 — Feature Expansion

| Feature | Key Files to Modify | Notes |
|---------|-------------------|-------|
| Push notifications | New `app/services/notification_service.py` | Trigger on character state change |
| Pest image diagnosis | `app/vision/species_classifier.py` (implement port) | Guardrail update required |
| Multi-language (i18n) | `app/services/prompt_builder.py`, seed messages | `Accept-Language` header |
| BM25 hybrid (TD-006) | `app/retrieval/hybrid_retriever.py` | `rank_bm25` library |
| Species auto-import | `app/ingestion/plant_knowledge.py` | External botany API |
| User plant sharing | `app/models/plant.py` + new `plant_shares` table | Auth prerequisite |

---

## 9. Key People & References

| Resource | Location |
|----------|----------|
| API interactive docs | `GET http://localhost:8000/docs` |
| API ReDoc | `GET http://localhost:8000/redoc` |
| HTTP collection | `docs/api-collection.http` |
| Troubleshooting guide | `docs/TROUBLESHOOTING.md` |
| Env template | `.env.example` |
| Demo seed IDs | `app/seeds/demo_seed.py` (constants at top of file) |
| Test suite | `tests/` — 799 tests, 83% coverage |
| Quality gate | `bash scripts/check_gate.sh` |
| Contact | plant.project090@gmail.com |
