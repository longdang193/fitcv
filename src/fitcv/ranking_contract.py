"""@meta
name: ranking_contract
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.stage-artifact-diagnostics
responsibility:
  - Shared ranking contracts for thresholds, fit-label mapping, and validation.
inputs:
  - Ranking config and score values
outputs:
  - Validated thresholds, labels, and invariant checks
lifecycle:
  - status: active
"""

import hashlib
import json
import math
from typing import Any, Mapping

FIT_LABEL_STRONG = "strong"
FIT_LABEL_STRETCH = "stretch"
FIT_LABEL_SKIP = "skip"
VALID_FIT_LABELS = frozenset({FIT_LABEL_STRONG, FIT_LABEL_STRETCH, FIT_LABEL_SKIP})
SCORE_STATUS_VALID = "valid"
SCORE_STATUS_UNSCORED = "unscored"
SCORE_STATUS_INVALID = "invalid"
SCORE_STATUSES = frozenset({SCORE_STATUS_VALID, SCORE_STATUS_UNSCORED, SCORE_STATUS_INVALID})

STRUCTURED_FACTOR_IDS = (
    "must_have_match",
    "title_relevance",
    "seniority_fit",
    "declared_preference_fit",
    "location_fit",
    "language_fit",
)
CORE_STRUCTURED_FACTOR_IDS = STRUCTURED_FACTOR_IDS[:4]
OPTIONAL_ELIGIBILITY_FACTOR_IDS = STRUCTURED_FACTOR_IDS[4:]
BASELINE_WEIGHT_IDS = ("holistic_ai_fit", "structured_fit")
DECLARED_PREFERENCE_COMPONENT_IDS = ("domain", "role_family", "work_mode")
RANKING_POLICY_KEYS = frozenset(
    {
        "policy_version",
        "normalizer_version",
        "active_baseline_mode",
        "baseline_weights",
        "structured_factor_weights",
        "declared_preference_component_weights",
        "missing_value_defaults",
        "fit_label_thresholds",
        "label_migration_gate",
    }
)
NORMALIZER_IDS = {
    "holistic_ai_fit": "clamped-ai-score-v1",
    "must_have_match": "required-skill-ratio-v1",
    "title_relevance": "title-role-overlap-v1",
    "seniority_fit": "seniority-ladder-distance-v1",
    "declared_preference_fit": "declared-preference-v1",
    "location_fit": "eligibility-location-projection-v1",
    "language_fit": "eligibility-language-projection-v1",
}
RANKING_ORDER_VERSION = "baseline-all-eligible-personalized-fingerprint-url-v1"
AI_COMPATIBILITY_RANKING_ORDER_VERSION = "ai-compatibility-v1"
# New Stage 6 runs use the holistic AI score directly. Keep the existing order
# versions readable so historical personalized rows remain compatible.
AI_ONLY_RANKING_ORDER_VERSION = "ai-only-finite-ai-score-fingerprint-url-v1"
RANKING_SCORE_CONTRACT_VERSION = "ranking_score_v1"
RANKING_DECISION_ENVELOPE_VERSION = "ranking_decision_envelope_v1"
RANKING_CV_HANDOFF_VERSION = "ranking_cv_handoff_v1"
LEGACY_ADAPTER_VERSION = "ranking-row-legacy-v1"

_RANKING_CV_HANDOFF_FIELDS = (
    "schema_version",
    "canonical_job_identity",
    "job_qualifiers",
    "baseline_rank",
    "baseline_score",
    "score_status",
    "failure_code",
    "disposition",
    "retry_eligible",
    "evidence_ids",
    "confirmed_gaps",
    "confirmed_unknowns",
    "candidate_profile_revision",
    "ranking_order_version",
    "ranking_policy_version",
    "ranking_contract_version",
    "source_provenance",
)

def _fit_label_from_thresholds(score: float, thresholds: Mapping[str, Any]) -> str:
    exact_thresholds = _mapping(thresholds, "ranking_policy.fit_label_thresholds")
    _exact_keys(
        exact_thresholds,
        frozenset({"strong", "stretch"}),
        "ranking_policy.fit_label_thresholds",
    )
    strong = _unit_float(
        exact_thresholds["strong"],
        "ranking_policy.fit_label_thresholds.strong",
    )
    stretch = _unit_float(
        exact_thresholds["stretch"],
        "ranking_policy.fit_label_thresholds.stretch",
    )
    if strong <= stretch:
        raise ValueError("ranking_policy.fit_label_thresholds.strong must be > stretch")
    if score >= strong:
        return FIT_LABEL_STRONG
    if score >= stretch:
        return FIT_LABEL_STRETCH
    return FIT_LABEL_SKIP


def fit_label_from_score(score: float, config: dict[str, Any]) -> str:
    ranking_policy = _mapping(config.get("ranking_policy"), "ranking_policy")
    return _fit_label_from_thresholds(score, ranking_policy.get("fit_label_thresholds"))


def resolve_fit_label_for_row(
    row: Mapping[str, Any],
    config: dict[str, Any],
) -> str | None:
    """Resolve a ranking label from the canonical numeric score and thresholds."""
    normalized = dict(row)
    if normalized.get("baseline_fit") is None and normalized.get("final_score") is not None:
        normalized["baseline_fit"] = normalized["final_score"]
    score_state = normalize_score_state(normalized)
    if score_state["score_status"] != SCORE_STATUS_VALID:
        return None
    ranking_policy = dict(config.get("ranking_policy") or {})
    baseline_weights = dict(ranking_policy.get("baseline_weights") or {})
    if normalized.get("baseline_fit") is None and baseline_weights == {
        "holistic_ai_fit": 1.0,
        "structured_fit": 0.0,
    }:
        normalized["baseline_fit"] = score_state.get("ai_score")
    raw_score = normalized.get("baseline_fit")
    if not is_finite_score(raw_score):
        return None
    return fit_label_from_score(float(raw_score), config)


def is_finite_score(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and 0.0 <= float(value) <= 1.0
    )


def normalize_score_state(row: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize current and legacy score rows without inventing scores."""
    raw_status = str(row.get("score_status") or "").strip().lower()
    raw_failure = str(row.get("failure_code") or "").strip() or None
    parser_status = str(
        row.get("parser_status") or row.get("reranker_parser_status") or ""
    ).strip().lower()
    score_reasoning = str(
        row.get("score_reasoning") or row.get("reranker_score_reasoning") or ""
    ).strip().lower()
    score = row.get("ai_score")
    if score is None and raw_status == SCORE_STATUS_VALID:
        score = row.get("holistic_ai_fit", row.get("baseline_fit"))
    elif score is None and not raw_status and not raw_failure and not parser_status:
        score = row.get("holistic_ai_fit", row.get("baseline_fit"))

    parser_failures = {
        "malformed_json": SCORE_STATUS_INVALID,
        "non_object_payload": SCORE_STATUS_INVALID,
        "missing_ai_score": SCORE_STATUS_INVALID,
        "invalid_ai_score": SCORE_STATUS_INVALID,
    }
    if raw_failure in parser_failures:
        status = parser_failures[raw_failure]
    elif raw_failure in {"timeout", "adapter_timeout"}:
        status = SCORE_STATUS_UNSCORED
        raw_failure = "timeout"
    elif raw_failure in {
        "provider_failure",
        "adapter_http_error",
        "adapter_transport_error",
        "adapter_contract_error",
    }:
        status = SCORE_STATUS_UNSCORED
        raw_failure = "provider_failure"
    elif raw_failure in {"validation_failure", "validation_error"}:
        status = SCORE_STATUS_INVALID
        raw_failure = "validation_failure"
    elif raw_status in SCORE_STATUSES:
        status = raw_status
    elif parser_status in parser_failures:
        status = parser_failures[parser_status]
        raw_failure = raw_failure or parser_status
    elif parser_status == "runtime_exception":
        status = SCORE_STATUS_UNSCORED
        raw_failure = raw_failure or "provider_failure"
    elif "parse failure" in score_reasoning:
        status = SCORE_STATUS_INVALID
        raw_failure = raw_failure or "parser_failure"
    elif "scoring error" in score_reasoning:
        status = SCORE_STATUS_UNSCORED
        raw_failure = raw_failure or "provider_failure"
    elif is_finite_score(score):
        status = SCORE_STATUS_VALID
    else:
        status = SCORE_STATUS_UNSCORED
        raw_failure = raw_failure or "legacy_ambiguous_score_state"

    if status == SCORE_STATUS_VALID and not is_finite_score(score):
        status = SCORE_STATUS_INVALID
        raw_failure = raw_failure or "invalid_ai_score"
    if status == SCORE_STATUS_INVALID and not raw_failure:
        raw_failure = "validation_failure"
    if status == SCORE_STATUS_UNSCORED and not raw_failure:
        raw_failure = "score_unavailable"
    disposition = str(row.get("disposition") or "").strip() or None
    if disposition is None:
        if status == SCORE_STATUS_VALID:
            disposition = "scored"
        elif raw_failure == "needs_enrichment":
            disposition = "needs_enrichment"
        elif status == SCORE_STATUS_INVALID:
            disposition = "invalid_score"
        elif raw_failure in {"timeout", "provider_failure", "budget_exceeded"}:
            disposition = "retryable_failure"
        else:
            disposition = "unavailable"
    retry_value = row.get("retry_eligible")
    retry_eligible = (
        bool(retry_value)
        if retry_value is not None
        else status == SCORE_STATUS_UNSCORED and raw_failure in {
            "needs_enrichment",
            "timeout",
            "provider_failure",
            "budget_exceeded",
        }
    )
    return {
        "ai_score": float(score) if status == SCORE_STATUS_VALID and score is not None else None,
        "score_status": status,
        "failure_code": raw_failure,
        "disposition": disposition,
        "retry_eligible": retry_eligible,
    }


_EXPORT_SCORE_STATE_INPUT_FIELDS = (
    "ai_score",
    "score_status",
    "failure_code",
    "parser_status",
    "reranker_parser_status",
    "score_reasoning",
    "reranker_score_reasoning",
    "final_score",
    "holistic_ai_fit",
    "baseline_fit",
    "personalized_display_score",
)


def normalize_score_state_for_export(row: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize export rows without inventing failures for stage-only outcomes."""
    has_score_evidence = any(
        row.get(field) not in (None, "")
        for field in _EXPORT_SCORE_STATE_INPUT_FIELDS
        if field != "score_status"
    )
    has_stage_disposition = bool(str(row.get("pipeline_status") or "").strip()) or isinstance(
        row.get("job_outcome"), Mapping
    )
    if not has_score_evidence and has_stage_disposition:
        return {
            "ai_score": None,
            "score_status": SCORE_STATUS_UNSCORED,
            "failure_code": None,
            "disposition": "not_scored",
            "retry_eligible": False,
        }
    if not any(row.get(field) not in (None, "") for field in _EXPORT_SCORE_STATE_INPUT_FIELDS):
        return {
            "ai_score": None,
            "score_status": SCORE_STATUS_UNSCORED,
            "failure_code": None,
            "disposition": "unavailable",
            "retry_eligible": False,
        }
    return normalize_score_state(row)


def validate_weight_contract(weights: dict[str, float], *, expected_sum: float = 1.0) -> None:
    total = 0.0
    for feature_name, value in weights.items():
        if value < 0.0 or value > 1.0:
            raise ValueError(
                f"Invalid ranking weight for '{feature_name}': {value}. Expected within [0.0, 1.0]."
            )
        total += value
    if abs(total - expected_sum) > 1e-6:
        raise ValueError(
            f"Invalid ranking weights sum: {total}. Expected {expected_sum}."
        )


def _exact_keys(payload: Mapping[str, Any], expected: frozenset[str], label: str) -> None:
    unknown = sorted(set(payload) - expected)
    if unknown:
        raise ValueError(f"Unknown {label} keys: {unknown}")
    missing = sorted(expected - set(payload))
    if missing:
        raise ValueError(f"Missing {label} keys: {missing}")


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return dict(value)


def _unit_float(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite number within [0.0, 1.0]")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite number within [0.0, 1.0]") from exc
    if not math.isfinite(parsed) or not 0.0 <= parsed <= 1.0:
        raise ValueError(f"{label} must be a finite number within [0.0, 1.0]")
    return parsed


def _exact_weight_map(value: Any, keys: tuple[str, ...], label: str) -> dict[str, float]:
    payload = _mapping(value, label)
    _exact_keys(payload, frozenset(keys), label)
    weights = {key: _unit_float(payload[key], f"{label}.{key}") for key in keys}
    validate_weight_contract(weights)
    return weights


def validate_ranking_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    validated = _mapping(policy, "ranking_policy")
    _exact_keys(validated, RANKING_POLICY_KEYS, "ranking_policy")
    if validated["policy_version"] != "ranking-v2":
        raise ValueError("ranking_policy.policy_version must be ranking-v2")
    if validated["normalizer_version"] != "absolute-fit-v1":
        raise ValueError("ranking_policy.normalizer_version must be absolute-fit-v1")
    if validated["active_baseline_mode"] != "holistic_ai_only":
        raise ValueError("ranking_policy.active_baseline_mode must be holistic_ai_only")

    validated["baseline_weights"] = _exact_weight_map(
        validated["baseline_weights"], BASELINE_WEIGHT_IDS, "ranking_policy.baseline_weights"
    )
    if validated["baseline_weights"] != {
        "holistic_ai_fit": 1.0,
        "structured_fit": 0.0,
    }:
        raise ValueError(
            "ranking_policy.baseline_weights must equal "
            "{'holistic_ai_fit': 1.0, 'structured_fit': 0.0} "
            "while active_baseline_mode is holistic_ai_only"
        )
    validated["structured_factor_weights"] = _exact_weight_map(
        validated["structured_factor_weights"],
        STRUCTURED_FACTOR_IDS,
        "ranking_policy.structured_factor_weights",
    )
    validated["declared_preference_component_weights"] = _exact_weight_map(
        validated["declared_preference_component_weights"],
        DECLARED_PREFERENCE_COMPONENT_IDS,
        "ranking_policy.declared_preference_component_weights",
    )

    missing_defaults = _mapping(
        validated["missing_value_defaults"], "ranking_policy.missing_value_defaults"
    )
    missing_ids = ("holistic_ai_fit", *STRUCTURED_FACTOR_IDS)
    _exact_keys(
        missing_defaults,
        frozenset(missing_ids),
        "ranking_policy.missing_value_defaults",
    )
    validated["missing_value_defaults"] = {
        key: _unit_float(missing_defaults[key], f"ranking_policy.missing_value_defaults.{key}")
        for key in missing_ids
    }

    thresholds = _mapping(validated["fit_label_thresholds"], "ranking_policy.fit_label_thresholds")
    _exact_keys(thresholds, frozenset({"strong", "stretch"}), "ranking_policy.fit_label_thresholds")
    thresholds = {
        "strong": _unit_float(thresholds["strong"], "ranking_policy.fit_label_thresholds.strong"),
        "stretch": _unit_float(thresholds["stretch"], "ranking_policy.fit_label_thresholds.stretch"),
    }
    if thresholds["strong"] <= thresholds["stretch"]:
        raise ValueError("ranking_policy.fit_label_thresholds.strong must be > stretch")
    validated["fit_label_thresholds"] = thresholds

    gate = _mapping(validated["label_migration_gate"], "ranking_policy.label_migration_gate")
    _exact_keys(
        gate,
        frozenset({"maximum_total_label_migration_rate", "maximum_strong_skip_crossings"}),
        "ranking_policy.label_migration_gate",
    )
    crossings = gate["maximum_strong_skip_crossings"]
    if isinstance(crossings, bool) or not isinstance(crossings, int) or crossings < 0:
        raise ValueError(
            "ranking_policy.label_migration_gate.maximum_strong_skip_crossings "
            "must be a non-negative integer"
        )
    validated["label_migration_gate"] = {
        "maximum_total_label_migration_rate": _unit_float(
            gate["maximum_total_label_migration_rate"],
            "ranking_policy.label_migration_gate.maximum_total_label_migration_rate",
        ),
        "maximum_strong_skip_crossings": crossings,
    }
    return validated


def _canonical_fingerprint(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _normalized_handoff_string(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _canonical_handoff_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key).strip(): _canonical_handoff_value(inner)
            for key, inner in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_canonical_handoff_value(item) for item in value]
    if isinstance(value, str):
        return value.strip()
    return value


def _ordered_handoff_strings(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple, set, frozenset)):
        raise ValueError(f"ranking_cv_handoff.{field} must be an array")
    return sorted(
        {
            normalized
            for item in value
            if (normalized := _normalized_handoff_string(item)) is not None
        }
    )


def canonicalize_ranking_cv_handoff(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return the exact object covered by the ranking-to-CV fingerprint."""
    if not isinstance(payload, Mapping):
        raise ValueError("ranking_cv_handoff must be an object")
    canonical = {
        "schema_version": _normalized_handoff_string(payload.get("schema_version")),
        "canonical_job_identity": _canonical_handoff_value(
            payload.get("canonical_job_identity")
        ),
        "job_qualifiers": _canonical_handoff_value(payload.get("job_qualifiers")),
        "baseline_rank": payload.get("baseline_rank"),
        "baseline_score": payload.get(
            "baseline_score",
            payload.get("baseline_fit", payload.get("final_score")),
        ),
        "score_status": _normalized_handoff_string(payload.get("score_status")),
        "failure_code": _normalized_handoff_string(payload.get("failure_code")),
        "disposition": _normalized_handoff_string(payload.get("disposition")),
        "retry_eligible": payload.get("retry_eligible"),
        "evidence_ids": _ordered_handoff_strings(
            payload.get("evidence_ids", payload.get("canonical_evidence_ids")),
            "evidence_ids",
        ),
        "confirmed_gaps": _ordered_handoff_strings(
            payload.get("confirmed_gaps", payload.get("gaps")),
            "confirmed_gaps",
        ),
        "confirmed_unknowns": _ordered_handoff_strings(
            payload.get("confirmed_unknowns", payload.get("unknowns")),
            "confirmed_unknowns",
        ),
        "candidate_profile_revision": _normalized_handoff_string(
            payload.get("candidate_profile_revision", payload.get("profile_revision"))
        ),
        "ranking_order_version": _normalized_handoff_string(
            payload.get("ranking_order_version")
        ),
        "ranking_policy_version": _normalized_handoff_string(
            payload.get("ranking_policy_version")
        ),
        "ranking_contract_version": _normalized_handoff_string(
            payload.get("ranking_contract_version", RANKING_SCORE_CONTRACT_VERSION)
        ),
        "source_provenance": _canonical_handoff_value(
            payload.get("source_provenance", payload.get("provenance"))
        ),
    }
    return canonical


def validate_ranking_cv_handoff(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return the canonical ranking-to-CV handoff object."""
    canonical = canonicalize_ranking_cv_handoff(payload)
    if canonical["schema_version"] != RANKING_CV_HANDOFF_VERSION:
        raise ValueError(
            f"ranking_cv_handoff.schema_version must be {RANKING_CV_HANDOFF_VERSION}"
        )
    if canonical["canonical_job_identity"] in (None, "", {}):
        raise ValueError("ranking_cv_handoff.canonical_job_identity is required")
    if canonical["job_qualifiers"] is None:
        raise ValueError("ranking_cv_handoff.job_qualifiers is required")
    rank = canonical["baseline_rank"]
    if rank is not None and (isinstance(rank, bool) or not isinstance(rank, int) or rank < 1):
        raise ValueError("ranking_cv_handoff.baseline_rank must be a positive integer or null")
    score = canonical["baseline_score"]
    if score is not None and not is_finite_score(score):
        raise ValueError("ranking_cv_handoff.baseline_score must be a finite score or null")
    if canonical["score_status"] not in SCORE_STATUSES:
        raise ValueError("ranking_cv_handoff.score_status is invalid")
    if canonical["score_status"] == SCORE_STATUS_VALID and (score is None or rank is None):
        raise ValueError("valid ranking_cv_handoff rows require baseline rank and score")
    if canonical["disposition"] is None:
        raise ValueError("ranking_cv_handoff.disposition is required")
    if not isinstance(canonical["retry_eligible"], bool):
        raise ValueError("ranking_cv_handoff.retry_eligible must be boolean")
    for field in (
        "candidate_profile_revision",
        "ranking_order_version",
        "ranking_policy_version",
        "ranking_contract_version",
    ):
        if canonical[field] is None:
            raise ValueError(f"ranking_cv_handoff.{field} is required")
    if not isinstance(canonical["source_provenance"], Mapping) or not canonical["source_provenance"]:
        raise ValueError("ranking_cv_handoff.source_provenance is required")
    return canonical


def ranking_cv_handoff_sha256(payload: Mapping[str, Any]) -> str:
    canonical = validate_ranking_cv_handoff(payload)
    encoded = json.dumps(
        canonical,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_ranking_cv_handoff(
    row: Mapping[str, Any],
    *,
    candidate_profile_revision: Any = None,
    ranking_order_version: Any = None,
    ranking_policy_version: Any = None,
    ranking_contract_version: Any = RANKING_SCORE_CONTRACT_VERSION,
    source_provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one immutable, fingerprinted ranking-to-CV handoff."""
    score_state = normalize_score_state(row)
    source_provenance_value = source_provenance
    if source_provenance_value is None:
        source_provenance_value = row.get("source_provenance", row.get("provenance"))
    if isinstance(source_provenance_value, Mapping):
        source_provenance_value = dict(source_provenance_value)
        provenance_aliases = (
            ("jd_reference", "jd_reference"),
            ("ranking_input_fingerprint", "ranking_input_fingerprint"),
            ("ranking_input_fingerprint", "ai_score_input_fingerprint"),
            ("raw_job_fingerprint", "raw_job_fingerprint"),
        )
        for provenance_key, row_key in provenance_aliases:
            if provenance_key not in source_provenance_value and row.get(row_key) not in (None, ""):
                source_provenance_value[provenance_key] = row[row_key]
        if "jd_reference" not in source_provenance_value:
            for row_key in ("job_url", "source_job_url"):
                if row.get(row_key) not in (None, ""):
                    source_provenance_value["jd_reference"] = row[row_key]
                    break
    baseline_score = row.get("baseline_score", row.get("baseline_fit"))
    if score_state["score_status"] == SCORE_STATUS_VALID:
        baseline_score = score_state["ai_score"]
    else:
        baseline_score = None
    canonical = validate_ranking_cv_handoff(
        {
            "schema_version": RANKING_CV_HANDOFF_VERSION,
            "canonical_job_identity": row.get(
                "canonical_job_identity",
                row.get("job_identity", row.get("raw_job_fingerprint")),
            ),
            "job_qualifiers": row.get(
                "job_qualifiers",
                row.get("qualifiers", row.get("job", {}).get("qualifiers") if isinstance(row.get("job"), Mapping) else None),
            ),
            "baseline_rank": row.get("baseline_rank"),
            "baseline_score": baseline_score,
            "score_status": score_state["score_status"],
            "failure_code": score_state["failure_code"],
            "disposition": score_state["disposition"],
            "retry_eligible": score_state["retry_eligible"],
            "evidence_ids": row.get(
                "evidence_ids",
                row.get("canonical_evidence_ids", row.get("selected_evidence_ids")),
            ),
            "confirmed_gaps": row.get("confirmed_gaps", row.get("gaps")),
            "confirmed_unknowns": row.get("confirmed_unknowns", row.get("unknowns")),
            "candidate_profile_revision": candidate_profile_revision
            if candidate_profile_revision is not None
            else row.get("candidate_profile_revision", row.get("profile_revision")),
            "ranking_order_version": ranking_order_version
            if ranking_order_version is not None
            else row.get("ranking_order_version"),
            "ranking_policy_version": ranking_policy_version
            if ranking_policy_version is not None
            else row.get("ranking_policy_version"),
            "ranking_contract_version": ranking_contract_version
            if ranking_contract_version is not None
            else row.get("ranking_contract_version"),
            "source_provenance": source_provenance_value,
        }
    )
    return {
        **canonical,
        "handoff_fingerprint": ranking_cv_handoff_sha256(canonical),
    }


def build_ranking_contract_context(
    policy: Mapping[str, Any],
    *,
    eligibility_policy: Mapping[str, Any],
    eligibility_policy_fingerprint: str,
) -> dict[str, Any]:
    validated = validate_ranking_policy(policy)
    eligibility_factors = _mapping(
        _mapping(eligibility_policy, "eligibility_policy").get("factors"),
        "eligibility_policy.factors",
    )
    retained = list(CORE_STRUCTURED_FACTOR_IDS)
    for factor_id in OPTIONAL_ELIGIBILITY_FACTOR_IDS:
        factor_policy = _mapping(eligibility_factors.get(factor_id), f"eligibility_policy.factors.{factor_id}")
        if factor_policy.get("mode") == "ranking_only":
            retained.append(factor_id)
    configured = validated["structured_factor_weights"]
    retained_total = sum(configured[factor_id] for factor_id in retained)
    if retained_total <= 0.0:
        raise ValueError("Effective structured factor weights must have positive total")
    effective = {
        factor_id: configured[factor_id] / retained_total
        for factor_id in retained
    }
    fingerprint_payload = {
        "ranking_policy": validated,
        "effective_structured_factor_weights": effective,
        "factor_ids": list(STRUCTURED_FACTOR_IDS),
        "normalizer_ids": NORMALIZER_IDS,
        "eligibility_policy_fingerprint": str(eligibility_policy_fingerprint),
        "ranking_order_version": RANKING_ORDER_VERSION,
        "ranking_score_contract_version": RANKING_SCORE_CONTRACT_VERSION,
        "ranking_decision_envelope_version": RANKING_DECISION_ENVELOPE_VERSION,
        "legacy_adapter_version": LEGACY_ADAPTER_VERSION,
    }
    return {
        "ranking_policy": validated,
        "effective_structured_factor_weights": effective,
        "ranking_contract_fingerprint": _canonical_fingerprint(fingerprint_payload),
        "ranking_order_version": RANKING_ORDER_VERSION,
        "ranking_score_contract_version": RANKING_SCORE_CONTRACT_VERSION,
        "ranking_decision_envelope_version": RANKING_DECISION_ENVELOPE_VERSION,
        "legacy_adapter_version": LEGACY_ADAPTER_VERSION,
    }


def build_baseline_result(
    *,
    holistic_ai_fit: Any,
    structured_factors: Mapping[str, Any],
    context: Mapping[str, Any],
    holistic_score_status: str | None = None,
    holistic_failure_code: str | None = None,
) -> dict[str, Any]:
    policy = _mapping(context.get("ranking_policy"), "ranking_contract.ranking_policy")
    defaults = _mapping(policy["missing_value_defaults"], "ranking_policy.missing_value_defaults")
    configured = _mapping(policy["structured_factor_weights"], "ranking_policy.structured_factor_weights")
    effective = _mapping(
        context.get("effective_structured_factor_weights"),
        "ranking_contract.effective_structured_factor_weights",
    )
    factor_values = dict(structured_factors)
    unknown = sorted(set(factor_values) - set(STRUCTURED_FACTOR_IDS))
    if unknown:
        raise ValueError(f"Unknown structured factors: {unknown}")

    normalized_factors: dict[str, dict[str, Any]] = {}
    structured_fit = 0.0
    for factor_id in STRUCTURED_FACTOR_IDS:
        missing = factor_id not in factor_values or factor_values[factor_id] is None
        value = defaults[factor_id] if missing else _unit_float(factor_values[factor_id], factor_id)
        effective_weight = float(effective.get(factor_id, 0.0))
        contribution = value * effective_weight
        structured_fit += contribution
        normalized_factors[factor_id] = {
            "value": value,
            "source": "missing_default" if missing else "provided",
            "normalizer_id": NORMALIZER_IDS[factor_id],
            "missing_default_applied": missing,
            "ranking_enabled": factor_id in effective,
            "configured_weight": float(configured[factor_id]),
            "effective_weight": effective_weight,
            "contribution": contribution,
        }

    score_state = normalize_score_state(
        {
            "ai_score": holistic_ai_fit,
            "score_status": holistic_score_status,
            "failure_code": holistic_failure_code,
        }
    )
    holistic_missing = score_state["score_status"] != SCORE_STATUS_VALID
    holistic_value = score_state["ai_score"]
    baseline_weights = _mapping(policy["baseline_weights"], "ranking_policy.baseline_weights")
    baseline_fit = None
    label = None
    if not holistic_missing:
        if context.get("ranking_order_version") == AI_ONLY_RANKING_ORDER_VERSION:
            baseline_fit = float(holistic_value)
        else:
            baseline_fit = (
                float(holistic_value) * float(baseline_weights["holistic_ai_fit"])
                + structured_fit * float(baseline_weights["structured_fit"])
            )
        label = _fit_label_from_thresholds(baseline_fit, policy["fit_label_thresholds"])
    return {
        "holistic_ai_fit": holistic_value,
        "holistic_ai_fit_missing_default_applied": False,
        "score_status": score_state["score_status"],
        "failure_code": score_state["failure_code"],
        "structured_fit": structured_fit,
        "baseline_fit": baseline_fit,
        "baseline_fit_label": label,
        "baseline_mode": policy["active_baseline_mode"],
        "normalized_factors": normalized_factors,
        "ranking_policy_version": policy["policy_version"],
        "normalizer_version": policy["normalizer_version"],
        "ranking_order_version": context.get("ranking_order_version", RANKING_ORDER_VERSION),
        "ranking_score_contract_version": context.get(
            "ranking_score_contract_version", RANKING_SCORE_CONTRACT_VERSION
        ),
        "ranking_decision_envelope_version": context.get(
            "ranking_decision_envelope_version", RANKING_DECISION_ENVELOPE_VERSION
        ),
        "ranking_contract_fingerprint": context["ranking_contract_fingerprint"],
    }


def _normalized_alias_value(field: str, value: Any) -> Any:
    if field in {"baseline_fit", "baseline_rank"}:
        parsed = _unit_float(value, field) if field == "baseline_fit" else int(value)
        return parsed
    return str(value or "").strip().lower()


def adapt_legacy_ranking_row(row: Mapping[str, Any]) -> dict[str, Any]:
    adapted = dict(row)
    aliases = {
        "baseline_fit": "final_score",
        "baseline_fit_label": "fit_label",
        "baseline_rank": "final_rank",
    }
    for canonical, legacy in aliases.items():
        canonical_present = canonical in adapted and adapted[canonical] is not None
        legacy_present = legacy in adapted and adapted[legacy] is not None
        if canonical_present and legacy_present:
            if _normalized_alias_value(canonical, adapted[canonical]) != _normalized_alias_value(
                canonical, adapted[legacy]
            ):
                raise ValueError(f"conflicting ranking fields: {canonical} and {legacy}")
        elif legacy_present:
            adapted[canonical] = _normalized_alias_value(canonical, adapted[legacy])
        adapted.pop(legacy, None)
    if "baseline_fit_label" in adapted:
        adapted["baseline_fit_label"] = _normalized_alias_value(
            "baseline_fit_label", adapted["baseline_fit_label"]
        )
    if "baseline_fit" in adapted:
        adapted["baseline_fit"] = float(adapted["baseline_fit"])
    if "baseline_rank" in adapted:
        adapted["baseline_rank"] = int(adapted["baseline_rank"])
    return adapted


def project_legacy_ranking_aliases(row: Mapping[str, Any]) -> dict[str, Any]:
    projected = dict(row)
    if "baseline_fit" in row:
        projected["final_score"] = row["baseline_fit"]
    if "baseline_fit_label" in row:
        projected["fit_label"] = row["baseline_fit_label"]
    if "baseline_rank" in row:
        projected["final_rank"] = row["baseline_rank"]
    return projected


def build_label_migration_summary(
    rows: list[Mapping[str, Any]],
    gate: Mapping[str, Any],
) -> dict[str, Any]:
    labels = (FIT_LABEL_STRONG, FIT_LABEL_STRETCH, FIT_LABEL_SKIP)
    matrix = {old: {new: 0 for new in labels} for old in labels}
    comparable = 0
    migrated = 0
    crossings = 0
    for row in rows:
        old = str(row.get("legacy_model_fit_label") or "").strip().lower()
        new = str(row.get("baseline_fit_label") or "").strip().lower()
        if old not in VALID_FIT_LABELS or new not in VALID_FIT_LABELS:
            continue
        comparable += 1
        matrix[old][new] += 1
        if old != new:
            migrated += 1
        if {old, new} == {FIT_LABEL_STRONG, FIT_LABEL_SKIP}:
            crossings += 1

    reasons: list[str] = []
    migration_rate = migrated / comparable if comparable else 0.0
    if comparable == 0:
        status = "insufficient_evidence"
        reasons.append("no_comparable_legacy_labels")
    else:
        if migration_rate > float(gate["maximum_total_label_migration_rate"]):
            reasons.append("total_migration_rate_exceeded")
        if crossings > int(gate["maximum_strong_skip_crossings"]):
            reasons.append("strong_skip_crossings_exceeded")
        status = "failed" if reasons else "passed"
    return {
        "status": status,
        "comparable_row_count": comparable,
        "migration_matrix": matrix,
        "total_migration_rate": migration_rate,
        "strong_skip_crossings": crossings,
        "reason_codes": reasons,
    }

