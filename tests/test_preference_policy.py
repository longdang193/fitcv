"""
@meta
type: test
scope: unit
domain: preference_policy
covers:
  - cv_system.preference-learning
  - cv_system.ranking-policy-lifecycle
excludes:
  - sqlite persistence
tags:
  - fast
  - ci-safe
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest
import yaml

from fitcv.decision_feedback import validate_decision_learning_policy
from fitcv.preference_policy import (
    PromotionDecision,
    PreferenceRuntimeContract,
    build_policy_snapshot_identity,
    build_training_run_identity,
    evaluate_promotion_gate,
    max_coordinate_delta,
    preference_vector_fingerprint,
    project_personalized_score,
    resolved_preference_policy_from_snapshot,
    resolved_preference_policy_from_dict,
    resolved_preference_policy_to_dict,
    resolve_run_preference_policy,
    resolve_zero_residual_policy,
)


def _runtime() -> PreferenceRuntimeContract:
    return PreferenceRuntimeContract.build(
        domain_id="ranking_v1",
        baseline_policy_fingerprint="baseline",
        ranking_contract_fingerprint="ranking",
        embedding_model="model",
        embedding_dimension=2,
        embedding_contract_fingerprint="embedding",
        learned_alpha=0.05,
        preference_vector_norm_bound=1.0,
    )


def test_content_addressed_identities_ignore_envelope_fields() -> None:
    payload = {"domain_id": "ranking_v1", "preference_vector": [0.1, -0.1]}
    first_fingerprint, first_id = build_policy_snapshot_identity(
        {**payload, "policy_snapshot_id": "ignored", "status": "candidate", "created_at": "first"}
    )
    second_fingerprint, second_id = build_policy_snapshot_identity(
        {**payload, "policy_snapshot_id": "other", "status": "active", "created_at": "second"}
    )

    assert first_fingerprint == second_fingerprint
    assert first_id == second_id == f"rps_{first_fingerprint}"
    assert build_training_run_identity({"result": payload, "created_at": "first"}) == (
        build_training_run_identity({"result": payload, "created_at": "second"})
    )


def test_projection_uses_raw_score_for_order_and_clips_display_only() -> None:
    projection = project_personalized_score(
        runtime_contract=_runtime(),
        baseline_fit=0.99,
        preference_vector=(1.0, 0.0),
        normalized_embedding=(1.0, 0.0),
    )

    assert projection.preference_residual == pytest.approx(0.05)
    assert projection.personalized_rank_score == pytest.approx(1.04)
    assert projection.personalized_display_score == 1.0
    assert projection.score_was_clipped is True


def test_zero_residual_has_same_shape() -> None:
    resolved = resolve_zero_residual_policy(_runtime(), status="zero_residual_no_active")
    projection = project_personalized_score(
        runtime_contract=resolved.runtime_contract,
        baseline_fit=0.4,
        preference_vector=resolved.preference_vector,
        normalized_embedding=(0.0, 1.0),
    )

    assert resolved.policy_snapshot_id is None
    assert resolved.preference_vector == (0.0, 0.0)
    assert projection.personalized_rank_score == 0.4


def test_active_snapshot_resolution_round_trips() -> None:
    runtime = _runtime()
    vector = (0.2, -0.2)
    snapshot = {
        "status": "active",
        "runtime_contract_fingerprint": runtime.runtime_contract_fingerprint,
        "policy_snapshot_id": "snapshot",
        "preference_vector_json": list(vector),
        "preference_vector_fingerprint": preference_vector_fingerprint(vector),
        "payload_fingerprint": "payload",
    }

    resolved = resolved_preference_policy_from_snapshot(runtime, snapshot)

    assert resolved_preference_policy_from_dict(
        resolved_preference_policy_to_dict(resolved)
    ) == resolved


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_projection_rejects_nonfinite_values(value: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        project_personalized_score(
            runtime_contract=_runtime(),
            baseline_fit=value,
            preference_vector=(0.0, 0.0),
            normalized_embedding=(1.0, 0.0),
        )


def test_activation_policy_is_exact_and_fingerprinted() -> None:
    policy = yaml.safe_load(
        Path("config/policy/decision_learning.yaml").read_text(encoding="utf-8")
    )["decision_learning_policy"]
    validated, _ = validate_decision_learning_policy(policy)

    assert validated["inverse_optimization"]["activation"] == {
        "activation_version": "ranking-policy-lifecycle-v1",
        "minimum_fold_vector_stability": 0.0,
    }

    policy["inverse_optimization"]["activation"]["unknown"] = True
    with pytest.raises(ValueError, match="activation contains unknown keys"):
        validate_decision_learning_policy(policy)


def _metrics(*, agreement: float, margin: float, regret: float, clipping: float) -> dict:
    return {
        "pair_agreement_rate": agreement,
        "margin_satisfaction_rate": margin,
        "weighted_regret": regret,
        "clipping_frequency": clipping,
    }


def test_promotion_gate_is_uniform_for_baseline_and_parent() -> None:
    candidate = _metrics(agreement=0.8, margin=0.7, regret=0.1, clipping=0.0)
    baseline = _metrics(agreement=0.7, margin=0.7, regret=0.2, clipping=0.0)
    parent = _metrics(agreement=0.8, margin=0.6, regret=0.1, clipping=0.0)

    decision = evaluate_promotion_gate(
        candidate_metrics=candidate,
        comparator_metrics=(baseline, parent),
        fold_stabilities=(0.4, 0.7),
        tolerance=1.0e-6,
        minimum_fold_vector_stability=0.0,
    )

    assert decision == PromotionDecision(passed=True, reason_code="passed")


def test_promotion_gate_rejects_regression_missing_metric_and_clipping() -> None:
    baseline = _metrics(agreement=0.7, margin=0.7, regret=0.2, clipping=0.0)
    for candidate, reason in (
        (_metrics(agreement=0.8, margin=0.7, regret=0.3, clipping=0.0), "metric_regression"),
        (_metrics(agreement=0.8, margin=0.7, regret=0.1, clipping=0.1), "metric_regression"),
        ({"pair_agreement_rate": 0.8}, "missing_metric"),
    ):
        assert evaluate_promotion_gate(
            candidate_metrics=candidate,
            comparator_metrics=(baseline,),
            fold_stabilities=(0.4,),
            tolerance=1.0e-6,
            minimum_fold_vector_stability=0.0,
        ).reason_code == reason


def test_max_coordinate_delta_validates_vectors() -> None:
    assert max_coordinate_delta((0.1, -0.2), (0.1, -0.1)) == pytest.approx(0.1)
    with pytest.raises(ValueError, match="dimension"):
        max_coordinate_delta((0.1,), (0.1, 0.2))
    with pytest.raises(ValueError, match="nonempty"):
        max_coordinate_delta((), ())


def test_existing_resolved_policy_replay_never_calls_resolver() -> None:
    existing = resolved_preference_policy_to_dict(
        resolve_zero_residual_policy(_runtime(), status="zero_residual_no_active")
    )

    resolved = resolve_run_preference_policy(
        ranking_rows=[{"normalized_embedding": [1.0, 0.0]}],
        config={},
        existing_payload=existing,
        resolver=lambda runtime: (_ for _ in ()).throw(AssertionError("resolver called")),
    )

    assert resolved_preference_policy_to_dict(resolved) == existing
