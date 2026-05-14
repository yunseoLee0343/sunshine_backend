# TICKET-048 — Qwen Query Embedding Alignment

## Summary

Ensures `/retrieval/query` embeds user queries using the same
`Qwen/Qwen3-Embedding-0.6B` model and 1024-dim L2-normalised vector contract
used by stored chunk embeddings.

## Hard Invariants

| Invariant | Value |
|-----------|-------|
| Query embedding model | `Qwen/Qwen3-Embedding-0.6B` |
| Query embedding `vector_dim` | `1024` |
| Query vector normalized | `True` (L2-normalize before dot-product) |
| Stored chunk model must equal query model | enforced in `HybridRetriever` |
| Stored chunk `vector_dim` must equal `1024` | enforced in `HybridRetriever` |

## Input Contract

`POST /retrieval/query`

```json
{
  "request_id": "uuid",
  "user_id": "uuid",
  "plant_id": "uuid | null",
  "species_profile_id": "uuid | null",
  "query": "몬스테라 여름 물 주기",
  "selected_rag_layers": ["species_profile", "care_knowledge"],
  "top_k": 5
}
```

Field aliases (backward compatible):

| API field | Internal field |
|-----------|---------------|
| `query` | `question` |
| `selected_rag_layers` | `rag_layers` |

## Output Contract

```json
{
  "request_id": "uuid",
  "question": "...",
  "total_results": 2,
  "from_cache": false,
  "results": [
    {
      "chunk_document_id": "uuid",
      "rank": 1,
      "similarity_score": 0.918,
      "layer": "care_knowledge",
      "chunk_kind": "seasonal_watering",
      "chunk_text": "...",
      "source_metadata": null,
      "structured_metadata": {"reference_only": false}
    }
  ]
}
```

`pest_disease_reference` chunks always have `structured_metadata.reference_only = true`.

## `retrieval_runs` persisted fields

```
request_id
user_id
plant_id
species_profile_id
question / question_hash
rag_layers
top_k
model_name = Qwen/Qwen3-Embedding-0.6B
embedding_model_rev
query_vector_hash
chunk_builder_version
total_results
created_at
```

## Error Responses

| Condition | HTTP | `error` key |
|-----------|------|-------------|
| All stored embeddings incompatible with current model/dim | 503 | `incompatible_embedding` |
| Invalid `rag_layers` value (e.g. `companion_plant`) | 422 | Pydantic validation |

## Allowed RAG Layers

```
species_profile
care_knowledge
pest_disease_reference
```

`companion_plant` and `user_memory` are rejected by schema validation.

## Not in Scope

LLMPort, final answer, PromptBuilder, EvidenceBuilder, Rule Engine,
reranker, CRAG, Self-RAG, HyDE, multi-query, companion ranking,
diagnosis, treatment, web search, Redis, worker, scheduler.
