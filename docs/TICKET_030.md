# TICKET-030 — Frontend Care Log + Feedback

## 0. 목표

Sunshine frontend에 **관리 기록 UI**를 구현한다.

이 티켓은 backend 기능을 만들지 않는다.  
이 티켓은 Rule Engine을 frontend에서 재구현하지 않는다.  
이 티켓은 reminder/push/chat/history/companion UI를 만들지 않는다.

Ticket 30의 책임은 아래까지만이다.

```text
CareLogScreen
  -> watering action button
  -> note input
  -> POST care log
  -> feedback display
  -> recent care logs list
```

---

## 1. Ticket Identity

### Ticket ID

```text
TICKET-030
```

### Name

```text
Frontend Care Log + Feedback
```

### Goal

```text
Implement the frontend care-log UI so a user can record watering or a note, receive immediate feedback, and view recent care logs for the current plant.
```

### Core output

```text
CareLogScreen
CareActionButtons
CareNoteForm
CareFeedbackCard
RecentCareLogs
CareLogItem
care log API client methods
care log frontend state
care log UI tests
```

### Strict non-goal

```text
no backend code changes
no DB migration
no Docker or compose changes
no chat UI
no growth history timeline
no companion recommendation UI
no reminders
no push notification
no pruning / repotting / fertilizing
no frontend Rule Engine
no frontend LLM call
no browser E2E automation
```

---

## 2. 주변 티켓과의 연결

Ticket 30은 frontend care-log UI만 담당한다.

```text
Ticket 27:
  frontend shell and routes exist

Ticket 29:
  PlantDetailScreen may link to CareLogScreen

Ticket 30:
  user records watering/note and sees backend feedback

Ticket 31:
  Chat UI is implemented later

Ticket 32:
  Growth History UI is implemented later
```

허용 흐름:

```text
/plants/:plantId/care-logs
  -> POST /plants/{plant_id}/care-logs
  -> GET /plants/{plant_id}/care-logs
  -> render feedback and recent logs
```

금지 흐름:

```text
CareLogScreen
  -> chat answer
  -> growth timeline
  -> companion recommendation
  -> reminder scheduling
  -> frontend-generated care decision
```

---

## 3. 수정/생성 허용 파일

### 생성/수정 가능한 파일

```text
frontend/src/screens/CareLogScreen.tsx
frontend/src/api/client.ts
frontend/src/api/types.ts
frontend/src/api/careLogs.ts
frontend/src/components/care/CareActionButtons.tsx
frontend/src/components/care/CareNoteForm.tsx
frontend/src/components/care/CareFeedbackCard.tsx
frontend/src/components/care/RecentCareLogs.tsx
frontend/src/components/care/CareLogItem.tsx
frontend/src/state/careLogState.ts
frontend/src/__tests__/care_log_flow.test.tsx
frontend/src/__tests__/care_log_api.test.ts
docs/frontend_care_log_flow.md
```

### 선택 생성 가능

```text
frontend/src/components/care/__tests__/CareActionButtons.test.tsx
frontend/src/components/care/__tests__/CareNoteForm.test.tsx
frontend/src/components/care/__tests__/CareFeedbackCard.test.tsx
frontend/src/components/care/__tests__/RecentCareLogs.test.tsx
```

### 좁은 수정 허용

```text
frontend/src/routes.tsx
frontend/src/App.tsx
frontend/src/components/Nav.tsx
frontend/src/screens/PlantDetailScreen.tsx
```

허용 목적:

```text
wire /plants/:plantId/care-logs route
add navigation link from Plant Detail to Care Log
preserve existing Ticket 27/28/29 routes
```

---

## 4. 금지 파일/디렉터리

아래는 생성하거나 수정하지 않는다.

```text
app/
alembic/
migrations/
Dockerfile
docker-compose.yml
.env.example
.github/workflows/
mobile/
ios/
android/

frontend/src/screens/ChatScreen.tsx
frontend/src/screens/GrowthHistoryScreen.tsx
frontend/src/screens/CompanionRecommendationScreen.tsx

frontend/src/components/chat/
frontend/src/components/history/
frontend/src/components/companion/

playwright.config.*
cypress.config.*
selenium.*
```

규칙:

```text
Ticket 30 must not modify backend behavior, database schema, Docker/CI topology, later frontend flows, browser E2E, or mobile-native code.
```

---

## 5. UI 계약

### Route

```text
/plants/:plantId/care-logs
```

### Required visible content

```text
관리 기록
current plant nickname or plant id fallback
물 줬어요
메모 남기기
기록 저장
최근 관리 기록
저장되었습니다
navigation back to plant detail
```

### Required states

```text
loading state while submitting
success feedback state
error state
empty recent logs state
validation state for empty note
```

---

## 6. Watering Action 계약

사용자가 `물 줬어요`를 누르면:

```text
POST /plants/{plant_id}/care-logs
```

Payload:

```json
{
  "action": "watering",
  "note": null
}
```

필수 동작:

```text
show loading state
send X-User-Id header
render backend CareLogFeedbackResponse
refresh recent care logs after success
do not optimistic-save unconfirmed record
```

금지:

```text
compute whether watering is needed on frontend
override Rule Engine action
change watering into another care type
create reminder schedule after watering
```

---

## 7. Note Action 계약

사용자가 note를 입력하면:

```text
POST /plants/{plant_id}/care-logs
```

Payload:

```json
{
  "action": "note",
  "note": "잎 상태가 좋아 보임"
}
```

필수 동작:

```text
trim whitespace before validation
reject empty note
send X-User-Id header
render backend feedback
refresh recent logs after success
preserve typed note when POST fails
```

주의:

```text
Do not invent a backend max length unless Ticket 26 schema exposes one.
```

---

## 8. Feedback Display 계약

Frontend는 Ticket 26의 `CareLogFeedbackResponse`를 렌더링한다.

필수 표시:

```text
care_log_id
action
recorded_at
feedback.message
feedback.character_mood if present
```

규칙:

```text
If backend returns character mood/expression, display it as backend-provided feedback.
Do not generate new mood text locally.
```

금지:

```text
frontend-generated character mood
frontend-generated care advice
LLM-generated feedback
hardcoded "이제 물을 더 주지 마세요" unless returned by backend
```

---

## 9. Recent Care Logs 계약

필수 호출:

```text
GET /plants/{plant_id}/care-logs
```

필수 표시:

```text
recent watering logs
recent note logs
action
note if present
recorded_at
empty state if none
```

금지:

```text
growth history timeline
environment summary events
chat answer history
companion recommendation history
```

---

## 10. API Client 계약

추가 또는 확장할 methods:

```typescript
createCareLog(
  plantId: string,
  input: {
    action: "watering" | "note";
    note?: string | null;
  }
): Promise<CareLogFeedbackResponse>;

getCareLogs(
  plantId: string
): Promise<CareLogListResponse>;
```

필수 header:

```http
X-User-Id: demo-user-001
```

허용 endpoints:

```text
POST /plants/{plant_id}/care-logs
GET /plants/{plant_id}/care-logs
GET /healthz for smoke only
```

금지 endpoints:

```text
POST /plants/{plant_id}/chat
GET /plants/{plant_id}/history
GET /plants/{plant_id}/companion-recommendations
POST /sensor-readings
```

---

## 11. Runtime 계약

Ticket 30은 frontend UI ticket이다.

허용 runtime:

```text
frontend dev server
  -> browser
  -> existing backend care-log APIs
  -> render feedback and recent logs
```

금지 runtime:

```text
new backend process
new worker
new scheduler
new reminder loop
new push daemon
new browser automation daemon
new model loader
```

Network 금지:

```text
external LLM
push provider
analytics SaaS
marketplace
```

Environment 금지:

```text
PUSH_*
REMINDER_*
SCHEDULER_*
OPENAI_*
ANTHROPIC_*
VLLM_*
MQTT_*
REDIS_*
MARKETPLACE_*
```

---

## 12. `/healthz` / `/readyz` 계약

Ticket 30은 backend health endpoint를 수정하지 않는다.

```text
GET /healthz:
  must remain backend process liveness only

GET /readyz:
  must not be added or modified by this ticket
```

Frontend may call `/healthz` only for backend connectivity smoke.

금지:

```text
treating /healthz as care-log DB readiness
treating /healthz as reminder readiness
adding /readyz semantics in frontend
```

---

## 13. Functional Gate

아래 gate를 통과해야 한다.

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "[Gate 0] Scope boundary"
git diff --name-only origin/main...HEAD | tee /tmp/ticket30_changed_files.txt || true

python - <<'PY'
from pathlib import Path

allowed = {
    "frontend/src/screens/CareLogScreen.tsx",
    "frontend/src/api/client.ts",
    "frontend/src/api/types.ts",
    "frontend/src/api/careLogs.ts",
    "frontend/src/components/care/CareActionButtons.tsx",
    "frontend/src/components/care/CareNoteForm.tsx",
    "frontend/src/components/care/CareFeedbackCard.tsx",
    "frontend/src/components/care/RecentCareLogs.tsx",
    "frontend/src/components/care/CareLogItem.tsx",
    "frontend/src/components/care/__tests__/CareActionButtons.test.tsx",
    "frontend/src/components/care/__tests__/CareNoteForm.test.tsx",
    "frontend/src/components/care/__tests__/CareFeedbackCard.test.tsx",
    "frontend/src/components/care/__tests__/RecentCareLogs.test.tsx",
    "frontend/src/state/careLogState.ts",
    "frontend/src/routes.tsx",
    "frontend/src/App.tsx",
    "frontend/src/components/Nav.tsx",
    "frontend/src/screens/PlantDetailScreen.tsx",
    "frontend/src/__tests__/care_log_flow.test.tsx",
    "frontend/src/__tests__/care_log_api.test.ts",
    "docs/frontend_care_log_flow.md",
}

forbidden_prefixes = (
    "app/",
    "alembic/",
    "migrations/",
    ".github/workflows/",
    "mobile/",
    "ios/",
    "android/",
)

forbidden_exact = {
    "Dockerfile",
    "docker-compose.yml",
    ".env.example",
    "frontend/src/screens/ChatScreen.tsx",
    "frontend/src/screens/GrowthHistoryScreen.tsx",
    "frontend/src/screens/CompanionRecommendationScreen.tsx",
    "playwright.config.ts",
    "playwright.config.js",
    "cypress.config.ts",
    "cypress.config.js",
}

changed = [
    line.strip()
    for line in Path("/tmp/ticket30_changed_files.txt").read_text().splitlines()
    if line.strip()
]

violations = []
for file in changed:
    if file in forbidden_exact:
        violations.append(("forbidden_exact_file", file))
    if file.startswith(forbidden_prefixes):
        violations.append(("forbidden_prefix", file))
    if file not in allowed and not file.startswith("frontend/src/components/care/"):
        violations.append(("not_in_allowed_files", file))

if violations:
    for kind, file in violations:
        print(f"{kind}: {file}")
    raise SystemExit(1)

print("ticket30_scope_boundary: pass")
PY

echo "[Gate 1] Frontend checks"
cd frontend
npm ci
npm run typecheck
npm test -- --run
npm run build
cd ..

echo "[Gate 2] Required files"
python - <<'PY'
from pathlib import Path

required = [
    "frontend/src/screens/CareLogScreen.tsx",
    "frontend/src/components/care/CareActionButtons.tsx",
    "frontend/src/components/care/CareNoteForm.tsx",
    "frontend/src/components/care/CareFeedbackCard.tsx",
    "frontend/src/components/care/RecentCareLogs.tsx",
    "frontend/src/components/care/CareLogItem.tsx",
]

for file in required:
    assert Path(file).exists(), file

print("care_log_screen_components_exist: pass")
PY

echo "[Gate 3] API client contract"
python - <<'PY'
from pathlib import Path

client = Path("frontend/src/api/client.ts").read_text()
care_api = Path("frontend/src/api/careLogs.ts").read_text() if Path("frontend/src/api/careLogs.ts").exists() else ""
types = Path("frontend/src/api/types.ts").read_text()
combined = client + "\n" + care_api

required_tokens = [
    "createCareLog",
    "getCareLogs",
    "/care-logs",
    "X-User-Id",
    "watering",
    "note",
]
missing = [token for token in required_tokens if token not in combined]
assert not missing, missing

for typ in ["CareLogFeedbackResponse", "CareLogListResponse"]:
    assert typ in types, typ

print("care_log_api_client_contract: pass")
PY

echo "[Gate 4] Leakage checks"
python - <<'PY'
from pathlib import Path

targets = [
    Path("frontend/src/screens/CareLogScreen.tsx"),
    Path("frontend/src/api/client.ts"),
    Path("frontend/src/api/careLogs.ts") if Path("frontend/src/api/careLogs.ts").exists() else None,
    *Path("frontend/src/components/care").rglob("*.tsx"),
]
targets = [p for p in targets if p is not None]

for path in targets:
    text = path.read_text(errors="ignore")
    forbidden = [
        "/chat",
        "/history",
        "/companion-recommendations",
        "/sensor-readings",
        "askChat",
        "getGrowthHistory",
        "getCompanionRecommendations",
        "reminder",
        "Reminder",
        "push notification",
        "Notification.requestPermission",
        "setInterval",
        "schedule",
        "pruning",
        "repotting",
        "fertilizing",
        "soil_moisture_pct <",
        "computeAction",
        "ruleEngine",
        "openai",
        "anthropic",
        "vllm",
    ]
    hits = [token for token in forbidden if token in text]
    assert not hits, f"{path}: forbidden leakage: {hits}"

print("care_log_leakage_checks: pass")
PY

echo "[Gate 5] Route check"
python - <<'PY'
from pathlib import Path
routes = Path("frontend/src/routes.tsx").read_text()
assert "/plants/:plantId/care-logs" in routes
print("care_log_route_wired: pass")
PY

echo "[Gate 6] Backend smoke"
docker build -t sunshine-backend:ticket30 .
docker rm -f sunshine-backend-ticket30 >/dev/null 2>&1 || true
docker run -d   --name sunshine-backend-ticket30   -p 8000:8000   -e APP_NAME=sunshine-backend   -e APP_ENV=local   sunshine-backend:ticket30

cleanup() {
  docker rm -f sunshine-backend-ticket30 >/dev/null 2>&1 || true
}
trap cleanup EXIT

for i in $(seq 1 30); do
  if curl -fsS http://localhost:8000/healthz >/tmp/healthz.ticket30.json; then
    break
  fi
  sleep 1
done

python - <<'PY'
import json
from pathlib import Path
body = json.loads(Path("/tmp/healthz.ticket30.json").read_text())
assert body == {"status": "ok", "service": "sunshine-backend"}, body
print("healthz_liveness_regression: pass")
PY

curl -fsS   -X POST "http://localhost:8000/plants/demo-plant-chorok-001/care-logs"   -H "Content-Type: application/json"   -H "X-User-Id: demo-user-001"   -d '{"action":"watering","note":null}'   > /tmp/ticket30.carelog.post.json

curl -fsS   -H "X-User-Id: demo-user-001"   "http://localhost:8000/plants/demo-plant-chorok-001/care-logs"   > /tmp/ticket30.carelog.get.json

python - <<'PY'
import json
from pathlib import Path

post = json.loads(Path("/tmp/ticket30.carelog.post.json").read_text())
get = json.loads(Path("/tmp/ticket30.carelog.get.json").read_text())

post_text = json.dumps(post, ensure_ascii=False)
for required in ["care_log_id", "action", "recorded_at", "feedback"]:
    assert required in post_text, required

get_text = json.dumps(get, ensure_ascii=False)
assert "watering" in get_text or "note" in get_text

print("backend_care_log_api_smoke: pass")
PY

echo "[Gate 7] Readiness boundary"
if grep -R "readyz" frontend docs; then
  echo "forbidden_readyz_frontend"
  exit 1
fi

if grep -R "readyz" app tests >/dev/null 2>&1; then
  echo "forbidden_readyz_backend"
  exit 1
fi

echo "ticket30_functional_gate: pass"
```

---

## 14. Required Tests

최소 테스트:

```text
test_care_log_screen_renders_title
test_care_log_screen_renders_watering_button
test_care_log_screen_renders_note_form
test_watering_button_posts_watering_action
test_note_form_requires_non_empty_note
test_note_form_posts_note_action
test_success_response_renders_feedback_card
test_feedback_card_shows_character_mood_when_present
test_recent_care_logs_renders_watering_and_note_items
test_recent_care_logs_empty_state
test_successful_post_refreshes_recent_logs
test_post_failure_shows_error_state
test_get_logs_failure_shows_error_state
test_care_log_api_client_sends_x_user_id
test_only_watering_and_note_actions_are_visible
test_no_reminder_or_push_code
test_no_frontend_rule_engine
test_no_chat_history_companion_endpoint_calls
test_healthz_contract_unchanged
test_no_readyz_added_by_ticket30
```

---

## 15. Acceptance Criteria

Ticket 30은 아래 조건을 모두 만족해야 한다.

```text
CareLogScreen exists
/plants/:plantId/care-logs route is wired
watering action button is visible
note form is visible
only watering and note actions are exposed
tapping watering calls POST /plants/{plant_id}/care-logs with action=watering
submitting note calls POST /plants/{plant_id}/care-logs with action=note
note action rejects empty note text
success feedback is rendered from backend response
character mood feedback is rendered only if backend returns it
recent care logs are loaded with GET /plants/{plant_id}/care-logs
recent logs show watering and note items
successful POST refreshes recent logs
API client sends X-User-Id
frontend does not compute care decisions
frontend does not implement reminders/push
frontend does not call chat/history/companion APIs
frontend build passes
frontend tests pass
backend /healthz remains liveness-only
/readyz is not introduced or modified by this ticket
Docker backend smoke passes
```
s