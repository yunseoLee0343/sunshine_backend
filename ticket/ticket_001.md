# TICKET-001 — Core Domain Models + Postgres Baseline

## 0. 목표

Sunshine MVP의 Postgres 기반 영속성 토대를 구현한다.

이 티켓은 데이터베이스 foundation만 추가한다.  
제품 기능 API나 워크플로우는 구현하지 않는다.

Ticket 0의 `/healthz`는 그대로 liveness-only로 유지한다.  
DB readiness는 새 endpoint인 `/readyz`에서만 확인한다.

---

## 1. 핵심 요구사항

### Ticket ID

```text
TICKET-001
````

### Name

```text
Core Domain Models + Postgres Baseline
```

### Goal

```text
Add durable Postgres-backed persistence foundation for Sunshine MVP without implementing product workflows.
```

### Core output

```text
backend + postgres compose topology
database settings
Alembic migration baseline
core domain tables
repository smoke layer
/readyz DB readiness endpoint
```

### Strict non-goal

```text
no MQTT
no LLM
no RAG
no vision inference
no worker
no plant onboarding API
no chat pipeline
no Rule Engine
```

---

## 2. 수정/생성 허용 파일

### 수정 가능한 기존 파일

```text
app/main.py
app/core/config.py
pyproject.toml
docker-compose.yml
.env.example
.github/workflows/ci.yml
```

### 생성 가능한 새 파일

```text
app/db/__init__.py
app/db/base.py
app/db/session.py
app/db/health.py

app/models/__init__.py
app/models/user.py
app/models/species_profile.py
app/models/plant.py
app/models/plant_character.py
app/models/sensor_reading.py
app/models/environment_snapshot.py
app/models/care_log.py
app/models/chat_request.py
app/models/llm_run.py
app/models/recommendation_evidence.py
app/models/retrieved_chunk.py

app/repositories/__init__.py
app/repositories/base_repository.py
app/repositories/smoke_repository.py

alembic.ini
alembic/env.py
alembic/script.py.mako
alembic/versions/0001_core_domain_models.py

tests/test_healthz_contract.py
tests/test_readyz_contract.py
tests/test_db_models.py
tests/test_repository_smoke.py
tests/test_migrations.py
```

위 목록에 없는 파일은 수정하거나 생성하지 않는다.

---

## 3. Dependency 계약

### 허용 runtime dependencies

```text
fastapi
uvicorn
pydantic
pydantic-settings
sqlalchemy
asyncpg
alembic
psycopg or psycopg[binary] only if migration/test tooling needs sync DB access
```

### 허용 dev dependencies

```text
pytest
pytest-asyncio
httpx
ruff
```

### 금지 dependencies

```text
paho-mqtt
redis
celery
rq
openai
anthropic
vllm
pgvector
sentence-transformers
torch
torchvision
transformers
tensorflow
onnxruntime
openvino
opencv-python
Pillow
```

---

## 4. Docker Compose 계약

Ticket 1의 compose service는 정확히 아래 두 개여야 한다.

```text
backend
postgres
```

Required service names:

```yaml
services:
  backend:
  postgres:
```

금지 service names:

```yaml
nginx:
worker:
redis:
mqtt:
vllm:
llm:
cache:
db:
api:
```

규칙:

```text
postgres는 Ticket 1에서 추가되는 유일한 dependency service다.
Redis, MQTT, vLLM, Nginx, worker는 later-ticket service다.
backend service는 하나의 uvicorn process만 실행해야 한다.
```

---

## 5. Environment 계약

`.env.example`에는 아래 key만 허용한다.

```env
APP_NAME=sunshine-backend
APP_ENV=local

DATABASE_HOST=postgres
DATABASE_PORT=5432
DATABASE_NAME=sunshine
DATABASE_USER=sunshine
DATABASE_PASSWORD=change-me-local-only
DATABASE_URL=postgresql+asyncpg://sunshine:change-me-local-only@postgres:5432/sunshine

POSTGRES_DB=sunshine
POSTGRES_USER=sunshine
POSTGRES_PASSWORD=change-me-local-only
```

규칙:

```text
DATABASE_* is allowed because Ticket 1 owns Postgres.
POSTGRES_* is allowed only for local docker-compose postgres bootstrap.
No production secret may be committed.
Password values must be obvious local placeholders.
```

금지 env:

```text
REDIS_URL
MQTT_URL
LLM_BASE_URL
VLLM_BASE_URL
OPENAI_API_KEY
ANTHROPIC_API_KEY
JWT_SECRET
SECRET_KEY
API_TOKEN
PRIVATE_KEY
```

---

## 6. Core Schema 계약

Ticket 1은 아래 table을 persistence primitive로 정의한다.
이 table들을 이용한 제품 워크플로우는 구현하지 않는다.

---

### `users`

```text
id UUID primary key
display_name text nullable
created_at timestamptz not null
updated_at timestamptz not null
```

---

### `species_profiles`

```text
id UUID primary key
korean_name text not null
scientific_name text nullable
common_name text nullable
care_level text nullable
water_min_pct numeric nullable
water_max_pct numeric nullable
light_min_lux numeric nullable
light_max_lux numeric nullable
humidity_min_pct numeric nullable
humidity_max_pct numeric nullable
temperature_min_c numeric nullable
temperature_max_c numeric nullable
metadata_json jsonb not null default '{}'
created_at timestamptz not null
updated_at timestamptz not null
```

---

### `plants`

```text
id UUID primary key
user_id UUID not null references users(id)
species_profile_id UUID nullable references species_profiles(id)
nickname text not null
room_name text nullable
created_at timestamptz not null
updated_at timestamptz not null
```

---

### `plant_characters`

```text
id UUID primary key
plant_id UUID not null references plants(id)
mood text not null
expression text not null
status_message text not null
reason_code text not null
created_at timestamptz not null
```

---

### `sensor_readings`

```text
id UUID primary key
reading_id text not null unique
device_id text not null
plant_id UUID not null references plants(id)
measured_at timestamptz not null
temperature_c numeric not null
humidity_pct numeric not null
light_lux numeric not null
soil_moisture_pct numeric not null
created_at timestamptz not null
```

---

### `environment_snapshots`

```text
id UUID primary key
plant_id UUID not null references plants(id)
window text not null
window_start timestamptz not null
window_end timestamptz not null
temperature_avg_c numeric nullable
temperature_min_c numeric nullable
temperature_max_c numeric nullable
humidity_avg_pct numeric nullable
humidity_min_pct numeric nullable
humidity_max_pct numeric nullable
light_avg_lux numeric nullable
light_min_lux numeric nullable
light_max_lux numeric nullable
soil_moisture_avg_pct numeric nullable
soil_moisture_min_pct numeric nullable
soil_moisture_max_pct numeric nullable
created_at timestamptz not null
unique(plant_id, window, window_start, window_end)
```

---

### `care_logs`

```text
id UUID primary key
plant_id UUID not null references plants(id)
action_type text not null
note text nullable
acted_at timestamptz not null
created_at timestamptz not null
```

---

### `chat_requests`

```text
id UUID primary key
user_id UUID not null references users(id)
plant_id UUID nullable references plants(id)
question text not null
status text not null
created_at timestamptz not null
```

---

### `llm_runs`

```text
id UUID primary key
request_id UUID not null references chat_requests(id)
profile text nullable
model_name text nullable
prompt_hash text nullable
prompt_text text nullable
response_text text nullable
tokens_in integer nullable
tokens_out integer nullable
latency_ms integer nullable
created_at timestamptz not null
```

---

### `recommendation_evidence`

```text
id UUID primary key
request_id UUID not null references chat_requests(id)
evidence_type text not null
evidence_json jsonb not null
created_at timestamptz not null
```

---

### `retrieved_chunks`

```text
id UUID primary key
request_id UUID not null references chat_requests(id)
chunk_id text not null
score numeric nullable
source text nullable
text text nullable
metadata_json jsonb not null default '{}'
created_at timestamptz not null
```

---

## 7. 구현 허용 범위

Ticket 1에서 구현 가능한 것:

```text
SQLAlchemy model definitions
Alembic migration
database session factory
DB readiness probe
repository smoke functions
/readyz endpoint that checks DB connectivity
```

Ticket 1에서 구현하면 안 되는 것:

```text
plant onboarding endpoints
sensor ingestion endpoint
MQTT subscriber
snapshot aggregation algorithm
Rule Engine
chat endpoint
LLMPort
PromptBuilder
EvidenceBuilder
RAG retriever
pgvector extension
vector embedding
vision classifier
worker process
Redis queue
vLLM runtime
Nginx
admin console
```

중요:

```text
llm_runs, recommendation_evidence, retrieved_chunks tables are allowed because Ticket 1 owns schema foundation.

But generating LLM output, building prompts, retrieving RAG chunks, or persisting real chat evidence is forbidden.
```

---

## 8. 금지 구현 패턴

### Startup 금지

```text
run alembic upgrade automatically during app startup
connect to DB during app import
create tables automatically with metadata.create_all()
seed data automatically during backend startup
start worker/subscriber/scheduler process
subscribe to MQTT
connect to Redis
call LLM/vLLM/OpenAI/Anthropic
load ML or vision model
download anything
write local SQLite fallback
```

### API expansion 금지

```text
POST /plants
GET /plants
POST /sensor-readings
POST /chat
POST /chat/intent
any RAG endpoint
any vision endpoint
```

### Docker expansion 금지

```text
nginx service
worker service
redis service
mqtt service
vllm service
extra exposed ports except backend 8000 and postgres 5432 if explicitly needed for local dev
```

### DB shortcut 금지

```text
SQLite fallback
local file DB
JSON-file persistence
migration-free table creation
```

---

## 9. Runtime 계약

허용 runtime topology:

```text
host
  -> backend container
      -> uvicorn app.main:app
      -> GET /healthz
      -> GET /readyz
      -> async SQLAlchemy session factory

  -> postgres container
      -> PostgreSQL 16
```

허용 long-lived containers:

```text
backend
postgres
```

금지 long-lived containers:

```text
nginx
worker
redis
mqtt
vllm
```

### Backend process invariant

```text
exactly one foreground uvicorn process

required command:
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Backend must not run:

```text
migrations
worker
scheduler
MQTT subscriber
Redis consumer
model loader
LLM engine
```

### Postgres process invariant

```text
official postgres server process only
```

---

## 10. Network 계약

Required:

```text
backend listens on 0.0.0.0:8000
host maps localhost:8000 -> backend:8000
postgres listens inside compose network on postgres:5432
backend connects to postgres:5432 inside compose network
```

Allowed for local gate convenience:

```text
postgres may expose 5432:5432
```

Forbidden:

```text
backend binds to 127.0.0.1 only
backend exposes extra app ports
nginx/TLS/gateway in Ticket 1
Redis/MQTT/vLLM network dependency
external network dependency for startup or tests
```

---

## 11. `/healthz` 계약

`/healthz`는 Ticket 0과 동일하게 liveness-only다.

```http
GET /healthz
200
```

```json
{
  "status": "ok",
  "service": "sunshine-backend"
}
```

Hard rule:

```text
/healthz must not check Postgres.
```

금지:

```text
DB check
Redis check
MQTT check
LLM/vLLM check
RAG/vector DB check
vision check
external network check
response shape change
```

---

## 12. `/readyz` 계약

`/readyz`는 Ticket 1에서 새로 추가되는 dependency readiness endpoint다.

DB reachable일 때:

```http
GET /readyz
200
```

```json
{
  "status": "ready",
  "service": "sunshine-backend",
  "checks": {
    "database": "ok"
  }
}
```

DB unavailable일 때:

```http
GET /readyz
503
```

```json
{
  "status": "not_ready",
  "service": "sunshine-backend",
  "checks": {
    "database": "error"
  }
}
```

Allowed readiness check:

```sql
SELECT 1
```

금지 readiness checks:

```text
redis.ping()
mqtt health
vLLM health
vector index health
model warmup
worker reachability
external HTTP probe
```

---

## 13. Migration 계약

Migrations는 explicit operation이어야 한다.

Allowed:

```bash
alembic upgrade head
alembic downgrade -1
alembic current
```

Forbidden:

```text
running migrations automatically during app import
running migrations automatically inside /healthz
running migrations automatically inside /readyz
running migrations automatically during uvicorn startup
using metadata.create_all() as migration replacement
```

---

## 14. Repository Smoke 계약

Repository smoke layer는 DB access와 table usability만 증명한다.

Allowed repository smoke operations:

```text
insert one user
insert one species profile
insert one plant linked to user/species
read it back
rollback or delete test row
```

Forbidden repository behavior:

```text
business workflow orchestration
onboarding API behavior
sensor ingestion behavior
chat request processing
rule execution
LLM call
RAG retrieval
```

---

## 15. 테스트 요구사항

아래 테스트를 추가한다.

```text
tests/test_healthz_contract.py
tests/test_readyz_contract.py
tests/test_db_models.py
tests/test_repository_smoke.py
tests/test_migrations.py
```

### Healthz tests

필수 케이스:

```text
GET /healthz returns 200
response exactly equals {"status": "ok", "service": "sunshine-backend"}
/healthz does not touch DB
/healthz still succeeds when DB is down or unavailable
```

### Readyz tests

필수 케이스:

```text
GET /readyz returns 200 when DB SELECT 1 succeeds
response checks contains only {"database": "ok"}
GET /readyz returns 503 when DB connection fails
failure response checks contains only {"database": "error"}
/readyz does not check Redis/MQTT/LLM/RAG/vision/model readiness
```

### DB model tests

필수 확인:

```text
users table model exists
species_profiles table model exists
plants table model exists
plant_characters table model exists
sensor_readings table model exists
environment_snapshots table model exists
care_logs table model exists
chat_requests table model exists
llm_runs table model exists
recommendation_evidence table model exists
retrieved_chunks table model exists

sensor_readings.reading_id is unique
environment_snapshots unique(plant_id, window, window_start, window_end)
foreign keys are defined
created_at/updated_at fields exist where required
```

### Migration tests

필수 확인:

```text
alembic upgrade head succeeds
required tables exist after migration
alembic current reports head
no metadata.create_all shortcut is required
```

### Repository smoke tests

필수 케이스:

```text
create smoke user
create smoke species profile
create smoke plant linked to user/species
read smoke plant back
rollback/delete smoke data
no business workflow or product API behavior
```

### Boundary tests

필수 확인:

```text
no app/mqtt/
no app/llm/
no app/rag/
no app/retrieval/
no app/vision/
no app/workers/
no deploy/

no POST /plants
no GET /plants
no POST /sensor-readings
no POST /chat
no POST /chat/intent
no RAG endpoint
no vision endpoint

no MQTT/Redis/LLM/RAG/vLLM/vision/worker dependency
no SQLite fallback
no local file DB
no auto migration on startup
```

---

## 16. Functional Expectations

### Compose scope

Expected:

```text
docker compose config --services
  backend
  postgres
```

Forbidden:

```text
nginx
worker
redis
mqtt
vllm
llm
cache
db
api
```

---

### Healthz liveness

Expected:

```http
GET /healthz
200
```

```json
{
  "status": "ok",
  "service": "sunshine-backend"
}
```

With Postgres down:

```text
/healthz still returns 200
same exact JSON
```

---

### Readyz readiness

With Postgres up:

```http
GET /readyz
200
```

```json
{
  "status": "ready",
  "service": "sunshine-backend",
  "checks": {
    "database": "ok"
  }
}
```

With Postgres down:

```http
GET /readyz
503
```

```json
{
  "status": "not_ready",
  "service": "sunshine-backend",
  "checks": {
    "database": "error"
  }
}
```

---

### Migration

Expected:

```text
alembic upgrade head succeeds
all required tables exist
```

Required tables:

```text
users
species_profiles
plants
plant_characters
sensor_readings
environment_snapshots
care_logs
chat_requests
llm_runs
recommendation_evidence
retrieved_chunks
```

---

### Repository smoke

Expected:

```text
SmokeRepository can:
  insert user
  insert species profile
  insert plant linked to user/species
  read plant back
  rollback/delete smoke rows
```

---

## 17. 구현 금지 항목

이 티켓에서 아래 기능은 구현하지 않는다.

```text
plant onboarding endpoint
species candidates endpoint
sensor ingestion endpoint
MQTT subscriber
snapshot aggregation
Rule Engine
chat endpoint
LLMPort
PromptBuilder
EvidenceBuilder
RAG retriever
pgvector extension
vector embedding
vision classifier
worker process
Redis queue
vLLM runtime
Nginx
admin console
model loading
external API calls
automatic seed data
automatic migration on app startup
```

---

## 18. 최종 완료 조건

Ticket 1은 아래가 모두 만족되면 완료다.

```text
docker-compose has exactly backend + postgres.
.env.example contains only allowed DB/local app keys.
SQLAlchemy core domain models exist.
Alembic baseline migration exists.
alembic upgrade head creates all required core tables.
database session factory exists.
DB readiness probe exists.
GET /healthz remains Ticket 0 liveness-only exact response.
GET /readyz returns DB readiness only.
GET /readyz returns 503 when DB is down.
SmokeRepository proves basic DB insert/read.
No product workflow API exists.
No MQTT, Redis, worker, vision, LLM, RAG, Rule Engine, vLLM, Nginx, or admin feature leaks into this ticket.
No automatic migrations or metadata.create_all shortcut.
No SQLite/local file persistence fallback.
```
