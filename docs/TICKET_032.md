# Ticket 32 — Antigravity Execution Contract

## 0. Goal

Implement the **Frontend Growth History** screen in the same bounded style as Ticket 14-derived contracts.

This ticket should give Antigravity one narrow job:

```text
Existing backend Growth History API
  -> frontend GrowthHistoryScreen
  -> timeline renderer
  -> care/environment/character history display
  -> loading / empty / error states
```

Do not implement backend history logic, history mutation, photo timeline, timelapse, growth graphs, weekly reports, P3 reports, or full audit viewers.

---

## 1. Ticket Identity

```text
Ticket ID: Ticket 32
Name: Frontend Growth History
Layer: Frontend User Flow 8 / Plant History Timeline UI

Depends on:
- Ticket 4: Character State Engine
- Ticket 7: Environment Snapshot Aggregation
- Ticket 11: Care Action Logging
- Ticket 12: Growth History API
- Ticket 25: Auth/User Scope Minimal
- Ticket 26: API Response Schemas + Frontend Contract
- Ticket 27: UI Shell / Frontend MVP Baseline
- Ticket 29: Frontend Home + Plant Detail
- Ticket 30: Frontend Care Log + Feedback

Does not depend on:
- Ticket 33: MVP Product Guardrail Tests
- Ticket 34: MVP Release Gate
- photo timeline
- timelapse
- growth graph
- weekly report
- P3 long report
```

---

## 2. What This Ticket Owns

Ticket 32 owns only:

```text
GrowthHistoryScreen
  -> call GET /plants/{plant_id}/history
  -> render timeline items
  -> sort by timestamp descending
  -> filter by all / care / environment / character
  -> show care log history
  -> show environment summary history
  -> show character state history
  -> show loading / empty / error states
```

The frontend must render the existing Ticket 26 `GrowthHistoryResponse` shape. It must not create, edit, or synthesize history records.

---

## 3. What This Ticket Must Not Own

Do not implement:

```text
backend history logic
DB schema changes
history event creation
history event editing
care-log creation/editing
chat history UI
full audit evidence viewer
photo timeline
image upload history
timelapse
growth graph
weekly report
monthly report
P3 long report
frontend Rule Engine
frontend LLM call
backend endpoint changes
Docker/compose changes
browser E2E automation
mobile/native code
```

---

## 4. Allowed Files

Antigravity may create or modify only:

```text
frontend/src/screens/GrowthHistoryScreen.tsx
frontend/src/api/client.ts
frontend/src/api/types.ts
frontend/src/api/history.ts
frontend/src/components/history/GrowthTimeline.tsx
frontend/src/components/history/GrowthTimelineItem.tsx
frontend/src/components/history/HistoryTypeBadge.tsx
frontend/src/components/history/HistoryEmptyState.tsx
frontend/src/components/history/HistoryFilterTabs.tsx
frontend/src/components/history/HistoryLoadingState.tsx
frontend/src/components/history/HistoryErrorState.tsx
frontend/src/state/historyState.ts
frontend/src/__tests__/growth_history_flow.test.tsx
frontend/src/__tests__/growth_history_api.test.ts
docs/frontend_growth_history_flow.md
```

Optional component tests:

```text
frontend/src/components/history/__tests__/GrowthTimeline.test.tsx
frontend/src/components/history/__tests__/GrowthTimelineItem.test.tsx
frontend/src/components/history/__tests__/HistoryTypeBadge.test.tsx
frontend/src/components/history/__tests__/HistoryFilterTabs.test.tsx
frontend/src/components/history/__tests__/HistoryEmptyState.test.tsx
```

Allowed narrow wiring only:

```text
frontend/src/routes.tsx
frontend/src/App.tsx
frontend/src/components/Nav.tsx
frontend/src/screens/PlantDetailScreen.tsx
```

These may only be changed to:

```text
- wire /plants/:plantId/history
- add Plant Detail -> Growth History navigation
- preserve Ticket 27/28/29/30/31 routes and behavior
```

---

## 5. Forbidden Files

Do not create or modify:

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
frontend/src/screens/CareLogScreen.tsx
frontend/src/screens/CompanionRecommendationScreen.tsx
frontend/src/components/chat/
frontend/src/components/care/
frontend/src/components/companion/
frontend/src/components/timelapse/
frontend/src/components/graphs/
playwright.config.*
cypress.config.*
selenium.*
```

Reason:

```text
Ticket 32 is frontend Growth History rendering only.
It must not change backend behavior, DB schema, Docker/CI topology, chat/care/companion flows, browser E2E, mobile-native code, graphing, or timelapse.
```

---

## 6. Screen Contract

Route:

```text
/plants/:plantId/history
```

Required visible content:

```text
- page title: 성장 기록
- current plant nickname or plant id fallback
- timeline list
- care log items
- note items
- environment summary items
- character state change items
- timestamp per item
- item type badge
- filter tabs
- loading state
- empty state
- error state
- navigation back to Plant Detail
```

Required Korean labels:

```text
성장 기록
최근 기록
물주기
메모
환경 요약
상태 변화
아직 기록이 없어요
기록을 불러오는 중이에요.
성장 기록을 불러오지 못했어요.
```

---

## 7. Timeline Item Contract

The frontend must render this existing backend shape:

```typescript
type GrowthHistoryItem = {
  type: "care_log" | "environment_summary" | "character_state";
  timestamp: string;
  title: string;
  summary: string;
};
```

Optional fields may be rendered only if already returned by the backend:

```typescript
type OptionalGrowthHistoryItemFields = {
  care_log_id?: string;
  snapshot_id?: string;
  character_state_id?: string;
  action?: "watering" | "note";
  mood?: string;
  expression?: string;
  severity?: "info" | "warning" | "critical";
};
```

Required badge mapping:

```text
care_log + action=watering -> 물주기
care_log + action=note     -> 메모
environment_summary        -> 환경 요약
character_state            -> 상태 변화
unknown safe fallback       -> 기타 기록
```

Rendering rules:

```text
- show title
- show summary
- show timestamp
- show type badge
- do not raw-dump JSON
- do not fabricate summary
- do not fabricate sensor values
- do not fabricate mood/expression
```

---

## 8. Sorting and Filter Contract

Required behavior:

```text
- default sort: timestamp descending
- invalid timestamp: render last or safe fallback
- 전체 tab: all items
- 관리 tab: care_log items
- 환경 tab: environment_summary items
- 상태 tab: character_state items
```

Forbidden behavior:

```text
- mutate backend records
- call backend again for each filter tab
- generate new history items on frontend
- merge chat/evidence records into timeline
```

---

## 9. API Client Contract

Add or extend:

```typescript
getGrowthHistory(plantId: string): Promise<GrowthHistoryResponse>;
```

Required request header:

```http
X-User-Id: demo-user-001
```

Allowed endpoint calls:

```text
GET /plants/{plant_id}/history
GET /healthz only for backend smoke
```

Forbidden endpoint calls in Ticket 32 frontend code:

```text
POST /plants/{plant_id}/care-logs
GET /plants/{plant_id}/care-logs
POST /plants/{plant_id}/chat
GET /chat-runs/{request_id}/evidence
GET /plants/{plant_id}/companion-recommendations
POST /sensor-readings
```

---

## 10. State Contract

Create minimal frontend state for:

```text
items
selectedFilter
loading
error
```

Do not persist timeline state to localStorage. Do not create optimistic history records. Do not cache cross-plant history globally.

---

## 11. Empty / Loading / Error Contract

Loading:

```text
기록을 불러오는 중이에요.
```

Empty:

```text
아직 기록이 없어요.
```

Empty state must include:

```text
- link/button to Plant Detail
- optional link/button to Care Log screen
```

Error:

```text
성장 기록을 불러오지 못했어요.
```

Error state may include retry if the existing frontend pattern already supports retry.

Forbidden:

```text
- auto-creating sample history items
- silently hiding API errors
- hardcoded fake timeline in runtime UI
```

---

## 12. Runtime Contract

Allowed runtime shape:

```text
frontend dev server
  -> browser
  -> existing backend GET /plants/{plant_id}/history
  -> render timeline response
```

Backend runtime remains unchanged:

```text
backend container
  -> uvicorn app.main:app
  -> /healthz
  -> existing MVP APIs
```

Forbidden runtime shape:

```text
frontend
  -> starts backend
  -> starts DB
  -> starts worker
  -> starts report generator
  -> starts timelapse processor
  -> starts graph rendering service
  -> starts browser E2E runner
```

---

## 13. Network / Env Contract

Allowed frontend env inherited from Ticket 27:

```env
VITE_SUNSHINE_API_BASE_URL=http://localhost:8000
VITE_SUNSHINE_DEMO_USER_ID=demo-user-001
```

Forbidden env vars:

```text
REPORT_*
TIMELAPSE_*
GRAPH_*
OPENAI_*
ANTHROPIC_*
VLLM_*
MQTT_*
REDIS_*
MARKETPLACE_*
ANALYTICS_*
```

Do not edit backend `.env.example`.

---

## 14. Health Boundary

Ticket 32 must not modify:

```http
GET /healthz
```

Ticket 32 must not add or modify:

```http
GET /readyz
```

Permanent invariant:

```text
/healthz = backend process liveness only
/readyz = dependency readiness only
```

Frontend may call `/healthz` only for backend connectivity smoke. It must not interpret `/healthz` as DB/history-table/readiness.

---

## 15. Required Tests

Add at least:

```text
test_growth_history_screen_renders_title
test_growth_history_screen_fetches_history
test_growth_history_api_client_sends_x_user_id
test_growth_history_renders_watering_log_item
test_growth_history_renders_note_item
test_growth_history_renders_environment_summary_item
test_growth_history_renders_character_state_item
test_growth_history_sorts_items_descending_by_timestamp
test_growth_history_filter_all_shows_all_items
test_growth_history_filter_care_shows_care_log_items
test_growth_history_filter_environment_shows_environment_summary_items
test_growth_history_filter_character_shows_character_state_items
test_growth_history_empty_state
test_growth_history_loading_state
test_growth_history_error_state
test_growth_history_invalid_timestamp_safe_fallback
test_growth_history_does_not_call_mutation_endpoints
test_no_photo_timeline_timelapse_or_growth_graph
test_healthz_contract_unchanged
test_no_readyz_added_by_ticket32
```

---

## 16. Functional Gate

Use this as the Antigravity acceptance gate.

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "[Gate 0] Ticket 32 scope boundary"

git diff --name-only origin/main...HEAD | tee /tmp/ticket32_changed_files.txt || true

python - <<'PY'
from pathlib import Path

allowed = {
    "frontend/src/screens/GrowthHistoryScreen.tsx",
    "frontend/src/api/client.ts",
    "frontend/src/api/types.ts",
    "frontend/src/api/history.ts",
    "frontend/src/components/history/GrowthTimeline.tsx",
    "frontend/src/components/history/GrowthTimelineItem.tsx",
    "frontend/src/components/history/HistoryTypeBadge.tsx",
    "frontend/src/components/history/HistoryEmptyState.tsx",
    "frontend/src/components/history/HistoryFilterTabs.tsx",
    "frontend/src/components/history/HistoryLoadingState.tsx",
    "frontend/src/components/history/HistoryErrorState.tsx",
    "frontend/src/components/history/__tests__/GrowthTimeline.test.tsx",
    "frontend/src/components/history/__tests__/GrowthTimelineItem.test.tsx",
    "frontend/src/components/history/__tests__/HistoryTypeBadge.test.tsx",
    "frontend/src/components/history/__tests__/HistoryFilterTabs.test.tsx",
    "frontend/src/components/history/__tests__/HistoryEmptyState.test.tsx",
    "frontend/src/state/historyState.ts",
    "frontend/src/routes.tsx",
    "frontend/src/App.tsx",
    "frontend/src/components/Nav.tsx",
    "frontend/src/screens/PlantDetailScreen.tsx",
    "frontend/src/__tests__/growth_history_flow.test.tsx",
    "frontend/src/__tests__/growth_history_api.test.ts",
    "docs/frontend_growth_history_flow.md",
}

forbidden_prefixes = (
    "app/",
    "alembic/",
    "migrations/",
    ".github/workflows/",
    "mobile/",
    "ios/",
    "android/",
    "frontend/src/components/timelapse/",
    "frontend/src/components/graphs/",
)

forbidden_exact = {
    "Dockerfile",
    "docker-compose.yml",
    ".env.example",
    "frontend/src/screens/ChatScreen.tsx",
    "frontend/src/screens/CareLogScreen.tsx",
    "frontend/src/screens/CompanionRecommendationScreen.tsx",
    "playwright.config.ts",
    "playwright.config.js",
    "cypress.config.ts",
    "cypress.config.js",
}

changed = []
path = Path("/tmp/ticket32_changed_files.txt")
if path.exists():
    changed = [line.strip() for line in path.read_text().splitlines() if line.strip()]

violations = []
for file in changed:
    if file in forbidden_exact:
        violations.append(("forbidden_exact_file", file))
    if file.startswith(forbidden_prefixes):
        violations.append(("forbidden_prefix", file))
    if file not in allowed and not file.startswith("frontend/src/components/history/"):
        violations.append(("not_in_allowed_files", file))

if violations:
    for kind, file in violations:
        print(f"{kind}: {file}")
    raise SystemExit(1)

print("ticket32_scope_boundary: pass")
PY


echo "[Gate 1] Frontend dependency install"
cd frontend
npm ci


echo "[Gate 2] TypeScript check"
npm run typecheck


echo "[Gate 3] Frontend growth-history tests"
npm test -- --run \
  src/__tests__/growth_history_flow.test.tsx \
  src/__tests__/growth_history_api.test.ts \
  src/components/history/__tests__ || true

# Fallback for runners without directory args:
npm test -- --run


echo "[Gate 4] Build frontend"
npm run build
cd ..


echo "[Gate 5] Required history screen/components exist"

python - <<'PY'
from pathlib import Path

required = [
    "frontend/src/screens/GrowthHistoryScreen.tsx",
    "frontend/src/components/history/GrowthTimeline.tsx",
    "frontend/src/components/history/GrowthTimelineItem.tsx",
    "frontend/src/components/history/HistoryTypeBadge.tsx",
    "frontend/src/components/history/HistoryEmptyState.tsx",
    "frontend/src/components/history/HistoryFilterTabs.tsx",
    "frontend/src/components/history/HistoryLoadingState.tsx",
    "frontend/src/components/history/HistoryErrorState.tsx",
]

for file in required:
    assert Path(file).exists(), file

print("growth_history_screen_components_exist: pass")
PY


echo "[Gate 6] Growth history API client contract"

python - <<'PY'
from pathlib import Path

client = Path("frontend/src/api/client.ts").read_text()
history_api = Path("frontend/src/api/history.ts").read_text() if Path("frontend/src/api/history.ts").exists() else ""
types = Path("frontend/src/api/types.ts").read_text()

combined = client + "\n" + history_api

required_tokens = [
    "getGrowthHistory",
    "/history",
    "X-User-Id",
]
missing = [token for token in required_tokens if token not in combined]
assert not missing, missing

for typ in ["GrowthHistoryResponse", "GrowthHistoryItem"]:
    assert typ in types, typ

print("growth_history_api_client_contract: pass")
PY


echo "[Gate 7] Timeline renderer contract"

python - <<'PY'
from pathlib import Path

timeline = Path("frontend/src/components/history/GrowthTimeline.tsx").read_text()
item = Path("frontend/src/components/history/GrowthTimelineItem.tsx").read_text()
badge = Path("frontend/src/components/history/HistoryTypeBadge.tsx").read_text()
combined = timeline + "\n" + item + "\n" + badge

required_tokens = [
    "care_log",
    "environment_summary",
    "character_state",
    "timestamp",
    "title",
    "summary",
    "물주기",
    "메모",
    "환경 요약",
    "상태 변화",
]
missing = [token for token in required_tokens if token not in combined]
assert not missing, missing

print("timeline_renderer_contract: pass")
PY


echo "[Gate 8] No later-feature / mutation endpoint leakage"

python - <<'PY'
from pathlib import Path

targets = [
    Path("frontend/src/screens/GrowthHistoryScreen.tsx"),
    Path("frontend/src/api/client.ts"),
    Path("frontend/src/api/history.ts") if Path("frontend/src/api/history.ts").exists() else None,
    *Path("frontend/src/components/history").rglob("*.tsx"),
]
targets = [p for p in targets if p is not None]

for path in targets:
    text = path.read_text(errors="ignore")
    forbidden_tokens = [
        "POST /plants",
        "method: \"POST\"",
        "method: 'POST'",
        "/care-logs",
        "/chat",
        "/chat-runs/",
        "/companion-recommendations",
        "/sensor-readings",
        "askChat",
        "createCareLog",
        "getCompanionRecommendations",
        "timelapse",
        "TimeLapse",
        "growth graph",
        "GrowthGraph",
        "weekly report",
        "monthly report",
        "P3",
        "long report",
        "openai",
        "anthropic",
        "vllm",
        "marketplace",
        "purchase",
        "affiliate",
    ]
    hits = [token for token in forbidden_tokens if token in text]
    assert not hits, f"{path}: forbidden leakage: {hits}"

print("no_later_feature_or_mutation_endpoint_leakage: pass")
PY


echo "[Gate 9] Required route wiring"

python - <<'PY'
from pathlib import Path

routes = Path("frontend/src/routes.tsx").read_text()
required_route = "/plants/:plantId/history"
assert required_route in routes, required_route

print("growth_history_route_wired: pass")
PY


echo "[Gate 10] Backend Docker health regression"

docker build -t sunshine-backend:ticket32 .

docker rm -f sunshine-backend-ticket32 >/dev/null 2>&1 || true

docker run -d \
  --name sunshine-backend-ticket32 \
  -p 8000:8000 \
  -e APP_NAME=sunshine-backend \
  -e APP_ENV=local \
  sunshine-backend:ticket32

cleanup() {
  docker rm -f sunshine-backend-ticket32 >/dev/null 2>&1 || true
}
trap cleanup EXIT

for i in $(seq 1 30); do
  if curl -fsS http://localhost:8000/healthz >/tmp/healthz.ticket32.json; then
    break
  fi
  sleep 1
done

test -s /tmp/healthz.ticket32.json

python - <<'PY'
import json
from pathlib import Path

body = json.loads(Path("/tmp/healthz.ticket32.json").read_text())
assert body == {"status": "ok", "service": "sunshine-backend"}, body
print("healthz_liveness_regression: pass")
PY


echo "[Gate 11] Backend growth-history API smoke"

curl -fsS \
  -H "X-User-Id: demo-user-001" \
  "http://localhost:8000/plants/demo-plant-chorok-001/history" \
  > /tmp/ticket32.history.json

python - <<'PY'
import json
from pathlib import Path

body = json.loads(Path("/tmp/ticket32.history.json").read_text())
text = json.dumps(body, ensure_ascii=False)

assert "plant_id" in text, "plant_id"
assert "items" in body or "items" in text, "items"

items = body.get("items", [])
assert isinstance(items, list), type(items)

required_types = {"care_log", "environment_summary", "character_state"}
seen = {item.get("type") for item in items if isinstance(item, dict)}
assert seen & required_types, f"expected at least one MVP history type, got {seen}"

for item in items:
    if not isinstance(item, dict):
        continue
    for key in ["type", "timestamp", "title", "summary"]:
        assert key in item, (key, item)

print("backend_growth_history_api_smoke: pass")
PY


echo "[Gate 12] Readiness boundary check"

if grep -R "readyz" frontend docs; then
  echo "forbidden_readyz_frontend: Ticket 32 must not introduce /readyz semantics"
  exit 1
fi

if grep -R "readyz" app tests >/dev/null 2>&1; then
  echo "forbidden_readyz_backend: Ticket 32 must not modify backend readiness"
  exit 1
fi

echo "readyz_absent_or_unchanged: pass"


echo "[Gate 13] Report"

cat <<'REPORT'
Ticket 32 Functional Gate Report

Scope:
- frontend Growth History only: pass
- no backend code changes: pass
- no Docker/compose changes: pass
- no Chat UI changes: pass
- no Care Log UI changes: pass
- no Companion UI changes: pass
- no photo timeline/timelapse/growth graph: pass
- no weekly/P3 long report: pass

Frontend:
- GrowthHistoryScreen: pass
- timeline renderer: pass
- care history visible: pass
- environment history visible: pass
- character state changes visible: pass
- filtering tabs: pass
- loading/empty/error states: pass
- API client sends X-User-Id: pass

Runtime:
- backend /healthz remains liveness-only: pass
- /readyz not introduced by this ticket: pass
- Docker backend smoke passed: pass

Result:
- pass
REPORT
```

---

## 17. Acceptance Criteria

Ticket 32 passes only if all are true:

```text
- GrowthHistoryScreen exists
- /plants/:plantId/history route is wired
- getGrowthHistory calls GET /plants/{plant_id}/history
- API client sends X-User-Id
- timeline renders care_log watering items
- timeline renders care_log note items
- timeline renders environment_summary items
- timeline renders character_state items
- timeline shows timestamp/title/summary per item
- timeline sorts by timestamp descending by default
- filter tabs work for all/care/environment/character
- loading state exists
- empty state exists
- error state exists
- invalid timestamps are handled safely
- frontend does not create or mutate history records
- frontend does not call care/chat/companion/sensor endpoints
- no photo timeline is implemented
- no timelapse is implemented
- no growth graph is implemented
- no weekly/P3 long report is implemented
- no backend product code is modified
- frontend build passes
- frontend tests pass
- backend /healthz remains liveness-only
- /readyz is not introduced or modified by this ticket
- Docker backend smoke passes
```

---

## 18. Minimal Mermaid Flow

```mermaid
flowchart TD
    A[GrowthHistoryScreen] --> B[getGrowthHistory]
    B --> C[GET /plants/{plant_id}/history]
    C --> D[GrowthHistoryResponse]
    D --> E[Sort by timestamp desc]
    E --> F[Filter tabs]
    F --> G[GrowthTimeline]
    G --> H[GrowthTimelineItem]
    H --> I[HistoryTypeBadge]

    D --> J[Loading / Empty / Error states]

    X[Forbidden] -. no .-> X1[backend changes]
    X -. no .-> X2[history mutation]
    X -. no .-> X3[photo timeline]
    X -. no .-> X4[timelapse]
    X -. no .-> X5[growth graph]
    X -. no .-> X6[weekly or P3 report]
    X -. no .-> X7[full audit viewer]
```

---

## 19. Boundary Verdict

```text
Scope preserved: yes
Later-ticket leakage: no
Product guardrail suite implemented: no
Release gate implemented: no
Photo timeline implemented: no
Timelapse implemented: no
Growth graph implemented: no
Weekly/P3 long report implemented: no
Full audit viewer implemented: no
History mutation implemented: no
Backend product code modified: no
Docker/compose modified: no
/healthz modified: no
/readyz introduced: no
Ticket 32 independently verifiable: yes
```
