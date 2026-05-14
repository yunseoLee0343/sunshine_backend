# TICKET-046 — Dataset Source Update

## Summary

Switches the plant relational knowledge ingestion source from `전체식물_농사로데이터.xlsx`
to `전체식물_분류정보_v1_updated_7_2.xlsx`, sheet `전체식물_분류정보`.

## Changes

| File | Change |
|------|--------|
| `app/core/config.py` | Added `PLANT_KNOWLEDGE_EXCEL_PATH` (default: `data/전체식물_분류정보_v1_updated_7_2.xlsx`) |
| `app/ingestion/excel_loader.py` | New module: validates headers, strips admin columns, returns filtered rows |
| `app/services/plant_knowledge_ingest_service.py` | Updated `COLUMN_MAP` for new headers; `ingest_file` delegates to `excel_loader`; added `scientific_name` validation |

## Input contract

```
file:  data/전체식물_분류정보_v1_updated_7_2.xlsx
sheet: 전체식물_분류정보
```

### Required columns (34)

```
한국명  학명  농사로_매칭  농사로ID  과명  원산지
기능성설명  용도  생육형태  생장속도  생육온도  겨울최저온도
습도  광요구도  관리수준  관리요구도  토양  비료
물주기_봄  물주기_여름  물주기_가을  물주기_겨울
병충해  병충해관리  독성  냄새
잎형태  잎색  꽃색  꽃피는계절
성장높이(cm)  성장너비(cm)  번식방법  배치장소
```

### Ignored source-management columns

These columns are stripped before row hashing so they cannot cause spurious updates.

```
번호
수정이유_분류정보
참고링크_분류정보
확인필요_항목
```

## Output tables (unchanged)

```
plant_knowledge_entries
plant_care_requirements
plant_seasonal_watering
plant_pest_references
plant_visual_traits
plant_placements
plant_knowledge_sources
```

## Idempotency invariants

- `source_row_hash` is computed from filtered rows (ignored columns excluded).
- Re-ingesting the same row produces `ignored` status, not a duplicate.
- Only normalized content changes trigger `updated` status.

## Not in scope

Embedding, vector index, retrieval API, LLM, chunks, diagnosis, treatment, Redis, worker, scheduler.
