"""@meta
name: run_inverse_optimization
type: script
domain: inverse_optimization
ownership: feature
capabilities:
  - cv_system.preference-learning
responsibility:
  - Adapt canonical offline preference-learning JSON to typed domain records.
  - Emit canonical solver and evaluation artifacts atomically.
inputs:
  - inverse_training_bundle_v1 JSON and optional compatible parent JSON.
outputs:
  - inverse_optimization_result_v1 or preference_evaluation_result_v1 JSON.
lifecycle:
  - status: active
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime
from enum import Enum
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fitcv.config import load_config  # noqa: E402
from fitcv.decision_feedback import (  # noqa: E402
    DecisionRatingEvent,
    RatingEventType,
    RatingValue,
    build_episode_records,
    optimizer_policy_fingerprint,
    validate_decision_learning_policy,
)
from fitcv.inverse_optimization import (  # noqa: E402
    CompatibleParentReference,
    EvaluationAlternativeSlice,
    EvaluationEpisodeContext,
    InverseOptimizationRequest,
    InverseTrainingEpisode,
    RetrievalAuditContext,
    evaluate_preference_residual,
    solve_preference_residual,
)
from fitcv.preference_policy import (  # noqa: E402
    PreferenceRuntimeContract,
    build_policy_snapshot_identity,
    build_training_run_identity,
    evaluate_promotion_gate,
    max_coordinate_delta,
    preference_vector_fingerprint,
)
from fitcv.shortlist_runtime import build_contract_fingerprint  # noqa: E402
from fitcv_cp import sqlite_store  # noqa: E402

_BUNDLE_KEYS = {"schema_version", "domain_id", "event_watermark", "episodes"}
_EPISODE_KEYS = {
    "feedback_source",
    "events_loaded_through_sequence",
    "rating_events",
    "evaluation_context",
}
_EVENT_KEYS = {
    "event_sequence",
    "event_id",
    "episode_id",
    "alternative_id",
    "event_type",
    "rating",
    "rating_scale_version",
    "acted_by",
    "created_at",
}
_CONTEXT_KEYS = {"episode_id", "alternative_slices", "retrieval_audit"}
_SLICE_KEYS = {"alternative_id", "baseline_fit_label", "location_bucket", "language_bucket"}
_AUDIT_KEYS = {
    "audit_fingerprint",
    "sample_count",
    "cutoff_vector_similarity",
    "sampled_vector_similarities",
    "relevance_labels_available",
}
_PARENT_KEYS = {
    "parent_kind",
    "domain_id",
    "parent_ref",
    "preference_vector",
    "baseline_policy_fingerprint",
    "ranking_contract_fingerprint",
    "embedding_contract_fingerprint",
    "embedding_dimension",
    "learned_alpha",
}


def _object(value: Any, keys: set[str], field: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{field} must contain exact keys")
    return value


def _integer(value: Any, field: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{field} must be an integer >= {minimum}")
    return int(value)


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be finite")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be finite") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def _text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} is required")
    return text


def _timestamp(value: Any) -> datetime.datetime:
    text = _text(value, "created_at")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("created_at must be RFC3339") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("created_at must be timezone-aware")
    return parsed


def _rating_event(value: Any) -> DecisionRatingEvent:
    payload = _object(value, _EVENT_KEYS, "rating event")
    event_type = RatingEventType(_text(payload["event_type"], "event_type"))
    raw_rating = payload["rating"]
    rating = None if raw_rating is None else RatingValue(_integer(raw_rating, "rating", minimum=1))
    return DecisionRatingEvent(
        event_sequence=_integer(payload["event_sequence"], "event_sequence", minimum=1),
        event_id=_text(payload["event_id"], "event_id"),
        episode_id=_text(payload["episode_id"], "episode_id"),
        alternative_id=_text(payload["alternative_id"], "alternative_id"),
        event_type=event_type,
        rating=rating,
        rating_scale_version=_text(payload["rating_scale_version"], "rating_scale_version"),
        acted_by=_text(payload["acted_by"], "acted_by"),
        created_at=_timestamp(payload["created_at"]),
    )


def _evaluation_context(value: Any) -> EvaluationEpisodeContext | None:
    if value is None:
        return None
    payload = _object(value, _CONTEXT_KEYS, "evaluation context")
    raw_slices = payload["alternative_slices"]
    if not isinstance(raw_slices, list):
        raise ValueError("alternative_slices must be a list")
    slices = tuple(
        EvaluationAlternativeSlice(
            alternative_id=_text(item["alternative_id"], "alternative_id"),
            baseline_fit_label=_text(item["baseline_fit_label"], "baseline_fit_label"),
            location_bucket=None if item["location_bucket"] is None else str(item["location_bucket"]),
            language_bucket=None if item["language_bucket"] is None else str(item["language_bucket"]),
        )
        for item in (_object(raw, _SLICE_KEYS, "evaluation alternative slice") for raw in raw_slices)
    )
    raw_audit = payload["retrieval_audit"]
    audit = None
    if raw_audit is not None:
        audit_payload = _object(raw_audit, _AUDIT_KEYS, "retrieval audit")
        similarities = audit_payload["sampled_vector_similarities"]
        if not isinstance(similarities, list):
            raise ValueError("sampled_vector_similarities must be a list")
        if not isinstance(audit_payload["relevance_labels_available"], bool):
            raise ValueError("relevance_labels_available must be boolean")
        audit = RetrievalAuditContext(
            audit_fingerprint=_text(audit_payload["audit_fingerprint"], "audit_fingerprint"),
            sample_count=_integer(audit_payload["sample_count"], "sample_count"),
            cutoff_vector_similarity=_number(
                audit_payload["cutoff_vector_similarity"],
                "cutoff_vector_similarity",
            ),
            sampled_vector_similarities=tuple(
                _number(item, "sampled_vector_similarity") for item in similarities
            ),
            relevance_labels_available=audit_payload["relevance_labels_available"],
        )
    return EvaluationEpisodeContext(
        episode_id=_text(payload["episode_id"], "episode_id"),
        alternative_slices=slices,
        retrieval_audit=audit,
    )


def _request_from_bundle(value: Any, domain_id: str) -> InverseOptimizationRequest:
    payload = _object(value, _BUNDLE_KEYS, "training bundle")
    if payload["schema_version"] != "inverse_training_bundle_v1":
        raise ValueError("unsupported training bundle")
    if _text(payload["domain_id"], "domain_id") != domain_id:
        raise ValueError("bundle domain conflicts with --domain")
    raw_episodes = payload["episodes"]
    if not isinstance(raw_episodes, list):
        raise ValueError("episodes must be a list")
    episodes = []
    for raw_item in raw_episodes:
        item = _object(raw_item, _EPISODE_KEYS, "training episode")
        episode, alternatives = build_episode_records(item["feedback_source"])
        episodes.append(
            InverseTrainingEpisode(
                episode=episode,
                alternatives=alternatives,
                events=tuple(_rating_event(event) for event in item["rating_events"]),
                events_loaded_through_sequence=_integer(
                    item["events_loaded_through_sequence"],
                    "events_loaded_through_sequence",
                ),
                evaluation_context=_evaluation_context(item["evaluation_context"]),
            )
        )
    return InverseOptimizationRequest(
        schema_version="inverse_optimization_request_v1",
        domain_id=domain_id,
        event_watermark=_integer(payload["event_watermark"], "event_watermark"),
        episodes=tuple(episodes),
    )


def _parent_reference(value: Any) -> CompatibleParentReference:
    payload = _object(value, _PARENT_KEYS, "parent reference")
    raw_vector = payload["preference_vector"]
    if not isinstance(raw_vector, list):
        raise ValueError("preference_vector must be a list")
    return CompatibleParentReference(
        parent_kind=_text(payload["parent_kind"], "parent_kind"),
        domain_id=_text(payload["domain_id"], "domain_id"),
        parent_ref=_text(payload["parent_ref"], "parent_ref"),
        preference_vector=tuple(_number(value, "preference_vector") for value in raw_vector),
        baseline_policy_fingerprint=_text(
            payload["baseline_policy_fingerprint"],
            "baseline_policy_fingerprint",
        ),
        ranking_contract_fingerprint=_text(
            payload["ranking_contract_fingerprint"],
            "ranking_contract_fingerprint",
        ),
        embedding_contract_fingerprint=_text(
            payload["embedding_contract_fingerprint"],
            "embedding_contract_fingerprint",
        ),
        embedding_dimension=_integer(payload["embedding_dimension"], "embedding_dimension", minimum=1),
        learned_alpha=_number(payload["learned_alpha"], "learned_alpha"),
    )


def _json_default(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    raise TypeError(f"unsupported JSON value: {type(value).__name__}")


def _canonical_json(payload: Any) -> str:
    value = dataclasses.asdict(cast(Any, payload)) if dataclasses.is_dataclass(payload) else payload
    return json.dumps(value, default=_json_default, sort_keys=True, separators=(",", ":"))


def _emit_payload(payload: Any, output_path: Path | None) -> None:
    text = _canonical_json(payload) + "\n"
    if output_path is None:
        sys.stdout.write(text)
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(text)
            temporary_path = Path(handle.name)
        os.replace(temporary_path, output_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _exit_code(status: str) -> int:
    if status in {
        "optimal", "evaluated", "insufficient_evidence", "candidate_created", "no_op",
        "active", "rejected", "zero_residual", "inspection",
    }:
        return 0
    if status == "invalid_input":
        return 2
    if status in {"evaluation_rejected", "stale", "conflict", "invalid_state", "incompatible"}:
        return 4
    return 3


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train, evaluate, and manage ranking policies.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("train", "evaluate", "candidate"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--domain", required=True)
        subparser.add_argument("--input", required=True, type=Path)
        subparser.add_argument("--output", type=Path)
        if command == "evaluate":
            subparser.add_argument("--parent", type=Path)
    reject = subparsers.add_parser("reject")
    reject.add_argument("--snapshot", required=True)
    reject.add_argument("--acted-by", required=True)
    reject.add_argument("--reason", required=True)
    reject.add_argument("--output", type=Path)
    activate = subparsers.add_parser("activate")
    activate.add_argument("--snapshot", required=True)
    activate.add_argument("--expected-parent", required=True)
    activate.add_argument("--acted-by", required=True)
    activate.add_argument("--output", type=Path)
    rollback = subparsers.add_parser("rollback")
    rollback.add_argument("--domain", required=True)
    rollback.add_argument("--expected-active", required=True)
    rollback.add_argument("--target", required=True)
    rollback.add_argument("--acted-by", required=True)
    rollback.add_argument("--output", type=Path)
    inspect = subparsers.add_parser("inspect")
    inspect.add_argument("--domain", required=True)
    inspect.add_argument("--run-id")
    inspect.add_argument("--output", type=Path)
    return parser


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


def _candidate_operation(request: InverseOptimizationRequest) -> dict[str, Any]:
    config = load_config()
    policy, decision_fingerprint = validate_decision_learning_policy(
        config["decision_learning_policy"]
    )
    expected_head = _request_evidence_head(request)
    current_head = sqlite_store.get_decision_evidence_head(request.domain_id)
    if expected_head["evidence_head_fingerprint"] != current_head["evidence_head_fingerprint"]:
        return {"status": "invalid_input", "error_code": "stale_evidence"}
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
    active = sqlite_store.resolve_active_ranking_policy(
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
    latest_head = sqlite_store.get_decision_evidence_head(request.domain_id)
    latest_active = sqlite_store.resolve_active_ranking_policy(
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
        latest_head["evidence_head_fingerprint"] != expected_head["evidence_head_fingerprint"]
        or latest_parent != parent_ref
        or latest_fingerprint != decision_fingerprint
        or latest_policy["inverse_optimization"] != optimizer
    ):
        training_row["status"] = "invalid_input"
        training_row["result_json"] = {**result_payload, "status": "invalid_input", "error_code": "stale_evidence"}
        training_row.pop("training_run_id")
        training_row["training_run_id"] = build_training_run_identity(training_row)
        sqlite_store.persist_candidate_attempt(training_row)
        return cast(dict[str, Any], training_row["result_json"])
    persisted = sqlite_store.persist_candidate_attempt(training_row, snapshot_row)
    return {
        **result_payload,
        "training_run_id": persisted["training_run"]["training_run_id"],
        "policy_snapshot_id": (
            persisted["snapshot"]["policy_snapshot_id"] if persisted["snapshot"] else None
        ),
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    output_path = args.output
    result: Any
    try:
        if args.command in {"train", "evaluate", "candidate"}:
            bundle = json.loads(args.input.read_text(encoding="utf-8"))
            request = _request_from_bundle(bundle, args.domain)
            policy = load_config()["decision_learning_policy"]
        if args.command == "train":
            result = solve_preference_residual(request, policy)
        elif args.command == "evaluate":
            full_result = solve_preference_residual(request, policy)
            parent = None
            if args.parent is not None:
                parent = _parent_reference(
                    json.loads(args.parent.read_text(encoding="utf-8"))
                )
            result = evaluate_preference_residual(request, full_result, policy, parent)
        elif args.command == "candidate":
            result = _candidate_operation(request)
        elif args.command == "reject":
            result = sqlite_store.reject_ranking_policy_candidate(
                args.snapshot, acted_by=args.acted_by, reason=args.reason
            )
        elif args.command == "activate":
            lifecycle = sqlite_store.inspect_ranking_policy_lifecycle("ranking_v1")
            snapshot = next(
                (row for row in lifecycle["snapshots"] if row["policy_snapshot_id"] == args.snapshot),
                None,
            )
            if snapshot is None:
                raise KeyError(args.snapshot)
            evidence = sqlite_store.get_decision_evidence_head(snapshot["domain_id"])
            result = sqlite_store.activate_ranking_policy_candidate(
                args.snapshot,
                expected_parent_ref=args.expected_parent,
                evidence_head_fingerprint=evidence["evidence_head_fingerprint"],
                acted_by=args.acted_by,
            )
        elif args.command == "rollback":
            result = sqlite_store.rollback_ranking_policy(
                args.domain,
                expected_active=args.expected_active,
                target=args.target,
                acted_by=args.acted_by,
            )
        else:
            result = {
                "status": "inspection",
                **sqlite_store.inspect_ranking_policy_lifecycle(args.domain),
            }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        lifecycle_errors = {
            "active snapshot changed": ("conflict", "active_snapshot_changed"),
            "conflicting rejection reason": ("conflict", "conflicting_rejection_reason"),
            "candidate parent changed": ("stale", "candidate_parent_changed"),
            "candidate evidence changed": ("stale", "candidate_evidence_changed"),
            "rollback target is incompatible": ("incompatible", "rollback_target_incompatible"),
            "snapshot is not candidate": ("invalid_state", "snapshot_not_candidate"),
            "rollback target must be retired": ("invalid_state", "rollback_target_not_retired"),
        }
        status, error_code = lifecycle_errors.get(
            str(exc), ("invalid_input", f"{type(exc).__name__}:{exc}")
        )
        result = {"status": status, "error_code": error_code}
    _emit_payload(result, output_path)
    status = result["status"] if isinstance(result, dict) else result.status
    return _exit_code(status)


if __name__ == "__main__":
    raise SystemExit(main())
