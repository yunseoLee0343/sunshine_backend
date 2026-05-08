# TICKET-014C — Hybrid Retrieval Boundary

## 0. 목표

Sunshine 백엔드에서 Ticket 14A의 정형 식물 지식 필터와 Ticket 14B의 vector chunk를 결합한 hybrid retrieval boundary를 구현한다.

이 티켓은 final answer를 만들지 않는다.
이 티켓은 prompt를 만들지 않는다.
이 티켓은 EvidenceBuilder / ForwardContext를 만들지 않는다.
이 티켓은 LLM을 호출하지 않는다.
이 티켓은 diagnosis / treatment / pesticide instruction을 만들지 않는다.
이 티켓은 companion compatibility ranking을 만들지 않는다.

Ticket 14C의 책임은 아래까지만이다.

```text
query
  + selected_rag_layers
  + species_profile_id (optional)
  + plant_id (optional)
  + top_k
  -> validate inputs
  -> resolve relational filters via Ticket 14A
  -> embed query via Ticket 14B LocalEmbeddingPort
  -> kNN search over 14B chunk embeddings within filtered scope
  -> persist retrieval_runs + retrieved_chunks
  -> return chunks with source_metadata + structured_metadata
```

---

## 1. Ticket Identity

### Ticket ID

```text
TICKET-014C
```

### Name

```text
Hybrid Retrieval Boundary
```

---

## 2. Goal

```text
Expose POST /retrieval/query as the only retrieval surface in the system,
combining Ticket 14A relational filters with Ticket 14B vector chunks into
a single deterministic hybrid retrieval call. The endpoint persists every
retrieval run and the chunks it returned, so that Ticket 15+ can build
evidence bundles on top of this audit trail without 14C touching prompts,
LLMs, evidence, diagnosis, treatment, or companion ranking.
```

---

## 3. Core Scope

```text
RagLayer enum locked to layers that 14A/14B can serve
RagLayer -> ChunkKind mapping
HybridRetrievalRequest / HybridRetrievalResponse schemas
RetrievalService (validation + filter + embed + knn + persist + format)
POST /retrieval/query
retrieval_runs schema (hybrid)
retrieved_chunks schema (hybrid)
deterministic ordering and tie-break
source_metadata field
structured_metadata field
ownership check for plant_id
species_profile_id resolution to 14A entries
RetrievalRunRepository / RetrievedChunkRepository
```

---

## 4. Strict Non-goals

```text
no final answer generation
no chat answer
no POST /plants/{plant_id}/chat
no POST /chat
no PromptBuilder
no EvidenceBuilder
no ForwardContext
no LLMPort
no LLM call
no streaming
no SSE
no fixed final answer format
no [결론][근거][행동][주의] format
no Rule Engine execution
no rule + chunk fusion (that is Ticket 15)
no companion compatibility filter
no companion recommendation ranking
no definitive pest/disease diagnosis
no image-based diagnosis
no treatment recommendation
no pesticide instruction
no reranker
no HyDE
no CRAG
no Self-RAG
no multi-query retrieval
no query decomposition
no LLM-based query rewriting
no web search
no URL fetching
no crawler
no PDF parsing
no arbitrary document ingestion (chunks must already exist via 14B)
no chunk creation in this ticket (chunks come from 14B)
no embedding generation in this ticket (embeddings come from 14B)
no Redis / scheduler / worker / model server
no LangChain / LlamaIndex
```

---

## 5. Dependencies

### Upstream tickets

```text
Ticket 0:
  Backend Skeleton + CI/CD Baseline
Ticket 1:
  Core Domain Models + Postgres Baseline (users, species_profiles, plants)
Ticket 14A:
  Plant Relational Knowledge Store
    - PlantKnowledgeRepository (read-only)
    - resolves species_profile_id to plant_knowledge_id when wired
Ticket 14B:
  Excel-Derived Embedding Chunk Store
    - LocalEmbeddingPort (for embedding the query)
    - ChunkRepository (read chunk text + metadata)
    - EmbeddingRepository.knn (vector search over chunks)
```

### Downstream tickets

```text
Ticket 15:
  EvidenceBuilder consumes retrieval_runs and retrieved_chunks for
  ForwardContext.
Ticket 16:
  PromptBuilder consumes EvidenceBuilder output. Ticket 14C does not feed
  PromptBuilder directly.
Ticket 17:
  LLMPort. Out of scope for 14C.
Ticket 18:
  Chat Care Answer API. Out of scope for 14C.
Ticket 19:
  pest/disease reference answer guardrail. Out of scope for 14C.
Ticket 20/21:
  companion compatibility / recommendation. Out of scope for 14C.
```

### Allowed runtime dependencies

```text
existing FastAPI / Pydantic / SQLAlchemy / Alembic / Postgres stack
the embedding library locked by Ticket 14B
the vector backend locked by Ticket 14B (pgvector or local jsonb)
numpy
Python stdlib hashlib / json / math / dataclasses
pytest / httpx / ruff (dev)
```

### Forbidden runtime dependencies

```text
openai
anthropic
vllm
tensorflow
onnxruntime
openvino
faiss
chromadb
langchain
llama-index
scrapy
beautifulsoup4
playwright
selenium
redis
celery
rq
apscheduler
jinja2
```

규칙:

```text
14C must not introduce a new embedding library or vector backend. It uses
  whatever Ticket 14B locked.
```

---

## 6. Allowed Files

### 수정 가능한 기존 파일

```text
app/main.py
app/api/__init__.py
app/repositories/__init__.py
app/core/config.py
pyproject.toml
.github/workflows/ci.yml
```

### 생성 가능한 새 파일

```text
app/domain/rag.py
app/domain/retrieval.py
app/schemas/retrieval.py
app/api/retrieval.py
app/services/retrieval_service.py
app/retrieval/__init__.py
app/retrieval/hybrid_retriever.py
app/repositories/retrieval_run_repository.py
app/repositories/retrieved_chunk_repository.py

tests/test_rag_layer_mapping.py
tests/test_retrieval_request_validation.py
tests/test_hybrid_retriever.py
tests/test_retrieval_service.py
tests/test_retrieval_api.py
tests/test_retrieval_persistence.py
tests/test_retrieval_determinism.py
tests/test_retrieval_ownership.py
tests/test_ticket14c_boundary.py
```

### 조건부 migration 허용

```text
alembic/versions/<ticket14c_retrieval_runs>.py
```

허용 table:

```text
retrieval_runs
retrieved_chunks
```

금지 migration:

```text
plant_knowledge_*       (owned by 14A)
plant_chunk_documents   (owned by 14B)
plant_chunk_embeddings  (owned by 14B)
evidence_bundles
llm_runs
recommendation_evidence
prompt tables
final answer tables
companion ranking tables
chat transcript tables
web crawl tables
```

---

## 7. Forbidden Files

```text
app/services/evidence_builder.py
app/services/prompt_builder.py
app/services/chat_orchestrator.py
app/services/chat_care_answer_service.py
app/services/llm_port.py
app/services/companion_recommendation.py
app/services/pest_diagnosis_service.py
app/services/chunk_build_service.py
app/services/plant_knowledge_ingest_service.py

app/embedding/chunk_builder.py
app/embedding/build_chunks.py

app/api/chat.py
app/api/chat_runs.py
app/api/companion.py
app/api/diagnosis.py
app/api/evidence.py

app/llm/
deploy/
```

규칙:

```text
Ticket 14C must not modify Ticket 14A schema or services.
Ticket 14C must not modify Ticket 14B schema, services, or chunk text builder.
Ticket 14C must not modify Rule Engine, chat intent classifier,
  EvidenceBuilder, PromptBuilder, LLMPort, companion recommendation, or
  final chat answer logic except for type import compatibility.
```

---

## 8. Data / Schema Contract

### `retrieval_runs`

Allowed columns:

```text
retrieval_run_id          UUID PK
request_id                UUID NOT NULL
user_id                   UUID NOT NULL
plant_id                  UUID NULL FK -> plants
species_profile_id        UUID NULL FK -> species_profiles
query                     TEXT NOT NULL
selected_rag_layers_json  JSONB NOT NULL
relational_filters_json   JSONB NOT NULL DEFAULT '{}'
top_k_requested           INTEGER NOT NULL
top_k_returned            INTEGER NOT NULL
embedding_model_name      TEXT NOT NULL
embedding_model_rev       TEXT NOT NULL
query_vector_hash         TEXT NOT NULL
chunk_builder_version     TEXT NOT NULL
created_at                TIMESTAMPTZ NOT NULL
```

규칙:

```text
request_id is required and unique together with retrieval_run_id semantics:
  same request_id may only be reused for the same (user_id, query,
  selected_rag_layers, relational_filters, top_k) tuple. Otherwise reject.
query_vector_hash = sha256(canonical_json({"model": embedding_model_name,
  "rev": embedding_model_rev, "vector": rounded_vector})).
chunk_builder_version mirrors Ticket 14B CHUNK_BUILDER_VERSION at run time.
```

### `retrieved_chunks`

Allowed columns:

```text
id                          UUID PK
retrieval_run_id            UUID NOT NULL FK -> retrieval_runs
chunk_id                    UUID NOT NULL FK -> plant_chunk_documents
plant_knowledge_id          UUID NOT NULL FK -> plant_knowledge_entries
rank                        INTEGER NOT NULL
score                       DOUBLE PRECISION NOT NULL
layer                       TEXT NOT NULL
chunk_kind                  TEXT NOT NULL
source_metadata_json        JSONB NOT NULL
structured_metadata_json    JSONB NOT NULL
created_at                  TIMESTAMPTZ NOT NULL
```

규칙:

```text
rank is 1-based.
score is the raw vector distance returned by the EmbeddingRepository.knn —
  lower is closer for L2.
layer is the RagLayer string requested by the caller.
chunk_kind is the ChunkKind that produced the chunk.
source_metadata_json captures provenance (Excel file/sheet/row, 농사로ID,
  scientific_name, korean_name).
structured_metadata_json captures relational fields relevant to the chunk
  (e.g. care_requirement fields when chunk_kind = care_requirement).
```

### Forbidden columns

```text
final_answer
chat_answer
prompt
prompt_hash
llm_response
model_provider
streaming_chunks
diagnosis
treatment
pesticide
companion_ranking
companion_compatibility_score
ranking_score_external
crawl_url
fetched_html
pdf_path
```

---

## 9. RagLayer Contract

Allowed RagLayer values in 14C:

```text
species_profile
care_knowledge
pest_disease_reference
```

Forbidden RagLayer values in 14C:

```text
companion_plant
user_memory
web_search
general_web
diagnosis
marketplace
image_diagnosis
llm_memory
vector_global
```

규칙:

```text
companion_plant retrieval is owned by Ticket 20/21 once they exist. Until
  then, 14C must reject companion_plant in selected_rag_layers with 400
  or 422.
user_memory retrieval is out of scope for 14C.
```

RagLayer -> ChunkKind mapping:

```text
species_profile        -> {identity, visual_trait}
care_knowledge         -> {care_requirement, seasonal_watering, placement}
pest_disease_reference -> {pest_reference}
```

규칙:

```text
A request with selected_rag_layers = ["species_profile", "care_knowledge"]
  considers chunks of ChunkKind in
  {identity, visual_trait, care_requirement, seasonal_watering, placement}.
Chunks outside the mapped set are excluded from kNN candidates.
pest_disease_reference chunks must be returned with reference_only=true in
  source_metadata.
```

---

## 10. Service Contract

아래 파일을 생성한다.

```text
app/retrieval/hybrid_retriever.py
app/services/retrieval_service.py
```

필수 class shape:

```python
class HybridRetriever:
    async def retrieve(
        self,
        *,
        query: str,
        layers: list[RagLayer],
        relational_filters: RelationalFilters,
        top_k: int,
    ) -> list[RetrievedChunkRow]:
        ...

class RetrievalService:
    async def query(
        self,
        *,
        request: HybridRetrievalRequest,
    ) -> HybridRetrievalResponse:
        ...
```

`RelationalFilters` shape:

```text
species_profile_id  UUID | None
plant_knowledge_id  UUID | None
```

규칙:

```text
species_profile_id is resolved to plant_knowledge_id via 14A repositories.
  If species_profile_id is supplied but no matching 14A entry exists,
  the run still executes with relational filter = no plant restriction,
  but logs the unresolved id in relational_filters_json.
plant_knowledge_id may be passed directly for tests/admin paths.
```

필수 동작 (RetrievalService.query):

```text
1.  Validate request shape (RagLayer set, top_k bounds, query non-empty).
2.  Verify ownership if plant_id is supplied (user_id must own plant_id).
3.  Resolve relational filters from species_profile_id when present.
4.  Embed the query via Ticket 14B LocalEmbeddingPort.
5.  Compute query_vector_hash deterministically.
6.  Compute the candidate ChunkKind set from selected_rag_layers.
7.  Call EmbeddingRepository.knn(query_vector, top_k_oversample, filter).
8.  Filter results to the candidate ChunkKind set and the resolved
    plant_knowledge_id when present.
9.  Sort by (score asc, chunk_id asc).
10. Trim to top_k.
11. For each chunk:
      - Load source_metadata from 14A.plant_knowledge_sources +
        plant_knowledge_entries (file/sheet/row, 농사로ID, scientific_name,
        korean_name).
      - Load structured_metadata from the relevant 14A 1:1 section
        matching chunk_kind.
12. Persist retrieval_runs.
13. Persist retrieved_chunks rows.
14. Return HybridRetrievalResponse.
```

금지 behavior:

```text
calling LLM
calling reranker
multi-query retrieval
HyDE / CRAG / Self-RAG
LLM-based query rewriting
calling external network beyond Postgres
calling vector services other than 14B EmbeddingRepository
generating final answer
generating prompt
building EvidenceBuilder output
running Rule Engine
ranking companions
emitting diagnosis or treatment
re-ranking chunks via LLM scoring
```

---

## 11. API or CLI Contract

### Endpoint

```http
POST /retrieval/query
Content-Type: application/json
```

### Request

```json
{
  "request_id": "00000000-0000-0000-0000-000000014c01",
  "user_id": "00000000-0000-0000-0000-000000014c02",
  "plant_id": "00000000-0000-0000-0000-000000014c03",
  "species_profile_id": "00000000-0000-0000-0000-000000014c04",
  "query": "몬스테라 여름 물 주기",
  "selected_rag_layers": ["species_profile", "care_knowledge"],
  "top_k": 5
}
```

규칙:

```text
request_id is required.
user_id is required (auth substitute until later tickets wire auth).
plant_id is optional. When supplied, ownership is verified.
species_profile_id is optional. When supplied, it scopes retrieval to one
  plant_knowledge entry.
query is required and non-empty after trim.
selected_rag_layers must be a non-empty subset of allowed RagLayer.
top_k must satisfy 1 <= top_k <= RETRIEVAL_TOP_K_MAX.
```

### Response

```json
{
  "request_id": "00000000-0000-0000-0000-000000014c01",
  "retrieval_run_id": "uuid",
  "selected_rag_layers": ["species_profile", "care_knowledge"],
  "embedding_model": {
    "name": "<locked-model-name>",
    "rev": "<locked-revision>"
  },
  "chunk_builder_version": "v1",
  "top_k_requested": 5,
  "top_k_returned": 3,
  "chunks": [
    {
      "chunk_id": "uuid",
      "plant_knowledge_id": "uuid",
      "rank": 1,
      "score": 0.18,
      "layer": "care_knowledge",
      "chunk_kind": "seasonal_watering",
      "text": "물주기_여름: 흙이 마르면 충분히 관수 ...",
      "source_metadata": {
        "source_kind": "nongsaro_excel",
        "source_file": "전체식물_농사로데이터.xlsx",
        "source_sheet": "Sheet1",
        "source_row": 42,
        "nongsaro_id": "12345",
        "scientific_name": "Monstera deliciosa",
        "korean_name": "몬스테라",
        "reference_only": false
      },
      "structured_metadata": {
        "watering_spring": "2주에 한 번",
        "watering_summer": "주 1회",
        "watering_autumn": "2주에 한 번",
        "watering_winter": "한 달에 한 번"
      }
    }
  ]
}
```

규칙:

```text
chunks is [] when no chunk passes filters.
top_k_returned <= top_k_requested.
chunk text comes from plant_chunk_documents.text.
source_metadata.reference_only is true when chunk_kind = pest_reference.
structured_metadata fields depend on chunk_kind:
  identity        -> identity fields (korean_name, scientific_name,
                     family_name, origin, functional_description, use_purpose)
  care_requirement   -> care fields
  seasonal_watering  -> watering_spring/summer/autumn/winter
  pest_reference     -> pests_text, pests_management_text, parsed_pest_terms,
                        reference_only=true
  visual_trait       -> visual fields
  placement          -> placement, propagation_method, toxicity, odor
```

Required status behavior:

```text
200:
  retrieval succeeded.

400 or 422:
  empty/invalid query.
  empty selected_rag_layers.
  invalid RagLayer (e.g., companion_plant, user_memory, web_search).
  top_k out of [1, RETRIEVAL_TOP_K_MAX].
  malformed UUID.

403 or 404:
  plant_id supplied but does not belong to user_id.
  plant_id supplied but does not exist.

409:
  request_id reused with mismatching (user_id, query, layers, filters, top_k).

503:
  EmbeddingRepository or LocalEmbeddingPort failed (no chunks/embeddings
  available because 14B has not been built yet).
```

금지 response fields:

```text
final_answer
chat_answer
prompt
prompt_hash
evidence_bundle
rule_result
diagnosis
treatment
pesticide
companion_ranking
llm_response
model_provider
streaming
```

### CLI — Forbidden in 14C

```text
no python -m app.retrieval.* CLI for ad-hoc retrieval.
14C is HTTP-only. Internal scripts may call RetrievalService directly in
  tests, but no top-level command is exposed.
```

---

## 12. Runtime Contract

허용 runtime topology:

```text
host
  -> backend container
      -> uvicorn app.main:app
      -> GET /healthz
      -> GET /readyz
      -> POST /retrieval/query
      -> RetrievalService
      -> HybridRetriever
      -> 14A read-only repositories
      -> 14B LocalEmbeddingPort
      -> 14B EmbeddingRepository.knn
      -> Postgres reads/writes for retrieval_runs / retrieved_chunks
  -> postgres container
      -> PostgreSQL (with vector extension if pgvector backend)
  -> optional mqtt/mqtt-ingest from earlier tickets
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
embedding-server
embedding-worker
retrieval-worker
chunk-worker
crawler-worker
generic-worker
```

Backend process invariant:

```text
exactly one foreground uvicorn process
no retrieval worker
no embedding worker
no LLM/vLLM process
no scheduler/worker process
```

Startup allowed:

```text
import app.main
create FastAPI app
register existing prior-ticket routes
register POST /retrieval/query route
```

Startup forbidden:

```text
auto-load embedding model unless first /retrieval/query is served
auto-build chunks
auto-call retrieval
auto-call LLM
download model weights
run migrations
create vector extension
fetch URLs
```

규칙:

```text
LocalEmbeddingPort initialization may be lazy on first request.
First-request latency is acceptable. Startup must remain side-effect free.
```

---

## 13. Network / Env Contract

Required network:

```text
backend listens on 0.0.0.0:8000
postgres reachable by DATABASE_URL
```

Forbidden network behavior:

```text
external web search
URL fetching
crawler requests
external LLM API call
vLLM call
Redis call
external embedding model download at runtime
external vector DB service call
```

Allowed backend env:

```env
APP_NAME=sunshine-backend
APP_ENV=local
DATABASE_URL=postgresql+asyncpg://sunshine:change-me-local-only@postgres:5432/sunshine
RETRIEVAL_TOP_K_DEFAULT=5
RETRIEVAL_TOP_K_MAX=20
RETRIEVAL_KNN_OVERSAMPLE=4
EMBEDDING_BACKEND=pgvector            # inherited from Ticket 14B
EMBEDDING_MODEL_NAME=<locked>         # inherited from Ticket 14B
EMBEDDING_MODEL_REV=<locked>          # inherited from Ticket 14B
EMBEDDING_MODEL_LOCAL_PATH=/models/<locked>
CHUNK_BUILDER_VERSION=v1              # inherited from Ticket 14B
```

Forbidden env:

```text
REDIS_URL
LLM_BASE_URL
VLLM_BASE_URL
OPENAI_API_KEY
ANTHROPIC_API_KEY
RAG_INDEX_URL
WEB_SEARCH_API_KEY
CRAWLER_ENABLED
RERANKER_MODEL_PATH
PROMPT_TEMPLATE_PATH
JINJA_TEMPLATE_DIR
SSE_ENABLED
FINAL_ANSWER_MODEL
```

---

## 14. Persistence Contract

Allowed DB operations:

```text
read users
read plants (ownership check)
read species_profiles (resolution to 14A)
read plant_knowledge_entries
read plant_care_requirements
read plant_seasonal_watering
read plant_pest_references
read plant_visual_traits
read plant_placements
read plant_knowledge_sources
read plant_chunk_documents
read plant_chunk_embeddings
insert retrieval_runs
insert retrieved_chunks
read retrieval_runs
read retrieved_chunks
```

Forbidden DB operations:

```text
write plant_knowledge_*       (owned by 14A)
write plant_chunk_documents   (owned by 14B)
write plant_chunk_embeddings  (owned by 14B)
write evidence_bundles        (owned by 15)
write llm_runs                (owned by 17+)
write recommendation_evidence (owned by 22)
write care_logs
write environment_snapshots
write plant_characters
write species_profiles
write plants
write users
```

Idempotency:

```text
For the same (user_id, request_id) where (query, selected_rag_layers,
  relational_filters, top_k) match the existing retrieval_run, return the
  existing run with 200 and the same ordered chunks.
For mismatching content under the same request_id, return 409.
```

`/healthz` 계약:

```text
unchanged from Ticket 0 liveness.
must not query retrieval_runs or retrieved_chunks.
must not load the embedding model.
must not call LocalEmbeddingPort.
```

`/readyz` 계약:

```text
remains DB-only.
must not require any retrieval to have happened.
must not require chunks or embeddings to exist.
must not add "retrieval": "ok".
must not add "vector": "ok".
must not add "embedding": "ok".
must not load the embedding model.
```

---

## 15. Boundary Contract

Ticket 14C는 다음 boundary를 강제한다.

```text
Ticket 14C is a retrieval boundary, not an answer boundary.
Ticket 14C produces no final answer.
Ticket 14C produces no prompt.
Ticket 14C produces no evidence bundle.
Ticket 14C produces no LLM call.
Ticket 14C produces no Rule Engine result.
Ticket 14C produces no diagnosis.
Ticket 14C produces no treatment.
Ticket 14C produces no companion ranking.
Ticket 14C does not create chunks (14B owns that).
Ticket 14C does not generate embeddings outside the LocalEmbeddingPort
  call for the query string.
Ticket 14C consumes 14A and 14B as read-only.
```

Forbidden symbol references in 14C code:

```text
import openai
import anthropic
import vllm
import tensorflow
import onnxruntime
import openvino
import faiss
import chromadb
import langchain
import llama_index
import scrapy
import bs4
import playwright
import selenium
import redis
import celery
import rq
import apscheduler
import jinja2
```

Cross-ticket invariants:

```text
14C must not import from app.services.evidence_builder.
14C must not import from app.services.prompt_builder.
14C must not import from app.services.llm_port.
14C must not import from app.services.companion_recommendation.
14C must not import from app.services.pest_diagnosis_service.
14C may import from app.repositories.plant_knowledge_repository (14A read).
14C may import from app.repositories.chunk_repository (14B read).
14C may import from app.repositories.embedding_repository (14B knn).
14C may import from app.embedding.local_embedding_port (14B port).
14C must not call any function that performs LLM-style generate / chat /
  completion.
```

Determinism:

```text
For the same (query, layers, relational_filters, top_k, embedding_model,
  chunk_builder_version, chunk corpus), POST /retrieval/query returns the
  same chunk order.
Tie-break: score asc, then chunk_id asc.
Floating-point rounding for query_vector_hash uses a fixed precision
  (e.g., 6 decimal places after L2 normalization).
```

---

## 16. Test Requirements

아래 테스트를 추가한다.

```text
tests/test_rag_layer_mapping.py
tests/test_retrieval_request_validation.py
tests/test_hybrid_retriever.py
tests/test_retrieval_service.py
tests/test_retrieval_api.py
tests/test_retrieval_persistence.py
tests/test_retrieval_determinism.py
tests/test_retrieval_ownership.py
tests/test_ticket14c_boundary.py
```

### RagLayer mapping tests

```text
allowed layers: species_profile, care_knowledge, pest_disease_reference.
forbidden layers rejected: companion_plant, user_memory, web_search,
  general_web, diagnosis, marketplace, image_diagnosis, llm_memory,
  vector_global.
mapping is exactly:
  species_profile        -> {identity, visual_trait}
  care_knowledge         -> {care_requirement, seasonal_watering, placement}
  pest_disease_reference -> {pest_reference}
```

### Request validation tests

```text
empty query -> 400/422.
empty selected_rag_layers -> 400/422.
invalid layer -> 400/422.
top_k = 0 -> 400/422.
top_k > RETRIEVAL_TOP_K_MAX -> 400/422.
malformed UUID -> 400/422.
```

### HybridRetriever tests

```text
species_profile_id resolves to a single plant_knowledge_id and limits
  candidate chunks to that plant.
selected_rag_layers limits candidate chunks to mapped ChunkKinds.
knn returns chunks ordered by score asc, then chunk_id asc.
top_k_returned <= top_k_requested.
unmatched query (no chunks meet filters) returns [].
embedding model name and rev are inherited from 14B.
the retriever calls LocalEmbeddingPort exactly once per query.
```

### RetrievalService tests

```text
retrieval_run is persisted with the request_id, user_id, plant_id,
  species_profile_id, query, selected_rag_layers, relational_filters,
  top_k_requested, top_k_returned, embedding_model_name, embedding_model_rev,
  query_vector_hash, chunk_builder_version.
retrieved_chunks rows are persisted with rank, score, layer, chunk_kind,
  source_metadata_json, structured_metadata_json.
pest_reference chunks return source_metadata.reference_only = true.
chunk text never contains LLM-generated content (asserted on chunk text
  byte equality with 14B chunk text).
```

### API tests

```text
POST /retrieval/query 200 with chunks for matching query.
POST /retrieval/query 200 with chunks=[] for unmatched query.
POST /retrieval/query 400/422 for invalid layer / top_k / empty query.
POST /retrieval/query 403/404 for cross-user plant_id.
POST /retrieval/query 409 for request_id reuse with mismatching content.
POST /retrieval/query 503 when 14B has no chunks or embeddings yet.

response never contains:
  final_answer, chat_answer, prompt, prompt_hash, evidence_bundle,
  rule_result, diagnosis, treatment, pesticide, companion_ranking,
  llm_response, model_provider, streaming.
```

### Persistence tests

```text
retrieval_runs row count increases by 1 per accepted request_id.
retrieved_chunks row count equals top_k_returned per accepted request.
re-submitting the same request_id with the same content returns the same
  retrieval_run_id and the same chunk order without inserting a new row.
re-submitting the same request_id with mismatching content returns 409 and
  inserts no rows.
```

### Determinism tests

```text
same (query, layers, filters, top_k, embedding_model, chunk_corpus) ->
  same chunk order across two runs.
tie-break is score asc, chunk_id asc.
query_vector_hash is stable across runs for the same query and model.
```

### Ownership tests

```text
plant_id belonging to a different user -> 403 or 404.
plant_id that does not exist -> 403 or 404.
no plant data is leaked in 403/404 responses.
```

### Boundary tests

```text
no app/services/evidence_builder.py
no app/services/prompt_builder.py
no app/services/chat_orchestrator.py
no app/services/chat_care_answer_service.py
no app/services/llm_port.py
no app/services/companion_recommendation.py
no app/services/pest_diagnosis_service.py
no app/api/chat.py
no app/api/chat_runs.py
no app/api/companion.py
no app/api/diagnosis.py
no app/api/evidence.py
no app/llm/

no chunk creation in 14C (no writes to plant_chunk_documents).
no embedding creation in 14C (no writes to plant_chunk_embeddings).
no plant_knowledge_* writes in 14C.
no evidence_bundles / llm_runs / recommendation_evidence writes in 14C.

no forbidden imports anywhere under app/api/retrieval.py,
  app/services/retrieval_service.py, app/retrieval/hybrid_retriever.py:
  openai, anthropic, vllm, tensorflow, onnxruntime, openvino,
  faiss, chromadb, langchain, llama_index, scrapy, bs4,
  playwright, selenium, redis, celery, rq, apscheduler, jinja2.

no reranker / HyDE / CRAG / Self-RAG / multi-query / LLM-rewrite
  code paths exist.
```

---

## 17. Functional Expectations

### Hybrid retrieval — care_knowledge + species_profile

Input:

```json
{
  "request_id": "00000000-0000-0000-0000-000000014c01",
  "user_id": "00000000-0000-0000-0000-000000014c02",
  "plant_id": "00000000-0000-0000-0000-000000014c03",
  "species_profile_id": "00000000-0000-0000-0000-000000014c04",
  "query": "몬스테라 여름 물 주기",
  "selected_rag_layers": ["species_profile", "care_knowledge"],
  "top_k": 5
}
```

Expected:

```text
ownership of plant_id is verified.
species_profile_id resolves to plant_knowledge_id for "Monstera deliciosa".
candidate chunk kinds = {identity, visual_trait, care_requirement,
  seasonal_watering, placement} for that plant only.
the seasonal_watering chunk for "Monstera deliciosa" is highly likely
  rank 1 because the query mentions 여름 물 주기.
response chunks contain text + source_metadata + structured_metadata.
retrieval_runs has 1 row. retrieved_chunks has up to 5 rows.
```

### Pest reference — reference_only

Input:

```json
{
  "request_id": "00000000-0000-0000-0000-000000014c10",
  "user_id": "00000000-0000-0000-0000-000000014c02",
  "query": "잎에 하얀 점",
  "selected_rag_layers": ["pest_disease_reference"],
  "top_k": 5
}
```

Expected:

```text
chunks come only from chunk_kind = pest_reference.
each chunk's source_metadata.reference_only is true.
response contains no diagnosis field.
response contains no treatment field.
response contains no pesticide field.
chunk text does not invent disease names beyond the Excel pests_text content.
```

### No matches

Input:

```json
{
  "query": "완전히 관련 없는 우주 로켓 엔진",
  "selected_rag_layers": ["care_knowledge"],
  "top_k": 5
}
```

Expected:

```text
top_k_returned may be 0 if knn yields no chunks above an implementation-
  defined irrelevance threshold, or top_k_returned may equal top_k with
  high distance scores. The contract is: chunks are still returned in
  rank order if any candidate exists. Empty corpus -> 503.

If empty result is returned:
  {
    "top_k_returned": 0,
    "chunks": []
  }
```

### Forbidden layer

Input:

```json
{
  "selected_rag_layers": ["companion_plant"]
}
```

Expected:

```text
400 or 422.
no retrieval_run is persisted.
no chunks are returned.
```

### request_id reuse — match

Input:

```text
Same request_id, same (user_id, query, layers, filters, top_k).
```

Expected:

```text
200 with the existing retrieval_run_id and the same chunk order.
no new retrieval_runs row is inserted.
no new retrieved_chunks rows are inserted.
```

### request_id reuse — mismatch

Input:

```text
Same request_id, different query.
```

Expected:

```text
409.
no new retrieval_runs row is inserted.
no new retrieved_chunks rows are inserted.
```

### Cross-user access

Input:

```text
user_id = U1, plant_id belongs to U2.
```

Expected:

```text
403 or 404.
no retrieval_run is persisted.
no chunk leakage.
```

### 14B not built yet

Input:

```text
Valid request, but plant_chunk_documents / plant_chunk_embeddings is empty.
```

Expected:

```text
503 with a stable error code (e.g., "knowledge_not_built").
no retrieval_run is persisted.
```

### Determinism probe

Input:

```text
Two consecutive identical requests with different request_ids.
```

Expected:

```text
chunks list is identical in order (chunk_id sequence and rank).
score values match within a fixed numerical tolerance.
query_vector_hash matches.
```

---

## 18. Final Completion Criteria

Ticket 14C는 아래가 모두 만족되면 완료다.

```text
ruff check . passes.
ruff format --check . passes.
pytest passes.
docker build passes.
app.main import has no retrieval / embedding side effect.

POST /retrieval/query exists and is the only retrieval HTTP endpoint.
RagLayer enum is locked to
  {species_profile, care_knowledge, pest_disease_reference}.
RagLayer -> ChunkKind mapping is exactly:
  species_profile        -> {identity, visual_trait}
  care_knowledge         -> {care_requirement, seasonal_watering, placement}
  pest_disease_reference -> {pest_reference}.

retrieval_runs and retrieved_chunks tables exist with the documented
  hybrid columns (relational_filters_json, embedding_model_name,
  embedding_model_rev, query_vector_hash, chunk_builder_version,
  source_metadata_json, structured_metadata_json).

RetrievalService validates request, verifies plant ownership, resolves
  species_profile_id via Ticket 14A, embeds query via Ticket 14B
  LocalEmbeddingPort, runs knn via Ticket 14B EmbeddingRepository,
  filters by RagLayer -> ChunkKind, sorts by (score asc, chunk_id asc),
  trims to top_k, persists retrieval_runs and retrieved_chunks, and
  returns chunks with source_metadata + structured_metadata.

source_metadata.reference_only is true for pest_reference chunks.

response never contains final_answer, chat_answer, prompt, prompt_hash,
  evidence_bundle, rule_result, diagnosis, treatment, pesticide,
  companion_ranking, llm_response, model_provider, or streaming.

Idempotency:
  same request_id with matching content returns the existing run and
    chunk order with 200 and inserts nothing.
  same request_id with mismatching content returns 409 and inserts nothing.

Determinism:
  same (query, layers, filters, top_k, embedding_model, chunk corpus)
    yields the same chunk order.
  tie-break is score asc, chunk_id asc.
  query_vector_hash is deterministic.

Empty/missing 14B corpus returns 503 with a stable error code.

No app/services/evidence_builder.py, app/services/prompt_builder.py,
  app/services/llm_port.py, app/services/companion_recommendation.py,
  app/services/pest_diagnosis_service.py, app/api/chat.py,
  app/api/chat_runs.py, app/api/companion.py, app/api/diagnosis.py,
  app/api/evidence.py, or app/llm/ exists.

No openai / anthropic / vllm / tensorflow / onnxruntime / openvino /
  faiss / chromadb / langchain / llama-index / scrapy / bs4 /
  playwright / selenium / redis / celery / rq / apscheduler / jinja2
  dependency is added.

No chunk creation, embedding generation, plant_knowledge writes,
  evidence bundle, llm_runs, or recommendation_evidence writes occur in
  14C.

/healthz liveness remains unchanged.
/readyz remains DB-only and does not load the embedding model.

Pest reference chunks remain reference-only.
companion_plant retrieval is rejected (Ticket 20/21 ownership).
user_memory retrieval is rejected (out of scope).
web search / URL fetching / crawler / PDF ingestion paths do not exist.

Ticket 15 EvidenceBuilder boundary is not crossed:
  no ForwardContext is built.
  no evidence_bundles are written.
  no rule_result is computed.
  no PromptBuilder is invoked.
  no LLM is called.
```
