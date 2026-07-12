"""@meta
name: late_stage_contract
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.stage-artifact-diagnostics
responsibility:
  - Shared late-stage status helpers for analysis/generation/pipeline consumers.
inputs:
  - late-stage status strings and ranked job payloads
outputs:
  - canonical status mappings and deterministic truth payloads
lifecycle:
  - status: active
"""

from __future__ import annotations

from typing import Any, Final, Literal

CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS = "blocked_by_reranker_fit"
CV_ANALYSIS_READY_FOR_GENERATION_STATUS = "ready_for_generation"
CV_ANALYSIS_SKIPPED_FIT_GATE_STATUS = "skipped_fit_gate"
CV_ANALYSIS_FAILED_STATUS = "analysis_failed"
CV_GENERATION_REVIEW_REQUIRED_STATUS = "review_required"
CV_GENERATION_ACCEPTED_STATUS: Final[Literal["accepted"]] = "accepted"
CV_GENERATION_VALIDATION_FAILED_STATUS: Final[Literal["validation_failed"]] = "validation_failed"
CV_GENERATION_FAILED_STATUS: Final[Literal["generation_failed"]] = "generation_failed"
CV_GENERATION_PERSISTENCE_FAILED_STATUS: Final[Literal["persistence_failed"]] = "persistence_failed"

AnalysisStatus = Literal[
    "blocked_by_reranker_fit",
    "ready_for_generation",
    "skipped_fit_gate",
    "analysis_failed",
]

GenerationStatus = Literal[
    "accepted",
    "validation_failed",
    "generation_failed",
    "blocked_by_reranker_fit",
    "skipped_fit_gate",
    "analysis_failed",
]

CV_GENERATION_FINAL_STATUSES: Final[frozenset[str]] = frozenset(
    {
        CV_GENERATION_ACCEPTED_STATUS,
        CV_GENERATION_REVIEW_REQUIRED_STATUS,
        CV_GENERATION_VALIDATION_FAILED_STATUS,
        CV_GENERATION_FAILED_STATUS,
        CV_GENERATION_PERSISTENCE_FAILED_STATUS,
    }
)


def shortlist_status_for_ranked_job(job: dict[str, Any]) -> str:
    shortlist_origin = str(job.get("shortlist_origin") or "").strip().lower()
    if shortlist_origin == "backfill":
        return "backfilled_for_scoring"
    return "returned_by_vector_search"


def validation_status_for_cv_status(status: str) -> str:
    if status == CV_GENERATION_ACCEPTED_STATUS:
        return CV_GENERATION_ACCEPTED_STATUS
    if status == CV_GENERATION_VALIDATION_FAILED_STATUS:
        return "failed"
    if status == CV_GENERATION_PERSISTENCE_FAILED_STATUS:
        return CV_GENERATION_ACCEPTED_STATUS
    return "not_run"


def deterministic_truth_fields(status: str | None) -> dict[str, str | None]:
    normalized_status = str(status or "").strip()
    if not normalized_status:
        return {
            "deterministic_outcome": None,
            "stage_owned_subreason": None,
            "source_stage": None,
        }
    if normalized_status == CV_GENERATION_ACCEPTED_STATUS:
        return {
            "deterministic_outcome": CV_GENERATION_ACCEPTED_STATUS,
            "stage_owned_subreason": normalized_status,
            "source_stage": "cv_generation",
        }
    if normalized_status == CV_GENERATION_REVIEW_REQUIRED_STATUS:
        return {
            "deterministic_outcome": "not_applicable",
            "stage_owned_subreason": normalized_status,
            "source_stage": "cv_generation",
        }
    if normalized_status in {
        CV_GENERATION_VALIDATION_FAILED_STATUS,
        CV_GENERATION_FAILED_STATUS,
        CV_GENERATION_PERSISTENCE_FAILED_STATUS,
    }:
        return {
            "deterministic_outcome": "rejected",
            "stage_owned_subreason": normalized_status,
            "source_stage": "cv_generation",
        }
    if normalized_status == CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS:
        return {
            "deterministic_outcome": "blocked",
            "stage_owned_subreason": normalized_status,
            "source_stage": "cv_analysis",
        }
    if normalized_status == CV_ANALYSIS_SKIPPED_FIT_GATE_STATUS:
        return {
            "deterministic_outcome": "skipped",
            "stage_owned_subreason": normalized_status,
            "source_stage": "cv_analysis",
        }
    if normalized_status == CV_ANALYSIS_FAILED_STATUS:
        return {
            "deterministic_outcome": "rejected",
            "stage_owned_subreason": normalized_status,
            "source_stage": "cv_analysis",
        }
    if normalized_status == CV_ANALYSIS_READY_FOR_GENERATION_STATUS:
        return {
            "deterministic_outcome": None,
            "stage_owned_subreason": normalized_status,
            "source_stage": "cv_analysis",
        }
    return {
        "deterministic_outcome": None,
        "stage_owned_subreason": None,
        "source_stage": None,
    }


def cv_generation_status_for_analysis_status(status: str) -> str:
    if status in {
        CV_ANALYSIS_READY_FOR_GENERATION_STATUS,
        CV_ANALYSIS_SKIPPED_FIT_GATE_STATUS,
        CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS,
        CV_ANALYSIS_FAILED_STATUS,
    }:
        return "not_attempted"
    return "failed"
