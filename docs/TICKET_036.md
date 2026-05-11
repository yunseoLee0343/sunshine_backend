/clear
# TICKET-036 Implement: UI Shell & Baseline (Frontend)

다음 가이드라인에 따라 Sunshine 프론트엔드 MVP의 기초 뼈대를 구현해줘. 전체 문서를 읽지 말고 이 요약에만 집중해.

### 1. 목표 및 환경 설정
- **기술 스택**: Vite + React + TypeScript + Tailwind CSS (또는 기본 CSS).
- **목표**: 모든 MVP 화면을 이동할 수 있는 라우팅 구조와 백엔드 통신을 위한 공통 API 클라이언트 구축.
- **핵심 정책**: 모든 API 요청은 헤더에 `X-User-Id: demo-user-001`을 기본으로 포함해야 함.

### 2. 라우팅 및 화면 스켈레톤 (Routes)
다음 경로에 대한 빈 페이지(스켈레톤)와 네비게이션을 구현해:
- `/`: 홈 화면 (T-038)
- `/onboarding`: 식물 등록 flow (T-037)
- `/plants/:plantId`: 식물 상세 (T-038)
- `/plants/:plantId/care`: 관리 기록 (T-039)
- `/plants/:plantId/chat`: 지능형 채팅 (T-040)
- `/plants/:plantId/history`: 성장 이력 (T-041)

### 3. 필수 구현 대상
- **Shared API Client**: `axios` 또는 `fetch`를 사용하여 `X-User-Id`를 주입하는 공통 모듈.
- **Response Types**: Ticket 26에서 정의된 백엔드 응답 스키마(PlantCard, ChatAnswer 등)를 TypeScript 인터페이스로 선언.
- **Common Components**: 전역 로딩(Loading), 에러 처리(Error Boundary), 기본 레이아웃(Shell).

### 4. 제약 사항 (절대 금지)
- **백엔드 수정 금지**: 백엔드 API나 Docker 설정을 절대 건드리지 마.
- **디테일 UX 금지**: 각 화면의 내부 기능(채팅 로직, 온보딩 단계 등)은 다음 티켓의 범위이므로 지금은 빈 화면만 만들어.
- **인증 UI 금지**: 실제 로그인 화면이나 JWT 처리 로직을 만들지 마. 오직 헤더 하드코딩만 허용.
- **Native/Push 금지**: 리액트 네이티브나 푸시 알림, 타임랩스 기능을 넣지 마.

지금 바로 `src/api/client.ts`와 `src/App.tsx`(라우터 설정) 작성을 시작해줘.