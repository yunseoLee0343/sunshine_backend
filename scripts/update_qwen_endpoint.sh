#!/usr/bin/env bash
# Update the file-based Qwen endpoint registry.
# Usage: ./scripts/update_qwen_endpoint.sh <base_url> [model]
# Example: ./scripts/update_qwen_endpoint.sh https://abc-123.runpod.net qwen3.6
set -euo pipefail

BASE_URL="${1:?Usage: $0 <base_url> [model]}"
MODEL="${2:-qwen3.6}"
OUTPUT_FILE="runtime/qwen_endpoint.json"

mkdir -p "$(dirname "$OUTPUT_FILE")"

TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

cat > "$OUTPUT_FILE" <<EOF
{
  "provider": "qwen",
  "model": "$MODEL",
  "base_url": "$BASE_URL",
  "api_key": null,
  "timeout_seconds": 120,
  "updated_at": "$TIMESTAMP"
}
EOF

echo "Endpoint registry updated: $OUTPUT_FILE"
echo "  base_url: $BASE_URL"
echo "  model:    $MODEL"
echo "  updated:  $TIMESTAMP"
