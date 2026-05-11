/clear
# TICKET-038 Implement: Frontend Home + Plant Detail

다음 가이드라인에 따라 홈 및 식물 상세 UI를 구현해줘. 전체 문서를 읽지 말고 이 요약에만 집중해.

### 1. 목표 및 핵심 로직
- **목표**: 사용자의 식물 리스트(Home)와 특정 식물의 상세 상태(Detail/Environment) 시각화.
- **데이터 소스**: 
  - `GET /plants`: 등록된 식물들의 요약 카드 리스트.
  - `GET /plants/{plant_id}`: 특정 식물의 캐릭터 상태 및 오늘의 할 일(`today_action`).
  - `GET /plants/{plant_id}/environment`: 최신 센서 값 및 24시간/7일 요약 정보.

### 2. 주요 화면 및 컴포넌트
1. **HomeScreen**: 
   - `HomePlantCard`: 식물 별명, 캐릭터 이미지(기분 반영), 환경 요약 배지.
   - `TodayAction`: "물 줄 시간이에요!" 등 룰 엔진의 결과를 강조 표시.
2. **PlantDetailScreen**: 
   - 식물 전체 개요 및 관리(Care), 채팅(Chat), 이력(History) 메뉴로의 네비게이션 링크.
3. **EnvironmentDetailScreen**: 
   - `SensorValueGrid`: 온도, 습도, 조도 등 현재 수치를 그리드로 표시.
   - `CharacterExplanation`: 환경에 대해 캐릭터가 해주는 설명 텍스트 표시.

### 3. 필수 구현 대상
- **Character Renderer**: 백엔드에서 온 `mood`(Happy, Thirsty 등)에 따라 적절한 아이콘이나 이미지를 매칭하는 로직.
- **Summary Panels**: 24시간 및 7일간의 환경 변화를 텍스트나 간단한 지표로 요약하여 표시.
- **API Integration**: 홈 화면 진입 시 식물 목록을 페칭하고 `X-User-Id`를 포함하여 요청.

### 4. 제약 사항 (절대 금지)
- **추가 UI 금지**: 관리 기록(Care Log), 채팅(Chat), 성장 이력(History), 동반 식물 UI는 여기서 만들지 마.
- **로직 계산 금지**: "상태가 좋다/나쁘다"를 프론트엔드에서 계산하지 마. 오직 백엔드 결과만 출력.
- **그래프 금지**: 이번 티켓에서는 복잡한 차트나 그래프, 타임랩스 기능을 넣지 마. (텍스트/수치 중심)
- **백엔드 수정 금지**: 기존 API 응답 구조를 변경하지 마.

지금 바로 `src/pages/Home/`과 `src/pages/PlantDetail/` 작성을 시작해줘.