# Sunshine Backend — Troubleshooting Guide

Quick reference for errors encountered during development and production operation.

---

## Table of Contents

1. [API Error Codes](#1-api-error-codes)
2. [Startup & Connection Issues](#2-startup--connection-issues)
3. [Database & Migration Issues](#3-database--migration-issues)
4. [Chat & RAG Pipeline Issues](#4-chat--rag-pipeline-issues)
5. [Sensor & Snapshot Issues](#5-sensor--snapshot-issues)
6. [Embedding & Retrieval Issues](#6-embedding--retrieval-issues)
7. [Test Suite Issues](#7-test-suite-issues)
8. [Docker Issues](#8-docker-issues)

---

## 1. API Error Codes

### 422 — User identity required

**Symptom:**
```json
{"detail": "user identity required: supply X-User-Id header or ?user_id= query param"}
```

**Cause:** A user-scoped endpoint received neither the `X-User-Id` header nor a `user_id` parameter.

**Fix:** Add the header to all requests:
```bash
curl http://localhost:8000/plants \
  -H "X-User-Id: 2a307656-dfbb-55f6-9054-007f2014e4a9"
```

---

### 422 — Invalid X-User-Id

**Symptom:**
```json
{"detail": "X-User-Id must be a valid UUID"}
```

**Cause:** The `X-User-Id` header value is not a valid UUID.

**Fix:** Ensure the value is a lowercase hyphenated UUID4 string (e.g., `2a307656-dfbb-55f6-9054-007f2014e4a9`).

---

### 403 — Forbidden

**Symptom:** `403 Forbidden` on `GET /plants/{plant_id}` or similar.

**Cause:** The `user_id` / `X-User-Id` in the request does not match `plant.user_id` in the database.

**Debug:**
```sql
SELECT id, user_id, nickname FROM plants WHERE id = '<plant_id>';
```

Compare the result with the user_id you are sending. Use the demo user UUID for demo plants:
`2a307656-dfbb-55f6-9054-007f2014e4a9`

---

### 404 — Plant not found

**Symptom:** `404 {"detail": "plant not found"}` on chat or companion endpoints.

**Causes:**
1. The `plant_id` does not exist in the database.
2. You are querying a different environment (local vs staging).
3. The demo seed was not run after the last `alembic downgrade`.

**Fix:**
```bash
python -m app.seeds.demo_seed
# Demo plant ID: 23d1867e-f2d0-5bf7-a4c3-f3568c06aeea
```

---

### 409 — Idempotency conflict (cached result)

There is no 409 in the current API — duplicate `request_id` submissions silently return the cached result (`from_cache: true`). If you need a fresh response, generate a new `request_id` UUID.

---

### 503 — Knowledge not built / retrieval returns empty results

**Symptom:** Chat answers are generic (not species-specific), or companion recommendations list is empty.

**Cause:** `plant_chunk_embeddings` table is empty — the knowledge build pipeline has not been run.

**Fix:**
```bash
# 1. Ingest plant knowledge
python -m app.ingestion.plant_knowledge --file data/species.xlsx

# 2. Build chunks and embeddings
python -m app.embedding.build_chunks

# 3. Verify
docker compose exec postgres psql -U sunshine sunshine \
  -c "SELECT COUNT(*) FROM plant_chunk_embeddings;"
```

---

### 503 — Readiness probe failing

**Symptom:** `GET /readyz` returns `{"status":"not_ready","checks":{"database":"error"}}`.

**Causes & Fixes:**

| Cause | Fix |
|-------|-----|
| PostgreSQL not started | `docker compose up postgres -d` |
| Wrong `DATABASE_URL` in `.env` | Check host, port, credentials match `docker-compose.yml` |
| Migrations not applied | `alembic upgrade head` |
| Connection pool exhausted | Restart backend; check `pg_stat_activity` for stuck connections |

---

### 500 — Internal Server Error on chat

**Symptom:** `500` on `POST /plants/{plant_id}/chat`.

**Most likely cause:** `MockLLMClient` failed to produce a parseable structured response, or `EvidenceBuilderService` encountered a DB error.

**Debug:**
```bash
# Check application logs
docker compose logs backend --since 5m

# Test evidence builder separately
curl -X POST http://localhost:8000/evidence/build \
  -H "Content-Type: application/json" \
  -d '{
    "plant_id": "23d1867e-f2d0-5bf7-a4c3-f3568c06aeea",
    "user_id": "2a307656-dfbb-55f6-9054-007f2014e4a9",
    "question": "물주기",
    "intent": "watering_question"
  }'
```

---

## 2. Startup & Connection Issues

### `asyncpg.exceptions.ConnectionRefusedError`

**Symptom:** Backend crashes immediately with connection refused.

**Fix:**
```bash
# 1. Ensure postgres is running
docker compose up postgres -d

# 2. Wait for health check to pass
docker compose ps postgres
# Status should show "(healthy)"

# 3. Verify DATABASE_URL in .env
cat .env | grep DATABASE_URL
# Should match: postgresql+asyncpg://sunshine:...@localhost:5432/sunshine
```

---

### `FATAL: database "sunshine" does not exist`

**Cause:** PostgreSQL is running but the database was not created.

**Fix:**
```bash
docker compose exec postgres createdb -U sunshine sunshine
# Or: restart the postgres container (POSTGRES_DB env var creates it on first start)
docker compose down postgres && docker compose up postgres -d
```

---

### `alembic.util.exc.CommandError: Can't locate revision`

**Cause:** Migration files are out of sync with the database's `alembic_version` table.

**Fix:**
```bash
# Check what the DB thinks the current revision is
docker compose exec postgres psql -U sunshine sunshine \
  -c "SELECT * FROM alembic_version;"

# Stamp to a known revision (dangerous — only if you know the state)
alembic stamp <revision_id>

# Or wipe and re-apply (destroys data)
alembic downgrade base && alembic upgrade head
```

---

### Port 8000 already in use

**Symptom:** `OSError: [Errno 98] Address already in use`

**Fix:**
```bash
# Find the occupying process
lsof -i :8000          # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill it or use a different port
uvicorn app.main:app --port 8001
```

---

## 3. Database & Migration Issues

### Migration fails with FK constraint violation

**Cause:** Attempting to drop a table that still has dependent rows.

**Fix:** Drop in reverse dependency order:
```sql
TRUNCATE llm_runs, chat_requests, evidence_bundles,
         retrieval_result_chunks, retrieval_runs,
         plant_chunk_embeddings, plant_chunk_documents,
         plant_characters, care_logs, environment_snapshots,
         sensor_readings, plants, plant_knowledge_entries,
         species_profiles, users CASCADE;
```

---

### `UniqueViolationError` on seed re-run

**Cause:** The seed was modified and entity UUIDs changed, causing duplicate-key errors.

**Fix:** The demo seed uses UUID5 (stable) — re-running should be safe. If you see this error, a row with a different UUID but same natural key may exist:
```bash
# Wipe demo data and re-seed
docker compose exec postgres psql -U sunshine sunshine \
  -c "DELETE FROM plants WHERE id = '23d1867e-f2d0-5bf7-a4c3-f3568c06aeea';"
python -m app.seeds.demo_seed
```

---

### Slow queries / high CPU on PostgreSQL

**Diagnose:**
```sql
-- Longest running queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY duration DESC
LIMIT 10;

-- Missing indexes
SELECT schemaname, tablename, attname, n_live_tup, n_distinct
FROM pg_stats
WHERE tablename IN ('plant_chunk_embeddings', 'retrieval_result_chunks')
ORDER BY n_live_tup DESC;
```

**Most likely bottleneck:** Full scan of `plant_chunk_embeddings` during retrieval. See ADR-003 and TD-003 (pgvector migration).

---

## 4. Chat & RAG Pipeline Issues

### Chat returns `from_cache: true` unexpectedly

**Cause:** The same `request_id` was used in a previous request.

**Fix:** Generate a new UUID for each unique conversation turn:
```python
import uuid
request_id = str(uuid.uuid4())
```

---

### Answer has no plant-specific information (generic response)

**Symptoms:**
- `retrieved_chunks` is empty in the audit evidence
- Answer does not mention the species

**Diagnosis:**
```bash
# Check audit evidence
curl http://localhost:8000/chat-runs/<request_id>/evidence | jq '.retrieved_chunks | length'

# Check chunk embeddings exist
docker compose exec postgres psql -U sunshine sunshine \
  -c "SELECT COUNT(*) FROM plant_chunk_embeddings;"
```

**Fix:** Run the knowledge build pipeline (see Section 1, "503 — Knowledge not built").

---

### Intent classified as `unknown_question`

**Cause:** The question text doesn't match any of the regex patterns in `ChatIntentClassifier`.

**Expected behavior:** `unknown_question` falls back to `["species_profile", "care_knowledge"]` RAG layers — still produces a reasonable answer.

**If you want to add a new intent:**
1. Add a regex pattern in `app/llm/intent_classifier_mock.py`
2. Add the intent → RAG layer mapping in `chat_orchestrator.py → _INTENT_TO_RAG_LAYERS`
3. Add tests in `tests/test_chat_intent_classifier.py`

---

### Pest question returns `diagnosis_allowed: false`

**Expected behavior.** This is the guardrail working correctly (TICKET-019). The pest reference question intent (`pest_reference_question`) always sets:
- `is_reference_only: true`
- `diagnosis_allowed: false`

The answer still contains reference information from `pest_disease_reference` RAG layer. Remote diagnosis is intentionally blocked.

---

### `prompt_hash` integrity check fails in audit

**Symptom:** `GET /chat-runs/{id}/evidence` shows `prompt_hash_valid: false`.

**Cause:** The prompt template or context data changed between when the answer was generated and when the audit was run, producing a different hash.

**This is an expected signal** — it means the system changed after the answer was cached. In production, treat this as a staleness warning. If it occurs frequently, check for non-deterministic elements in `PromptBuilder`.

---

## 5. Sensor & Snapshot Issues

### Sensor reading accepted but snapshot not updating

**Cause:** `SnapshotService` is not being called automatically after sensor ingest. In MVP, snapshot aggregation is triggered manually.

**Manual trigger:**
```bash
# Run rule + character sync (which also reads the latest snapshot)
curl -X POST http://localhost:8000/internal/rule-character-sync/<plant_id>

# Or run snapshot service directly (requires Python script)
python -c "
import asyncio
from app.db.session import AsyncSessionLocal
from app.services.snapshot_service import SnapshotService
from datetime import datetime, UTC
import uuid

async def run():
    async with AsyncSessionLocal() as session:
        svc = SnapshotService(session)
        await svc.build(uuid.UUID('<plant_id>'), datetime.now(UTC))
        await session.commit()

asyncio.run(run())
"
```

**Long-term fix:** See TD-004 (automated snapshot scheduler).

---

### MQTT sensor readings not appearing in database

**Check MQTT worker logs:**
```bash
docker compose logs mqtt-ingest --since 10m
```

**Check MQTT broker connectivity:**
```bash
docker compose exec mqtt mosquitto_sub -t "sunshine/#" -v
# Then publish a test message from another terminal
```

**Common causes:**
| Cause | Fix |
|-------|-----|
| `mqtt-ingest` container not started | `docker compose up mqtt-ingest -d` |
| Wrong topic format | Verify: `sunshine/{device_id}/sensor` |
| Invalid payload JSON | Check `MqttIngestResult.outcome` in logs |
| Plant not found for device_id | Ensure sensor's `plant_id` is registered in DB |

---

## 6. Embedding & Retrieval Issues

### `sentence_transformers` not installed

**Symptom:** `ModuleNotFoundError: No module named 'sentence_transformers'`

**Cause:** `sentence-transformers` is a runtime dependency but not in `pyproject.toml` (it's expected to be pre-installed in the production image).

**Fix:**
```bash
pip install sentence-transformers
```

Add to `pyproject.toml` dependencies if it should always be installed:
```toml
"sentence-transformers>=2.7.0",
```

---

### Model download fails (offline environment)

**Symptom:** `ConnectionError` when `LocalEmbeddingService._load()` is first called.

**Fix:** Pre-download the model on a machine with internet access:
```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"

# Then copy the cache to the production machine:
# Default cache: ~/.cache/huggingface/
# Set HF_HOME environment variable to redirect the cache path
```

---

### Retrieval returns 0 results

**Diagnosis sequence:**
```bash
# 1. Are there any chunk embeddings?
docker compose exec postgres psql -U sunshine sunshine \
  -c "SELECT COUNT(*) FROM plant_chunk_embeddings;"

# 2. Is the species linked to a knowledge entry?
docker compose exec postgres psql -U sunshine sunshine \
  -c "SELECT ke.id FROM plant_knowledge_entries ke
      JOIN species_profiles sp ON sp.id = ke.species_profile_id
      WHERE sp.id = '<species_profile_id>';"

# 3. Are there chunk documents for this entry?
docker compose exec postgres psql -U sunshine sunshine \
  -c "SELECT chunk_kind, text_hash FROM plant_chunk_documents
      WHERE plant_knowledge_id = '<knowledge_entry_id>';"
```

**Fix if empty:** Run the knowledge build pipeline. See Section 1, "503 — Knowledge not built".

---

## 7. Test Suite Issues

### Tests fail with `asyncpg` connection errors

**Cause:** A test that requires a real DB connection ran without `DATABASE_URL` set.

**These tests are skipped automatically** (module-level `pytest.skip` when `DATABASE_URL` is absent). If they are running and failing, check:
```bash
echo $DATABASE_URL   # Should be empty for unit tests
python -m pytest --ignore=tests/e2e   # Always ignore e2e in unit runs
```

---

### Coverage below 80%

**Symptom:** `pytest-cov` reports below threshold; `scripts/check_gate.sh` fails.

**Quick diagnosis:**
```bash
python -m pytest --ignore=tests/e2e -q --tb=no --cov --cov-report=term-missing 2>&1 | grep "TOTAL"
```

**Likely causes:**
- New code added without tests
- Omit list in `[tool.coverage.run]` changed
- A test file was deleted

**Fix:** Write unit tests for uncovered lines. See existing tests in `tests/` for patterns. Priority: service layer (`app/services/`) and domain layer (`app/domain/`).

---

### `asyncio_default_test_loop_scope` warning

**Symptom:** Deprecation warning about asyncio loop scope.

**Current config in `pyproject.toml`** already sets:
```toml
asyncio_default_test_loop_scope = "session"
```

This is correct. The warning comes from `pytest-asyncio` version differences; it is safe to ignore.

---

### Test imports fail for `app.seeds.demo_seed`

**Cause:** The seeds module tries to load `DATABASE_URL` at import time via `settings`.

**Fix:** Ensure `DATABASE_URL` is set in environment or `.env` before running any test that imports from `app.seeds`.

---

## 8. Docker Issues

### Build fails: `pip install` times out

**Fix:**
```bash
# Increase Docker build timeout or use a faster mirror
docker build --network=host --progress=plain .

# On Windows: check Docker Desktop → Settings → Resources → Network
```

---

### Container starts but immediately exits

**Check the exit code:**
```bash
docker compose ps
docker compose logs backend
```

**Common causes:**

| Exit Code | Meaning | Fix |
|-----------|---------|-----|
| 1 | Application error | Check logs for Python traceback |
| 137 | OOM kill | Increase Docker memory limit |
| 139 | Segfault | Likely native lib issue; try `python:3.12` base |

---

### `docker compose exec` fails with "no such container"

**Cause:** Container not running.

```bash
docker compose up -d        # Start all services
docker compose ps           # Check status
```

---

### Volume mount causes permission errors (Linux)

**Symptom:** `PermissionError` when writing to mounted volume.

**Fix:**
```bash
# Match UID inside container (1000 by default for appuser)
sudo chown -R 1000:1000 ./data ./logs
```

Or adjust `Dockerfile`:
```dockerfile
RUN adduser --system --uid 1000 --ingroup appgroup appuser
```

---

### Old image used after code change

**Fix:** Force rebuild:
```bash
docker compose build --no-cache backend
docker compose up -d backend
```
