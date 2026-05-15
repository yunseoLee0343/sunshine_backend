# TICKET-060A3 — Excel Catalog Mock Candidate Provider

## Goal
Stop using `image_ref` substring matching. In dev/MVP mode, return deterministic raw candidate guesses that are expected to resolve through the Excel-only catalog resolver.

## Depends On
- TICKET-060A0
- TICKET-060A2

## Allowed Files
- `app/vision/mock_species_classifier.py`
- optionally `app/vision/catalog_species_classifier.py`
- `app/api/plants.py` only for provider wiring
- tests/docs

## Required Behavior
- Do not inspect `image_ref` for keywords.
- For any image_ref, return deterministic candidate guesses such as:
  - `몬스테라 델리시오사 / Monstera deliciosa`
  - `스킨답서스 / Epipremnum aureum`
  - `스파티필름 / Spathiphyllum wallisii`
- Use source: `catalog_mock`.
- Respect `top_k`.
- Confidence must be honest:
  - 0.60 medium
  - 0.50 medium
  - 0.45 low

## Important
The mock provider still does not do real image inference. It only prevents UUID `image_ref` from producing unknown-only fallback during MVP.

## Acceptance Criteria
- UUID upload refs return registerable candidates after Excel import.
- No fallback-only `잘 모르겠어요` for arbitrary UUID image_ref.
- No file I/O, image decode, or network.
