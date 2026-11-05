"""@meta
name: ai_score
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.stage-artifact-diagnostics
responsibility:
  - Module metadata placeholder for src.fitcv.ai_score.
inputs:
  - Internal runtime calls and module imports
outputs:
  - Module-level symbols and runtime behavior
lifecycle:
  - status: active
"""

import json
import hashlib
import logging
import math
import os
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from fitcv.config import (
    get_prompt_replacement,
    get_prompt_replacement_metadata,
    get_ranking_ai_score_model,
    get_ranking_prompt_id,
    get_stage_runtime_concurrency,
    resolve_model_routing_part,
)
from fitcv.contracts import RANKING_AI_SCORE_PROMPT_SCHEMA_VERSION
from fitcv.llm_runtime import (
    LlmAdapter,
    LlmAdapterResponse,
    LlmRuntimeFailure,
    LlmRuntimeResult,
    LlmTaskRequest,
    LlmTransportPool,
    get_ranking_transport_pool,
    LlmValidationResult,
    execute_llm_task,
    project_llm_runtime_evidence,
)
from fitcv.runtime_routing import LlmRouting, resolve_llm_routing
from fitcv.persistence import get_local_sqlite_path, sqlite_connection
from fitcv.pipeline_stages.common import job_identity_index_keys, job_identity_keys
from fitcv.evidence import bounded_term_values, build_evidence_excerpt, project_candidate_evidence
from fitcv.candidate import flatten_rankable_skills
from fitcv.semantic_snapshot import compile_semantic_policy, resolve_semantic_value
from fitcv.prompts import render_prompt
from fitcv.ranking_contract import (
    SCORE_STATUS_INVALID,
    SCORE_STATUS_UNSCORED,
    SCORE_STATUS_VALID,
    VALID_FIT_LABELS,
)

logger = logging.getLogger(__name__)

RANKING_INPUT_CONTRACT_VERSION = "ranking_input_v3"
RANKING_REQUEST_MAX_CHARS = 12_000
RANKING_TERM_MAX_CHARS = 160
RANKING_EVIDENCE_TEXT_MAX_CHARS = 400
RANKING_MAX_SKILLS = 8
RANKING_MAX_EVIDENCE = 2


def _semantic_policy(config: dict[str, Any] | None) -> dict[str, Any]:
    candidate = (config or {}).get("semantic_policy")
    return candidate if isinstance(candidate, dict) else compile_semantic_policy(config or {})


def _canonical_skill(value: Any, policy: dict[str, Any]) -> str:
    return resolve_semantic_value(str(value or "").strip(), "skill", policy)


def _bounded_text(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _bounded_values(values: Any, *, limit: int, item_chars: int = RANKING_TERM_MAX_CHARS) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in list(values or []):
        text = _bounded_text(value, item_chars)
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
        if len(result) >= limit:
            break
    return result

# ── constants ─────────────────────────────────────────────────────────────────
def _stable_json_fingerprint(payload: dict[str, Any]) -> str:
    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def build_ai_score_contract_fingerprint(
    config: dict[str, Any], *, resolved_route: LlmRouting | None = None
) -> dict[str, Any]:
    customization = get_prompt_replacement_metadata("ranking_ai_score", config)
    model = get_ranking_ai_score_model(config)
    route = resolved_route
    if route is None:
        try:
            route = resolve_llm_routing("ranking_ai_score", model_fallback=model, runtime_config=config)
        except Exception:
            route = None
    payload = {
        "ai_score_model": get_ranking_ai_score_model(config),
        "route": {
            key: getattr(route, key, None)
            for key in ("provider", "base_url", "wire_api", "model", "timeout_seconds", "temperature", "configuration_revision", "model_record_id")
        },
        "prompt_schema_version": RANKING_AI_SCORE_PROMPT_SCHEMA_VERSION,
        "prompt_id": get_ranking_prompt_id(config),
        "prompt_customized": customization["customized"],
        "prompt_replacement_sha256": customization["replacement_sha256"],
        "prompt_replacement_char_count": customization["replacement_char_count"],
    }
    return {
        "payload": payload,
        "fingerprint": _stable_json_fingerprint(payload),
    }


def build_ai_score_input_fingerprint(
    job: dict[str, Any],
    candidate_summary: str,
    top_evidence: list[str],
    config: dict[str, Any],
    *,
    ranking_input: dict[str, Any] | None = None,
    resolved_route: LlmRouting | None = None,
) -> dict[str, Any]:
    request_record = build_ranking_request(
        job, candidate_summary, top_evidence, config,
        ranking_input=ranking_input, resolved_route=resolved_route,
    )
    payload = {
        "request": request_record["request_payload"],
        "route": request_record["route_payload"],
        "prompt": request_record["request"].prompt,
        "ranking_input": request_record.get("bounded_ranking_input") or {},
        "canonical_checksums": request_record.get("canonical_checksums") or {},
        "contract_fingerprint": build_ai_score_contract_fingerprint(config, resolved_route=resolved_route)["fingerprint"],
        "input_contract_version": RANKING_INPUT_CONTRACT_VERSION,
    }
    return {
        "payload": payload,
        "fingerprint": _stable_json_fingerprint(payload),
    }


def build_ranking_request(
    job: dict[str, Any],
    candidate_summary: str,
    top_evidence: list[Any],
    config: dict[str, Any],
    *,
    ranking_input: dict[str, Any] | None = None,
    resolved_route: LlmRouting | None = None,
) -> dict[str, Any]:
    from fitcv.embeddings import build_job_summary_text

    source = ranking_input or {}
    jd_summary = _bounded_text(source.get("job_requirements") or build_job_summary_text(job), 4_000)
    candidate_text = _bounded_text(source.get("candidate_summary") or candidate_summary, 2_500)
    evidence = (
        list(source.get("candidate_evidence") or [])[:RANKING_MAX_EVIDENCE]
        if "candidate_evidence" in source
        else list(top_evidence or [])[:RANKING_MAX_EVIDENCE]
    )

    def evidence_text(item: Any) -> str:
        if not isinstance(item, dict):
            return str(item)
        fields = [
            _bounded_text(item.get("title"), RANKING_TERM_MAX_CHARS),
            _bounded_text(item.get("parent_title"), RANKING_TERM_MAX_CHARS),
            _bounded_text(item.get("organization"), RANKING_TERM_MAX_CHARS),
            _bounded_text(item.get("scoring_context"), RANKING_EVIDENCE_TEXT_MAX_CHARS),
            ", ".join(_bounded_values(item.get("skills"), limit=RANKING_MAX_SKILLS)),
            _bounded_text(item.get("text"), RANKING_EVIDENCE_TEXT_MAX_CHARS),
        ]
        return " | ".join(value for value in fields if value)

    route = resolved_route or resolve_llm_routing("ranking_ai_score", runtime_config=config)
    base_request_payload = {
        "routing_part": "ranking_ai_score",
        "prompt": "",
        "response_mode": "json_object",
        "input_contract_version": RANKING_INPUT_CONTRACT_VERSION,
    }
    serialized_without_prompt = len(json.dumps(base_request_payload, ensure_ascii=False))
    prompt_budget = RANKING_REQUEST_MAX_CHARS - serialized_without_prompt - 2
    if prompt_budget < 1:
        raise ValueError("ranking request mandatory contract exceeds 12000 characters")
    truncation_steps: list[str] = []

    def render_prompt(current_jd: str, current_candidate: str, current_evidence: list[str]) -> str:
        return build_scoring_prompt(current_jd, current_candidate, current_evidence, config=config)

    prompt = render_prompt(jd_summary, candidate_text, [evidence_text(item) for item in evidence])
    if len(prompt) > prompt_budget:
        for evidence_count in range(len(evidence) - 1, -1, -1):
            candidate_prompt = render_prompt(
                jd_summary,
                candidate_text,
                [evidence_text(item) for item in evidence[:evidence_count]],
            )
            if len(candidate_prompt) <= prompt_budget:
                prompt = candidate_prompt
                truncation_steps.append(f"candidate_evidence:{len(evidence)}->{evidence_count}")
                break
        else:
            for candidate_limit in (2_000, 1_000, 500, 0):
                candidate_prompt = render_prompt(
                    jd_summary,
                    candidate_text[:candidate_limit],
                    [],
                )
                if len(candidate_prompt) <= prompt_budget:
                    prompt = candidate_prompt
                    truncation_steps.append(f"candidate_facts:{len(candidate_text)}->{candidate_limit}")
                    break
            else:
                for jd_limit in (3_000, 2_000, 1_000, 500, 0):
                    candidate_prompt = render_prompt(
                        jd_summary[:jd_limit],
                        "",
                        [],
                    )
                    if len(candidate_prompt) <= prompt_budget:
                        prompt = candidate_prompt
                        truncation_steps.append(f"job_requirements:{len(jd_summary)}->{jd_limit}")
                        break
                else:
                    prompt = prompt[:prompt_budget]
                    truncation_steps.append("mandatory_prompt_tail")
    request = LlmTaskRequest(routing_part="ranking_ai_score", prompt=prompt, response_mode="json_object")
    request_payload = {
        **base_request_payload,
        "prompt": prompt,
    }
    route_payload = {key: getattr(route, key) for key in ("provider", "base_url", "wire_api", "model", "timeout_seconds", "request_start_interval_secs", "auth_mode", "temperature", "model_record_id", "configuration_revision")}
    bounded_ranking_input = {
        key: value
        for key, value in source.items()
        if key in {"job_requirements", "candidate_summary", "candidate_evidence", "contract_metadata"}
    }
    return {
        "request": request,
        "route": route,
        "request_payload": request_payload,
        "route_payload": route_payload,
        "bounded_ranking_input": bounded_ranking_input,
        "canonical_checksums": dict((source.get("contract_metadata") or {}).get("canonical_checksums") or {}),
        "prompt_truncated": bool(truncation_steps),
        "prompt_truncation_steps": truncation_steps,
        "fingerprint": _stable_json_fingerprint({"request": request_payload, "route": route_payload}),
    }


def build_ranking_input_diagnostics(
    ranking_input: dict[str, Any] | None,
    request_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return bounded, persisted diagnostics for the exact scorer handoff."""
    source = ranking_input or {}
    metadata = dict(source.get("contract_metadata") or {})
    evidence = [item for item in list(source.get("candidate_evidence") or []) if isinstance(item, dict)]
    request_payload = dict((request_record or {}).get("request_payload") or {})
    candidate_skill_count = 0
    candidate_summary_value = source.get("candidate_summary")
    if isinstance(candidate_summary_value, str):
        try:
            candidate_skill_count = len(list((json.loads(candidate_summary_value) or {}).get("skills") or []))
        except (TypeError, ValueError, json.JSONDecodeError):
            candidate_skill_count = 0
    serialized_request = (
        len(json.dumps(request_payload, ensure_ascii=False, sort_keys=True))
        if request_payload
        else None
    )
    return {
        "contract_version": str(metadata.get("version") or RANKING_INPUT_CONTRACT_VERSION),
        "semantic_policy_fingerprint": str(metadata.get("semantic_policy_fingerprint") or ""),
        "canonical_checksums": dict(metadata.get("canonical_checksums") or {}),
        "selected_evidence_ids": [str(item.get("evidence_id") or "") for item in evidence[:RANKING_MAX_EVIDENCE]],
        "selected_evidence_titles": [
            _bounded_text(item.get("parent_title") or item.get("title"), RANKING_TERM_MAX_CHARS)
            for item in evidence[:RANKING_MAX_EVIDENCE]
            if _bounded_text(item.get("parent_title") or item.get("title"), RANKING_TERM_MAX_CHARS)
        ],
        "selected_evidence_count": len(evidence[:RANKING_MAX_EVIDENCE]),
        "candidate_skill_count": candidate_skill_count,
        "omitted_counts": dict(metadata.get("omitted_counts") or {}),
        "request_char_count": serialized_request,
        "request_max_chars": RANKING_REQUEST_MAX_CHARS,
        "request_within_budget": serialized_request is None or serialized_request <= RANKING_REQUEST_MAX_CHARS,
        "prompt_truncated": bool((request_record or {}).get("prompt_truncated")),
        "prompt_truncation_steps": list((request_record or {}).get("prompt_truncation_steps") or []),
    }


# ── prompt construction ────────────────────────────────────────────────────────

def build_scoring_prompt(
    jd_summary: str,
    candidate_summary: str,
    top_evidence: list[str],
    *,
    config: dict[str, Any] | None = None,
) -> str:
    """Build the structured reranking prompt for one job.

    Inputs:
        jd_summary        : labelled-section text from build_job_summary_text()
        candidate_summary : brief candidate paragraph (skills, experience level)
        top_evidence      : optional top 0-2 candidate evidence chunk_text strings

    Returns:
        A prompt string with rubric embedded. Model must return JSON only.
    """
    evidence_section = ""
    if top_evidence:
        bullets = "\n".join(f"  - {e}" for e in top_evidence)
        evidence_section = f"\n\nTop matched candidate evidence:\n{bullets}"
    prompt_id = get_ranking_prompt_id(config or {})
    return render_prompt(
        prompt_id,
        {
            "jd_summary": jd_summary,
            "candidate_summary": candidate_summary,
            "evidence_section": evidence_section,
        },
        replacement_text=get_prompt_replacement("ranking_ai_score", config),
    ).text


# ── response parsing ──────────────────────────────────────────────────────────


def build_ranking_job_input(
    job: dict[str, Any],
    profile: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build bounded ranking-only input; retrieval projection stays separate."""
    policy = _semantic_policy(config)

    def bounded(values: Any, limit: int = 8) -> list[str]:
        return _bounded_values(values, limit=limit)

    def canonical_values(values: Any, limit: int = 8) -> tuple[list[str], list[str]]:
        display: list[str] = []
        canonical: list[str] = []
        seen: set[str] = set()
        for value in list(values or []):
            text = _bounded_text(value, RANKING_TERM_MAX_CHARS)
            key = _canonical_skill(text, policy)
            if not text or not key or key in seen:
                continue
            seen.add(key)
            display.append(text)
            canonical.append(key)
            if len(display) >= limit:
                break
        return display, canonical

    projected_evidence = profile.get("_projected_evidence_pool")
    if not isinstance(projected_evidence, list):
        from fitcv.evidence import project_candidate_evidence

        projected_evidence = project_candidate_evidence(profile)
    evidence = [{
        "evidence_id": str(item.get("evidence_id") or ""),
        "kind": str(item.get("kind") or ""),
        "title": _bounded_text(item.get("title"), RANKING_TERM_MAX_CHARS),
        "text": _bounded_text(build_evidence_excerpt(item, job), RANKING_EVIDENCE_TEXT_MAX_CHARS),
        "source_section": _bounded_text(item.get("source_section"), RANKING_TERM_MAX_CHARS),
        "parent_id": _bounded_text(item.get("parent_id"), RANKING_TERM_MAX_CHARS),
        "parent_title": _bounded_text(item.get("parent_title"), RANKING_TERM_MAX_CHARS),
        "organization": _bounded_text(item.get("organization"), RANKING_TERM_MAX_CHARS),
        "scoring_context": _bounded_text(build_evidence_excerpt(item, job), RANKING_EVIDENCE_TEXT_MAX_CHARS),
        "source_refs": _bounded_values(item.get("source_refs"), limit=4),
        "skills": _bounded_values(item.get("skills"), limit=RANKING_MAX_SKILLS),
    } for item in projected_evidence[:RANKING_MAX_EVIDENCE] if isinstance(item, dict)]
    required_values = list(job.get("required_skills_canonical") or job.get("required_skills") or [])
    all_required_skills, required_canonical = canonical_values(
        required_values,
        limit=max(8, len(required_values)),
    )
    all_candidate_skills = [str(value).strip() for value in flatten_rankable_skills(profile) if str(value).strip()]
    technology_requirements, technology_canonical = canonical_values(
        job.get("tech_stack_canonical") or job.get("tech_stack")
    )
    preferred_skills, preferred_canonical = canonical_values(
        job.get("preferred_skills_canonical") or job.get("preferred_skills")
    )
    priority_keys = {
        value: bucket
        for bucket, values in enumerate((required_canonical, technology_canonical, preferred_canonical))
        for value in values
    }
    prioritized_candidate_skills = sorted(
        all_candidate_skills,
        key=lambda skill: (priority_keys.get(_canonical_skill(skill, policy), 3), all_candidate_skills.index(skill)),
    )
    required_skills = all_required_skills[:RANKING_MAX_SKILLS]
    candidate_skills = prioritized_candidate_skills[:RANKING_MAX_SKILLS]
    candidate_skill_keys = {_canonical_skill(skill, policy) for skill in all_candidate_skills}
    matched_skills = [skill for skill, canonical in zip(all_required_skills, required_canonical, strict=False) if canonical in candidate_skill_keys]
    missing_skills = [skill for skill, canonical in zip(all_required_skills, required_canonical, strict=False) if canonical not in candidate_skill_keys]
    languages = [
        {"name": _bounded_text(item.get("name"), RANKING_TERM_MAX_CHARS), "level": _bounded_text(item.get("level"), RANKING_TERM_MAX_CHARS)}
        for item in list(profile.get("languages") or [])[:8]
        if isinstance(item, dict) and _bounded_text(item.get("name"), RANKING_TERM_MAX_CHARS)
    ]
    employment = [
        {
            "role": _bounded_text(item.get("role"), RANKING_TERM_MAX_CHARS),
            "company": _bounded_text(item.get("company") or item.get("organization"), RANKING_TERM_MAX_CHARS),
            "start": _bounded_text(item.get("start"), 32),
            "end": _bounded_text(item.get("end"), 32),
        }
        for item in list(profile.get("experiences") or [])[:8]
        if isinstance(item, dict)
    ]
    education = [
        {key: _bounded_text(item.get(key), RANKING_TERM_MAX_CHARS) for key in ("degree", "field", "institution", "start", "end") if _bounded_text(item.get(key), RANKING_TERM_MAX_CHARS)}
        for item in list(profile.get("education") or [])[:4]
        if isinstance(item, dict)
    ]
    certifications = [
        {key: _bounded_text(item.get(key), RANKING_TERM_MAX_CHARS) for key in ("name", "issuer", "date", "expires") if _bounded_text(item.get(key), RANKING_TERM_MAX_CHARS)}
        for item in list(profile.get("certifications") or [])[:4]
        if isinstance(item, dict)
    ]
    requirements = {
        "title": str(job.get("title") or "")[:160],
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "seniority": str(job.get("seniority") or ""),
        "job_family": str(job.get("job_family") or ""),
        "domain": str(job.get("domain") or ""),
        "responsibilities": bounded(job.get("responsibilities")),
        "technology_requirements": technology_requirements,
        "language_requirements": bounded(job.get("language_requirements") or job.get("languages")),
        "location": {"location_type": str(job.get("location_type") or ""), "actual_location": job.get("actual_location") or job.get("location") or None},
        "years_experience_min": job.get("years_experience_min"),
        "years_experience_max": job.get("years_experience_max"),
        "skill_coverage": {
            "matched": matched_skills[:8],
            "missing": missing_skills[:8],
            "matched_count": len(matched_skills),
            "required_count": len(all_required_skills),
        },
    }
    candidate = {
        "skills": candidate_skills,
        "years_experience": profile.get("years_experience"),
        "target_role": str((profile.get("preferences") or {}).get("target_role") or ""),
        "languages": languages,
        "employment": employment,
        "education": education,
        "certifications": certifications,
    }
    contract_metadata = {
        "version": RANKING_INPUT_CONTRACT_VERSION,
        "semantic_policy_fingerprint": str(policy.get("policy_fingerprint") or ""),
        "canonical_checksums": {
            "job_requirements": _stable_json_fingerprint(requirements),
            "candidate_facts": _stable_json_fingerprint(candidate),
        },
        "omitted_counts": {
            "candidate_skills": max(0, len(all_candidate_skills) - len(candidate_skills)),
            "evidence": max(0, len(projected_evidence) - len(evidence)),
        },
    }
    return {
        "job_requirements": json.dumps(requirements, ensure_ascii=False, sort_keys=True),
        "candidate_summary": json.dumps(candidate, ensure_ascii=False, sort_keys=True),
        "candidate_evidence": evidence,
        "contract_metadata": contract_metadata,
    }


def parse_score_response(response_text: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Parse and validate the model's JSON scoring response.

    Handles:
    - Valid JSON
    - Markdown-fenced JSON (```json ... ```)
    - Legacy fit_label → retained only as migration diagnostics
    - Score must be finite and within [0, 1]
    - Malformed JSON → explicit invalid score state

    Returns:
        Dict with score fields plus optional legacy label diagnostics.
    """
    _defaults: dict[str, Any] = {
        "ai_score": None,
        "legacy_model_fit_label": None,
        "score_reasoning": "",
        "matched_strengths": [],
        "key_risks": [],
        "score_status": SCORE_STATUS_INVALID,
        "failure_code": None,
    }

    def _failure(code: str, reasoning: str) -> dict[str, Any]:
        failed = _defaults.copy()
        failed["score_reasoning"] = reasoning
        failed["parser_status"] = code
        failed["failure_code"] = code
        return failed

    # Strip markdown fences if present
    text = response_text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if fence_match:
        text = fence_match.group(1).strip()

    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        logger.warning("parse_score_response: malformed JSON — returning defaults")
        return _failure("malformed_json", "Scoring response parse failure: malformed_json")

    if not isinstance(data, dict):
        return _failure("non_object_payload", "Scoring response parse failure: non_object_payload")

    if "ai_score" not in data or data.get("ai_score") is None:
        return _failure("missing_ai_score", "Scoring response parse failure: missing_ai_score")
    if isinstance(data.get("ai_score"), bool):
        return _failure("invalid_ai_score", "Scoring response parse failure: invalid_ai_score")
    try:
        raw_score = float(data["ai_score"])
    except (TypeError, ValueError):
        return _failure("invalid_ai_score", "Scoring response parse failure: invalid_ai_score")
    if not math.isfinite(raw_score) or not 0.0 <= raw_score <= 1.0:
        return _failure("invalid_ai_score", "Scoring response parse failure: invalid_ai_score")
    legacy_label = str(data.get("fit_label") or "").lower().strip()
    missing_fields = [
        field for field in ("score_reasoning", "matched_strengths", "key_risks")
        if field not in data
    ]

    return {
        "ai_score":          raw_score,
        "legacy_model_fit_label": legacy_label if legacy_label in VALID_FIT_LABELS else None,
        "score_reasoning":   str(data.get("score_reasoning", "")),
        "matched_strengths": list(data.get("matched_strengths", []) or []),
        "key_risks":         list(data.get("key_risks", []) or []),
        "score_status":      SCORE_STATUS_VALID,
        "failure_code":      None,
        "missing_fields":    missing_fields,
        "parser_status":     "ok",
    }


# ── integration: score one job ────────────────────────────────────────────────

def _execute_ranking_runtime(
    job: dict[str, Any],
    candidate_summary: str,
    top_evidence: list[str],
    config: dict[str, Any],
    *,
    adapter: LlmAdapter | None = None,
    ranking_request: dict[str, Any] | None = None,
    resolved_route: LlmRouting | None = None,
    transport_pool: LlmTransportPool | None = None,
) -> LlmRuntimeResult:
    record = ranking_request or build_ranking_request(job, candidate_summary, top_evidence, config, resolved_route=resolved_route)
    request = record["request"]

    def _parser(response: LlmAdapterResponse) -> dict[str, Any]:
        return parse_score_response(response.raw_text, config=config)

    def _validator(value: Any) -> LlmValidationResult:
        required_fields = {
            "ai_score",
            "legacy_model_fit_label",
            "score_reasoning",
            "matched_strengths",
            "key_risks",
            "parser_status",
            "score_status",
            "failure_code",
        }
        errors: list[str] = []
        if not isinstance(value, dict) or not required_fields.issubset(value):
            errors.append("Ranking parser returned invalid contract.")
        elif value.get("score_status") != SCORE_STATUS_VALID:
            errors.append(f"Ranking score is {value.get('score_status')!r}.")
        elif not isinstance(value.get("ai_score"), (int, float)) or isinstance(value.get("ai_score"), bool):
            errors.append("Ranking parser returned no finite numeric ai_score.")
        elif not math.isfinite(float(value["ai_score"])) or not 0.0 <= float(value["ai_score"]) <= 1.0:
            errors.append("Ranking parser returned ai_score outside [0.0, 1.0].")
        missing_fields = list(value.get("missing_fields") or []) if isinstance(value, dict) else []
        if missing_fields:
            errors.append(f"Ranking response missing required fields: {missing_fields}.")
        is_valid = not errors
        return LlmValidationResult(
            valid=is_valid,
            errors=errors,
            details={},
        )

    return execute_llm_task(
        request,
        parser=_parser,
        validator=_validator,
        adapter=adapter,
        resolved_route=record["route"],
        transport_pool=transport_pool,
    )


def _ranking_result_to_row(job: dict[str, Any], result: LlmRuntimeResult) -> dict[str, Any]:
    value = dict(result.parsed_value) if isinstance(result.parsed_value, dict) else {}
    failure = result.failure
    if result.status != "succeeded" or failure is not None:
        if failure is None:
            failure = LlmRuntimeFailure(
                stage="validate",
                code="validation_error",
                message="Ranking runtime returned no parsed value.",
            )
        if failure.stage in {"adapter", "routing"}:
            score_status = SCORE_STATUS_UNSCORED
            failure_code = "timeout" if failure.code == "adapter_timeout" else "provider_failure"
        elif failure.stage == "parse":
            score_status = SCORE_STATUS_INVALID
            failure_code = str(value.get("failure_code") or "parser_failure")
        else:
            score_status = SCORE_STATUS_INVALID
            failure_code = str(value.get("failure_code") or "validation_failure")
        value.update(
            {
                "ai_score": None,
                "score_status": score_status,
                "failure_code": failure_code,
                "score_reasoning": str(value.get("score_reasoning") or failure.message),
                "matched_strengths": list(value.get("matched_strengths") or []),
                "key_risks": list(value.get("key_risks") or []),
                "legacy_model_fit_label": None,
                "parser_status": str(value.get("parser_status") or failure.code),
                "retry_eligible": score_status == SCORE_STATUS_UNSCORED,
            }
        )
    else:
        value["retry_eligible"] = False
    value["job_url"] = str(job.get("job_url", ""))
    for identity_field in ("run_job_id", "raw_job_fingerprint", "source_job_url"):
        if job.get(identity_field) not in (None, ""):
            value[identity_field] = job[identity_field]
    return value


def score_job(
    job: dict[str, Any],
    candidate_summary: str,
    top_evidence: list[str],
    config: dict[str, Any],
    *,
    ranking_request: dict[str, Any] | None = None,
    resolved_route: LlmRouting | None = None,
    transport_pool: LlmTransportPool | None = None,
) -> dict[str, Any]:
    """Score one job through shared LLM runtime."""
    return _ranking_result_to_row(
        job,
        _execute_ranking_runtime(
            job,
            candidate_summary,
            top_evidence,
            config,
            ranking_request=ranking_request,
            resolved_route=resolved_route,
            transport_pool=transport_pool,
        ),
    )


# ── integration: score shortlist ─────────────────────────────────────────────

def run_ai_scoring(
    shortlist: list[dict[str, Any]],
    candidate_summary: str,
    config: dict[str, Any],
    top_n: int | None = None,
    *,
    runtime_observation_callback: Callable[[dict[str, Any]], None] | None = None,
    ranking_inputs: dict[str, dict[str, Any]] | None = None,
    resolved_route: LlmRouting | None = None,
    transport_pool: LlmTransportPool | None = None,
) -> list[dict[str, Any]]:
    """Score at most top_n shortlisted jobs.

    top_n defaults to config["pipeline"]["ai_score_top_n"] (50 if missing).
    shortlist: list of job dicts from VECTOR_SEARCH (must include job_url and
               structured JD fields). Each item may optionally include
               "top_evidence" (list[str]).

    Requires routed OpenAI-compatible provider config and API key.
    """
    effective_top_n = (
        top_n
        if top_n is not None
        else int((config.get("pipeline") or {}).get("ai_score_top_n") or config.get("rerank_top_n", 50))
    )
    ranking_concurrency = get_stage_runtime_concurrency(
        config,
        stage="ranking",
        default=1,
    )
    selected_jobs = shortlist[:effective_top_n]
    transport_pool = transport_pool or get_ranking_transport_pool()

    def _score_single(input_index: int, job: dict[str, Any]) -> dict[str, Any]:
        ranking_input = dict(job.get("ranking_input") or {})
        if not ranking_input and ranking_inputs:
            identity_keys = job_identity_index_keys(job)
            ranking_input = dict(
                next(
                    (
                        ranking_inputs[key]
                        for key in identity_keys
                        if key in ranking_inputs
                    ),
                    {},
                )
            )
        if "candidate_evidence" in ranking_input:
            top_evidence = list(ranking_input.get("candidate_evidence") or [])[:2]
        else:
            top_evidence = list(job.get("top_evidence", []) or [])[:2]
        scoring_candidate_summary = str(ranking_input.get("candidate_summary") or candidate_summary)
        try:
            request_record = build_ranking_request(job, scoring_candidate_summary, top_evidence, config, ranking_input=ranking_input, resolved_route=resolved_route)
            if runtime_observation_callback is None:
                score_row = score_job(
                    job=job,
                    candidate_summary=scoring_candidate_summary,
                    top_evidence=top_evidence,
                    config=config,
                    ranking_request=request_record,
                    resolved_route=resolved_route,
                    transport_pool=transport_pool,
                )
                score_row["ranking_input_diagnostics"] = build_ranking_input_diagnostics(
                    ranking_input,
                    request_record,
                )
                return score_row
            result = _execute_ranking_runtime(job, scoring_candidate_summary, top_evidence, config, ranking_request=request_record, transport_pool=transport_pool)
            identity_keys = job_identity_keys(job)
            runtime_observation_callback(
                {
                    "contract_version": "llm_runtime_observation_v1",
                    "scope_key": str(
                        job.get("raw_job_fingerprint")
                        or (identity_keys[0] if identity_keys else "")
                    ),
                    "input_index": input_index,
                    "invocation_index": 1,
                    "evidence": project_llm_runtime_evidence(result),
                }
            )
            score_row = _ranking_result_to_row(job, result)
            score_row["ranking_input_diagnostics"] = build_ranking_input_diagnostics(
                ranking_input,
                request_record,
            )
            return score_row
        except Exception as exc:  # noqa: BLE001
            return {
                "job_url": str(job.get("job_url", "")),
                **{
                    field_name: job[field_name]
                    for field_name in ("run_job_id", "raw_job_fingerprint", "source_job_url")
                    if job.get(field_name) not in (None, "")
                },
                "ai_score": None, "legacy_model_fit_label": None,
                "score_status": SCORE_STATUS_UNSCORED,
                "failure_code": "provider_failure",
                "retry_eligible": True,
                "score_reasoning": f"Scoring error: {exc}",
                "matched_strengths": [], "key_risks": [],
                "parser_status": "runtime_exception",
            }

    scored_by_index: dict[int, dict[str, Any]] = {}
    if ranking_concurrency <= 1:
        for index, job in enumerate(selected_jobs):
            scored_by_index[index] = _score_single(index, job)
    else:
        with ThreadPoolExecutor(max_workers=ranking_concurrency) as executor:
            future_to_index = {
                executor.submit(_score_single, index, job): index
                for index, job in enumerate(selected_jobs)
            }
            for future in as_completed(future_to_index):
                scored_by_index[future_to_index[future]] = future.result()
    return [scored_by_index[i] for i in range(len(selected_jobs))]


# ── integration: persist scores ───────────────────────────────────────────────



def _ensure_local_ai_score_results_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_score_results (
            job_url TEXT PRIMARY KEY,
            ai_score REAL NOT NULL,
            fit_label TEXT NOT NULL,
            score_reasoning TEXT NOT NULL,
            matched_strengths_json TEXT NOT NULL,
            key_risks_json TEXT NOT NULL,
            scored_at TEXT NOT NULL
        )
        """
    )
    conn.commit()



def store_ai_scores(
    scores: list[dict[str, Any]],
    config: dict[str, Any],
) -> None:
    """Insert AI scoring results into local sqlite store."""
    scores = [
        score for score in scores
        if str(score.get("score_status") or SCORE_STATUS_VALID) == SCORE_STATUS_VALID
        and score.get("ai_score") is not None
    ]
    if not scores:
        return

    now = datetime.now(tz=timezone.utc).isoformat()
    db_path = Path(get_local_sqlite_path())
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite_connection(db_path) as conn:
        _ensure_local_ai_score_results_table(conn)
        conn.executemany(
            """
            INSERT INTO ai_score_results(
                job_url,
                ai_score,
                fit_label,
                score_reasoning,
                matched_strengths_json,
                key_risks_json,
                scored_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_url) DO UPDATE SET
                ai_score = excluded.ai_score,
                fit_label = excluded.fit_label,
                score_reasoning = excluded.score_reasoning,
                matched_strengths_json = excluded.matched_strengths_json,
                key_risks_json = excluded.key_risks_json,
                scored_at = excluded.scored_at
            """,
            [
                (
                    str(score["job_url"]),
                    float(score["ai_score"]),
                    str(score.get("legacy_model_fit_label") or ""),
                    str(score.get("score_reasoning") or ""),
                    json.dumps(list(score.get("matched_strengths") or []), ensure_ascii=False),
                    json.dumps(list(score.get("key_risks") or []), ensure_ascii=False),
                    now,
                )
                for score in scores
            ],
        )
        conn.commit()

