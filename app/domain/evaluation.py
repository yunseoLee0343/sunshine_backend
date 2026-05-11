"""Evaluation domain types — TICKET-034.

Pure data containers. No DB, no HTTP, no external calls.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Literal

AbTestGroup = Literal["control", "experiment"]


@dataclass(frozen=True)
class EvaluationMetrics:
    faithfulness: float          # 0.0–1.0: answer grounded in evidence
    answer_relevance: float      # 0.0–1.0: answer covers question keywords
    ground_truth_similarity: float  # 0.0–1.0: overlap with expected answer keywords


@dataclass(frozen=True)
class GroundTruthSpec:
    """In-memory ground truth entry (ORM-free)."""

    id: uuid.UUID
    question_keywords: list[str]
    expected_answer: str
    required_keywords: list[str]
    intent: str


@dataclass
class EvaluationResult:
    request_id: uuid.UUID
    ab_test_group: AbTestGroup
    metrics: EvaluationMetrics
    matched_ground_truth_id: uuid.UUID | None = None
