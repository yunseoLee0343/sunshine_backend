# TICKET-049 — Qwen3.6 LLMPort Adapter

## Summary

Replaces the mock final-answer generator with a `QwenLLMClient` adapter backed
by a Qwen3.6 vLLM OpenAI-compatible HTTP endpoint. `MockLLMClient` is retained
for tests. Domain services depend only on `LLMPort`.

## Config

| Setting | Default | Description |
|---------|---------|-------------|
| `LLM_BACKEND` | `mock` | `mock` or `qwen` |
| `QWEN_LLM_MODEL` | `qwen3.6` | Model name forwarded to vLLM |
| `QWEN_LLM_BASE_URL` | `http://localhost:8080` | vLLM server base URL |
| `QWEN_LLM_TIMEOUT_SECONDS` | `30.0` | Per-request HTTP timeout |

Embedding config (`EMBEDDING_MODEL_NAME`, `EMBEDDING_VECTOR_DIM`) is kept
separate and is NOT read by `QwenLLMClient`.

## Architecture

```
ChatOrchestrator
    ↓ get_llm_client()  (from client_factory)
    ├── LLM_BACKEND=mock  → MockLLMClient   (tests, local dev)
    └── LLM_BACKEND=qwen  → QwenLLMClient  (production)
```

`ChatOrchestrator` imports only `get_llm_client`; it never imports
`QwenLLMClient` directly.

## Request / Response (OpenAI-compatible)

### POST `{QWEN_LLM_BASE_URL}/v1/chat/completions`

```json
{
  "model": "qwen3.6",
  "messages": [
    {"role": "system", "content": "<system_prompt>"},
    {"role": "user",   "content": "<user_turn>"}
  ],
  "max_tokens": 1024,
  "temperature": 0.0,
  "stream": false
}
```

### LLMResponse mapping

| `LLMResponse` field | Source |
|---------------------|--------|
| `content` | `choices[0].message.content` |
| `model_metadata.model_name` | `response.model` |
| `model_metadata.provider` | `"qwen"` (constant) |
| `input_tokens` | `usage.prompt_tokens` |
| `output_tokens` | `usage.completion_tokens` |
| `finish_reason` | `choices[0].finish_reason` |

## Error Handling

| Condition | Raised exception |
|-----------|-----------------|
| `httpx.TimeoutException` | `LLMProviderError` |
| `httpx.RequestError` | `LLMProviderError` |
| HTTP status != 200 | `LLMProviderError` |
| Empty `choices` list | `LLMProviderError` |
| `stream=True` | `StreamingNotSupportedError` |

`LLMProviderError` is defined in `app/llm/qwen_client.py`.

## Invariants

- No network calls at FastAPI startup or import time.
- No embedding logic inside `QwenLLMClient`.
- No retrieval logic inside `QwenLLMClient`.
- No prompt building inside `QwenLLMClient`.
- Evidence-before-LLM pipeline order is preserved in `ChatOrchestrator`.
- Rule Engine results cannot be overridden by LLM output.
- Final answer must contain `[결론]`, `[근거]`, `[행동]`, `[주의]` sections.

## Not in Scope

Streaming SSE, embedding generation, retrieval API, EvidenceBuilder rewrite,
PromptBuilder rewrite, fine-tuning, reranker, CRAG, Self-RAG, web search,
vision, audio, Redis, worker, scheduler.
