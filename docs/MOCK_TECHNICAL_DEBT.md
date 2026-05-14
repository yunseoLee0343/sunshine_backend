# Mock Technical Debt Register

> **목적** — MVP 안정성을 위해 도입된 모든 가짜(Mock) 구현체를 전수 조사하여,
> 상용화 단계에서 교체해야 할 대상과 방법을 명시한다.
>
> **최종 업데이트** — 2026-05-11
> **범위** — `app/llm/`, `app/services/`, `app/embedding/`, `app/core/auth.py`

---

## 1. AI / ML

| 티켓 | Mock 항목 | 현재 로직 | 교체 대상 (Real) |
|------|-----------|-----------|------------------|
| T-018 | **LLM 응답 생성** | ~~`app/llm/mock_client.py` — 프롬프트 해시 기반으로 고정된 4-섹션(결론/근거/행동/주의) 한국어 답변 반환. 외부 네트워크·API 키 불필요.~~ **✅ TICKET-049에서 교체됨** — `app/llm/qwen_client.py` (`QwenLLMClient`, vLLM OpenAI-호환 엔드포인트). `LLM_BACKEND=qwen` 설정 시 Qwen3.6 실 모델 호출. `MockLLMClient`는 테스트 전용으로 유지. | 추가 개선: **Anthropic Claude API** (`claude-opus-4-7` 또는 `claude-sonnet-4-6`)로 전환 가능. `LLMPort.complete()` 인터페이스 그대로 유지. |
| T-032 | **LLM 자기치유(Self-Healing)** | `app/llm/mock_healing_client.py` — 첫 번째 호출 시 고의로 섹션 마커 없는 기형 응답을 반환해 재시도 파이프라인을 테스트. 실제 재생성 로직 없음. | Anthropic Claude API 동일 모델. 자기치유 오케스트레이터(`self_healing_orchestrator.py`)는 이미 구현돼 있으므로 `MockHealingLLMClient` → `AnthropicLLMClient`로 주입만 교체. |
| T-030 | **비전 분석(Vision Analysis)** | `app/llm/mock_vision_client.py` — 이미지 URI 경로 키워드(pest/yellow/wilt/spot/healthy)를 기반으로 고정된 한국어 시각 증상 반환. 실제 이미지 디코딩 없음. | **Anthropic Claude Vision API** (`claude-sonnet-4-6`). `VisionPort.analyze()` 구현체에서 `base64` 인코딩 이미지를 `image` 블록으로 전송. |
| T-031 | **음성 변환 STT / TTS** | `app/llm/mock_audio_client.py` — STT: URI 키워드 매핑 → 6개 고정 한국어 녹취록. TTS: 텍스트 해시 기반 가짜 오디오 URI 생성, 실제 음성 파일 없음. | **STT** — Google Cloud Speech-to-Text v2 (`chirp` 모델, `ko-KR`). **TTS** — Google Cloud Text-to-Speech (`ko-KR-Neural2-C` 보이스). `AudioPort` 인터페이스 그대로 유지. |
| T-003 | **식물 종 판별(Species Classification)** | `app/vision/mock_species_classifier.py` — `image_ref` 문자열 서브스트링 매핑으로 몬스테라 / 스킨답서스 / 필로덴드론 3종만 인식. | **Plant.id API v3** (식물 특화 비전 모델). 대안: **Google Cloud Vision AutoML** 또는 **iNaturalist API**. `SpeciesClassifierPort` 인터페이스 그대로 유지. |
| T-034 | **의도 분류기 Stage 2** | `app/llm/intent_classifier_mock.py` — Stage 1 정규식이 실패할 때 동작하는 확장 정규식 기반 분류기. 매치 시 confidence 0.70, 폴백 시 0.50 고정 반환. | **LLM 기반 few-shot 분류기** (Claude API, 시스템 프롬프트에 인텐트 정의 + 예시 삽입). 또는 **OpenAI GPT-4o mini** (비용 절감형). |

---

## 2. Security

| 티켓 | Mock 항목 | 현재 로직 | 교체 대상 (Real) |
|------|-----------|-----------|------------------|
| T-025 | **사용자 인증** | `app/core/auth.py` — `X-User-Id` 헤더 또는 `?user_id=` 쿼리 파라미터로 UUID를 직접 수신. JWT 검증·세션·비밀번호 없음. 데모 UUID(`7923c9bd-…`) 하드코딩. | **Auth0** 또는 **AWS Cognito** 기반 JWT Bearer 토큰. `get_current_user` 의존성 함수를 `python-jose` + JWKS 엔드포인트 검증 방식으로 교체. 프론트엔드 Axios 인터셉터에 `Authorization: Bearer <token>` 추가 필요. |

---

## 3. Data / IoT

| 티켓 | Mock 항목 | 현재 로직 | 교체 대상 (Real) |
|------|-----------|-----------|------------------|
| T-005/6 | **센서 데이터** | 실제 IoT 기기 없이 REST `POST /sensor-readings` 또는 MQTT 수동 페이로드로 토양수분·조도·온습도·기온 값을 주입. `demo_scenario.py`의 seed 스크립트가 고정 값으로 데이터베이스를 채움. | **AWS IoT Core** + 실제 센서 모듈(예: SHT31 온습도, BH1750 조도, Capacitive Soil Moisture v2.0). IoT 기기 → MQTT 브로커 → `mqtt_sensor_ingest_service.py` 파이프라인은 이미 구현돼 있으므로 기기 연결만 추가하면 됨. |
| T-014 | **로컬 벡터 임베딩** | `app/embedding/local_embedding_service.py` — `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` 모델을 서버 메모리에 로드해 추론. 모델 크기 약 480 MB, 콜드스타트 지연 있음. | **OpenAI `text-embedding-3-small` API** (1536-dim, 비용 효율적) 또는 **Anthropic `voyage-multilingual-2`**. `LocalEmbeddingService` 를 `dim` 프로퍼티와 `embed()` 메서드를 유지하는 `RemoteEmbeddingService`로 교체. pgvector 인덱스를 새 차원에 맞게 재생성 필요. |

---

## 4. Storage

| 티켓 | Mock 항목 | 현재 로직 | 교체 대상 (Real) |
|------|-----------|-----------|------------------|
| T-030 | **이미지 파일 URI 처리** | `image_ref`를 불투명(opaque) 문자열로만 취급. 실제 파일 I/O·디코딩 없음. 테스트·시드 데이터는 `test://mock-image/monstera` 형식의 가짜 URI 사용. 업로드 플로우 없음. | **AWS S3 Presigned URL** (업로드 시 `PUT`, 분석 시 `GET`) 또는 **Firebase Storage**. 온보딩 플로우에서 클라이언트가 S3에 직접 업로드 후 `image_ref`에 S3 key 저장. 비전 분석 시 key로 원본 이미지를 다운로드해 base64 인코딩 후 Vision API 전달. |

---

## Appendix A — 교체 우선순위

유저 경험(UX)과 서비스 신뢰도에 미치는 영향 순으로 정렬.

| 순위 | 항목 | 이유 |
|------|------|------|
| **1** | **LLM 응답 생성 (T-018)** | 핵심 가치 제안. 현재 모든 답변이 동일해 사용자가 즉시 Mock임을 인지함. Claude API 연동만으로 서비스 차별화 달성. |
| **2** | **사용자 인증 (T-025)** | 보안 취약점. `X-User-Id`를 클라이언트에서 임의 변조 가능 → 타 사용자 데이터 접근 가능. 실 서비스 배포 전 반드시 교체. |
| **3** | **식물 종 판별 (T-003)** | 온보딩 경험 직결. 3종만 인식하는 Mock은 실제 사용자 식물의 95%를 "Unknown"으로 반환. Plant.id API 교체 시 12만+ 종 인식 가능. |
| **4** | **로컬 벡터 임베딩 (T-014)** | 서버 리소스 문제. 480 MB 모델 메모리 상주로 저사양 서버에서 OOM 위험. 클라우드 임베딩 API 전환 시 인프라 비용 절감. |
| **5** | **비전 분석 (T-030) + 이미지 URI (Storage)** | 함께 교체해야 의미 있음. 실제 이미지 분석 없이는 비전 API 단독 교체 효과 없음. S3 업로드 파이프라인과 동시 구현 권장. |
| **6** | **음성 변환 STT / TTS (T-031)** | 현재 UI에 음성 입력 미구현. 프론트엔드 Voice UI 추가와 병행할 때 교체 의미 있음. |
| **7** | **의도 분류기 Stage 2 (T-034)** | Stage 1 정규식이 대부분 커버. LLM 분류기 교체 전 Stage 1 패턴 보강으로 단기 품질 개선 가능. |
| **8** | **LLM 자기치유 (T-032)** | T-018 교체 후 자동 해결. 실제 LLM 응답이 파싱 실패하면 자기치유 오케스트레이터가 재시도 → 별도 Mock 불필요. |
| **9** | **센서 데이터 (T-005/6)** | 하드웨어 의존. IoT 기기 조달·펌웨어 개발 리드타임이 가장 길므로 우선순위는 낮지만 착수 시점은 빨라야 함. |

---

## Appendix B — 인터페이스 교체 가이드

### B-1. LLM (T-018 / T-032)

```
현재: MockLLMClient  →  LLMPort  ←  chat_orchestrator
교체: AnthropicLLMClient implements LLMPort
```

- `LLMPort.complete(request: LLMRequest) -> LLMResponse` 시그니처 유지.
- `anthropic.AsyncAnthropic().messages.create()` 호출, `content[0].text` → `LLMResponse.content` 매핑.
- `stream=True` 지원 추가 시 `LLMResponse.stream_chunks: AsyncIterator[str]` 필드 확장 필요.
- 환경변수 `ANTHROPIC_API_KEY` 주입 (기존 `.env` + `pydantic-settings`).

### B-2. Vision Analysis (T-030)

```
현재: MockVisionClient  →  VisionPort  ←  vision 서비스 레이어
교체: AnthropicVisionClient implements VisionPort
```

- `VisionPort.analyze(image_uri, locale)` 유지.
- S3 key → `boto3.get_object()` → base64 인코딩 → `{"type":"image","source":{"type":"base64","media_type":"image/jpeg","data":"..."}}` 블록 포함한 메시지 전송.
- `VisionAnalysisResult.suggests_pest` 필드는 Claude 응답 텍스트에서 키워드 추출로 채움.

### B-3. Audio STT / TTS (T-031)

```
현재: MockAudioClient  →  AudioPort  ←  audio 서비스 레이어
교체: GoogleAudioClient implements AudioPort
```

- STT: `google.cloud.speech_v2.SpeechClient().recognize()`, 결과 첫 번째 `alternative.transcript` → `SttResult.transcript`.
- TTS: `google.cloud.texttospeech.TextToSpeechClient().synthesize_speech()`, 결과 `audio_content` → S3 업로드 → `AudioMetadata.audio_uri` = S3 key.
- 언어 코드 `ko-KR` 그대로 사용 가능.

### B-4. Species Classification (T-003)

```
현재: MockSpeciesClassifier  →  SpeciesClassifierPort  ←  SpeciesCandidateService
교체: PlantIdSpeciesClassifier implements SpeciesClassifierPort
```

- `SpeciesClassifierPort.classify_species(image_ref, locale, top_k)` 유지.
- Plant.id API v3: `POST https://api.plant.id/v3/identification`, 바디에 `{"images": ["data:image/jpeg;base64,..."], "similar_images": false}`.
- 응답 `result.classification.suggestions[].name` → `SpeciesCandidate.scientific_name`, `probability` → `confidence`.

### B-5. Authentication (T-025)

```
현재: get_current_user (X-User-Id 헤더 파싱)
교체: JWT Bearer 검증
```

- `fastapi.security.HTTPBearer` 의존성으로 `Authorization` 헤더 추출.
- `python-jose[cryptography]`로 JWKS 엔드포인트 검증 (`jwks_uri` = Auth0 또는 Cognito 발급).
- `resolve_user_id()` 시그니처 유지, `CurrentUser.user_id` 소스만 JWT `sub` 클레임으로 변경.
- 프론트엔드: `src/api/client.ts`의 `X-User-Id` 헤더 → `Authorization: Bearer ${token}` 인터셉터로 교체.

### B-6. Embeddings (T-014)

```
현재: LocalEmbeddingService (sentence-transformers, 384-dim)
교체: RemoteEmbeddingService (OpenAI text-embedding-3-small, 1536-dim)
```

- `embed(text: str) -> list[float]` 및 `embed_batch(...)` 시그니처 유지.
- `openai.AsyncOpenAI().embeddings.create(model="text-embedding-3-small", input=texts)` 호출.
- **주의**: 차원 변경(384 → 1536)으로 인해 `plant_chunk_embeddings` 테이블의 `embedding vector(384)` 컬럼을 `vector(1536)`으로 재생성하는 Alembic 마이그레이션 및 전체 재임베딩 작업 필요.
