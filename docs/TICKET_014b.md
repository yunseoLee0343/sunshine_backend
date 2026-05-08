# TICKET-014B — Excel-Derived Embedding Chunk Store

## 0. 목표

Sunshine 백엔드에서 Ticket 14A의 정형 식물 지식을 deterministic text chunk로 변환하고, 각 chunk에 local embedding을 부여하여 vector storage에 저장한다.

이 티켓은 retrieval API를 노출하지 않는다.
이 티켓은 LLM summarization을 하지 않는다.
이 티켓은 web/PDF 등 임의 문서를 ingest하지 않는다.
이 티켓은 final answer / prompt / evidence / diagnosis / treatment를 만들지 않는다.

Ticket 14B의 책임은 아래까지만이다.

```text
Ticket 14A relational rows
  -> deterministic per-section text chunks
  -> stable chunk_id / text_hash / source_row_hash
  -> local embedding generation
  -> vector storage (pgvector OR local vector storage abstraction)
  -> idempotent rebuild
  -> read-only repositories that Ticket 14C can consume
```

---

## 1. Ticket Identity

### Ticket ID

```text
TICKET-014B
```

### Name

```text
Excel-Derived Embedding Chunk Store
```

---

## 2. Goal

```text
Convert Ticket 14A's normalized plant knowledge rows into deterministic
text chunks per knowledge section, embed them with a local embedding model,
and persist (chunk, embedding) pairs in pgvector or a local vector storage
abstraction so that Ticket 14C can perform hybrid retrieval — without
introducing any retrieval API, LLM summarization, web/PDF ingestion,
EvidenceBuilder, PromptBuilder, or final answer logic in this ticket.
```

---

## 3. Core Scope

```text
ChunkKind enum (identity, care_requirement, seasonal_watering, pest_reference, visual_trait, placement)
deterministic chunk text builder per ChunkKind
plant_chunk_documents schema
plant_chunk_embeddings schema
LocalEmbeddingPort Protocol
LocalEmbeddingService default implementation
ChunkBuildService (rebuild / incremental)
vector storage abstraction (pgvector backend OR local fallback)
CLI build entrypoint (python -m app.embedding.build_chunks)
read-only repositories for Ticket 14C
```

---

## 4. Strict Non-goals

```text
no POST /retrieval/query
no POST /retrieval/chunks
no GET /retrieval/*
no user-facing retrieval API
no hybrid retrieval logic
no scoring/ranking endpoint
no reranker
no HyDE / CRAG / Self-RAG / multi-query

no LLM summarization
no LLM rephrasing
no LLM-generated chunk text
no LLMPort
no LLM call
no PromptBuilder
no EvidenceBuilder
no ForwardContext
no final answer
no chat answer
no diagnosis
no treatment / pesticide instruction
no companion ranking

no arbitrary document ingestion
no web ingestion
no URL fetching
no crawler
no PDF parsing pipeline
no markdown / docx / html ingestion
no chunk source other than Ticket 14A relational tables
no Rule Engine execution

no Redis / scheduler / worker / model server
no LangChain / LlamaIndex
no streaming
no SSE
```

---

## 5. Dependencies

### Upstream tickets

```text
Ticket 0:
  Backend Skeleton + CI/CD Baseline
Ticket 1:
  Core Domain Models + Postgres Baseline
Ticket 14A:
  Plant Relational Knowledge Store
    - plant_knowledge_entries
    - plant_care_requirements
    - plant_seasonal_watering
    - plant_pest_references
    - plant_visual_traits
    - plant_placements
    - plant_knowledge_sources
```

### Downstream tickets

```text
Ticket 14C:
  Hybrid Retrieval Boundary — joins 14A relational filters with 14B
  vector chunks at POST /retrieval/query.
Ticket 15+:
  EvidenceBuilder / ForwardContext / PromptBuilder / LLMPort / final answer
  remain owned by Ticket 15 and later. Ticket 14B must not leak into them.
```

### Allowed runtime dependencies

```text
existing FastAPI / Pydantic / SQLAlchemy / Alembic / Postgres stack
pgvector (Python client) OR a local vector storage abstraction backed by
  Postgres JSONB / numpy persisted arrays — pick one and lock it
sentence-transformers OR an equivalent local embedding library — pick one
  and lock it
numpy
Python stdlib hashlib / json / math / pathlib / dataclasses
pytest / httpx / ruff (dev)
```

규칙:

```text
exactly one embedding library is locked in pyproject.toml.
exactly one vector storage backend is locked.
no runtime download of model weights — model files must be vendored,
  cached, or pre-fetched out of band.
```

### Forbidden runtime dependencies

```text
openai
anthropic
vllm
torch (only if the embedding library does not require it; if required, allowed but no LLM/inference side effects)
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

주의:

```text
torch may be transitively pulled by sentence-transformers. That is allowed,
but no torch-based generation, LLM, or fine-tuning code may be added in
this ticket. Embedding inference only.
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
app/domain/chunk.py
app/schemas/chunk.py
app/models/plant_chunk_document.py
app/models/plant_chunk_embedding.py
app/repositories/chunk_repository.py
app/repositories/embedding_repository.py
app/embedding/__init__.py
app/embedding/local_embedding_port.py
app/embedding/local_embedding_service.py
app/embedding/chunk_builder.py
app/embedding/build_chunks.py
app/services/chunk_build_service.py

tests/test_chunk_kind_schema.py
tests/test_chunk_text_determinism.py
tests/test_local_embedding_port.py
tests/test_local_embedding_service.py
tests/test_chunk_build_service.py
tests/test_chunk_repository.py
tests/test_embedding_repository.py
tests/test_chunk_idempotency.py
tests/test_ticket14b_boundary.py
```

### 조건부 migration 허용

```text
alembic/versions/<ticket14b_plant_chunks>.py
```

허용 table:

```text
plant_chunk_documents
plant_chunk_embeddings
```

조건부 허용 extension:

```text
CREATE EXTENSION IF NOT EXISTS vector
  - allowed only if pgvector is the chosen backend.
  - must be created in this migration only, not at app startup.
```

금지 migration:

```text
retrieval_runs
retrieved_chunks
evidence_bundles
llm_runs
recommendation_evidence
prompt tables
final answer tables
companion ranking tables
web crawl tables
generic document tables
```

---

## 7. Forbidden Files

```text
app/retrieval/
app/api/retrieval.py
app/services/retrieval_service.py
app/services/knowledge_ingest_service.py
app/repositories/retrieval_repository.py

app/services/evidence_builder.py
app/services/prompt_builder.py
app/services/chat_orchestrator.py
app/services/chat_care_answer_service.py
app/services/llm_port.py
app/services/companion_recommendation.py
app/services/pest_diagnosis_service.py

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
Ticket 14B must not modify Ticket 14A schema or services beyond importing
  read-only repositories.
Ticket 14B must not modify Rule Engine, chat intent classifier,
  EvidenceBuilder, PromptBuilder, LLMPort, companion recommendation, or
  final chat answer logic.
```

---

## 8. Data / Schema Contract

### `plant_chunk_documents`

Allowed columns:

```text
chunk_id              UUID PK
plant_knowledge_id    UUID NOT NULL FK -> plant_knowledge_entries
chunk_kind            TEXT NOT NULL
text                  TEXT NOT NULL
text_hash             TEXT NOT NULL
source_row_hash       TEXT NOT NULL
chunk_version         INTEGER NOT NULL DEFAULT 1
created_at            TIMESTAMPTZ NOT NULL
updated_at            TIMESTAMPTZ NOT NULL
```

Required uniqueness:

```text
UNIQUE (plant_knowledge_id, chunk_kind)
```

Allowed `chunk_kind` values:

```text
identity
care_requirement
seasonal_watering
pest_reference
visual_trait
placement
```

규칙:

```text
text is the deterministic concatenation of normalized 14A fields for the
  given chunk_kind.
text must be non-empty after normalization. If a section has no usable
  fields, the chunk for that kind is not created.
text_hash = sha256(text).
source_row_hash mirrors plant_knowledge_sources.source_row_hash at chunk
  build time.
chunk_version is bumped only when the deterministic builder version
  changes (locked per ticket).
```

### `plant_chunk_embeddings`

Allowed columns:

```text
chunk_id               UUID PK FK -> plant_chunk_documents
embedding_model_name   TEXT NOT NULL
embedding_model_rev    TEXT NOT NULL
embedding_dim          INTEGER NOT NULL
vector                 vector(<dim>) NOT NULL          -- pgvector backend
vector_json            JSONB NULL                       -- fallback backend
vector_norm            DOUBLE PRECISION NOT NULL
text_hash_at_embed     TEXT NOT NULL
created_at             TIMESTAMPTZ NOT NULL
updated_at             TIMESTAMPTZ NOT NULL
```

규칙:

```text
exactly one of vector or vector_json is populated, depending on the chosen
  backend. The migration must enforce this with a CHECK constraint.
embedding_model_name and embedding_model_rev are stamped from config.
embedding_dim is stamped from the model.
vector_norm is the L2 norm of the embedding.
text_hash_at_embed records the chunk's text_hash at the time of embedding,
  used to detect drift.
```

### Forbidden columns

```text
final_answer
prompt
chat_answer
llm_response
llm_summary
diagnosis
treatment
pesticide
companion_ranking
ranking_score
score
crawl_url
fetched_html
pdf_path
generic_document_id
```

### Optional pgvector index

```text
CREATE INDEX ON plant_chunk_embeddings USING ivfflat (vector vector_l2_ops)
  WITH (lists = ...);
```

규칙:

```text
allowed only with pgvector backend.
must be created in the 14B migration.
must not be created at app startup.
```

---

## 9. Service Contract

### Chunk text builder

아래 파일을 생성한다.

```text
app/embedding/chunk_builder.py
```

필수 함수 shape:

```python
def build_chunk_text(
    *,
    plant_knowledge_id: UUID,
    chunk_kind: ChunkKind,
    sections: PlantKnowledgeSections,
) -> str | None:
    ...
```

규칙:

```text
Builder is pure and deterministic.
Same PlantKnowledgeSections + same ChunkKind always yields the same string.
Returns None if all relevant fields for the kind are empty.
Builder version is a constant in code (e.g., CHUNK_BUILDER_VERSION = "v1").
```

ChunkKind text composition contract:

```text
identity:
  Korean name, scientific name, family, origin, functional description, use.

care_requirement:
  growth form, growth speed, growth temperature text, winter min temperature
  text, humidity band, light requirement, management level, management
  demand, soil, fertilizer.

seasonal_watering:
  watering_spring, watering_summer, watering_autumn, watering_winter — each
  prefixed with the season label and joined with a stable separator.

pest_reference:
  pests_text, pests_management_text — wrapped with a "reference_only: true"
  marker token at the end of the chunk text.

visual_trait:
  leaf_shape, leaf_color, flower_color, flowering_season, height_cm_text,
  width_cm_text.

placement:
  placement, propagation_method, toxicity, odor.
```

금지:

```text
calling LLM to compose chunk text
calling LLM to summarize relational fields
inserting any field not present in 14A schema
inserting any free-text not derived from 14A normalized rows
```

### LocalEmbeddingPort

아래 파일을 생성한다.

```text
app/embedding/local_embedding_port.py
```

필수 Protocol shape:

```python
class LocalEmbeddingPort(Protocol):
    model_name: str
    model_rev: str
    embedding_dim: int

    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...
```

규칙:

```text
embed must be deterministic per (model_name, model_rev, normalized text).
embed must not call any external network endpoint.
embed must not call an LLM.
embed must not stream.
```

### LocalEmbeddingService

아래 파일을 생성한다.

```text
app/embedding/local_embedding_service.py
```

필수 동작:

```text
1. Load the locked embedding model from a local cache path.
2. Expose model_name, model_rev, embedding_dim.
3. Normalize input text deterministically (NFC unicode + collapse whitespace).
4. Compute embeddings in batches.
5. L2-normalize embeddings before returning.
```

금지:

```text
downloading model weights at runtime.
calling external embedding APIs.
calling OpenAI / Anthropic / vLLM / any hosted inference.
generating text via LLM.
```

### ChunkBuildService

아래 파일을 생성한다.

```text
app/services/chunk_build_service.py
```

필수 class shape:

```python
class ChunkBuildService:
    async def rebuild_all(
        self,
        *,
        dry_run: bool = False,
    ) -> "ChunkBuildResult":
        ...

    async def rebuild_for_plant(
        self,
        *,
        plant_knowledge_id: UUID,
        dry_run: bool = False,
    ) -> "ChunkBuildResult":
        ...
```

필수 동작:

```text
1.  Load 14A entries via PlantKnowledgeRepository.
2.  For each entry and each ChunkKind:
    a. Build deterministic chunk text via build_chunk_text.
    b. Skip if text is None.
    c. Compute text_hash.
    d. Look up existing plant_chunk_documents by (plant_knowledge_id, chunk_kind).
    e. If text_hash equals existing, count as ignored.
    f. Else upsert chunk document and mark for re-embed.
3.  For chunks marked for re-embed:
    a. Call LocalEmbeddingPort.embed in batches.
    b. Upsert plant_chunk_embeddings with text_hash_at_embed.
4.  Detect drift:
    a. If a chunk's plant_chunk_embeddings.text_hash_at_embed != current
       text_hash, re-embed.
5.  Return inserted_chunks / updated_chunks / ignored_chunks /
    inserted_embeddings / updated_embeddings / ignored_embeddings counts.
```

`ChunkBuildResult` shape:

```json
{
  "inserted_chunks": 0,
  "updated_chunks": 0,
  "ignored_chunks": 0,
  "inserted_embeddings": 0,
  "updated_embeddings": 0,
  "ignored_embeddings": 0,
  "errors": []
}
```

금지 behavior:

```text
calling LLM
calling external network
fetching URLs
crawling web
parsing PDF
auto-summarizing
auto-translating
inserting chunks not derived from 14A
exposing scoring/retrieval
writing retrieval_runs / retrieved_chunks / evidence_bundles / llm_runs /
  recommendation_evidence
```

---

## 10. API or CLI Contract

### CLI — Required

```bash
python -m app.embedding.build_chunks \
  [--plant-knowledge-id <uuid>] \
  [--rebuild] \
  [--dry-run]
```

CLI exit semantics:

```text
exit 0:
  build finished. result JSON printed to stdout.
exit 2:
  validation error (invalid uuid, missing 14A data).
exit 3:
  partial failure. summary JSON printed to stderr.
```

CLI stdout JSON shape on success:

```json
{
  "scope": "all",
  "inserted_chunks": 0,
  "updated_chunks": 0,
  "ignored_chunks": 0,
  "inserted_embeddings": 0,
  "updated_embeddings": 0,
  "ignored_embeddings": 0,
  "errors": []
}
```

### HTTP API — Forbidden in 14B

```text
no POST /retrieval/query
no POST /retrieval/chunks
no GET /retrieval/*
no POST /chunks/*
no POST /embedding/*
no GET /embedding/*
```

### Optional internal read-only inspect — Allowed only as repository

```text
ChunkRepository.get_by_id(chunk_id)
ChunkRepository.list_by_plant(plant_knowledge_id)
EmbeddingRepository.get_by_chunk_id(chunk_id)
EmbeddingRepository.knn(query_vector, top_k, filter)
```

규칙:

```text
EmbeddingRepository.knn is internal only. It must not be exposed via HTTP
  in this ticket. It is consumed by Ticket 14C only.
EmbeddingRepository.knn must not accept free-text query — only an already-
  embedded query_vector. The text-to-vector conversion is the caller's
  responsibility (Ticket 14C will own that).
```

---

## 11. Runtime Contract

허용 runtime topology:

```text
host
  -> backend container
      -> uvicorn app.main:app
      -> GET /healthz
      -> GET /readyz
      -> Postgres reads/writes for plant_chunk_* tables only
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
chunk-worker
crawler-worker
generic-worker
```

Backend process invariant:

```text
exactly one foreground uvicorn process
no embedding worker
no chunk worker
no crawler process
no LLM/vLLM process
no scheduler/worker process
```

Startup allowed:

```text
import app.main
create FastAPI app
register existing prior-ticket routes
import chunk/embedding model and repository definitions
```

Startup forbidden:

```text
auto-build chunks at startup
auto-embed at startup
auto-load embedding model into memory at startup unless explicitly invoked
  by the CLI command
auto-call retrieval
auto-call LLM
download model weights
run migrations
create vector extension
```

CLI invocation invariant:

```text
chunk build is triggered explicitly via python -m app.embedding.build_chunks.
chunk build must not be triggered as a background task or scheduler.
```

---

## 12. Network / Env Contract

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
EMBEDDING_BACKEND=pgvector            # pgvector | local_jsonb
EMBEDDING_MODEL_NAME=<locked-model-name>
EMBEDDING_MODEL_REV=<locked-revision>
EMBEDDING_MODEL_LOCAL_PATH=/models/<locked-model-name>
EMBEDDING_BATCH_SIZE=32
CHUNK_BUILDER_VERSION=v1
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
```

---

## 13. Persistence Contract

Allowed DB operations:

```text
read plant_knowledge_entries
read plant_care_requirements
read plant_seasonal_watering
read plant_pest_references
read plant_visual_traits
read plant_placements
read plant_knowledge_sources
insert/upsert plant_chunk_documents
insert/upsert plant_chunk_embeddings
read plant_chunk_documents
read plant_chunk_embeddings
```

Forbidden DB operations:

```text
write plant_knowledge_*
insert/update retrieval_runs
insert/update retrieved_chunks
insert/update evidence_bundles
insert/update llm_runs
insert/update recommendation_evidence
insert/update care_logs
insert/update environment_snapshots
insert/update plant_characters
insert/update species_profiles
insert/update plants
insert/update users
```

Idempotency:

```text
re-running build with no 14A change reports all chunks/embeddings as ignored.
changing one 14A row triggers re-embed only for affected chunks of that
  plant_knowledge_id.
re-running build does not duplicate chunk_id values for the same
  (plant_knowledge_id, chunk_kind).
```

`/healthz` 계약:

```text
unchanged from Ticket 0 liveness.
must not query plant_chunk_* tables.
must not load embedding model.
```

`/readyz` 계약:

```text
remains DB-only.
must not require any chunk or embedding row to exist.
must not add "embedding": "ok".
must not add "vector": "ok".
must not add "chunks": "ok".
must not load the embedding model.
```

---

## 14. Boundary Contract

Ticket 14B는 다음 boundary를 강제한다.

```text
Ticket 14B is a chunk + embedding build boundary.
Ticket 14B produces no retrieval API.
Ticket 14B produces no scoring/ranking endpoint.
Ticket 14B produces no LLM input or output.
Ticket 14B produces no diagnosis.
Ticket 14B produces no treatment.
Ticket 14B produces no companion ranking.
Ticket 14B produces no Rule Engine result.
Ticket 14B chunks come exclusively from Ticket 14A relational rows.
```

Forbidden symbol references in 14B code:

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

조건부 허용 import:

```text
import sentence_transformers      # only if it is the locked embedding library
import pgvector                   # only if pgvector backend is selected
import torch                      # only as a transitive dep of the embedding library
```

규칙:

```text
the embedding library and vector backend are locked once in pyproject.toml
  and must be used through the LocalEmbeddingPort / repository abstractions.
the embedding library must not be used to call any LLM-style generation
  function. Embedding-only.
```

Cross-ticket invariants:

```text
14B reads 14A repositories only.
14B does not modify 14A schema or services.
14B does not expose user-facing HTTP endpoints — Ticket 14C owns that.
14B repositories may return chunk text + vector but never score, ranking,
  diagnosis, treatment, or LLM-generated text.
```

---

## 15. Test Requirements

아래 테스트를 추가한다.

```text
tests/test_chunk_kind_schema.py
tests/test_chunk_text_determinism.py
tests/test_local_embedding_port.py
tests/test_local_embedding_service.py
tests/test_chunk_build_service.py
tests/test_chunk_repository.py
tests/test_embedding_repository.py
tests/test_chunk_idempotency.py
tests/test_ticket14b_boundary.py
```

### Chunk kind / schema tests

```text
ChunkKind enum exactly equals
  {identity, care_requirement, seasonal_watering, pest_reference,
   visual_trait, placement}.
plant_chunk_documents enforces UNIQUE (plant_knowledge_id, chunk_kind).
plant_chunk_embeddings is 1:1 with plant_chunk_documents on chunk_id.
plant_chunk_documents has no diagnosis, treatment, prompt, or final_answer
  columns.
plant_chunk_embeddings stores embedding_model_name, embedding_model_rev,
  embedding_dim, and vector_norm.
```

### Chunk text determinism tests

```text
build_chunk_text is pure: same input -> same output across runs.
build_chunk_text returns None when all section fields are empty.
text_hash equals sha256(text).
text composition follows the locked ChunkKind contract.
pest_reference chunks contain a stable "reference_only" marker token.
no chunk text contains LLM-generated phrases — text is byte-equal to a
  deterministic concatenation of 14A field values.
```

### LocalEmbeddingPort / Service tests

```text
LocalEmbeddingPort.embed returns list of list[float] with len == embedding_dim.
LocalEmbeddingService is deterministic for fixed model_name + model_rev +
  normalized input.
LocalEmbeddingService normalizes vectors to unit L2 norm.
LocalEmbeddingService never calls external network.
LocalEmbeddingService never calls LLM-style generate / chat / completion.
```

### ChunkBuildService tests

```text
rebuild_all on a fresh DB inserts chunks and embeddings for every non-empty
  ChunkKind per plant_knowledge entry.
rebuild_all immediately rerun reports all ignored.
modifying one 14A row triggers updated_chunks > 0 only for that plant.
modifying one 14A row triggers re-embed only for affected chunks
  (text_hash drift).
dry_run does not write any DB rows and does not call embed.
chunks for an entry whose 14A section is fully empty are not created.
```

### Repository tests

```text
ChunkRepository.list_by_plant returns chunks ordered by chunk_kind enum order.
EmbeddingRepository.get_by_chunk_id returns vector + model metadata.
EmbeddingRepository.knn returns top_k chunks ordered by L2 distance asc.
EmbeddingRepository.knn must accept query_vector only (not text).
no repository method returns score, ranking, diagnosis, treatment, or
  LLM-generated text.
```

### Idempotency tests

```text
running build twice with no 14A change yields zero changes on the second run.
text_hash equality implies ignored.
text_hash drift implies re-embed and updated text_hash_at_embed.
chunk_id is stable across rebuilds for the same (plant_knowledge_id,
  chunk_kind).
```

### Boundary tests

```text
no app/retrieval/
no app/api/retrieval.py
no app/services/retrieval_service.py
no app/repositories/retrieval_repository.py

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

no forbidden imports anywhere under app/:
  openai, anthropic, vllm, tensorflow, onnxruntime, openvino,
  faiss, chromadb, langchain, llama_index, scrapy, bs4,
  playwright, selenium, redis, celery, rq, apscheduler, jinja2

chunk text contains no LLM-generated content (asserted via field-level
  byte equality with deterministic concatenation).

no pdf parsing, html parsing, or url-fetching code path is reachable from
  ChunkBuildService.

no writes to retrieval_runs / retrieved_chunks / evidence_bundles /
  llm_runs / recommendation_evidence.
```

---

## 16. Functional Expectations

### Initial build

Input:

```bash
python -m app.embedding.build_chunks --rebuild
```

Expected on a DB with 247 plant_knowledge_entries and an average of 5
non-empty ChunkKinds per entry:

```json
{
  "scope": "all",
  "inserted_chunks": 1235,
  "updated_chunks": 0,
  "ignored_chunks": 0,
  "inserted_embeddings": 1235,
  "updated_embeddings": 0,
  "ignored_embeddings": 0,
  "errors": []
}
```

### Idempotent rebuild

Input (immediate second run with no 14A change):

```bash
python -m app.embedding.build_chunks --rebuild
```

Expected:

```json
{
  "inserted_chunks": 0,
  "updated_chunks": 0,
  "ignored_chunks": 1235,
  "inserted_embeddings": 0,
  "updated_embeddings": 0,
  "ignored_embeddings": 1235,
  "errors": []
}
```

### Single-plant update

Scenario:

```text
14A row for ("Monstera deliciosa", "12345") changes 광요구도 from "반음지" to "반양지".
```

Input:

```bash
python -m app.embedding.build_chunks \
  --plant-knowledge-id <monstera-uuid>
```

Expected:

```text
care_requirement chunk text changes -> text_hash drift -> updated_chunks +=1.
identity / seasonal_watering / pest_reference / visual_trait / placement
  chunks unchanged -> ignored_chunks += others.
care_requirement embedding re-embedded -> updated_embeddings += 1.
chunk_id for ("Monstera deliciosa", care_requirement) is unchanged.
```

### Empty section

Scenario:

```text
A 14A entry has no values in any visual_trait field.
```

Expected:

```text
no plant_chunk_documents row is created for chunk_kind=visual_trait for
  that entry.
no plant_chunk_embeddings row is created for that missing chunk.
```

### Pest reference chunk

Expected text shape (reference-only):

```text
the chunk text concatenates pests_text and pests_management_text and ends
  with a stable "reference_only: true" marker token.
the chunk does not contain "diagnosis", "treatment", or "pesticide
  prescription" tokens emitted by 14B logic.
```

### Forbidden behavior probe

```text
calling LocalEmbeddingPort.embed with very long text -> truncated or
  chunked deterministically; never sent to an external API.
attempting to import app.retrieval.* -> module does not exist in 14B.
attempting POST /retrieval/query -> 404 in 14B scope.
attempting POST /chunks or POST /embedding -> 404 in 14B scope.
modifying app/services/evidence_builder.py -> file does not exist in 14B.
```

---

## 17. Final Completion Criteria

Ticket 14B는 아래가 모두 만족되면 완료다.

```text
ruff check . passes.
ruff format --check . passes.
pytest passes.
docker build passes.
app.main import has no chunk-build / embedding side effect.

ChunkKind enum is locked to
  {identity, care_requirement, seasonal_watering, pest_reference,
   visual_trait, placement}.
build_chunk_text is deterministic and pure.
plant_chunk_documents and plant_chunk_embeddings tables exist.
plant_chunk_documents enforces UNIQUE (plant_knowledge_id, chunk_kind).
plant_chunk_embeddings is 1:1 with plant_chunk_documents.

LocalEmbeddingPort exists.
LocalEmbeddingService is deterministic, local, and L2-normalized.
LocalEmbeddingService does not call external networks or LLMs.

ChunkBuildService.rebuild_all and rebuild_for_plant are implemented.
Re-running build with no 14A change reports all ignored.
Modifying one 14A row triggers updated_chunks for the affected plant only.
text_hash drift triggers re-embed.
dry_run does not write to DB and does not embed.

ChunkRepository / EmbeddingRepository expose internal read-only access.
EmbeddingRepository.knn accepts query_vector only (no text).
No repository returns score, diagnosis, treatment, ranking, or LLM text.

No app/retrieval/, app/llm/, evidence/prompt/chat/companion/diagnosis files
  exist.
No POST /retrieval/query, POST /retrieval/chunks, POST /embedding/*, or
  POST /chunks/* endpoints exist.

No openai / anthropic / vllm / tensorflow / onnxruntime / openvino / faiss /
  chromadb / langchain / llama-index / scrapy / bs4 / playwright / selenium /
  redis / celery / rq / apscheduler / jinja2 dependency is added.

If pgvector is selected, the vector extension is created in the 14B
  migration only — never at app startup.
If a local jsonb fallback is selected, vector_json is used and no pgvector
  extension is created.

Chunk text comes exclusively from Ticket 14A relational rows. No web,
  PDF, html, markdown, docx, or arbitrary document is ingested.

No LLM is called.
No final answer, prompt, evidence bundle, Rule Engine result, diagnosis,
  treatment, pesticide instruction, or companion ranking is produced.

/healthz liveness remains unchanged.
/readyz remains DB-only and does not load the embedding model.

Pest reference chunks remain reference-only.
```
