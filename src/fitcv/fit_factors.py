"""@meta
name: fit_factors
type: utility
domain: eligibility
ownership: feature
capabilities:
  - cv_system.location-language-eligibility
responsibility:
  - Validate and fingerprint eligibility policy.
  - Adapt candidate profile facts and evaluate symmetric fit factors.
inputs:
  - Candidate profile, canonical job facts, eligibility policy
outputs:
  - Deterministic JSON-safe factor and eligibility records
lifecycle:
  - status: active
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from typing import Any, Literal, TypedDict, cast

FactorId = Literal["location_fit", "language_fit"]
EvaluationStatus = Literal["pass", "fail", "unknown", "not_applicable"]
PolicyMode = Literal["disabled", "ranking_only", "gate_required"]
EligibilityDecision = Literal["retain", "reject"]
LanguageLevel = Literal["a1", "a2", "b1", "b2", "c1", "c2", "native", "unknown"]
LanguageSource = Literal["native", "level", "read_write_speak", "unknown"]

ELIGIBILITY_POLICY_VERSION = "eligibility-v1"
ACTUAL_LOCATION_EXTRACTION_VERSION = "actual-location-extraction-v1"
LANGUAGE_REQUIREMENT_EXTRACTION_VERSION = "language-requirement-extraction-v1"
LOCATION_FIT_EVALUATOR_VERSION = "location-fit-evaluator-v1"
LANGUAGE_FIT_EVALUATOR_VERSION = "language-fit-evaluator-v1"
LOCATION_FIT_NORMALIZER_VERSION = "location-fit-normalizer-v1"
LANGUAGE_FIT_NORMALIZER_VERSION = "language-fit-normalizer-v1"

_FACTOR_IDS: tuple[FactorId, ...] = ("language_fit", "location_fit")
_POLICY_MODES = frozenset({"disabled", "ranking_only", "gate_required"})
_EVALUATION_STATUSES = frozenset({"pass", "fail", "unknown", "not_applicable"})
_LOCATION_NORMALIZATION_KEYS = frozenset(
    {
        "exact_city",
        "exact_region",
        "exact_country",
        "remote_unrestricted",
        "no_match",
        "unknown_value",
        "not_applicable_value",
    }
)
_LANGUAGE_NORMALIZATION_KEYS = frozenset(
    {"met", "unmet", "unknown_value", "not_applicable_value", "requirement_weights"}
)
_REQUIREMENT_TYPES = frozenset({"required", "preferred", "unspecified"})
_EXTRACTION_STATUSES = frozenset({"complete", "partial", "unknown"})
_LEVEL_ORDER = {"a1": 0, "a2": 1, "b1": 2, "b2": 3, "c1": 4, "c2": 5, "native": 6}
_WHITESPACE_RE = re.compile(r"\s+")
_LOCATION_TOKEN_RE = re.compile(r"[,;]")


class LanguageCapability(TypedDict):
    language: str
    level: LanguageLevel
    source: LanguageSource


class CandidateFitContext(TypedDict):
    preferred_locations: list[str]
    preferred_work_modes: list[str]
    language_inventory_status: Literal["complete", "unknown"]
    language_capabilities: list[LanguageCapability]
    diagnostic_codes: list[str]


class FactorEvaluation(TypedDict):
    factor_id: FactorId
    status: EvaluationStatus
    score: float | None
    confidence: float
    reason_code: str
    evidence: dict[str, Any]
    evaluator_version: str
    normalizer_version: str


class FactorPolicyResult(TypedDict):
    factor_id: FactorId
    policy_version: str
    mode: PolicyMode
    eligibility_decision: EligibilityDecision
    ranking_enabled: bool
    ranking_value: float | None
    diagnostic_code: str
    evaluation: FactorEvaluation


class EligibilityResult(TypedDict):
    fit_factor_results: dict[FactorId, FactorPolicyResult]
    eligibility_policy_fingerprint: str
    eligibility_decision: EligibilityDecision
    eligibility_reason_codes: list[str]


def _require_mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _require_exact_keys(mapping: dict[str, Any], expected: frozenset[str], path: str) -> None:
    actual = frozenset(mapping)
    unknown = sorted(actual - expected)
    missing = sorted(expected - actual)
    if unknown:
        raise ValueError(f"{path} contains unknown keys: {', '.join(unknown)}")
    if missing:
        raise ValueError(f"{path} is missing keys: {', '.join(missing)}")


def _bounded_number(value: Any, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{path} must be numeric")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise ValueError(f"{path} must be finite")
    if not 0.0 <= normalized <= 1.0:
        raise ValueError(f"{path} must be inside [0, 1]")
    return normalized


def validate_eligibility_policy(raw_policy: Any) -> dict[str, Any]:
    policy = _require_mapping(raw_policy, "eligibility_policy")
    _require_exact_keys(policy, frozenset({"policy_version", "factors"}), "eligibility_policy")
    if policy["policy_version"] != ELIGIBILITY_POLICY_VERSION:
        raise ValueError(
            f"eligibility_policy.policy_version must be {ELIGIBILITY_POLICY_VERSION}"
        )

    factors = _require_mapping(policy["factors"], "eligibility_policy.factors")
    if frozenset(factors) != frozenset(_FACTOR_IDS):
        raise ValueError("eligibility_policy.factors must contain exactly location_fit and language_fit")

    validated_factors: dict[str, Any] = {}
    for factor_id in _FACTOR_IDS:
        factor = _require_mapping(factors[factor_id], f"eligibility_policy.factors.{factor_id}")
        _require_exact_keys(
            factor,
            frozenset({"mode", "normalization"}),
            f"eligibility_policy.factors.{factor_id}",
        )
        mode = str(factor["mode"])
        if mode not in _POLICY_MODES:
            raise ValueError(f"eligibility_policy.factors.{factor_id}.mode is invalid")
        normalization = _require_mapping(
            factor["normalization"],
            f"eligibility_policy.factors.{factor_id}.normalization",
        )
        expected_keys = (
            _LOCATION_NORMALIZATION_KEYS
            if factor_id == "location_fit"
            else _LANGUAGE_NORMALIZATION_KEYS
        )
        _require_exact_keys(
            normalization,
            expected_keys,
            f"eligibility_policy.factors.{factor_id}.normalization",
        )
        validated_normalization: dict[str, Any] = {}
        for key, value in normalization.items():
            if key == "requirement_weights":
                weights = _require_mapping(
                    value,
                    "eligibility_policy.factors.language_fit.normalization.requirement_weights",
                )
                _require_exact_keys(
                    weights,
                    _REQUIREMENT_TYPES,
                    "eligibility_policy.factors.language_fit.normalization.requirement_weights",
                )
                validated_weights = {
                    weight_name: _bounded_number(weight_value, f"requirement_weights.{weight_name}")
                    for weight_name, weight_value in weights.items()
                }
                required_weight = validated_weights["required"]
                if required_weight <= 0.0 or required_weight < max(validated_weights.values()):
                    raise ValueError("required requirement weight must be positive and not below other weights")
                validated_normalization[key] = validated_weights
            else:
                validated_normalization[key] = _bounded_number(
                    value,
                    f"eligibility_policy.factors.{factor_id}.normalization.{key}",
                )
        if factor_id == "location_fit":
            ordered = (
                validated_normalization["exact_city"],
                validated_normalization["exact_region"],
                validated_normalization["exact_country"],
                validated_normalization["no_match"],
            )
            if not all(left >= right for left, right in zip(ordered, ordered[1:])):
                raise ValueError("location normalization ordering is invalid")
        validated_factors[factor_id] = {
            "mode": mode,
            "normalization": validated_normalization,
        }

    return {
        "policy_version": ELIGIBILITY_POLICY_VERSION,
        "factors": {
            "location_fit": validated_factors["location_fit"],
            "language_fit": validated_factors["language_fit"],
        },
    }


def fingerprint_eligibility_policy(raw_policy: Any) -> str:
    policy = validate_eligibility_policy(raw_policy)
    payload = json.dumps(
        policy,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _display_text(value: Any) -> str:
    return _WHITESPACE_RE.sub(" ", unicodedata.normalize("NFKC", str(value))).strip()


def _comparison_key(value: Any) -> str:
    return _display_text(value).casefold()


def normalize_display_text(value: Any) -> str:
    return _display_text(value)


def comparison_key(value: Any) -> str:
    return _comparison_key(value)

def _unique_display_values(values: list[Any], *, split_locations: bool = False) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for value in values:
        candidates = _LOCATION_TOKEN_RE.split(str(value)) if split_locations else [str(value)]
        for candidate in candidates:
            display = _display_text(candidate)
            key = _comparison_key(display)
            if not key:
                continue
            previous = normalized.get(key)
            if previous is None or display < previous:
                normalized[key] = display
    return normalized


def _candidate_level(entry: dict[str, Any]) -> tuple[LanguageLevel, LanguageSource]:
    if entry.get("native") is True:
        return "native", "native"
    explicit_level = _comparison_key(entry.get("level", ""))
    if explicit_level in _LEVEL_ORDER:
        return cast(LanguageLevel, explicit_level), "level"
    dimensions = [_comparison_key(entry.get(key, "")) for key in ("read", "write", "speak")]
    if all(level in _LEVEL_ORDER for level in dimensions):
        minimum = min(dimensions, key=_LEVEL_ORDER.__getitem__)
        return cast(LanguageLevel, minimum), "read_write_speak"
    return "unknown", "unknown"


def build_candidate_fit_context(
    profile: Any,
    *,
    valid_work_modes: list[str] | tuple[str, ...] | set[str] | frozenset[str],
) -> CandidateFitContext:
    profile_mapping = profile if isinstance(profile, dict) else {}
    preferences = profile_mapping.get("preferences")
    preference_mapping = preferences if isinstance(preferences, dict) else {}

    raw_locations = preference_mapping.get("locations")
    location_values = raw_locations if isinstance(raw_locations, list) else []
    raw_work_modes = preference_mapping.get("location_types")
    work_mode_values = raw_work_modes if isinstance(raw_work_modes, list) else []
    work_mode_keys = {_comparison_key(value) for value in valid_work_modes if _comparison_key(value)}
    preferred_locations_by_key = _unique_display_values(location_values, split_locations=True)
    preferred_locations = [
        preferred_locations_by_key[key]
        for key in sorted(preferred_locations_by_key)
        if key not in work_mode_keys
    ]
    preferred_work_modes_by_key = _unique_display_values(work_mode_values)
    preferred_work_modes = [preferred_work_modes_by_key[key] for key in sorted(preferred_work_modes_by_key)]

    diagnostic_codes: list[str] = []
    if "languages" not in profile_mapping:
        inventory_status: Literal["complete", "unknown"] = "unknown"
        language_entries: list[Any] = []
        diagnostic_codes.append("candidate_languages_absent")
    elif not isinstance(profile_mapping["languages"], list):
        inventory_status = "unknown"
        language_entries = []
        diagnostic_codes.append("candidate_languages_malformed")
    else:
        inventory_status = "complete"
        language_entries = profile_mapping["languages"]

    capabilities_by_key: dict[str, LanguageCapability] = {}
    for raw_entry in language_entries:
        if not isinstance(raw_entry, dict):
            diagnostic_codes.append("candidate_language_entry_malformed")
            continue
        language = _display_text(raw_entry.get("name", ""))
        language_key = _comparison_key(language)
        if not language_key:
            diagnostic_codes.append("candidate_language_name_missing")
            continue
        level, source = _candidate_level(raw_entry)
        capability: LanguageCapability = {
            "language": language,
            "level": level,
            "source": source,
        }
        previous = capabilities_by_key.get(language_key)
        previous_rank = _LEVEL_ORDER.get(previous["level"], -1) if previous else -1
        current_rank = _LEVEL_ORDER.get(level, -1)
        if previous is None or current_rank > previous_rank or (
            current_rank == previous_rank and language < previous["language"]
        ):
            capabilities_by_key[language_key] = capability

    return {
        "preferred_locations": preferred_locations,
        "preferred_work_modes": preferred_work_modes,
        "language_inventory_status": inventory_status,
        "language_capabilities": [capabilities_by_key[key] for key in sorted(capabilities_by_key)],
        "diagnostic_codes": sorted(set(diagnostic_codes)),
    }


def _factor_evaluation(
    *,
    factor_id: FactorId,
    status: EvaluationStatus,
    score: float | None,
    confidence: float,
    reason_code: str,
    evidence: dict[str, Any],
) -> FactorEvaluation:
    if status not in _EVALUATION_STATUSES:
        raise ValueError("invalid evaluation status")
    if score is not None:
        score = _bounded_number(score, "factor_evaluation.score")
    confidence = _bounded_number(confidence, "factor_evaluation.confidence")
    return {
        "factor_id": factor_id,
        "status": status,
        "score": score,
        "confidence": confidence,
        "reason_code": reason_code,
        "evidence": evidence,
        "evaluator_version": (
            LOCATION_FIT_EVALUATOR_VERSION
            if factor_id == "location_fit"
            else LANGUAGE_FIT_EVALUATOR_VERSION
        ),
        "normalizer_version": (
            LOCATION_FIT_NORMALIZER_VERSION
            if factor_id == "location_fit"
            else LANGUAGE_FIT_NORMALIZER_VERSION
        ),
    }


def evaluate_location_fit(
    actual_location: Any,
    candidate_context: CandidateFitContext,
    normalization: Any,
) -> FactorEvaluation:
    rules = _require_mapping(normalization, "location_fit.normalization")
    preferences = candidate_context.get("preferred_locations", [])
    if not preferences:
        return _factor_evaluation(
            factor_id="location_fit",
            status="not_applicable",
            score=None,
            confidence=1.0,
            reason_code="location_not_applicable",
            evidence={"preferred_locations": []},
        )
    if not isinstance(actual_location, dict):
        return _factor_evaluation(
            factor_id="location_fit",
            status="unknown",
            score=None,
            confidence=0.0,
            reason_code="location_unknown",
            evidence={"diagnostic": "actual_location_malformed"},
        )

    extraction_status = _comparison_key(actual_location.get("extraction_status", "unknown"))
    if extraction_status not in _EXTRACTION_STATUSES:
        extraction_status = "unknown"
    remote_scope = _comparison_key(actual_location.get("remote_scope", ""))
    if remote_scope == "unrestricted" and extraction_status == "complete":
        return _factor_evaluation(
            factor_id="location_fit",
            status="pass",
            score=_bounded_number(rules["remote_unrestricted"], "remote_unrestricted"),
            confidence=1.0,
            reason_code="location_remote_unrestricted",
            evidence={"match_type": "remote_unrestricted"},
        )

    preference_keys = {_comparison_key(value) for value in preferences}
    matches: list[tuple[float, str, str]] = []
    for field_name, score_key in (
        ("city", "exact_city"),
        ("region", "exact_region"),
        ("country", "exact_country"),
    ):
        display = _display_text(actual_location.get(field_name, ""))
        if display and _comparison_key(display) in preference_keys:
            matches.append(
                (_bounded_number(rules[score_key], score_key), field_name, display)
            )
    if matches:
        score, field_name, display = max(matches, key=lambda item: (item[0], item[1], item[2]))
        return _factor_evaluation(
            factor_id="location_fit",
            status="pass",
            score=score,
            confidence=1.0 if extraction_status == "complete" else 0.75,
            reason_code=f"location_exact_{field_name}",
            evidence={"match_type": f"exact_{field_name}", "matched_value": display},
        )
    if extraction_status == "complete":
        return _factor_evaluation(
            factor_id="location_fit",
            status="fail",
            score=_bounded_number(rules["no_match"], "no_match"),
            confidence=1.0,
            reason_code="location_no_match",
            evidence={"preferred_locations": list(preferences)},
        )
    return _factor_evaluation(
        factor_id="location_fit",
        status="unknown",
        score=None,
        confidence=0.0,
        reason_code="location_unknown",
        evidence={"extraction_status": extraction_status},
    )


def _language_truth(
    requirement: Any,
    candidate_context: CandidateFitContext,
) -> tuple[str, str, str]:
    if not isinstance(requirement, dict):
        return "unknown", "unspecified", ""
    requirement_type = _comparison_key(requirement.get("requirement_type", "unspecified"))
    if requirement_type not in _REQUIREMENT_TYPES:
        requirement_type = "unspecified"
    language = _display_text(requirement.get("language", ""))
    expected_level = _comparison_key(requirement.get("expected_level", "unspecified"))
    extraction_status = _comparison_key(requirement.get("extraction_status", "unknown"))
    if extraction_status != "complete" or not language:
        return "unknown", requirement_type, language
    if expected_level not in {*_LEVEL_ORDER, "unspecified"}:
        return "unknown", requirement_type, language

    capabilities = {
        _comparison_key(capability["language"]): capability
        for capability in candidate_context.get("language_capabilities", [])
    }
    capability = capabilities.get(_comparison_key(language))
    if capability is None:
        truth = (
            "unmet"
            if candidate_context.get("language_inventory_status") == "complete"
            else "unknown"
        )
        return truth, requirement_type, language
    if expected_level == "unspecified":
        return "met", requirement_type, language
    candidate_level = capability["level"]
    if candidate_level == "unknown":
        return "unknown", requirement_type, language
    truth = "met" if _LEVEL_ORDER[candidate_level] >= _LEVEL_ORDER[expected_level] else "unmet"
    return truth, requirement_type, language


def evaluate_language_fit(
    language_requirements: Any,
    candidate_context: CandidateFitContext,
    normalization: Any,
) -> FactorEvaluation:
    rules = _require_mapping(normalization, "language_fit.normalization")
    if not isinstance(language_requirements, list):
        return _factor_evaluation(
            factor_id="language_fit",
            status="unknown",
            score=None,
            confidence=0.0,
            reason_code="language_requirements_unknown",
            evidence={"diagnostic": "language_requirements_malformed"},
        )
    if not language_requirements:
        return _factor_evaluation(
            factor_id="language_fit",
            status="not_applicable",
            score=None,
            confidence=1.0,
            reason_code="language_not_applicable",
            evidence={"requirements": []},
        )

    weights = _require_mapping(rules["requirement_weights"], "requirement_weights")
    outcomes: list[dict[str, str | float]] = []
    weighted_score = 0.0
    total_weight = 0.0
    required_unmet = False
    required_unknown = False
    confirmed_count = 0
    for requirement in language_requirements:
        truth, requirement_type, language = _language_truth(requirement, candidate_context)
        weight = _bounded_number(weights[requirement_type], f"requirement_weights.{requirement_type}")
        value_key = "unknown_value" if truth == "unknown" else truth
        value = _bounded_number(rules[value_key], f"language_fit.normalization.{value_key}")
        weighted_score += weight * value
        total_weight += weight
        if truth != "unknown":
            confirmed_count += 1
        required_unmet = required_unmet or (
            requirement_type == "required" and truth == "unmet"
        )
        required_unknown = required_unknown or (
            requirement_type == "required" and truth == "unknown"
        )
        outcomes.append(
            {
                "language": language,
                "requirement_type": requirement_type,
                "truth": truth,
                "weight": weight,
                "value": value,
            }
        )

    if required_unmet:
        status: EvaluationStatus = "fail"
        reason_code = "language_required_unmet"
    elif required_unknown:
        status = "unknown"
        reason_code = "language_required_unknown"
    else:
        status = "pass"
        reason_code = "language_requirements_satisfied"
    score = weighted_score / total_weight if total_weight > 0.0 else None
    outcomes.sort(key=lambda item: (_comparison_key(item["language"]), str(item["requirement_type"])))
    return _factor_evaluation(
        factor_id="language_fit",
        status=status,
        score=score,
        confidence=confirmed_count / len(language_requirements),
        reason_code=reason_code,
        evidence={"requirements": outcomes},
    )


def project_factor_evaluation(
    evaluation: FactorEvaluation,
    factor_policy: Any,
    *,
    policy_version: str,
) -> FactorPolicyResult:
    policy = _require_mapping(factor_policy, "factor_policy")
    mode_raw = str(policy.get("mode", ""))
    if mode_raw not in _POLICY_MODES:
        raise ValueError("factor policy mode is invalid")
    mode = cast(PolicyMode, mode_raw)
    normalization = _require_mapping(policy.get("normalization"), "factor_policy.normalization")
    status = evaluation["status"]
    decision: EligibilityDecision = (
        "reject" if mode == "gate_required" and status == "fail" else "retain"
    )
    ranking_enabled = mode == "ranking_only"
    ranking_value: float | None = None
    if ranking_enabled:
        if status in {"pass", "fail"}:
            ranking_value = evaluation["score"]
        elif status == "unknown":
            ranking_value = _bounded_number(normalization["unknown_value"], "unknown_value")
        else:
            ranking_value = _bounded_number(
                normalization["not_applicable_value"],
                "not_applicable_value",
            )
    return {
        "factor_id": evaluation["factor_id"],
        "policy_version": policy_version,
        "mode": mode,
        "eligibility_decision": decision,
        "ranking_enabled": ranking_enabled,
        "ranking_value": ranking_value,
        "diagnostic_code": evaluation["reason_code"],
        "evaluation": cast(FactorEvaluation, dict(evaluation)),
    }


def evaluate_fit_factors(
    *,
    actual_location: Any,
    language_requirements: Any,
    candidate_context: CandidateFitContext,
    eligibility_policy: Any,
) -> EligibilityResult:
    """@capability cv_system.location-language-eligibility"""
    policy = validate_eligibility_policy(eligibility_policy)
    factors = cast(dict[str, dict[str, Any]], policy["factors"])
    evaluations: dict[FactorId, FactorEvaluation] = {
        "language_fit": evaluate_language_fit(
            language_requirements,
            candidate_context,
            factors["language_fit"]["normalization"],
        ),
        "location_fit": evaluate_location_fit(
            actual_location,
            candidate_context,
            factors["location_fit"]["normalization"],
        ),
    }
    results: dict[FactorId, FactorPolicyResult] = {
        factor_id: project_factor_evaluation(
            evaluations[factor_id],
            factors[factor_id],
            policy_version=cast(str, policy["policy_version"]),
        )
        for factor_id in _FACTOR_IDS
    }
    decision: EligibilityDecision = (
        "reject"
        if any(result["eligibility_decision"] == "reject" for result in results.values())
        else "retain"
    )
    reason_codes = sorted(
        {
            result["diagnostic_code"]
            for result in results.values()
            if result["evaluation"]["status"] in {"fail", "unknown"}
        }
    )
    return {
        "fit_factor_results": results,
        "eligibility_policy_fingerprint": fingerprint_eligibility_policy(policy),
        "eligibility_decision": decision,
        "eligibility_reason_codes": reason_codes,
    }