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

from enum import Enum
from typing import Any, Final, Literal

CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS = "blocked_by_reranker_fit"
CV_ANALYSIS_READY_FOR_GENERATION_STATUS = "ready_for_generation"
CV_ANALYSIS_SKIPPED_FIT_GATE_STATUS = "skipped_fit_gate"
CV_ANALYSIS_FAILED_STATUS = "analysis_failed"
CV_ANALYSIS_HANDOFF_CONTRACT_FAILED_STATUS = "handoff_contract_failed"
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

CV_CONTENT_VALIDITY_PENDING = "pending"
CV_CONTENT_VALID = "valid"
CV_CONTENT_INVALID = "invalid"
CV_CONTENT_PROVENANCE_UNAVAILABLE = "provenance_unavailable"
CV_TECHNICAL_PENDING = "pending"
CV_TECHNICAL_COMPLETE = "complete"
CV_TECHNICAL_FAILED = "failed"
CV_TECHNICAL_NOT_ATTEMPTED = "not_attempted"
CV_DRAFT_ACCEPTED = "accepted"
CV_DRAFT_QUARANTINED = "quarantined"
CV_DRAFT_UNAVAILABLE = "unavailable"
CV_REVIEW_NOT_REQUIRED = "not_required"
CV_PDF_VERIFIED = "verified"
CV_PERSISTENCE_NOT_ATTEMPTED = "not_attempted"
CV_SUBMISSION_BLOCKED = "blocked"
CV_SUBMISSION_ELIGIBLE = "eligible"


class LifecycleDimension(str, Enum):
    CONTENT_VALIDITY = "content_validity"
    TECHNICAL_GENERATION = "technical_generation"
    DRAFT_DISPOSITION = "draft_disposition"
    REVIEW = "review"
    PDF_ARTIFACT = "pdf_artifact"
    PERSISTENCE = "persistence"
    SUBMISSION_CLEARANCE = "submission_clearance"


LIFECYCLE_DIMENSIONS: Final[tuple[str, ...]] = tuple(item.value for item in LifecycleDimension)


def _lifecycle_row(row: dict[str, Any]) -> dict[str, Any]:
    nested = row.get("lifecycle_dimensions") or row.get("lifecycle")
    if isinstance(nested, dict):
        return {**nested, **row}
    return row


def _normalized_value(row: dict[str, Any], key: str) -> str:
    return str(row.get(key) or "").strip().lower()


def derive_lifecycle_dimensions(row: dict[str, Any]) -> dict[str, str]:
    """Project legacy late-stage fields into independent lifecycle dimensions."""
    row = _lifecycle_row(row)
    generation_status = str(row.get("generation_status") or row.get("status") or "").strip().lower()
    validation = row.get("validation") or row.get("validation_result") or {}
    if "content_validity" in row:
        content = _normalized_value(row, "content_validity")
    elif isinstance(validation, dict) and validation.get("valid") is True:
        content = CV_CONTENT_VALID
    elif isinstance(validation, dict) and validation.get("valid") is False:
        content = CV_CONTENT_INVALID
    elif generation_status == CV_GENERATION_ACCEPTED_STATUS:
        content = CV_CONTENT_VALID
    elif generation_status in {CV_GENERATION_VALIDATION_FAILED_STATUS, CV_GENERATION_FAILED_STATUS}:
        content = CV_CONTENT_INVALID
    else:
        content = CV_CONTENT_VALIDITY_PENDING

    technical = _normalized_value(row, "technical_generation")
    if not technical:
        if generation_status in {CV_GENERATION_ACCEPTED_STATUS, "generated", "complete", "completed"}:
            technical = CV_TECHNICAL_COMPLETE
        elif generation_status in CV_GENERATION_FINAL_STATUSES or generation_status in {"failed", "error"}:
            technical = CV_TECHNICAL_FAILED
        elif generation_status in {"pending", "running", ""}:
            technical = CV_TECHNICAL_PENDING if generation_status else CV_TECHNICAL_NOT_ATTEMPTED
        else:
            technical = CV_TECHNICAL_FAILED

    draft = _normalized_value(row, "draft_disposition")
    if not draft:
        if row.get("draft_disposition") == "":
            draft = CV_DRAFT_UNAVAILABLE
        elif generation_status in {CV_GENERATION_ACCEPTED_STATUS, CV_GENERATION_REVIEW_REQUIRED_STATUS, "generated", "complete", "completed"}:
            draft = CV_DRAFT_ACCEPTED
        elif generation_status in {CV_GENERATION_VALIDATION_FAILED_STATUS, "validation_failed"} and (
            row.get("structured_cv_final")
            or row.get("markdown_final")
            or row.get("quarantined_structured_cv")
            or row.get("quarantined_markdown")
        ):
            draft = CV_DRAFT_QUARANTINED
        else:
            draft = CV_DRAFT_UNAVAILABLE

    review = _normalized_value(row, "review") or _normalized_value(row, "review_status")
    mandatory_review = bool(row.get("mandatory_review") or row.get("review_required"))
    if not review or review == "none":
        review = CV_REVIEW_PENDING_STATUS if mandatory_review else CV_REVIEW_NOT_REQUIRED
    elif review == "reviewed":
        review = CV_REVIEW_APPROVED_STATUS

    pdf = _normalized_value(row, "pdf_artifact") or _normalized_value(row, "pdf_status")
    if pdf in {"generated", "pass", "passed", "accepted", CV_PDF_PERSISTED_STATUS}:
        pdf = CV_PDF_VERIFIED
    elif pdf in {"fail", "failed", "error"}:
        pdf = CV_PDF_FAILED_STATUS
    elif not pdf:
        pdf = CV_PDF_PENDING_STATUS if generation_status in {CV_GENERATION_ACCEPTED_STATUS, CV_GENERATION_REVIEW_REQUIRED_STATUS, "generated", "complete", "completed"} else CV_TECHNICAL_NOT_ATTEMPTED

    persistence = _normalized_value(row, "persistence") or _normalized_value(row, "persistence_status")
    if persistence in {"saved", "success", "successful", CV_PERSISTENCE_PERSISTED_STATUS}:
        persistence = CV_PERSISTENCE_PERSISTED_STATUS
    elif persistence in {"fail", "failed", "error"}:
        persistence = CV_PERSISTENCE_FAILED_STATUS
    elif not persistence:
        persistence = CV_PERSISTENCE_PENDING_STATUS if generation_status in {CV_GENERATION_ACCEPTED_STATUS, CV_GENERATION_REVIEW_REQUIRED_STATUS, "generated", "complete", "completed"} else CV_PERSISTENCE_NOT_ATTEMPTED

    return {
        LifecycleDimension.CONTENT_VALIDITY.value: content,
        LifecycleDimension.TECHNICAL_GENERATION.value: technical,
        LifecycleDimension.DRAFT_DISPOSITION.value: draft,
        LifecycleDimension.REVIEW.value: review,
        LifecycleDimension.PDF_ARTIFACT.value: pdf,
        LifecycleDimension.PERSISTENCE.value: persistence,
    }


def derive_submission_clearance(row: dict[str, Any]) -> dict[str, Any]:
    """Derive submission eligibility only from lifecycle dimensions and page-fit gates."""
    row = _lifecycle_row(row)
    dimensions = derive_lifecycle_dimensions(row)
    blockers: list[str] = []
    required = (
        (LifecycleDimension.TECHNICAL_GENERATION.value, dimensions[LifecycleDimension.TECHNICAL_GENERATION.value] != CV_TECHNICAL_COMPLETE),
        (LifecycleDimension.CONTENT_VALIDITY.value, dimensions[LifecycleDimension.CONTENT_VALIDITY.value] != CV_CONTENT_VALID),
        (LifecycleDimension.DRAFT_DISPOSITION.value, dimensions[LifecycleDimension.DRAFT_DISPOSITION.value] != CV_DRAFT_ACCEPTED),
        (LifecycleDimension.PDF_ARTIFACT.value, dimensions[LifecycleDimension.PDF_ARTIFACT.value] != CV_PDF_VERIFIED),
        (LifecycleDimension.PERSISTENCE.value, dimensions[LifecycleDimension.PERSISTENCE.value] != CV_PERSISTENCE_PERSISTED_STATUS),
    )
    blockers.extend(name for name, blocked in required if blocked)
    mandatory_review = bool(row.get("mandatory_review") or row.get("review_required"))
    review = dimensions[LifecycleDimension.REVIEW.value]
    if mandatory_review and review != CV_REVIEW_APPROVED_STATUS:
        blockers.append(LifecycleDimension.REVIEW.value)
    elif not mandatory_review and review == CV_REVIEW_REJECTED_STATUS:
        blockers.append(LifecycleDimension.REVIEW.value)

    page_fit_required = bool(row.get("page_fit_required") or row.get("page_fit_gate_required"))
    page_fit = _normalized_value(row, "page_fit_status") or _normalized_value(row, "page_fit")
    if page_fit in {"fail", "failed", "blocked", "overflow"} or row.get("page_fit_passed") is False:
        blockers.append("page_fit")
    elif page_fit_required and page_fit not in {"pass", "passed", "verified", "accepted"}:
        blockers.append("page_fit")

    diagnostics = row.get("diagnostics")
    if isinstance(diagnostics, dict):
        diagnostics = diagnostics.get("diagnostics") or []
    if isinstance(diagnostics, (list, tuple)):
        try:
            from fitcv.pipeline_contracts import dedupe_diagnostics
            if any(bool(item.get("blocking")) for item in dedupe_diagnostics(diagnostics) if isinstance(item, dict)):
                blockers.append("diagnostic")
        except (ImportError, TypeError, ValueError):
            if diagnostics:
                blockers.append("diagnostic")

    blockers = list(dict.fromkeys(blockers))
    clearance = CV_SUBMISSION_ELIGIBLE if not blockers else CV_SUBMISSION_BLOCKED
    return {
        LifecycleDimension.SUBMISSION_CLEARANCE.value: clearance,
        "submission_permitted": clearance == CV_SUBMISSION_ELIGIBLE,
        "submission_blockers": blockers,
        "submission_clearance_blockers": blockers,
        "lifecycle_dimensions": dimensions,
    }


AnalysisStatus = Literal[
    "blocked_by_reranker_fit",
    "ready_for_generation",
    "skipped_fit_gate",
    "analysis_failed",
    "handoff_contract_failed",
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
    "handoff_contract_failed",
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
        CV_ANALYSIS_HANDOFF_CONTRACT_FAILED_STATUS,
    }
)
CV_DEBUG_ANALYSIS_OMISSION_STATUSES: Final[frozenset[str]] = frozenset(
    {
        CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS,
        CV_ANALYSIS_SKIPPED_FIT_GATE_STATUS,
        CV_ANALYSIS_FAILED_STATUS,
        CV_ANALYSIS_HANDOFF_CONTRACT_FAILED_STATUS,
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
    """Return the legacy permission projection plus derived lifecycle clearance."""
    # Keep the old sparse-row behavior for historical callers that supplied no
    # lifecycle or artifact gate fields; new rows use the strict derived path.
    legacy_keys = {"pdf_status", "persistence_status", "content_validity", "technical_generation", "draft_disposition", "review", "page_fit_status", "page_fit"}
    if not any(key in row for key in legacy_keys):
        generation_status = str(row.get("generation_status") or row.get("status") or "").strip()
        review_status = str(row.get("review_status") or "").strip().lower()
        mandatory_review = bool(row.get("mandatory_review") or row.get("review_required"))
        technical_ok = generation_status == CV_GENERATION_ACCEPTED_STATUS and not bool(row.get("technical_failure"))
        review_ok = review_status == CV_REVIEW_APPROVED_STATUS or (not mandatory_review and review_status != CV_REVIEW_REJECTED_STATUS)
        blockers = [name for name, blocked in (("technical_failure", not technical_ok), ("review_pending", not review_ok)) if blocked]
        result = {"submission_permitted": technical_ok and review_ok, "submission_blockers": blockers}
        result[LifecycleDimension.SUBMISSION_CLEARANCE.value] = CV_SUBMISSION_ELIGIBLE if result["submission_permitted"] else CV_SUBMISSION_BLOCKED
        result["submission_clearance_blockers"] = blockers
        result["lifecycle_dimensions"] = derive_lifecycle_dimensions(row)
        return result
    return derive_submission_clearance(row)


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
    state.update(derive_lifecycle_dimensions(state))
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
    if normalized_status == CV_ANALYSIS_HANDOFF_CONTRACT_FAILED_STATUS:
        return {
            "deterministic_outcome": "rejected",
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
        if status in {CV_ANALYSIS_READY_FOR_GENERATION_STATUS, CV_ANALYSIS_FAILED_STATUS, CV_ANALYSIS_HANDOFF_CONTRACT_FAILED_STATUS}:
            return "ranked_no_cv"
        if stage_owned_subreason in {CV_ANALYSIS_READY_FOR_GENERATION_STATUS, CV_ANALYSIS_FAILED_STATUS, CV_ANALYSIS_HANDOFF_CONTRACT_FAILED_STATUS}:
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
        if stage_owned_subreason == CV_ANALYSIS_HANDOFF_CONTRACT_FAILED_STATUS:
            return {"label": "CV handoff contract failed", "badge_class": "badge-error"}

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
        CV_ANALYSIS_HANDOFF_CONTRACT_FAILED_STATUS,
    }:
        return "not_attempted"
    return "failed"
