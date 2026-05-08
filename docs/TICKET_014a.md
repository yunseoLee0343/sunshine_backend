# TICKET-014A — Plant Relational Knowledge Store

## 0. 목표

Sunshine 백엔드에 `전체식물_농사로데이터.xlsx` 기반의 정형 식물 지식을 normalized relational schema로 ingest하는 boundary를 구현한다.

이 티켓은 embedding을 만들지 않는다.
이 티켓은 vector index를 만들지 않는다.
이 티켓은 retrieval API를 노출하지 않는다.
이 티켓은 LLM/Prompt/Evidence/final answer/diagnosis/treatment를 만들지 않는다.

Ticket 14A의 책임은 아래까지만이다.

```text
전체식물_농사로데이터.xlsx
  -> deterministic row parsing
  -> normalized relational tables
  -> source provenance (file/sheet/row/row_hash)
  -> idempotent upsert by stable plant identity
  -> read-only repositories that Ticket 14B/14C can consume
```

---

## 1. Ticket Identity

### Ticket ID

```text
TICKET-014A
```

### Name

```text
Plant Relational Knowledge Store
```

---

## 2. Goal

```text
Ingest 전체식물_농사로데이터.xlsx into normalized relational tables that
represent plant identity, care requirements, seasonal watering, pest reference,
visual traits, placement, and source provenance, in a way that is deterministic,
idempotent, and consumable by downstream chunk builders and retrieval services
without any embedding, retrieval API, LLM, or final answer logic in this ticket.
```

---

## 3. Core Scope

```text
Excel loader for 전체식물_농사로데이터.xlsx
PlantKnowledgeIngestService
PlantKnowledge relational schema (entries + care + watering + pest + visual + placement + source)
deterministic source_row_hash per Excel row
idempotent upsert by stable plant identity key
CLI ingestion entrypoint (python -m app.ingestion.plant_knowledge)
read-only repositories for downstream tickets
internal read-only inspect helper for tests/CLI dump only
```

---

## 4. Strict Non-goals

```text
no embedding generation
no vector index
no pgvector schema in this ticket
no chunk store
no retrieval API
no POST /retrieval/query
no hybrid retrieval logic
no scoring/ranking
no LLMPort
no LLM call
no PromptBuilder
no EvidenceBuilder
no ForwardContext
no final answer
no chat answer
no chat orchestrator
no diagnosis
no treatment / pesticide instruction
no companion compatibility ranking
no Rule Engine execution
no web search
no web crawler
no URL fetching
no PDF parsing pipeline
no arbitrary document ingestion
no Redis / scheduler / worker / model server
no LangChain / LlamaIndex
no HyDE / CRAG / Self-RAG / multi-query / reranker
```

---

## 5. Dependencies

### Upstream tickets

```text
Ticket 0:
  Backend Skeleton + CI/CD Baseline
Ticket 1:
  Core Domain Models + Postgres Baseline
    - users, species_profiles, plants are required for FK integrity even if
      this ticket does not write to them.
```

### Downstream tickets

```text
Ticket 14B:
  Builds deterministic text chunks from Ticket 14A relational rows and
  generates embeddings.
Ticket 14C:
  Joins 14A relational filters with 14B vector chunks to expose hybrid
  retrieval at POST /retrieval/query.
Ticket 15+:
  EvidenceBuilder / ForwardContext / PromptBuilder / LLMPort / final answer
  remain owned by Ticket 15 and later. Ticket 14A must not leak into them.
```

### Allowed runtime dependencies

```text
existing FastAPI / Pydantic / SQLAlchemy / Alembic / Postgres stack
openpyxl OR pandas (for Excel parsing only — pick one and lock it)
Python stdlib hashlib / json / re / pathlib / dataclasses
pytest / httpx / ruff (dev)
```

### Forbidden runtime dependencies

```text
openai
anthropic
vllm
sentence-transformers
torch
tensorflow
onnxruntime
openvino
faiss
chromadb
pgvector
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
app/domain/plant_knowledge.py
app/schemas/plant_knowledge.py
app/models/plant_knowledge_entry.py
app/models/plant_care_requirement.py
app/models/plant_seasonal_watering.py
app/models/plant_pest_reference.py
app/models/plant_visual_trait.py
app/models/plant_placement.py
app/models/plant_knowledge_source.py
app/repositories/plant_knowledge_repository.py
app/services/plant_knowledge_ingest_service.py
app/ingestion/__init__.py
app/ingestion/excel_loader.py
app/ingestion/plant_knowledge.py

tests/test_plant_knowledge_schema.py
tests/test_excel_loader.py
tests/test_plant_knowledge_ingest_service.py
tests/test_plant_knowledge_repository.py
tests/test_plant_knowledge_idempotency.py
tests/test_ticket14a_boundary.py
```

### 조건부 migration 허용

```text
alembic/versions/<ticket14a_plant_knowledge>.py
```

허용 table:

```text
plant_knowledge_entries
plant_care_requirements
plant_seasonal_watering
plant_pest_references
plant_visual_traits
plant_placements
plant_knowledge_sources
```

금지 migration:

```text
knowledge_chunks
plant_chunk_documents
plant_chunk_embeddings
retrieval_runs
retrieved_chunks
evidence_bundles
llm_runs
recommendation_evidence
prompt tables
final answer tables
vector index tables
companion ranking tables
web crawl tables
```

---

## 7. Forbidden Files

아래 경로는 14A에서 생성하거나 수정하지 않는다.

```text
app/retrieval/
app/api/retrieval.py
app/services/retrieval_service.py
app/services/knowledge_ingest_service.py
app/repositories/chunk_repository.py
app/repositories/retrieval_repository.py
app/repositories/embedding_repository.py
app/services/embedding_service.py
app/services/local_embedding_port.py
app/embedding/

app/services/evidence_builder.py
app/services/prompt_builder.py
app/services/chat_orchestrator.py
app/services/chat_care_answer_service.py
app/services/llm_port.py
app/services/companion_recommendation.py
app/services/pest_diagnosis_service.py

app/api/chat.py
app/api/companion.py
app/api/chat_runs.py
app/api/diagnosis.py
app/api/evidence.py
app/llm/
deploy/
```

규칙:

```text
Ticket 14A must not modify Rule Engine, chat intent classifier, retrieval,
embedding, EvidenceBuilder, PromptBuilder, LLMPort, companion recommendation,
or final chat answer logic except for type import compatibility at app.main /
app.api/__init__.py / app.repositories/__init__.py registration points.
```

---

## 8. Data / Schema Contract

Excel 컬럼은 아래 매핑으로 받아들인다. Excel 헤더는 Korean이며 normalized DB 컬럼은 ASCII snake_case로 고정한다.

### Source columns (Excel)

```text
한국명             -> korean_name
학명               -> scientific_name
농사로_매칭         -> nongsaro_match
농사로ID            -> nongsaro_id
과명               -> family_name
원산지             -> origin
기능성설명          -> functional_description
용도               -> use_purpose

생육형태            -> growth_form
생장속도            -> growth_speed
생육온도            -> growth_temperature_text
겨울최저온도         -> winter_min_temperature_text
습도               -> humidity_band
광요구도            -> light_requirement
관리수준            -> management_level
관리요구도          -> management_demand
토양               -> soil
비료               -> fertilizer

물주기_봄          -> watering_spring
물주기_여름        -> watering_summer
물주기_가을        -> watering_autumn
물주기_겨울        -> watering_winter

병충해             -> pests_text
병충해관리          -> pests_management_text

독성               -> toxicity
냄새               -> odor

잎형태             -> leaf_shape
잎색               -> leaf_color
꽃색               -> flower_color
꽃피는계절          -> flowering_season

성장높이(cm)        -> height_cm_text
성장너비(cm)        -> width_cm_text
번식방법            -> propagation_method
배치장소            -> placement
```

### `plant_knowledge_entries`

Allowed columns:

```text
plant_knowledge_id        UUID PK
korean_name               TEXT NOT NULL
scientific_name           TEXT NOT NULL
nongsaro_match            TEXT NULL
nongsaro_id               TEXT NULL
family_name               TEXT NULL
origin                    TEXT NULL
functional_description    TEXT NULL
use_purpose               TEXT NULL
created_at                TIMESTAMPTZ NOT NULL
updated_at                TIMESTAMPTZ NOT NULL
```

Required uniqueness:

```text
UNIQUE (scientific_name, COALESCE(nongsaro_id, ''))
```

규칙:

```text
korean_name must not be empty.
scientific_name must not be empty.
trimmed whitespace before validation.
canonicalize scientific_name casing per Excel value (do not auto-correct).
```

### `plant_care_requirements`

Allowed columns:

```text
plant_knowledge_id            UUID PK FK -> plant_knowledge_entries
growth_form                   TEXT NULL
growth_speed                  TEXT NULL
growth_temperature_text       TEXT NULL
winter_min_temperature_text   TEXT NULL
humidity_band                 TEXT NULL
light_requirement             TEXT NULL
management_level              TEXT NULL
management_demand             TEXT NULL
soil                          TEXT NULL
fertilizer                    TEXT NULL
created_at                    TIMESTAMPTZ NOT NULL
updated_at                    TIMESTAMPTZ NOT NULL
```

규칙:

```text
1:1 with plant_knowledge_entries.
no parsed numeric ranges in this ticket — keep raw text.
no inferred enum.
```

### `plant_seasonal_watering`

Allowed columns:

```text
plant_knowledge_id   UUID PK FK -> plant_knowledge_entries
watering_spring      TEXT NULL
watering_summer      TEXT NULL
watering_autumn      TEXT NULL
watering_winter      TEXT NULL
created_at           TIMESTAMPTZ NOT NULL
updated_at           TIMESTAMPTZ NOT NULL
```

규칙:

```text
1:1 with plant_knowledge_entries.
preserve original Excel free text.
no parsing into days/intervals in this ticket.
```

### `plant_pest_references`

Allowed columns:

```text
plant_knowledge_id      UUID PK FK -> plant_knowledge_entries
pests_text              TEXT NULL
pests_management_text   TEXT NULL
parsed_pest_terms       JSONB NOT NULL DEFAULT '[]'
reference_only          BOOLEAN NOT NULL DEFAULT TRUE
created_at              TIMESTAMPTZ NOT NULL
updated_at              TIMESTAMPTZ NOT NULL
```

규칙:

```text
parsed_pest_terms is a deterministic split of pests_text by /[,、/、]/ then trimmed.
parsed_pest_terms must be a JSON array of strings, ordered as in source text.
reference_only must remain TRUE — Ticket 14A is not a diagnosis source.
no symptom-to-disease mapping.
no treatment instruction.
no pesticide instruction.
```

### `plant_visual_traits`

Allowed columns:

```text
plant_knowledge_id    UUID PK FK -> plant_knowledge_entries
leaf_shape            TEXT NULL
leaf_color            TEXT NULL
flower_color          TEXT NULL
flowering_season      TEXT NULL
height_cm_text        TEXT NULL
width_cm_text         TEXT NULL
created_at            TIMESTAMPTZ NOT NULL
updated_at            TIMESTAMPTZ NOT NULL
```

규칙:

```text
height_cm_text and width_cm_text remain TEXT in this ticket.
no float coercion in this ticket.
```

### `plant_placements`

Allowed columns:

```text
plant_knowledge_id    UUID PK FK -> plant_knowledge_entries
placement             TEXT NULL
propagation_method    TEXT NULL
toxicity              TEXT NULL
odor                  TEXT NULL
created_at            TIMESTAMPTZ NOT NULL
updated_at            TIMESTAMPTZ NOT NULL
```

### `plant_knowledge_sources`

Allowed columns:

```text
plant_knowledge_id   UUID PK FK -> plant_knowledge_entries
source_kind          TEXT NOT NULL
source_file          TEXT NOT NULL
source_sheet         TEXT NOT NULL
source_row           INTEGER NOT NULL
source_row_hash      TEXT NOT NULL
ingested_at          TIMESTAMPTZ NOT NULL
```

규칙:

```text
source_kind must equal 'nongsaro_excel' for this ticket.
source_file is the basename of the ingested file.
source_sheet is the worksheet name.
source_row is the 1-based source row index in the sheet.
source_row_hash is sha256 of canonical JSON of the parsed source row.
on re-ingest of the same row_hash, no update is needed (idempotent).
```

### Forbidden columns/tables

```text
embedding
vector
embedding_dim
vector_norm
chunk_id
chunk_text
llm_summary
ranking_score
final_answer
prompt
diagnosis
treatment
pesticide
companion_ranking
crawl_url
fetched_html
pdf_path
```

---

## 9. Service Contract

아래 파일을 생성한다.

```text
app/services/plant_knowledge_ingest_service.py
```

필수 class shape:

```python
from pathlib import Path
from uuid import UUID

class PlantKnowledgeIngestService:
    async def ingest_excel(
        self,
        *,
        excel_path: Path,
        sheet: str | None = None,
        dry_run: bool = False,
    ) -> "PlantKnowledgeIngestResult":
        ...
```

필수 동작:

```text
1.  Open the Excel file deterministically.
2.  Read header row and validate required columns.
3.  For each data row:
    a. Trim and normalize whitespace.
    b. Skip rows where both korean_name and scientific_name are empty.
    c. Reject rows where scientific_name is empty but korean_name is non-empty.
    d. Compute source_row_hash from canonical JSON of the parsed row.
    e. Resolve plant_knowledge_id by (scientific_name, COALESCE(nongsaro_id, '')).
    f. Upsert plant_knowledge_entries.
    g. Upsert plant_care_requirements / plant_seasonal_watering /
       plant_pest_references / plant_visual_traits / plant_placements (1:1).
    h. Upsert plant_knowledge_sources with new ingested_at on change.
    i. If row_hash matches the existing source row hash, count as ignored.
4.  Return inserted / updated / ignored / rejected counts and per-row errors.
5.  In dry_run mode, perform validation only, no DB writes.
```

`PlantKnowledgeIngestResult` shape:

```json
{
  "inserted": 0,
  "updated": 0,
  "ignored": 0,
  "rejected": 0,
  "errors": [
    {
      "row": 17,
      "reason": "empty_scientific_name"
    }
  ]
}
```

금지 behavior:

```text
calling LLM
calling external network
fetching URLs
crawling web
parsing PDF
auto-translating Korean text
auto-classifying pests as diagnoses
auto-ranking companions
generating embeddings
writing chunk tables
writing retrieval tables
writing evidence_bundles
writing llm_runs
running Rule Engine
```

---

## 10. API or CLI Contract

### CLI — Required

```bash
python -m app.ingestion.plant_knowledge \
  --file data/전체식물_농사로데이터.xlsx \
  [--sheet Sheet1] \
  [--dry-run]
```

CLI exit semantics:

```text
exit 0:
  ingest finished. result JSON printed to stdout.
exit 2:
  validation error (missing file, missing required columns, bad sheet).
exit 3:
  one or more rows rejected. summary JSON printed to stderr.
```

CLI stdout JSON shape on success:

```json
{
  "file": "전체식물_농사로데이터.xlsx",
  "sheet": "Sheet1",
  "inserted": 0,
  "updated": 0,
  "ignored": 0,
  "rejected": 0,
  "errors": []
}
```

### HTTP API — Forbidden in 14A

```text
no POST /knowledge/plants
no POST /retrieval/query
no POST /retrieval/chunks
no GET /retrieval/*
no POST /embedding/*
```

### Optional internal read-only inspect — Allowed only as repository

```text
PlantKnowledgeRepository.get_by_id(plant_knowledge_id)
PlantKnowledgeRepository.get_by_scientific_name(scientific_name, nongsaro_id)
PlantKnowledgeRepository.list_paginated(limit, offset)
```

규칙:

```text
no scoring, no ranking, no relevance filtering in 14A repositories.
list_paginated must order by (scientific_name asc, plant_knowledge_id asc).
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
      -> Postgres reads/writes for plant_knowledge_* tables only
  -> postgres container
      -> PostgreSQL
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
vector-db
embedding-worker
ingest-worker
crawler-worker
generic-worker
```

Backend process invariant:

```text
exactly one foreground uvicorn process
no embedding worker
no crawler process
no LLM/vLLM process
no scheduler/worker process
```

Startup allowed:

```text
import app.main
create FastAPI app
register existing prior-ticket routes
import plant_knowledge model/repository definitions
```

Startup forbidden:

```text
auto-ingest Excel on startup
auto-build chunks
auto-build embeddings
auto-call retrieval
auto-call LLM
run migrations
```

CLI invocation invariant:

```text
ingest is triggered explicitly via python -m app.ingestion.plant_knowledge.
ingest must not be triggered as a background task or scheduler.
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
PLANT_KNOWLEDGE_EXCEL_PATH=data/전체식물_농사로데이터.xlsx
PLANT_KNOWLEDGE_EXCEL_SHEET=Sheet1
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
WEB_SEARCH_API_KEY
CRAWLER_ENABLED
RERANKER_MODEL_PATH
```

---

## 13. Persistence Contract

Allowed DB operations:

```text
insert/upsert plant_knowledge_entries
insert/upsert plant_care_requirements
insert/upsert plant_seasonal_watering
insert/upsert plant_pest_references
insert/upsert plant_visual_traits
insert/upsert plant_placements
insert/update plant_knowledge_sources
read plant_knowledge_* tables
```

Forbidden DB operations:

```text
insert/update knowledge_chunks
insert/update plant_chunk_documents
insert/update plant_chunk_embeddings
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
re-ingesting the same Excel produces the same plant_knowledge_id values.
re-ingesting the same row_hash counts as ignored.
re-ingesting a changed row updates existing rows in place and bumps updated_at.
```

`/healthz` 계약:

```text
unchanged from Ticket 0 liveness.
must not query plant_knowledge_* tables.
must not check ingest result.
```

`/readyz` 계약:

```text
remains DB-only.
must not require any plant_knowledge row to exist.
must not add "knowledge": "ok".
must not add "ingest": "ok".
```

---

## 14. Boundary Contract

Ticket 14A는 다음 boundary를 강제한다.

```text
Ticket 14A is a relational ingestion boundary.
Ticket 14A produces no chunks.
Ticket 14A produces no embeddings.
Ticket 14A produces no retrieval API.
Ticket 14A produces no LLM input or output.
Ticket 14A produces no diagnosis.
Ticket 14A produces no treatment.
Ticket 14A produces no companion ranking.
Ticket 14A produces no Rule Engine result.
```

Forbidden symbol references in 14A code:

```text
import openai
import anthropic
import vllm
import sentence_transformers
import torch
import tensorflow
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
```

Cross-ticket invariants:

```text
14A may be consumed by 14B and 14C only as a read-only repository.
14A repositories must not return scores, embeddings, or vectors.
14A repositories must not accept query strings — only structured filters.
```

---

## 15. Test Requirements

아래 테스트를 추가한다.

```text
tests/test_plant_knowledge_schema.py
tests/test_excel_loader.py
tests/test_plant_knowledge_ingest_service.py
tests/test_plant_knowledge_repository.py
tests/test_plant_knowledge_idempotency.py
tests/test_ticket14a_boundary.py
```

### Schema tests

```text
plant_knowledge_entries enforces non-empty korean_name and scientific_name.
plant_knowledge_entries enforces UNIQUE (scientific_name, COALESCE(nongsaro_id, '')).
plant_care_requirements is 1:1 with plant_knowledge_entries.
plant_seasonal_watering is 1:1 with plant_knowledge_entries.
plant_pest_references is 1:1 with plant_knowledge_entries.
plant_pest_references.reference_only defaults to TRUE.
plant_visual_traits is 1:1 with plant_knowledge_entries.
plant_placements is 1:1 with plant_knowledge_entries.
plant_knowledge_sources is 1:1 with plant_knowledge_entries.
no embedding/vector/chunk columns exist on any 14A table.
```

### Excel loader tests

```text
required Korean header columns are validated.
unknown extra columns are ignored without failure.
empty rows are skipped.
rows with empty scientific_name are rejected with reason "empty_scientific_name".
parsed_pest_terms is deterministic split of pests_text on , 、 / and trimmed.
source_row_hash is deterministic for the same row content.
loader does not call any external network.
loader does not call LLM.
```

### Ingest service tests

```text
new Excel ingest inserts rows and writes plant_knowledge_sources.
re-ingesting the same Excel reports all rows as ignored.
modifying a single row reports inserted=0, updated=1, ignored=N-1.
dry_run does not write any DB rows.
ingest returns rejected count and per-row error reasons.
ingest does not write to chunk, embedding, retrieval, evidence, llm_runs,
  or recommendation_evidence tables.
```

### Repository tests

```text
get_by_id returns the entry and joined 1:1 sections.
get_by_scientific_name resolves entry by (scientific_name, nongsaro_id).
list_paginated orders by (scientific_name asc, plant_knowledge_id asc).
no repository method accepts a free-text query string.
no repository method returns score, embedding, or vector fields.
```

### Idempotency tests

```text
ingesting the same Excel twice produces the same plant_knowledge_id values.
source_row_hash equality implies ignored.
changed row content implies updated and updated_at bump.
```

### Boundary tests

```text
no app/retrieval/
no app/api/retrieval.py
no app/services/retrieval_service.py
no app/embedding/
no app/services/embedding_service.py
no app/services/local_embedding_port.py
no app/repositories/embedding_repository.py
no app/repositories/chunk_repository.py
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
  openai, anthropic, vllm, sentence_transformers, torch, tensorflow,
  faiss, chromadb, langchain, llama_index, scrapy, bs4,
  playwright, selenium, redis, celery, rq, apscheduler

no forbidden columns in any 14A migration:
  embedding, vector, embedding_dim, vector_norm, chunk_id, chunk_text,
  llm_summary, ranking_score, final_answer, prompt, diagnosis, treatment,
  pesticide, companion_ranking
```

---

## 16. Functional Expectations

### Successful ingest

Input:

```bash
python -m app.ingestion.plant_knowledge \
  --file data/전체식물_농사로데이터.xlsx \
  --sheet Sheet1
```

Expected (first run):

```json
{
  "file": "전체식물_농사로데이터.xlsx",
  "sheet": "Sheet1",
  "inserted": 247,
  "updated": 0,
  "ignored": 0,
  "rejected": 0,
  "errors": []
}
```

Expected (immediate second run with same file):

```json
{
  "file": "전체식물_농사로데이터.xlsx",
  "sheet": "Sheet1",
  "inserted": 0,
  "updated": 0,
  "ignored": 247,
  "rejected": 0,
  "errors": []
}
```

### Single row update

Excel row for 학명 = "Monstera deliciosa", 농사로ID = "12345" changes 광요구도 from "반음지" to "반양지".

Expected:

```json
{
  "inserted": 0,
  "updated": 1,
  "ignored": 246,
  "rejected": 0,
  "errors": []
}
```

추가 검증:

```text
plant_knowledge_entries row for ("Monstera deliciosa", "12345") is unchanged in id.
plant_care_requirements.light_requirement is "반양지".
plant_knowledge_sources.source_row_hash is updated.
plant_knowledge_sources.ingested_at is bumped.
```

### Rejected row

Row with empty 학명 but non-empty 한국명 = "이름없는식물".

Expected:

```json
{
  "rejected": 1,
  "errors": [
    {
      "row": 17,
      "reason": "empty_scientific_name"
    }
  ]
}
```

### Dry run

```bash
python -m app.ingestion.plant_knowledge \
  --file data/전체식물_농사로데이터.xlsx \
  --sheet Sheet1 \
  --dry-run
```

Expected:

```text
counts are computed
no rows are written
plant_knowledge_entries / plant_care_requirements / plant_seasonal_watering /
plant_pest_references / plant_visual_traits / plant_placements /
plant_knowledge_sources are unchanged
```

### Repository read

```python
entry = await repo.get_by_scientific_name("Monstera deliciosa", "12345")
```

Expected:

```text
entry.korean_name == "몬스테라"
entry.care_requirement.light_requirement is preserved as Excel free text
entry.seasonal_watering.watering_summer preserves Excel free text
entry.pest_reference.reference_only is True
entry has no embedding, no vector, no score, no chunks attribute
```

### Forbidden behavior probe

```text
calling repo.get_by_scientific_name with a fuzzy query string -> not supported (no such API).
calling list_paginated and expecting score field -> not present.
attempting to import app.embedding.* -> module does not exist.
attempting to call POST /retrieval/query -> 404 in this ticket scope.
```

---

## 17. Final Completion Criteria

Ticket 14A는 아래가 모두 만족되면 완료다.

```text
ruff check . passes.
ruff format --check . passes.
pytest passes.
docker build passes.
app.main import has no ingestion side effect.

전체식물_농사로데이터.xlsx can be ingested via
  python -m app.ingestion.plant_knowledge --file <path>.

plant_knowledge_entries / plant_care_requirements / plant_seasonal_watering /
plant_pest_references / plant_visual_traits / plant_placements /
plant_knowledge_sources tables exist.

Required Korean Excel columns are validated.
Empty scientific_name rows are rejected with row index and reason.
parsed_pest_terms is a deterministic JSON array.
source_row_hash is deterministic for the same row content.
Re-ingesting the same Excel reports all rows as ignored.
Re-ingesting a changed row reports updated=1 and bumps updated_at.
Dry run writes no DB rows.

PlantKnowledgeRepository exposes structured-filter reads only.
No repository method takes a query string.
No repository method returns score, embedding, or vector fields.

No app/retrieval/, app/embedding/, app/llm/, evidence/prompt/chat/companion/
diagnosis files exist.
No POST /retrieval/query, POST /retrieval/chunks, or POST /embedding/* exists.

No knowledge_chunks, plant_chunk_documents, plant_chunk_embeddings,
retrieval_runs, retrieved_chunks, evidence_bundles, llm_runs, or
recommendation_evidence writes occur.

No openai / anthropic / vllm / sentence-transformers / torch / tensorflow /
faiss / chromadb / langchain / llama-index / scrapy / bs4 / playwright /
selenium / redis / celery / rq / apscheduler dependency is added.

/healthz liveness remains unchanged.
/readyz remains DB-only.

Pest reference rows are reference-only:
  no diagnosis output.
  no treatment output.
  no pesticide instruction.
```
