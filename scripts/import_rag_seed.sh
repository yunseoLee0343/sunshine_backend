#!/usr/bin/env bash
# import_rag_seed.sh — TICKET-047
# Imports rag_knowledge_seed_20260513.sql into the running postgres container.
#
# Usage:
#   bash scripts/import_rag_seed.sh [path/to/rag_knowledge_seed_20260513.sql]
#
# Default SQL path: rag_knowledge_seed_20260513.sql (current directory)
# Does NOT run migrations. Does NOT start services.

set -euo pipefail

SQL_FILE="${1:-rag_knowledge_seed_20260513.sql}"

if [[ ! -f "$SQL_FILE" ]]; then
  echo "ERROR: seed file not found: $SQL_FILE" >&2
  exit 1
fi

echo "Importing $SQL_FILE into sunshine database …"
docker compose exec -T postgres psql -U sunshine sunshine < "$SQL_FILE"
echo "Done."
