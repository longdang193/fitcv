"""@meta
name: optimization_service
type: module
domain: inverse_optimization
ownership: feature
responsibility:
  - Own shared store-backed ranking-policy candidate orchestration.
  - Preserve CLI and HTTP candidate semantics through one function boundary.
inputs:
  - Typed inverse-optimization request, canonical config, store, and compare tokens.
outputs:
  - Typed candidate-operation result payload and immutable lifecycle rows.
capabilities:
  - cv_system.preference-learning
lifecycle:
  - status: active
"""

from __future__ import annotations

import dataclasses
import json
from typing import Any, cast

from fitcv.config import load_config
from fitcv.decision_feedback import optimizer_policy_fingerprint, validate_decision_learning_policy
from fitcv.embeddings import build_embedding_contract_fingerprint
from fitcv.inverse_optimization import (
    CompatibleParentReference,
    InverseOptimizationRequest,
    evaluate_preference_residual,
    solve_preference_residual,
)
from fitcv.preference_policy import (
    PreferenceRuntimeContract,
    build_policy_snapshot_identity,
    build_training_run_identity,
    evaluate_promotion_gate,
    max_coordinate_delta,
    preference_vector_fingerprint,
)
from fitcv.shortlist_runtime import build_contract_fingerprint
from fitcv_cp.store import ControlPlaneStore

def _request_evidence_head(request: InverseOptimizationRequest) -> dict[str, Any]:
    episodes = []
    for item in sorted(request.episodes, key=lambda value: value.episode.episode_id):
        episode = item.episode
        episodes.append(
            {
                "episode_id": episode.episode_id,
                "domain_id": episode.domain_id,
                "preference_context_fingerprint": episode.preference_context_fingerprint,
                "qualification_context_fingerprint": episode.qualification_context_fingerprint,
                "ranking_contract_fingerprint": episode.ranking_contract_fingerprint,
                "embedding_contract_fingerprint": episode.embedding_contract_fingerprint,
                "baseline_policy_fingerprint": episode.baseline_policy_fingerprint,
                "embedding_model": episode.embedding_model,
                "embedding_dimension": episode.embedding_dimension,
                "rating_scale_version": episode.rating_scale_version,
                "candidate_set_fingerprint": episode.candidate_set_fingerprint,
                "source_stage_artifact_fingerprint": episode.source_stage_artifact_fingerprint,
                "alternatives": [
                    {
                        "alternative_id": alternative.alternative_id,
                        "displayed_rank": alternative.displayed_rank,
                        "baseline_fit": alternative.baseline_fit,
                        "baseline_fit_label": alternative.baseline_fit_label,
                        "normalized_embedding": json.loads(alternative.normalized_embedding_json),
                        "embedding_vector_fingerprint": alternative.embedding_vector_fingerprint,
                        "shortlist_origin": alternative.shortlist_origin,
                    }
                    for alternative in sorted(
                        item.alternatives,
                        key=lambda value: (value.displayed_rank, value.alternative_id),
                    )
                ],
                "events": [
                    {
                        "event_sequence": event.event_sequence,
                        "event_id": event.event_id,
                        "episode_id": event.episode_id,
                        "alternative_id": event.alternative_id,
                        "event_type": event.event_type.value,
                        "rating": int(event.rating) if event.rating is not None else None,
                        "rating_scale_version": event.rating_scale_version,
                    }
                    for event in sorted(
                        item.events,
                        key=lambda value: (value.event_sequence or 0, value.event_id),
                    )
                ],
            }
        )
    payload = {
        "schema_version": "decision_evidence_head_v1",
        "domain_id": request.domain_id,
        "event_watermark": request.event_watermark,
        "episodes": episodes,
    }
    return {**payload, "evidence_head_fingerprint": build_contract_fingerprint(payload)}


def _metric_payload(value: Any) -> dict[str, Any] | None:
    return dataclasses.asdict(value) if value is not None else None


def current_activation_provenance(
    snapshot: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, str]:
    policy = config["decision_learning_policy"]
    optimizer = policy["inverse_optimization"]
    embedding_contract = build_embedding_contract_fingerprint(config)
    embedding_payload = embedding_contract["payload"]
    runtime = PreferenceRuntimeContract.build(
        domain_id=str(snapshot["domain_id"]),
        baseline_policy_fingerprint=str(build_contract_fingerprint(config["ranking_policy"])),
        ranking_contract_fingerprint=str(
            config["ranking_contract"]["ranking_contract_fingerprint"]
        ),
        embedding_model=str(embedding_payload["embedding_model"]),
        embedding_dimension=int(embedding_payload["embedding_dimension"]),
        embedding_contract_fingerprint=str(embedding_contract["fingerprint"]),
        learned_alpha=float(optimizer["learned_alpha"]),
        preference_vector_norm_bound=float(optimizer["preference_vector_norm_bound"]),
    )
    return {
        "current_runtime_contract_fingerprint": runtime.runtime_contract_fingerprint,
        "current_compiler_policy_fingerprint": str(
            build_contract_fingerprint(policy["preference_compiler"])
        ),
        "current_decision_learning_policy_fingerprint": str(
            config["decision_learning_policy_fingerprint"]
        ),
        "current_optimizer_policy_fingerprint": optimizer_policy_fingerprint(policy),
        "current_activation_policy_fingerprint": str(
            build_contract_fingerprint(optimizer["activation"])
        ),
    }


def create_ranking_policy_candidate(
    request: InverseOptimizationRequest,
    *,
    store: ControlPlaneStore,
    config: dict[str, Any],
    expected_evidence_head_fingerprint: str | None = None,
    expected_parent_ref: str | None = None,
) -> dict[str, Any]:
    expected_head = _request_evidence_head(request)
    current_head = store.get_decision_evidence_head(request.domain_id)
    expected_head_fingerprint = (
        expected_evidence_head_fingerprint
        or str(expected_head["evidence_head_fingerprint"])
    )
    if expected_head_fingerprint != current_head["evidence_head_fingerprint"]:
        return {
            "status": "stale" if expected_evidence_head_fingerprint is not None else "invalid_input",
            "error_code": "stale_evidence",
        }
    policy, decision_fingerprint = validate_decision_learning_policy(
        config["decision_learning_policy"]
    )
    first = request.episodes[0].episode
    optimizer = policy["inverse_optimization"]
    runtime = PreferenceRuntimeContract.build(
        domain_id=request.domain_id,
        baseline_policy_fingerprint=first.baseline_policy_fingerprint,
        ranking_contract_fingerprint=first.ranking_contract_fingerprint,
        embedding_model=first.embedding_model,
        embedding_dimension=first.embedding_dimension,
        embedding_contract_fingerprint=first.embedding_contract_fingerprint,
        learned_alpha=optimizer["learned_alpha"],
        preference_vector_norm_bound=optimizer["preference_vector_norm_bound"],
    )
    active = store.resolve_active_ranking_policy(
        request.domain_id, runtime.runtime_contract_fingerprint
    )
    parent = None
    parent_vector = tuple(0.0 for _ in range(first.embedding_dimension))
    parent_kind = "zero_residual"
    parent_ref = f"zero_residual:{first.baseline_policy_fingerprint}"
    if active is not None:
        parent_vector = tuple(float(value) for value in active["preference_vector_json"])
        parent_kind = "learned"
        parent_ref = f"learned:{active['policy_snapshot_id']}"
        parent = CompatibleParentReference(
            parent_kind=parent_kind,
            domain_id=request.domain_id,
            parent_ref=parent_ref,
            preference_vector=parent_vector,
            baseline_policy_fingerprint=first.baseline_policy_fingerprint,
            ranking_contract_fingerprint=first.ranking_contract_fingerprint,
            embedding_contract_fingerprint=first.embedding_contract_fingerprint,
            embedding_dimension=first.embedding_dimension,
            learned_alpha=optimizer["learned_alpha"],
        )
    if expected_parent_ref is not None and expected_parent_ref != parent_ref:
        return {"status": "stale", "error_code": "candidate_parent_changed"}
    solved = solve_preference_residual(request, policy)
    evaluated = evaluate_preference_residual(request, solved, policy, parent)
    status = solved.status
    promotion = {"passed": False, "reason_code": solved.status}
    no_op_delta = None
    candidate_vector = solved.candidate_preference_vector
    if solved.status == "optimal" and evaluated.status == "evaluated" and candidate_vector is not None:
        aggregate = evaluated.aggregate_metrics
        candidate_metrics = _metric_payload(aggregate.candidate if aggregate else None)
        comparators = [_metric_payload(aggregate.baseline if aggregate else None)]
        if evaluated.parent_comparison_status == "compatible":
            comparators.append(_metric_payload(aggregate.parent if aggregate else None))
        fold_stabilities = tuple(
            float(fold.vector_stability)
            for fold in evaluated.fold_results
            if fold.status == "evaluated" and fold.vector_stability is not None
        )
        decision = evaluate_promotion_gate(
            candidate_metrics=candidate_metrics or {},
            comparator_metrics=tuple(value or {} for value in comparators),
            fold_stabilities=fold_stabilities,
            tolerance=optimizer["numeric_tolerances"]["numeric_equivalence_absolute"],
            minimum_fold_vector_stability=optimizer["activation"]["minimum_fold_vector_stability"],
        )
        promotion = dataclasses.asdict(decision)
        if decision.passed:
            no_op_delta = max_coordinate_delta(candidate_vector, parent_vector)
            status = (
                "no_op"
                if no_op_delta <= optimizer["numeric_tolerances"]["numeric_equivalence_absolute"]
                else "candidate_created"
            )
        else:
            status = "evaluation_rejected"
    elif solved.status == "insufficient_evidence" or evaluated.status == "insufficient_evidence":
        status = "insufficient_evidence"
    elif solved.status == "invalid_input" or evaluated.status == "invalid_input":
        status = "invalid_input"
    result_payload = {
        "status": status,
        "solver_result": dataclasses.asdict(solved),
        "evaluation_result": dataclasses.asdict(evaluated),
        "promotion_gate": promotion,
        "no_op_max_coordinate_delta": no_op_delta,
        "evidence_head_fingerprint": expected_head["evidence_head_fingerprint"],
        "parent_policy_ref": parent_ref,
    }
    activation_fingerprint = build_contract_fingerprint(optimizer["activation"])
    training_row: dict[str, Any] = {
        "schema_version": "inverse_training_run_v1",
        "domain_id": request.domain_id,
        "status": status,
        "cohort_fingerprint": solved.cohort_fingerprint or "unavailable",
        "event_watermark": request.event_watermark,
        "edge_set_fingerprint": solved.edge_set_fingerprint or "unavailable",
        "rating_scale_version": first.rating_scale_version,
        "compiler_version": policy["preference_compiler"]["compiler_version"],
        "compiler_policy_fingerprint": build_contract_fingerprint(policy["preference_compiler"]),
        "decision_learning_policy_fingerprint": decision_fingerprint,
        "optimizer_policy_fingerprint": optimizer_policy_fingerprint(policy),
        "activation_policy_fingerprint": activation_fingerprint,
        "baseline_policy_fingerprint": first.baseline_policy_fingerprint,
        "ranking_contract_fingerprint": first.ranking_contract_fingerprint,
        "embedding_model": first.embedding_model,
        "embedding_contract_fingerprint": first.embedding_contract_fingerprint,
        "embedding_dimension": first.embedding_dimension,
        "learned_alpha": optimizer["learned_alpha"],
        "parent_policy_kind": parent_kind,
        "parent_policy_ref": parent_ref,
        "problem_fingerprint": solved.problem_fingerprint,
        "evaluation_fingerprint": evaluated.evaluation_fingerprint,
        "result_json": result_payload,
    }
    training_row["training_run_id"] = build_training_run_identity(training_row)
    snapshot_row = None
    if status == "candidate_created" and candidate_vector is not None:
        snapshot_row = {
            "schema_version": "ranking_policy_snapshot_v1",
            "domain_id": request.domain_id,
            "status": "candidate",
            "runtime_contract_fingerprint": runtime.runtime_contract_fingerprint,
            "baseline_policy_fingerprint": first.baseline_policy_fingerprint,
            "ranking_contract_fingerprint": first.ranking_contract_fingerprint,
            "embedding_model": first.embedding_model,
            "embedding_contract_fingerprint": first.embedding_contract_fingerprint,
            "embedding_dimension": first.embedding_dimension,
            "learned_alpha": optimizer["learned_alpha"],
            "preference_vector_norm_bound": optimizer["preference_vector_norm_bound"],
            "parent_policy_kind": parent_kind,
            "parent_policy_ref": parent_ref,
            "preference_vector_json": list(candidate_vector),
            "preference_vector_fingerprint": preference_vector_fingerprint(candidate_vector),
            "training_run_id": training_row["training_run_id"],
            "event_watermark": request.event_watermark,
            "cohort_fingerprint": solved.cohort_fingerprint,
            "edge_set_fingerprint": solved.edge_set_fingerprint,
            "rating_scale_version": first.rating_scale_version,
            "compiler_version": policy["preference_compiler"]["compiler_version"],
            "compiler_policy_fingerprint": training_row["compiler_policy_fingerprint"],
            "decision_learning_policy_fingerprint": decision_fingerprint,
            "optimizer_policy_fingerprint": training_row["optimizer_policy_fingerprint"],
            "activation_policy_fingerprint": activation_fingerprint,
            "problem_fingerprint": solved.problem_fingerprint,
            "solver_metadata_json": {
                "solver_name": solved.solver_name,
                "solver_version": solved.solver_version,
                "solver_options_fingerprint": solved.solver_options_fingerprint,
            },
            "evaluation_version": evaluated.evaluation_version,
            "evaluation_fingerprint": evaluated.evaluation_fingerprint,
            "evaluation_json": dataclasses.asdict(evaluated),
        }
        fingerprint, snapshot_id = build_policy_snapshot_identity(snapshot_row)
        snapshot_row["payload_fingerprint"] = fingerprint
        snapshot_row["policy_snapshot_id"] = snapshot_id
    latest_head = store.get_decision_evidence_head(request.domain_id)
    latest_active = store.resolve_active_ranking_policy(
        request.domain_id, runtime.runtime_contract_fingerprint
    )
    latest_parent = (
        f"learned:{latest_active['policy_snapshot_id']}"
        if latest_active is not None
        else f"zero_residual:{first.baseline_policy_fingerprint}"
    )
    latest_policy, latest_fingerprint = validate_decision_learning_policy(
        load_config()["decision_learning_policy"]
    )
    if (
        latest_head["evidence_head_fingerprint"] != expected_head_fingerprint
        or latest_parent != parent_ref
        or latest_fingerprint != decision_fingerprint
        or latest_policy["inverse_optimization"] != optimizer
    ):
        training_row["status"] = "invalid_input"
        training_row["result_json"] = {**result_payload, "status": "invalid_input", "error_code": "stale_evidence"}
        training_row.pop("training_run_id")
        training_row["training_run_id"] = build_training_run_identity(training_row)
        store.persist_candidate_attempt(training_row)
        return cast(dict[str, Any], training_row["result_json"])
    persisted = store.persist_candidate_attempt(training_row, snapshot_row)
    return {
        **result_payload,
        "training_run_id": persisted["training_run"]["training_run_id"],
        "policy_snapshot_id": (
            persisted["snapshot"]["policy_snapshot_id"] if persisted["snapshot"] else None
        ),
    }
