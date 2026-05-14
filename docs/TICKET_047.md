# TICKET-047 — Qwen Embedding & SQL Seed Import

## Summary

Updates chunk/embedding contract to `Qwen/Qwen3-Embedding-0.6B` (vector_dim=1024)
and adds an explicit SQL seed import gate for `rag_knowledge_seed_20260513.sql`.

## Embedding Contract

| Setting | Value |
|---------|-------|
| `EMBEDDING_MODEL_NAME` | `Qwen/Qwen3-Embedding-0.6B` |
| `EMBEDDING_VECTOR_DIM` | `1024` |
| `EMBEDDING_NORMALIZE` | `true` |

## Chunk Kinds (exactly 6)

```
identity
visual_trait
placement
care_requirement
seasonal_watering
pest_reference
```

## Output Tables

### plant_chunk_documents

```
id
plant_knowledge_id
chunk_kind
chunk_text
text_hash
created_at
updated_at
```

### plant_chunk_embeddings

```
id
chunk_document_id
model_name = Qwen/Qwen3-Embedding-0.6B
vector_dim = 1024
vector
vector_norm
text_hash_at_embed
created_at
updated_at
```

## SQL Seed Import

The seed file `rag_knowledge_seed_20260513.sql` is a **data artifact**.
It is NOT auto-imported at app startup, NOT required by `/healthz` or `/readyz`.

### Import command

```bash
docker compose exec -T postgres psql -U sunshine sunshine < rag_knowledge_seed_20260513.sql
```

Or use the script:

```bash
bash scripts/import_rag_seed.sh rag_knowledge_seed_20260513.sql
```

### Static SQL validation

```bash
python scripts/validate_rag_seed_sql.py rag_knowledge_seed_20260513.sql
```

### Post-import DB validation

```bash
python scripts/validate_rag_seed_db.py
```

### Validation SQL

```sql
-- row count
SELECT COUNT(*) FROM plant_knowledge_entries;
SELECT COUNT(*) FROM plant_chunk_documents;
SELECT COUNT(*) FROM plant_chunk_embeddings;

-- dim mismatch
SELECT COUNT(*) FROM plant_chunk_embeddings WHERE vector_dim <> 1024;

-- chunk_kind distribution
SELECT chunk_kind, COUNT(*)
FROM plant_chunk_documents
GROUP BY chunk_kind
ORDER BY chunk_kind;

-- model distribution
SELECT model_name, vector_dim, COUNT(*)
FROM plant_chunk_embeddings
GROUP BY model_name, vector_dim
ORDER BY model_name, vector_dim;
```

## Stale Embedding Detection

Existing embeddings with `model_name != Qwen/Qwen3-Embedding-0.6B` or
`vector_dim != 1024` are treated as stale and re-embedded on next build run.

## CLI

```bash
# Build all
python -m app.embedding.build_chunks

# Build single entry
python -m app.embedding.build_chunks --entry-id <UUID>

# Dry-run (no DB, no model download)
python -m app.embedding.build_chunks --dry-run
```

## Not in scope

Embedding generation from scratch, query embedding, POST /retrieval/query,
LLMPort, PromptBuilder, EvidenceBuilder, diagnosis, treatment, Redis, worker, scheduler.
