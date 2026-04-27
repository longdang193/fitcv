"""
@meta
name: agentic_cv_analysis
type: adapter
domain: cv_analysis
responsibility:
  - Adapt one ranked FitCV job into a pipeline-shaped CV analysis record.
  - Preserve original FitCV fit-gate and evidence or gap semantics for later pipeline integration.
inputs:
  - one ranked or enriched job row
  - candidate profile data
  - FitCV runtime config
outputs:
  - CV analysis record compatible with pipeline stage expectations
capabilities:
  - cv_system.agentic-analysis-adapter
tags:
  - cv
  - analysis
  - adapter
lifecycle:
  status: active
"""

from typing import Any, Final, Literal, TypedDict, cast

from fitcv.candidate import flatten_skills
from fitcv.evidence import (
    build_cv_analysis_input_fingerprint,
    retrieve_evidence,
    retrieve_evidence_bundle,
)
from fitcv.gap_analysis import compute_gap

BLOCKED_BY_RERANKER_STATUS: Final[Literal["blocked_by_reranker_fit"]] = "blocked_by_reranker_fit"
READY_FOR_GENERATION_STATUS: Final[Literal["ready_for_generation"]] = "ready_for_generation"
SKIPPED_FIT_GATE_STATUS: Final[Literal["skipped_fit_gate"]] = "skipped_fit_gate"
ANALYSIS_FAILED_STATUS: Final[Literal["analysis_failed"]] = "analysis_failed"

_FIT_LABEL_ORDER = {"strong", "stretch", "skip"}

AnalysisStatus = Literal[
    "blocked_by_reranker_fit",
    "ready_for_generation",
    "skipped_fit_gate",
    "analysis_failed",
]
FitClassification = Literal["strong", "stretch", "skip"]


class ErrorPayload(TypedDict):
    stage: str
    message: str


class CvAnalysisRecord(TypedDict, total=False):
    job_url: str
    job_title: str
    status: AnalysisStatus
    analysis_input_fingerprint: str | None
    analysis_reuse_status: str
    ranking_fit_label: str | None
    fit_classification: FitClassification | None
    decision_chain: dict[str, Any]
    job_snapshot: dict[str, Any]
    evidence_payload: list[dict[str, Any]]
    evidence_used: list[dict[str, Any]]
    evidence_selection_summary: dict[str, Any]
    gap_summary: dict[str, Any] | None
    outcome_reason: ErrorPayload | None
    error: ErrorPayload | None


def extract_job_url(job: dict[str, Any]) -> str:
    return str(job.get("job_url") or job.get("jobUrl") or "")


def extract_job_title(job: dict[str, Any]) -> str:
    return str(job.get("title") or job.get("job_title") or "")


def build_evidence_used(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    debug_evidence: list[dict[str, Any]] = []
    for item in evidence:
        debug_item: dict[str, Any] = {
            "evidence_type": str(item.get("evidence_type") or ""),
            "source_ref": str(item.get("source_ref") or ""),
            "name": str(item.get("name") or ""),
            "matched_channels": list(item.get("matched_channels") or []),
            "selection_reasons": list(item.get("selection_reasons") or []),
        }
        channel_subscores = dict(item.get("channel_subscores") or {})
        semantic_alignment = dict(item.get("semantic_alignment") or {})
        if channel_subscores:
            debug_item["channel_subscores"] = channel_subscores
        if semantic_alignment:
            debug_item["semantic_alignment"] = semantic_alignment
        debug_evidence.append(
            {key: value for key, value in debug_item.items() if value not in ("", None)}
        )
    return debug_evidence


def build_analysis_input_summary(job: dict[str, Any]) -> dict[str, Any]:
    summary = {
        "required_skills": list(job.get("required_skills") or []),
        "preferred_skills": list(job.get("preferred_skills") or []),
        "responsibilities": list(job.get("responsibilities") or []),
        "job_family": str(job.get("job_family") or ""),
        "domain": str(job.get("domain") or ""),
        "location_type": str(job.get("location_type") or ""),
    }
    return {
        key: value
        for key, value in summary.items()
        if value not in (None, "", [])
    }


def _fit_label_from_ai_score(score: float, config: dict[str, Any]) -> FitClassification:
    thresholds = dict(config.get("fit_label_thresholds") or {})
    strong_threshold = float(thresholds.get("strong", 0.70))
    stretch_threshold = float(thresholds.get("stretch", 0.40))
    if score >= strong_threshold:
        return "strong"
    if score >= stretch_threshold:
        return "stretch"
    return "skip"


def resolve_ranked_job_fit(job: dict[str, Any], config: dict[str, Any]) -> FitClassification:
    ranked_fit_raw = str(job.get("fit_label") or "").strip().lower()
    if ranked_fit_raw in _FIT_LABEL_ORDER:
        return cast(FitClassification, ranked_fit_raw)
    raw_ai_score = job.get("ai_score")
    if raw_ai_score is None:
        return "skip"
    return _fit_label_from_ai_score(float(raw_ai_score), config)


def _shortlist_status_for_ranked_job(job: dict[str, Any]) -> str:
    shortlist_origin = str(job.get("shortlist_origin") or "").strip().lower()
    if shortlist_origin == "backfill":
        return "backfilled_for_scoring"
    return "returned_by_vector_search"


def _validation_status_for_cv_status(status: str) -> str:
    if status == "accepted":
        return "accepted"
    if status == "validation_failed":
        return "failed"
    if status == "persistence_failed":
        return "accepted"
    return "not_run"


def build_decision_chain(
    *,
    job: dict[str, Any],
    fit_classification: FitClassification | None,
    cv_analysis_status: str,
    cv_status: str,
) -> dict[str, Any]:
    ranking_fit_label = str(fit_classification or "").strip() or None
    ranking_fit_source = str(job.get("fit_label_source") or "reranker").strip() or None
    return {
        "shortlist": {
            "status": _shortlist_status_for_ranked_job(job),
            "advanced_to_scoring": True,
        },
        "primary_fit": {
            "source": ranking_fit_source,
            "label": ranking_fit_label,
        },
        "cv_analysis": {
            "status": cv_analysis_status,
            "completed": cv_analysis_status not in {"not_run", "failed", BLOCKED_BY_RERANKER_STATUS},
        },
        "cv_generation": {
            "status": cv_status,
            "attempted": cv_status not in {"not_applicable", "not_attempted", SKIPPED_FIT_GATE_STATUS},
        },
        "validation": {
            "status": _validation_status_for_cv_status(cv_status),
        },
    }


def build_cv_analysis_record(
    *,
    job: dict[str, Any],
    status: AnalysisStatus,
    analysis_input_fingerprint: str | None,
    analysis_reuse_status: str,
    evidence_payload: list[dict[str, Any]],
    evidence_selection_summary: dict[str, Any] | None,
    gap_summary: dict[str, Any] | None,
    fit_classification: FitClassification | None,
    error: ErrorPayload | None,
) -> CvAnalysisRecord:
    if status == READY_FOR_GENERATION_STATUS:
        cv_status = "not_attempted"
    elif status == SKIPPED_FIT_GATE_STATUS:
        cv_status = SKIPPED_FIT_GATE_STATUS
    elif status == BLOCKED_BY_RERANKER_STATUS:
        cv_status = "not_attempted"
    else:
        cv_status = "failed"

    evidence_used = build_evidence_used(evidence_payload)
    return {
        "job_url": extract_job_url(job),
        "job_title": extract_job_title(job),
        "status": status,
        "analysis_input_fingerprint": analysis_input_fingerprint,
        "analysis_reuse_status": analysis_reuse_status,
        "ranking_fit_label": str(fit_classification or "").strip() or None,
        "fit_classification": fit_classification,
        "decision_chain": build_decision_chain(
            job=job,
            fit_classification=fit_classification,
            cv_analysis_status=status,
            cv_status=cv_status,
        ),
        "job_snapshot": dict(job),
        "evidence_payload": list(evidence_payload),
        "evidence_used": evidence_used,
        "evidence_selection_summary": dict(evidence_selection_summary or {}),
        "gap_summary": gap_summary,
        "outcome_reason": error if status in {SKIPPED_FIT_GATE_STATUS, BLOCKED_BY_RERANKER_STATUS} else None,
        "error": error if status not in {SKIPPED_FIT_GATE_STATUS, BLOCKED_BY_RERANKER_STATUS} else None,
    }


def is_generation_ready(record: dict[str, Any]) -> bool:
    return str(record.get("status") or "") == READY_FOR_GENERATION_STATUS


def _candidate_skill_names(profile: dict[str, Any]) -> list[str]:
    candidate_skills = flatten_skills(profile)
    if candidate_skills:
        return candidate_skills
    return [
        str(skill)
        for skill in list(profile.get("skills") or [])
        if skill
    ]


def _compact_mapping(mapping: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in mapping.items()
        if value not in ({}, [], None)
    }


def _build_evidence_selection_summary(
    evidence_bundle: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    return _compact_mapping(
        {
            "channel_counts": dict(evidence_bundle.get("channel_counts") or {}),
            "effective_channel_pool_size": int(evidence_bundle.get("effective_channel_pool_size") or 0),
            "merged_pool_size": int(evidence_bundle.get("merged_pool_size") or 0),
            "deduped_pool_size": int(evidence_bundle.get("deduped_pool_size") or 0),
            "selected_evidence_count": len(evidence),
            "selected_evidence_ids": list(evidence_bundle.get("selected_evidence_ids") or []),
            "unselected_top_candidates": list(evidence_bundle.get("unselected_top_candidates") or []),
            "hybrid_alignment": dict(evidence_bundle.get("hybrid_alignment") or {}),
            "semantic_alignment": dict(evidence_bundle.get("semantic_alignment") or {}),
        }
    )


def analyze_ranked_job(
    job: dict[str, Any],
    profile: dict[str, Any],
    config: dict[str, Any],
    *,
    top_k: int | None = None,
) -> CvAnalysisRecord:
    ranking_fit_label = resolve_ranked_job_fit(job, config)
    if ranking_fit_label == "skip":
        return build_cv_analysis_record(
            job=job,
            status=BLOCKED_BY_RERANKER_STATUS,
            analysis_input_fingerprint=None,
            analysis_reuse_status="not_run_reranker_skip",
            evidence_payload=[],
            evidence_selection_summary=None,
            gap_summary=None,
            fit_classification=ranking_fit_label,
            error={
                "stage": "reranker_fit",
                "message": f"Blocked {extract_job_url(job)} before CV analysis (reranker fit=skip)",
            },
        )

    analysis_fingerprint_record = build_cv_analysis_input_fingerprint(profile, job, config)
    evidence: list[dict[str, Any]] = []
    evidence_selection_summary: dict[str, Any] = {}
    gap_summary: dict[str, Any] | None = None
    try:
        evidence_top_k = int(top_k if top_k is not None else config["pipeline"]["evidence_top_k"])
        evidence_bundle = retrieve_evidence_bundle(
            profile,
            job,
            top_k=evidence_top_k,
            config=config,
        )
        evidence = list(evidence_bundle.get("selected_evidence") or [])
        evidence_selection_summary = _build_evidence_selection_summary(evidence_bundle, evidence)

        if not evidence:
            evidence = retrieve_evidence(profile, job, top_k=evidence_top_k)
            if evidence:
                evidence_selection_summary = _compact_mapping(
                    {
                        "channel_counts": evidence_selection_summary.get("channel_counts") or {},
                        "effective_channel_pool_size": int(
                            evidence_selection_summary.get("effective_channel_pool_size") or 0
                        ),
                        "merged_pool_size": max(
                            len(evidence),
                            int(evidence_selection_summary.get("merged_pool_size") or 0),
                        ),
                        "deduped_pool_size": max(
                            len(evidence),
                            int(evidence_selection_summary.get("deduped_pool_size") or 0),
                        ),
                        "selected_evidence_count": len(evidence),
                        "selected_evidence_ids": [str(item.get("evidence_id") or "") for item in evidence],
                        "unselected_top_candidates": list(
                            evidence_selection_summary.get("unselected_top_candidates") or []
                        ),
                        "hybrid_alignment": dict(evidence_selection_summary.get("hybrid_alignment") or {}),
                        "semantic_alignment": dict(evidence_selection_summary.get("semantic_alignment") or {}),
                    }
                )

        gap_summary = compute_gap(
            required_skills=job.get("required_skills") or [],
            candidate_skills=_candidate_skill_names(profile),
            years_experience_min=job.get("years_experience_min"),
            years_experience_max=job.get("years_experience_max"),
            years_candidate=profile.get("years_experience"),
            config=config,
        )

        fit_classification = resolve_ranked_job_fit(job, config)
        if fit_classification == "skip":
            return build_cv_analysis_record(
                job=job,
                status=SKIPPED_FIT_GATE_STATUS,
                analysis_input_fingerprint=str(analysis_fingerprint_record["fingerprint"]),
                analysis_reuse_status="fresh_compute",
                evidence_payload=evidence,
                evidence_selection_summary=evidence_selection_summary,
                gap_summary=gap_summary,
                fit_classification=fit_classification,
                error={
                    "stage": "fit_gate",
                    "message": f"Skipped {extract_job_url(job)} (fit=skip)",
                },
            )

        return build_cv_analysis_record(
            job=job,
            status=READY_FOR_GENERATION_STATUS,
            analysis_input_fingerprint=str(analysis_fingerprint_record["fingerprint"]),
            analysis_reuse_status="fresh_compute",
            evidence_payload=evidence,
            evidence_selection_summary=evidence_selection_summary,
            gap_summary=gap_summary,
            fit_classification=fit_classification,
            error=None,
        )
    except Exception as exc:
        return build_cv_analysis_record(
            job=job,
            status=ANALYSIS_FAILED_STATUS,
            analysis_input_fingerprint=str(analysis_fingerprint_record["fingerprint"]),
            analysis_reuse_status="fresh_compute",
            evidence_payload=evidence,
            evidence_selection_summary=evidence_selection_summary,
            gap_summary=gap_summary,
            fit_classification=ranking_fit_label,
            error={
                "stage": "analysis",
                "message": str(exc),
            },
        )
