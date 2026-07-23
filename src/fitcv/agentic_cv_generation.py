"""@meta
name: agentic_cv_generation
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.stage-artifact-diagnostics
responsibility:
  - Module metadata placeholder for src.fitcv.agentic_cv_generation.
inputs:
  - Internal runtime calls and module imports
outputs:
  - Module-level symbols and runtime behavior
lifecycle:
  - status: active
"""

from collections.abc import Mapping
from copy import deepcopy
import datetime
import hashlib
import json
from pathlib import Path
import os
from typing import Any, Callable, Literal, TypedDict, cast

from fitcv.agentic_cv_analysis import (
    FitClassification,
    build_analysis_input_summary,
    build_decision_chain,
    build_evidence_used,
    extract_job_title,
    extract_job_url,
)
from fitcv.candidate_name_policy import is_candidate_name_placeholder, resolved_candidate_profile_name
from fitcv.config import (
    get_cv_acceptance_policy,
    get_cv_generation_model,
    get_cv_generation_prompt_version,
    get_cv_generation_structured_prompt_id,
)
from fitcv.runtime_routing import resolve_cv_generation_routing_snapshot
from fitcv.cv_generator import (
    _execute_cv_generation_runtime,
    _get_enabled_section_names,
    _resolve_template_path,
    build_live_structured_cv_response_schema as _canonical_live_structured_cv_response_schema,
    generate_cv,
    render_cv_markdown,
)
from fitcv.late_stage_contract import (
    CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS as BLOCKED_BY_RERANKER_STATUS,
    CV_ANALYSIS_READY_FOR_GENERATION_STATUS as READY_FOR_GENERATION_STATUS,
    CV_ANALYSIS_SKIPPED_FIT_GATE_STATUS as SKIPPED_FIT_GATE_STATUS,
    CV_GENERATION_ACCEPTED_STATUS as ACCEPTED_STATUS,
    CV_GENERATION_FAILED_STATUS as GENERATION_FAILED_STATUS,
    CV_GENERATION_VALIDATION_FAILED_STATUS as VALIDATION_FAILED_STATUS,
    GenerationStatus,
)
from fitcv.pipeline_contracts import ReviewRequiredReasonCode
from fitcv.pipeline_stages.common import job_identity_keys
from fitcv.reuse import build_reuse_decision
from fitcv.validator import AnalysisGroundingPayload, run_all_validations
DEFAULT_MAX_SUMMARY_LINES = 3

_REPAIRABLE_VALIDATION_FIELDS = ("grounding_violations", "skill_violations")


class RepairAttempt(TypedDict, total=False):
    performed: bool
    missing_sections: list[str]
    reason: str


class ValidationSnapshot(TypedDict):
    valid: bool
    missing_sections: list[str]
    grounding_violations: list[str]
    deterministic_grounding_violations: list[str]
    semantic_grounding_violations: list[str]
    skill_violations: list[str]
    warnings: list[str]
    support_source_summary: dict[str, Any]
    markdown_quality_blocking_issues: list[str]
    markdown_quality_review_flags: list[str]


class ErrorPayload(TypedDict, total=False):
    stage: str
    code: str
    message: str


class CvGenerationResult(TypedDict, total=False):
    result_contract_version: str
    raw_job_fingerprint: str
    job_url: str
    job_title: str
    analysis_input_fingerprint: str
    cv_generation_input_fingerprint: str
    cv_generation_input_components: dict[str, Any]
    cv_generation_reuse_status: str
    reuse_decision: dict[str, Any]
    reused_cv_version_id: str | None
    status: GenerationStatus
    ranking_fit_label: str | None
    fit_classification: FitClassification | None
    decision_chain: dict[str, Any]
    analysis_input_summary: dict[str, Any]
    evidence_used: list[dict[str, Any]]
    evidence_selection_summary: dict[str, Any]
    gap_summary: dict[str, Any] | None
    structured_cv_initial: dict[str, Any] | None
    validation_initial: ValidationSnapshot | None
    repair_attempt: RepairAttempt
    structured_cv_final: dict[str, Any] | None
    markdown_final: str | None
    validation: dict[str, Any] | None
    outcome_reason: ErrorPayload | None
    error: ErrorPayload | None
    review_required_reason_code: str | None
    validation_evidence_fingerprint: str
    llm_runtime_observations: list[dict[str, Any]]
    cv_generation_trace: dict[str, Any]

_LIVE_TRACE_SCHEMA_VERSION = "stage_execution_trace_record_v1"
_LIVE_TRACE_SCHEMA_NAME = "fitcv_structured_cv_document"
_LIVE_TRACE_PROMPT_CONTRACT = "fitcv_structured_generation_prompt"
_LIVE_TRACE_FAMILY = "stage_execution_trace"
_LIVE_TRACE_STEP_ID = "cv_generation"
_LIVE_TRACE_DEBUG_ENV_KEYS = (
    "FITCV_LLM_DEBUG_LIVE",
    "FITCV_LLM_DEBUG_LIVE_DUMP_PATH",
)



def _empty_repair_attempt() -> RepairAttempt:
    return {
        "performed": False,
        "missing_sections": [],
    }



def _build_requirement_priorities(job: dict[str, Any]) -> list[dict[str, Any]]:
    priorities: list[dict[str, Any]] = []
    for index, requirement in enumerate(list(job.get("required_skills") or [])):
        priorities.append(
            {
                "requirement": str(requirement),
                "priority": "primary" if index < 2 else "secondary",
                "target_sections": ["experience", "skills"],
            }
        )
    return priorities


def _build_generation_ready_analysis(
    analysis_record: dict[str, Any],
    profile: dict[str, Any],
    job: dict[str, Any],
) -> dict[str, Any]:
    allowed_claim_ids = [
        str(item.get("evidence_id") or item.get("claim_id") or "")
        for item in list(analysis_record.get("evidence_payload") or [])
        if str(item.get("evidence_id") or item.get("claim_id") or "")
    ]
    required_skills = [str(skill) for skill in list(job.get("required_skills") or []) if str(skill)]
    requirement_priorities = _build_requirement_priorities(job)
    hold_reason = str(
        (analysis_record.get("outcome_reason") or analysis_record.get("error") or {}).get("message") or ""
    ).strip()
    ready_for_generation = str(analysis_record.get("status") or "") == READY_FOR_GENERATION_STATUS
    unsupported_requirements_count = 0 if allowed_claim_ids else len(required_skills)
    selected_claim_ids = list(allowed_claim_ids)
    return {
        "analysis_id": str(analysis_record.get("analysis_input_fingerprint") or extract_job_url(job) or "analysis"),
        "job_input": {
            "title": str(job.get("title") or job.get("job_title") or analysis_record.get("job_title") or ""),
            "company": str(job.get("company") or job.get("companyName") or ""),
        },
        "profile_input": {
            "candidate_name": resolved_candidate_profile_name(profile) or str(profile.get("name") or ""),
        },
        "required_sections": ["summary", "experience", "skills"],
        "generation_constraints": {
            "max_summary_lines": DEFAULT_MAX_SUMMARY_LINES,
        },
        "analysis_context": {
            "allowed_claim_ids": selected_claim_ids,
        },
        "requirement_priorities": requirement_priorities,
        "allowed_claim_evidence": [
            {
                "claim_id": claim_id,
                "evidence": claim_id,
                "supports_requirements": required_skills,
            }
            for claim_id in selected_claim_ids
        ],
        "pre_writing_decision": {
            "ready_for_generation": ready_for_generation,
            "hold_reasons": [] if ready_for_generation else [hold_reason or "Generation blocked by upstream hold."],
            "uncertainty_notes": [],
        },
        "readiness_diagnostics": {
            "supported_requirements_count": len(required_skills) if selected_claim_ids else 0,
            "unsupported_requirements_count": unsupported_requirements_count,
            "weak_evidence_claim_ids": [],
            "selected_evidence_claim_ids": selected_claim_ids,
            "readiness_score": len(selected_claim_ids),
            "score_components": {
                "support_points": len(selected_claim_ids),
                "unsupported_requirement_penalty": unsupported_requirements_count,
                "weak_evidence_penalty": 0,
                "manual_review_penalty": 0,
            },
            "generation_ready_reason": (
                "Ready for generation from FitCV late-stage adapter."
                if ready_for_generation
                else "Blocked before generation by FitCV late-stage adapter."
            ),
        },
    }

def _augmented_gap_summary_from_analysis(analysis_record: dict[str, Any]) -> dict[str, Any]:
    gap_summary = dict(analysis_record.get("gap_summary") or {})
    do_not_claim = [str(item) for item in list(analysis_record.get("do_not_claim") or []) if str(item)]
    requirement_coverage = [
        dict(item)
        for item in list(analysis_record.get("requirement_coverage") or [])
        if isinstance(item, dict)
    ]
    section_confidence_hints = dict(analysis_record.get("section_confidence_hints") or {})
    if do_not_claim:
        gap_summary["do_not_claim"] = do_not_claim
    if requirement_coverage:
        gap_summary["requirement_coverage"] = requirement_coverage
    if section_confidence_hints:
        gap_summary["section_confidence_hints"] = section_confidence_hints
    return gap_summary




def _empty_cv_generation_trace(
    *,
    template_path: str | None,
) -> dict[str, Any]:
    return {
        "trace_schema_version": _LIVE_TRACE_SCHEMA_VERSION,
        "trace_family": _LIVE_TRACE_FAMILY,
        "step_id": _LIVE_TRACE_STEP_ID,
        "trace_status": "completed",
        "trace_metadata": {
            "prompt_contract": _LIVE_TRACE_PROMPT_CONTRACT,
            "template_path": str(template_path or ""),
            "response_schema_name": _LIVE_TRACE_SCHEMA_NAME,
        },
        "attempts": [],
        "input_summary": {
            "attempt_count": 0,
            "input_item_count": 0,
        },
        "output_summary": {
            "accepted_output_present": False,
            "final_status": "",
        },
        "validation_summary": {
            "initial_valid": None,
            "final_valid": None,
            "initial_missing_fields": [],
            "final_missing_fields": [],
            "initial_grounding_violation_count": 0,
            "final_grounding_violation_count": 0,
            "initial_skill_violation_count": 0,
            "final_skill_violation_count": 0,
        },
        "repair_summary": {
            "repair_attempted": False,
            "repair_attempt_count": 0,
            "repair_targets": [],
            "repair_reason": "",
        },
        "error_summary": None,
    }

def _error_code_from_message(message: str) -> str | None:
    normalized = str(message or "")
    for token in normalized.replace(":", " ").split():
        if token.isdigit():
            return token
    return None


def _update_live_trace_validation_cycle(
    trace_payload: dict[str, Any],
    *,
    validation_initial: ValidationSnapshot | None,
    validation_final: dict[str, Any] | None,
) -> None:
    if not isinstance(trace_payload.get("validation_summary"), dict):
        return
    validation_summary = dict(trace_payload["validation_summary"])
    if validation_initial is None:
        validation_summary["initial_valid"] = False
        validation_summary["initial_missing_fields"] = []
    else:
        validation_summary["initial_valid"] = bool(validation_initial["valid"])
        validation_summary["initial_missing_fields"] = list(validation_initial["missing_sections"])
    if isinstance(validation_final, dict):
        validation_summary["final_valid"] = bool(validation_final.get("valid"))
        validation_summary["final_missing_fields"] = list(validation_final.get("missing_sections") or [])
        validation_summary["violation_count"] = (
            len(list(validation_final.get("grounding_violations") or []))
            + len(list(validation_final.get("skill_violations") or []))
        )
        validation_summary["warning_count"] = len(list(validation_final.get("warnings") or []))
    trace_payload["validation_summary"] = validation_summary


def _coerce_fit_classification(value: Any) -> FitClassification | None:
    normalized = str(value or "").strip().lower()
    if normalized in {"strong", "stretch", "skip"}:
        return cast(FitClassification, normalized)
    return None


def _coerce_passthrough_status(value: Any) -> GenerationStatus:
    normalized = str(value or "").strip()
    if normalized in {
        BLOCKED_BY_RERANKER_STATUS,
        SKIPPED_FIT_GATE_STATUS,
        "analysis_failed",
    }:
        return cast(GenerationStatus, normalized)
    return GENERATION_FAILED_STATUS


def _coerce_error_payload(value: Any) -> ErrorPayload | None:
    if not isinstance(value, dict):
        return None
    stage = str(value.get("stage") or "").strip()
    message = str(value.get("message") or "").strip()
    if not stage or not message:
        return None
    return {
        "stage": stage,
        "message": message,
    }




def _is_candidate_name_placeholder_validation(validation: dict[str, Any]) -> bool:
    grounding_violations = list(validation.get("grounding_violations") or [])
    if not grounding_violations:
        return False
    return all("candidate-name placeholder" in str(item).lower() for item in grounding_violations)


def _should_repair_candidate_name_placeholder(
    validation: dict[str, Any],
    structured_cv: dict[str, Any] | None,
    profile: dict[str, Any] | None,
) -> bool:
    if validation.get("valid"):
        return False
    if not isinstance(structured_cv, dict):
        return False
    if not resolved_candidate_profile_name(profile):
        return False
    if list(validation.get("missing_sections") or []):
        return False
    if list(validation.get("skill_violations") or []):
        return False
    if list(validation.get("deterministic_grounding_violations") or []):
        return False
    if list(validation.get("semantic_grounding_violations") or []):
        return False
    if not _is_candidate_name_placeholder_validation(validation):
        return False
    sections = structured_cv.get("sections")
    if not isinstance(sections, dict):
        return False
    header = sections.get("header")
    if not isinstance(header, dict):
        return False
    return bool(is_candidate_name_placeholder(header.get("name")))


def _should_retry_missing_sections(validation: dict[str, Any]) -> bool:
    missing_sections = list(validation.get("missing_sections") or [])
    if not missing_sections:
        return False
    return all(not validation.get(field) for field in _REPAIRABLE_VALIDATION_FIELDS)

def _shallow_section_repair_targets(structured_cv: dict[str, Any] | None) -> list[str]:
    if not isinstance(structured_cv, dict):
        return []
    sections = structured_cv.get("sections")
    if not isinstance(sections, dict):
        return []
    targets: list[str] = []
    experience_rows = list(sections.get("experience") or [])
    if experience_rows and any(
        isinstance(item, dict)
        and not [str(b).strip() for b in list(item.get("bullets") or []) if str(b).strip()]
        for item in experience_rows
    ):
        targets.append("experience")
    project_rows = list(sections.get("projects") or [])
    if project_rows and any(
        isinstance(item, dict)
        and str(item.get("context") or "").strip()
        and not [str(b).strip() for b in list(item.get("bullets") or []) if str(b).strip()]
        for item in project_rows
    ):
        targets.append("projects")
    return targets


def _build_validation_grounding_payload(
    analysis_record: dict[str, Any],
    job: dict[str, Any],
    evidence_payload: list[dict[str, Any]],
    evidence_used: list[dict[str, Any]],
) -> AnalysisGroundingPayload:
    return {
        "evidence_payload": list(evidence_payload),
        "evidence_used": list(evidence_used),
        "evidence_selection_summary": dict(analysis_record.get("evidence_selection_summary") or {}),
        "analysis_input_summary": build_analysis_input_summary(job),
    }


def _build_validation_snapshot(validation: Mapping[str, Any] | None) -> ValidationSnapshot | None:
    if validation is None:
        return None
    return {
        "valid": bool(validation.get("valid")),
        "missing_sections": list(validation.get("missing_sections") or []),
        "grounding_violations": list(validation.get("grounding_violations") or []),
        "deterministic_grounding_violations": list(validation.get("deterministic_grounding_violations") or []),
        "semantic_grounding_violations": list(validation.get("semantic_grounding_violations") or []),
        "skill_violations": list(validation.get("skill_violations") or []),
        "warnings": list(validation.get("warnings") or []),
        "support_source_summary": dict(validation.get("support_source_summary") or {}),
        "markdown_quality_blocking_issues": list(validation.get("markdown_quality_blocking_issues") or []),
        "markdown_quality_review_flags": list(validation.get("markdown_quality_review_flags") or []),
    }

def _run_generation_validations(
    markdown: str,
    *,
    profile: dict[str, Any],
    config: dict[str, Any],
    structured_cv: dict[str, Any] | None,
    analysis_grounding: AnalysisGroundingPayload,
) -> dict[str, Any]:
    return dict(
        run_all_validations(
            markdown,
            profile=profile,
            config=config,
            structured_cv=structured_cv,
            analysis_grounding=analysis_grounding,
        )
    )

def _determine_repair_targets(validation: dict[str, Any], structured_cv: dict[str, Any] | None) -> list[str]:
    repair_targets: list[str] = []
    if not validation["valid"] and _should_retry_missing_sections(validation):
        repair_targets = list(validation.get("missing_sections") or [])
    if repair_targets:
        return repair_targets
    return _shallow_section_repair_targets(structured_cv)

def _normalize_missing_section_keys(missing_sections: list[str] | None) -> list[str]:
    keys: list[str] = []
    for raw in list(missing_sections or []):
        value = str(raw).strip().lower()
        if not value:
            continue
        if value in {"skills", "experience", "projects", "education", "languages", "certifications"}:
            keys.append(value)
    return list(dict.fromkeys(keys))

def _backfill_required_sections_from_profile(
    *,
    structured_cv: dict[str, Any] | None,
    profile: dict[str, Any],
    missing_sections: list[str] | None,
) -> tuple[dict[str, Any] | None, list[str]]:
    if not isinstance(structured_cv, dict):
        return structured_cv, []
    repair_keys = _normalize_missing_section_keys(missing_sections)
    if not repair_keys:
        return structured_cv, []

    repaired = deepcopy(structured_cv)
    sections = repaired.setdefault("sections", {})
    if not isinstance(sections, dict):
        return structured_cv, []

    repaired_keys: list[str] = []
    if "skills" in repair_keys:
        profile_skills: list[str] = []
        for item in list(profile.get("skills") or []):
            if isinstance(item, dict):
                value = str(item.get("name") or "").strip()
            else:
                value = str(item).strip()
            if value:
                profile_skills.append(value)
        unique_skills = list(dict.fromkeys(profile_skills))[:12]
        if unique_skills:
            sections["skills"] = {"groups": [{"label": "Core Skills", "items": unique_skills}]}
            repaired_keys.append("skills")

    if "experience" in repair_keys:
        existing_experience = list(sections.get("experience") or [])
        if not existing_experience:
            fallback_experience: list[dict[str, Any]] = []
            for exp in list(profile.get("experiences") or [])[:3]:
                if not isinstance(exp, dict):
                    continue
                bullet_texts = [
                    (
                        str(item.get("text") or "").strip()
                        if isinstance(item, dict)
                        else str(item).strip()
                    )
                    for item in list(exp.get("bullets") or [])
                    if (
                        str(item.get("text") or "").strip()
                        if isinstance(item, dict)
                        else str(item).strip()
                    )
                ]
                fallback_experience.append(
                    {
                        "role": str(exp.get("role") or "").strip(),
                        "company": str(exp.get("company") or "").strip(),
                        "start": exp.get("start"),
                        "end": exp.get("end"),
                        "location": str(exp.get("location") or "").strip() or None,
                        "bullets": bullet_texts[:2] or ["Delivered cross-functional work aligned with business goals."],
                    }
                )
            if fallback_experience:
                sections["experience"] = fallback_experience
                repaired_keys.append("experience")

    if "projects" in repair_keys:
        existing_projects = list(sections.get("projects") or [])
        if not existing_projects:
            fallback_projects: list[dict[str, Any]] = []
            for project in list(profile.get("projects") or [])[:3]:
                if not isinstance(project, dict):
                    continue
                bullets = [
                    str(item).strip()
                    for item in list(project.get("highlights") or project.get("bullets") or [])
                    if str(item).strip()
                ]
                fallback_projects.append(
                    {
                        "name": str(project.get("name") or "").strip(),
                        "context": str(project.get("context") or project.get("period") or "").strip() or None,
                        "bullets": bullets[:2] or ["Built project outcome with measurable business impact."],
                    }
                )
            if fallback_projects:
                sections["projects"] = fallback_projects
                repaired_keys.append("projects")

    if "education" in repair_keys:
        existing_education = list(sections.get("education") or [])
        if not existing_education:
            fallback_education = []
            for edu in list(profile.get("education") or [])[:2]:
                if not isinstance(edu, dict):
                    continue
                fallback_education.append(
                    {
                        "degree": str(edu.get("degree") or "").strip(),
                        "institution": str(edu.get("institution") or "").strip(),
                        "field": str(edu.get("field") or "").strip() or None,
                        "start": edu.get("start"),
                        "end": edu.get("end"),
                    }
                )
            if fallback_education:
                sections["education"] = fallback_education
                repaired_keys.append("education")

    if "languages" in repair_keys:
        existing_languages = list(sections.get("languages") or [])
        if not existing_languages:
            fallback_languages = []
            for lang in list(profile.get("languages") or [])[:5]:
                if isinstance(lang, dict):
                    name = str(lang.get("name") or "").strip()
                    level = str(lang.get("level") or "").strip() or None
                else:
                    name = str(lang).strip()
                    level = None
                if not name:
                    continue
                fallback_languages.append({"name": name, "level": level})
            if fallback_languages:
                sections["languages"] = fallback_languages
                repaired_keys.append("languages")

    return repaired, repaired_keys

def _run_repair_cycle(
    *,
    structured_cv: dict[str, Any] | None,
    markdown: str,
    validation: dict[str, Any],
    profile: dict[str, Any],
    config: dict[str, Any],
    analysis_grounding: AnalysisGroundingPayload,
    retry_executor: Callable[[list[str]], tuple[dict[str, Any] | None, str, dict[str, Any], dict[str, Any] | None]],
    runtime_provenance: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, str, dict[str, Any], RepairAttempt, dict[str, Any] | None]:
    repair_attempt = _empty_repair_attempt()
    if not validation["valid"] and _should_repair_candidate_name_placeholder(validation, structured_cv, profile):
        repair_attempt = _build_candidate_name_repair_attempt()
        structured_cv, markdown = _repair_candidate_name_placeholder(structured_cv or {}, profile, config)
        validation = _run_generation_validations(
            markdown,
            profile=profile,
            config=config,
            structured_cv=structured_cv,
            analysis_grounding=analysis_grounding,
        )

    repair_targets = _determine_repair_targets(validation, structured_cv)
    if repair_targets:
        repair_attempt = _build_repair_attempt(repair_targets)
        structured_cv, markdown, validation, retry_provenance = retry_executor(repair_targets)
        if retry_provenance is not None:
            runtime_provenance = retry_provenance

    if not validation.get("valid"):
        structured_cv, repaired_keys = _backfill_required_sections_from_profile(
            structured_cv=structured_cv,
            profile=profile,
            missing_sections=list(validation.get("missing_sections") or []),
        )
        if repaired_keys:
            markdown = render_cv_markdown(structured_cv or {}, config)
            validation = _run_generation_validations(
                markdown,
                profile=profile,
                config=config,
                structured_cv=structured_cv,
                analysis_grounding=analysis_grounding,
            )
            if validation.get("valid"):
                repair_attempt = {
                    "performed": True,
                    "missing_sections": repaired_keys,
                    "reason": "deterministic_section_backfill",
                }

    return structured_cv, markdown, validation, repair_attempt, runtime_provenance

def _execute_generation_attempt(
    generator: Callable[[list[str] | None], Any],
    *,
    profile: dict[str, Any],
    config: dict[str, Any],
    analysis_grounding: AnalysisGroundingPayload,
    repair_missing_sections: list[str] | None = None,
) -> tuple[dict[str, Any] | None, str, dict[str, Any], dict[str, Any] | None]:
    generated_cv = generator(repair_missing_sections)
    structured_cv, markdown, runtime_provenance = _unwrap_generated_cv(generated_cv)
    validation = _run_generation_validations(
        markdown,
        profile=profile,
        config=config,
        structured_cv=structured_cv,
        analysis_grounding=analysis_grounding,
    )
    return structured_cv, markdown, validation, runtime_provenance

def _build_fallback_provider_generator(
    *,
    job: dict[str, Any],
    evidence_payload: list[dict[str, Any]],
    gap_summary: dict[str, Any],
    profile: dict[str, Any],
    config: dict[str, Any],
    fit: str,
    evidence_selection_summary: dict[str, Any],
) -> Callable[[list[str] | None], Any]:
    def _call(repair_missing_sections: list[str] | None) -> Any:
        return generate_cv(
            job,
            evidence_payload,
            gap_summary,
            profile,
            config,
            fit_classification=fit,
            evidence_selection_summary=evidence_selection_summary,
            repair_missing_sections=repair_missing_sections,
        )

    return _call

def _build_fallback_retry_executor(
    *,
    fallback_provider_generator: Callable[[list[str] | None], Any],
    profile: dict[str, Any],
    config: dict[str, Any],
    analysis_grounding: AnalysisGroundingPayload,
) -> Callable[[list[str]], tuple[dict[str, Any] | None, str, dict[str, Any], dict[str, Any] | None]]:
    def _retry(
        repair_targets: list[str],
    ) -> tuple[dict[str, Any] | None, str, dict[str, Any], dict[str, Any] | None]:
        return _execute_generation_attempt(
            fallback_provider_generator,
            profile=profile,
            config=config,
            analysis_grounding=analysis_grounding,
            repair_missing_sections=repair_targets,
        )

    return _retry


def _build_repair_attempt(missing_sections: list[str] | None = None) -> RepairAttempt:
    return {
        "performed": bool(missing_sections),
        "missing_sections": list(missing_sections or []),
    }


def _build_candidate_name_repair_attempt() -> RepairAttempt:
    return {
        "performed": True,
        "missing_sections": [],
        "reason": "candidate_name_placeholder",
    }


def _repair_candidate_name_placeholder(
    structured_cv: dict[str, Any],
    profile: dict[str, Any],
    config: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    repaired_structured_cv = deepcopy(structured_cv)
    sections = repaired_structured_cv.setdefault("sections", {})
    header = sections.setdefault("header", {})
    header["name"] = resolved_candidate_profile_name(profile)
    repaired_markdown = render_cv_markdown(repaired_structured_cv, config)
    return repaired_structured_cv, repaired_markdown


def _unwrap_generated_cv(
    generated_cv: Any,
) -> tuple[dict[str, Any] | None, str, dict[str, Any] | None]:
    if isinstance(generated_cv, dict):
        markdown = str(generated_cv.get("markdown") or "")
        structured_cv = generated_cv.get("structured_cv")
        runtime_evidence = generated_cv.get("llm_runtime_evidence")
        return (
            dict(structured_cv) if isinstance(structured_cv, dict) else None,
            markdown,
            dict(runtime_evidence) if isinstance(runtime_evidence, dict) else None,
        )
    return None, str(generated_cv), None



_CV_GENERATION_FINGERPRINT_SCHEMA_VERSION = "cv_generation_input_fingerprint_v2"
_CV_GENERATION_RESULT_CONTRACT_VERSION = "cv_generation_result_v2"


def build_cv_generation_input_fingerprint(
    analysis_record: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(analysis_record, dict) or not isinstance(config, dict):
        raise TypeError("analysis_record and config must be mappings")
    template_path = Path(_resolve_template_path(config))
    try:
        template_fingerprint = hashlib.sha256(template_path.read_bytes()).hexdigest()
    except OSError:
        template_fingerprint = ""
    routing = resolve_cv_generation_routing_snapshot(
        config,
        default_model=get_cv_generation_model(config),
    )
    payload = {
        "schema_version": _CV_GENERATION_FINGERPRINT_SCHEMA_VERSION,
        "generation_contract_version": _CV_GENERATION_RESULT_CONTRACT_VERSION,
        "analysis_input_fingerprint": str(analysis_record.get("analysis_input_fingerprint") or ""),
        "fit_classification": str(analysis_record.get("fit_classification") or ""),
        "prompt_id": get_cv_generation_structured_prompt_id(config),
        "prompt_version": get_cv_generation_prompt_version(config),
        "template_path": str(template_path),
        "template_fingerprint": template_fingerprint,
        "enabled_sections": sorted(_get_enabled_section_names(config)),
        "acceptance_policy": get_cv_acceptance_policy(config),
        "validation_policy": {
            "required_sections": sorted(str(item) for item in list(config.get("required_cv_sections") or [])),
            "cv_validation": dict(((config.get("cv") or {}).get("validation") or {})),
            "content_rules": dict(((config.get("cv") or {}).get("content_rules") or {})),
        },
        "route_contract": {
            "provider": str(routing.get("provider") or ""),
            "model": str(routing.get("model") or ""),
            "base_url": str(routing.get("base_url") or ""),
            "wire_api": str(routing.get("wire_api") or ""),
        },
    }
    seed = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return {
        "fingerprint": hashlib.sha256(seed.encode("utf-8")).hexdigest(),
        "payload": payload,
    }


def _extract_failed_rule_ids(validation: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(validation, dict):
        return []
    rule_ids: list[str] = []
    for key in (
        "grounding_violations",
        "deterministic_grounding_violations",
        "semantic_grounding_violations",
        "skill_violations",
        "markdown_quality_blocking_issues",
    ):
        for item in list(validation.get(key) or []):
            if isinstance(item, dict):
                rule_id = str(item.get("rule_id") or item.get("code") or "").strip()
                if rule_id:
                    rule_ids.append(rule_id)
            elif isinstance(item, str) and item.strip():
                rule_ids.append(item.strip())
    return sorted(set(rule_ids))


def _first_failing_section_key(validation: Mapping[str, Any] | None) -> str | None:
    if not isinstance(validation, dict):
        return None
    missing_sections = [
        str(item).strip()
        for item in list(validation.get("missing_sections") or [])
        if str(item).strip()
    ]
    return missing_sections[0] if missing_sections else None


def normalize_review_required_reason_code(
    *,
    status: str,
    error: ErrorPayload | None,
    validation_initial: Mapping[str, Any] | None = None,
) -> ReviewRequiredReasonCode | None:
    if status == "persistence_failed":
        return ReviewRequiredReasonCode.PERSISTENCE_FAILED
    if status == VALIDATION_FAILED_STATUS:
        return ReviewRequiredReasonCode.POST_VALIDATION_FAILED
    if status != "review_required":
        return None
    stage = str((error or {}).get("stage") or "").strip().lower()
    message = str((error or {}).get("message") or "").strip().lower()
    if stage in {"provider", "provider_error", "generation"}:
        return ReviewRequiredReasonCode.PROVIDER_ERROR
    if "timeout" in message:
        return ReviewRequiredReasonCode.TIMEOUT
    if stage in {"markdown", "markdown_quality", "markdown_quality_review"}:
        return ReviewRequiredReasonCode.MARKDOWN_STRUCTURE_VIOLATION
    if stage in {"policy", "policy_acceptance"}:
        if "ratio" in message:
            return ReviewRequiredReasonCode.POLICY_REQUIRED_RATIO_FAIL
        if "missing" in message:
            return ReviewRequiredReasonCode.POLICY_MISSING_REQUIRED_FAIL
        return ReviewRequiredReasonCode.POLICY_ACCEPTANCE_FAIL
    if stage in {"validation", "post_validation"}:
        return ReviewRequiredReasonCode.POST_VALIDATION_FAILED
    if stage == "review_gate":
        if "unsupported requirement" in message:
            return ReviewRequiredReasonCode.UNSUPPORTED_REQUIREMENT_GAP
        if "low confidence" in message:
            return ReviewRequiredReasonCode.LOW_CONFIDENCE_SECTIONS
        if "quality" in message:
            return ReviewRequiredReasonCode.QUALITY_GATE_FAILED
        if _extract_failed_rule_ids(validation_initial) or _first_failing_section_key(validation_initial):
            return ReviewRequiredReasonCode.VALIDATION_GUARDRAIL_FAILED
        return ReviewRequiredReasonCode.REVIEW_GATE_MANUAL_REQUIRED
    if stage in {"template", "schema"}:
        return ReviewRequiredReasonCode.TEMPLATE_CONTRACT_VIOLATION
    if stage == "empty_output":
        return ReviewRequiredReasonCode.EMPTY_OUTPUT
    return ReviewRequiredReasonCode.MANUAL_REVIEW_OTHER


def build_validation_evidence_fingerprint(
    *,
    status: str,
    validation: Mapping[str, Any] | None,
    error: ErrorPayload | None,
) -> str:
    snapshot = dict(validation or {})
    payload = {
        "schema_version": "validation_evidence_fingerprint_v1",
        "status": str(status or ""),
        "missing_sections": list(snapshot.get("missing_sections") or []),
        "failed_rule_ids": _extract_failed_rule_ids(snapshot),
        "first_failing_section_key": _first_failing_section_key(snapshot),
        "markdown_quality_blocking_issues": list(snapshot.get("markdown_quality_blocking_issues") or []),
        "markdown_quality_review_flags": list(snapshot.get("markdown_quality_review_flags") or []),
        "reason_stage": str((error or {}).get("stage") or ""),
        "reason_code": str((error or {}).get("code") or ""),
        "reason_message": str((error or {}).get("message") or ""),
    }
    seed = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def hitl_review_reason_for_case(
    analysis_record: dict[str, Any] | None,
    generation_result: dict[str, Any] | None,
    validation_snapshot: Mapping[str, Any] | None = None,
) -> str | None:
    if not isinstance(analysis_record, dict) or not isinstance(generation_result, dict):
        return None
    if str(generation_result.get("status") or "").strip().lower() != ACCEPTED_STATUS:
        return None
    section_hints = analysis_record.get("section_confidence_hints")
    if isinstance(section_hints, dict):
        low_sections = sorted(
            str(section).strip()
            for section, hint in section_hints.items()
            if str(hint or "").strip().lower() in {"low", "very_low", "none", "unsupported"}
        )
        if low_sections:
            return f"Low confidence sections: {', '.join(low_sections)}"
    if list(analysis_record.get("do_not_claim") or []):
        unsupported = sorted(
            {
                str(item.get("requirement") or "").strip()
                for item in list(analysis_record.get("requirement_coverage") or [])
                if isinstance(item, dict)
                and str(item.get("support_strength") or "").strip().lower()
                in {"unsupported", "weak", "insufficient"}
                and str(item.get("requirement") or "").strip()
            }
        )
        if unsupported:
            return (
                "Unsupported requirements require review: "
                + ", ".join(unsupported[:6])
                + ". Review the generated CV output against these requirements and decide approve as-is, regenerate once, or reject."
            )
    review_flags = list((validation_snapshot or {}).get("markdown_quality_review_flags") or [])
    if review_flags:
        return "Markdown quality requires review: " + str(review_flags[0])
    blocking_issues = list((validation_snapshot or {}).get("markdown_quality_blocking_issues") or [])
    if blocking_issues:
        return "Markdown quality issue detected: " + str(blocking_issues[0])
    return None


def check_cv_acceptance_policy(
    *,
    fit_classification: str | None,
    gap_summary: dict[str, Any] | None,
    policy: dict[str, Any],
) -> tuple[bool, str | None, str]:
    fit = str(fit_classification or "").strip().lower()
    if fit not in {"strong", "stretch"}:
        return True, None, "policy_not_applicable_fit"
    required_match = dict(policy.get("required_match") or {})
    min_ratio_by_fit = dict(required_match.get("min_ratio_by_fit") or {})
    max_missing_by_fit = dict(required_match.get("max_missing_by_fit") or {})
    force_review_fits = {
        str(item).strip().lower()
        for item in list(policy.get("force_review_when_any_required_missing_for_fits") or [])
        if str(item).strip()
    }
    gap = dict(gap_summary or {})
    matched_required = len(list(gap.get("matched") or []))
    missing_required = len(list(gap.get("missing") or []))
    matchable_required = int(gap.get("matchable_required_count") or (matched_required + missing_required))
    required_ratio = float(matched_required / matchable_required) if matchable_required > 0 else 0.0
    if fit in force_review_fits and missing_required > 0:
        return False, ReviewRequiredReasonCode.POLICY_MISSING_REQUIRED_FAIL.value, "Required gaps require review."
    if required_ratio < float(min_ratio_by_fit.get(fit, 0.0)):
        return False, ReviewRequiredReasonCode.POLICY_REQUIRED_RATIO_FAIL.value, "Required match ratio requires review."
    if missing_required > int(max_missing_by_fit.get(fit, 10_000)):
        return False, ReviewRequiredReasonCode.POLICY_MISSING_REQUIRED_FAIL.value, "Too many required gaps require review."
    return True, None, "policy_pass"


def _review_required_reason(
    analysis_record: dict[str, Any],
    result: CvGenerationResult,
    config: dict[str, Any],
) -> tuple[str, str] | None:
    section_hints = analysis_record.get("section_confidence_hints")
    if isinstance(section_hints, dict):
        low_sections = sorted(
            str(section).strip()
            for section, hint in section_hints.items()
            if str(hint or "").strip().lower() in {"low", "very_low", "none", "unsupported"}
        )
        if low_sections:
            return ReviewRequiredReasonCode.LOW_CONFIDENCE_SECTIONS.value, f"Low confidence sections: {', '.join(low_sections)}"
    do_not_claim = [str(item).strip() for item in list(analysis_record.get("do_not_claim") or []) if str(item).strip()]
    if do_not_claim:
        unsupported = sorted({
            str(item.get("requirement") or "").strip()
            for item in list(analysis_record.get("requirement_coverage") or [])
            if isinstance(item, dict)
            and str(item.get("support_strength") or "").strip().lower() in {"unsupported", "weak", "insufficient"}
            and str(item.get("requirement") or "").strip()
        })
        if unsupported:
            return (
                ReviewRequiredReasonCode.UNSUPPORTED_REQUIREMENT_GAP.value,
                "Unsupported requirements require review: " + ", ".join(unsupported[:6]),
            )
    validation = dict(result.get("validation") or result.get("validation_initial") or {})
    review_flags = [str(item).strip() for item in list(validation.get("markdown_quality_review_flags") or []) if str(item).strip()]
    if review_flags:
        return ReviewRequiredReasonCode.MARKDOWN_STRUCTURE_VIOLATION.value, "Markdown quality requires review: " + review_flags[0]
    policy_pass, reason_code, note = check_cv_acceptance_policy(
        fit_classification=result.get("fit_classification"),
        gap_summary=result.get("gap_summary"),
        policy=get_cv_acceptance_policy(config),
    )
    if not policy_pass and reason_code:
        return reason_code, note
    return None


def _finalize_generation_result(
    result: CvGenerationResult,
    *,
    analysis_record: dict[str, Any],
    config: dict[str, Any],
    fingerprint_result: dict[str, Any],
    reuse_status: str,
    reuse_reason_code: str,
    reused_cv_version_id: str | None = None,
) -> CvGenerationResult:
    finalized = deepcopy(result)
    finalized["result_contract_version"] = _CV_GENERATION_RESULT_CONTRACT_VERSION
    finalized["raw_job_fingerprint"] = str(analysis_record.get("raw_job_fingerprint") or "")
    finalized["analysis_input_fingerprint"] = str(analysis_record.get("analysis_input_fingerprint") or "")
    finalized["cv_generation_input_fingerprint"] = str(fingerprint_result["fingerprint"])
    finalized["cv_generation_input_components"] = dict(fingerprint_result["payload"])
    finalized["cv_generation_reuse_status"] = reuse_status
    finalized["reuse_decision"] = build_reuse_decision(
        decision=reuse_status,
        reason_code=reuse_reason_code,
        fingerprint=str(fingerprint_result["fingerprint"]),
        source_artifact_type="cv_generation",
    )
    finalized["reused_cv_version_id"] = reused_cv_version_id
    status = str(finalized.get("status") or "")
    if status == ACCEPTED_STATUS:
        review_reason = _review_required_reason(analysis_record, finalized, config)
        if review_reason is not None:
            reason_code, message = review_reason
            finalized["status"] = "review_required"
            finalized["review_required_reason_code"] = reason_code
            finalized["outcome_reason"] = {"stage": "review", "code": reason_code, "message": message}
            finalized["error"] = None
            status = "review_required"
    reason = finalized.get("outcome_reason") or finalized.get("error")
    validation_snapshot = finalized.get("validation") or finalized.get("validation_initial")
    if not finalized.get("review_required_reason_code"):
        normalized_reason_code = normalize_review_required_reason_code(
            status=status,
            error=reason,
            validation_initial=validation_snapshot,
        )
        finalized["review_required_reason_code"] = (
            normalized_reason_code.value if normalized_reason_code is not None else None
        )
    finalized["validation_evidence_fingerprint"] = build_validation_evidence_fingerprint(
        status=status,
        validation=validation_snapshot,
        error=reason,
    )
    error = finalized.get("error")
    if isinstance(error, dict) and not error.get("code"):
        error["code"] = status or str(error.get("stage") or "failure")
    return finalized


def _reusable_result_or_none(
    *,
    analysis_record: dict[str, Any],
    profile: dict[str, Any],
    config: dict[str, Any],
    reusable_record: dict[str, Any] | None,
    fingerprint_result: dict[str, Any],
) -> CvGenerationResult | None:
    if not isinstance(reusable_record, dict):
        return None
    if str(reusable_record.get("status") or "") not in {"", ACCEPTED_STATUS}:
        return None
    if str(reusable_record.get("cv_generation_input_fingerprint") or "") != str(fingerprint_result["fingerprint"]):
        return None
    components = reusable_record.get("cv_generation_input_components")
    if isinstance(components, dict) and components.get("schema_version") != _CV_GENERATION_FINGERPRINT_SCHEMA_VERSION:
        return None
    structured_cv = reusable_record.get("structured_cv_final") or reusable_record.get("cv_structured")
    markdown = str(reusable_record.get("markdown_final") or reusable_record.get("cv_markdown") or "")
    if not isinstance(structured_cv, dict) or not markdown:
        return None
    job = dict(analysis_record.get("job_snapshot") or {})
    evidence_payload = list(analysis_record.get("evidence_payload") or [])
    evidence_used = list(analysis_record.get("evidence_used") or [])
    grounding = _build_validation_grounding_payload(analysis_record, job, evidence_payload, evidence_used)
    validation = run_all_validations(
        markdown,
        profile,
        config,
        structured_cv=structured_cv,
        analysis_grounding=grounding,
    )
    if not validation.get("valid"):
        return None
    return _build_result(
        analysis_record=analysis_record,
        job=job,
        status=ACCEPTED_STATUS,
        fit_classification=_coerce_fit_classification(analysis_record.get("fit_classification")),
        structured_cv_initial=structured_cv,
        validation_initial=_build_validation_snapshot(validation),
        repair_attempt=_empty_repair_attempt(),
        structured_cv_final=structured_cv,
        markdown_final=markdown,
        validation=validation,
        error=None,
        llm_runtime_evidence=[],
    )


def transition_cv_generation_persistence_failed(
    accepted_result: dict[str, Any],
    *,
    message: str,
) -> CvGenerationResult:
    if str(accepted_result.get("status") or "") != ACCEPTED_STATUS:
        raise ValueError("persistence failure transition requires accepted result")
    failed = cast(CvGenerationResult, deepcopy(accepted_result))
    failed["status"] = "persistence_failed"
    failed["outcome_reason"] = None
    failed["error"] = {
        "stage": "persistence",
        "code": "persistence_failed",
        "message": str(message or "CV persistence failed"),
    }
    failed["review_required_reason_code"] = ReviewRequiredReasonCode.PERSISTENCE_FAILED.value
    return failed


def _build_result(
    *,
    analysis_record: dict[str, Any],
    job: dict[str, Any],
    status: GenerationStatus,
    fit_classification: FitClassification | None,
    structured_cv_initial: dict[str, Any] | None,
    validation_initial: ValidationSnapshot | None,
    repair_attempt: RepairAttempt,
    structured_cv_final: dict[str, Any] | None,
    markdown_final: str | None,
    validation: dict[str, Any] | None,
    error: ErrorPayload | None,
    llm_runtime_evidence: list[dict[str, Any]] | None = None,
    cv_generation_trace: dict[str, Any] | None = None,
) -> CvGenerationResult:
    evidence_payload = list(analysis_record.get("evidence_payload") or [])
    evidence_used = list(analysis_record.get("evidence_used") or [])
    if not evidence_used and evidence_payload:
        evidence_used = build_evidence_used(evidence_payload)

    cv_analysis_status = str(analysis_record.get("status") or "")
    cv_status: str = status
    if status in {ACCEPTED_STATUS, VALIDATION_FAILED_STATUS, GENERATION_FAILED_STATUS}:
        cv_analysis_status = READY_FOR_GENERATION_STATUS
    if status == BLOCKED_BY_RERANKER_STATUS:
        cv_status = "not_attempted"

    result: CvGenerationResult = {
        "job_url": extract_job_url(job),
        "job_title": extract_job_title(job),
        "status": status,
        "ranking_fit_label": str(fit_classification or "").strip() or None,
        "fit_classification": fit_classification,
        "decision_chain": build_decision_chain(
            job=job,
            fit_classification=fit_classification,
            cv_analysis_status=cv_analysis_status,
            cv_status=cv_status,
        ),
        "analysis_input_summary": build_analysis_input_summary(job),
        "evidence_used": evidence_used,
        "evidence_selection_summary": dict(analysis_record.get("evidence_selection_summary") or {}),
        "gap_summary": analysis_record.get("gap_summary"),
        "structured_cv_initial": structured_cv_initial,
        "validation_initial": validation_initial,
        "repair_attempt": repair_attempt,
        "structured_cv_final": structured_cv_final,
        "markdown_final": markdown_final,
        "validation": validation,
        "outcome_reason": error if status in {SKIPPED_FIT_GATE_STATUS, BLOCKED_BY_RERANKER_STATUS} else None,
        "error": error if status not in {SKIPPED_FIT_GATE_STATUS, BLOCKED_BY_RERANKER_STATUS} else None,
    }
    runtime_evidence = [dict(item) for item in (llm_runtime_evidence or []) if isinstance(item, dict)]
    if runtime_evidence:
        identity_keys = job_identity_keys(job)
        scope_key = str(
            analysis_record.get("raw_job_fingerprint")
            or (identity_keys[0] if identity_keys else extract_job_url(job))
        )
        result["llm_runtime_observations"] = [
            {
                "contract_version": "llm_runtime_observation_v1",
                "scope_key": scope_key,
                "input_index": 0,
                "invocation_index": index,
                "evidence": evidence,
            }
            for index, evidence in enumerate(runtime_evidence, start=1)
        ]
    if cv_generation_trace:
        result["cv_generation_trace"] = dict(cv_generation_trace)
    return result


def _generate_fresh_from_analysis(
    analysis_record: dict[str, Any],
    profile: dict[str, Any],
    config: dict[str, Any],
) -> CvGenerationResult:
    job = dict(analysis_record.get("job_snapshot") or {})
    if not job:
        job = {
            "job_url": str(analysis_record.get("job_url") or ""),
            "job_title": str(analysis_record.get("job_title") or ""),
            "title": str(analysis_record.get("job_title") or ""),
        }
    status = str(analysis_record.get("status") or "")
    fit_classification = _coerce_fit_classification(analysis_record.get("fit_classification"))
    if status != READY_FOR_GENERATION_STATUS:
        passthrough_error = analysis_record.get("outcome_reason") or analysis_record.get("error")
        return _build_result(
            analysis_record=analysis_record,
            job=job,
            status=_coerce_passthrough_status(status),
            fit_classification=fit_classification,
            structured_cv_initial=None,
            validation_initial=None,
            repair_attempt=_empty_repair_attempt(),
            structured_cv_final=None,
            markdown_final=None,
            validation=None,
            error=_coerce_error_payload(passthrough_error),
            llm_runtime_evidence=[],
        )

    evidence_payload = list(analysis_record.get("evidence_payload") or [])
    evidence_used = list(analysis_record.get("evidence_used") or [])
    if not evidence_used and evidence_payload:
        evidence_used = build_evidence_used(evidence_payload)
    analysis_grounding = _build_validation_grounding_payload(
        analysis_record,
        job,
        evidence_payload,
        evidence_used,
    )
    gap_summary = _augmented_gap_summary_from_analysis(analysis_record)
    fit = str(fit_classification or "skip")
    evidence_selection_summary = dict(analysis_record.get("evidence_selection_summary") or {})
    runtime_evidence: list[dict[str, Any]] = []
    trace_payload = _empty_cv_generation_trace(
        template_path=str(_resolve_template_path(config)),
    )
    provider_generator = _build_fallback_provider_generator(
        job=job,
        evidence_payload=evidence_payload,
        gap_summary=gap_summary,
        profile=profile,
        config=config,
        fit=fit,
        evidence_selection_summary=evidence_selection_summary,
    )

    def _call_provider(
        repair_targets: list[str] | None,
        attempt_trace: dict[str, Any],
        attempt_index: int,
    ) -> Any:
        return provider_generator(repair_targets)

    failure_stage = "generation"

    def _writer_attempt(
        repair_targets: list[str] | None,
    ) -> tuple[dict[str, Any] | None, str, dict[str, Any], dict[str, Any] | None]:
        attempt_index = len(trace_payload["attempts"]) + 1
        attempt_trace = {
            "attempt_index": attempt_index,
            "attempt_type": "initial_generation" if attempt_index == 1 else "repair_retry",
            "input_item_count": len(evidence_payload),
            "retry_reason": "missing_or_shallow_sections" if repair_targets else None,
            "debug_flags_active": {
                key: bool(str(os.environ.get(key) or "").strip())
                for key in _LIVE_TRACE_DEBUG_ENV_KEYS
            },
            "prompt_contract": _LIVE_TRACE_PROMPT_CONTRACT,
            "template_path": str(_resolve_template_path(config)),
            "response_schema_name": _LIVE_TRACE_SCHEMA_NAME,
        }
        trace_payload["attempts"].append(attempt_trace)
        result = _execute_generation_attempt(
            lambda missing: _call_provider(missing, attempt_trace, attempt_index),
            profile=profile,
            config=config,
            analysis_grounding=analysis_grounding,
            repair_missing_sections=repair_targets,
        )
        if result[3] is not None:
            evidence = dict(result[3])
            runtime_evidence.append(evidence)
            attempt_trace.setdefault("llm_runtime_evidence", evidence)
            provenance = dict(evidence.get("provenance") or {})
            attempt_trace.setdefault("response_id", provenance.get("response_id"))
        attempt_trace.setdefault("provider_status", "accepted")
        attempt_trace.setdefault("accepted_output_present", True)
        return result

    structured_cv_initial: dict[str, Any] | None = None
    validation_initial: ValidationSnapshot | None = None
    repair_attempt = _empty_repair_attempt()
    try:
        structured_cv, markdown, validation, _initial_runtime_evidence = _writer_attempt(None)
        structured_cv_initial = structured_cv
        validation_initial = _build_validation_snapshot(validation)
        structured_cv, markdown, validation, repair_attempt, _latest_runtime_evidence = _run_repair_cycle(
            structured_cv=structured_cv,
            markdown=markdown,
            validation=validation,
            profile=profile,
            config=config,
            analysis_grounding=analysis_grounding,
            retry_executor=lambda targets: _writer_attempt(targets),
            runtime_provenance=_initial_runtime_evidence,
        )
        result_status: GenerationStatus = ACCEPTED_STATUS if validation.get("valid") else VALIDATION_FAILED_STATUS
        error: ErrorPayload | None = None
        structured_cv_final = structured_cv if result_status == ACCEPTED_STATUS else None
        markdown_final = markdown if result_status == ACCEPTED_STATUS else None
        if result_status == VALIDATION_FAILED_STATUS:
            error = {
                "stage": "validation",
                "message": f"CV validation failed for {extract_job_url(job)}",
            }
        if trace_payload is not None:
            trace_payload["input_summary"] = {
                "attempt_count": len(trace_payload["attempts"]),
                "input_item_count": len(evidence_payload),
            }
            trace_payload["repair_summary"] = {
                "repair_attempted": bool(repair_attempt.get("performed")),
                "repair_attempt_count": max(len(trace_payload["attempts"]) - 1, 0),
                "repair_targets": list(repair_attempt.get("missing_sections") or []),
                "repair_reason": str(repair_attempt.get("reason") or ""),
            }
            _update_live_trace_validation_cycle(
                trace_payload,
                validation_initial=validation_initial,
                validation_final=validation,
            )
            trace_payload["output_summary"] = {
                "accepted_output_present": result_status == ACCEPTED_STATUS,
                "final_status": result_status,
            }
            trace_payload["error_summary"] = error
        return _build_result(
            analysis_record=analysis_record,
            job=job,
            status=result_status,
            fit_classification=fit_classification,
            structured_cv_initial=structured_cv_initial,
            validation_initial=validation_initial,
            repair_attempt=repair_attempt,
            structured_cv_final=structured_cv_final,
            markdown_final=markdown_final,
            validation=validation,
            error=error,
            llm_runtime_evidence=runtime_evidence,
            cv_generation_trace=trace_payload,
        )
    except Exception as exc:
        if trace_payload is not None:
            if not trace_payload["attempts"]:
                trace_payload["attempts"].append({"attempt_index": 1, "attempt_type": "initial_generation"})
            latest_attempt = trace_payload["attempts"][-1]
            latest_attempt.setdefault("provider_status", "error")
            latest_attempt.setdefault("accepted_output_present", False)
            latest_attempt.setdefault("error_stage", failure_stage)
            latest_attempt.setdefault("error_message", str(exc))
            latest_attempt.setdefault("error_code", _error_code_from_message(str(exc)))
            trace_payload["trace_status"] = "degraded"
            trace_payload["input_summary"] = {
                "attempt_count": len(trace_payload["attempts"]),
                "input_item_count": len(evidence_payload),
            }
            trace_payload["repair_summary"] = {
                "repair_attempted": bool(repair_attempt.get("performed")),
                "repair_attempt_count": max(len(trace_payload["attempts"]) - 1, 0),
                "repair_targets": list(repair_attempt.get("missing_sections") or []),
                "repair_reason": str(repair_attempt.get("reason") or ""),
            }
            _update_live_trace_validation_cycle(
                trace_payload,
                validation_initial=validation_initial,
                validation_final=None,
            )
            trace_payload["output_summary"] = {
                "accepted_output_present": False,
                "final_status": GENERATION_FAILED_STATUS,
            }
            trace_payload["error_summary"] = {
                "error_stage": failure_stage,
                "error_code": _error_code_from_message(str(exc)),
                "error_message": str(exc),
            }
        return _build_result(
            analysis_record=analysis_record,
            job=job,
            status=GENERATION_FAILED_STATUS,
            fit_classification=fit_classification,
            structured_cv_initial=structured_cv_initial,
            validation_initial=validation_initial,
            repair_attempt=repair_attempt,
            structured_cv_final=None,
            markdown_final=None,
            validation=None,
            error={"stage": failure_stage, "message": str(exc)},
            llm_runtime_evidence=runtime_evidence,
            cv_generation_trace=trace_payload,
        )

def generate_from_analysis(
    analysis_record: dict[str, Any],
    profile: dict[str, Any],
    config: dict[str, Any],
    *,
    reusable_record: dict[str, Any] | None = None,
) -> CvGenerationResult:
    if not isinstance(analysis_record, dict) or not isinstance(profile, dict) or not isinstance(config, dict):
        raise TypeError("analysis_record, profile, and config must be mappings")
    fingerprint_result = build_cv_generation_input_fingerprint(analysis_record, config)
    if str(analysis_record.get("status") or "") == READY_FOR_GENERATION_STATUS:
        reused = _reusable_result_or_none(
            analysis_record=analysis_record,
            profile=profile,
            config=config,
            reusable_record=reusable_record,
            fingerprint_result=fingerprint_result,
        )
        if reused is not None:
            return _finalize_generation_result(
                reused,
                analysis_record=analysis_record,
                config=config,
                fingerprint_result=fingerprint_result,
                reuse_status="reused_exact_match",
                reuse_reason_code="exact_fingerprint_match",
                reused_cv_version_id=str((reusable_record or {}).get("version_id") or "") or None,
            )
    fresh = _generate_fresh_from_analysis(analysis_record, profile, config)
    reuse_reason = "candidate_rejected" if reusable_record is not None else "fresh_compute_required"
    return _finalize_generation_result(
        fresh,
        analysis_record=analysis_record,
        config=config,
        fingerprint_result=fingerprint_result,
        reuse_status="fresh_compute",
        reuse_reason_code=reuse_reason,
    )
