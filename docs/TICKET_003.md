# TICKET-003 — Species Candidate Mock / VisionPort Boundary

## 0. 목표

Sunshine 백엔드에 식물 종 후보 추천 경계를 구현한다.

이 티켓은 실제 vision inference를 구현하지 않는다.  
목표는 나중에 실제 classifier로 교체 가능한 `SpeciesClassifierPort`를 만들고, 현재는 deterministic mock classifier로 `POST /plants/species-candidates`를 동작시키는 것이다.

`image_ref`는 opaque string이다.  
파일을 열거나, 이미지를 디코딩하거나, 모델을 로딩하지 않는다.

---

## 1. 핵심 요구사항

### Ticket ID

```text
TICKET-003
````

### Name

```text
Species Candidate Mock / VisionPort Boundary
```

### Goal

```text
Provide plant species candidate results behind a replaceable classifier port without introducing real vision inference.
```

### Core output

```text
SpeciesClassifierPort
MockSpeciesClassifier
SpeciesCandidateService
POST /plants/species-candidates
unknown fallback candidate: "잘 모르겠어요"
no model dependency
no disease/pest/health fields
```

---

## 2. 주변 티켓과의 경계

Ticket 3은 Ticket 2의 `POST /plants/species-candidates`를 classifier port 뒤로 옮기는 티켓이다.

```text
Ticket 2:
  POST /plants/species-candidates
  DB/catalog lookup 중심

Ticket 3:
  POST /plants/species-candidates
    -> SpeciesCandidateService
    -> SpeciesClassifierPort
    -> MockSpeciesClassifier
    -> optional species_profiles lookup
```

Ticket 3에서 허용:

```text
species candidate 생성
mock species classifier
species_profile_id optional resolution
unknown fallback candidate
```

Ticket 3에서 금지:

```text
real image inference
image bytes parsing
image file open
image URL fetch
model loading
model download
disease classifier
pest classifier
health classifier
plant creation
character state creation
sensor ingestion
LLM/RAG
worker/Redis/MQTT
```

---

## 3. 수정/생성 허용 파일

### 수정 가능한 기존 파일

```text
app/api/plants.py
app/schemas/plants.py
app/services/plant_onboarding.py
app/repositories/species_repository.py
app/main.py
pyproject.toml
.github/workflows/ci.yml
```

### 생성 가능한 새 파일

```text
app/vision/__init__.py
app/vision/species_classifier.py
app/vision/mock_species_classifier.py
app/services/species_candidate_service.py
tests/test_species_classifier_contract.py
tests/test_mock_species_classifier.py
tests/test_species_candidates_api.py
tests/test_ticket3_boundary.py
```

### 조건부 허용 파일

기존 Ticket 2 schema가 너무 강하게 결합되어 있을 때만 생성 가능하다.

```text
app/schemas/species_candidates.py
```

조건:

```text
request/response DTO 분리만 허용
model inference schema 금지
disease/pest/health schema 금지
```

---

## 4. 금지 파일/디렉터리

아래 파일/디렉터리는 만들거나 수정하지 않는다.

```text
app/mqtt/
app/llm/
app/rag/
app/retrieval/
app/workers/
app/rules/
app/models/vision_model.py
app/services/health_classifier.py
app/services/disease_classifier.py
app/services/pest_classifier.py
app/services/evidence_builder.py
app/services/prompt_builder.py
app/services/chat_orchestrator.py
app/repositories/audit_repository.py
app/repositories/chunk_repository.py
deploy/
models/
weights/
checkpoints/
```

주의:

```text
app/vision/은 이 티켓에서 허용된다.
단, SpeciesClassifierPort와 MockSpeciesClassifier 구현에만 사용한다.
```

---

## 5. SpeciesClassifierPort 계약

`app/vision/species_classifier.py`에 classifier port를 정의한다.

필수 shape:

```python
from typing import Protocol

class SpeciesClassifierPort(Protocol):
    async def classify_species(
        self,
        image_ref: str,
        *,
        locale: str = "ko-KR",
        top_k: int = 3,
    ) -> list[SpeciesCandidate]:
        ...
```

`SpeciesCandidate`는 species identification field만 포함한다.

허용 field:

```text
label_ko
label_en
scientific_name
confidence
confidence_label
source
```

예시:

```json
{
  "label_ko": "몬스테라",
  "label_en": "Monstera",
  "scientific_name": "Monstera deliciosa",
  "confidence": 0.91,
  "confidence_label": "high",
  "source": "mock"
}
```

금지 field:

```text
disease
disease_prediction
pest
pest_prediction
health
health_prediction
diagnosis
treatment
pesticide
severity
recommended_action
```

---

## 6. MockSpeciesClassifier 계약

`app/vision/mock_species_classifier.py`에 `MockSpeciesClassifier`를 구현한다.

필수 동작:

```text
same image_ref -> same candidates
network access 금지
file open 금지
image decoding 금지
model loading 금지
random output 금지
current-time-dependent output 금지
external dependency 금지
```

Deterministic mapping:

```text
image_ref contains "monstera" or "몬스테라"
  -> label_ko: 몬스테라
  -> label_en: Monstera
  -> scientific_name: Monstera deliciosa
  -> confidence: 0.91
  -> confidence_label: high
  -> source: mock

image_ref contains "pothos" or "스킨답서스"
  -> label_ko: 스킨답서스
  -> label_en: Pothos
  -> scientific_name: Epipremnum aureum
  -> confidence: 0.88
  -> confidence_label: high
  -> source: mock

image_ref contains "philodendron" or "필로덴드론"
  -> label_ko: 필로덴드론
  -> label_en: Philodendron
  -> scientific_name: Philodendron hederaceum
  -> confidence: 0.84
  -> confidence_label: medium
  -> source: mock

otherwise
  -> fallback candidate
```

Fallback candidate:

```json
{
  "label_ko": "잘 모르겠어요",
  "label_en": "Unknown",
  "scientific_name": null,
  "confidence": 0.0,
  "confidence_label": "low",
  "source": "mock"
}
```

---

## 7. API 계약

### Endpoint

```http
POST /plants/species-candidates
Content-Type: application/json
```

### Request

```json
{
  "user_id": "00000000-0000-0000-0000-000000000101",
  "image_ref": "uploads/mock/monstera.jpg",
  "locale": "ko-KR",
  "top_k": 3
}
```

### Response

```json
{
  "candidates": [
    {
      "species_profile_id": "00000000-0000-0000-0000-000000000201",
      "label_ko": "몬스테라",
      "label_en": "Monstera",
      "scientific_name": "Monstera deliciosa",
      "confidence": 0.91,
      "confidence_label": "high",
      "source": "mock"
    }
  ]
}
```

규칙:

```text
Endpoint는 SpeciesClassifierPort를 호출해야 한다.
Endpoint는 real model을 instantiate하면 안 된다.
classifier result를 species_profiles에 optional resolve할 수 있다.
species_profile_id는 DB match가 없으면 null 가능.
mock이 분류하지 못하면 "잘 모르겠어요" fallback을 반환한다.
response에 disease/pest/health/diagnosis field를 넣지 않는다.
```

---

## 8. SpeciesCandidateService 계약

`app/services/species_candidate_service.py`를 생성한다.

책임:

```text
image_ref + locale + top_k 입력 수신
SpeciesClassifierPort 호출
classifier candidate를 API DTO로 변환
optional species_profiles lookup
species_profile_id resolution
```

금지:

```text
image file read
image URL fetch
image decoding
real inference
OpenVINO / PyTorch / TensorFlow / ONNX Runtime 호출
health classification
disease classification
pest classification
plant profile creation
character state creation
LLM call
RAG call
```

---

## 9. SpeciesRepository 연동 계약

`app/repositories/species_repository.py`는 candidate를 existing `species_profiles`와 매칭할 때만 사용한다.

허용 lookup:

```text
find by scientific_name
find by korean_name
find by common_name / label_en if already supported
```

허용 결과:

```text
match exists:
  species_profile_id = matched profile id

no match:
  species_profile_id = null
```

금지 DB write:

```text
plants insert
plant_characters insert
sensor_readings insert
environment_snapshots insert
chat_requests insert
llm_runs insert
recommendation_evidence insert
retrieved_chunks insert
```

---

## 10. Runtime 계약

허용 runtime topology:

```text
host
  -> backend container
      -> uvicorn app.main:app
      -> POST /plants/species-candidates
      -> SpeciesCandidateService
      -> SpeciesClassifierPort
      -> MockSpeciesClassifier
      -> optional species_profiles lookup

  -> postgres container
      -> PostgreSQL
```

허용 long-lived containers:

```text
backend
postgres
```

금지 long-lived containers:

```text
redis
mqtt
worker
nginx
vllm
model-server
```

Backend process invariant:

```text
exactly one foreground uvicorn process
no model server
no worker
no scheduler
no MQTT subscriber
no Redis consumer
no LLM runtime
no background preload
```

Startup invariant:

```text
Allowed:
  import app.main
  create FastAPI app
  load settings
  register routes
  instantiate MockSpeciesClassifier as lightweight Python object

Forbidden:
  open image files
  load model weights
  download model
  initialize GPU/NPU
  initialize OpenVINO
  import torch/tensorflow/onnxruntime
  connect to Redis/MQTT/vLLM
  call external APIs
```

---

## 11. image_ref 계약

`image_ref`는 opaque string이다.

허용:

```text
string matching on image_ref
deterministic mapping based on image_ref text
```

금지:

```text
open(image_ref)
Image.open(image_ref)
cv2.imread(image_ref)
requests.get(image_ref)
httpx.get(image_ref)
urllib/urlopen
EXIF parsing
image bytes parsing
image decoding
```

즉 Ticket 3에서는 아래처럼 처리한다.

```text
uploads/mock/monstera.jpg
  -> string contains "monstera"
  -> mock candidate: 몬스테라
```

---

## 12. Health / Readiness 계약

### `/healthz`

Ticket 0 liveness contract를 그대로 유지한다.

```http
GET /healthz
200
```

```json
{
  "status": "ok",
  "service": "sunshine-backend"
}
```

`/healthz`에서 금지:

```text
check MockSpeciesClassifier
check model readiness
check species candidate behavior
check DB
change response shape
```

### `/readyz`

Ticket 1 readiness는 DB-only로 유지한다.

```json
{
  "status": "ready",
  "service": "sunshine-backend",
  "checks": {
    "database": "ok"
  }
}
```

`/readyz`에서 금지:

```text
check mock classifier
check model files
check image storage
check GPU/NPU availability
include "vision": "ok"
include "model": "ok"
```

---

## 13. Determinism 계약

같은 request는 항상 같은 logical candidate list를 반환해야 한다.

예:

```json
{
  "image_ref": "uploads/mock/monstera.jpg",
  "locale": "ko-KR",
  "top_k": 3
}
```

필수:

```text
same request -> same response
same image_ref -> same candidates
```

금지:

```text
random confidence
time-dependent output
environment-dependent output
network-dependent output
file-content-dependent output
```

---

## 14. Dependency 계약

허용 dependency:

```text
existing FastAPI / Pydantic / Pydantic Settings
SQLAlchemy / asyncpg / Alembic if already introduced
pytest / httpx / ruff
```

금지 dependency:

```text
torch
torchvision
tensorflow
keras
onnxruntime
openvino
opencv-python
Pillow
transformers
timm
ultralytics
sentence-transformers
vllm
openai
anthropic
redis
paho-mqtt
pgvector
```

---

## 15. 테스트 요구사항

아래 테스트를 추가한다.

```text
tests/test_species_classifier_contract.py
tests/test_mock_species_classifier.py
tests/test_species_candidates_api.py
tests/test_ticket3_boundary.py
```

### SpeciesClassifierPort tests

필수 확인:

```text
SpeciesClassifierPort shape exists
classify_species(image_ref, locale, top_k) async contract
returns list[SpeciesCandidate]
SpeciesCandidate contains allowed fields only
no disease/pest/health fields
```

### MockSpeciesClassifier tests

필수 케이스:

```text
monstera image_ref -> 몬스테라 candidate
몬스테라 image_ref -> 몬스테라 candidate
pothos image_ref -> 스킨답서스 candidate
스킨답서스 image_ref -> 스킨답서스 candidate
philodendron image_ref -> 필로덴드론 candidate
필로덴드론 image_ref -> 필로덴드론 candidate
unknown image_ref -> 잘 모르겠어요 fallback
same image_ref twice -> same output
top_k respected
no file open
no network
no model loading
```

### API tests

필수 케이스:

```text
POST /plants/species-candidates with monstera -> candidates returned
same request twice -> same response
unknown image_ref -> 잘 모르겠어요 fallback
response includes species_profile_id key
species_profile_id may be null when unresolved
response excludes disease/pest/health/diagnosis fields
endpoint does not create plant
endpoint does not create character state
```

### Boundary tests

필수 확인:

```text
no app/mqtt/
no app/llm/
no app/rag/
no app/retrieval/
no app/workers/
no app/rules/
no models/
no weights/
no checkpoints/

no real ML dependency
no OpenVINO/PyTorch/TensorFlow/ONNX Runtime dependency
no opencv/Pillow dependency
no Redis/MQTT dependency
no LLM/RAG/vLLM/OpenAI/Anthropic dependency

no image file open
no image URL fetch
no image decoding
no model loading

no disease classifier
no pest classifier
no health classifier

no writes to:
  plants
  plant_characters
  sensor_readings
  environment_snapshots
  chat_requests
  llm_runs
  recommendation_evidence
  retrieved_chunks
```

---

## 16. Functional Expectations

### Known species

Input:

```json
{
  "user_id": "00000000-0000-0000-0000-000000000101",
  "image_ref": "uploads/mock/monstera.jpg",
  "locale": "ko-KR",
  "top_k": 3
}
```

Expected:

```text
first candidate:
  label_ko = 몬스테라
  label_en = Monstera
  scientific_name = Monstera deliciosa
  confidence = 0.91
  confidence_label = high
  source = mock
```

### Unknown fallback

Input:

```json
{
  "user_id": "00000000-0000-0000-0000-000000000101",
  "image_ref": "uploads/mock/unrecognized-plant.jpg",
  "locale": "ko-KR",
  "top_k": 3
}
```

Expected:

```text
first candidate:
  label_ko = 잘 모르겠어요
  label_en = Unknown
  scientific_name = null
  confidence = 0.0
  confidence_label = low
  source = mock
```

### No diagnosis leakage

Response must not contain:

```text
disease
disease_prediction
pest
pest_prediction
health
health_prediction
diagnosis
treatment
pesticide
severity
recommended_action
```

### No product write

Calling `POST /plants/species-candidates` must not create:

```text
plant row
plant_character row
sensor_reading row
chat/evidence/RAG row
```

---

## 17. 구현 금지 항목

이 티켓에서 아래 기능은 구현하지 않는다.

```text
real species classifier
disease classifier
pest classifier
health classifier
image bytes parsing
image file open
EXIF parsing
model file loading
model registry
model download
training pipeline
OpenVINO integration
PyTorch integration
TensorFlow integration
ONNX Runtime integration
plant creation changes beyond candidate mapping
character state engine
plant card recommendation
care action logging
growth history
companion recommendation
LLMPort
PromptBuilder
EvidenceBuilder
RAG retrieval
pgvector retrieval
vLLM
Redis queue
async worker
MQTT ingestion
```

---

## 18. 최종 완료 조건

Ticket 3은 아래가 모두 만족되면 완료다.

```text
SpeciesClassifierPort exists.
MockSpeciesClassifier exists.
MockSpeciesClassifier is deterministic.
POST /plants/species-candidates calls SpeciesClassifierPort.
Known image_ref returns stable species candidate.
Unknown image_ref returns "잘 모르겠어요" fallback.
Candidate response includes only species-identification fields.
No disease/pest/health/diagnosis fields leak into response.
image_ref remains opaque string.
No image IO, URL fetch, image decoding, model loading, model dependency exists.
Endpoint does not create plants or product-side rows.
No Redis, MQTT, worker, LLM, RAG, vLLM, OpenVINO, PyTorch, TensorFlow, ONNX Runtime leaks into this ticket.
/healthz liveness remains unchanged.
/readyz remains DB-only.
```