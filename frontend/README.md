# 🌿 Sunshine Frontend

Sunshine 식물 케어 앱의 프론트엔드. React SPA로 백엔드 FastAPI와 통신한다.

---

## 🛠 Tech Stack

| 항목 | 버전 |
|------|------|
| Vite | 8.x |
| React | 19.x |
| TypeScript | 6.x |
| React Router | v7 |
| Axios | 1.x |
| CSS Modules | (스타일링) |

> **.env 파일 불필요.** 백엔드 주소는 `vite.config.ts`의 프록시에 하드코딩돼 있다.
> `/api/v1/*` → `http://localhost:8000` 으로 자동 포워딩.

---

## ⚡ Setup & Run

```bash
# 1. 의존성 설치
npm install

# 2. 개발 서버 실행
npm run dev
# → http://localhost:5173
```

백엔드가 `localhost:8000`에서 실행 중이어야 API가 정상 동작한다.
백엔드 실행 방법은 [`docs/RUN_GUIDE.md`](../docs/RUN_GUIDE.md) 참고.

### 기타 명령어

```bash
npm run build   # 프로덕션 빌드 (dist/)
npm run lint    # ESLint 검사
npm run preview # 빌드 결과물 로컬 미리보기
```

---

## 📁 폴더 구조

```
src/
├── api/
│   ├── client.ts          # Axios 인스턴스 + X-User-Id 헤더 + 401/403 인터셉터
│   ├── types.ts           # 전체 API 응답 타입 정의 (백엔드 스키마 1:1 매핑)
│   ├── onboarding.ts      # 식물 등록 (이미지 업로드, 종 후보 조회, 식물 생성)
│   ├── home.ts            # 홈 카드 목록 조회
│   ├── careLogs.ts        # 케어 로그 목록 조회 / 물주기·메모 기록
│   ├── chat.ts            # 채팅 질문 전송 / 답변 수신
│   ├── history.ts         # 성장 이력 타임라인 조회
│   └── companion.ts       # 동반 식물 추천 조회
│
├── components/
│   ├── Shell.tsx          # 전역 헤더 + 하단 탭 네비게이션 (Shell / PlantShell)
│   ├── Loading.tsx        # 전역 로딩 스피너
│   └── ErrorBoundary.tsx  # React 오류 경계 (예외 캐치 + 폴백 UI)
│
├── pages/
│   ├── Home/              # 등록 식물 카드 목록 (T-038)
│   ├── Onboarding/        # 4단계 식물 등록 플로우 (T-037)
│   │   ├── Step1ImagePicker.tsx   # 이미지 선택
│   │   ├── Step2Candidates.tsx    # 종 후보 선택
│   │   ├── Step3Profile.tsx       # 닉네임·방 이름 입력
│   │   └── Step4Success.tsx       # 등록 완료
│   ├── PlantDetail/       # 환경 지표 + 캐릭터 상태 (T-038)
│   ├── CareLog/           # 물주기·메모 기록 + 최근 이력 (T-039)
│   ├── Chat/              # 질문 입력 + 4-섹션 답변 + 동반 식물 카드 (T-040)
│   └── GrowthHistory/     # 케어·환경·캐릭터 통합 타임라인 (T-041)
│
└── App.tsx                # 라우트 정의
```

### 라우트 맵

| URL | 페이지 | 설명 |
|-----|--------|------|
| `/` | Home | 식물 카드 목록 |
| `/onboarding` | Onboarding | 식물 등록 |
| `/plants/:plantId` | PlantDetail | 환경 + 캐릭터 |
| `/plants/:plantId/care` | PlantCare | 케어 로그 |
| `/plants/:plantId/chat` | PlantChat | 채팅 Q&A |
| `/plants/:plantId/history` | PlantHistory | 성장 이력 |

---

## ✅ 주요 기능 확인 가이드

### 🔑 Authentication

`src/api/client.ts` 에 데모 유저 UUID가 하드코딩돼 있다.
별도 로그인 없이 모든 요청에 자동 주입된다.

```ts
// src/api/client.ts
const DEMO_USER_ID = '7923c9bd-80d8-d2d1-1937-b9e0e7e28887'

const client = axios.create({
  baseURL: '/api/v1',
  headers: { 'X-User-Id': DEMO_USER_ID },
})
```

| 상태코드 | 인터셉터 동작 |
|----------|-------------|
| 401 | `window.location.replace('/')` — 홈으로 리다이렉트 |
| 403 | `Promise.reject(new Error('이 식물에 접근할 권한이 없어요.'))` |

---

### 💬 Chat UI

`/plants/:plantId/chat` 경로에서 확인.

- 질문 입력 → `POST /chat/{plantId}` 호출
- 응답의 `answer` 객체를 4-섹션으로 렌더링:

```
┌─────────────────────────────┐
│ [결론] 결론 텍스트           │
├─────────────────────────────┤
│ [근거] 근거 텍스트           │
├─────────────────────────────┤
│ [행동] 행동 텍스트           │
├─────────────────────────────┤
│ [주의] 주의 텍스트           │
└─────────────────────────────┘
```

- `intent === 'companion_plant_question'` 일 때 답변 하단에 동반 식물 인라인 카드 자동 렌더링 (`CompanionInlineCard`)
- `is_reference_only === true` 일 때 병충해 경고 배너 (`PestCautionBanner`) 표시

---

### 📅 Growth History

`/plants/:plantId/history` 경로에서 확인.

- `GET /plants/:plantId/history` 호출 → 케어 로그·환경 요약·캐릭터 변화 통합 타임라인 표시
- 상단 필터 탭으로 `전체 / 케어 / 환경 / 캐릭터` 전환 가능

---

## 🚦 릴리즈 게이트

배포 전 아래 스크립트로 최종 검수를 통과해야 한다.

```bash
# 프로젝트 루트에서 실행
bash scripts/frontend_release_gate.sh
```

내부 검사 순서:

1. `tsc --noEmit` — TypeScript 타입 오류
2. `eslint .` — 린트 오류
3. `vite build` — 프로덕션 빌드
4. API smoke test — `/healthz`, `/readyz`, `/home` 응답 확인 (백엔드 필요)

> `SKIP_SMOKE=1 bash scripts/frontend_release_gate.sh` 으로 백엔드 없이 lint+build만 실행 가능.

---

## ⚠️ 현재 제약 사항

| 항목 | 상태 | 비고 |
|------|------|------|
| LLM 답변 | Mock | 동일 질문 → 항상 동일 답변 |
| 식물 종 판별 | Mock | 3종(몬스테라·포토스·필로덴드론)만 인식 |
| 이미지 업로드 | Mock URI | 실제 파일 저장 없음 |
| 음성 입력 | 미구현 | UI 없음 |
| 인증 | X-User-Id 헤더 | JWT 없음 |

교체 우선순위 및 실제 API 연동 방법 → [`docs/MOCK_TECHNICAL_DEBT.md`](../docs/MOCK_TECHNICAL_DEBT.md)
