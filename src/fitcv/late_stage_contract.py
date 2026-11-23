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
CV_GENERATION_PDF_FAILED_STATUS: Final[Literal["pdf_failed"]] = "pdf_failed"
CV_GENERATION_ACCEPTED_STATUS: Final[Literal["accepted"]] = "accepted"
CV_GENERATION_VALIDATION_FAILED_STATUS: Final[Literal["validation_failed"]] = "validation_failed"
CV_GENERATION_FAILED_STATUS: Final[Literal["generation_failed"]] = "generation_failed"
CV_GENERATION_PERSISTENCE_FAILED_STATUS: Final[Literal["persistence_failed"]] = "persistence_failed"
CV_REVIEW_PENDING_STATUS = "pending"
CV_REVIEW_APPROVED_STATUS = "approved"
CV_REVIEW_REJECTED_STATUS = "rejected"
CV_PDF_PENDING_STATUS = "pending"
CV_PDF_PERSISTED_STATUS = "persisted"
CV_PDF_FAILED_STATUS = "failed"
CV_PERSISTENCE_PENDING_STATUS = "pending"
CV_PERSISTENCE_PERSISTED_STATUS = "persisted"
CV_PERSISTENCE_FAILED_STATUS = "failed"

AnalysisStatus = Literal[
    "blocked_by_reranker_fit",
    "ready_for_generation",
    "skipped_fit_gate",
    "analysis_failed",
]

GenerationStatus = Literal[
    "accepted",
    "review_required",
    "validation_failed",
    "generation_failed",
    "persistence_failed",
    "blocked_by_reranker_fit",
    "skipped_fit_gate",
    "analysis_failed",
]

CV_GENERATION_FINAL_STATUSES: Final[frozenset[str]] = frozenset(
    {
        CV_GENERATION_ACCEPTED_STATUS,
        CV_GENERATION_REVIEW_REQUIRED_STATUS,
        CV_GENERATION_PDF_FAILED_STATUS,
        CV_GENERATION_VALIDATION_FAILED_STATUS,
        CV_GENERATION_FAILED_STATUS,
        CV_GENERATION_PERSISTENCE_FAILED_STATUS,
    }
)
CV_GENERATION_ATTEMPTED_STATUSES: Final[frozenset[str]] = CV_GENERATION_FINAL_STATUSES
CV_GENERATION_NON_ACCEPTED_FINAL_STATUSES: Final[frozenset[str]] = frozenset(
    {
        CV_GENERATION_REVIEW_REQUIRED_STATUS,
        CV_GENERATION_PDF_FAILED_STATUS,
        CV_GENERATION_VALIDATION_FAILED_STATUS,
        CV_GENERATION_FAILED_STATUS,
        CV_GENERATION_PERSISTENCE_FAILED_STATUS,
    }
)
CV_ANALYSIS_FINAL_STATUSES: Final[frozenset[str]] = frozenset(
    {
        CV_ANALYSIS_READY_FOR_GENERATION_STATUS,
        CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS,
        CV_ANALYSIS_SKIPPED_FIT_GATE_STATUS,
        CV_ANALYSIS_FAILED_STATUS,
    }
)
CV_DEBUG_ANALYSIS_OMISSION_STATUSES: Final[frozenset[str]] = frozenset(
    {
        CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS,
        CV_ANALYSIS_SKIPPED_FIT_GATE_STATUS,
        CV_ANALYSIS_FAILED_STATUS,
    }
)


def shortlist_status_for_ranked_job(job: dict[str, Any]) -> str:
    return "returned_by_vector_search"


def validation_status_for_cv_status(status: str) -> str:
    if status == CV_GENERATION_ACCEPTED_STATUS:
        return CV_GENERATION_ACCEPTED_STATUS
    if status in {CV_GENERATION_VALIDATION_FAILED_STATUS, CV_GENERATION_FAILED_STATUS, CV_GENERATION_PERSISTENCE_FAILED_STATUS, CV_GENERATION_PDF_FAILED_STATUS}:
        return "failed"
    return "not_run"




def derive_submission_permission(row: dict[str, Any]) -> dict[str, Any]:
    """Derive submission permission from independent technical and review states."""
    generation_status = str(row.get("generation_status") or row.get("status") or "").strip()
    review_status = str(row.get("review_status") or "").strip().lower()
    pdf_status = str(row.get("pdf_status") or "").strip().lower()
    persistence_status = str(row.get("persistence_status") or "").strip().lower()
    mandatory_review = bool(row.get("mandatory_review") or row.get("review_required"))
    technical_ok = generation_status == CV_GENERATION_ACCEPTED_STATUS and not bool(row.get("technical_failure"))
    pdf_ok = pdf_status == CV_PDF_PERSISTED_STATUS or (not pdf_status and technical_ok)
    persisted = persistence_status == CV_PERSISTENCE_PERSISTED_STATUS or (not persistence_status and pdf_ok)
    review_ok = review_status == CV_REVIEW_APPROVED_STATUS or (not mandatory_review and review_status != CV_REVIEW_REJECTED_STATUS)
    permitted = technical_ok and pdf_ok and persisted and review_ok
    return {
        "submission_permitted": permitted,
        "submission_blockers": [
            reason for reason, blocked in (
                ("technical_failure", not technical_ok),
                ("pdf_failure", not pdf_ok),
                ("persistence_failure", not persisted),
                ("review_pending", not review_ok),
            ) if blocked
        ],
    }


def build_late_stage_state(
    *,
    generation_status: str,
    review_status: str | None = None,
    pdf_status: str | None = None,
    persistence_status: str | None = None,
    cv_revision: str | None = None,
    pdf_revision: str | None = None,
) -> dict[str, Any]:
    state = {
        "generation_status": str(generation_status or ""),
        "review_status": str(review_status or (CV_REVIEW_PENDING_STATUS if generation_status == CV_GENERATION_REVIEW_REQUIRED_STATUS else "none")),
        "pdf_status": str(pdf_status or (CV_PDF_PENDING_STATUS if generation_status in {CV_GENERATION_ACCEPTED_STATUS, CV_GENERATION_REVIEW_REQUIRED_STATUS} else CV_PDF_FAILED_STATUS)),
        "persistence_status": str(persistence_status or (CV_PERSISTENCE_PENDING_STATUS if generation_status in {CV_GENERATION_ACCEPTED_STATUS, CV_GENERATION_REVIEW_REQUIRED_STATUS} else CV_PERSISTENCE_FAILED_STATUS)),
        "cv_revision": str(cv_revision or ""),
        "pdf_revision": str(pdf_revision or ""),
    }
    state.update(derive_submission_permission(state))
    return state

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
        CV_GENERATION_PDF_FAILED_STATUS,
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


def canonical_pipeline_outcome_status(row: dict[str, Any]) -> str:
    pipeline_status = str(row.get("pipeline_status") or "").strip()
    if pipeline_status in {"ranked_with_cv", "ranked_no_cv", "ranked_blocked_by_reranker_fit", "ranked_skipped_fit_gate"}:
        return pipeline_status

    status = str(row.get("status") or "").strip()
    if status in {"ranked_with_cv", "ranked_no_cv", "ranked_blocked_by_reranker_fit", "ranked_skipped_fit_gate"}:
        return status

    source_stage = str(row.get("source_stage") or "").strip()
    stage_owned_subreason = str(row.get("stage_owned_subreason") or "").strip()
    deterministic_outcome = str(row.get("deterministic_outcome") or "").strip()

    if source_stage == "cv_generation" or status in CV_GENERATION_FINAL_STATUSES:
        if deterministic_outcome == CV_GENERATION_ACCEPTED_STATUS or status == CV_GENERATION_ACCEPTED_STATUS or stage_owned_subreason == CV_GENERATION_ACCEPTED_STATUS:
            return "ranked_with_cv"
        if status in CV_GENERATION_NON_ACCEPTED_FINAL_STATUSES:
            return "ranked_no_cv"
        if stage_owned_subreason in CV_GENERATION_NON_ACCEPTED_FINAL_STATUSES:
            return "ranked_no_cv"
        if deterministic_outcome in {"rejected", CV_GENERATION_REVIEW_REQUIRED_STATUS}:
            return "ranked_no_cv"

    if source_stage == "cv_analysis" or status in CV_ANALYSIS_FINAL_STATUSES:
        if status == CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS or stage_owned_subreason == CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS:
            return "ranked_blocked_by_reranker_fit"
        if status == CV_ANALYSIS_SKIPPED_FIT_GATE_STATUS or stage_owned_subreason == CV_ANALYSIS_SKIPPED_FIT_GATE_STATUS:
            return "ranked_skipped_fit_gate"
        if status in {CV_ANALYSIS_READY_FOR_GENERATION_STATUS, CV_ANALYSIS_FAILED_STATUS}:
            return "ranked_no_cv"
        if stage_owned_subreason in {CV_ANALYSIS_READY_FOR_GENERATION_STATUS, CV_ANALYSIS_FAILED_STATUS}:
            return "ranked_no_cv"

    return pipeline_status


def pipeline_outcome_surface(row: dict[str, Any]) -> dict[str, str]:
    pipeline_status = str(row.get("pipeline_status") or "")
    deterministic_outcome = str(row.get("deterministic_outcome") or "").strip()
    stage_owned_subreason = str(row.get("stage_owned_subreason") or "").strip()
    source_stage = str(row.get("source_stage") or "").strip()

    if source_stage == "cv_generation":
        if deterministic_outcome == CV_GENERATION_ACCEPTED_STATUS:
            return {"label": "CV created", "badge_class": "badge-success"}
        if stage_owned_subreason == CV_GENERATION_REVIEW_REQUIRED_STATUS:
            return {"label": "CV review required", "badge_class": "badge-warning"}
        if stage_owned_subreason == CV_GENERATION_PDF_FAILED_STATUS:
            return {"label": "CV PDF generation failed", "badge_class": "badge-error"}
        if stage_owned_subreason == CV_GENERATION_VALIDATION_FAILED_STATUS:
            return {"label": "CV validation failed", "badge_class": "badge-error"}
        if stage_owned_subreason == CV_GENERATION_FAILED_STATUS:
            return {"label": "CV generation failed", "badge_class": "badge-error"}
        if stage_owned_subreason == CV_GENERATION_PERSISTENCE_FAILED_STATUS:
            return {"label": "CV persistence failed", "badge_class": "badge-error"}

    if source_stage == "cv_analysis":
        if stage_owned_subreason == CV_ANALYSIS_READY_FOR_GENERATION_STATUS:
            return {"label": "Ready for CV generation", "badge_class": "badge-info"}
        if stage_owned_subreason == CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS:
            return {"label": "Ranked, blocked by reranker fit", "badge_class": "badge-warning"}
        if stage_owned_subreason == CV_ANALYSIS_SKIPPED_FIT_GATE_STATUS:
            return {"label": "Skipped after CV analysis", "badge_class": "badge-warning"}
        if stage_owned_subreason == CV_ANALYSIS_FAILED_STATUS:
            return {"label": "CV analysis failed", "badge_class": "badge-error"}

    return {
        "label": pipeline_status or "Unknown pipeline outcome",
        "badge_class": "badge-info",
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
