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
import math
from pathlib import Path
import os
import re
import time
import uuid
from typing import Any, Callable, Literal, TypedDict, cast

from fitcv.agentic_cv_analysis import (
    FitClassification,
    build_analysis_input_summary,
    build_decision_chain,
    build_evidence_used,
    extract_job_title,
    extract_job_url,
)
from fitcv.evidence import _descriptor_requirement_ref
from fitcv.candidate_name_policy import is_candidate_name_placeholder, resolved_candidate_profile_name
from fitcv.config import (
    get_cv_acceptance_policy,
    get_cv_generation_model,
    get_cv_generation_prompt_version,
    get_cv_generation_structured_prompt_id,
)
from fitcv.contracts import FINAL_ARTIFACT_CONTRACT_VERSION, TRACE_CONTRACT_VERSION
from fitcv.runtime_routing import resolve_cv_generation_routing_snapshot
from fitcv.cv_generator import (
    _execute_cv_generation_runtime,
    _get_enabled_section_names,
    _resolve_template_path,
    _canonical_render_item_key,
    _render_config_fingerprint,
    _template_sha256,
    build_live_structured_cv_response_schema as _canonical_live_structured_cv_response_schema,
    build_render_proof_identity,
    final_artifact_acceptance_passes,
    generate_cv,
    render_cv_markdown,
    render_cv_native_acceptance,
    render_item_requirement_support,
    render_proof_matches,
    trim_structured_cv_for_page_fit,
)
from fitcv.late_stage_contract import (
    CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS as BLOCKED_BY_RERANKER_STATUS,
    CV_ANALYSIS_READY_FOR_GENERATION_STATUS as READY_FOR_GENERATION_STATUS,
    CV_ANALYSIS_SKIPPED_FIT_GATE_STATUS as SKIPPED_FIT_GATE_STATUS,
    CV_GENERATION_ACCEPTED_STATUS as ACCEPTED_STATUS,
    CV_GENERATION_FAILED_STATUS as GENERATION_FAILED_STATUS,
    CV_GENERATION_REVIEW_REQUIRED_STATUS as REVIEW_REQUIRED_STATUS,
    CV_GENERATION_VALIDATION_FAILED_STATUS as VALIDATION_FAILED_STATUS,
    GenerationStatus,
)
from fitcv.pipeline_contracts import ReviewRequiredReasonCode, classify_cv_outcome
from fitcv.pipeline_stages.common import job_identity_keys
from fitcv.reuse import build_reuse_decision
from fitcv.validator import AnalysisGroundingPayload, run_all_validations
DEFAULT_MAX_SUMMARY_LINES = 3
CV_CONTENT_PLAN_VERSION = "cv_content_plan_v1"
DEFAULT_SECTION_CLAIM_LIMITS = {
    "summary": 3,
    "experience": 6,
    "projects": 4,
    "education": 2,
    "certifications": 2,
}

_REPAIRABLE_VALIDATION_FIELDS = ("grounding_violations", "skill_violations")


def _evidence_score_for_sort(value: Any) -> float:
    if isinstance(value, bool):
        return 0.0
    try:
        score = float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
    return score if math.isfinite(score) else 0.0


def build_generation_preflight(
    analysis_record: dict[str, Any],
    content_plan: dict[str, Any],
) -> dict[str, Any]:
    evidence = [
        item for item in list(analysis_record.get("evidence_payload") or []) if isinstance(item, dict)
    ]
    evidence_ids = {
        str(item.get("evidence_id") or item.get("claim_id") or "").strip()
        for item in evidence
        if str(item.get("evidence_id") or item.get("claim_id") or "").strip()
    }
    approved_claims = [
        item for item in list(content_plan.get("approved_claims") or []) if isinstance(item, dict)
    ]
    limits = dict(dict(content_plan.get("space_budget") or {}).get("section_claim_limits") or {})
    section_counts: dict[str, int] = {}
    invalid_claims: list[str] = []
    for claim in approved_claims:
        section = str(claim.get("target_section") or "").strip()
        claim_id = str(claim.get("claim_id") or claim.get("evidence_id") or "").strip()
        section_counts[section] = section_counts.get(section, 0) + 1
        if not claim_id or claim_id not in evidence_ids or not list(claim.get("supports_requirements") or []):
            invalid_claims.append(claim_id or "missing_claim_id")
    impossible_requirements = [
        str(item.get("requirement_instance_id") or item.get("requirement") or "").strip()
        for item in list(analysis_record.get("requirement_coverage") or [])
        if isinstance(item, dict)
        and str(item.get("selected_support") or "").strip().lower() == "verified"
        and not list(item.get("supporting_evidence_ids") or [])
        and str(item.get("requirement_instance_id") or item.get("requirement") or "").strip()
    ]
    checks = {
        "evidence_available": bool(evidence),
        "section_budget": all(
            count <= int(limits.get(section, count)) for section, count in section_counts.items()
        ),
        "grounded_high_value_claims": bool(approved_claims) and not invalid_claims,
        "impossible_requirements": not impossible_requirements,
    }
    blocking_reasons: list[str] = []
    if not checks["evidence_available"]:
        blocking_reasons.append("no_selected_evidence")
    if not checks["section_budget"]:
        blocking_reasons.append("section_budget_exceeded")
    if not checks["grounded_high_value_claims"]:
        blocking_reasons.append("ungrounded_high_value_claims")
    blocking_reasons.extend(f"impossible_requirement_support:{item}" for item in impossible_requirements)
    return {
        "schema_version": "cv_generation_preflight_v1",
        "status": "ready" if not blocking_reasons else "review",
        "provider_call_count_effect": 0,
        "checks": checks,
        "blocking_reasons": blocking_reasons,
    }


class RepairAttempt(TypedDict, total=False):
    performed: bool
    missing_sections: list[str]
    reason: str
    local_repair_attempted: bool
    local_repair_succeeded: bool
    local_repair_failed: bool
    provider_retry_attempted: bool
    provider_retry_succeeded: bool
    failure_category: str
    targeted_generation_attempted: bool
    targeted_generation_succeeded: bool
    full_regeneration_attempted: bool
    full_regeneration_succeeded: bool
    review_required: bool


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
    final_artifact_contract_version: str
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
    quality_warnings: list[str]
    outcome_reason: ErrorPayload | None
    error: ErrorPayload | None
    review_required_reason_code: str | None
    validation_evidence_fingerprint: str
    page_fit_status: str | None
    render_acceptance: dict[str, Any] | None
    trim_count: int
    trimmed_claim_ids: list[str]
    trim_reason: str | None
    post_trim_validation_status: str
    post_trim_missing_requirements: list[str]
    llm_runtime_observations: list[dict[str, Any]]
    cv_generation_trace: dict[str, Any]
    content_plan: dict[str, Any]
    uncertainties: list[dict[str, Any]]
    render_item_provenance: list[dict[str, Any]]
    content_acceptance: bool
    final_artifact_acceptance: dict[str, Any]
    render_acceptance: dict[str, Any]
    page_fit_status: str | None
    artifact_checksum: str | None
    trim_attempt_count: int


def build_cv_content_plan(
    analysis_record: dict[str, Any],
    job: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build deterministic approved claims from verified requirement coverage."""
    evidence = [item for item in list(analysis_record.get("evidence_payload") or []) if isinstance(item, dict)]
    coverage = [item for item in list(analysis_record.get("requirement_coverage") or []) if isinstance(item, dict)]
    support_by_evidence: dict[str, list[str]] = {}
    requirement_groups: dict[str, str] = {}
    for row in coverage:
        if str(row.get("selected_support") or "").strip().lower() != "verified":
            continue
        requirement_ref = _descriptor_requirement_ref(row)
        requirement_group = str(
            row.get("requirement") or row.get("canonical_skill") or row.get("requirement_id") or ""
        ).strip().casefold()
        if not requirement_group:
            requirement_group = re.sub(r"(?:[-:]\d+)+$", "", requirement_ref.casefold())
            requirement_group = re.sub(r"-[a-z0-9-]+$", "", requirement_group)
        requirement_groups[requirement_ref] = requirement_group
        for evidence_id in list(row.get("supporting_evidence_ids") or []):
            evidence_key = str(evidence_id).strip()
            if evidence_key and requirement_ref:
                support_by_evidence.setdefault(evidence_key, []).append(requirement_ref)

    approved_candidates: list[tuple[dict[str, Any], list[str], str, set[str]]] = []
    omitted_evidence: list[dict[str, Any]] = []
    for item in evidence:
        evidence_id = str(item.get("evidence_id") or item.get("claim_id") or "").strip()
        if not evidence_id:
            continue
        requirement_ids = list(dict.fromkeys(support_by_evidence.get(evidence_id) or []))
        if requirement_ids:
            source_section = str(item.get("source_section") or "").strip().lower()
            target_section = {
                "experiences": "experience",
                "projects": "projects",
                "education": "education",
                "certifications": "certifications",
                "volunteering": "experience",
            }.get(source_section, "summary")
            approved_candidates.append(
                (dict(item), requirement_ids, target_section, {requirement_groups.get(ref, ref) for ref in requirement_ids})
            )
        else:
            omitted_evidence.append({"evidence_id": evidence_id, "reason": "no_verified_requirement_support"})
    approved_claims: list[dict[str, Any]] = []
    section_counts: dict[str, int] = {}
    remaining = list(approved_candidates)
    covered_groups: set[str] = set()
    while remaining:
        eligible = [
            candidate
            for candidate in remaining
            if section_counts.get(candidate[2], 0) < DEFAULT_SECTION_CLAIM_LIMITS.get(candidate[2], 2)
        ]
        if not eligible:
            break
        item, requirement_ids, target_section, groups = min(
            eligible,
            key=lambda candidate: (
                -len(candidate[3] - covered_groups),
                -_evidence_score_for_sort(candidate[0].get("score")),
                -len({str(skill).strip().casefold() for skill in list(candidate[0].get("skills") or []) if str(skill).strip()}),
                str(candidate[0].get("evidence_id") or candidate[0].get("claim_id") or ""),
            ),
        )
        remaining.remove((item, requirement_ids, target_section, groups))
        evidence_id = str(item.get("evidence_id") or item.get("claim_id") or "").strip()
        limit = DEFAULT_SECTION_CLAIM_LIMITS.get(target_section, 2)
        if section_counts.get(target_section, 0) >= limit:
            omitted_evidence.append({"evidence_id": evidence_id, "reason": "space_budget_exceeded"})
            continue
        section_counts[target_section] = section_counts.get(target_section, 0) + 1
        covered_groups.update(groups)
        approved_claims.append(
            {
                "claim_id": evidence_id,
                "evidence_id": evidence_id,
                "claim": str(item.get("text") or item.get("name") or "").strip(),
                "supports_requirements": requirement_ids,
                "target_section": target_section,
                "source_section": str(item.get("source_section") or "").strip().lower() or None,
                "source_ref": str(item.get("source_ref") or "").strip() or None,
                "canonical_source_id": str(
                    item.get("canonical_source_id")
                    or item.get("parent_id")
                    or item.get("source_ref")
                    or evidence_id
                ).strip(),
                "canonical_source_label": str(
                    item.get("parent_title") or item.get("name") or item.get("title") or ""
                ).strip() or None,
                "protected_numbers_dates": _protected_numbers_dates(item),
            }
        )
    for item, _, _, _ in remaining:
        omitted_evidence.append(
            {
                "evidence_id": str(item.get("evidence_id") or item.get("claim_id") or "").strip(),
                "reason": "space_budget_exceeded",
            }
        )
    plan = {
        "schema_version": CV_CONTENT_PLAN_VERSION,
        "analysis_input_fingerprint": str(analysis_record.get("analysis_input_fingerprint") or ""),
        "approved_evidence_ids": [str(item["evidence_id"]) for item in approved_claims],
        "approved_claims": approved_claims,
        "supported_requirements": sorted({req for item in approved_claims for req in item["supports_requirements"]}),
        "target_section": "full_document",
        "space_budget": {
            "max_summary_lines": DEFAULT_MAX_SUMMARY_LINES,
            "section_claim_limits": dict(DEFAULT_SECTION_CLAIM_LIMITS),
            "page_count": 1,
            "page_fit_status": "unverified",
            "enabled_sections": sorted(_get_enabled_section_names(config or {})),
        },
        "omitted_evidence": omitted_evidence,
    }
    plan["generation_preflight"] = build_generation_preflight(analysis_record, plan)
    plan["content_fingerprint"] = hashlib.sha256(
        json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return plan


def build_render_item_provenance_v1(
    *,
    content_plan: dict[str, Any],
    evidence_payload: list[dict[str, Any]],
    requirement_coverage: list[dict[str, Any]],
    structured_cv: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build host-owned trim metadata without changing provider output schema."""
    evidence_by_id = {
        str(item.get("evidence_id") or item.get("claim_id") or "").strip(): item
        for item in evidence_payload
        if isinstance(item, dict) and str(item.get("evidence_id") or item.get("claim_id") or "").strip()
    }
    approved_claims = [
        item for item in list(content_plan.get("approved_claims") or []) if isinstance(item, dict)
    ]
    verified_by_requirement: dict[str, set[str]] = {}
    for row in requirement_coverage:
        if not isinstance(row, dict) or str(row.get("selected_support") or "").strip().lower() != "verified":
            continue
        requirement_ref = _descriptor_requirement_ref(row)
        if requirement_ref:
            verified_by_requirement[requirement_ref] = {
                str(value).strip()
                for value in list(row.get("supporting_evidence_ids") or [])
                if str(value).strip()
            }

    def _text_tokens(value: Any, *, minimum_length: int = 3) -> set[str]:
        return {
            token
            for token in re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).split()
            if len(token) >= minimum_length
        }

    requirement_namespace_tokens = {
        "required",
        "preferred",
        "optional",
        "skill",
        "skills",
        "language",
        "languages",
        "experience",
        "year",
        "years",
        "level",
        "requirement",
        "requirements",
        "instance",
        "support",
        "supports",
    }

    claim_entries: list[dict[str, Any]] = []
    for claim in approved_claims:
        evidence_id = str(claim.get("evidence_id") or claim.get("claim_id") or "").strip()
        claim_text = str(claim.get("claim") or "").strip()
        evidence_text = str((evidence_by_id.get(evidence_id) or {}).get("text") or "").strip()
        claim_entries.append(
            {
                "section": str(claim.get("target_section") or "summary").strip().lower(),
                "tokens": _text_tokens(f"{claim_text} {evidence_text}"),
                "support_tokens": _text_tokens(
                    " ".join(str(value) for value in list(claim.get("supports_requirements") or [])),
                    minimum_length=1,
                ) - requirement_namespace_tokens,
                "evidence_ids": [evidence_id] if evidence_id else [],
                "supported_requirement_ids": [
                    str(value).strip()
                    for value in list(claim.get("supports_requirements") or [])
                    if str(value).strip()
                ],
                "source_section": str(claim.get("source_section") or "").strip().lower(),
                "source_ref": str(claim.get("source_ref") or "").strip(),
                "canonical_source_id": str(claim.get("canonical_source_id") or "").strip(),
                "canonical_source_label": str(claim.get("canonical_source_label") or "").strip(),
            }
        )

    strict_source_claims = any(
        claim["canonical_source_id"] or claim["canonical_source_label"]
        for claim in claim_entries
    )

    def _identity(value: Any) -> str:
        return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold())).strip()

    def _claim_identity_keys(claim: dict[str, Any]) -> set[str]:
        keys = {
            value
            for value in (
                claim.get("canonical_source_id"),
                claim.get("source_ref"),
                claim.get("canonical_source_label"),
            )
            if str(value or "").strip()
        }
        return {_identity(value) for value in keys if _identity(value)}

    def _item_identity_keys(section: str, item: dict[str, Any]) -> set[str]:
        values = [item.get("canonical_source_id"), item.get("source_ref"), item.get("evidence_id")]
        if section == "experience":
            values.extend((item.get("role"), item.get("company"), item.get("name")))
        elif section == "projects":
            values.append(item.get("name"))
        elif section == "education":
            values.extend((item.get("degree"), item.get("institution"), item.get("name")))
        elif section == "certifications":
            values.extend((item.get("name"), item.get("title"), item.get("issuer")))
        elif section == "languages":
            values.append(item.get("name"))
        else:
            values.extend((item.get("name"), item.get("title")))
        return {_identity(value) for value in values if _identity(value)}

    items: list[dict[str, Any]] = []
    sections = structured_cv.get("sections") if isinstance(structured_cv, dict) else None
    if not isinstance(sections, dict):
        for claim in claim_entries:
            canonical_key = f"{claim['section']}:{' '.join(sorted(claim['tokens']))}"
            items.append(
                {
                    "item_id": hashlib.sha256(canonical_key.encode("utf-8")).hexdigest(),
                    "section": claim["section"],
                    "canonical_item_key": canonical_key,
                    "evidence_ids": claim["evidence_ids"],
                    "supported_requirement_ids": claim["supported_requirement_ids"],
                    "requirement_priority": "primary" if claim["supported_requirement_ids"] else "none",
                    "protected": bool(claim["supported_requirement_ids"]),
                }
            )
        return {"schema_version": "render_item_provenance_v1", "items": items}

    def _claim_matches_item(claim: dict[str, Any], item_tokens: set[str]) -> bool:
        if not claim["tokens"] or len(item_tokens & claim["tokens"]) < 2:
            return False
        support_tokens = set(claim.get("support_tokens") or [])
        return not support_tokens or bool(item_tokens & support_tokens)

    for section in ("experience", "projects", "education", "certifications", "publications", "languages"):
        section_items = sections.get(section)
        if not isinstance(section_items, list):
            continue
        section_claims = [
            claim
            for claim in claim_entries
            if claim["section"] == section and claim["supported_requirement_ids"]
        ]
        section_matched_required_claims: set[int] = set()
        for candidate in section_items:
            if not isinstance(candidate, dict):
                continue
            candidate_tokens = _text_tokens(
                " ".join(str(value) for value in candidate.values()),
                minimum_length=1,
            )
            section_matched_required_claims.update(
                id(claim)
                    for claim in claim_entries
                    if claim["section"] == section
                    and claim["supported_requirement_ids"]
                    and _claim_matches_item(claim, candidate_tokens)
            )
        if len(section_items) == 1 and len(section_claims) == 1 and not section_matched_required_claims:
            section_matched_required_claims.add(id(section_claims[0]))
        for item in section_items:
            if not isinstance(item, dict):
                continue
            canonical_key = _canonical_render_item_key(section, item)
            item_tokens = _text_tokens(
                " ".join(str(value) for value in item.values()),
                minimum_length=1,
            )
            if strict_source_claims:
                item_identity_keys = _item_identity_keys(section, item)
                source_matches = [
                    claim
                    for claim in claim_entries
                    if claim["section"] == section
                    and item_identity_keys.intersection(_claim_identity_keys(claim))
                ]
                matched_source_ids = {
                    claim["canonical_source_id"] or claim["source_ref"] or claim["evidence_ids"][0]
                    for claim in source_matches
                }
                ambiguous = len(matched_source_ids) > 1
                matches = [] if ambiguous else source_matches
                attribution_status = (
                    "ambiguous"
                    if ambiguous
                    else "resolved"
                    if matches
                    else "unmatched"
                )
            else:
                matches = [
                    claim
                    for claim in claim_entries
                    if claim["section"] == section and _claim_matches_item(claim, item_tokens)
                ]
                if not matches:
                    if len(section_items) == 1 and len(section_claims) == 1:
                        matches = section_claims
                ambiguous = len(matches) > 1
                attribution_status = "ambiguous" if ambiguous else "resolved" if matches else "unmatched"
            unresolved_required = any(
                id(claim) not in section_matched_required_claims for claim in section_claims
            )
            supported_ids = sorted({value for match in matches for value in match["supported_requirement_ids"]})
            evidence_ids = sorted({value for match in matches for value in match["evidence_ids"]})
            if section == "languages" and not strict_source_claims:
                language_name = str(item.get("name") or "").strip().casefold()
                for requirement_ref in verified_by_requirement:
                    if language_name and language_name in requirement_ref.casefold():
                        supported_ids.append(requirement_ref)
                        evidence_ids.extend(sorted(verified_by_requirement[requirement_ref]))
            supported_ids = sorted(set(supported_ids))
            items.append(
                {
                    "item_id": hashlib.sha256(canonical_key.encode("utf-8")).hexdigest(),
                    "section": section,
                    "canonical_item_key": canonical_key,
                    "evidence_ids": sorted(set(evidence_ids)),
                    "supported_requirement_ids": supported_ids,
                    "requirement_priority": "primary" if supported_ids else "none",
                    "attribution_status": attribution_status,
                    "protected": (
                        ambiguous
                        or bool(supported_ids)
                        or unresolved_required
                        or (strict_source_claims and bool(section_claims) and attribution_status == "unmatched")
                    ),
                }
            )
    return {"schema_version": "render_item_provenance_v1", "items": items}


def _protected_numbers_dates(item: dict[str, Any]) -> list[str]:
    text = str(item.get("text") or item.get("name") or "")
    return list(dict.fromkeys(re.findall(r"\b(?:\d+(?:[.,]\d+)?|\d{4}|\d{1,2}/\d{4})\b", text)))


def merge_repaired_section(
    existing_cv: dict[str, Any],
    section_name: str,
    repaired_section_data: Any,
) -> dict[str, Any]:
    allowed = {"header", "summary", "experience", "projects", "education", "skills", "certifications", "publications", "languages"}
    section = str(section_name or "").strip().lower()
    if section not in allowed:
        raise ValueError(f"unknown CV section: {section_name}")
    merged = deepcopy(existing_cv)
    sections = merged.setdefault("sections", {})
    if not isinstance(sections, dict):
        raise ValueError("structured CV sections must be a mapping")
    sections[section] = deepcopy(repaired_section_data)
    return merged

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
        "failure_category": "none",
        "targeted_generation_attempted": False,
        "targeted_generation_succeeded": False,
        "full_regeneration_attempted": False,
        "full_regeneration_succeeded": False,
        "review_required": False,
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
    config: dict[str, Any] | None = None,
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
        "content_plan": build_cv_content_plan(analysis_record, job, config),
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
    trace_id: str,
) -> dict[str, Any]:
    return {
        "trace_id": str(trace_id),
        "trace_schema_version": _LIVE_TRACE_SCHEMA_VERSION,
        "trace_contract_version": TRACE_CONTRACT_VERSION,
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
            "local_repair_attempted": False,
            "local_repair_succeeded": False,
            "local_repair_failed": False,
            "provider_retry_attempted": False,
            "provider_retry_succeeded": False,
        },
        "efficiency_summary": {
            "schema_version": "accepted_cv_efficiency_v1",
            "status": "not_run",
            "elapsed_ms": None,
            "provider_call_count": 0,
            "token_usage": None,
            "token_usage_status": "not_run",
            "input_token_estimate": 0,
            "approved_input_token_estimate": 0,
            "regeneration_count": 0,
            "review_question_count": "not_applicable",
            "human_action_count": "not_applicable",
            "stage_timings": {
                key: {"value": None, "status": "unavailable", "owner": owner, "denominator": denominator}
                for key, owner, denominator in (
                    ("queue_wait_ms", "worker_boundary", "generation_attempts"),
                    ("analysis_ms", "analysis", "generation_attempts"),
                    ("retrieval_ms", "analysis", "retrieval_calls"),
                    ("content_planning_ms", "generation", "generation_attempts"),
                    ("provider_ms", "generation", "provider_calls"),
                    ("validation_ms", "generation", "validation_cycles"),
                    ("local_repair_ms", "generation", "repair_attempts"),
                    ("render_ms", "artifact_boundary", "render_calls"),
                    ("persistence_ms", "store_boundary", "persisted_artifacts"),
                )
            },
            "failure_causes": [],
            "savings": {
                "local_repair_attempted": False,
                "local_repair_succeeded": False,
                "local_repair_failed": False,
                "provider_retry_avoided": {"value": None, "status": "unavailable"},
                "tokens_avoided": {"value": None, "status": "unavailable"},
                "provider_latency_avoided": {"value": None, "status": "unavailable"},
                "proof_reuse": {"value": None, "status": "unavailable"},
                "provider_calls_avoided": {"value": None, "status": "unavailable"},
                "renders_avoided": {"value": None, "status": "unavailable"},
                "questions_avoided": {"value": None, "status": "unavailable"},
                "review_time_ms": {"value": None, "status": "unavailable"},
            },
        },
        "error_summary": None,
    }


def _update_efficiency_summary(
    trace_payload: dict[str, Any],
    *,
    input_metrics: dict[str, Any],
    started_at: float,
    status: str,
    review_question_count: int,
) -> None:
    attempts = [
        dict(item)
        for item in list(trace_payload.get("attempts") or [])
        if isinstance(item, dict)
    ]
    usage_blocks = []
    for attempt in attempts:
        evidence = attempt.get("llm_runtime_evidence")
        telemetry = evidence.get("telemetry") if isinstance(evidence, dict) else None
        usage = telemetry.get("usage") if isinstance(telemetry, dict) else None
        if isinstance(usage, dict) and usage:
            usage_blocks.append(dict(usage))
    summary = dict(trace_payload.get("efficiency_summary") or {})
    summary.update(
        {
            "schema_version": "accepted_cv_efficiency_v1",
            "status": "accepted" if status == ACCEPTED_STATUS else "not_accepted",
            "elapsed_ms": max(0, int((time.monotonic() - started_at) * 1000)),
            "provider_call_count": len(attempts),
            "token_usage": usage_blocks or None,
            "token_usage_status": "available" if usage_blocks else "not_run",
            "input_token_estimate": int(input_metrics.get("full_input_token_estimate") or 0),
            "approved_input_token_estimate": int(input_metrics.get("approved_input_token_estimate") or 0),
            "regeneration_count": max(len(attempts) - 1, 0),
            "review_question_count": int(review_question_count),
            "human_action_count": "not_applicable",
        }
    )
    stage_timings = dict(summary.get("stage_timings") or {})
    latency_values = []
    for attempt in attempts:
        evidence = attempt.get("llm_runtime_evidence")
        provenance = evidence.get("provenance") if isinstance(evidence, dict) else None
        latency = provenance.get("latency_ms") if isinstance(provenance, dict) else None
        if isinstance(latency, (int, float)) and latency >= 0:
            latency_values.append(int(latency))
    provider_stage = dict(stage_timings.get("provider_ms") or {})
    provider_stage.update({
        "value": sum(latency_values) if latency_values else None,
        "status": "measured" if latency_values else "unavailable",
    })
    stage_timings["provider_ms"] = provider_stage
    repair_summary = dict(trace_payload.get("repair_summary") or {})
    savings = dict(summary.get("savings") or {})
    repair_attempted = bool(repair_summary.get("repair_attempted"))
    repair_kind = str(repair_summary.get("repair_kind") or "").strip()
    inferred_local_repair_attempted = repair_attempted and repair_kind in {
        "deterministic_section_backfill",
        "candidate_name_placeholder",
    }
    local_repair_attempted = bool(
        repair_summary.get("local_repair_attempted", inferred_local_repair_attempted)
    )
    local_repair_succeeded = bool(
        repair_summary.get(
            "local_repair_succeeded",
            local_repair_attempted and status == ACCEPTED_STATUS,
        )
    )
    local_repair_failed = bool(
        repair_summary.get(
            "local_repair_failed",
            local_repair_attempted and status != ACCEPTED_STATUS,
        )
    )
    savings.update({
        "local_repair_attempted": local_repair_attempted,
        "local_repair_succeeded": local_repair_succeeded,
        "local_repair_failed": local_repair_failed,
    })
    summary["stage_timings"] = stage_timings
    summary["savings"] = savings
    trace_payload["efficiency_summary"] = summary

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
    causes: list[str] = []
    if validation_summary.get("initial_missing_fields") or validation_summary.get("final_missing_fields"):
        causes.append("missing_sections")
    if validation_summary.get("initial_grounding_violation_count") or validation_summary.get("final_grounding_violation_count"):
        causes.append("unsupported_claims")
    if validation_summary.get("initial_skill_violation_count") or validation_summary.get("final_skill_violation_count"):
        causes.append("skill_constraints")
    if validation_summary.get("final_valid") is False and not causes:
        causes.append("validation_failed")
    efficiency = dict(trace_payload.get("efficiency_summary") or {})
    efficiency["failure_causes"] = sorted(set(causes))
    trace_payload["efficiency_summary"] = efficiency


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


def _generation_format_defect_category(validation: Mapping[str, Any]) -> str | None:
    if list(validation.get("missing_sections") or []):
        return "missing_mandatory_section"
    blocking_issues = [str(item).lower() for item in list(validation.get("markdown_quality_blocking_issues") or [])]
    if blocking_issues:
        if any("heading" in item or "schema" in item for item in blocking_issues):
            return "invalid_heading_or_schema"
        return "malformed_section"
    if any("length" in str(item).lower() or "budget" in str(item).lower() for item in list(validation.get("warnings") or [])):
        return "length_or_budget_violation"
    if list(validation.get("missing_required_fields") or []):
        return "missing_required_field"
    if not validation.get("valid") and not (
        list(validation.get("grounding_violations") or [])
        or list(validation.get("skill_violations") or [])
    ):
        return "other_deterministic_format_defect"
    return None


def _classify_repair_failure(
    validation: Mapping[str, Any],
    repair_targets: list[str],
) -> str:
    if bool(validation.get("valid")):
        return "none"
    if list(validation.get("markdown_quality_review_flags") or []):
        return "uncertainty"
    if _generation_format_defect_category(validation):
        return "deterministic"
    if repair_targets and (
        list(validation.get("grounding_violations") or [])
        or list(validation.get("skill_violations") or [])
    ):
        return "isolated_semantic"
    return "global_inconsistency"


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
        "requirement_coverage": list(analysis_record.get("requirement_coverage") or []),
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
    if not validation.get("valid"):
        failing_section = _first_failing_section_key(validation)
        if failing_section:
            return [failing_section]
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

_REPAIR_ARMS = frozenset({"provider_first", "local_first"})


def _coerce_repair_arm(value: Any) -> str:
    normalized = str(value or "local_first").strip().lower()
    return normalized if normalized in _REPAIR_ARMS else "local_first"


def _backfill_required_sections_from_profile(
    *,
    structured_cv: dict[str, Any] | None,
    profile: dict[str, Any],
    missing_sections: list[str] | None,
    selected_evidence_ids: list[str] | None = None,
    selection_present: bool | None = None,
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
    selection_is_present = (
        bool(selection_present)
        if selection_present is not None
        else selected_evidence_ids is not None
    )
    selection_state = (
        "EXPLICIT_NONEMPTY_SELECTION"
        if selection_is_present and selected_evidence_ids
        else "EXPLICIT_EMPTY_SELECTION"
        if selection_is_present
        else "LEGACY_UNAVAILABLE"
    )
    selected_ids = {
        str(item).strip()
        for item in list(selected_evidence_ids or [])
        if str(item).strip()
    }

    def selected_id_matches(candidate_id: Any, parent_id: str = "", *, allow_legacy_parent_prefix: bool = False) -> bool:
        normalized = str(candidate_id or "").strip()
        if not normalized:
            return False
        if normalized in selected_ids:
            return True
        if not allow_legacy_parent_prefix or not parent_id:
            return False
        return any(selected_id.startswith(f"ev_{parent_id}_") for selected_id in selected_ids)

    def selected_nested_evidence(entry: dict[str, Any]) -> list[dict[str, Any]]:
        nested = [item for item in list(entry.get("evidence") or []) if isinstance(item, dict)]
        if selection_state == "LEGACY_UNAVAILABLE":
            return nested
        if not nested:
            return []
        parent_id = str(entry.get("id") or "").strip()
        if parent_id in selected_ids:
            return nested
        return [
            item
            for item in nested
            if selected_id_matches(item.get("id"))
        ]

    def is_selected_profile_entry(entry: dict[str, Any]) -> bool:
        if selection_state == "LEGACY_UNAVAILABLE":
            return True
        if not selected_ids:
            return False
        nested = list(entry.get("evidence") or [])
        if nested:
            return bool(selected_nested_evidence(entry))
        evidence_refs = {
            str(item).strip()
            for item in list(entry.get("evidence_refs") or [])
            if str(item).strip()
        }
        if evidence_refs:
            return any(selected_id_matches(evidence_ref) for evidence_ref in evidence_refs)
        parent_id = str(entry.get("id") or "").strip()
        return selected_id_matches(parent_id, parent_id, allow_legacy_parent_prefix=True)

    def is_selected_plain_skill(value: Any) -> bool:
        if selection_state == "LEGACY_UNAVAILABLE":
            return True
        skill_name = str(value or "").strip().casefold()
        if not skill_name:
            return False
        for evidence in list(profile.get("_projected_evidence_pool") or []):
            if not isinstance(evidence, dict):
                continue
            evidence_skills = {
                str(item).strip().casefold()
                for item in list(evidence.get("skills") or [])
                if str(item).strip()
            }
            if skill_name in evidence_skills and selected_id_matches(evidence.get("evidence_id")):
                return True
        return False

    def is_selected_plain_language(value: Any) -> bool:
        return selection_state == "LEGACY_UNAVAILABLE"

    if "skills" in repair_keys:
        profile_skills: list[str] = []
        for item in list(profile.get("skills") or []):
            if isinstance(item, dict):
                if not is_selected_profile_entry(item):
                    continue
                value = str(item.get("name") or "").strip()
            else:
                if not is_selected_plain_skill(item):
                    continue
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
            eligible_experiences = [
                exp
                for exp in list(profile.get("experiences") or [])
                if isinstance(exp, dict) and is_selected_profile_entry(exp)
            ]
            for exp in eligible_experiences[:3]:
                if not isinstance(exp, dict):
                    continue
                nested_evidence = selected_nested_evidence(exp)
                if nested_evidence:
                    bullet_texts = [
                        str(item.get("text") or item.get("title") or "").strip()
                        for item in nested_evidence
                        if str(item.get("text") or item.get("title") or "").strip()
                    ][:2]
                else:
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
                    ][:2]
                has_experience_metadata = any(
                    str(exp.get(key) or "").strip()
                    for key in ("role", "company", "start", "end", "location")
                )
                if not bullet_texts and not has_experience_metadata:
                    continue
                fallback_experience.append(
                    {
                        "role": str(exp.get("role") or "").strip(),
                        "company": str(exp.get("company") or "").strip(),
                        "start": exp.get("start"),
                        "end": exp.get("end"),
                        "location": str(exp.get("location") or "").strip() or None,
                        "bullets": bullet_texts,
                    }
                )
            if fallback_experience:
                sections["experience"] = fallback_experience
                repaired_keys.append("experience")

    if "projects" in repair_keys:
        existing_projects = list(sections.get("projects") or [])
        if not existing_projects:
            fallback_projects: list[dict[str, Any]] = []
            eligible_projects = [
                project
                for project in list(profile.get("projects") or [])
                if isinstance(project, dict) and is_selected_profile_entry(project)
            ]
            for project in eligible_projects[:3]:
                if not isinstance(project, dict):
                    continue
                nested_evidence = selected_nested_evidence(project)
                if nested_evidence:
                    bullets = [
                        str(item.get("text") or item.get("title") or "").strip()
                        for item in nested_evidence
                        if str(item.get("text") or item.get("title") or "").strip()
                    ][:2]
                else:
                    bullets = [
                        str(item).strip()
                        for item in list(project.get("highlights") or project.get("bullets") or [])
                        if str(item).strip()
                    ][:2]
                if not bullets:
                    continue
                fallback_projects.append(
                    {
                        "name": str(project.get("name") or "").strip(),
                        "context": str(project.get("context") or project.get("period") or "").strip() or None,
                        "bullets": bullets,
                    }
                )
            if fallback_projects:
                sections["projects"] = fallback_projects
                repaired_keys.append("projects")

    if "education" in repair_keys:
        existing_education = list(sections.get("education") or [])
        if not existing_education:
            fallback_education = []
            eligible_education = [
                edu
                for edu in list(profile.get("education") or [])
                if isinstance(edu, dict) and is_selected_profile_entry(edu)
            ]
            for edu in eligible_education[:2]:
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
            eligible_languages = []
            for lang in list(profile.get("languages") or []):
                if isinstance(lang, dict):
                    if not is_selected_profile_entry(lang):
                        continue
                elif not is_selected_plain_language(lang):
                    continue
                eligible_languages.append(lang)
            for lang in eligible_languages[:5]:
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
    repair_arm: str | None = None,
) -> tuple[dict[str, Any] | None, str, dict[str, Any], RepairAttempt, dict[str, Any] | None]:
    repair_attempt = _empty_repair_attempt()
    repair_arm = _coerce_repair_arm(repair_arm or config.get("cv_generation_repair_arm"))
    if not validation["valid"] and _should_repair_candidate_name_placeholder(validation, structured_cv, profile):
        repair_attempt = _build_candidate_name_repair_attempt()
        repair_attempt["local_repair_attempted"] = True
        structured_cv, markdown = _repair_candidate_name_placeholder(structured_cv or {}, profile, config)
        validation = _run_generation_validations(
            markdown,
            profile=profile,
            config=config,
            structured_cv=structured_cv,
            analysis_grounding=analysis_grounding,
        )
        repair_attempt["local_repair_succeeded"] = bool(validation.get("valid"))
        repair_attempt["local_repair_failed"] = not repair_attempt["local_repair_succeeded"]

    selection_summary = (
        (analysis_grounding.get("evidence_selection_summary") or {})
        if isinstance(analysis_grounding, dict)
        else {}
    )
    selection_present = isinstance(selection_summary, dict) and "selected_evidence_ids" in selection_summary
    selected_evidence_ids = (
        list(selection_summary.get("selected_evidence_ids") or [])
        if selection_present
        else None
    )
    repair_targets = _determine_repair_targets(validation, structured_cv)
    failure_category = _classify_repair_failure(validation, repair_targets)
    repair_attempt["failure_category"] = failure_category
    if failure_category == "uncertainty":
        repair_attempt.update(
            {
                "reason": "review_required_uncertainty",
                "review_required": True,
            }
        )
        return structured_cv, markdown, validation, repair_attempt, runtime_provenance
    if repair_targets:
        if repair_arm == "local_first" and _generation_format_defect_category(validation) == "missing_mandatory_section":
            repaired_cv, repaired_keys = _backfill_required_sections_from_profile(
                structured_cv=structured_cv,
                profile=profile,
                missing_sections=list(validation.get("missing_sections") or []),
                selected_evidence_ids=selected_evidence_ids,
                selection_present=selection_present,
            )
            if repaired_keys:
                repair_attempt["local_repair_attempted"] = True
                repaired_markdown = render_cv_markdown(repaired_cv or {}, config)
                repaired_validation = _run_generation_validations(
                    repaired_markdown,
                    profile=profile,
                    config=config,
                    structured_cv=repaired_cv,
                    analysis_grounding=analysis_grounding,
                )
                structured_cv = repaired_cv
                markdown = repaired_markdown
                if repaired_validation.get("valid"):
                    repair_attempt.update(
                        {
                            "performed": True,
                            "missing_sections": repaired_keys,
                            "reason": "deterministic_section_backfill",
                            "local_repair_succeeded": True,
                        }
                    )
                    return (
                        repaired_cv,
                        repaired_markdown,
                        repaired_validation,
                        repair_attempt,
                        runtime_provenance,
                    )
                repair_attempt["local_repair_failed"] = True
        previous_repair_attempt = repair_attempt
        repair_attempt = _build_repair_attempt(repair_targets)
        for field in (
            "local_repair_attempted",
            "local_repair_succeeded",
            "local_repair_failed",
            "failure_category",
        ):
            if previous_repair_attempt.get(field):
                repair_attempt[field] = True
        repair_attempt["reason"] = (
            "provider_retry" if failure_category == "deterministic" else "targeted_generation"
        )
        repair_attempt["targeted_generation_attempted"] = True
        repair_attempt["provider_retry_attempted"] = True
        try:
            repaired_cv, repaired_markdown, validation, retry_provenance = retry_executor(repair_targets)
        except Exception as exc:
            setattr(exc, "repair_attempt", repair_attempt)
            raise
        if isinstance(structured_cv, dict) and isinstance(repaired_cv, dict):
            for section_name in repair_targets:
                section_key = str(section_name).strip().lower()
                repaired_sections = repaired_cv.get("sections")
                if isinstance(repaired_sections, dict) and section_key in repaired_sections:
                    replacement = repaired_sections[section_key]
                    existing_sections = structured_cv.get("sections") if isinstance(structured_cv, dict) else {}
                    existing_value = existing_sections.get(section_key) if isinstance(existing_sections, dict) else None
                    if not replacement and existing_value:
                        continue
                    structured_cv = merge_repaired_section(
                        structured_cv,
                        section_key,
                        replacement,
                    )
            markdown = render_cv_markdown(structured_cv, config)
            validation = _run_generation_validations(
                markdown,
                profile=profile,
                config=config,
                structured_cv=structured_cv,
                analysis_grounding=analysis_grounding,
            )
        else:
            structured_cv, markdown = repaired_cv, repaired_markdown
        if retry_provenance is not None:
            runtime_provenance = retry_provenance
        repair_attempt["failure_category"] = _classify_repair_failure(
            validation,
            _determine_repair_targets(validation, structured_cv),
        )
        repair_attempt["provider_retry_succeeded"] = bool(validation.get("valid"))
        repair_attempt["targeted_generation_succeeded"] = bool(validation.get("valid"))
        if repair_attempt["failure_category"] == "uncertainty":
            repair_attempt.update(
                {
                    "reason": "review_required_uncertainty",
                    "review_required": True,
                }
            )
            return structured_cv, markdown, validation, repair_attempt, runtime_provenance

    if repair_arm == "local_first" and not validation.get("valid") and not repair_attempt.get("local_repair_attempted"):
        structured_cv, repaired_keys = _backfill_required_sections_from_profile(
            structured_cv=structured_cv,
            profile=profile,
            missing_sections=list(validation.get("missing_sections") or []),
            selected_evidence_ids=selected_evidence_ids,
            selection_present=selection_present,
        )
        if repaired_keys:
            repair_attempt["local_repair_attempted"] = True
            markdown = render_cv_markdown(structured_cv or {}, config)
            validation = _run_generation_validations(
                markdown,
                profile=profile,
                config=config,
                structured_cv=structured_cv,
                analysis_grounding=analysis_grounding,
            )
            if validation.get("valid"):
                repair_attempt.update(
                    {
                        "performed": True,
                        "missing_sections": repaired_keys,
                        "reason": "deterministic_section_backfill",
                        "local_repair_succeeded": True,
                    }
                )
            else:
                repair_attempt["local_repair_failed"] = True

    if not validation.get("valid") and not repair_attempt.get("review_required"):
        repair_attempt["full_regeneration_attempted"] = True
        repair_attempt["reason"] = "full_regeneration"
        previous_structured_cv = structured_cv
        try:
            regenerated_cv, regenerated_markdown, regenerated_validation, regenerated_provenance = retry_executor([])
        except Exception as exc:
            setattr(exc, "repair_attempt", repair_attempt)
            raise
        candidate_validation = _run_generation_validations(
            regenerated_markdown,
            profile=profile,
            config=config,
            structured_cv=regenerated_cv,
            analysis_grounding=analysis_grounding,
        )
        if candidate_validation.get("valid"):
            structured_cv, markdown = regenerated_cv, regenerated_markdown
        else:
            structured_cv = previous_structured_cv
        validation = candidate_validation
        if not validation.get("valid") and regenerated_validation.get("valid"):
            structured_cv, markdown = regenerated_cv, regenerated_markdown
            validation = regenerated_validation
        if regenerated_provenance is not None:
            runtime_provenance = regenerated_provenance
        repair_attempt["failure_category"] = _classify_repair_failure(
            validation,
            _determine_repair_targets(validation, structured_cv),
        )
        if repair_attempt["failure_category"] == "uncertainty":
            repair_attempt.update(
                {
                    "reason": "review_required_uncertainty",
                    "review_required": True,
                }
            )
        repair_attempt["full_regeneration_succeeded"] = bool(validation.get("valid"))

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
    content_plan: dict[str, Any],
) -> Callable[[list[str] | None], Any]:
    provider_profile = {
        key: value
        for key, value in profile.items()
        if key not in {"candidate_profile_id", "revision"}
    }

    def _call(repair_missing_sections: list[str] | None) -> Any:
        return generate_cv(
            job,
            evidence_payload,
            gap_summary,
            provider_profile,
            config,
            fit_classification=fit,
            evidence_selection_summary=evidence_selection_summary,
            repair_missing_sections=repair_missing_sections,
            content_plan=content_plan,
            target_sections=repair_missing_sections,
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
        "content_plan": dict(analysis_record.get("content_plan") or {}),
        "uncertainties": [item for item in list(analysis_record.get("uncertainties") or []) if isinstance(item, dict)],
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
    if stage == "final_artifact_acceptance":
        return ReviewRequiredReasonCode.FINAL_ARTIFACT_ACCEPTANCE_FAILED
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
    trace_id: str,
    profile: dict[str, Any],
    reused_cv_version_id: str | None = None,
) -> CvGenerationResult:
    finalized = deepcopy(result)
    finalized = _apply_final_artifact_contract(
        finalized,
        analysis_record=analysis_record,
        profile=profile,
        config=config,
    )
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
    finalized["trace_id"] = str(trace_id)
    if isinstance(finalized.get("cv_generation_trace"), dict):
        finalized["cv_generation_trace"] = {
            **dict(finalized["cv_generation_trace"]),
            "trace_id": str(trace_id),
        }
    status = str(finalized.get("status") or "")
    if status == ACCEPTED_STATUS:
        review_reason = _review_required_reason(analysis_record, finalized, config)
        if review_reason is not None:
            reason_code, message = review_reason
            finalized["review_required_reason_code"] = reason_code
            warnings = list(finalized.get("quality_warnings") or [])
            warnings.append(message)
            finalized["quality_warnings"] = sorted(set(warnings))
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
    if "quality_warnings" not in finalized:
        validation_warnings = list((validation_snapshot or {}).get("warnings") or [])
        finalized["quality_warnings"] = sorted({str(item).strip() for item in validation_warnings if str(item).strip()})
    error = finalized.get("error")
    if isinstance(error, dict) and not error.get("code"):
        error["code"] = status or str(error.get("stage") or "failure")
    return finalized


def _native_final_artifact_enabled(config: dict[str, Any]) -> bool:
    return bool(
        ((config.get("cv") or {}).get("final_artifact_acceptance") or {}).get("enabled")
    )


def _render_acceptance_matches_final_content(
    structured_cv: dict[str, Any],
    markdown: str,
    config: dict[str, Any],
    render_acceptance: dict[str, Any] | None,
) -> bool:
    return render_proof_matches(
        render_acceptance,
        content_sha256=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
        template_sha256=_template_sha256(config),
        render_config_fingerprint=_render_config_fingerprint(config),
    )


def _apply_final_artifact_contract(
    result: CvGenerationResult,
    *,
    analysis_record: dict[str, Any],
    profile: dict[str, Any],
    config: dict[str, Any],
) -> CvGenerationResult:
    finalized = cast(CvGenerationResult, deepcopy(result))
    structured_cv = finalized.get("structured_cv_final")
    markdown = finalized.get("markdown_final")
    content_valid = bool(finalized.get("validation", {}).get("valid")) if isinstance(finalized.get("validation"), dict) else False
    if not isinstance(structured_cv, dict) or not isinstance(markdown, str) or not markdown:
        finalized["content_acceptance"] = content_valid
        finalized["final_artifact_acceptance"] = {"status": "not_applicable"}
        finalized["trim_attempt_count"] = 0
        return finalized
    evidence_payload = [item for item in list(analysis_record.get("evidence_payload") or []) if isinstance(item, dict)]
    requirement_coverage = [item for item in list(analysis_record.get("requirement_coverage") or []) if isinstance(item, dict)]
    provenance = build_render_item_provenance_v1(
        content_plan=dict(analysis_record.get("content_plan") or finalized.get("content_plan") or {}),
        evidence_payload=evidence_payload,
        requirement_coverage=requirement_coverage,
        structured_cv=structured_cv,
    )
    finalized["render_item_provenance"] = provenance
    finalized["content_acceptance"] = content_valid
    finalized["trim_attempt_count"] = 0
    if not _native_final_artifact_enabled(config):
        finalized["final_artifact_acceptance"] = {"status": "not_required", "content_valid": content_valid}
        return finalized

    render_acceptance = finalized.get("render_acceptance")
    if not isinstance(render_acceptance, dict) or not _render_acceptance_matches_final_content(
        structured_cv,
        markdown,
        config,
        render_acceptance,
    ):
        render_acceptance = render_cv_native_acceptance(markdown, config)
    final_ok = final_artifact_acceptance_passes(content_valid=content_valid, render_acceptance=render_acceptance)
    if not final_ok and content_valid and str(render_acceptance.get("page_fit_status") or "") == "fail":
        before_support = render_item_requirement_support(structured_cv, provenance)
        trimmed = trim_structured_cv_for_page_fit(structured_cv, provenance)
        trimmed_markdown = render_cv_markdown(trimmed, config)
        grounding = _build_validation_grounding_payload(
            analysis_record,
            dict(analysis_record.get("job_snapshot") or {}),
            evidence_payload,
            list(analysis_record.get("evidence_used") or []),
        )
        trimmed_validation = run_all_validations(
            trimmed_markdown,
            profile,
            config,
            structured_cv=trimmed,
            analysis_grounding=grounding,
        )
        after_support = render_item_requirement_support(trimmed, provenance)
        if trimmed_validation.get("valid") and before_support == after_support and trimmed != structured_cv:
            trimmed_render = render_cv_native_acceptance(trimmed_markdown, config)
            finalized["trim_attempt_count"] = 1
            if final_artifact_acceptance_passes(content_valid=True, render_acceptance=trimmed_render):
                structured_cv = trimmed
                markdown = trimmed_markdown
                finalized["structured_cv_final"] = structured_cv
                finalized["markdown_final"] = markdown
                finalized["validation"] = trimmed_validation
                content_valid = True
                render_acceptance = trimmed_render
                final_ok = True
    finalized["render_acceptance"] = render_acceptance
    finalized["page_fit_status"] = render_acceptance.get("page_fit_status") if isinstance(render_acceptance, dict) else None
    finalized["artifact_checksum"] = render_acceptance.get("artifact_checksum") if isinstance(render_acceptance, dict) else None
    finalized["final_artifact_acceptance"] = {
        "status": "accepted" if final_ok else "review_required",
        "content_valid": content_valid,
        "page_fit_status": finalized.get("page_fit_status"),
        "trim_attempt_count": finalized["trim_attempt_count"],
    }
    if not final_ok and str(finalized.get("status") or "") == ACCEPTED_STATUS:
        finalized["status"] = "review_required"
        finalized["error"] = {
            "stage": "render",
            "code": str((render_acceptance or {}).get("render_status") or "render_unverified"),
            "message": "Final CV artifact lacks verified native one-page render proof.",
        }
        finalized["structured_cv_final"] = None
        finalized["markdown_final"] = None
    trace = finalized.get("cv_generation_trace")
    if isinstance(trace, dict):
        trace = dict(trace)
        output_summary = dict(trace.get("output_summary") or {})
        output_summary.update(
            {
                "accepted_output_present": final_ok,
                "final_status": finalized.get("status"),
                "page_fit_status": finalized.get("page_fit_status"),
                "render_acceptance": render_acceptance,
            }
        )
        trace["output_summary"] = output_summary
        trace["render_acceptance"] = render_acceptance
        trace["page_fit_status"] = finalized.get("page_fit_status")
        trace["render_item_provenance"] = provenance
        finalized["cv_generation_trace"] = trace
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
    render_acceptance = reusable_record.get("render_acceptance")
    page_fit_status = reusable_record.get("page_fit_status")
    if not _render_acceptance_matches_final_content(structured_cv, markdown, config, render_acceptance):
        render_acceptance = render_cv_native_acceptance(structured_cv, config)
        page_fit_status = render_acceptance.get("page_fit_status")
    if _native_final_artifact_enabled(config) and not final_artifact_acceptance_passes(
        content_acceptance=bool(validation.get("valid")),
        page_fit_status=str(page_fit_status or "").strip() or None,
        render_acceptance=render_acceptance,
    ):
        return _build_result(
            analysis_record=analysis_record,
            job=job,
            status="review_required",
            fit_classification=_coerce_fit_classification(analysis_record.get("fit_classification")),
            structured_cv_initial=structured_cv,
            validation_initial=_build_validation_snapshot(validation),
            repair_attempt=_empty_repair_attempt(),
            structured_cv_final=structured_cv,
            markdown_final=markdown,
            validation=validation,
            error={
                "stage": "final_artifact_acceptance",
                "code": "reusable_render_proof_failed",
                "message": "Reusable CV artifact lacks native one-page render proof.",
            },
            llm_runtime_evidence=[],
            page_fit_status=str(page_fit_status or "").strip() or None,
            render_acceptance=render_acceptance if isinstance(render_acceptance, dict) else None,
        )
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
        page_fit_status=str(page_fit_status or "").strip() or None,
        render_acceptance=render_acceptance if isinstance(render_acceptance, dict) else None,
    )
    if isinstance(reusable_record.get("render_acceptance"), dict):
        reusable_result["render_acceptance"] = dict(reusable_record["render_acceptance"])
    return reusable_result


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
    page_fit_status: str | None = None,
    render_acceptance: dict[str, Any] | None = None,
    trim_count: int = 0,
    trimmed_claim_ids: list[str] | None = None,
    trim_reason: str | None = None,
    post_trim_validation_status: str = "not_run",
    post_trim_missing_requirements: list[str] | None = None,
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
        "final_artifact_contract_version": FINAL_ARTIFACT_CONTRACT_VERSION,
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
        "content_plan": dict(analysis_record.get("content_plan") or {}),
        "uncertainties": [
            dict(item)
            for item in list(analysis_record.get("uncertainties") or [])
            if isinstance(item, dict)
        ],
        "page_fit_status": page_fit_status,
        "render_acceptance": dict(render_acceptance) if isinstance(render_acceptance, dict) else None,
        "trim_count": int(trim_count),
        "trimmed_claim_ids": list(trimmed_claim_ids or []),
        "trim_reason": trim_reason,
        "post_trim_validation_status": post_trim_validation_status,
        "post_trim_missing_requirements": list(post_trim_missing_requirements or []),
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
    *,
    trace_id: str | None = None,
) -> CvGenerationResult:
    started_at = time.monotonic()
    trace_id = str(trace_id or uuid.uuid4())
    analysis_record = dict(analysis_record)
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
    content_plan = dict(analysis_record.get("content_plan") or build_cv_content_plan(analysis_record, job, config))
    if not isinstance(content_plan.get("generation_preflight"), dict):
        content_plan["generation_preflight"] = build_generation_preflight(analysis_record, content_plan)
    analysis_record["content_plan"] = content_plan
    approved_evidence_ids = {
        str(item).strip()
        for item in list(content_plan.get("approved_evidence_ids") or [])
        if str(item).strip()
    }
    writer_evidence_payload = [
        item
        for item in evidence_payload
        if str(item.get("evidence_id") or item.get("claim_id") or "").strip()
        in approved_evidence_ids
    ]
    full_input_character_count = len(json.dumps(evidence_payload, ensure_ascii=False, sort_keys=True))
    writer_input_character_count = len(json.dumps(writer_evidence_payload, ensure_ascii=False, sort_keys=True))
    input_metrics = {
        "full_input_item_count": len(evidence_payload),
        "approved_input_item_count": len(writer_evidence_payload),
        "omitted_input_item_count": len(evidence_payload) - len(writer_evidence_payload),
        "full_input_character_count": full_input_character_count,
        "approved_input_character_count": writer_input_character_count,
        "full_input_token_estimate": full_input_character_count // 4,
        "approved_input_token_estimate": writer_input_character_count // 4,
    }
    runtime_evidence: list[dict[str, Any]] = []
    trace_payload = _empty_cv_generation_trace(
        template_path=str(_resolve_template_path(config)),
        trace_id=trace_id,
    )
    trace_payload["generation_preflight"] = dict(content_plan.get("generation_preflight") or {})
    provider_generator = _build_fallback_provider_generator(
        job=job,
        evidence_payload=writer_evidence_payload,
        gap_summary=gap_summary,
        profile=profile,
        config=config,
        fit=fit,
        evidence_selection_summary=evidence_selection_summary,
        content_plan=content_plan,
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
            "input_item_count": len(writer_evidence_payload),
            "input_character_count": writer_input_character_count,
            "input_token_estimate": writer_input_character_count // 4,
            "retry_reason": "missing_or_shallow_sections" if repair_targets else None,
            "debug_flags_active": {
                key: bool(str(os.environ.get(key) or "").strip())
                for key in _LIVE_TRACE_DEBUG_ENV_KEYS
            },
            "prompt_contract": _LIVE_TRACE_PROMPT_CONTRACT,
            "template_path": str(_resolve_template_path(config)),
            "response_schema_name": _LIVE_TRACE_SCHEMA_NAME,
            "generation_preflight": dict(content_plan.get("generation_preflight") or {}),
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
        defect_category = _generation_format_defect_category(result[2])
        if defect_category:
            attempt_trace["failure_category"] = "generation_format_defect"
            attempt_trace["generation_format_defect_category"] = defect_category
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
            repair_arm=_coerce_repair_arm(config.get("cv_generation_repair_arm")),
        )
        result_status: GenerationStatus = (
            ACCEPTED_STATUS
            if validation.get("valid")
            else REVIEW_REQUIRED_STATUS
            if repair_attempt.get("review_required")
            else VALIDATION_FAILED_STATUS
        )
        error: ErrorPayload | None = None
        structured_cv_final = structured_cv if result_status == ACCEPTED_STATUS else None
        markdown_final = markdown if result_status == ACCEPTED_STATUS else None
        page_fit_status: str | None = None
        render_acceptance: dict[str, Any] | None = None
        trim_count = 0
        trimmed_claim_ids: list[str] = []
        trim_reason: str | None = None
        post_trim_validation_status = "not_run"
        post_trim_missing_requirements: list[str] = []
        if result_status == VALIDATION_FAILED_STATUS:
            error = {
                "stage": "validation",
                "message": f"CV validation failed for {extract_job_url(job)}",
            }
        if trace_payload is not None:
            trace_payload["input_summary"] = {
                "attempt_count": len(trace_payload["attempts"]),
                "input_item_count": len(writer_evidence_payload),
                **input_metrics,
            }
            trace_payload["repair_summary"] = {
                "repair_attempted": bool(repair_attempt.get("performed")),
                "repair_attempt_count": max(len(trace_payload["attempts"]) - 1, 0),
                "repair_targets": list(repair_attempt.get("missing_sections") or []),
                "repair_reason": str(repair_attempt.get("reason") or ""),
                "repair_kind": str(repair_attempt.get("reason") or ""),
                "local_repair_attempted": bool(repair_attempt.get("local_repair_attempted")),
                "local_repair_succeeded": bool(repair_attempt.get("local_repair_succeeded")),
                "local_repair_failed": bool(repair_attempt.get("local_repair_failed")),
                "provider_retry_attempted": bool(repair_attempt.get("provider_retry_attempted")),
                "provider_retry_succeeded": bool(repair_attempt.get("provider_retry_succeeded")),
                "failure_category": str(repair_attempt.get("failure_category") or "none"),
                "targeted_generation_attempted": bool(repair_attempt.get("targeted_generation_attempted")),
                "targeted_generation_succeeded": bool(repair_attempt.get("targeted_generation_succeeded")),
                "full_regeneration_attempted": bool(repair_attempt.get("full_regeneration_attempted")),
                "full_regeneration_succeeded": bool(repair_attempt.get("full_regeneration_succeeded")),
                "review_required": bool(repair_attempt.get("review_required")),
            }
            _update_live_trace_validation_cycle(
                trace_payload,
                validation_initial=validation_initial,
                validation_final=validation,
            )
            trace_payload["output_summary"] = {
                "accepted_output_present": result_status == ACCEPTED_STATUS,
                "final_status": result_status,
                "page_fit_status": page_fit_status,
                "render_acceptance": dict(render_acceptance or {}),
                "trim_count": trim_count,
                "trimmed_claim_ids": list(trimmed_claim_ids),
                "trim_reason": trim_reason,
                "post_trim_validation_status": post_trim_validation_status,
                "post_trim_missing_requirements": list(post_trim_missing_requirements),
            }
            _update_efficiency_summary(
                trace_payload,
                input_metrics=input_metrics,
                started_at=started_at,
                status=result_status,
                review_question_count=len(list(analysis_record.get("uncertainties") or [])),
            )
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
        failed_repair_attempt = getattr(exc, "repair_attempt", None)
        if isinstance(failed_repair_attempt, dict):
            repair_attempt = dict(failed_repair_attempt)
        runtime_failure_evidence = getattr(exc, "llm_runtime_evidence", None)
        if isinstance(runtime_failure_evidence, dict):
            runtime_evidence.append(dict(runtime_failure_evidence))
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
                "input_item_count": len(writer_evidence_payload),
                **input_metrics,
            }
            trace_payload["repair_summary"] = {
                "repair_attempted": bool(repair_attempt.get("performed")),
                "repair_attempt_count": max(len(trace_payload["attempts"]) - 1, 0),
                "repair_targets": list(repair_attempt.get("missing_sections") or []),
                "repair_reason": str(repair_attempt.get("reason") or ""),
                "repair_kind": str(repair_attempt.get("reason") or ""),
                "local_repair_attempted": bool(repair_attempt.get("local_repair_attempted")),
                "local_repair_succeeded": bool(repair_attempt.get("local_repair_succeeded")),
                "local_repair_failed": bool(repair_attempt.get("local_repair_failed")),
                "provider_retry_attempted": bool(repair_attempt.get("provider_retry_attempted")),
                "provider_retry_succeeded": bool(repair_attempt.get("provider_retry_succeeded")),
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
            _update_efficiency_summary(
                trace_payload,
                input_metrics=input_metrics,
                started_at=started_at,
                status=GENERATION_FAILED_STATUS,
                review_question_count=len(list(analysis_record.get("uncertainties") or [])),
            )
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
    analysis_record = dict(analysis_record)
    trace_id = str(uuid.uuid4())
    job = dict(analysis_record.get("job_snapshot") or {})
    analysis_record.setdefault(
        "content_plan",
        build_cv_content_plan(analysis_record, job, config),
    )
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
                trace_id=trace_id,
                profile=profile,
                reused_cv_version_id=str((reusable_record or {}).get("version_id") or "") or None,
            )
    fresh = _generate_fresh_from_analysis(analysis_record, profile, config, trace_id=trace_id)
    reuse_reason = "candidate_rejected" if reusable_record is not None else "fresh_compute_required"
    return _finalize_generation_result(
        fresh,
        analysis_record=analysis_record,
        config=config,
        fingerprint_result=fingerprint_result,
        reuse_status="fresh_compute",
        reuse_reason_code=reuse_reason,
        trace_id=trace_id,
        profile=profile,
    )
