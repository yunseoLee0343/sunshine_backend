#!/usr/bin/env bash
# Health-check the Qwen vLLM endpoint.
# Usage: ./scripts/check_qwen_endpoint.sh <base_url> [model]
# Example: ./scripts/check_qwen_endpoint.sh https://abc-123.runpod.net qwen3.6
set -euo pipefail

BASE_URL="${1:?Usage: $0 <base_url> [model]}"
MODEL="${2:-qwen3.6}"

echo "==> Checking /v1/models at $BASE_URL ..."
curl -fsS "$BASE_URL/v1/models" | python3 -m json.tool
echo ""

echo "==> Sending test chat completion to $BASE_URL ..."
curl -fsS "$BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"$MODEL\",
    \"messages\": [
      {\"role\": \"system\", \"content\": \"너는 식물 관리 도우미다.\"},
      {\"role\": \"user\", \"content\": \"몬스테라 물은 언제 줘?\"}
    ],
    \"max_tokens\": 64,
    \"temperature\": 0.0,
    \"stream\": false
  }" | python3 -m json.tool
echo ""
echo "==> Health check passed."
