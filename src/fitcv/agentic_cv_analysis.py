"""@meta
name: agentic_cv_analysis
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.stage-artifact-diagnostics
responsibility:
  - Module metadata placeholder for src.fitcv.agentic_cv_analysis.
inputs:
  - Internal runtime calls and module imports
outputs:
  - Module-level symbols and runtime behavior
lifecycle:
  - status: active
"""

import hashlib
import json
import math
import time
from collections.abc import Mapping
from typing import Any, Literal, TypedDict, cast

from fitcv.candidate import flatten_skills
from fitcv.config import get_stage_runtime_sleep_secs
from fitcv.contracts import normalize_analysis_channel_mapping
from fitcv.evidence import (
    build_cv_analysis_input_fingerprint,
    retrieve_evidence,
    retrieve_evidence_bundle,
)
from fitcv.gap_analysis import compute_gap
from fitcv.pipeline_stages.common import job_identity_keys
from fitcv.reuse import build_reuse_decision
from fitcv.late_stage_contract import (
    AnalysisStatus,
    CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS as BLOCKED_BY_RERANKER_STATUS,
    CV_ANALYSIS_FAILED_STATUS as ANALYSIS_FAILED_STATUS,
    CV_ANALYSIS_READY_FOR_GENERATION_STATUS as READY_FOR_GENERATION_STATUS,
    CV_ANALYSIS_SKIPPED_FIT_GATE_STATUS as SKIPPED_FIT_GATE_STATUS,
    cv_generation_status_for_analysis_status,
    shortlist_status_for_ranked_job,
    validation_status_for_cv_status,
)
from fitcv.ranking_contract import fit_label_from_score

_FIT_LABEL_ORDER = {"strong", "stretch", "skip"}
FitClassification = Literal["strong", "stretch", "skip"]


class ErrorPayload(TypedDict):
    stage: str
    message: str


class CvAnalysisRecord(TypedDict, total=False):
    raw_job_fingerprint: str
    job_url: str
    job_title: str
    status: AnalysisStatus
    analysis_input_fingerprint: str | None
    analysis_input_components: dict[str, Any]
    analysis_reuse_status: str
    reuse_decision: dict[str, Any]
    ranking_fit_label: str | None
    fit_classification: FitClassification | None
    decision_chain: dict[str, Any]
    job_snapshot: dict[str, Any]
    evidence_payload: list[dict[str, Any]]
    evidence_used: list[dict[str, Any]]
    evidence_selection_summary: dict[str, Any]
    gap_summary: dict[str, Any] | None
    requirement_coverage: list[dict[str, Any]]
    section_confidence_hints: dict[str, str]
    do_not_claim: list[str]
    outcome_reason: ErrorPayload | None
    error: ErrorPayload | None
    cv_analysis_trace: dict[str, Any]


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
    required_skills = list(job.get("required_skills_canonical") or [])
    if not required_skills:
        required_skills = list(job.get("required_skills") or [])

    preferred_skills = list(job.get("preferred_skills_canonical") or [])
    if not preferred_skills:
        preferred_skills = list(job.get("preferred_skills") or [])

    summary = {
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
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

def _fit_label_from_baseline_score(score: float, config: dict[str, Any]) -> FitClassification:
    return cast(FitClassification, fit_label_from_score(score, config))


def resolve_ranked_job_fit(job: dict[str, Any], config: dict[str, Any]) -> FitClassification:
    ranked_fit_raw = str(job.get("baseline_fit_label") or "").strip().lower()
    if ranked_fit_raw in _FIT_LABEL_ORDER:
        return cast(FitClassification, ranked_fit_raw)
    raw_baseline_fit = job.get("baseline_fit")
    if raw_baseline_fit is None:
        return "skip"
    try:
        baseline_fit = float(raw_baseline_fit)
    except (TypeError, ValueError):
        return "skip"
    if not math.isfinite(baseline_fit):
        return "skip"
    return _fit_label_from_baseline_score(baseline_fit, config)




def _authoritative_ranking_fit_label(
    job: dict[str, Any],
    fit_classification: FitClassification | None,
) -> FitClassification | None:
    ranked_fit_raw = str(job.get("baseline_fit_label") or "").strip().lower()
    if ranked_fit_raw in _FIT_LABEL_ORDER:
        return cast(FitClassification, ranked_fit_raw)
    if fit_classification is None:
        return None
    return fit_classification



def _build_cv_analysis_trace_record(
    *,
    job: dict[str, Any],
    status: AnalysisStatus,
    analysis_input_fingerprint: str | None,
    evidence_selection_summary: dict[str, Any] | None,
    requirement_coverage: list[dict[str, Any]] | None,
    section_confidence_hints: dict[str, str] | None,
    error: ErrorPayload | None,
) -> dict[str, Any]:
    identity_keys = job_identity_keys(job)
    canonical_identity = identity_keys[0] if identity_keys else extract_job_title(job)
    normalized_summary = dict(evidence_selection_summary or {})
    selected_evidence_count = int(normalized_summary.get("selected_evidence_count") or 0)
    fallback_used = bool(normalized_summary.get("fallback_used", False))
    error_summary = dict(error) if isinstance(error, dict) else None
    trace_status = "degraded" if status == ANALYSIS_FAILED_STATUS else "completed"
    trace_required_skills = list(job.get("required_skills_canonical") or [])
    if not trace_required_skills:
        trace_required_skills = list(job.get("required_skills") or [])

    trace_preferred_skills = list(job.get("preferred_skills_canonical") or [])
    if not trace_preferred_skills:
        trace_preferred_skills = list(job.get("preferred_skills") or [])
    return {
        "trace_schema_version": "stage_execution_trace_record_v1",
        "trace_family": "stage_execution_trace",
        "step_id": "cv_analysis",
        "trace_status": trace_status,
        "record_id": canonical_identity,
        "scope_type": "job",
        "scope_key": canonical_identity,
        "status": status,
        "attempts": [
            {
                "attempt_index": 1,
                "attempt_type": "analysis",
                "attempt_status": status,
                "provider_status": "failed" if status == ANALYSIS_FAILED_STATUS else "completed",
            }
        ],
        "input_summary": {
            "analysis_input_fingerprint": analysis_input_fingerprint,
            "required_skills_count": len(trace_required_skills),
            "preferred_skills_count": len(trace_preferred_skills),
            "responsibilities_count": len(list(job.get("responsibilities") or [])),
        },
        "output_summary": {
            "selected_evidence_count": selected_evidence_count,
            "fallback_used": fallback_used,
            "requirement_coverage_count": len(list(requirement_coverage or [])),
            "section_confidence_present": bool(section_confidence_hints),
        },
        "validation_summary": {
            "status": "not_run",
        },
        "repair_summary": {
            "repair_attempted": False,
            "repair_attempts": 0,
        },
        "error_summary": error_summary,
    }


def build_decision_chain(
    *,
    job: dict[str, Any],
    fit_classification: FitClassification | None,
    cv_analysis_status: str,
    cv_status: str,
) -> dict[str, Any]:
    ranking_fit_label = _authoritative_ranking_fit_label(job, fit_classification)
    ranking_fit_source = (
        "baseline_fit_label"
        if str(job.get("baseline_fit_label") or "").strip().lower() in _FIT_LABEL_ORDER
        else "baseline_fit_thresholds"
        if job.get("baseline_fit") is not None
        else "missing_baseline_fit"
    )
    return {
        "shortlist": {
            "status": shortlist_status_for_ranked_job(job),
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
            "status": validation_status_for_cv_status(cv_status),
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
    requirement_coverage: list[dict[str, Any]] | None,
    section_confidence_hints: dict[str, str] | None,
    do_not_claim: list[str] | None,
    fit_classification: FitClassification | None,
    error: ErrorPayload | None,
    analysis_input_components: dict[str, Any] | None = None,
    reuse_decision: dict[str, Any] | None = None,
) -> CvAnalysisRecord:
    cv_status = cv_generation_status_for_analysis_status(status)
    resolved_reuse_decision = reuse_decision or build_reuse_decision(
        decision=analysis_reuse_status,
        reason_code=analysis_reuse_status,
        fingerprint=analysis_input_fingerprint,
        source_artifact_type="cv_analysis",
    )
    evidence_used = build_evidence_used(evidence_payload)
    trace_record = _build_cv_analysis_trace_record(
        job=job,
        status=status,
        analysis_input_fingerprint=analysis_input_fingerprint,
        evidence_selection_summary=evidence_selection_summary,
        requirement_coverage=requirement_coverage,
        section_confidence_hints=section_confidence_hints,
        error=error,
    )
    return {
        "raw_job_fingerprint": str(job.get("raw_job_fingerprint") or ""),
        "job_url": extract_job_url(job),
        "job_title": extract_job_title(job),
        "status": status,
        "analysis_input_fingerprint": analysis_input_fingerprint,
        "analysis_input_components": dict(analysis_input_components or {}),
        "analysis_reuse_status": analysis_reuse_status,
        "reuse_decision": dict(resolved_reuse_decision),
        "ranking_fit_label": _authoritative_ranking_fit_label(job, fit_classification),
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
        "requirement_coverage": list(requirement_coverage or []),
        "section_confidence_hints": dict(section_confidence_hints or {}),
        "do_not_claim": list(do_not_claim or []),
        "outcome_reason": error if status in {SKIPPED_FIT_GATE_STATUS, BLOCKED_BY_RERANKER_STATUS} else None,
        "error": error if status not in {SKIPPED_FIT_GATE_STATUS, BLOCKED_BY_RERANKER_STATUS} else None,
        "cv_analysis_trace": trace_record,
    }

def _build_requirement_coverage(
    required_skills: list[str],
    evidence: list[dict[str, Any]],
    *,
    missing_skills: list[str],
) -> list[dict[str, Any]]:
    normalized_missing = {str(skill).strip().lower() for skill in missing_skills if str(skill).strip()}
    coverage: list[dict[str, Any]] = []
    for skill in required_skills:
        normalized_skill = str(skill).strip()
        lowered = normalized_skill.lower()
        if not normalized_skill:
            continue
        support_strength = "unsupported" if lowered in normalized_missing else "supported"
        coverage.append(
            {
                "requirement": normalized_skill,
                "support_strength": support_strength,
                "evidence_support_count": 0 if support_strength == "unsupported" else max(1, len(evidence)),
            }
        )
    return coverage

def _build_section_confidence_hints(
    evidence: list[dict[str, Any]],
    gap_summary: dict[str, Any] | None,
) -> dict[str, str]:
    missing_count = len(list((gap_summary or {}).get("missing") or []))
    evidence_count = len(evidence)
    if evidence_count >= 3 and missing_count == 0:
        level = "high"
    elif evidence_count >= 1:
        level = "medium"
    else:
        level = "low"
    return {
        "summary": level,
        "experience": "high" if evidence_count >= 2 else level,
        "projects": level,
        "skills": "high" if missing_count == 0 else "medium",
    }


def is_generation_ready(record: dict[str, Any]) -> bool:
    return bool(str(record.get("status") or "") == READY_FOR_GENERATION_STATUS)


def _candidate_skill_names(profile: dict[str, Any]) -> list[str]:
    candidate_skills = flatten_skills(profile)
    if candidate_skills:
        return [str(skill) for skill in candidate_skills if str(skill)]
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
    *,
    fallback_used: bool,
) -> dict[str, Any]:
    return _compact_mapping(
        {
            "channel_counts": normalize_analysis_channel_mapping(
                evidence_bundle.get("channel_counts") or {}
            ),
            "fallback_used": fallback_used,
            "effective_channel_pool_size": int(evidence_bundle.get("effective_channel_pool_size") or 0),
            "merged_pool_size": int(evidence_bundle.get("merged_pool_size") or 0),
            "deduped_pool_size": int(evidence_bundle.get("deduped_pool_size") or 0),
            "selected_evidence_count": len(evidence),
            "selected_evidence_ids": list(evidence_bundle.get("selected_evidence_ids") or []),
            "unselected_top_candidates": list(evidence_bundle.get("unselected_top_candidates") or []),
            "hybrid_alignment": normalize_analysis_channel_mapping(
                evidence_bundle.get("hybrid_alignment") or {}
            ),
            "semantic_alignment": dict(evidence_bundle.get("semantic_alignment") or {}),
        }
    )


def _cv_analysis_sleep_secs(config: dict[str, Any]) -> float:
    return get_stage_runtime_sleep_secs(config, stage="cv_analysis", default=0.0)


_REUSABLE_ANALYSIS_STATUSES = {READY_FOR_GENERATION_STATUS, SKIPPED_FIT_GATE_STATUS}
_REUSABLE_RECORD_REQUIRED_FIELDS = frozenset(
    {
        "raw_job_fingerprint",
        "job_url",
        "job_title",
        "status",
        "analysis_input_fingerprint",
        "analysis_input_components",
        "analysis_reuse_status",
        "reuse_decision",
        "ranking_fit_label",
        "fit_classification",
        "decision_chain",
        "job_snapshot",
        "evidence_payload",
        "evidence_used",
        "evidence_selection_summary",
        "gap_summary",
        "requirement_coverage",
        "section_confidence_hints",
        "do_not_claim",
        "outcome_reason",
        "error",
        "cv_analysis_trace",
    }
)


def _build_analysis_input_components(payload: dict[str, Any]) -> dict[str, Any]:
    def _hash(value: Any) -> str:
        seed = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()

    return {
        "contract_fingerprint": str(payload.get("contract_fingerprint") or ""),
        "profile_payload_hash": _hash(dict(payload.get("profile") or {})),
        "job_payload_hash": _hash(dict(payload.get("job") or {})),
    }


def _validate_analysis_inputs(
    job: dict[str, Any],
    profile: dict[str, Any],
    config: dict[str, Any],
    top_k: int | None,
) -> None:
    for name, value in (("job", job), ("profile", profile), ("config", config)):
        if not isinstance(value, Mapping):
            raise TypeError(f"{name} must be a mapping")
    if top_k is not None and (isinstance(top_k, bool) or not isinstance(top_k, int)):
        raise TypeError("top_k must be an integer")


def _reuse_rejection_reason(
    reusable_record: dict[str, Any] | None,
    *,
    analysis_input_fingerprint: str,
    analysis_input_components: dict[str, Any],
) -> str | None:
    if not isinstance(reusable_record, dict):
        return "no_reusable_snapshot_match"
    if str(reusable_record.get("status") or "") not in _REUSABLE_ANALYSIS_STATUSES:
        return "reusable_status_not_eligible"
    if str(reusable_record.get("analysis_input_fingerprint") or "") != analysis_input_fingerprint:
        return "analysis_input_fingerprint_mismatch"
    if not _REUSABLE_RECORD_REQUIRED_FIELDS.issubset(reusable_record):
        return "incomplete_reusable_record"
    prior_components = dict(reusable_record.get("analysis_input_components") or {})
    if str(prior_components.get("contract_fingerprint") or "") != str(
        analysis_input_components.get("contract_fingerprint") or ""
    ):
        return "contract_fingerprint_changed"
    return None


def _rebuild_reused_record(
    *,
    job: dict[str, Any],
    reusable_record: dict[str, Any],
    analysis_input_fingerprint: str,
    analysis_input_components: dict[str, Any],
) -> CvAnalysisRecord:
    status = cast(AnalysisStatus, str(reusable_record["status"]))
    fit_value = str(reusable_record.get("fit_classification") or "")
    fit_classification = cast(FitClassification, fit_value) if fit_value in _FIT_LABEL_ORDER else None
    prior_error = (
        reusable_record.get("outcome_reason")
        if status in {SKIPPED_FIT_GATE_STATUS, BLOCKED_BY_RERANKER_STATUS}
        else reusable_record.get("error")
    )
    return build_cv_analysis_record(
        job=job,
        status=status,
        analysis_input_fingerprint=analysis_input_fingerprint,
        analysis_input_components=analysis_input_components,
        analysis_reuse_status="reused_exact_match",
        reuse_decision=build_reuse_decision(
            decision="reused_exact_match",
            reason_code="exact_fingerprint_match",
            fingerprint=analysis_input_fingerprint,
            source_artifact_type="cv_analysis",
        ),
        evidence_payload=list(reusable_record.get("evidence_payload") or []),
        evidence_selection_summary=dict(reusable_record.get("evidence_selection_summary") or {}),
        gap_summary=reusable_record.get("gap_summary"),
        requirement_coverage=list(reusable_record.get("requirement_coverage") or []),
        section_confidence_hints=dict(reusable_record.get("section_confidence_hints") or {}),
        do_not_claim=list(reusable_record.get("do_not_claim") or []),
        fit_classification=fit_classification,
        error=cast(ErrorPayload | None, prior_error),
    )


def analyze_ranked_job(
    job: dict[str, Any],
    profile: dict[str, Any],
    config: dict[str, Any],
    *,
    top_k: int | None = None,
    reusable_record: dict[str, Any] | None = None,
) -> CvAnalysisRecord:
    _validate_analysis_inputs(job, profile, config, top_k)
    ranking_fit_label: FitClassification | None = None
    analysis_input_fingerprint: str | None = None
    analysis_input_components: dict[str, Any] = {}
    reuse_reason = "no_reusable_snapshot_match"
    evidence: list[dict[str, Any]] = []
    evidence_selection_summary: dict[str, Any] = {}
    gap_summary: dict[str, Any] | None = None
    try:
        ranking_fit_label = resolve_ranked_job_fit(job, config)
        if ranking_fit_label == "skip":
            return build_cv_analysis_record(
                job=job,
                status=cast(AnalysisStatus, BLOCKED_BY_RERANKER_STATUS),
                analysis_input_fingerprint=None,
                analysis_input_components={},
                analysis_reuse_status="not_run_reranker_skip",
                reuse_decision=build_reuse_decision(
                    decision="not_run_reranker_skip",
                    reason_code="reranker_blocked_before_analysis",
                    fingerprint=None,
                    source_artifact_type="cv_analysis",
                ),
                evidence_payload=[],
                evidence_selection_summary=None,
                gap_summary=None,
                requirement_coverage=[],
                section_confidence_hints={},
                do_not_claim=[],
                fit_classification=ranking_fit_label,
                error={
                    "stage": "reranker_fit",
                    "message": f"Blocked {extract_job_url(job)} before CV analysis (reranker fit=skip)",
                },
            )

        fingerprint_record = build_cv_analysis_input_fingerprint(profile, job, config)
        analysis_input_fingerprint = str(fingerprint_record["fingerprint"])
        analysis_input_components = _build_analysis_input_components(
            dict(fingerprint_record.get("payload") or {})
        )
        rejection_reason = _reuse_rejection_reason(
            reusable_record,
            analysis_input_fingerprint=analysis_input_fingerprint,
            analysis_input_components=analysis_input_components,
        )
        if rejection_reason is None:
            return _rebuild_reused_record(
                job=job,
                reusable_record=cast(dict[str, Any], reusable_record),
                analysis_input_fingerprint=analysis_input_fingerprint,
                analysis_input_components=analysis_input_components,
            )
        reuse_reason = rejection_reason
        reuse_decision = build_reuse_decision(
            decision="fresh_compute",
            reason_code=reuse_reason,
            fingerprint=analysis_input_fingerprint,
            source_artifact_type="cv_analysis",
        )

        sleep_secs = _cv_analysis_sleep_secs(config)
        if sleep_secs > 0:
            time.sleep(sleep_secs)
        evidence_top_k = int(top_k if top_k is not None else config["pipeline"]["evidence_top_k"])
        evidence_bundle = retrieve_evidence_bundle(
            profile,
            job,
            top_k=evidence_top_k,
            config=config,
        )
        evidence = list(evidence_bundle.get("selected_evidence") or [])
        evidence_selection_summary = _build_evidence_selection_summary(
            evidence_bundle,
            evidence,
            fallback_used=False,
        )

        if not evidence:
            evidence = retrieve_evidence(profile, job, top_k=evidence_top_k)
            if evidence:
                evidence_selection_summary = _compact_mapping(
                    {
                        "channel_counts": normalize_analysis_channel_mapping(
                            evidence_selection_summary.get("channel_counts") or {}
                        ),
                        "fallback_used": True,
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
                        "selected_evidence_ids": [
                            str(item.get("evidence_id") or "") for item in evidence
                        ],
                        "unselected_top_candidates": list(
                            evidence_selection_summary.get("unselected_top_candidates") or []
                        ),
                        "hybrid_alignment": normalize_analysis_channel_mapping(
                            evidence_selection_summary.get("hybrid_alignment") or {}
                        ),
                        "semantic_alignment": dict(
                            evidence_selection_summary.get("semantic_alignment") or {}
                        ),
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
        required_skills = [
            str(skill) for skill in list(job.get("required_skills") or []) if str(skill)
        ]
        missing_skills = [
            str(skill) for skill in list((gap_summary or {}).get("missing") or []) if str(skill)
        ]
        if fit_classification == "skip":
            return build_cv_analysis_record(
                job=job,
                status=cast(AnalysisStatus, SKIPPED_FIT_GATE_STATUS),
                analysis_input_fingerprint=analysis_input_fingerprint,
                analysis_input_components=analysis_input_components,
                analysis_reuse_status="fresh_compute",
                reuse_decision=reuse_decision,
                evidence_payload=evidence,
                evidence_selection_summary=evidence_selection_summary,
                gap_summary=gap_summary,
                requirement_coverage=_build_requirement_coverage(
                    required_skills,
                    evidence,
                    missing_skills=missing_skills,
                ),
                section_confidence_hints=_build_section_confidence_hints(evidence, gap_summary),
                do_not_claim=missing_skills,
                fit_classification=fit_classification,
                error={
                    "stage": "fit_gate",
                    "message": f"Skipped {extract_job_url(job)} (fit=skip)",
                },
            )

        return build_cv_analysis_record(
            job=job,
            status=cast(AnalysisStatus, READY_FOR_GENERATION_STATUS),
            analysis_input_fingerprint=analysis_input_fingerprint,
            analysis_input_components=analysis_input_components,
            analysis_reuse_status="fresh_compute",
            reuse_decision=reuse_decision,
            evidence_payload=evidence,
            evidence_selection_summary=evidence_selection_summary,
            gap_summary=gap_summary,
            requirement_coverage=_build_requirement_coverage(
                required_skills,
                evidence,
                missing_skills=missing_skills,
            ),
            section_confidence_hints=_build_section_confidence_hints(evidence, gap_summary),
            do_not_claim=missing_skills,
            fit_classification=fit_classification,
            error=None,
        )
    except Exception as exc:
        return build_cv_analysis_record(
            job=job,
            status=cast(AnalysisStatus, ANALYSIS_FAILED_STATUS),
            analysis_input_fingerprint=analysis_input_fingerprint,
            analysis_input_components=analysis_input_components,
            analysis_reuse_status="fresh_compute",
            reuse_decision=build_reuse_decision(
                decision="fresh_compute",
                reason_code=reuse_reason if analysis_input_fingerprint else "analysis_runtime_failure",
                fingerprint=analysis_input_fingerprint,
                source_artifact_type="cv_analysis",
            ),
            evidence_payload=evidence,
            evidence_selection_summary=evidence_selection_summary,
            gap_summary=gap_summary,
            requirement_coverage=[],
            section_confidence_hints={},
            do_not_claim=[],
            fit_classification=ranking_fit_label,
            error={
                "stage": "analysis",
                "message": str(exc),
            },
        )
