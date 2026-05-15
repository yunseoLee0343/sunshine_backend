# TICKET-060A0 — Excel Species Catalog Import Baseline

## Goal
Make `전체식물_분류정보_v1_updated_7_2.xlsx` the only allowed species catalog source for onboarding species classification.

## Root Cause
`config.py` has `PLANT_KNOWLEDGE_EXCEL_PATH=data/전체식물_분류정보_v1_updated_7_2.xlsx`, but the current backend has no confirmed Excel -> `species_profiles` importer. Current demo species are hardcoded in `demo_seed.py`, so catalog-constrained classification would still depend on demo/legacy DB rows unless explicitly fixed.

## Scope
Backend catalog import only.

## Allowed Files
- `app/core/config.py`
- `app/models/species_profile.py`
- `app/repositories/species_repository.py`
- `app/seeds/import_species_catalog.py`
- `app/seeds/demo_seed.py` only if needed to stop conflicting catalog assumptions
- `scripts/import_species_catalog.sh`
- `tests/test_species_catalog_import.py`
- `docs/TICKET_060A0.md`

## Requirements
1. Read only:
   - `settings.PLANT_KNOWLEDGE_EXCEL_PATH`
   - expected file: `data/전체식물_분류정보_v1_updated_7_2.xlsx`
2. Import rows into `species_profiles` with stable upsert.
3. Required Excel columns:
   - `한국명`
   - `학명`
   - optionally: `과명`, `기능성설명`, `생육형태`, `생육온도`, `습도`, `광요구도`, seasonal watering columns.
4. Store provenance in `metadata_json`:
```json
{
  "source": "전체식물_분류정보_v1_updated_7_2.xlsx",
  "source_version": "v1_updated_7_2",
  "catalog_allowed": true,
  "aliases": []
}
```
5. Generate stable UUID for each row from normalized `한국명 + 학명`.
6. Empty scientific name is allowed only if Korean name exists.
7. Duplicate rows must be deterministic: same normalized key updates same species row.

## Import Command
```bash
docker compose exec backend python -m app.seeds.import_species_catalog
```

## Verification SQL
```sql
SELECT COUNT(*) FROM species_profiles
WHERE metadata_json->>'catalog_allowed' = 'true'
  AND metadata_json->>'source' = '전체식물_분류정보_v1_updated_7_2.xlsx';

SELECT korean_name, scientific_name, metadata_json->>'source'
FROM species_profiles
WHERE metadata_json->>'catalog_allowed' = 'true'
LIMIT 20;
```

## Acceptance Criteria
- Import creates Excel-derived `species_profiles`.
- Imported rows are marked `catalog_allowed=true`.
- Re-running import is idempotent.
- Later species classification can restrict matching to Excel-derived rows only.
- No Qwen-VL, image decoding, or frontend changes.

## Do Not Implement
- Qwen3-VL
- image classification
- onboarding UI changes
- RAG chunk import
