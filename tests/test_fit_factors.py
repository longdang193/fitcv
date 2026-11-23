"""
@meta
type: test
scope: unit
domain: eligibility
covers:
  - eligibility policy validation and fingerprinting
  - candidate fit-context adaptation
  - symmetric location and language factor evaluation
  - shared policy projection
excludes:
  - pipeline orchestration and persistence
tags:
  - fast
  - ci-safe
"""

from __future__ import annotations

import copy
import json
import math
from collections.abc import Callable
from typing import Any

import pytest

from fitcv.fit_factors import (
    EvaluationStatus,
    FactorEvaluation,
    FactorId,
    build_candidate_fit_context,
    evaluate_fit_factors,
    evaluate_language_fit,
    evaluate_location_fit,
    fingerprint_eligibility_policy,
    project_factor_evaluation,
    validate_eligibility_policy,
)


ELIGIBILITY_POLICY: dict[str, Any] = {
    "policy_version": "eligibility-v1",
    "factors": {
        "location_fit": {
            "mode": "ranking_only",
            "normalization": {
                "exact_city": 1.0,
                "exact_region": 0.8,
                "exact_country": 0.6,
                "remote_unrestricted": 1.0,
                "no_match": 0.0,
                "unknown_value": 0.5,
                "not_applicable_value": 0.5,
            },
        },
        "language_fit": {
            "mode": "ranking_only",
            "normalization": {
                "met": 1.0,
                "unmet": 0.0,
                "unknown_value": 0.5,
                "not_applicable_value": 0.5,
                "requirement_weights": {
                    "required": 1.0,
                    "preferred": 0.5,
                    "unspecified": 0.5,
                },
            },
        },
    },
}


def test_validate_eligibility_policy_accepts_exact_phase_one_shape() -> None:
    assert validate_eligibility_policy(ELIGIBILITY_POLICY) == ELIGIBILITY_POLICY


@pytest.mark.parametrize(  # type: ignore[misc]
    ("mutator", "message"),
    [
        (lambda policy: policy.update(extra=True), "unknown"),
        (lambda policy: policy["factors"].pop("language_fit"), "exactly"),
        (
            lambda policy: policy["factors"]["location_fit"].update(mode="sometimes"),
            "mode",
        ),
        (
            lambda policy: policy["factors"]["location_fit"]["normalization"].update(
                exact_city=math.nan
            ),
            "finite",
        ),
        (
            lambda policy: policy["factors"]["location_fit"]["normalization"].update(
                exact_city=0.2,
                exact_region=0.8,
            ),
            "ordering",
        ),
        (
            lambda policy: policy["factors"]["language_fit"]["normalization"][
                "requirement_weights"
            ].update(required=0.4, preferred=0.5),
            "required",
        ),
    ],
)
def test_validate_eligibility_policy_rejects_invalid_contract(
    mutator: Callable[[dict[str, Any]], object],
    message: str,
) -> None:
    policy = copy.deepcopy(ELIGIBILITY_POLICY)
    mutator(policy)

    with pytest.raises(ValueError, match=message):
        validate_eligibility_policy(policy)


def test_policy_fingerprint_is_order_invariant_and_golden() -> None:
    reordered = {
        "factors": {
            "language_fit": copy.deepcopy(ELIGIBILITY_POLICY["factors"]["language_fit"]),
            "location_fit": copy.deepcopy(ELIGIBILITY_POLICY["factors"]["location_fit"]),
        },
        "policy_version": "eligibility-v1",
    }

    expected = "3f26909a8b2e0eb492c3b9026b1326b5424026a0a65cf561a59b073ff5a7d953"
    assert fingerprint_eligibility_policy(ELIGIBILITY_POLICY) == expected
    assert fingerprint_eligibility_policy(reordered) == expected


def test_candidate_context_is_deterministic_and_separates_work_modes() -> None:
    profile: dict[str, Any] = {
        "preferences": {
            "locations": [" München ; Berlin ", "Remote", "Berlin"],
            "location_types": ["Hybrid", "remote", "Hybrid"],
        },
        "languages": [
            {"name": "English", "read": "C2", "write": "B2", "speak": "C1"},
            {"name": "German", "level": "B2"},
            {"name": "Vietnamese", "native": True},
            {"name": "French", "read": "B1", "write": "A2"},
            {"name": "German", "level": "C1"},
        ],
    }

    context = build_candidate_fit_context(
        profile,
        valid_work_modes=["remote", "hybrid", "onsite"],
    )

    assert context == {
        "preferred_locations": ["Berlin", "München"],
        "preferred_work_modes": ["Hybrid", "remote"],
        "language_inventory_status": "complete",
        "language_capabilities": [
            {"language": "English", "level": "b2", "source": "read_write_speak"},
            {"language": "French", "level": "unknown", "source": "unknown"},
            {"language": "German", "level": "c1", "source": "level"},
            {"language": "Vietnamese", "level": "native", "source": "native"},
        ],
        "diagnostic_codes": [],
    }
    assert json.dumps(context, ensure_ascii=False, sort_keys=True) == json.dumps(
        build_candidate_fit_context(
            {
                **profile,
                "preferences": {
                    "locations": list(reversed(profile["preferences"]["locations"])),
                    "location_types": list(
                        reversed(profile["preferences"]["location_types"])
                    ),
                },
                "languages": list(reversed(profile["languages"])),
            },
            valid_work_modes=["onsite", "hybrid", "remote"],
        ),
        ensure_ascii=False,
        sort_keys=True,
    )


@pytest.mark.parametrize(  # type: ignore[misc]
    ("profile", "expected_status", "expected_diagnostic"),
    [
        ({}, "unknown", "candidate_languages_absent"),
        ({"languages": None}, "unknown", "candidate_languages_malformed"),
        ({"languages": []}, "complete", None),
    ],
)
def test_candidate_language_inventory_presence_contract(
    profile: dict[str, object],
    expected_status: str,
    expected_diagnostic: str | None,
) -> None:
    context = build_candidate_fit_context(profile, valid_work_modes=[])
    assert context["language_inventory_status"] == expected_status
    if expected_diagnostic is None:
        assert context["diagnostic_codes"] == []
    else:
        assert expected_diagnostic in context["diagnostic_codes"]


@pytest.mark.parametrize(  # type: ignore[misc]
    ("actual_location", "expected_status", "expected_score", "expected_reason"),
    [
        ({"extraction_status": "unknown"}, "unknown", None, "location_unknown"),
        (
            {"remote_scope": "unrestricted", "extraction_status": "complete"},
            "pass",
            1.0,
            "location_remote_unrestricted",
        ),
        (
            {"city": "Berlin", "country": "Germany", "extraction_status": "complete"},
            "pass",
            1.0,
            "location_exact_city",
        ),
        (
            {"city": "Hamburg", "country": "Germany", "extraction_status": "complete"},
            "fail",
            0.0,
            "location_no_match",
        ),
    ],
)
def test_location_evaluator_returns_total_absolute_results(
    actual_location: dict[str, object],
    expected_status: str,
    expected_score: float | None,
    expected_reason: str,
) -> None:
    context = build_candidate_fit_context(
        {"preferences": {"locations": ["Berlin"]}, "languages": []},
        valid_work_modes=["remote", "hybrid", "onsite"],
    )
    result = evaluate_location_fit(
        actual_location,
        context,
        ELIGIBILITY_POLICY["factors"]["location_fit"]["normalization"],
    )
    assert result["status"] == expected_status
    assert result["score"] == expected_score
    assert result["reason_code"] == expected_reason


def test_location_evaluator_returns_not_applicable_without_preferences() -> None:
    context = build_candidate_fit_context(
        {"preferences": {"locations": []}, "languages": []},
        valid_work_modes=["remote"],
    )
    result = evaluate_location_fit(
        {"city": "Berlin", "extraction_status": "complete"},
        context,
        ELIGIBILITY_POLICY["factors"]["location_fit"]["normalization"],
    )
    assert result["status"] == "not_applicable"
    assert result["score"] is None


def test_language_evaluator_fails_only_confirmed_required_unmet() -> None:
    context = build_candidate_fit_context(
        {"languages": [{"name": "English", "level": "B2"}]},
        valid_work_modes=[],
    )
    requirements = [
        {
            "language": "English",
            "expected_level": "C1",
            "requirement_type": "required",
            "extraction_status": "complete",
        },
        {
            "language": "German",
            "expected_level": "B2",
            "requirement_type": "preferred",
            "extraction_status": "complete",
        },
    ]

    result = evaluate_language_fit(
        requirements,
        context,
        ELIGIBILITY_POLICY["factors"]["language_fit"]["normalization"],
    )

    assert result["status"] == "fail"
    assert result["score"] == pytest.approx(0.0)
    assert result["reason_code"] == "language_required_unmet"


def test_language_evaluator_keeps_partial_required_requirement_unknown() -> None:
    context = build_candidate_fit_context({"languages": []}, valid_work_modes=[])
    result = evaluate_language_fit(
        [
            {
                "language": "German",
                "expected_level": "B2",
                "requirement_type": "required",
                "extraction_status": "partial",
            }
        ],
        context,
        ELIGIBILITY_POLICY["factors"]["language_fit"]["normalization"],
    )
    assert result["status"] == "unknown"
    assert result["score"] == pytest.approx(0.5)


def test_language_evaluator_uses_weighted_score_without_preferred_gate_failure() -> None:
    context = build_candidate_fit_context(
        {"languages": [{"name": "English", "level": "C1"}]},
        valid_work_modes=[],
    )
    result = evaluate_language_fit(
        [
            {
                "language": "English",
                "expected_level": "B2",
                "requirement_type": "required",
                "extraction_status": "complete",
            },
            {
                "language": "German",
                "expected_level": "B2",
                "requirement_type": "preferred",
                "extraction_status": "complete",
            },
        ],
        context,
        ELIGIBILITY_POLICY["factors"]["language_fit"]["normalization"],
    )
    assert result["status"] == "pass"
    assert result["score"] == pytest.approx(2.0 / 3.0)


@pytest.mark.parametrize("factor_id", ["location_fit", "language_fit"])  # type: ignore[misc]
@pytest.mark.parametrize("status", ["pass", "fail", "unknown", "not_applicable"])  # type: ignore[misc]
@pytest.mark.parametrize("mode", ["disabled", "ranking_only", "gate_required"])  # type: ignore[misc]
def test_projection_table_is_shared_and_exhaustive(
    factor_id: FactorId,
    status: EvaluationStatus,
    mode: str,
) -> None:
    evaluation: FactorEvaluation = {
        "factor_id": factor_id,
        "status": status,
        "score": 0.8 if status in {"pass", "fail"} else None,
        "confidence": 1.0,
        "reason_code": f"{factor_id}_{status}",
        "evidence": {},
        "evaluator_version": "test-v1",
        "normalizer_version": "test-v1",
    }
    result = project_factor_evaluation(
        evaluation,
        {
            "mode": mode,
            "normalization": {"unknown_value": 0.4, "not_applicable_value": 0.6},
        },
        policy_version="eligibility-v1",
    )

    assert result["eligibility_decision"] == (
        "reject" if mode == "gate_required" and status == "fail" else "retain"
    )
    assert result["ranking_enabled"] is (mode == "ranking_only")
    expected_ranking_value = None
    if mode == "ranking_only":
        expected_ranking_value = {
            "pass": 0.8,
            "fail": 0.8,
            "unknown": 0.4,
            "not_applicable": 0.6,
        }[status]
    assert result["ranking_value"] == expected_ranking_value


def test_evaluate_fit_factors_aggregates_one_symmetric_artifact() -> None:
    """@proves cv_system.location-language-eligibility"""
    policy = copy.deepcopy(ELIGIBILITY_POLICY)
    policy["factors"]["language_fit"]["mode"] = "gate_required"
    context = build_candidate_fit_context(
        {
            "preferences": {"locations": ["Berlin"]},
            "languages": [{"name": "English", "level": "B2"}],
        },
        valid_work_modes=["remote", "hybrid", "onsite"],
    )

    result = evaluate_fit_factors(
        actual_location={
            "city": "Berlin",
            "country": "Germany",
            "extraction_status": "complete",
        },
        language_requirements=[
            {
                "language": "English",
                "expected_level": "C1",
                "requirement_type": "required",
                "extraction_status": "complete",
            }
        ],
        candidate_context=context,
        eligibility_policy=policy,
    )

    assert list(result["fit_factor_results"]) == ["language_fit", "location_fit"]
    assert result["eligibility_decision"] == "reject"
    assert result["eligibility_reason_codes"] == ["language_required_unmet"]
    assert result["eligibility_policy_fingerprint"] == fingerprint_eligibility_policy(policy)