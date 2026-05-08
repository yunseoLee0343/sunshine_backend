# TICKET-013 — Hybrid Chat Intent Classifier

## 0. 목표

Sunshine 백엔드에 채팅 질문 intent classifier를 구현한다.

이 티켓은 사용자의 질문에 답변하지 않는다.  
이 티켓은 질문을 분류하고, 이후 어떤 downstream path가 실행되어야 하는지만 결정한다.

즉 Ticket 13의 책임은 아래 하나다.

```text
user question
  -> intent classification
  -> routing metadata
  -> classification metadata persistence
````

이 티켓은 Rule Engine, RAG, EvidenceBuilder, PromptBuilder, LLMPort, 최종 답변 생성을 실행하지 않는다.

---

## 1. Ticket Identity

### Ticket ID

```text
TICKET-013
```

### Name

```text
Hybrid Chat Intent Classifier
```

### Goal

```text
Classify user chat questions before rule/RAG/LLM execution and return a strict routing decision.
```

### Core output

```text
POST /chat/intent
ChatIntentClassifierPort
LightweightIntentClassifier
LLMFallbackIntentClassifier port/mock
HybridChatIntentClassifier
ChatIntentResult schema
intent routing table
classification metadata persistence by request_id
```

### Strict non-goal

```text
no final user-facing answer
no [결론][근거][행동][주의] answer
no Rule Engine execution
no RAG retrieval
no EvidenceBuilder
no PromptBuilder
no LLMPort final answer call
no pest/disease diagnosis
no image classification
no companion plant ranking
no chat conversation persistence beyond classification metadata
```

---

## 2. 주변 티켓과의 연결

Ticket 13은 아래 user flow의 시작점이다.

```text
User Flow 5:
  Asking a care question

User Flow 6:
  Pest or Disease Reference Question

User Flow 7:
  Companion Plant Recommendation
```

Ticket 13의 위치:

```text
User question
  -> Ticket 13: intent classification only
  -> later tickets:
      Ticket 14: RAG knowledge store
      Ticket 15: EvidenceBuilder
      Ticket 16: PromptBuilder
      Ticket 17: LLMPort
      Ticket 18: Chat Care Answer API
      Ticket 19: Pest/Disease Reference Answer
      Ticket 20/21: Companion recommendation
```

Ticket 13에서 허용:

```text
question normalization
lightweight intent classification
deterministic mock LLM fallback classification
routing metadata selection
classification metadata persistence
```

Ticket 13에서 금지:

```text
Rule Engine execution
RAG retrieval
evidence bundle creation
prompt generation
final answer generation
pest/disease diagnosis
companion ranking execution
```

---

## 3. 수정/생성 허용 파일

### 수정 가능한 기존 파일

```text
app/main.py
app/api/__init__.py
app/models/chat_request.py
app/repositories/__init__.py
app/repositories/plant_repository.py
app/core/config.py
pyproject.toml
.github/workflows/ci.yml
```

### 생성 가능한 새 파일

```text
app/api/chat_intent.py
app/schemas/chat_intent.py
app/domain/chat_intent.py
app/services/chat_intent_classifier.py
app/services/lightweight_intent_classifier.py
app/services/llm_intent_classifier.py
app/repositories/chat_intent_repository.py
tests/test_chat_intent_schema.py
tests/test_lightweight_intent_classifier.py
tests/test_llm_intent_fallback.py
tests/test_hybrid_chat_intent_classifier.py
tests/test_chat_intent_api.py
tests/test_chat_intent_persistence.py
tests/test_ticket13_boundary.py
```

### 조건부 허용

```text
app/llm/__init__.py
app/llm/intent_classifier_mock.py
```

조건:

```text
deterministic mock LLM classifier 용도로만 허용한다.
intent classification만 반환해야 한다.
LLMPort final answer boundary를 정의하면 안 된다.
external LLM API를 호출하면 안 된다.
user-facing answer를 생성하면 안 된다.
```

### Migration policy

기본값:

```text
Use existing chat_requests table from Ticket 1 if it already supports classification metadata.
```

필요할 때만 허용:

```text
add columns to chat_requests:
  request_id
  user_id
  plant_id
  question
  final_intent
  classifier
  confidence
  stage1_result_json
  stage2_result_json
  selected_rule_modules_json
  selected_rag_layers_json
  requires_evidence
  requires_final_answer
  created_at
```

대안:

```text
create chat_intent_classifications table
```

금지 migration:

```text
llm_runs prompt/response persistence
retrieved_chunks table changes
recommendation_evidence writes
vector index tables
companion ranking tables
conversation message history
```

---

## 4. 금지 파일/디렉터리

아래 경로는 생성하거나 수정하지 않는다.

```text
app/rag/
app/retrieval/
app/services/evidence_builder.py
app/services/prompt_builder.py
app/services/chat_orchestrator.py
app/services/chat_care_answer_service.py
app/services/rag_retriever.py
app/services/llm_port.py
app/services/companion_recommendation.py
app/repositories/chunk_repository.py
app/repositories/audit_repository.py
app/api/chat.py
app/api/companion.py
app/api/chat_runs.py
deploy/
```

이미 이전 티켓에서 존재할 수 있는 경로:

```text
app/rules/
app/snapshots/
app/mqtt/
app/vision/
app/api/home.py
app/api/environment.py
app/api/history.py
app/api/care_logs.py
```

규칙:

```text
Ticket 13 must not modify Rule Engine, RAG, PromptBuilder, EvidenceBuilder, LLMPort, or final chat answer behavior.
```

---

## 5. API 계약 — POST /chat/intent

### Endpoint

```http
POST /chat/intent
Content-Type: application/json
```

### Request

```json
{
  "request_id": "00000000-0000-0000-0000-000000001301",
  "user_id": "00000000-0000-0000-0000-000000001302",
  "plant_id": "00000000-0000-0000-0000-000000001303",
  "question": "몬스테라 물 줘야 해?",
  "locale": "ko-KR",
  "plant_context": {
    "nickname": "초록이",
    "species_name": "몬스테라"
  }
}
```

### Response

```json
{
  "request_id": "00000000-0000-0000-0000-000000001301",
  "plant_id": "00000000-0000-0000-0000-000000001303",
  "intent": "watering_question",
  "confidence": "high",
  "classifier": "lightweight",
  "matched_pattern": "물.*줘야",
  "reason": "Matched a common watering question pattern.",
  "selected_rule_modules": ["watering"],
  "selected_rag_layers": ["species_profile", "care_knowledge"],
  "requires_evidence": true,
  "requires_final_answer": true,
  "requires_llm_fallback": false
}
```

### Status behavior

```text
200:
  classification succeeded

400 or 422:
  invalid request_id
  missing question
  empty question
  unsupported locale if strict locale handling is implemented
  invalid plant_context shape

403 or 404:
  plant_id does not exist or does not belong to user_id

200 with unknown_question:
  unsupported but valid question
```

---

## 6. Input Schema 계약

```text
request_id: UUID
user_id: UUID
plant_id: UUID
question: non-empty string, max length 1000
locale: "ko-KR" initially
plant_context:
  nickname: string | null
  species_name: string | null
```

규칙:

```text
question must be stripped before classification.
empty or whitespace-only question is rejected.
request_id is the idempotent persistence key for classification metadata.
plant ownership must be verified before persistence.
```

---

## 7. Intent Enum 계약

허용 intent:

```text
watering_question
light_question
humidity_question
temperature_question
species_care_question
pest_reference_question
companion_plant_question
unknown_question
```

금지 intent:

```text
disease_diagnosis
pest_diagnosis
image_diagnosis
final_care_answer
general_chat
purchase_recommendation
medical_advice
marketplace
```

---

## 8. Classifier Source / Confidence 계약

허용 classifier source:

```text
lightweight
llm
```

테스트 내부에서만 허용:

```text
mock_llm
```

API-facing output에서는 `mock_llm`을 반드시 아래처럼 normalize한다.

```text
classifier = "llm"
```

허용 confidence:

```text
high
medium
low
```

Stage 1 accept condition:

```text
Accept Stage 1 only when:
  confidence == high
  exactly one intent matched
  matched intent is Stage-1 eligible
  all required output fields are present
```

Stage 2 escalation condition:

```text
confidence != high
no Stage 1 pattern matched
multiple intents matched
question length exceeds configured threshold
question is long or compound
question contains unclear context
question contains symptom-like words and care-action words together
question may involve pest/disease caution
recommendation request target is unclear
classifier output is missing required fields
```

---

## 9. Stage 1 Lightweight Classifier 계약

기본 구현은 regex/keyword/normalized phrase matcher다.

허용 구현:

```text
regex
keyword matcher
normalized phrase matcher
FastText-style local classifier only if explicitly approved
```

MVP 기본값:

```text
Use regex/keyword/normalized phrase matching.
Do not add model dependency.
```

필수 예시:

```text
물 줘야 해?           -> watering_question
물 줄까?              -> watering_question
물 또 줘야 해?        -> watering_question
흙 말랐어?            -> watering_question

햇빛 부족해?          -> light_question
빛이 부족한가?        -> light_question

습도 괜찮아?          -> humidity_question
건조해?               -> humidity_question

온도 괜찮아?          -> temperature_question
너무 추워?            -> temperature_question
너무 더워?            -> temperature_question

어떻게 키워?          -> species_care_question
관리법 알려줘         -> species_care_question

병충해야?             -> pest_reference_question
잎에 하얀 점          -> pest_reference_question
잎이 이상해           -> pest_reference_question

같이 키우기 좋은 식물 -> companion_plant_question
추천해줘 + 같이       -> companion_plant_question
```

Stage 1 result shape:

```json
{
  "intent": "watering_question",
  "confidence": "high",
  "classifier": "lightweight",
  "matched_pattern": "물.*줘야",
  "requires_llm_fallback": false
}
```

Stage 1 금지:

```text
generate final user answer
decide final care action
call Rule Engine
call RAG
call LLM for final answer
classify image content
produce disease/pest diagnosis
```

---

## 10. Stage 2 LLM Fallback Classifier 계약

Stage 2는 strict intent classifier다.
최종 답변 생성기가 아니다.

Implementation constraint:

```text
Use deterministic mock LLM classifier for this ticket.
No external network.
No OpenAI/Anthropic/vLLM adapter.
No LLMPort final answer boundary.
```

Required output shape:

```json
{
  "intent": "pest_reference_question",
  "confidence": "medium",
  "classifier": "llm",
  "reason": "The user describes suspicious leaf symptoms and asks whether it may be pest-related.",
  "selected_rule_modules": [],
  "selected_rag_layers": ["pest_disease_reference", "species_profile"],
  "requires_evidence": true,
  "requires_final_answer": true
}
```

허용:

```text
classify ambiguous questions
classify compound natural-language questions
select candidate rule modules
select candidate RAG layers
return confidence
return short reason
return unknown_question when unsupported
```

금지:

```text
answer the user directly
decide final care action
override Rule Engine output
produce disease or pest diagnosis
recommend pesticide/treatment
retrieve RAG chunks
call downstream tools directly
persist prompt/response as llm_runs
```

---

## 11. Intent Routing 계약

Routing table:

```text
watering_question:
  selected_rule_modules = ["watering"]
  selected_rag_layers = ["species_profile", "care_knowledge"]
  final answer path = care answer

light_question:
  selected_rule_modules = ["light"]
  selected_rag_layers = ["species_profile", "care_knowledge"]
  final answer path = care answer

humidity_question:
  selected_rule_modules = ["humidity"]
  selected_rag_layers = ["species_profile", "care_knowledge"]
  final answer path = care answer

temperature_question:
  selected_rule_modules = ["temperature"]
  selected_rag_layers = ["species_profile", "care_knowledge"]
  final answer path = care answer

species_care_question:
  selected_rule_modules = []
  selected_rag_layers = ["species_profile", "care_knowledge"]
  final answer path = care answer

pest_reference_question:
  selected_rule_modules = []
  selected_rag_layers = ["pest_disease_reference", "species_profile"]
  final answer path = reference-only answer

companion_plant_question:
  selected_rule_modules = []
  selected_rag_layers = ["companion_plant", "species_profile"]
  final answer path = recommendation answer

unknown_question:
  selected_rule_modules = []
  selected_rag_layers = []
  final answer path = clarification/fallback answer
```

규칙:

```text
Routing metadata is declarative.
Do not execute selected_rule_modules.
Do not retrieve selected_rag_layers.
Do not call companion compatibility filter.
Do not generate final answer path content.
```

---

## 12. Persistence 계약

Classification metadata는 `request_id` 기준으로 저장한다.

허용 table:

```text
chat_requests
```

또는:

```text
chat_intent_classifications
```

Required persisted fields:

```json
{
  "request_id": "uuid",
  "user_id": "uuid",
  "plant_id": "uuid",
  "question": "잎이 처졌는데 물 줘야 해?",
  "final_intent": "watering_question",
  "classifier": "llm",
  "confidence": "medium",
  "stage1_result": {
    "intent": "watering_question",
    "confidence": "medium",
    "matched_pattern": "물.*줘야"
  },
  "stage2_result": {
    "intent": "watering_question",
    "confidence": "medium",
    "reason": "The user asks about watering but includes symptom context."
  },
  "selected_rule_modules": ["watering"],
  "selected_rag_layers": ["species_profile", "care_knowledge"],
  "requires_evidence": true,
  "requires_final_answer": true,
  "created_at": "timestamp"
}
```

Idempotency rule:

```text
request_id is unique.
duplicate request_id with same body returns existing classification or idempotent result.
duplicate request_id with different question returns 409 or 400.
```

금지 persistence:

```text
llm_runs prompt/response
recommendation_evidence
retrieved_chunks
system_facts
vector index writes
chat answer transcript
```

---

## 13. Runtime 계약

허용 runtime topology:

```text
host
  -> backend container
      -> uvicorn app.main:app
      -> GET /healthz
      -> GET /readyz
      -> POST /chat/intent
      -> HybridChatIntentClassifier
      -> LightweightIntentClassifier
      -> deterministic LLM fallback classifier mock
      -> Postgres classification metadata persistence

  -> postgres container
      -> PostgreSQL

  -> optional mqtt/mqtt-ingest from Ticket 6
```

Allowed long-lived containers:

```text
backend
postgres
mqtt
mqtt-ingest
```

Forbidden new long-lived containers:

```text
redis
nginx
vllm
model-server
llm
rag
vector-db
chat-worker
generic-worker
```

Backend process invariant:

```text
exactly one foreground uvicorn process
no Redis worker
no RAG worker
no vLLM process
no external LLM client process
no chat orchestrator worker
```

Startup allowed:

```text
import app.main
create FastAPI app
register /chat/intent route
import classifier definitions
compile regex patterns
```

Startup forbidden:

```text
connect to external LLM API
connect to vLLM
connect to Redis
initialize vector DB
load embedding model
load torch/onnx/openvino model
run migrations
start workers
retrieve RAG chunks
```

---

## 14. Network / Env 계약

Required network:

```text
backend listens on 0.0.0.0:8000
postgres reachable by DATABASE_URL for persistence
```

Forbidden network behavior:

```text
external LLM API call
vLLM call
Redis call
vector DB call
web search
RAG service call
```

Allowed backend env:

```env
APP_NAME=sunshine-backend
APP_ENV=local
DATABASE_URL=postgresql+asyncpg://sunshine:change-me-local-only@postgres:5432/sunshine
CHAT_INTENT_STAGE1_THRESHOLD=high
CHAT_INTENT_LONG_QUESTION_CHARS=80
CHAT_INTENT_USE_MOCK_LLM_FALLBACK=true
```

Allowed if Ticket 6 exists:

```env
MQTT_HOST=mqtt
MQTT_PORT=1883
MQTT_TOPIC=sensor/readings/+
```

Forbidden env:

```text
REDIS_URL
LLM_BASE_URL
VLLM_BASE_URL
OPENAI_API_KEY
ANTHROPIC_API_KEY
RAG_INDEX_URL
PGVECTOR_URL
EMBEDDING_MODEL_PATH
FINAL_ANSWER_MODEL
```

---

## 15. `/healthz` 계약

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
run classifier
query chat_requests
query Postgres
call mock LLM fallback
check RAG/LLM/vector dependencies
change response shape
```

---

## 16. `/readyz` 계약

Ticket 13에서 `/readyz`는 DB readiness만 확인한다.

Expected response:

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
run classifier
require classification rows
check external LLM
check RAG/vector DB
check Redis/vLLM
add "chat_intent": "ok"
add "llm": "ok"
add "rag": "ok"
add "vector": "ok"
```

Classification correctness는 `/readyz`가 아니라 functional tests/gates에서 검증한다.

---

## 17. Data Access / Determinism 계약

Allowed DB operations:

```text
read plant by plant_id + user_id
insert classification metadata
read classification metadata by request_id
```

Forbidden DB operations:

```text
insert/update care_logs
insert/update environment_snapshots
insert/update plant_characters
insert llm_runs
insert recommendation_evidence
insert retrieved_chunks
insert system_facts
```

Determinism invariant:

```text
For the same request and same mock fallback configuration:
  POST /chat/intent

must return the same structured classification.
```

금지:

```text
nondeterministic fallback result
random confidence
external LLM call
temperature-based generation
free-form output not matching schema
```

---

## 18. Dependency 계약

허용 dependency:

```text
existing FastAPI / Pydantic / SQLAlchemy / Alembic / Postgres stack
pytest / httpx / ruff
Python stdlib re / enum / dataclasses
```

금지 dependency:

```text
openai
anthropic
vllm
pgvector
sentence-transformers
torch
tensorflow
onnxruntime
openvino
redis
celery
rq
apscheduler
faiss
chromadb
langchain
llama-index
```

---

## 19. 테스트 요구사항

아래 테스트를 추가한다.

```text
tests/test_chat_intent_schema.py
tests/test_lightweight_intent_classifier.py
tests/test_llm_intent_fallback.py
tests/test_hybrid_chat_intent_classifier.py
tests/test_chat_intent_api.py
tests/test_chat_intent_persistence.py
tests/test_ticket13_boundary.py
```

### Schema tests

필수 확인:

```text
request_id must be UUID.
user_id must be UUID.
plant_id must be UUID.
question is required.
question is stripped.
empty question is rejected.
question max length is enforced.
locale initially supports ko-KR.
intent enum only allows supported intents.
confidence enum only allows high/medium/low.
classifier enum only allows lightweight/llm.
```

### Lightweight classifier tests

필수 케이스:

```text
물 줘야 해? -> watering_question
물 줄까? -> watering_question
흙 말랐어? -> watering_question

햇빛 부족해? -> light_question
빛이 부족한가? -> light_question

습도 괜찮아? -> humidity_question
건조해? -> humidity_question

온도 괜찮아? -> temperature_question
너무 추워? -> temperature_question
너무 더워? -> temperature_question

어떻게 키워? -> species_care_question
관리법 알려줘 -> species_care_question

병충해야? -> pest_reference_question
잎에 하얀 점 -> pest_reference_question
잎이 이상해 -> pest_reference_question

같이 키우기 좋은 식물 -> companion_plant_question
추천해줘 + 같이 -> companion_plant_question
```

### Hybrid classifier tests

필수 케이스:

```text
high-confidence single Stage 1 match returns lightweight.
ambiguous question escalates to llm classifier mock.
long compound question escalates to llm classifier mock.
unsupported question returns unknown_question.
multiple Stage 1 matches escalate to Stage 2.
Stage 2 output must match strict schema.
```

### API tests

필수 케이스:

```text
POST /chat/intent returns watering_question for watering question.
POST /chat/intent returns light_question for light question.
POST /chat/intent returns humidity_question for humidity question.
POST /chat/intent returns temperature_question for temperature question.
POST /chat/intent returns species_care_question for species care question.
POST /chat/intent returns pest_reference_question for pest reference question.
POST /chat/intent returns companion_plant_question for companion recommendation question.
POST /chat/intent returns unknown_question for unsupported valid question.
empty question returns 400 or 422.
cross-user plant access returns 403 or 404.
```

### Persistence tests

필수 확인:

```text
classification metadata is persisted by request_id.
request_id is unique.
duplicate same request_id and same body returns existing/idempotent result.
duplicate same request_id with different question returns 400 or 409.
classification persistence does not write llm_runs.
classification persistence does not write retrieved_chunks.
classification persistence does not write recommendation_evidence.
```

### Boundary tests

필수 확인:

```text
no app/rag/
no app/retrieval/

no app/services/evidence_builder.py
no app/services/prompt_builder.py
no app/services/chat_orchestrator.py
no app/services/chat_care_answer_service.py
no app/services/rag_retriever.py
no app/services/llm_port.py

no app/api/chat.py
no app/api/companion.py
no app/api/chat_runs.py

no external LLM/RAG/vector/Redis/model dependency

no final answer fields:
  final_answer
  chat_answer
  [결론]
  [근거]
  [행동]
  [주의]

no downstream output fields:
  retrieved_chunks
  evidence_bundle
  prompt
  rule_result
  evidence_facts
  diagnosis
  pesticide
  treatment

no writes to:
  llm_runs
  recommendation_evidence
  retrieved_chunks
```

---

## 20. Functional Expectations

### Watering question

Input:

```json
{
  "request_id": "00000000-0000-0000-0000-000000001311",
  "user_id": "00000000-0000-0000-0000-000000001302",
  "plant_id": "00000000-0000-0000-0000-000000001303",
  "question": "물 줘야 해?",
  "locale": "ko-KR",
  "plant_context": {
    "nickname": "초록이",
    "species_name": "몬스테라"
  }
}
```

Expected:

```json
{
  "intent": "watering_question",
  "confidence": "high",
  "classifier": "lightweight",
  "selected_rule_modules": ["watering"],
  "selected_rag_layers": ["species_profile", "care_knowledge"],
  "requires_evidence": true,
  "requires_final_answer": true,
  "requires_llm_fallback": false
}
```

### Pest reference question

Input:

```text
잎에 하얀 점이 있어
```

Expected:

```json
{
  "intent": "pest_reference_question",
  "selected_rule_modules": [],
  "selected_rag_layers": ["pest_disease_reference", "species_profile"],
  "requires_evidence": true,
  "requires_final_answer": true
}
```

주의:

```text
This is only routing metadata.
No pest diagnosis is generated.
No treatment/pesticide recommendation is generated.
```

### Companion plant question

Input:

```text
같이 키우기 좋은 식물 추천해줘
```

Expected:

```json
{
  "intent": "companion_plant_question",
  "selected_rule_modules": [],
  "selected_rag_layers": ["companion_plant", "species_profile"],
  "requires_evidence": true,
  "requires_final_answer": true
}
```

주의:

```text
This is only routing metadata.
No companion compatibility filter is executed.
No ranking is returned.
```

### Ambiguous question

Input:

```text
잎이 처졌는데 물 줘야 해?
```

Expected:

```text
classifier = llm
requires_llm_fallback = true
intent = watering_question | pest_reference_question | unknown_question
confidence = medium | low
reason is present
```

### Unknown question

Input:

```text
오늘 저녁 메뉴 뭐 먹지?
```

Expected:

```json
{
  "intent": "unknown_question",
  "selected_rule_modules": [],
  "selected_rag_layers": [],
  "requires_evidence": false,
  "requires_final_answer": false
}
```

---

## 21. 구현 금지 항목

이 티켓에서 아래 기능은 구현하지 않는다.

```text
final user-facing answer
[결론][근거][행동][주의] answer format
POST /plants/{plant_id}/chat
POST /chat
chat conversation transcript
chat orchestrator

Rule Engine execution
Rule Engine output persistence
care action decision

RAG retrieval
reference document ingestion
vector index
pgvector
retrieved_chunks writes

EvidenceBuilder
ForwardContext
evidence bundle
evidence persistence

PromptBuilder
fixed final answer prompt

LLMPort
external LLM call
vLLM call
llm_runs prompt/response persistence
streaming

pest diagnosis
disease diagnosis
pesticide/treatment recommendation

companion compatibility filter execution
companion recommendation endpoint
companion ranking

Redis
worker
scheduler
vector DB
model server
```

---

## 22. 최종 완료 조건

Ticket 13은 아래가 모두 만족되면 완료다.

```text
POST /chat/intent exists.
ChatIntentResult schema exists.
ChatIntentClassifierPort exists.
LightweightIntentClassifier exists.
LLMFallbackIntentClassifier mock exists.
HybridChatIntentClassifier exists.
ChatIntentRepository exists.

Common watering question maps to watering_question.
Common light question maps to light_question.
Common humidity question maps to humidity_question.
Common temperature question maps to temperature_question.
Species care question maps to species_care_question.
Pest reference question maps to pest_reference_question.
Companion plant question maps to companion_plant_question.
Unsupported question maps to unknown_question.
Ambiguous question escalates to deterministic llm classifier mock.

Output includes intent, confidence, classifier, selected_rule_modules, selected_rag_layers, requires_evidence, requires_final_answer.
Classification metadata is persisted by request_id.
Duplicate request_id is idempotent.
Duplicate request_id with different question is rejected.
Cross-user access is blocked.

No final answer, RAG retrieval, EvidenceBuilder, PromptBuilder, Rule Engine execution, diagnosis, companion ranking, LLMPort, external LLM, Redis, vLLM, or vector DB leaks into this ticket.

No llm_runs, recommendation_evidence, or retrieved_chunks writes occur.

/healthz liveness remains unchanged.
/readyz remains DB-only.
```