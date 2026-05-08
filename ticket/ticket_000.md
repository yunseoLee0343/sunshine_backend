# TICKET-000 — Backend Skeleton + CI/CD Baseline

## 0. 목표

Sunshine 프로젝트의 가장 작은 실행 가능한 백엔드 foundation을 구현한다.

이 티켓은 FastAPI backend skeleton만 만든다.  
DB, Redis, MQTT, LLM, RAG, Vision, worker, Nginx, vLLM, `/readyz`는 구현하지 않는다.

Ticket 0의 핵심은 아래를 검증 가능한 상태로 만드는 것이다.

```text
minimal FastAPI app
GET /healthz
APP_NAME / APP_ENV settings
pytest + ruff
Dockerfile
docker-compose.yml with backend only
.env.example with APP_* only
GitHub Actions CI
executable functional gate report
````

---

## 1. Ticket Identity

### Ticket ID

```text
TICKET-000
```

### Name

```text
Backend Skeleton + CI/CD Baseline
```

### Goal

```text
Create the smallest runnable Sunshine backend foundation that can be verified by tests, Docker runtime smoke, and boundary-aware CI.
```

### Strict non-goal

```text
no DB
no Redis
no MQTT
no LLM
no RAG
no vision
no worker
no Nginx
no vLLM
no /readyz
```

---

## 2. 구현 범위

이 티켓에서 반드시 구현한다.

```text
FastAPI app object: app.main:app
GET /healthz
Settings object or function for APP_NAME and APP_ENV
pytest tests for /healthz
pytest tests for settings defaults
pytest or import test proving app.main import has no side effect
Ruff configuration
Dockerfile
docker-compose.yml with exactly one service: backend
.env.example with APP_NAME and APP_ENV only
GitHub Actions workflow with boundary, lint, test, docker runtime gates
```

구현하지 않는다.

```text
product API
database
readiness endpoint
domain/service/repository/model layer
migration
worker
future architecture placeholder directories
```

---

## 3. 수정/생성 허용 파일

아래 파일만 생성 또는 수정한다.

```text
app/__init__.py
app/main.py
app/core/__init__.py
app/core/config.py
tests/__init__.py
tests/test_healthz.py
pyproject.toml
Dockerfile
docker-compose.yml
.env.example
.github/workflows/ci.yml
```

Optional:

```text
README.md
```

조건:

```text
README.md는 reviewer가 명시적으로 요구한 경우에만 생성한다.
```

중요:

```text
"나중에 쓸 예정"이라는 이유로 빈 디렉터리를 만들지 않는다.
빈 placeholder directory도 boundary pollution으로 간주한다.
```

---

## 4. 금지 파일/디렉터리

아래 경로는 생성하지 않는다.

```text
app/api/
app/domain/
app/services/
app/repositories/
app/models/
app/db/
app/mqtt/
app/llm/
app/rag/
app/retrieval/
app/vision/
app/workers/
alembic/
migrations/
deploy/
scripts/
```

이유:

```text
Ticket 0은 product layer를 scaffold하는 티켓이 아니다.
app/api, app/services, app/models, app/db 등은 이후 티켓에서 명시적으로 열릴 때만 만든다.
```

---

## 5. FastAPI 계약

`app/main.py`에 FastAPI app object를 만든다.

필수:

```python
app = FastAPI(...)
```

필수 endpoint:

```http
GET /healthz
```

허용 endpoint:

```text
/healthz only
```

금지 endpoint:

```text
/readyz
/chat
/plants
/sensor-readings
/species-candidates
/admin
/mqtt
/rag
/vision
```

---

## 6. `/healthz` 계약

### Endpoint

```http
GET /healthz
```

### Status

```text
200
```

### Response body

```json
{
  "status": "ok",
  "service": "sunshine-backend"
}
```

### Hard constraints

```text
/healthz must be liveness-only.
/healthz must not check DB.
/healthz must not check Redis.
/healthz must not check MQTT.
/healthz must not check LLM or vLLM.
/healthz must not check RAG, vector index, or vision model.
/healthz must not call external network.
/healthz must not include timestamp, version, hostname, dependency status, env, or dynamic fields.
```

금지 response drift:

```text
{"status": "healthy"}
{"status": "up"}
{"service": null}
timestamp 추가
dependencies 추가
version 추가
hostname 추가
env 추가
```

---

## 7. `/readyz` 금지 계약

Ticket 0에는 readiness endpoint가 없다.

금지:

```text
GET /readyz
any readiness endpoint
any dependency health endpoint
any DB readiness logic
```

기대 동작:

```text
GET /readyz -> 404
```

주의:

```text
future tickets may introduce /readyz.
future /readyz must not replace or weaken /healthz.
```

---

## 8. Settings 계약

`app/core/config.py`에 Ticket 0 수준의 settings만 둔다.

허용 env:

```env
APP_NAME=sunshine-backend
APP_ENV=local
```

`.env.example`도 정확히 APP_*만 포함한다.

```env
APP_NAME=sunshine-backend
APP_ENV=local
```

금지 env:

```text
DATABASE_*
REDIS_*
MQTT_*
LLM_*
VLLM_*
OPENAI_*
ANTHROPIC_*
SECRET*
*PASSWORD*
*TOKEN*
PRIVATE_KEY*
JWT_SECRET
SECRET_KEY
```

규칙:

```text
.env.example must not contain real or placeholder secrets.
Ticket 0 allows only APP_NAME and APP_ENV.
```

---

## 9. Dependency 계약

### 허용 runtime dependencies

```text
fastapi
uvicorn
pydantic
pydantic-settings
```

### 허용 dev dependencies

```text
pytest
httpx
ruff
```

### 금지 dependencies

```text
sqlalchemy
asyncpg
psycopg
redis
paho-mqtt
vllm
openai
anthropic
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

## 10. Dockerfile 계약

Dockerfile 필수 속성:

```text
Python 3.11 slim base image
WORKDIR /app
install dependencies from pyproject.toml
copy only backend skeleton files needed for Ticket 0
expose or run port 8000 only
default command starts uvicorn app.main:app
exec-form CMD
```

필수 CMD:

```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

금지 Dockerfile pattern:

```text
shell-form CMD hiding the real process
ENTRYPOINT ["./scripts/start-all-services.sh"]
supervisord
start-all-services
sh -c "uvicorn ... & python ... & wait"
running migrations
starting workers
subscribing to MQTT
connecting to Redis/Postgres
loading models
starting vLLM
```

---

## 11. docker-compose 계약

`docker-compose.yml`은 정확히 하나의 service만 가진다.

Required service:

```yaml
services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      APP_NAME: sunshine-backend
      APP_ENV: local
```

금지 service names:

```yaml
api:
db:
cache:
llm:
nginx:
worker:
postgres:
redis:
mqtt:
vllm:
```

규칙:

```text
compose service는 backend 하나만 허용한다.
postgres도 Ticket 0에서는 금지다.
future service name을 미리 만들어 두지 않는다.
```

---

## 12. Runtime 계약

허용 runtime topology:

```text
host
  -> backend container
      -> uvicorn app.main:app
          -> GET /healthz
```

허용 long-lived container:

```text
backend
```

금지 runtime dependency:

```text
database
Redis
MQTT broker
vector DB
LLM runtime
vLLM
vision model
worker process
Nginx
external network
```

---

## 13. Process 계약

필수 process:

```text
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

필수 속성:

```text
exactly one foreground app process
no process supervisor
no background worker
no scheduler
no subscriber
no model loader
no migration runner
Docker stop/rm must terminate the process
```

금지 runtime process:

```text
python -m app.workers.main
python -m app.mqtt
python -m app.migrations
python -m app.llm
python -m app.vision
python -m app.rag
```

---

## 14. Startup Side-effect 계약

허용 startup action:

```text
import app.main
create FastAPI app
load Ticket 0 settings
register /healthz route
start uvicorn
```

금지 startup action:

```text
connect to DB
connect to Redis
subscribe to MQTT
call vLLM
call OpenAI/Anthropic
load ML/LLM/vision models
load RAG index
read secret files
run migrations
start workers
write user data
create local persistence directories
external network call
```

`python -c "import app.main"`은 외부 dependency 없이 성공해야 한다.

---

## 15. Network 계약

Required:

```text
inside container:
  listen on 0.0.0.0:8000

host mapping:
  localhost:8000 -> backend container:8000
```

Forbidden:

```text
bind only to 127.0.0.1 inside container
use port 5000
use port 8080
use port 8888
expose unrelated ports
add Nginx/TLS/gateway
```

---

## 16. Runtime State / Logging / Shutdown 계약

Ticket 0 backend는 stateless다.

금지 local persistence:

```text
/app/data
/app/db.sqlite
/app/logs/backend.log
/app/uploads
/app/models
/app/vector_index
/app/cache
```

허용 runtime state:

```text
Python import cache
process-local memory
stdout/stderr logs
OS temporary internals
```

Logging:

```text
logs to stdout/stderr
Docker logs can inspect the process
```

금지 logging persistence:

```text
required /app/logs directory
backend.log persistence
audit data as log-file persistence
```

Shutdown:

```text
docker stop sunshine-backend-test
docker rm -f sunshine-backend-test
```

위 명령으로 backend container가 종료되어야 한다.

---

## 17. CI 계약

GitHub Actions는 boundary-aware CI여야 한다.
단순히 “테스트가 돈다”가 아니라 Ticket 0 boundary를 검증해야 한다.

Required CI jobs:

```text
preflight-boundary
python-quality
python-tests
docker-functional-gate
report-summary
```

### preflight-boundary

검증:

```text
forbidden directories absent
/readyz absent
.env.example scope
compose service == backend only
```

### python-quality

검증:

```text
pip install -e ".[dev]"
ruff check .
ruff format --check .
```

### python-tests

검증:

```text
pytest
GET /healthz returns 200
exact JSON
app import no side effects
settings defaults
```

### docker-functional-gate

검증:

```text
docker compose config
compose services == backend
docker build
docker import gate
docker runtime smoke
curl /healthz
exact JSON
GET /readyz -> 404
```

### report-summary

출력:

```text
ticket id
result
commands run
passed invariants
non-goals confirmed
violations
```

---

## 18. 테스트 요구사항

아래 테스트를 추가한다.

```text
tests/test_healthz.py
```

필수 테스트:

```text
GET /healthz returns 200
GET /healthz response exactly equals {"status": "ok", "service": "sunshine-backend"}
GET /readyz returns 404 or route does not exist
settings default APP_NAME == sunshine-backend
settings default APP_ENV == local
import app.main has no side effects
```

Boundary checks는 CI에서 추가로 수행한다.

```text
no forbidden directories
no forbidden dependencies
no forbidden env
compose backend only
no product endpoints
```

---

## 19. Functional Expectations

### Healthz

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

### Readyz

Expected:

```text
GET /readyz -> 404
```

### Compose

Expected:

```text
docker compose config --services
backend
```

Only one line is allowed.

### Docker runtime

Expected:

```text
docker build succeeds
docker run succeeds
backend listens on localhost:8000
/healthz is reachable
/healthz returns exact JSON
container exits cleanly on docker stop/rm
```

### Import gate

Expected:

```text
python -c "import app.main"
```

succeeds without:

```text
DB connection
Redis connection
MQTT subscription
LLM call
model loading
migration
worker startup
external network call
```

---

## 20. 구현 금지 항목

이 티켓에서 아래 기능은 구현하지 않는다.

```text
/readyz
/chat
/plants
/sensor-readings
/species-candidates
/admin
OpenAPI examples for product workflows

DB connection
DB model
migration
repository layer
Redis queue
MQTT client
worker
Nginx
vLLM runtime

LLMPort
PromptBuilder
EvidenceBuilder
RAG retriever
vector DB
embedding model
vision model
model registry

startup external network call
local SQLite fallback
local file persistence
model download
background scheduler
```

---

## 21. 최종 완료 조건

Ticket 0은 아래가 모두 만족되면 완료다.

```text
FastAPI app object app.main:app exists.
GET /healthz exists.
GET /healthz returns HTTP 200.
GET /healthz returns exactly {"status": "ok", "service": "sunshine-backend"}.
GET /readyz is absent or returns 404.
Settings support APP_NAME and APP_ENV only.
.env.example contains APP_NAME and APP_ENV only.
Dockerfile starts exactly one uvicorn process using exec-form CMD.
docker-compose.yml has exactly one service: backend.
backend binds 0.0.0.0:8000 and maps host localhost:8000.
pytest passes.
ruff check passes.
ruff format --check passes.
docker build passes.
docker runtime smoke passes.
app.main import has no side effects.
CI has boundary, lint, test, docker runtime, report jobs.
No DB, Redis, MQTT, LLM, RAG, vision, worker, Nginx, vLLM, /readyz, product API, domain/service/repository/model/db layer leaks into this ticket.
```
