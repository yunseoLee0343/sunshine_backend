/clear
# TICKET-FINAL: MVP Gap Bridge & Readiness Cleanup

감사 보고서에서 식별된 5가지 Critical Gap을 해결하고 MVP를 100% 완성해줘.

### 1. 목표 및 핵심 작업 (Severity 1 & 2 해결)
- **Git Commit (T-031, 032, 034)**: 로컬에만 존재하는 오디오, 자가치유, 평가 시스템 코드를 검토하고 커밋 가능한 상태로 스테이징.
- **History API 구현 (T-041)**: `GET /plants/{plant_id}/history` 엔드포인트를 신설하여 `care_logs`, `environment_snapshots`, `character_mood_history`를 통합 정렬하여 반환.
- **Companion UI 연결 (T-040)**: 백엔드 T-021 API를 호출하여 채팅 답변 내에 '동반 식물 추천' 인라인 카드를 렌더링.
- **Auth Error Handling (T-025)**: 프론트엔드에서 401/403 에러 발생 시 사용자에게 알림을 주거나 홈으로 리다이렉트하는 가드레일 추가.

### 2. 필수 구현 상세
- **BE /history**: SQLAlchemy의 `union_all` 등을 활용해 서로 다른 3개 테이블의 이력을 `timestamp` 기준으로 합쳐서 반환할 것.
- **FE Companion UI**: `ChatAnswer` 객체에 추천 데이터가 있을 경우, T-040에서 누락된 인라인 카드 컴포넌트를 활성화.
- **Git Cleanup**: `git status` 상의 untracked 파일들을 기능별(Audio, Healing, Eval)로 분류하여 커밋 메시지 작성.

### 3. 제약 사항 (절대 금지)
- **신규 기능 추가 금지**: 보고서에 명시된 Gap 외에 새로운 기능을 절대 추가하지 마.
- **스키마 임의 변경 금지**: 기존에 잘 작동하는 온보딩이나 모니터링 DB 구조를 건드리지 마.
- **Mock 탈피 금지**: 여전히 실제 LLM이나 실제 카메라 API는 연결하지 마. (Mock 유지)

### 4. 수동 검증 (Smoke Test)
- `/history` 호출 시 타임라인의 '환경'과 '상태' 탭이 더 이상 비어있지 않은가?
- 102개 파일이 모두 커밋되어 `git status`가 깨끗한가?
- 동반 식물 질문 시 UI에 카드 형태로 추천 식물이 나타나는가?

지금 바로 `app/api/history.py` 구현과 미커밋 파일 정리를 시작해줘.