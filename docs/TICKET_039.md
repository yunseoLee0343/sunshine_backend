/clear
# TICKET-039 Implement: Frontend Care Log + Feedback

다음 가이드라인에 따라 관리 기록 및 피드백 UI를 구현해줘. 전체 문서를 읽지 말고 이 요약에만 집중해.

### 1. 목표 및 핵심 로직
- **목표**: 물주기 버튼, 노트 입력 폼을 통해 관리 기록을 생성하고 최근 이력을 목록으로 표시.
- **핵심 API 연동**:
  - `POST /plants/{plant_id}/care-logs`: 물주기(`action=watering`) 또는 노트(`action=note`) 기록 생성.
  - `GET /plants/{plant_id}/care-logs`: 최근 관리 이력(최신순) 리스트 수신.

### 2. 주요 UI 컴포넌트 및 흐름
1. **CareActionButtons**: 
   - '물 주었어요' 버튼 클릭 시 즉시 API 호출 및 성공 피드백 표시.
2. **CareNoteForm**: 
   - 텍스트 입력 후 '기록하기' 버튼 클릭. 빈 텍스트는 전송 방지 처리.
3. **CareFeedbackCard**: 
   - API 성공 응답에 포함된 캐릭터의 새로운 기분(`mood`)과 감사 메시지(`message`)를 팝업이나 상단 배너로 노출.
4. **RecentCareLogs**: 
   - 타임라인 형태로 최근 기록된 이력들(유형, 시간, 내용)을 리스트업.

### 3. 필수 구현 대상
- **Optimistic UI (선택)** 또는 **Refetch**: 기록 성공 후 자동으로 이력 리스트가 새로고침되도록 처리.
- **Feedback Logic**: 백엔드 응답 데이터(`character_feedback`)가 있을 때만 피드백 카드 렌더링.
- **Shared API Client**: 기존에 설정된 `X-User-Id` 헤더를 사용하여 요청 수행.

### 4. 제약 사항 (절대 금지)
- **로직 계산 금지**: "지금 물을 줘야 하는가?"를 프론트엔드에서 판단하지 마. (백엔드 룰 엔진 영역)
- **알림/푸시 금지**: 리마인더 알림이나 푸시 메시지 로직을 구현하지 마.
- **채팅/추천 UI 금지**: 채팅 화면이나 동반 식물 추천 로직을 여기서 만들지 마.
- **백엔드 수정 금지**: 기존 API 응답 구조를 변경하지 마.

지금 바로 `src/pages/CareLog/` 경로에 관련 컴포넌트 작성을 시작해줘.