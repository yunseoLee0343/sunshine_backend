# TICKET-025 — Auth / User Scope Minimal

## 0. 목표

Sunshine MVP에 최소 사용자 범위 검사를 추가한다.

이 티켓은 production auth를 구현하지 않는다.  
이 티켓은 OAuth/JWT/password login을 구현하지 않는다.  
이 티켓은 frontend auth UI를 만들지 않는다.

Ticket 25의 책임은 아래까지만이다.

```text
X-User-Id request header
  -> CurrentUser
  -> user-owned resource scoping
  -> created records attach user_id
  -> cross-user access denial
```

---

## 1. Ticket Identity

### Ticket ID

```text
TICKET-025
```

### Name

```text
Auth / User Scope Minimal
```

### Goal

```text
Add MVP-level user scoping so user-owned plants, care logs, sensor data, chat runs, and evidence cannot be accessed by another user.
```

### Core output

```text
CurrentUser model
dev auth header parser
user_id scoped service/repository access
cross-user access denial
minimal user-scope tests
```

### Strict non-goal

```text
no OAuth
no JWT
no password login
no social login
no refresh token
no session cookie
no RBAC
no admin role
no billing
no frontend auth UI
no external identity provider
no production auth redesign
```

---

## 2. 주변 티켓과의 연결

Ticket 25는 MVP 데이터 접근 경계다.

```text
Ticket 1:
  user-owned DB records exist or can be scoped

Ticket 2:
  plant onboarding must attach current user_id

Ticket 5/6:
  sensor readings must be scoped to owned plant

Ticket 11:
  care logs must be scoped to owned plant/user

Ticket 18/19/21:
  chat/care/pest/companion paths must only run for owned plants

Ticket 22:
  evidence query must only return current user's chat evidence

Ticket 23/24:
  demo/e2e fixtures should include multiple users for cross-user tests
```

Ticket 25의 역할:

```text
request
  + X-User-Id
  -> CurrentUser
  -> existing API/service/repository calls receive user_id
  -> owned data only
```

금지:

```text
real login
JWT signing or verification
OAuth provider integration
frontend session flow
admin authorization system
billing/subscription check
```

---

## 3. 수정/생성 허용 파일

### 생성 가능한 새 파일

```text
app/auth/__init__.py
app/auth/dev_auth.py
app/domain/user_scope.py
app/services/user_scope.py

tests/test_user_scope.py
tests/test_cross_user_access.py
tests/fixtures/user_scope_fixtures.py
```

### 수정 가능한 기존 API 파일

아래 파일은 user_id를 주입하고 ownership을 확인하는 범위에서만 수정한다.

```text
app/api/plants.py
app/api/chat.py
app/api/chat_runs.py
app/api/companion.py
app/api/sensor_readings.py
app/api/care_logs.py
app/api/history.py
app/api/home.py
```

허용 수정:

```text
- CurrentUser dependency 사용
- current_user.user_id를 service/repository에 전달
- missing user header 처리
- cross-user access 차단
- 기존 response schema는 access error 외에는 유지
```

### 수정 가능한 service/repository 파일

아래 파일은 ownership filter 추가 범위에서만 수정한다.

```text
app/services/plant_service.py
app/services/chat_orchestrator.py
app/services/audit_query_service.py
app/services/care_log_service.py
app/services/sensor_ingest.py
app/services/history_service.py
app/services/companion_recommendation.py

app/repositories/plant_repository.py
app/repositories/audit_repository.py
app/repositories/care_log_repository.py
app/repositories/sensor_repository.py
app/repositories/history_repository.py
app/repositories/companion_repository.py
```

허용 수정:

```text
- read path에 user_id filter 추가
- create path에 current_user.user_id attach
- plant ownership join 추가
- cross-user access 시 not_found/forbidden 반환
```

### 조건부 migration 허용

기존 user-owned table에 `user_id`가 없을 때만 허용한다.

```text
alembic/versions/<ticket25_user_scope>.py
```

허용 범위:

```text
- existing user-owned table에 user_id column 추가
- user_id index 추가
- plant_id ownership join에 필요한 minimal FK/index 추가
```

금지:

```text
- auth/session/token table
- role/permission table
- billing table
- admin table
- OAuth account table
```

---

## 4. 금지 파일/디렉터리

아래 경로는 생성하거나 수정하지 않는다.

```text
app/auth/oauth.py
app/auth/jwt.py
app/auth/passwords.py
app/auth/social_login.py
app/auth/billing.py
app/admin/
app/workers/
app/llm/
app/vision/
app/mqtt/
app/retrieval/reranker.py
app/retrieval/crag.py

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
Ticket 25는 최소 user scope ticket이다.
Production authentication, frontend session, admin authorization, billing, infrastructure expansion으로 확장하지 않는다.
```

---

## 5. Minimal Auth 계약

### Header

모든 user-scoped endpoint는 아래 header를 읽는다.

```http
X-User-Id: demo-user-001
```

선택 header:

```http
X-User-Name: Demo User
```

### CurrentUser

```python
# app/domain/user_scope.py

from dataclasses import dataclass


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    display_name: str | None = None
```

### Dev auth parser

```python
# app/auth/dev_auth.py

def get_current_user_from_headers(...) -> CurrentUser:
    ...
```

또는 테스트 가능한 순수 함수:

```python
def parse_current_user_from_headers(headers: Mapping[str, str]) -> CurrentUser:
    ...
```

필수 동작:

```text
- missing X-User-Id -> 401 unauthenticated
- empty X-User-Id -> 401 unauthenticated
- malformed X-User-Id -> 400 invalid_user_id
- valid X-User-Id -> CurrentUser
- no DB lookup
- no external auth call
- no password/session/token validation
```

허용 user_id 형식:

```text
ASCII-safe stable id
example: demo-user-001
```

---

## 6. User-Owned Resource 계약

다음 record는 user scope 대상이다.

```text
plants
plant_characters
sensor_readings
environment_snapshots
care_logs
chat_requests
llm_runs
recommendation_evidence
retrieved chunk links tied to chat run
companion recommendation evidence tied to chat run
```

규칙:

```text
- user-owned read path는 user_id filter를 포함해야 한다.
- user-owned create path는 current_user.user_id를 저장해야 한다.
- plant_id 기반 resource는 plant ownership을 먼저 확인해야 한다.
- cross-user read는 partial data를 반환하지 않는다.
- cross-user write는 다른 user의 데이터를 mutate하지 않는다.
```

---

## 7. Endpoint Scope 계약

### Plants

```text
GET /plants
  -> current user의 plant만 반환

GET /plants/{plant_id}
  -> plant.user_id == current_user.user_id일 때만 반환

POST /plants
  -> created plant.user_id == current_user.user_id
```

Cross-user access:

```text
preferred: 404 plant_not_found
allowed: 403 forbidden
```

MVP 선호:

```text
404 plant_not_found
```

### Care logs

```text
POST /plants/{plant_id}/care-logs
  -> plant belongs to current user
  -> care_log.user_id == current_user.user_id if schema supports it

GET /plants/{plant_id}/care-logs
  -> current user + owned plant logs only
```

### Sensor / Environment

```text
POST /sensor-readings
  -> target plant belongs to current user
  -> sensor_reading.user_id attached if schema supports it
  -> otherwise enforce through plant ownership join

GET environment/history paths
  -> current user owned plant only
```

### Chat

```text
POST /plants/{plant_id}/chat
  -> plant belongs to current user
  -> chat request/evidence is attached to user_id or scoped through plant ownership
```

### Audit evidence

```text
GET /chat-runs/{request_id}/evidence
  -> evidence returned only if request_id belongs to current user
```

Cross-user evidence access:

```text
preferred: 404 chat_run_not_found
```

### Companion recommendation

```text
GET /plants/{plant_id}/companion-recommendations
  -> plant belongs to current user

POST /plants/{plant_id}/chat companion path
  -> same ownership check
```

---

## 8. Error 계약

### Missing user

```json
{
  "error": "unauthenticated",
  "message": "X-User-Id header is required."
}
```

### Invalid user id

```json
{
  "error": "invalid_user_id",
  "message": "X-User-Id is malformed."
}
```

### Plant not found

```json
{
  "error": "plant_not_found",
  "message": "Plant was not found."
}
```

### Chat run not found

```json
{
  "error": "chat_run_not_found",
  "message": "Chat run was not found."
}
```

금지 error message:

```text
Plant exists but belongs to another user
Owner is demo-user-001
Access denied to user demo-user-002 for plant demo-plant-...
```

---

## 9. Functional Gate — 단순 실행 계약

Antigravity는 아래 수준의 gate를 통과해야 한다.

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "[Gate 1] quality"
ruff check app/auth app/domain/user_scope.py app/services/user_scope.py tests/test_user_scope.py tests/test_cross_user_access.py
ruff format --check app/auth app/domain/user_scope.py app/services/user_scope.py tests/test_user_scope.py tests/test_cross_user_access.py

echo "[Gate 2] user scope tests"
pytest -q tests/test_user_scope.py tests/test_cross_user_access.py

echo "[Gate 3] no production auth leakage"
python - <<'PY'
from pathlib import Path

targets = [
    Path("app/auth/dev_auth.py"),
    Path("app/domain/user_scope.py"),
    Path("app/services/user_scope.py"),
]

for path in targets:
    text = path.read_text()
    forbidden = [
        "oauth", "OAuth", "authlib", "oauthlib",
        "jwt", "JWT", "jose",
        "bcrypt", "argon2", "password",
        "refresh_token", "session", "cookie",
        "redis", "httpx", "requests", "aiohttp",
        "stripe", "billing",
    ]
    hits = [x for x in forbidden if x in text]
    assert not hits, f"{path}: forbidden auth leakage: {hits}"
PY

echo "[Gate 4] header parser contract"
python - <<'PY'
from app.auth.dev_auth import parse_current_user_from_headers

user = parse_current_user_from_headers({
    "x-user-id": "demo-user-001",
    "x-user-name": "Demo User",
})
assert user.user_id == "demo-user-001"
assert user.display_name == "Demo User"

for headers in [{}, {"x-user-id": ""}, {"x-user-id": "   "}]:
    try:
        parse_current_user_from_headers(headers)
    except Exception:
        pass
    else:
        raise AssertionError(f"expected auth failure for {headers}")
PY

echo "[Gate 5] healthz regression"
docker build -t sunshine-backend:ticket25 .
docker rm -f sunshine-backend-ticket25 >/dev/null 2>&1 || true
docker run -d \
  --name sunshine-backend-ticket25 \
  -p 8000:8000 \
  -e APP_NAME=sunshine-backend \
  -e APP_ENV=local \
  sunshine-backend:ticket25

cleanup() { docker rm -f sunshine-backend-ticket25 >/dev/null 2>&1 || true; }
trap cleanup EXIT

for i in $(seq 1 30); do
  if curl -fsS http://localhost:8000/healthz >/tmp/healthz.ticket25.json; then
    break
  fi
  sleep 1
done

test -s /tmp/healthz.ticket25.json
python - <<'PY'
import json
from pathlib import Path
body = json.loads(Path("/tmp/healthz.ticket25.json").read_text())
assert body == {"status": "ok", "service": "sunshine-backend"}, body
PY

echo "Ticket 25 gate: pass"
```

---

## 10. Required Tests

최소 테스트:

```text
test_parse_current_user_from_x_user_id_header
test_missing_x_user_id_returns_401
test_empty_x_user_id_returns_401
test_malformed_x_user_id_returns_400

test_create_plant_attaches_user_id
test_get_plants_returns_only_current_user_plants
test_get_other_user_plant_returns_404

test_create_care_log_for_other_user_plant_returns_404
test_sensor_reading_for_other_user_plant_returns_404
test_chat_for_other_user_plant_returns_404
test_chat_run_evidence_for_other_user_returns_404
test_companion_recommendation_for_other_user_plant_returns_404
test_growth_history_for_other_user_plant_returns_404

test_no_oauth_or_jwt_imported
test_healthz_contract_unchanged
test_no_readyz_added_by_ticket25
```

---

## 11. Acceptance Criteria

Ticket 25는 아래를 만족해야 pass다.

```text
- CurrentUser model exists
- X-User-Id dev auth parser/dependency exists
- missing X-User-Id returns 401
- empty X-User-Id returns 401
- malformed X-User-Id returns 400
- created plants attach current user_id
- created care logs attach current user_id or are scoped through owned plant
- created chat runs/evidence attach current user_id or are scoped through owned plant
- users can only list own plants
- users cannot read other users' plants
- users cannot write care logs to other users' plants
- users cannot create chat against other users' plants
- users cannot read other users' chat evidence
- sensor/history/companion paths are user-scoped
- no OAuth is implemented
- no JWT is implemented
- no password login is implemented
- no social login is implemented
- no billing is implemented
- no external identity provider is called
- no frontend auth UI is added
- /healthz remains liveness-only
- /readyz is not introduced or modified by this ticket
- pytest passes
- ruff passes
- Docker smoke gate passes
```

---

## 12. Do Not Implement

```text
OAuth
JWT
password login
logout endpoint
refresh token
session cookie
social login
email verification
RBAC
admin roles
billing
subscription check
API keys for users
frontend auth screen
mobile auth flow
CSRF framework
production secret management
new gateway/nginx auth
rate limiting
audit dashboard
Polaris
GPU telemetry
real LLM provider
SSE streaming
```

---

## 13. Antigravity 지시문

```text
Implement TICKET-025 only.

Focus on minimal MVP user scoping:
- X-User-Id header
- CurrentUser
- user_id ownership filtering
- cross-user access denial

Do not implement production authentication.
Do not implement OAuth/JWT/password/session/social login.
Do not add frontend auth UI.
Do not add billing/RBAC/admin roles.
Do not modify Docker/CI/runtime topology.
Do not change /healthz or add /readyz.

Use the allowed files only.
Add the required user-scope and cross-user tests.
Keep existing API response behavior unchanged except for auth/access-control errors.
```
