"""
@meta
type: test
scope: unit
domain: pipeline
covers:
  - status transition registry parity for deterministic truth and validation mapping
excludes:
  - live pipeline execution
tags:
  - fast
  - ci-safe
"""

from __future__ import annotations

import pytest

from fitcv.pipeline import (
    CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS,
    CV_ANALYSIS_FAILED_STATUS,
    CV_ANALYSIS_READY_FOR_GENERATION_STATUS,
    CV_ANALYSIS_SKIPPED_FIT_GATE_STATUS,
    CV_GENERATION_REVIEW_REQUIRED_STATUS,
    _cv_generation_status_for_analysis_status,
    _deterministic_truth_fields,
    _validation_status_for_cv_status,
)


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("accepted", {"deterministic_outcome": "accepted", "stage_owned_subreason": "accepted", "source_stage": "cv_generation"}),
        (CV_GENERATION_REVIEW_REQUIRED_STATUS, {"deterministic_outcome": "not_applicable", "stage_owned_subreason": CV_GENERATION_REVIEW_REQUIRED_STATUS, "source_stage": "cv_generation"}),
        ("validation_failed", {"deterministic_outcome": "rejected", "stage_owned_subreason": "validation_failed", "source_stage": "cv_generation"}),
        ("generation_failed", {"deterministic_outcome": "rejected", "stage_owned_subreason": "generation_failed", "source_stage": "cv_generation"}),
        ("persistence_failed", {"deterministic_outcome": "rejected", "stage_owned_subreason": "persistence_failed", "source_stage": "cv_generation"}),
        (CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS, {"deterministic_outcome": "blocked", "stage_owned_subreason": CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS, "source_stage": "cv_analysis"}),
        (CV_ANALYSIS_SKIPPED_FIT_GATE_STATUS, {"deterministic_outcome": "skipped", "stage_owned_subreason": CV_ANALYSIS_SKIPPED_FIT_GATE_STATUS, "source_stage": "cv_analysis"}),
        (CV_ANALYSIS_FAILED_STATUS, {"deterministic_outcome": "rejected", "stage_owned_subreason": CV_ANALYSIS_FAILED_STATUS, "source_stage": "cv_analysis"}),
        (CV_ANALYSIS_READY_FOR_GENERATION_STATUS, {"deterministic_outcome": None, "stage_owned_subreason": CV_ANALYSIS_READY_FOR_GENERATION_STATUS, "source_stage": "cv_analysis"}),
        ("", {"deterministic_outcome": None, "stage_owned_subreason": None, "source_stage": None}),
    ],
)
def test_deterministic_truth_fields_registry_parity(status: str, expected: dict[str, str | None]) -> None:
    assert _deterministic_truth_fields(status) == expected


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("accepted", "accepted"),
        ("validation_failed", "failed"),
        ("persistence_failed", "accepted"),
        ("review_required", "not_run"),
        ("generation_failed", "not_run"),
    ],
)
def test_validation_status_for_cv_status_parity(status: str, expected: str) -> None:
    assert _validation_status_for_cv_status(status) == expected


@pytest.mark.parametrize(
    ("analysis_status", "expected"),
    [
        (CV_ANALYSIS_READY_FOR_GENERATION_STATUS, "not_attempted"),
        (CV_ANALYSIS_SKIPPED_FIT_GATE_STATUS, "not_attempted"),
        (CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS, "not_attempted"),
        (CV_ANALYSIS_FAILED_STATUS, "not_attempted"),
        ("unexpected_status", "failed"),
    ],
)
def test_cv_generation_status_for_analysis_status_parity(analysis_status: str, expected: str) -> None:
    assert _cv_generation_status_for_analysis_status(analysis_status) == expected
