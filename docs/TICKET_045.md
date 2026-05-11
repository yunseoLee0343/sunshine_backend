/clear
# TICKET-CLEANUP: Document Mock Technical Debt

다음 가이드라인에 따라 프로젝트 내의 모든 Mock 구현체를 식별하고 `docs/MOCK_TECHNICAL_DEBT.md` 파일을 생성해줘.

### 1. 목표
- 현재 MVP의 안정성을 위해 도입된 '가짜(Mock)' 로직을 전수 조사하여 문서화.
- 향후 상용화 단계에서 '진짜(Real)'로 교체해야 할 타겟 서비스를 명시.

### 2. 문서 포함 내용 (Table 형식)
다음 카테고리별로 [티켓 ID / Mock 항목 / 현재 로직 / 교체 대상(Real)]을 정리해:
- **AI/ML**: LLM 응답(T-018/32), 비전 분석(T-030), 음성 변환(T-031), 식물 종 판별(T-003).
- **Security**: X-User-Id 헤더 인증(T-025).
- **Data/IoT**: 가짜 센서 데이터 생성(T-005/6), 로컬 벡터 검색(T-014).
- **Storage**: 이미지 파일 Mock URI 처리.

### 3. 상세 설명 (Appendix)
- **교체 우선순위**: 유저 경험에 가장 큰 영향을 주는 항목부터 순서대로 나열.
- **연결 방식 제안**: 실제 API(OpenAI, AWS, Google 등) 도입 시 고려해야 할 인터페이스 구조 간략히 기술.

### 4. 제약 사항
- **코드 수정 금지**: 기존 `.py`나 `.tsx` 파일의 로직을 절대 변경하지 마. 오직 문서(`md`) 생성에만 집중해.
- **현실적 대안**: 단순히 "진짜로 바꿈"이 아니라 "OpenAI GPT-4o API로 교체"와 같이 구체적인 서비스명을 언급해.

지금 바로 `docs/MOCK_TECHNICAL_DEBT.md` 작성을 시작해줘.