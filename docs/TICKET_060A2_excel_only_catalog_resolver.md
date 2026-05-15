# TICKET-060A2 — Excel-Only Catalog-Constrained Resolver

## Goal
Force all species candidate resolution to match only species rows imported from `전체식물_분류정보_v1_updated_7_2.xlsx`.

## Depends On
- TICKET-060A0
- TICKET-060A1

## Allowed Files
- `app/services/species_candidate_service.py`
- `app/repositories/species_repository.py`
- tests/docs

## Requirements
1. `SpeciesCandidateService` treats classifier output as raw guess.
2. Resolver must search only rows where:
```sql
metadata_json->>'catalog_allowed' = 'true'
AND metadata_json->>'source' = '전체식물_분류정보_v1_updated_7_2.xlsx'
```
3. Preserve match order:
   - scientific name exact
   - Korean name exact
   - common name exact
   - normalized scientific name
   - normalized common name
   - alias
4. If no Excel-catalog match:
   - `species_profile_id = null`
   - `catalog_matched = false`
   - `match_reason = "unmatched"`
5. If matched:
   - `species_profile_id != null`
   - `catalog_matched = true`
   - `display_name = species_profiles.korean_name`
   - `scientific_name = species_profiles.scientific_name`

## Acceptance Criteria
- Non-Excel/demo rows are not considered registerable candidates.
- Qwen-VL raw labels can later reuse this resolver.
- No UI changes.
