# TICKET-027 — UI Shell / Frontend MVP Baseline

## 0. 목표

Sunshine MVP를 수동으로 시연할 수 있는 최소 frontend shell을 만든다.

이 티켓은 화면별 깊은 UX 구현을 하지 않는다.  
이 티켓은 backend API를 새로 만들지 않는다.  
이 티켓은 mobile/native app을 만들지 않는다.

Ticket 27의 책임은 아래까지만이다.

```text
Ticket 26 frontend-facing API contract
  -> minimal Vite/React/TypeScript frontend shell
  -> MVP route skeletons
  -> shared API client
  -> demo user header support
  -> manual demo navigation
  -> frontend build/test smoke
```

---

## 1. Ticket Identity

### Ticket ID

```text
TICKET-027
```

### Name

```text
UI Shell / Frontend MVP Baseline
```

### Goal

```text
Create a minimal frontend shell that can manually navigate all MVP screens and call existing backend APIs using Ticket 26 response contracts.
```

### Core output

```text
Vite React TypeScript frontend shell
route/page skeletons
shared API client
Ticket 26 response types mirror
X-User-Id demo auth header
manual MVP navigation
loading/error components
frontend unit tests
frontend build gate
```

### Strict non-goal

```text
no backend API changes
no backend business logic changes
no database migration
no Docker/compose change
no production mobile app
no React Native
no push notification
no timelapse
no camera integration
no browser E2E automation
no Playwright/Cypress/Selenium
no auth login UI
no OAuth/JWT flow
no marketplace/purchase links
no streaming chat UI
```

---

## 2. 주변 티켓과의 연결

Ticket 27은 frontend 구현의 첫 shell이다.

```text
Ticket 23:
  demo seed data를 제공

Ticket 24:
  backend MVP E2E harness를 제공

Ticket 25:
  X-User-Id 기반 minimal user scope를 제공

Ticket 26:
  frontend가 따라야 할 API response schema를 제공

Ticket 27:
  frontend shell / routes / API client를 생성

Ticket 28:
  onboarding flow를 상세 구현

Ticket 29:
  home + plant detail을 상세 구현

Ticket 30:
  care log + feedback을 상세 구현

Ticket 31:
  chat + answer view를 상세 구현

Ticket 32:
  growth history view를 상세 구현
```

Ticket 27의 역할:

```text
frontend user
  -> route navigation
  -> minimal screen skeleton
  -> API client with X-User-Id
  -> render backend response or placeholder
```

금지:

```text
backend endpoint 생성
backend schema 변경
screen별 완성 UX 구현
native mobile implementation
browser automation
production auth flow
```

---

## 3. 수정/생성 허용 파일

### 생성 가능한 frontend 파일

```text
frontend/package.json
frontend/package-lock.json
frontend/tsconfig.json
frontend/vite.config.ts
frontend/vitest.config.ts
frontend/index.html

frontend/src/main.tsx
frontend/src/App.tsx
frontend/src/routes.tsx
frontend/src/styles.css

frontend/src/api/client.ts
frontend/src/api/types.ts
frontend/src/api/demo.ts

frontend/src/components/Layout.tsx
frontend/src/components/Nav.tsx
frontend/src/components/ScreenPlaceholder.tsx
frontend/src/components/LoadingState.tsx
frontend/src/components/ErrorState.tsx

frontend/src/screens/HomeScreen.tsx
frontend/src/screens/AddPlantScreen.tsx
frontend/src/screens/SpeciesCandidateScreen.tsx
frontend/src/screens/PlantProfileSetupScreen.tsx
frontend/src/screens/PlantCreatedScreen.tsx
frontend/src/screens/PlantDetailScreen.tsx
frontend/src/screens/EnvironmentDetailScreen.tsx
frontend/src/screens/CareLogScreen.tsx
frontend/src/screens/ChatScreen.tsx
frontend/src/screens/GrowthHistoryScreen.tsx
frontend/src/screens/CompanionRecommendationScreen.tsx

frontend/src/test/setup.ts
frontend/src/__tests__/ui_shell.test.tsx
frontend/src/__tests__/api_client.test.ts
```

### 생성 가능한 문서

```text
docs/frontend_mvp_shell.md
```

### 조건부 수정 가능

```text
package.json
```

허용 범위:

```text
frontend dev/test script alias만 추가
backend/Docker/CI 관련 script 추가 금지
```

---

## 4. 금지 파일/디렉터리

아래 경로는 생성하거나 수정하지 않는다.

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
playwright.config.*
cypress.config.*
selenium.*
```

규칙:

```text
Ticket 27 must not modify backend product code, database schema, Docker topology, CI topology, native mobile app, or browser automation.
```

---

## 5. Frontend Stack 계약

허용 stack:

```text
Vite
React
TypeScript
Vitest
Testing Library
plain CSS or minimal CSS
```

금지 stack:

```text
React Native
Expo
Next.js server runtime
server-side rendering
Playwright
Cypress
Selenium
native push notification library
camera/timelapse library
offline sync framework
```

---

## 6. Required Screens 계약

아래 화면 component를 모두 만든다.

```text
Home
Add Plant
Species Candidate Selection
Plant Profile Setup
Plant Created
Plant Detail
Environment Detail
Care Log
Chat
Growth History
Companion Recommendation
```

각 screen은 최소한 아래를 포함해야 한다.

```text
visible title
short user-facing description
stable route
loading state
error state
navigation back to Home or main layout
backend API call hook 또는 명시적 placeholder
```

주의:

```text
Ticket 27은 skeleton이다.
각 screen의 깊은 UX와 complete interaction은 Ticket 28-32에서 구현한다.
```

---

## 7. Route 계약

필수 route:

```text
/                                      -> HomeScreen
/plants/add                            -> AddPlantScreen
/plants/species-candidates             -> SpeciesCandidateScreen
/plants/profile-setup                  -> PlantProfileSetupScreen
/plants/created                        -> PlantCreatedScreen
/plants/:plantId                       -> PlantDetailScreen
/plants/:plantId/environment           -> EnvironmentDetailScreen
/plants/:plantId/care-logs             -> CareLogScreen
/plants/:plantId/chat                  -> ChatScreen
/plants/:plantId/history               -> GrowthHistoryScreen
/plants/:plantId/companion-recommendations -> CompanionRecommendationScreen
```

---

## 8. API Client 계약

아래 파일을 생성한다.

```text
frontend/src/api/client.ts
```

필수 client shape:

```typescript
type ApiClientConfig = {
  baseUrl: string;
  userId: string;
};

class SunshineApiClient {
  getHome(): Promise<HomePlantCardResponse>;
  getPlantCard(plantId: string): Promise<HomePlantCardResponse>;
  getEnvironmentDetail(plantId: string): Promise<EnvironmentDetailResponse>;
  createCareLog(
    plantId: string,
    input: CareLogInput,
  ): Promise<CareLogFeedbackResponse>;
  askChat(plantId: string, input: ChatInput): Promise<ChatAnswerResponse>;
  getCompanionRecommendations(
    plantId: string,
  ): Promise<CompanionRecommendationResponse>;
  getGrowthHistory(plantId: string): Promise<GrowthHistoryResponse>;
}
```

필수 header:

```http
X-User-Id: demo-user-001
```

기본 config:

```text
baseUrl: import.meta.env.VITE_SUNSHINE_API_BASE_URL ?? "http://localhost:8000"
userId: import.meta.env.VITE_SUNSHINE_DEMO_USER_ID ?? "demo-user-001"
```

금지:

```text
OAuth token
JWT token
session cookie auth
external auth provider call
```

---

## 9. Type 계약

아래 파일을 생성한다.

```text
frontend/src/api/types.ts
```

Ticket 26 schema family를 mirror한다.

필수 type:

```text
SpeciesCandidateResponse
PlantCreatedResponse
HomePlantCardResponse
EnvironmentDetailResponse
CareLogFeedbackResponse
ChatAnswerResponse
CompanionRecommendationResponse
GrowthHistoryResponse
ErrorResponse
```

규칙:

```text
Ticket 26 response shape와 충돌하는 frontend-only shape를 만들지 않는다.
answer.sections는 결론/근거/행동/주의 key를 유지한다.
companion response에는 marketplace/purchase/affiliate field를 추가하지 않는다.
species candidate response에는 disease/pest diagnosis field를 추가하지 않는다.
```

---

## 10. Manual Demo Flow 계약

사용자가 수동으로 아래 흐름을 따라갈 수 있어야 한다.

```text
Home
  -> Add Plant
  -> Species Candidate Selection
  -> Plant Profile Setup
  -> Plant Created
  -> Plant Detail
  -> Environment Detail
  -> Care Log
  -> Chat
  -> Companion Recommendation
  -> Growth History
```

최소 demo behavior:

```text
demo user id 표시 또는 config
demo plant id default 제공
backend connectivity status 표시 가능
각 screen에서 MVP flow를 수동 검증할 수 있는 최소 content 렌더링
```

---

## 11. Runtime 계약

허용 runtime:

```text
local frontend dev server
  -> browser
  -> existing backend API calls
  -> backend remains unchanged
```

backend runtime은 변경하지 않는다.

```text
backend container
  -> uvicorn app.main:app
  -> /healthz
  -> existing MVP APIs
```

금지 runtime:

```text
frontend starts backend
frontend starts DB/Redis/MQTT/vLLM
frontend starts Nginx
frontend starts browser E2E runner
frontend bundles into backend container
```

---

## 12. Environment 계약

허용 frontend-only env:

```env
VITE_SUNSHINE_API_BASE_URL=http://localhost:8000
VITE_SUNSHINE_DEMO_USER_ID=demo-user-001
```

금지 env:

```text
OPENAI_*
ANTHROPIC_*
VLLM_*
JWT_*
OAUTH_*
PUSH_*
MARKETPLACE_*
SENTRY_*
ANALYTICS_*
```

Backend `.env.example`은 수정하지 않는다.

---

## 13. Health / Readiness 계약

Ticket 27은 backend health endpoint를 수정하지 않는다.

```http
GET /healthz
```

Ticket 27은 readiness endpoint를 추가하지 않는다.

```http
GET /readyz
```

규칙:

```text
frontend may call /healthz only as a non-blocking backend connectivity indicator.
frontend must not reinterpret /healthz as dependency readiness.
/healthz remains liveness-only.
/readyz remains out of scope.
```

---

## 14. Functional Gate

Antigravity는 아래 gate를 통과시켜야 한다.

```bash
set -euo pipefail

echo "[Gate 1] Frontend install"
cd frontend
npm ci

echo "[Gate 2] TypeScript"
npm run typecheck

echo "[Gate 3] Unit tests"
npm test -- --run

echo "[Gate 4] Build"
npm run build
cd ..

echo "[Gate 5] Required routes/screens"
python - <<'PY'
from pathlib import Path

required = [
    "frontend/src/screens/HomeScreen.tsx",
    "frontend/src/screens/AddPlantScreen.tsx",
    "frontend/src/screens/SpeciesCandidateScreen.tsx",
    "frontend/src/screens/PlantProfileSetupScreen.tsx",
    "frontend/src/screens/PlantCreatedScreen.tsx",
    "frontend/src/screens/PlantDetailScreen.tsx",
    "frontend/src/screens/EnvironmentDetailScreen.tsx",
    "frontend/src/screens/CareLogScreen.tsx",
    "frontend/src/screens/ChatScreen.tsx",
    "frontend/src/screens/GrowthHistoryScreen.tsx",
    "frontend/src/screens/CompanionRecommendationScreen.tsx",
]
for file in required:
    assert Path(file).exists(), file

routes = Path("frontend/src/routes.tsx").read_text()
for route in [
    "/",
    "/plants/add",
    "/plants/species-candidates",
    "/plants/profile-setup",
    "/plants/created",
    "/plants/:plantId",
    "/plants/:plantId/environment",
    "/plants/:plantId/care-logs",
    "/plants/:plantId/chat",
    "/plants/:plantId/history",
    "/plants/:plantId/companion-recommendations",
]:
    assert route in routes, route

print("routes_and_screens: pass")
PY

echo "[Gate 6] API client contract"
python - <<'PY'
from pathlib import Path

client = Path("frontend/src/api/client.ts").read_text()
types = Path("frontend/src/api/types.ts").read_text()

for method in [
    "getHome",
    "getPlantCard",
    "getEnvironmentDetail",
    "createCareLog",
    "askChat",
    "getCompanionRecommendations",
    "getGrowthHistory",
]:
    assert method in client, method

assert "X-User-Id" in client

for typ in [
    "SpeciesCandidateResponse",
    "PlantCreatedResponse",
    "HomePlantCardResponse",
    "EnvironmentDetailResponse",
    "CareLogFeedbackResponse",
    "ChatAnswerResponse",
    "CompanionRecommendationResponse",
    "GrowthHistoryResponse",
    "ErrorResponse",
]:
    assert typ in types, typ

print("api_client_contract: pass")
PY

echo "[Gate 7] No backend or later frontend leakage"
python - <<'PY'
from pathlib import Path

for forbidden in [
    "app",
    "alembic",
    "migrations",
    "mobile",
    "ios",
    "android",
]:
    assert not Path(forbidden).exists() or forbidden == "app", forbidden

for path in Path("frontend").rglob("*"):
    if not path.is_file():
        continue
    if path.suffix not in {".ts", ".tsx", ".js", ".jsx", ".json", ".css", ".html", ".md"}:
        continue
    text = path.read_text(errors="ignore")
    forbidden_tokens = [
        "React Native",
        "expo",
        "push notification",
        "timelapse",
        "navigator.mediaDevices",
        "playwright",
        "cypress",
        "selenium",
        "openai",
        "anthropic",
        "vllm",
        "marketplace",
        "purchase_url",
        "affiliate",
        "OAuth",
        "JWT",
    ]
    hits = [token for token in forbidden_tokens if token in text]
    assert not hits, f"{path}: {hits}"

print("no_later_feature_leakage: pass")
PY
```

---

## 15. Tests

추가할 테스트:

```text
test_layout_renders_navigation
test_all_required_routes_are_registered
test_home_screen_renders_title_and_demo_state
test_add_plant_screen_renders_title
test_species_candidate_screen_renders_title
test_plant_profile_setup_screen_renders_title
test_plant_created_screen_renders_title
test_plant_detail_screen_renders_title
test_environment_detail_screen_renders_title
test_care_log_screen_renders_title
test_chat_screen_renders_title
test_growth_history_screen_renders_title
test_companion_recommendation_screen_renders_title
test_api_client_uses_base_url
test_api_client_sends_x_user_id_header
test_api_types_include_ticket26_response_families
test_backend_unavailable_shows_error_state
test_no_push_or_timelapse_ui_present
test_no_readyz_semantics_in_frontend
```

---

## 16. Acceptance Criteria

Ticket 27은 아래를 만족해야 완료다.

```text
frontend shell exists
all required MVP screen components exist
all required routes exist
manual demo navigation is possible
shared API client exists
API client sends X-User-Id header
API client defaults to demo-user-001
Ticket 26 response types are mirrored
loading state exists
error state exists
backend unavailable state is handled
frontend unit tests pass
frontend build passes
no backend product code modified
no Docker/compose change introduced
no React Native/native mobile code added
no push notification implemented
no timelapse implemented
no browser automation added
no OAuth/JWT/login UI added
no marketplace/purchase links added
/healthz remains unchanged
/readyz is not introduced
```

---

## 17. Do not implement

```text
Ticket 28 onboarding depth
Ticket 29 home/detail depth
Ticket 30 care log UX depth
Ticket 31 chat answer UX depth
Ticket 32 growth history depth
production mobile polish
React Native native app
push notification
timelapse
camera capture
offline sync
auth login UI
OAuth/JWT flow
billing UI
admin dashboard
browser E2E automation
new backend endpoints
backend schema changes
LLM provider changes
streaming chat UI
marketplace purchase links
```
