# TICKET-060A1 — Species Catalog Candidate Contract

## Goal
Extend species candidate response shape so classification can show raw model output and canonical Excel-catalog match.

## Depends On
- TICKET-060A0

## Allowed Files
- `app/schemas/plants.py`
- `frontend/src/api/types.ts`
- tests/docs

## Backend Change
Extend `SpeciesCandidateItem` without removing existing fields:

```py
display_name: str | None = None
catalog_matched: bool = False
raw_label: str | None = None
match_reason: str | None = None
```

## Frontend Type
Add matching optional fields to `SpeciesCandidateItem`.

## Contract
- `species_profile_id != null` means registerable.
- `catalog_matched=true` means candidate matched an Excel-imported species row.
- `display_name` is UI-preferred name.
- `raw_label` is classifier raw output, for future Qwen-VL.
- `match_reason`: `scientific_name_exact | korean_name_exact | common_name_exact | normalized | alias | catalog_default | unmatched`.

## Acceptance Criteria
- Existing response fields remain compatible.
- New fields serialize and compile in frontend.
- No classifier behavior changes.
