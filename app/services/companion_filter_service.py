"""CompanionFilterService — TICKET-020.

Deterministic companion plant compatibility filter.

Rules:
  - Compares room environment (light, humidity, temperature) against each
    candidate's growing-condition thresholds.
  - A dimension is SKIPPED (not penalised) when either the candidate's
    threshold or the measured sensor value is absent.
  - score = matched_dimensions / assessed_dimensions
    score = 0.5 (neutral) when assessed_dimensions == 0.
  - is_compatible = assessed_dimensions > 0 and score >= 0.5
  - The current plant's species is excluded from results.
  - Results are sorted: score desc, then common_name asc (deterministic ties).

No LLM, no DB writes, no API, no migrations.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.domain.companion import (
    CompanionCandidate,
    CompatibilityResult,
    RoomEnvironment,
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _DimResult:
    matched: bool
    reason: str


def _fmt(value: float, spec: str) -> str:
    return format(value, spec)


def _assess_dimension(
    env_val: float | None,
    min_val: float | None,
    max_val: float | None,
    *,
    label: str,
    unit: str,
    spec: str,
) -> _DimResult | None:
    """Return a dimension assessment, or None if data is insufficient to compare."""
    if min_val is None or max_val is None:
        return None  # candidate has no threshold for this dimension
    if env_val is None:
        return None  # sensor value missing; skip silently

    matched = min_val <= env_val <= max_val
    env_str = f"{_fmt(env_val, spec)}{unit}"
    range_str = f"{_fmt(min_val, spec)}–{_fmt(max_val, spec)}{unit}"

    if matched:
        reason = f"{label} 적합 (현재 {env_str}, 적정 {range_str})"
    else:
        direction = "부족" if env_val < min_val else "과다"
        reason = f"{label} 부적합 — {direction} (현재 {env_str}, 적정 {range_str} 필요)"

    return _DimResult(matched=matched, reason=reason)


def _build_cautions(candidate: CompanionCandidate) -> list[str]:
    cautions: list[str] = []
    if candidate.is_toxic:
        cautions.append("독성 식물 — 취급 주의 필요")
    if candidate.toxic_to_pets:
        cautions.append("반려동물에게 유해할 수 있음")
    if candidate.toxic_to_children:
        cautions.append("어린이 접근 주의 필요")
    return cautions


def _calculate(
    candidate: CompanionCandidate,
    env: RoomEnvironment | None,
) -> tuple[float, int, list[str], list[str]]:
    """Return (score, assessed_dimensions, reasons, caution_notes)."""
    reasons: list[str] = []
    matched = 0
    assessed = 0

    if env is None:
        reasons.append("환경 스냅샷 없음 — 환경 조건 비교 불가")
    else:
        for result in (
            _assess_dimension(
                env.light_avg_lux,
                candidate.light_min_lux,
                candidate.light_max_lux,
                label="광요구도",
                unit="lux",
                spec=".0f",
            ),
            _assess_dimension(
                env.humidity_avg_pct,
                candidate.humidity_min_pct,
                candidate.humidity_max_pct,
                label="습도 조건",
                unit="%",
                spec=".0f",
            ),
            _assess_dimension(
                env.temperature_avg_c,
                candidate.temperature_min_c,
                candidate.temperature_max_c,
                label="온도 조건",
                unit="°C",
                spec=".1f",
            ),
        ):
            if result is not None:
                assessed += 1
                if result.matched:
                    matched += 1
                reasons.append(result.reason)

    score = (matched / assessed) if assessed > 0 else 0.5
    cautions = _build_cautions(candidate)
    return round(score, 4), assessed, reasons, cautions


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def filter_companions(
    candidates: list[CompanionCandidate],
    environment: RoomEnvironment | None,
    *,
    current_species_id: uuid.UUID | None = None,
    top_k: int = 10,
) -> list[CompatibilityResult]:
    """Filter and rank companion plant candidates by environmental compatibility.

    Args:
        candidates:          Pool of species to evaluate.
        environment:         Current room environment; None = no snapshot.
        current_species_id:  Species already owned — excluded from results.
        top_k:               Maximum results to return.

    Returns:
        Sorted list (score desc, common_name asc) of CompatibilityResult,
        at most top_k entries.
    """
    results: list[CompatibilityResult] = []

    for candidate in candidates:
        if current_species_id is not None and candidate.species_id == current_species_id:
            continue

        score, assessed, reasons, cautions = _calculate(candidate, environment)
        is_compatible = assessed > 0 and score >= 0.5

        results.append(
            CompatibilityResult(
                candidate=candidate,
                score=score,
                assessed_dimensions=assessed,
                reasons=tuple(reasons),
                caution_notes=tuple(cautions),
                is_compatible=is_compatible,
            )
        )

    results.sort(key=lambda r: (-r.score, r.candidate.common_name))
    return results[:top_k]
