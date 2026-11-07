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
RANKING_MAX_REQUIREMENT_IDS = 32


class RankingInputBudgetExceeded(ValueError):
    """Raised when the mandatory ranking input cannot fit the request budget."""

    failure_code = "input_budget_exceeded"

    def __init__(self, message: str, *, visibility_manifest: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.visibility_manifest = dict(visibility_manifest or {})


class RankingInputIncomplete(RankingInputBudgetExceeded):
    """Raised when enrichment did not produce a safe scorer contract."""

    failure_code = "mandatory_input_incomplete"


class RankingInputEvidenceLimited(RankingInputBudgetExceeded):
    """Raised when only a zero-evidence ranking prompt fits the request budget."""

    failure_code = "evidence_limited"


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


def _bounded_source_refs(values: Any, *, limit: int = 4) -> list[dict[str, Any] | str]:
    result: list[dict[str, Any] | str] = []
    seen: set[str] = set()
    for value in list(values or []):
        if isinstance(value, dict):
            reference = {
                str(key): value[key]
                for key in ("document_id", "source_block_id", "locator")
                if key in value and value[key] not in (None, "")
            }
            if isinstance(reference.get("locator"), dict):
                reference["locator"] = dict(reference["locator"])
            normalized = json.dumps(reference, ensure_ascii=False, sort_keys=True)
        else:
            reference = _bounded_text(value, RANKING_TERM_MAX_CHARS)
            normalized = reference.casefold()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(reference)
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
        "request_record": request_record,
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
    mandatory_job_fields = {
        "title",
        "required_skills",
        "technology_requirements",
        "language_requirements",
        "location",
        "years_experience_min",
        "years_experience_max",
    }
    mandatory_candidate_fields = {
        "skills",
        "languages",
        "employment",
        "years_experience",
        "target_role",
    }

    def _structured_payload(value: Any) -> dict[str, Any] | None:
        try:
            parsed = json.loads(str(value or ""))
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        return parsed if isinstance(parsed, dict) else None

    def _serialize_payload(payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def bound_job_summary(value: Any) -> tuple[str, bool, dict[str, Any], list[dict[str, Any]]]:
        raw = str(value or "")
        payload = _structured_payload(raw)
        if payload is None:
            bounded = _bounded_text(raw, 4_000)
            metadata = {
                "raw_fields": ["job_requirements"],
                "selected_fields": ["job_requirements"],
                "rendered_fields": ["job_requirements"],
                "model_visible_fields": ["job_requirements"],
                "omitted_fields": [],
                "truncated_fields": ["job_requirements"] if bounded != raw else [],
            }
            return bounded, bounded != raw, metadata, [{"job_requirements": bounded}]
        bounded_payload = dict(payload)
        for key in ("required_skills", "technology_requirements", "preferred_skills", "language_requirements", "responsibilities"):
            values = bounded_payload.get(key)
            if isinstance(values, list):
                bounded_payload[key] = [
                    str(item).strip()
                    if not isinstance(item, dict)
                    else {
                        field: str(field_value).strip()
                        for field, field_value in item.items()
                        if str(field_value or "").strip()
                    }
                    for item in values
                    if isinstance(item, (dict, str, int, float))
                ]
        for key in ("title", "seniority", "job_family", "domain"):
            if key in bounded_payload:
                bounded_payload[key] = _bounded_text(bounded_payload[key], RANKING_TERM_MAX_CHARS)
        if isinstance(bounded_payload.get("location"), dict):
            bounded_payload["location"] = {
                key: _bounded_text(value, RANKING_TERM_MAX_CHARS)
                for key, value in bounded_payload["location"].items()
                if value not in (None, "")
            }
        selected_fields = [key for key in bounded_payload if key in payload]
        metadata = {
            "raw_fields": sorted(str(key) for key in payload),
            "selected_fields": selected_fields,
            "rendered_fields": selected_fields,
            "model_visible_fields": selected_fields,
            "omitted_fields": [],
            "truncated_fields": [
                key for key in selected_fields if bounded_payload.get(key) != payload.get(key)
            ],
        }
        variants: list[dict[str, Any]] = [dict(bounded_payload)]
        reduced = dict(bounded_payload)
        for key in ("preferred_skills", "responsibilities", "domain", "job_family", "seniority"):
            if key in reduced:
                reduced.pop(key)
                variants.append(dict(reduced))
        return _serialize_payload(bounded_payload), _serialize_payload(bounded_payload) != raw, metadata, variants

    def bound_candidate_summary(
        value: Any,
        *,
        mandatory_job: dict[str, Any] | None = None,
    ) -> tuple[str, bool, dict[str, Any], list[dict[str, Any]]]:
        raw = str(value or "")
        payload = _structured_payload(raw)
        if payload is None:
            bounded = _bounded_text(raw, 2_500)
            metadata = {
                "raw_fields": ["candidate_summary"],
                "selected_fields": ["candidate_summary"],
                "rendered_fields": ["candidate_summary"],
                "model_visible_fields": ["candidate_summary"],
                "omitted_fields": [],
                "truncated_fields": ["candidate_summary"] if bounded != raw else [],
            }
            return bounded, bounded != raw, metadata, [{"candidate_summary": bounded}]
        ordered_keys = (
            "skills",
            "languages",
            "employment",
            "mandatory_facts",
            "mandatory_clauses",
            "education",
            "certifications",
            "years_experience",
            "target_role",
        )
        bounded_payload = {
            key: payload[key]
            for key in ordered_keys
            if key in payload
        }
        for key in ("skills", "languages", "employment", "education", "certifications"):
            values = bounded_payload.get(key)
            if not isinstance(values, list):
                continue
            bounded_payload[key] = [
                {
                    field: _bounded_text(field_value, 96 if key == "employment" else 64)
                    for field, field_value in value.items()
                    if str(field_value or "").strip()
                }
                if isinstance(value, dict)
                else _bounded_text(value, 96 if key == "employment" else 64)
                for value in values
                if isinstance(value, (dict, str, int, float))
            ]

        language_requirements = [
            str(value).strip().casefold()
            for value in list((mandatory_job or {}).get("language_requirements") or [])
            if str(value).strip()
        ]
        if language_requirements and isinstance(bounded_payload.get("languages"), list):
            bounded_payload["languages"] = sorted(
                bounded_payload["languages"],
                key=lambda value: (
                    0
                    if any(
                        requirement in json.dumps(value, ensure_ascii=False).casefold()
                        for requirement in language_requirements
                    )
                    else 1
                ),
            )

        def serialize() -> str:
            return _serialize_payload(bounded_payload)

        changed = serialize() != raw
        omitted_counts: dict[str, int] = {}
        overflow_owner = ""
        while len(serialize()) > 2_500:
            removed = False
            for key in ("certifications", "education", "employment", "languages"):
                values = bounded_payload.get(key)
                if isinstance(values, list) and len(values) > 1:
                    values.pop()
                    omitted_counts[key] = omitted_counts.get(key, 0) + 1
                    overflow_owner = key
                    removed = True
                    break
            if removed:
                changed = True
                continue
            for key in ("certifications", "education", "employment", "languages"):
                values = bounded_payload.get(key)
                if isinstance(values, list):
                    shortened = False
                    for value in values:
                        if not isinstance(value, dict):
                            continue
                        for field, field_value in list(value.items()):
                            text = str(field_value or "")
                            if len(text) > 32:
                                value[field] = text[: max(32, len(text) - 32)]
                                overflow_owner = key
                                shortened = True
                                break
                        if shortened:
                            break
                    if shortened:
                        changed = True
                        break
            else:
                break
        selected_fields = [key for key in bounded_payload if key in payload]
        metadata = {
            "raw_fields": sorted(str(key) for key in payload),
            "selected_fields": selected_fields,
            "rendered_fields": selected_fields,
            "model_visible_fields": selected_fields,
            "omitted_fields": [key for key in payload if key not in bounded_payload],
            "truncated_fields": [
                key for key in selected_fields if bounded_payload.get(key) != payload.get(key)
            ],
            "omitted_counts": omitted_counts,
            "overflow_owner": overflow_owner,
        }
        return serialize(), changed, metadata, [dict(bounded_payload)]

    jd_raw = source.get("job_requirements") or build_job_summary_text(job)
    jd_summary, jd_summary_truncated, job_visibility, job_variants = bound_job_summary(jd_raw)

    candidate_text, candidate_summary_truncated, candidate_visibility, candidate_variants = bound_candidate_summary(
        source.get("candidate_summary") or candidate_summary,
        mandatory_job=_structured_payload(jd_raw),
    )
    mandatory_omissions = {
        str(key): int(value or 0)
        for key, value in dict((source.get("contract_metadata") or {}).get("mandatory_omissions") or {}).items()
    }
    if any(value > 0 for value in mandatory_omissions.values()):
        visibility_manifest = {
            "job": {**job_visibility, "mandatory_omitted_fields": [key for key in mandatory_omissions if key.startswith("job_")]},
            "candidate": {**candidate_visibility, "mandatory_omitted_fields": [key for key in mandatory_omissions if key.startswith("candidate_")]},
            "evidence": {
                "raw_count": len(list(source.get("candidate_evidence") or top_evidence or [])),
                "selected_count": len(list(source.get("candidate_evidence") or top_evidence or [])),
                "rendered_count": 0,
                "model_visible_count": 0,
                "omitted_count": 0,
            },
            "mandatory_omissions": mandatory_omissions,
            "mandatory_core_complete": False,
        }
        exception_type = (
            RankingInputIncomplete
            if int(mandatory_omissions.get("job_enrichment_fallback") or 0) > 0
            else RankingInputBudgetExceeded
        )
        raise exception_type(
            "mandatory ranking facts were omitted before request bounding",
            visibility_manifest=visibility_manifest,
        )
    evidence = (
        list(source.get("candidate_evidence") or [])[:RANKING_MAX_EVIDENCE]
        if "candidate_evidence" in source
        else list(top_evidence or [])[:RANKING_MAX_EVIDENCE]
    )

    def evidence_text(item: Any) -> str:
        if not isinstance(item, dict):
            return str(item)
        source_text = _bounded_text(item.get("text"), RANKING_EVIDENCE_TEXT_MAX_CHARS)
        scoring_context = _bounded_text(item.get("scoring_context"), RANKING_EVIDENCE_TEXT_MAX_CHARS)
        fields = [
            _bounded_text(item.get("evidence_id"), RANKING_TERM_MAX_CHARS),
            _bounded_text(item.get("kind") or item.get("evidence_type"), RANKING_TERM_MAX_CHARS),
            _bounded_text(item.get("source_section"), RANKING_TERM_MAX_CHARS),
            _bounded_text(item.get("title"), RANKING_TERM_MAX_CHARS),
            _bounded_text(item.get("parent_id"), RANKING_TERM_MAX_CHARS),
            _bounded_text(item.get("parent_title"), RANKING_TERM_MAX_CHARS),
            _bounded_text(item.get("organization"), RANKING_TERM_MAX_CHARS),
            ", ".join(_bounded_values(item.get("skills"), limit=RANKING_MAX_SKILLS)),
            f"source_text: {source_text}" if source_text else "",
            f"scoring_context: {scoring_context}"
            if scoring_context and scoring_context != source_text
            else "",
            json.dumps(_bounded_source_refs(item.get("source_refs"), limit=4), ensure_ascii=False, sort_keys=True),
            _bounded_text(item.get("support_state"), RANKING_TERM_MAX_CHARS),
            _bounded_text(item.get("source_ref"), RANKING_TERM_MAX_CHARS),
        ]
        return " | ".join(value for value in fields if value)

    route = resolved_route or resolve_llm_routing("ranking_ai_score", runtime_config=config)
    base_request_payload = {
        "routing_part": "ranking_ai_score",
        "prompt": "",
        "response_mode": "json_object",
        "input_contract_version": RANKING_INPUT_CONTRACT_VERSION,
    }
    def serialized_request_size(prompt_value: str) -> int:
        return len(json.dumps({**base_request_payload, "prompt": prompt_value}, ensure_ascii=False))

    if serialized_request_size("") > RANKING_REQUEST_MAX_CHARS:
        raise RankingInputBudgetExceeded("ranking request mandatory contract exceeds 12000 characters")
    truncation_steps: list[str] = []
    if candidate_summary_truncated:
        truncation_steps.append("candidate_facts:field_aware_bound")

    def render_prompt(current_jd: str, current_candidate: str, current_evidence: list[str]) -> str:
        return build_scoring_prompt(current_jd, current_candidate, current_evidence, config=config)

    selected_job = jd_summary
    selected_candidate = candidate_text
    selected_evidence = [evidence_text(item) for item in evidence]
    attempts: list[tuple[str, str, list[str], str]] = [
        (jd_summary, candidate_text, selected_evidence, "full"),
    ]
    for candidate_variant in candidate_variants[1:]:
        attempts.append((jd_summary, _serialize_payload(candidate_variant), selected_evidence, "candidate_optional"))
    for job_variant in job_variants[1:]:
        attempts.append((_serialize_payload(job_variant), candidate_text, selected_evidence, "job_optional"))
    for job_variant in job_variants[1:]:
        for candidate_variant in candidate_variants[1:]:
            attempts.append((_serialize_payload(job_variant), _serialize_payload(candidate_variant), selected_evidence, "optional"))
    base_attempts = list(attempts)
    evidence_counts = range(len(evidence) - 1, 0, -1) if evidence else (0,)
    for evidence_count in evidence_counts:
        attempts.extend(
            (job_value, candidate_value, selected_evidence[:evidence_count], f"candidate_evidence:{len(evidence)}->{evidence_count}")
            for job_value, candidate_value, _evidence, _reason in base_attempts
        )
    prompt = ""
    for job_value, candidate_value, evidence_value, reason in attempts:
        candidate_prompt = render_prompt(job_value, candidate_value, evidence_value)
        if serialized_request_size(candidate_prompt) <= RANKING_REQUEST_MAX_CHARS:
            prompt = candidate_prompt
            selected_job = job_value
            selected_candidate = candidate_value
            selected_evidence = evidence_value
            if reason != "full":
                truncation_steps.append(reason)
            break
    if not prompt:
        if evidence:
            zero_evidence_attempts = [
                (job_value, candidate_value, [])
                for job_value, candidate_value, _evidence, _reason in base_attempts
            ]
            for job_value, candidate_value, evidence_value in zero_evidence_attempts:
                candidate_prompt = render_prompt(job_value, candidate_value, evidence_value)
                if serialized_request_size(candidate_prompt) <= RANKING_REQUEST_MAX_CHARS:
                    raise RankingInputEvidenceLimited(
                        "ranking request fits only without selected attributable evidence",
                        visibility_manifest={
                            "job": job_visibility,
                            "candidate": candidate_visibility,
                            "evidence": {
                                "raw_count": len(list(source.get("candidate_evidence") or evidence)),
                                "selected_count": len(evidence),
                                "rendered_count": 0,
                                "model_visible_count": 0,
                                "selected_ids": [],
                                "omitted_count": len(evidence),
                            },
                            "mandatory_omissions": mandatory_omissions,
                            "mandatory_core_complete": not any(
                                value > 0 for value in mandatory_omissions.values()
                            ),
                        },
                    )
        visibility_manifest = {
            "job": job_visibility,
            "candidate": candidate_visibility,
            "evidence": {
                "raw_count": len(list(source.get("candidate_evidence") or evidence)),
                "selected_count": len(evidence),
                "rendered_count": 0,
                "model_visible_count": 0,
                "omitted_count": len(evidence),
            },
        }
        raise RankingInputBudgetExceeded(
            "ranking request mandatory contract exceeds 12000 characters",
            visibility_manifest=visibility_manifest,
        )
    request = LlmTaskRequest(routing_part="ranking_ai_score", prompt=prompt, response_mode="json_object")
    request_payload = {
        **base_request_payload,
        "prompt": prompt,
    }
    route_payload = {key: getattr(route, key) for key in ("provider", "base_url", "wire_api", "model", "timeout_seconds", "request_start_interval_secs", "auth_mode", "temperature", "model_record_id", "configuration_revision")}
    rendered_evidence = []
    for item, rendered_text in zip(evidence, selected_evidence, strict=False):
        rendered_item = dict(item) if isinstance(item, dict) else {"text": str(item)}
        rendered_item["rendered_text"] = rendered_text
        rendered_evidence.append(rendered_item)
    bounded_ranking_input = {
        "job_requirements": selected_job,
        "candidate_summary": selected_candidate,
        "candidate_evidence": rendered_evidence,
        "contract_metadata": dict(source.get("contract_metadata") or {}),
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
        "visibility_manifest": {
            "job": {
                **job_visibility,
                "rendered_fields": list(_structured_payload(selected_job) or job_visibility)[0:] if _structured_payload(selected_job) else job_visibility["rendered_fields"],
                "model_visible_fields": list(_structured_payload(selected_job) or job_visibility)[0:] if _structured_payload(selected_job) else job_visibility["model_visible_fields"],
            },
            "candidate": {
                **candidate_visibility,
                "mandatory_omitted_fields": [
                    key for key in mandatory_omissions if key.startswith("candidate_") and mandatory_omissions[key] > 0
                ],
                "rendered_fields": list(_structured_payload(selected_candidate) or candidate_visibility)[0:] if _structured_payload(selected_candidate) else candidate_visibility["rendered_fields"],
                "model_visible_fields": list(_structured_payload(selected_candidate) or candidate_visibility)[0:] if _structured_payload(selected_candidate) else candidate_visibility["model_visible_fields"],
            },
            "evidence": {
                "raw_count": len(list(source.get("candidate_evidence") or evidence)),
                "selected_count": len(evidence),
                "rendered_count": len(selected_evidence),
                "model_visible_count": len(selected_evidence),
                "selected_ids": [
                    str(item.get("evidence_id") or "")
                    for item in evidence[:len(selected_evidence)]
                    if isinstance(item, dict)
                ],
                "omitted_count": max(0, len(evidence) - len(selected_evidence)),
            },
            "mandatory_omissions": mandatory_omissions,
            "mandatory_core_complete": not any(value > 0 for value in mandatory_omissions.values()),
        },
        "fingerprint": _stable_json_fingerprint({"request": request_payload, "route": route_payload}),
    }


def build_ranking_input_diagnostics(
    ranking_input: dict[str, Any] | None,
    request_record: dict[str, Any] | None = None,
    *,
    retrieval_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return bounded, persisted diagnostics for the exact scorer handoff."""
    source = ranking_input or {}
    final_payload = dict((request_record or {}).get("bounded_ranking_input") or {})
    if final_payload:
        source = final_payload
    metadata = dict(source.get("contract_metadata") or {})
    evidence = [item for item in list(source.get("candidate_evidence") or []) if isinstance(item, dict)]
    request_payload = dict((request_record or {}).get("request_payload") or {})
    candidate_skill_count = 0
    visible_candidate_skills: list[str] = []
    candidate_summary_value = source.get("candidate_summary")
    if isinstance(candidate_summary_value, str):
        try:
            candidate_payload = json.loads(candidate_summary_value) or {}
            candidate_skills = list(candidate_payload.get("skills") or [])
            candidate_skill_count = len(candidate_skills)
            visible_candidate_skills = [
                _bounded_text(value, RANKING_TERM_MAX_CHARS)
                for value in candidate_skills[:RANKING_MAX_SKILLS]
                if _bounded_text(value, RANKING_TERM_MAX_CHARS)
            ]
        except (TypeError, ValueError, json.JSONDecodeError):
            candidate_skill_count = 0
    serialized_request = (
        len(json.dumps(request_payload, ensure_ascii=False, sort_keys=True))
        if request_payload
        else None
    )
    retrieval = dict(retrieval_metadata or {})
    backend_metadata = {
        key: retrieval[key]
        for key in (
            "retrieval_strategy",
            "requested_strategy",
            "effective_strategy",
            "backend_id",
            "embedding_backend_id",
            "requested_embedding_backend_id",
            "effective_embedding_backend_metadata",
            "configured_model",
            "dimension",
            "model_revision",
            "preprocessing_version",
            "contract_fingerprint",
        )
        if key in retrieval
    }
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
        "visible_candidate_skills": visible_candidate_skills,
        "bounded_requirement_ids": [
            str(value)
            for value in list(metadata.get("requirement_ids") or [])[:RANKING_MAX_REQUIREMENT_IDS]
            if str(value).strip()
        ],
        "effective_backend_metadata": backend_metadata,
        "effective_retrieval_metadata": {
            key: backend_metadata[key]
            for key in (
                "retrieval_strategy",
                "requested_strategy",
                "effective_strategy",
                "backend_id",
                "embedding_backend_id",
                "requested_embedding_backend_id",
                "effective_embedding_backend_metadata",
            )
            if key in backend_metadata
        },
        "omitted_counts": dict(metadata.get("omitted_counts") or {}),
        "mandatory_omissions": dict(metadata.get("mandatory_omissions") or {}),
        "mandatory_core_complete": not any(
            int(value or 0) > 0
            for value in dict(metadata.get("mandatory_omissions") or {}).values()
        ),
        "request_char_count": serialized_request,
        "request_max_chars": RANKING_REQUEST_MAX_CHARS,
        "request_within_budget": serialized_request is None or serialized_request <= RANKING_REQUEST_MAX_CHARS,
        "prompt_truncated": bool((request_record or {}).get("prompt_truncated")),
        "prompt_truncation_steps": list((request_record or {}).get("prompt_truncation_steps") or []),
        "visibility_manifest": dict((request_record or {}).get("visibility_manifest") or {}),
        "bounded_ranking_input": final_payload,
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

    def canonical_values(
        values: Any,
        limit: int = 8,
        *,
        preserve_full: bool = False,
    ) -> tuple[list[str], list[str]]:
        display: list[str] = []
        canonical: list[str] = []
        seen: set[str] = set()
        for value in list(values or []):
            text = str(value or "").strip() if preserve_full else _bounded_text(value, RANKING_TERM_MAX_CHARS)
            key = _canonical_skill(text, policy)
            if not text or not key or key in seen:
                continue
            seen.add(key)
            display.append(text)
            canonical.append(key)
            if len(display) >= limit:
                break
        return display, canonical

    def mandatory_clause_records(
        values: Any,
        fallback_values: tuple[tuple[str, Any], ...] = (),
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        seen: set[str] = set()

        def add_record(raw: Any, clause_type: str | None = None) -> None:
            if isinstance(raw, dict):
                value = raw.get("value") or raw.get("text") or raw.get("requirement") or raw.get("name")
                current_type = raw.get("clause_type") or raw.get("type") or clause_type or "mandatory"
                normalized = raw.get("normalized_value") or _canonical_skill(value, policy)
                source_span = raw.get("source_span") or raw.get("source_spans")
                required = bool(raw.get("required", True))
            else:
                value = raw
                current_type = clause_type or "mandatory"
                normalized = _canonical_skill(value, policy)
                source_span = None
                required = True
            display = str(value or "").strip()
            normalized_text = str(normalized or "").strip()
            if not display or not normalized_text:
                return
            bounded_span = source_span
            if isinstance(source_span, dict):
                bounded_span = {
                    str(key): item
                    for key, item in source_span.items()
                    if item not in (None, "")
                }
            elif isinstance(source_span, list):
                bounded_span = [
                    dict(item) if isinstance(item, dict) else item
                    for item in source_span
                ]
            clause_id = str(raw.get("clause_id") or "") if isinstance(raw, dict) else ""
            if not clause_id:
                clause_id = f"{str(current_type).strip().lower()}:{_stable_json_fingerprint({'type': current_type, 'value': normalized_text})[:12]}"
            if clause_id in seen:
                return
            seen.add(clause_id)
            record = {
                "clause_id": clause_id,
                "clause_type": str(current_type).strip() or "mandatory",
                "value": display,
                "normalized_value": normalized_text,
                "required": required,
            }
            if bounded_span:
                record["source_span"] = bounded_span
            records.append(record)

        for value in list(values or []):
            add_record(value)
        for clause_type, values_for_type in fallback_values:
            for value in list(values_for_type or []):
                add_record(value, clause_type)
        return records

    projected_evidence = profile.get("_projected_evidence_pool")
    if not isinstance(projected_evidence, list):
        from fitcv.evidence import project_candidate_evidence

        projected_evidence = project_candidate_evidence(profile)
    evidence = [{
        "evidence_id": str(item.get("evidence_id") or ""),
        "kind": str(item.get("kind") or ""),
        "title": _bounded_text(item.get("title"), RANKING_TERM_MAX_CHARS),
        "text": _bounded_text(
            build_evidence_excerpt(item, job, semantic_policy=policy),
            RANKING_EVIDENCE_TEXT_MAX_CHARS,
        ),
        "source_section": _bounded_text(item.get("source_section"), RANKING_TERM_MAX_CHARS),
        "parent_id": _bounded_text(item.get("parent_id"), RANKING_TERM_MAX_CHARS),
        "parent_title": _bounded_text(item.get("parent_title"), RANKING_TERM_MAX_CHARS),
        "organization": _bounded_text(item.get("organization"), RANKING_TERM_MAX_CHARS),
        "scoring_context": _bounded_text(
            item.get("scoring_context") or build_evidence_excerpt(item, job, semantic_policy=policy),
            RANKING_EVIDENCE_TEXT_MAX_CHARS,
        ),
        "support_state": _bounded_text(item.get("support_state"), RANKING_TERM_MAX_CHARS),
        "source_refs": _bounded_source_refs(item.get("source_refs"), limit=4),
        "source_ref": _bounded_text(item.get("source_ref"), RANKING_TERM_MAX_CHARS),
        "skills": _bounded_values(item.get("skills"), limit=RANKING_MAX_SKILLS),
    } for item in projected_evidence[:RANKING_MAX_EVIDENCE] if isinstance(item, dict)]
    required_values = list(job.get("required_skills_canonical") or job.get("required_skills") or [])
    all_required_skills, required_canonical = canonical_values(
        required_values,
        limit=max(8, len(required_values)),
        preserve_full=True,
    )
    all_candidate_skills: list[str] = []
    candidate_skill_keys_seen: set[str] = set()
    for value in flatten_rankable_skills(profile):
        display = str(value).strip()
        canonical = _canonical_skill(display, policy)
        if not display or not canonical or canonical in candidate_skill_keys_seen:
            continue
        candidate_skill_keys_seen.add(canonical)
        all_candidate_skills.append(display)
    technology_values = list(job.get("tech_stack_canonical") or job.get("tech_stack") or [])
    all_technology_requirements, technology_canonical = canonical_values(
        technology_values,
        limit=max(8, len(technology_values)),
        preserve_full=True,
    )
    technology_requirements = all_technology_requirements
    preferred_skills, preferred_canonical = canonical_values(
        job.get("preferred_skills_canonical") or job.get("preferred_skills")
    )
    priority_keys: dict[str, int] = {}
    for bucket, values in enumerate((required_canonical, technology_canonical, preferred_canonical)):
        for value in values:
            priority_keys.setdefault(value, bucket)
    prioritized_candidate_skills = sorted(
        all_candidate_skills,
        key=lambda skill: (priority_keys.get(_canonical_skill(skill, policy), 3), all_candidate_skills.index(skill)),
    )
    required_skills = all_required_skills
    candidate_skills = prioritized_candidate_skills
    candidate_skill_keys = {_canonical_skill(skill, policy) for skill in all_candidate_skills}
    matched_skills = [skill for skill, canonical in zip(all_required_skills, required_canonical, strict=False) if canonical in candidate_skill_keys]
    missing_skills = [skill for skill, canonical in zip(all_required_skills, required_canonical, strict=False) if canonical not in candidate_skill_keys]
    all_candidate_languages = [
        {"name": _bounded_text(item.get("name"), RANKING_TERM_MAX_CHARS), "level": _bounded_text(item.get("level"), RANKING_TERM_MAX_CHARS)}
        for item in list(profile.get("languages") or [])
        if isinstance(item, dict) and _bounded_text(item.get("name"), RANKING_TERM_MAX_CHARS)
    ]
    languages = all_candidate_languages
    all_candidate_employment = [
        {
            "role": _bounded_text(item.get("role"), RANKING_TERM_MAX_CHARS),
            "company": _bounded_text(item.get("company") or item.get("organization"), RANKING_TERM_MAX_CHARS),
            "start": _bounded_text(item.get("start"), 32),
            "end": _bounded_text(item.get("end"), 32),
        }
        for item in list(profile.get("experiences") or [])
        if isinstance(item, dict)
    ]
    employment = all_candidate_employment
    mandatory_skill_keys = set(required_canonical) | set(technology_canonical)
    visible_candidate_skill_keys = {
        _canonical_skill(skill, policy)
        for skill in candidate_skills
    }
    job_language_values = list(job.get("language_requirements") or job.get("languages") or [])
    mandatory_candidate_skill_keys = {
        _canonical_skill(skill, policy)
        for skill in all_candidate_skills
        if _canonical_skill(skill, policy) in mandatory_skill_keys
    }
    job_mandatory_clauses = mandatory_clause_records(
        job.get("mandatory_clauses"),
        (
            ("qualification", job.get("qualifications")),
            ("education", job.get("education_requirements") or job.get("education")),
            ("certification", job.get("certification_requirements") or job.get("certifications")),
            ("language", job_language_values),
            ("employment_constraint", job.get("employment_constraints")),
        ),
    )
    mandatory_omissions = {
        "job_required_skills": 0,
        "job_technology_requirements": 0,
        "job_language_requirements": 0,
        "job_mandatory_clauses": 0,
        "candidate_required_skills": 0,
        "candidate_languages": 0,
        "candidate_employment": 0,
        "candidate_education": 0,
        "candidate_certifications": 0,
        "candidate_mandatory_clauses": 0,
        "job_enrichment_fallback": int(job.get("enrich_reuse_status") == "enrichment_fallback"),
    }
    def requirement_tokens(value: Any) -> set[str]:
        stop_words = {"and", "the", "for", "with", "from", "this", "that", "required", "related"}
        return {
            token
            for token in re.findall(r"[a-z0-9+#]+", str(value or "").casefold())
            if len(token) >= 3 and token not in stop_words
        }

    def record_matches_requirement(
        record: dict[str, str],
        required_values: Any,
        fields: tuple[str, ...],
    ) -> bool:
        record_values = [
            _canonical_skill(record.get(field), policy)
            for field in fields
            if _canonical_skill(record.get(field), policy)
        ]
        record_text = " ".join(record_values)
        record_terms = requirement_tokens(record_text)
        for required_value in list(required_values or []):
            required_key = _canonical_skill(required_value, policy)
            if not required_key:
                continue
            if any(
                candidate == required_key
                or (len(candidate) >= 8 and (candidate in required_key or required_key in candidate))
                for candidate in record_values
            ):
                return True
            required_terms = requirement_tokens(required_value)
            overlap = record_terms & required_terms
            if len(overlap) >= max(2, math.ceil(len(record_terms) * 0.6)):
                return True
        return False

    def prioritize_records(values: Any, required_values: Any, fields: tuple[str, ...]) -> list[dict[str, str]]:
        records: list[dict[str, str]] = []
        for item in list(values or []):
            if not isinstance(item, dict):
                continue
            record = {
                key: _bounded_text(item.get(key), RANKING_TERM_MAX_CHARS)
                for key in fields
                if _bounded_text(item.get(key), RANKING_TERM_MAX_CHARS)
            }
            if record:
                records.append(record)
        return sorted(
            records,
            key=lambda record: (
                0
                if record_matches_requirement(record, required_values, fields)
                else 1
            ),
        )

    education_requirements = list(job.get("education_requirements") or job.get("education") or [])
    certification_requirements = list(job.get("certification_requirements") or job.get("certifications") or [])
    education = prioritize_records(
        profile.get("education"),
        education_requirements,
        ("degree", "field", "institution", "start", "end"),
    )
    certifications = prioritize_records(
        profile.get("certifications"),
        certification_requirements,
        ("name", "issuer", "date", "expires"),
    )
    candidate_mandatory_clauses = mandatory_clause_records(profile.get("mandatory_clauses"))
    mandatory_facts = {
        "education": [
            record for record in education
            if record_matches_requirement(record, education_requirements, ("degree", "field"))
        ],
        "certifications": [
            record for record in certifications
            if record_matches_requirement(record, certification_requirements, ("name", "issuer"))
        ],
        "mandatory_clauses": candidate_mandatory_clauses,
    }
    requirements = {
        "title": str(job.get("title") or "")[:160],
        "required_skills": required_skills,
        "qualifications": bounded(job.get("qualifications"), limit=16),
        "education_requirements": bounded(education_requirements, limit=16),
        "certification_requirements": bounded(certification_requirements, limit=16),
        "employment_constraints": bounded(job.get("employment_constraints"), limit=16),
        "mandatory_clauses": job_mandatory_clauses,
        "preferred_skills": preferred_skills,
        "seniority": str(job.get("seniority") or ""),
        "job_family": str(job.get("job_family") or ""),
        "domain": str(job.get("domain") or ""),
        "responsibilities": bounded(job.get("responsibilities")),
        "technology_requirements": technology_requirements,
        "language_requirements": [
            str(value).strip()
            for value in list(job.get("language_requirements") or job.get("languages") or [])
            if str(value).strip()
        ],
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
        "mandatory_facts": mandatory_facts,
        "mandatory_clauses": candidate_mandatory_clauses,
    }
    contract_metadata = {
        "version": RANKING_INPUT_CONTRACT_VERSION,
        "semantic_policy_fingerprint": str(policy.get("policy_fingerprint") or ""),
        "canonical_checksums": {
            "job_requirements": _stable_json_fingerprint(requirements),
            "candidate_facts": _stable_json_fingerprint(candidate),
            "job_requirements_complete": _stable_json_fingerprint({
                key: job.get(key)
                for key in (
                    "title", "required_skills", "required_skills_canonical",
                    "preferred_skills", "preferred_skills_canonical", "tech_stack",
                    "tech_stack_canonical", "language_requirements", "languages",
                    "location", "actual_location", "location_type", "years_experience_min",
                    "years_experience_max", "seniority", "job_family", "domain",
                    "responsibilities",
                    "qualifications", "education_requirements", "certification_requirements",
                    "certifications", "employment_constraints", "mandatory_clauses",
                )
                if key in job
            }),
            "candidate_facts_complete": _stable_json_fingerprint({
                key: value
                for key, value in profile.items()
                if not str(key).startswith("_")
            }),
        },
        "omitted_counts": {
            "candidate_skills": max(0, len(all_candidate_skills) - len(candidate_skills)),
            "evidence": max(0, len(projected_evidence) - len(evidence)),
        },
        "mandatory_omissions": mandatory_omissions,
        "requirement_ids": [
            *[f"required:{index}" for index in range(len(required_skills))],
            *[f"technology:{index}" for index in range(len(technology_requirements))],
            *[f"preferred:{index}" for index in range(len(preferred_skills))],
            *[f"responsibility:{index}" for index in range(len(requirements["responsibilities"]))],
            *[f"mandatory:{record['clause_id']}" for record in job_mandatory_clauses],
        ],
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
        except RankingInputBudgetExceeded as exc:
            return {
                "job_url": str(job.get("job_url", "")),
                **{
                    field_name: job[field_name]
                    for field_name in ("run_job_id", "raw_job_fingerprint", "source_job_url")
                    if job.get(field_name) not in (None, "")
                },
                "ai_score": None, "legacy_model_fit_label": None,
                "score_status": SCORE_STATUS_UNSCORED,
                "score_state": "evidence_limited" if isinstance(exc, RankingInputEvidenceLimited) else "unscored",
                "evidence_limited": isinstance(exc, RankingInputEvidenceLimited),
                "failure_code": exc.failure_code,
                "retry_eligible": False,
                "score_reasoning": f"Scoring error: {exc}",
                "matched_strengths": [], "key_risks": [],
                "parser_status": exc.failure_code,
                "ranking_input_diagnostics": {
                    "contract_version": RANKING_INPUT_CONTRACT_VERSION,
                    "request_within_budget": False,
                    "request_max_chars": RANKING_REQUEST_MAX_CHARS,
                    "prompt_truncated": True,
                    "prompt_truncation_steps": ["mandatory_core_did_not_fit"],
                    "visibility_manifest": exc.visibility_manifest,
                },
            }
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
                "ranking_input_diagnostics": build_ranking_input_diagnostics(
                    ranking_input,
                    request_record if "request_record" in locals() else None,
                ),
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

