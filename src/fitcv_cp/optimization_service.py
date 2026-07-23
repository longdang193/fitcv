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
from typing import Any

from fitcv.config import load_config
from fitcv.decision_feedback import (
    optimizer_policy_fingerprint,
    reduce_rating_event_states,
    validate_decision_learning_policy,
)
from fitcv.embeddings import build_embedding_contract_fingerprint
from fitcv.inverse_optimization import (
    CompatibleParentReference,
    InverseOptimizationRequest,
    InverseOptimizationResult,
    PreferenceEvaluationResult,
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
from fitcv_cp.settings_store import (
    load_active_settings,
    settings_revision as build_settings_revision,
)
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


def _optimization_display_status(status: str) -> str:
    if status == "candidate_created":
        return "Succeeded"
    if status == "no_op":
        return "No Change"
    if status in {"evaluation_rejected", "insufficient_evidence"}:
        return "Not Created"
    return "Failed"


def _job_label(job: dict[str, Any] | None, source_job_url: str) -> str:
    payload = job or {}
    title = str(payload.get("job_title") or payload.get("title") or "").strip()
    company = str(payload.get("company") or payload.get("company_name") or "").strip()
    if title and company:
        return f"{title} at {company}"
    return title or company or source_job_url


def _historical_rating_evidence(
    request: InverseOptimizationRequest,
    store: ControlPlaneStore,
) -> tuple[list[str], list[dict[str, Any]]]:
    effective: list[tuple[int, str, Any, Any, Any]] = []
    for item in request.episodes:
        states = reduce_rating_event_states(
            item.events,
            event_watermark=request.event_watermark,
        )
        events_by_id = {event.event_id: event for event in item.events}
        alternatives_by_id = {
            alternative.alternative_id: alternative for alternative in item.alternatives
        }
        for state in states.values():
            if state.rating == "unrated" or state.source_event_id is None:
                continue
            event = events_by_id.get(state.source_event_id)
            alternative = alternatives_by_id.get(state.alternative_id)
            if event is None or alternative is None or event.event_sequence is None:
                raise ValueError("effective rating evidence is incomplete")
            effective.append(
                (
                    int(event.event_sequence),
                    event.event_id,
                    item.episode,
                    alternative,
                    event,
                )
            )
    effective.sort(key=lambda value: (value[0], value[1]))
    source_event_ids: list[str] = []
    rows: list[dict[str, Any]] = []
    for _sequence, event_id, episode, alternative, event in effective:
        if event_id in source_event_ids:
            raise ValueError("duplicate effective rating event")
        source_event_ids.append(event_id)
        rows.append(
            {
                "source_rating_event_id": event_id,
                "run_id": episode.run_id,
                "alternative_id": alternative.alternative_id,
                "job_label": _job_label(
                    store.get_run_job(episode.run_id, alternative.alternative_id),
                    alternative.source_job_url,
                ),
                "source_job_url": alternative.source_job_url,
                "displayed_rank": alternative.displayed_rank,
                "baseline_fit": alternative.baseline_fit,
                "baseline_fit_label": alternative.baseline_fit_label,
                "rating": int(event.rating),
                "rated_at": event.created_at.isoformat(),
            }
        )
    return source_event_ids, rows


def current_activation_provenance(
    snapshot: dict[str, Any],
    config: dict[str, Any],
    *,
    personalization_strength: float | None = None,
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
        learned_alpha=float(
            optimizer["learned_alpha"]
            if personalization_strength is None
            else personalization_strength
        ),
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
    ranking_mode: str,
    personalization_strength: float,
    settings_revision: str,
    expected_evidence_head_fingerprint: str | None = None,
    expected_parent_ref: str | None = None,
) -> dict[str, Any]:
    if ranking_mode == "baseline":
        return {
            "status": "not_started",
            "error_code": "personalized_ranking_required",
        }
    if ranking_mode != "personalized":
        return {"status": "invalid_input", "error_code": "invalid_ranking_mode"}
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
    canonical_policy, decision_fingerprint = validate_decision_learning_policy(
        config["decision_learning_policy"]
    )
    canonical_optimizer = canonical_policy["inverse_optimization"]
    bounds = canonical_optimizer["learned_alpha_bounds"]
    strength = float(personalization_strength)
    if not float(bounds["minimum"]) <= strength <= float(bounds["maximum"]):
        return {
            "status": "invalid_input",
            "error_code": "personalization_strength_out_of_range",
        }
    optimizer = {**canonical_optimizer, "learned_alpha": strength}
    policy = {**canonical_policy, "inverse_optimization": optimizer}
    canonical_optimizer_fingerprint = optimizer_policy_fingerprint(canonical_policy)
    if request.episodes:
        first = request.episodes[0].episode
        baseline_policy_fingerprint = first.baseline_policy_fingerprint
        ranking_contract_fingerprint = first.ranking_contract_fingerprint
        embedding_model = first.embedding_model
        embedding_dimension = first.embedding_dimension
        embedding_contract_fingerprint = first.embedding_contract_fingerprint
        rating_scale_version = str(
            getattr(
                first,
                "rating_scale_version",
                canonical_policy["rating_scale"]["version"],
            )
        )
    else:
        embedding_contract = build_embedding_contract_fingerprint(config)
        embedding_payload = embedding_contract["payload"]
        baseline_policy_fingerprint = str(
            build_contract_fingerprint(config["ranking_policy"])
        )
        ranking_contract_fingerprint = str(
            config["ranking_contract"]["ranking_contract_fingerprint"]
        )
        embedding_model = str(embedding_payload["embedding_model"])
        embedding_dimension = int(embedding_payload["embedding_dimension"])
        embedding_contract_fingerprint = str(embedding_contract["fingerprint"])
        rating_scale_version = str(canonical_policy["rating_scale"]["version"])
    runtime = PreferenceRuntimeContract.build(
        domain_id=request.domain_id,
        baseline_policy_fingerprint=baseline_policy_fingerprint,
        ranking_contract_fingerprint=ranking_contract_fingerprint,
        embedding_model=embedding_model,
        embedding_dimension=embedding_dimension,
        embedding_contract_fingerprint=embedding_contract_fingerprint,
        learned_alpha=optimizer["learned_alpha"],
        preference_vector_norm_bound=optimizer["preference_vector_norm_bound"],
    )
    active = store.resolve_active_ranking_policy(
        request.domain_id, runtime.runtime_contract_fingerprint
    )
    parent = None
    parent_vector = tuple(0.0 for _ in range(embedding_dimension))
    parent_kind = "zero_residual"
    parent_ref = f"zero_residual:{baseline_policy_fingerprint}"
    if active is not None:
        parent_vector = tuple(float(value) for value in active["preference_vector_json"])
        parent_kind = "learned"
        parent_ref = f"learned:{active['policy_snapshot_id']}"
        parent = CompatibleParentReference(
            parent_kind=parent_kind,
            domain_id=request.domain_id,
            parent_ref=parent_ref,
            preference_vector=parent_vector,
            baseline_policy_fingerprint=baseline_policy_fingerprint,
            ranking_contract_fingerprint=ranking_contract_fingerprint,
            embedding_contract_fingerprint=embedding_contract_fingerprint,
            embedding_dimension=embedding_dimension,
            learned_alpha=optimizer["learned_alpha"],
        )
    if expected_parent_ref is not None and expected_parent_ref != parent_ref:
        return {"status": "stale", "error_code": "candidate_parent_changed"}
    terminal_error_code: str | None = None
    try:
        source_rating_event_ids, rating_evidence_rows = _historical_rating_evidence(
            request, store
        )
    except ValueError:
        source_rating_event_ids = []
        rating_evidence_rows = []
        terminal_error_code = "rating_evidence_unavailable"
    solved: InverseOptimizationResult | None
    evaluated: PreferenceEvaluationResult | None
    try:
        if terminal_error_code is not None:
            solved = None
            evaluated = None
        elif not request.episodes:
            solved = None
            evaluated = None
            terminal_error_code = "zero_rating_evidence"
        else:
            solved = solve_preference_residual(request, policy)
            evaluated = evaluate_preference_residual(request, solved, policy, parent)
    except Exception:
        solved = None
        evaluated = None
        terminal_error_code = "solver_execution_failed"
    status = (
        solved.status
        if solved is not None
        else "insufficient_evidence"
        if terminal_error_code == "zero_rating_evidence"
        else "invalid_input"
        if terminal_error_code == "rating_evidence_unavailable"
        else "solver_error"
    )
    promotion = {"passed": False, "reason_code": status}
    no_op_delta = None
    candidate_vector = solved.candidate_preference_vector if solved is not None else None
    if (
        solved is not None
        and evaluated is not None
        and solved.status == "optimal"
        and evaluated.status == "evaluated"
        and candidate_vector is not None
    ):
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
    elif solved is not None and evaluated is not None and (
        solved.status == "insufficient_evidence"
        or evaluated.status == "insufficient_evidence"
    ):
        status = "insufficient_evidence"
    elif solved is not None and evaluated is not None and (
        solved.status == "invalid_input" or evaluated.status == "invalid_input"
    ):
        status = "invalid_input"
    result_payload = {
        "status": status,
        "solver_result": dataclasses.asdict(solved) if solved is not None else None,
        "evaluation_result": (
            dataclasses.asdict(evaluated) if evaluated is not None else None
        ),
        "promotion_gate": promotion,
        "no_op_max_coordinate_delta": no_op_delta,
        "evidence_head_fingerprint": expected_head["evidence_head_fingerprint"],
        "parent_policy_ref": parent_ref,
        "settings_revision": settings_revision,
        "personalization_strength": strength,
    }
    if terminal_error_code is not None:
        result_payload["error_code"] = terminal_error_code
    activation_fingerprint = build_contract_fingerprint(optimizer["activation"])
    training_row: dict[str, Any] = {
        "schema_version": "inverse_training_run_v1",
        "domain_id": request.domain_id,
        "status": status,
        "cohort_fingerprint": (
            solved.cohort_fingerprint if solved is not None else None
        ) or "unavailable",
        "event_watermark": request.event_watermark,
        "edge_set_fingerprint": (
            solved.edge_set_fingerprint if solved is not None else None
        ) or "unavailable",
        "rating_scale_version": rating_scale_version,
        "compiler_version": policy["preference_compiler"]["compiler_version"],
        "compiler_policy_fingerprint": build_contract_fingerprint(policy["preference_compiler"]),
        "decision_learning_policy_fingerprint": decision_fingerprint,
        "optimizer_policy_fingerprint": canonical_optimizer_fingerprint,
        "activation_policy_fingerprint": activation_fingerprint,
        "baseline_policy_fingerprint": baseline_policy_fingerprint,
        "ranking_contract_fingerprint": ranking_contract_fingerprint,
        "embedding_model": embedding_model,
        "embedding_contract_fingerprint": embedding_contract_fingerprint,
        "embedding_dimension": embedding_dimension,
        "learned_alpha": optimizer["learned_alpha"],
        "parent_policy_kind": parent_kind,
        "parent_policy_ref": parent_ref,
        "problem_fingerprint": (
            solved.problem_fingerprint if solved is not None else None
        ),
        "evaluation_fingerprint": (
            evaluated.evaluation_fingerprint if evaluated is not None else None
        ),
        "result_json": result_payload,
    }
    training_row["training_run_id"] = build_training_run_identity(training_row)
    snapshot_row = None
    if status == "candidate_created" and candidate_vector is not None:
        assert solved is not None and evaluated is not None
        snapshot_row = {
            "schema_version": "ranking_policy_snapshot_v1",
            "domain_id": request.domain_id,
            "status": "candidate",
            "runtime_contract_fingerprint": runtime.runtime_contract_fingerprint,
            "baseline_policy_fingerprint": baseline_policy_fingerprint,
            "ranking_contract_fingerprint": ranking_contract_fingerprint,
            "embedding_model": embedding_model,
            "embedding_contract_fingerprint": embedding_contract_fingerprint,
            "embedding_dimension": embedding_dimension,
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
            "rating_scale_version": rating_scale_version,
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
        else f"zero_residual:{baseline_policy_fingerprint}"
    )
    latest_policy, latest_fingerprint = validate_decision_learning_policy(
        load_config()["decision_learning_policy"]
    )
    latest_settings = load_active_settings()
    latest_mode = latest_settings.get("preference_optimization.ranking_mode")
    latest_strength = latest_settings.get(
        "preference_optimization.personalization_strength"
    )
    if (
        latest_head["evidence_head_fingerprint"] != expected_head_fingerprint
        or latest_parent != parent_ref
        or latest_fingerprint != decision_fingerprint
        or optimizer_policy_fingerprint(latest_policy) != canonical_optimizer_fingerprint
        or build_settings_revision(latest_settings) != settings_revision
        or latest_mode != ranking_mode
        or latest_strength is None
        or float(latest_strength) != strength
    ):
        return {"status": "stale", "error_code": "optimization_precondition_changed"}
    projection_payload = {
        "settings_revision": settings_revision,
        "ranking_mode": ranking_mode,
        "personalization_strength": strength,
        "evidence_head_fingerprint": expected_head["evidence_head_fingerprint"],
        "event_watermark": request.event_watermark,
        "source_rating_event_ids": source_rating_event_ids,
        "rating_evidence_rows": rating_evidence_rows,
    }
    persisted = store.persist_candidate_attempt(
        training_row,
        snapshot_row,
        projection_payload,
    )
    return {
        **result_payload,
        "display_status": _optimization_display_status(status),
        "preference_optimization_run_id": persisted["optimization_run"][
            "preference_optimization_run_id"
        ],
        "policy_snapshot_id": (
            persisted["snapshot"]["policy_snapshot_id"] if persisted["snapshot"] else None
        ),
    }
