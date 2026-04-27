"""
@meta
name: agentic_cv_generation
type: adapter
domain: cv_generation
responsibility:
  - Run one FitCV generation pass from a CV analysis record.
  - Preserve validator-owned accept or reject semantics without taking over persistence.
inputs:
  - one CV analysis record
  - candidate profile data
  - FitCV runtime config
outputs:
  - generation outcome with accepted artifacts or explicit validation or generation failure
capabilities:
  - cv_system.agentic-generation-adapter
tags:
  - cv
  - generation
  - adapter
lifecycle:
  status: active
"""

from copy import deepcopy
from contextlib import contextmanager
from pathlib import Path
import importlib
import os
import sys
from typing import Any, Final, Iterator, Literal, TypedDict, cast

from fitcv.agentic_cv_analysis import (
    BLOCKED_BY_RERANKER_STATUS,
    READY_FOR_GENERATION_STATUS,
    SKIPPED_FIT_GATE_STATUS,
    FitClassification,
    build_analysis_input_summary,
    build_decision_chain,
    build_evidence_used,
    extract_job_title,
    extract_job_url,
)
from fitcv.cv_generator import generate_cv, render_cv_markdown
from fitcv.validator import AnalysisGroundingPayload, run_all_validations

ACCEPTED_STATUS: Final[Literal["accepted"]] = "accepted"
VALIDATION_FAILED_STATUS: Final[Literal["validation_failed"]] = "validation_failed"
GENERATION_FAILED_STATUS: Final[Literal["generation_failed"]] = "generation_failed"
DEFAULT_MAX_SUMMARY_LINES = 3
DEFAULT_FITCV_LANGGRAPH_ENV_FILENAME = ".env"
DEFAULT_FITCV_LANGGRAPH_REPO_NAME = "fitcv-langgraph"

_REPAIRABLE_VALIDATION_FIELDS = ("grounding_violations", "skill_violations")
_CANDIDATE_NAME_PLACEHOLDER_VALUES = {
    "candidate name",
    "your name",
}

GenerationStatus = Literal[
    "accepted",
    "validation_failed",
    "generation_failed",
    "blocked_by_reranker_fit",
    "skipped_fit_gate",
    "analysis_failed",
]


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


class ErrorPayload(TypedDict):
    stage: str
    message: str


class CvGenerationResult(TypedDict, total=False):
    job_url: str
    job_title: str
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


class _LanggraphRuntimeBridge(TypedDict):
    env_values: dict[str, str]
    run_from_analysis: Any


def _empty_repair_attempt() -> RepairAttempt:
    return {
        "performed": False,
        "missing_sections": [],
    }


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _discover_fitcv_langgraph_repo_root() -> Path | None:
    env_value = os.environ.get("FITCV_LANGGRAPH_REPO_ROOT", "").strip()
    if env_value:
        candidate = Path(env_value)
        if candidate.is_dir():
            return candidate
    for ancestor in _repo_root().parents:
        candidate = ancestor / DEFAULT_FITCV_LANGGRAPH_REPO_NAME
        if candidate.is_dir():
            return candidate
    return None


def _resolve_fitcv_langgraph_env_file(repo_root: Path) -> Path | None:
    env_value = os.environ.get("FITCV_LANGGRAPH_ENV_FILE", "").strip()
    if env_value:
        candidate = Path(env_value)
        if candidate.is_file():
            return candidate
    candidate = repo_root / DEFAULT_FITCV_LANGGRAPH_ENV_FILENAME
    if candidate.is_file():
        return candidate
    return None


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


@contextmanager
def _temporary_environ(values: dict[str, str]) -> Iterator[None]:
    previous: dict[str, str | None] = {
        key: os.environ.get(key)
        for key in values
    }
    os.environ.update(values)
    try:
        yield
    finally:
        for key, old_value in previous.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value


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
            "candidate_name": _resolved_candidate_profile_name(profile) or str(profile.get("name") or ""),
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


def _render_langgraph_draft_markdown(draft: dict[str, Any] | None, profile: dict[str, Any]) -> str | None:
    if not isinstance(draft, dict):
        return None
    lines = [f"# {_resolved_candidate_profile_name(profile) or 'Candidate'}"]
    summary = str(draft.get("summary") or "").strip()
    if summary:
        lines.extend(["## Summary", summary])
    skills = [str(skill).strip() for skill in list(draft.get("skills") or []) if str(skill).strip()]
    if skills:
        lines.extend(["## Skills", ", ".join(skills)])
    experience_entries = list(draft.get("experience") or [])
    if experience_entries:
        lines.append("## Experience")
        for entry in experience_entries:
            if not isinstance(entry, dict):
                continue
            role = str(entry.get("role") or "").strip() or "Experience"
            lines.append(f"### {role}")
            for bullet in list(entry.get("bullets") or []):
                if isinstance(bullet, dict):
                    bullet_text = str(bullet.get("text") or "").strip()
                else:
                    bullet_text = str(bullet).strip()
                if bullet_text:
                    lines.append(f"- {bullet_text}")
    return "\n".join(lines)


def _load_fitcv_langgraph_runtime() -> _LanggraphRuntimeBridge | None:
    runtime_runner = globals().get("run_cv_generation_from_analysis")
    runtime_loader = globals().get("load_live_provider_config_from_env")
    repo_root = _discover_fitcv_langgraph_repo_root()
    if repo_root is None:
        return None
    env_file = _resolve_fitcv_langgraph_env_file(repo_root)
    env_values = dict(os.environ)
    if env_file is not None:
        env_values.update(_parse_env_file(env_file))

    if runtime_loader is None or runtime_runner is None:
        src_root = repo_root / "src"
        if src_root.is_dir():
            src_root_text = str(src_root)
            if src_root_text not in sys.path:
                sys.path.insert(0, src_root_text)
        live_module = importlib.import_module("fitcv_langgraph.providers.live")
        graph_module = importlib.import_module("fitcv_langgraph.graphs.cv_generation.graph")
        runtime_loader = getattr(live_module, "load_live_provider_config_from_env")
        runtime_runner = getattr(graph_module, "run_cv_generation_from_analysis")

    runtime_loader(env_values)
    return {
        "env_values": env_values,
        "run_from_analysis": runtime_runner,
    }


def _run_fitcv_langgraph_live_generation(
    analysis_record: dict[str, Any],
    profile: dict[str, Any],
    job: dict[str, Any],
) -> CvGenerationResult | None:
    runtime = _load_fitcv_langgraph_runtime()
    if runtime is None:
        return None
    analysis_payload = _build_generation_ready_analysis(analysis_record, profile, job)
    with _temporary_environ(runtime["env_values"]):
        state = runtime["run_from_analysis"](analysis_payload, execution_mode="live")
    final_result = state.get("final_result")
    if not isinstance(final_result, dict):
        return None
    comparison_output = dict(final_result.get("comparison_output") or {})
    comparison_validation = dict(final_result.get("comparison_validation") or {})
    draft = comparison_output.get("draft")
    structured_cv = dict(draft) if isinstance(draft, dict) else None
    markdown = _render_langgraph_draft_markdown(structured_cv, profile)
    repair_attempts = list(state.get("repair_attempts") or [])
    repair_attempt: RepairAttempt = {
        "performed": bool(repair_attempts),
        "missing_sections": list(comparison_validation.get("missing_sections") or []),
    }
    if repair_attempts:
        repair_attempt["reason"] = str(repair_attempts[0].get("repair_class") or "")
    validation_payload = {
        "valid": str(final_result.get("status") or "") == ACCEPTED_STATUS,
        "missing_sections": list(comparison_validation.get("missing_sections") or []),
        "grounding_violations": list(comparison_validation.get("unsupported_claim_ids") or []),
        "deterministic_grounding_violations": list(comparison_validation.get("unsupported_claim_ids") or []),
        "semantic_grounding_violations": [],
        "skill_violations": [],
        "warnings": [],
        "support_source_summary": {},
    }
    return _build_result(
        analysis_record=analysis_record,
        job=job,
        status=(
            ACCEPTED_STATUS
            if str(final_result.get("status") or "") == ACCEPTED_STATUS
            else VALIDATION_FAILED_STATUS
        ),
        fit_classification=_coerce_fit_classification(analysis_record.get("fit_classification")),
        structured_cv_initial=structured_cv,
        validation_initial=_build_validation_snapshot(validation_payload),
        repair_attempt=repair_attempt,
        structured_cv_final=structured_cv if str(final_result.get("status") or "") == ACCEPTED_STATUS else None,
        markdown_final=markdown if str(final_result.get("status") or "") == ACCEPTED_STATUS else None,
        validation=validation_payload,
        error=None if str(final_result.get("status") or "") == ACCEPTED_STATUS else {
            "stage": "validation",
            "message": "fitcv-langgraph live provider rejected the draft.",
        },
    )


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


def _normalize_candidate_name_token(value: str) -> str:
    normalized = str(value or "")
    normalized = normalized.replace("[", " ").replace("]", " ")
    return " ".join(normalized.split()).strip().lower()


def _is_candidate_name_placeholder(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return _normalize_candidate_name_token(value) in _CANDIDATE_NAME_PLACEHOLDER_VALUES


def _resolved_candidate_profile_name(profile: dict[str, Any] | None) -> str:
    if not isinstance(profile, dict):
        return ""
    candidate_name = str(profile.get("name") or "").strip()
    if not candidate_name or _is_candidate_name_placeholder(candidate_name):
        return ""
    return candidate_name


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
    if not _resolved_candidate_profile_name(profile):
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
    return _is_candidate_name_placeholder(header.get("name"))


def _should_retry_missing_sections(validation: dict[str, Any]) -> bool:
    missing_sections = list(validation.get("missing_sections") or [])
    if not missing_sections:
        return False
    return all(not validation.get(field) for field in _REPAIRABLE_VALIDATION_FIELDS)


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


def _build_validation_snapshot(validation: dict[str, Any] | None) -> ValidationSnapshot | None:
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
    }


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
    header["name"] = _resolved_candidate_profile_name(profile)
    repaired_markdown = render_cv_markdown(repaired_structured_cv, config)
    return repaired_structured_cv, repaired_markdown


def _unwrap_generated_cv(generated_cv: Any) -> tuple[dict[str, Any] | None, str]:
    if isinstance(generated_cv, dict):
        markdown = str(generated_cv.get("markdown") or "")
        structured_cv = generated_cv.get("structured_cv")
        if isinstance(structured_cv, dict):
            return structured_cv, markdown
        return None, markdown
    return None, str(generated_cv)


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

    return {
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


def generate_from_analysis(
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
        )

    live_provider_result = _run_fitcv_langgraph_live_generation(
        analysis_record=analysis_record,
        profile=profile,
        job=job,
    )
    if live_provider_result is not None:
        return live_provider_result

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
    gap_summary = analysis_record.get("gap_summary") or {}
    fit = str(fit_classification or "skip")
    structured_cv_initial: dict[str, Any] | None = None
    validation_initial: ValidationSnapshot | None = None
    repair_attempt = _empty_repair_attempt()

    try:
        generated_cv = generate_cv(
            job,
            evidence_payload,
            gap_summary,
            profile,
            config,
            fit_classification=fit,
            evidence_selection_summary=dict(analysis_record.get("evidence_selection_summary") or {}),
        )
        structured_cv, markdown = _unwrap_generated_cv(generated_cv)
        structured_cv_initial = structured_cv

        validation = run_all_validations(
            markdown,
            profile,
            config,
            structured_cv=structured_cv,
            analysis_grounding=analysis_grounding,
        )
        validation_initial = _build_validation_snapshot(validation)

        if not validation["valid"] and _should_repair_candidate_name_placeholder(validation, structured_cv, profile):
            repair_attempt = _build_candidate_name_repair_attempt()
            structured_cv, markdown = _repair_candidate_name_placeholder(structured_cv or {}, profile, config)
            validation = run_all_validations(
                markdown,
                profile,
                config,
                structured_cv=structured_cv,
                analysis_grounding=analysis_grounding,
            )

        if not validation["valid"] and _should_retry_missing_sections(validation):
            missing_sections = list(validation.get("missing_sections") or [])
            repair_attempt = _build_repair_attempt(missing_sections)
            generated_cv = generate_cv(
                job,
                evidence_payload,
                gap_summary,
                profile,
                config,
                fit_classification=fit,
                evidence_selection_summary=dict(analysis_record.get("evidence_selection_summary") or {}),
                repair_missing_sections=missing_sections,
            )
            structured_cv, markdown = _unwrap_generated_cv(generated_cv)
            validation = run_all_validations(
                markdown,
                profile,
                config,
                structured_cv=structured_cv,
                analysis_grounding=analysis_grounding,
            )

        if not validation["valid"]:
            return _build_result(
                analysis_record=analysis_record,
                job=job,
                status=VALIDATION_FAILED_STATUS,
                fit_classification=fit_classification,
                structured_cv_initial=structured_cv_initial,
                validation_initial=validation_initial,
                repair_attempt=repair_attempt,
                structured_cv_final=None,
                markdown_final=None,
                validation=validation,
                error={
                    "stage": "validation",
                    "message": f"CV validation failed for {extract_job_url(job)}",
                },
            )

        return _build_result(
            analysis_record=analysis_record,
            job=job,
            status=ACCEPTED_STATUS,
            fit_classification=fit_classification,
            structured_cv_initial=structured_cv_initial,
            validation_initial=validation_initial,
            repair_attempt=repair_attempt,
            structured_cv_final=structured_cv,
            markdown_final=markdown,
            validation=validation,
            error=None,
        )
    except Exception as exc:
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
            error={
                "stage": "generation",
                "message": str(exc),
            },
        )
