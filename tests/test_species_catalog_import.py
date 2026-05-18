"""TICKET-060A0 — Species catalog importer unit tests.

Tests are pure (no DB, no file I/O against the real Excel) using an
in-memory openpyxl workbook written to a temp file.
"""

from __future__ import annotations

import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

import openpyxl
import pytest

from app.seeds.import_species_catalog import (
    SOURCE_FILE,
    SOURCE_VERSION,
    _CATALOG_NS,
    _str,
    build_record,
    catalog_uuid,
    load_rows,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2025, 1, 1, tzinfo=UTC)

_BASE_HEADERS = [
    "번호", "한국명", "학명", "농사로_매칭", "농사로ID", "과명", "원산지",
    "기능성설명", "용도", "수정이유_분류정보", "참고링크_분류정보", "확인필요_항목",
    "생육형태", "생장속도", "생육온도", "겨울최저온도", "습도", "광요구도",
    "관리수준", "관리요구도", "토양", "비료",
    "물주기_봄", "물주기_여름", "물주기_가을", "물주기_겨울",
    "병충해", "병충해관리", "독성", "냄새", "잎형태", "잎색",
    "꽃색", "꽃피는계절", "성장높이(cm)", "성장너비(cm)", "번식방법", "배치장소",
]


def _make_row(**kwargs) -> dict:
    """Build a row dict with all headers, overriding named fields."""
    base = {h: None for h in _BASE_HEADERS}
    base.update(kwargs)
    return base


def _write_xlsx(headers: list[str], data_rows: list[list]) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in data_rows:
        ws.append(row)
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    wb.save(tmp.name)
    tmp.close()
    return Path(tmp.name)


# ---------------------------------------------------------------------------
# _str helper
# ---------------------------------------------------------------------------

def test_str_none_returns_none() -> None:
    assert _str(None) is None


def test_str_empty_string_returns_none() -> None:
    assert _str("") is None
    assert _str("  ") is None


def test_str_strips_whitespace() -> None:
    assert _str("  몬스테라  ") == "몬스테라"


def test_str_converts_int() -> None:
    assert _str(42) == "42"


# ---------------------------------------------------------------------------
# catalog_uuid
# ---------------------------------------------------------------------------

def test_catalog_uuid_is_deterministic() -> None:
    u1 = catalog_uuid("몬스테라", "Monstera deliciosa")
    u2 = catalog_uuid("몬스테라", "Monstera deliciosa")
    assert u1 == u2


def test_catalog_uuid_is_uuid5_in_catalog_namespace() -> None:
    expected = uuid.uuid5(_CATALOG_NS, "몬스테라::monstera deliciosa")
    assert catalog_uuid("몬스테라", "Monstera deliciosa") == expected


def test_catalog_uuid_differs_for_different_species() -> None:
    assert catalog_uuid("몬스테라", "Monstera deliciosa") != catalog_uuid("스킨답서스", "Epipremnum aureum")


def test_catalog_uuid_normalizes_case_and_whitespace() -> None:
    u1 = catalog_uuid("몬스테라", "Monstera deliciosa")
    u2 = catalog_uuid("몬스테라", "MONSTERA DELICIOSA")
    assert u1 == u2


def test_catalog_uuid_allows_none_scientific_name() -> None:
    u = catalog_uuid("무이름식물", None)
    assert isinstance(u, uuid.UUID)


# ---------------------------------------------------------------------------
# build_record
# ---------------------------------------------------------------------------

def test_build_record_returns_none_for_missing_korean_name() -> None:
    row = _make_row(한국명=None, 학명="Monstera deliciosa")
    assert build_record(row, _NOW) is None


def test_build_record_returns_none_for_empty_korean_name() -> None:
    row = _make_row(한국명="   ", 학명="Monstera deliciosa")
    assert build_record(row, _NOW) is None


def test_build_record_valid_row_returns_dict() -> None:
    row = _make_row(한국명="몬스테라", 학명="Monstera deliciosa", 과명="천남성과")
    rec = build_record(row, _NOW)
    assert rec is not None
    assert rec["korean_name"] == "몬스테라"
    assert rec["scientific_name"] == "Monstera deliciosa"


def test_build_record_id_is_stable_uuid() -> None:
    row = _make_row(한국명="몬스테라", 학명="Monstera deliciosa")
    rec = build_record(row, _NOW)
    assert rec is not None
    assert rec["id"] == catalog_uuid("몬스테라", "Monstera deliciosa")


def test_build_record_metadata_catalog_allowed_true() -> None:
    row = _make_row(한국명="몬스테라", 학명="Monstera deliciosa")
    rec = build_record(row, _NOW)
    assert rec is not None
    assert rec["metadata_json"]["catalog_allowed"] is True


def test_build_record_metadata_source_fields() -> None:
    row = _make_row(한국명="몬스테라", 학명="Monstera deliciosa")
    rec = build_record(row, _NOW)
    assert rec is not None
    assert rec["metadata_json"]["source"] == SOURCE_FILE
    assert rec["metadata_json"]["source_version"] == SOURCE_VERSION


def test_build_record_metadata_aliases_is_empty_list() -> None:
    row = _make_row(한국명="몬스테라", 학명="Monstera deliciosa")
    rec = build_record(row, _NOW)
    assert rec is not None
    assert rec["metadata_json"]["aliases"] == []


def test_build_record_optional_columns_stored_in_metadata() -> None:
    row = _make_row(
        한국명="몬스테라", 학명="Monstera deliciosa",
        과명="천남성과", 생육온도="16~20℃", 습도="70% 이상",
    )
    rec = build_record(row, _NOW)
    assert rec is not None
    assert rec["metadata_json"]["과명"] == "천남성과"
    assert rec["metadata_json"]["생육온도"] == "16~20℃"
    assert rec["metadata_json"]["습도"] == "70% 이상"


def test_build_record_none_optional_columns_not_in_metadata() -> None:
    row = _make_row(한국명="몬스테라", 학명="Monstera deliciosa", 과명=None)
    rec = build_record(row, _NOW)
    assert rec is not None
    assert "과명" not in rec["metadata_json"]


def test_build_record_numeric_fields_are_none() -> None:
    row = _make_row(한국명="몬스테라", 학명="Monstera deliciosa")
    rec = build_record(row, _NOW)
    assert rec is not None
    for field in ("water_min_pct", "water_max_pct", "light_min_lux", "light_max_lux",
                  "humidity_min_pct", "humidity_max_pct", "temperature_min_c", "temperature_max_c"):
        assert rec[field] is None, f"{field} should be None"


def test_build_record_care_level_from_management_column() -> None:
    row = _make_row(한국명="몬스테라", 학명="Monstera deliciosa", 관리수준="초보자")
    rec = build_record(row, _NOW)
    assert rec is not None
    assert rec["care_level"] == "초보자"


def test_build_record_allows_missing_scientific_name() -> None:
    row = _make_row(한국명="알수없는식물", 학명=None)
    rec = build_record(row, _NOW)
    assert rec is not None
    assert rec["scientific_name"] is None


def test_build_record_timestamps_equal_now() -> None:
    row = _make_row(한국명="몬스테라", 학명="Monstera deliciosa")
    rec = build_record(row, _NOW)
    assert rec is not None
    assert rec["created_at"] == _NOW
    assert rec["updated_at"] == _NOW


# ---------------------------------------------------------------------------
# load_rows
# ---------------------------------------------------------------------------

def test_load_rows_raises_for_missing_file() -> None:
    with pytest.raises(FileNotFoundError, match="Excel catalog not found"):
        load_rows(Path("/nonexistent/path.xlsx"))


def test_load_rows_returns_correct_count() -> None:
    data = [
        [1, "몬스테라", "Monstera deliciosa"] + [None] * (len(_BASE_HEADERS) - 3),
        [2, "스킨답서스", "Epipremnum aureum"] + [None] * (len(_BASE_HEADERS) - 3),
    ]
    path = _write_xlsx(_BASE_HEADERS, data)
    rows = load_rows(path)
    assert len(rows) == 2


def test_load_rows_keys_match_headers() -> None:
    data = [[1, "몬스테라", "Monstera deliciosa"] + [None] * (len(_BASE_HEADERS) - 3)]
    path = _write_xlsx(_BASE_HEADERS, data)
    rows = load_rows(path)
    assert rows[0]["한국명"] == "몬스테라"
    assert rows[0]["학명"] == "Monstera deliciosa"


def test_load_rows_empty_sheet_returns_empty_list() -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(_BASE_HEADERS)
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    wb.save(tmp.name)
    tmp.close()
    rows = load_rows(Path(tmp.name))
    assert rows == []


# ---------------------------------------------------------------------------
# Idempotency: same normalized key -> same UUID
# ---------------------------------------------------------------------------

def test_same_key_produces_same_uuid_across_builds() -> None:
    row = _make_row(한국명="몬스테라", 학명="Monstera deliciosa")
    r1 = build_record(row, _NOW)
    r2 = build_record(row, datetime(2025, 6, 1, tzinfo=UTC))
    assert r1 is not None and r2 is not None
    assert r1["id"] == r2["id"]
