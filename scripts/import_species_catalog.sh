#!/usr/bin/env bash
# Import Excel species catalog into species_profiles.
#
# Usage (from project root on EC2):
#   bash scripts/import_species_catalog.sh
#   bash scripts/import_species_catalog.sh --dry-run
#
# The Excel file must be present at the path configured in PLANT_KNOWLEDGE_EXCEL_PATH
# (default: data/전체식물_분류정보_v1_updated_7_2.xlsx).
# Copy it from docs/ if needed:
#   cp docs/전체식물_분류정보_v1_updated_7_2.xlsx data/

set -euo pipefail

DRY_RUN=""
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN="--dry-run" ;;
  esac
done

echo "[import_species_catalog] running inside backend container..."
docker compose exec -T backend python -m app.seeds.import_species_catalog $DRY_RUN

echo ""
echo "[import_species_catalog] verification:"
docker compose exec -T backend python - <<'PY'
import asyncio
from sqlalchemy import text
from app.db.session import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as s:
        r = await s.execute(text(
            "SELECT COUNT(*) FROM species_profiles "
            "WHERE metadata_json->>'catalog_allowed' = 'true' "
            "AND metadata_json->>'source' = '전체식물_분류정보_v1_updated_7_2.xlsx'"
        ))
        count = r.scalar()
        print(f"catalog_allowed rows: {count}")

asyncio.run(check())
PY
