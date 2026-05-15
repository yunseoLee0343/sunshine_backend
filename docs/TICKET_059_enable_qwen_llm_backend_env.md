# Claude Code Ticket: TICKET-059

## Goal
Connect `sunshine_backend` Chat pipeline to the real remote Qwen vLLM runtime instead of the mock LLM client.

## Root cause
The backend container currently has no Qwen/LLM environment variables.

Observed command:

```bash
docker compose exec backend env | grep -E 'LLM_BACKEND|QWEN_ENDPOINT|QWEN_LLM|INTERNAL'
```

Output:

```text
<empty>
```

Observed client check:

```bash
docker compose exec -T backend python - <<'PY'
from app.llm.client_factory import get_llm_client
print(type(get_llm_client()))
PY
```

Output:

```text
<class 'app.llm.mock_client.MockLLMClient'>
```

As a result, Chat responses return:

```json
"model_name": "mock-model-v1"
```

even though the RunPod vLLM endpoint responds correctly with:

```json
"model": "qwen3.6"
```

Source-level cause:

```text
docker-compose.yml
  backend.environment
    currently contains only APP_NAME, APP_ENV, DATABASE_URL

app/core/config.py
  default LLM_BACKEND = "mock"

app/llm/client_factory.py
  if settings.LLM_BACKEND == "qwen":
    return QwenLLMClient(...)
  else:
    return MockLLMClient()

app/services/chat_orchestrator.py
  _LLM_CLIENT = get_llm_client()
  this happens at module import time
```

Therefore, if `LLM_BACKEND=qwen` is not present before the backend process starts, the orchestrator locks in the mock client until the backend container is recreated.

## Scope
Implement a deployment/config fix only.

This ticket owns:
- `docker-compose.yml` backend Qwen env vars
- `.env.example` or docs update if present
- verification commands
- runtime endpoint registration procedure

This ticket does not own:
- QwenLLMClient implementation
- EndpointRegistry implementation
- ChatOrchestrator redesign
- RunPod vLLM server setup
- frontend changes
- RAG/prompt changes
- sensor/MQTT changes

## Current source
Current `docker-compose.yml` backend environment:

```yaml
backend:
  environment:
    APP_NAME: sunshine-backend
    APP_ENV: local
    DATABASE_URL: postgresql+asyncpg://sunshine:change-me-local-only@postgres:5432/sunshine
```

This is insufficient because no `LLM_BACKEND`, `QWEN_*`, or `INTERNAL_TOKEN` is injected into the backend container.

## Required change

Update `docker-compose.yml`:

```yaml
services:
  backend:
    build: .
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      APP_NAME: sunshine-backend
      APP_ENV: local
      DATABASE_URL: postgresql+asyncpg://sunshine:change-me-local-only@postgres:5432/sunshine

      # LLM runtime selection
      LLM_BACKEND: qwen

      # Dynamic RunPod/vLLM endpoint registry
      QWEN_ENDPOINT_REGISTRY_MODE: db
      QWEN_LLM_MODEL: qwen3.6
      QWEN_LLM_BASE_URL: http://localhost:8080
      QWEN_LLM_TIMEOUT_SECONDS: "120"
      QWEN_LLM_API_KEY: ""
      QWEN_LLM_AUTH_HEADER: Authorization

      # Internal endpoint registry API token
      INTERNAL_TOKEN: change-this-internal-token
    depends_on:
      postgres:
        condition: service_healthy
```

Notes:
- `QWEN_LLM_BASE_URL` is only fallback when DB registry has no active endpoint.
- The real RunPod URL must be registered via `/internal/runtime-endpoints/qwen`.
- Use a stronger `INTERNAL_TOKEN` outside local demo.

## Required behavior

### 1. Backend container must expose Qwen env
After recreation:

```bash
docker compose exec backend env | grep -E 'LLM_BACKEND|QWEN_ENDPOINT|QWEN_LLM|INTERNAL'
```

Expected:

```text
LLM_BACKEND=qwen
QWEN_ENDPOINT_REGISTRY_MODE=db
QWEN_LLM_MODEL=qwen3.6
QWEN_LLM_TIMEOUT_SECONDS=120
INTERNAL_TOKEN=...
```

### 2. Backend must instantiate `QwenLLMClient`
After recreation:

```bash
docker compose exec -T backend python - <<'PY'
from app.llm.client_factory import get_llm_client
print(type(get_llm_client()))
PY
```

Expected:

```text
<class 'app.llm.qwen_client.QwenLLMClient'>
```

### 3. Runtime registry must point to RunPod vLLM
Register endpoint:

```bash
export EC2_BACKEND="http://localhost:8000"
export INTERNAL_TOKEN="change-this-internal-token"
export VLLM_BASE_URL="https://<runpod-8000-url>"

curl -X PUT "$EC2_BACKEND/internal/runtime-endpoints/qwen" \
  -H "Content-Type: application/json" \
  -H "X-Internal-Token: $INTERNAL_TOKEN" \
  -d "{
    \"provider\": \"qwen\",
    \"model\": \"qwen3.6\",
    \"base_url\": \"${VLLM_BASE_URL%/}\"
  }"
```

Check:

```bash
curl -X POST "$EC2_BACKEND/internal/runtime-endpoints/qwen/check" \
  -H "X-Internal-Token: $INTERNAL_TOKEN"
```

Expected:

```json
{
  "endpoint": "https://<runpod-8000-url>",
  "status": "ok",
  "detail": null
}
```

### 4. Chat response must use Qwen
Call with a fresh request id:

```bash
export PLANT_ID="814646d9-9cbe-5723-aedf-e9a9b7531e1f"
export USER_ID="7507fdac-da23-5956-a5a4-9239de655be0"
export REQ_ID="$(python3 -c 'import uuid; print(uuid.uuid4())')"

curl -i "http://localhost:8000/plants/$PLANT_ID/chat" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $USER_ID" \
  -d "{
    \"request_id\": \"$REQ_ID\",
    \"user_id\": \"$USER_ID\",
    \"question\": \"물 언제 줘야 해?\"
  }"
```

Expected response must not include:

```json
"model_name": "mock-model-v1"
```

Expected response should include:

```json
"model_name": "qwen3.6"
```

or the model id returned by vLLM.

## Tests / checks

### Static checks
- `docker-compose.yml` contains `LLM_BACKEND: qwen`.
- `docker-compose.yml` contains `QWEN_ENDPOINT_REGISTRY_MODE: db`.
- `docker-compose.yml` contains `QWEN_LLM_MODEL: qwen3.6`.
- `docker-compose.yml` contains `INTERNAL_TOKEN`.

### Runtime checks
- `docker compose exec backend env | grep ...` returns Qwen env vars.
- `get_llm_client()` returns `QwenLLMClient`.
- `/internal/runtime-endpoints/qwen/check` returns `status=ok`.
- `/plants/{plant_id}/chat` returns non-mock model name with fresh `request_id`.

## Rollout commands after pull

Run on EC2:

```bash
cd ~/sunshine_backend

git pull origin main

docker compose up -d --force-recreate backend

docker compose exec backend alembic upgrade head

docker compose exec backend env | grep -E 'LLM_BACKEND|QWEN_ENDPOINT|QWEN_LLM|INTERNAL'

docker compose exec -T backend python - <<'PY'
from app.llm.client_factory import get_llm_client
print(type(get_llm_client()))
PY
```

Then register RunPod endpoint:

```bash
export EC2_BACKEND="http://localhost:8000"
export INTERNAL_TOKEN="change-this-internal-token"
export VLLM_BASE_URL="https://<runpod-8000-url>"

curl -fsS "$VLLM_BASE_URL/v1/models"

curl -X PUT "$EC2_BACKEND/internal/runtime-endpoints/qwen" \
  -H "Content-Type: application/json" \
  -H "X-Internal-Token: $INTERNAL_TOKEN" \
  -d "{
    \"provider\": \"qwen\",
    \"model\": \"qwen3.6\",
    \"base_url\": \"${VLLM_BASE_URL%/}\"
  }"

curl -X POST "$EC2_BACKEND/internal/runtime-endpoints/qwen/check" \
  -H "X-Internal-Token: $INTERNAL_TOKEN"
```

Fresh chat smoke:

```bash
export PLANT_ID="814646d9-9cbe-5723-aedf-e9a9b7531e1f"
export USER_ID="7507fdac-da23-5956-a5a4-9239de655be0"
export REQ_ID="$(python3 -c 'import uuid; print(uuid.uuid4())')"

curl -fsS "http://localhost:8000/plants/$PLANT_ID/chat" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $USER_ID" \
  -d "{
    \"request_id\": \"$REQ_ID\",
    \"user_id\": \"$USER_ID\",
    \"question\": \"물 언제 줘야 해?\"
  }" | jq '{model_name, from_cache, answer}'
```

## Important operational note
Always use a fresh `request_id` for smoke tests.

If `from_cache=true`, the backend may return an old mock result from `llm_runs`, even after switching to Qwen.

## Acceptance criteria
- `docker-compose.yml` injects Qwen env vars into backend.
- Backend container reports `LLM_BACKEND=qwen`.
- `get_llm_client()` returns `QwenLLMClient`.
- RunPod endpoint registry health check returns `ok`.
- Fresh Chat API response no longer returns `mock-model-v1`.
- No frontend files changed.
- No backend Python logic changed unless strictly necessary.
- No RunPod runtime repo changes.

## Do not implement
- frontend changes
- ChatOrchestrator refactor
- QwenLLMClient refactor
- endpoint registry redesign
- production secret manager
- HTTPS/nginx setup
- RAG/prompt changes
- sensor/MQTT changes
