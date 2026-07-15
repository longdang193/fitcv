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
RANKING_ORDER_VERSION = "baseline-fingerprint-url-v1"
LEGACY_ADAPTER_VERSION = "ranking-row-legacy-v1"

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
        "legacy_adapter_version": LEGACY_ADAPTER_VERSION,
    }
    return {
        "ranking_policy": validated,
        "effective_structured_factor_weights": effective,
        "ranking_contract_fingerprint": _canonical_fingerprint(fingerprint_payload),
        "ranking_order_version": RANKING_ORDER_VERSION,
        "legacy_adapter_version": LEGACY_ADAPTER_VERSION,
    }


def build_baseline_result(
    *,
    holistic_ai_fit: Any,
    structured_factors: Mapping[str, Any],
    context: Mapping[str, Any],
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

    holistic_missing = holistic_ai_fit is None
    holistic_value = (
        float(defaults["holistic_ai_fit"])
        if holistic_missing
        else _unit_float(holistic_ai_fit, "holistic_ai_fit")
    )
    baseline_weights = _mapping(policy["baseline_weights"], "ranking_policy.baseline_weights")
    baseline_fit = (
        holistic_value * float(baseline_weights["holistic_ai_fit"])
        + structured_fit * float(baseline_weights["structured_fit"])
    )
    label = _fit_label_from_thresholds(baseline_fit, policy["fit_label_thresholds"])
    return {
        "holistic_ai_fit": holistic_value,
        "holistic_ai_fit_missing_default_applied": holistic_missing,
        "structured_fit": structured_fit,
        "baseline_fit": baseline_fit,
        "baseline_fit_label": label,
        "baseline_mode": policy["active_baseline_mode"],
        "normalized_factors": normalized_factors,
        "ranking_policy_version": policy["policy_version"],
        "normalizer_version": policy["normalizer_version"],
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

