"""@meta
name: inverse_optimization
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.preference-learning
responsibility:
  - Build one compatible preference-evidence cohort and solve one bounded latent residual.
  - Evaluate learned residuals with episode-grouped held-out evidence.
inputs:
  - Immutable decision episodes, alternatives, rating events, and decision-learning policy.
outputs:
  - Typed offline solver and evaluation results.
lifecycle:
  - status: active
"""

from __future__ import annotations

import dataclasses
import hashlib
import importlib
import importlib.metadata
import json
import math
import time
from dataclasses import dataclass
from typing import Any, Iterable

from fitcv.decision_feedback import (
    DecisionAlternative,
    DecisionEpisode,
    DecisionRatingEvent,
    PreferenceCompilerResult,
    compile_preference_edges,
    optimizer_policy_fingerprint,
    validate_decision_learning_policy,
)
from fitcv.shortlist_runtime import build_contract_fingerprint

_REQUEST_SCHEMA_VERSION = "inverse_optimization_request_v1"
_RESULT_SCHEMA_VERSION = "inverse_optimization_result_v1"
_EVALUATION_RESULT_SCHEMA_VERSION = "preference_evaluation_result_v1"
_PROBLEM_SCHEMA_VERSION = "inverse_problem_v1"
_TRAINING_BUNDLE_SCHEMA_VERSION = "inverse_training_bundle_v1"


@dataclass(frozen=True)
class EvaluationAlternativeSlice:
    alternative_id: str
    baseline_fit_label: str
    location_bucket: str | None
    language_bucket: str | None


@dataclass(frozen=True)
class RetrievalAuditContext:
    audit_fingerprint: str
    sample_count: int
    cutoff_vector_similarity: float
    sampled_vector_similarities: tuple[float, ...]
    relevance_labels_available: bool = False


@dataclass(frozen=True)
class EvaluationEpisodeContext:
    episode_id: str
    alternative_slices: tuple[EvaluationAlternativeSlice, ...]
    retrieval_audit: RetrievalAuditContext | None = None


@dataclass(frozen=True)
class InverseTrainingEpisode:
    episode: DecisionEpisode
    alternatives: tuple[DecisionAlternative, ...]
    events: tuple[DecisionRatingEvent, ...]
    events_loaded_through_sequence: int
    evaluation_context: EvaluationEpisodeContext | None = None


@dataclass(frozen=True)
class InverseOptimizationRequest:
    schema_version: str
    domain_id: str
    event_watermark: int
    episodes: tuple[InverseTrainingEpisode, ...]


@dataclass(frozen=True)
class CompatibleParentReference:
    parent_kind: str
    domain_id: str
    parent_ref: str
    preference_vector: tuple[float, ...]
    baseline_policy_fingerprint: str
    ranking_contract_fingerprint: str
    embedding_contract_fingerprint: str
    embedding_dimension: int
    learned_alpha: float


@dataclass(frozen=True)
class InverseOptimizationDiagnostics:
    episode_count: int
    edge_count: int
    evidence_weight_sum: float
    zero_direction_count: int
    nonzero_direction_count: int
    unique_direction_count: int
    direction_span_status: str
    error_code: str | None = None
    solver_seconds: float | None = None


@dataclass(frozen=True)
class InverseOptimizationResult:
    schema_version: str
    status: str
    domain_id: str
    event_watermark: int
    cohort_fingerprint: str | None
    edge_set_fingerprint: str | None
    optimizer_policy_fingerprint: str | None
    decision_learning_policy_fingerprint: str | None
    problem_fingerprint: str | None
    candidate_preference_vector: tuple[float, ...] | None
    objective_value: float | None
    independently_recomputed_objective: float | None
    max_preference_violation: float | None
    preference_vector_norm: float | None
    vector_norm_residual: float | None
    embedding_model: str | None
    embedding_dimension: int | None
    embedding_contract_fingerprint: str | None
    learned_alpha: float | None
    solver_name: str | None
    solver_version: str | None
    solver_options_fingerprint: str | None
    raw_solver_status: str | None
    diagnostics: InverseOptimizationDiagnostics


@dataclass(frozen=True)
class PreferenceMetricSummary:
    pair_count: int
    evidence_weight_sum: float
    pair_agreement_rate: float | None
    margin_satisfaction_rate: float | None
    weighted_regret: float
    clipping_frequency: float | None
    rank_change_fraction: float | None


@dataclass(frozen=True)
class PreferenceFoldResult:
    fold_index: int
    status: str
    train_episode_ids: tuple[str, ...]
    validation_episode_ids: tuple[str, ...]
    problem_fingerprint: str | None
    baseline_metrics: PreferenceMetricSummary
    candidate_metrics: PreferenceMetricSummary | None
    parent_metrics: PreferenceMetricSummary | None
    vector_stability: float | None


@dataclass(frozen=True)
class PreferenceAggregateMetrics:
    baseline: PreferenceMetricSummary
    candidate: PreferenceMetricSummary | None
    parent: PreferenceMetricSummary | None


@dataclass(frozen=True)
class PreferenceCoverage:
    baseline_labels: tuple[tuple[str, int], ...]
    rating_gaps: tuple[tuple[str, int], ...]
    locations: tuple[tuple[str, int], ...]
    languages: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class RetrievalAuditSummary:
    status: str
    recall: None
    sample_count: int
    audit_fingerprints: tuple[str, ...]


@dataclass(frozen=True)
class PreferenceEvaluationResult:
    schema_version: str
    status: str
    evaluation_version: str
    evaluation_mode: str
    cohort_fingerprint: str | None
    full_problem_fingerprint: str | None
    parent_comparison_status: str
    fold_results: tuple[PreferenceFoldResult, ...]
    aggregate_metrics: PreferenceAggregateMetrics | None
    coverage: PreferenceCoverage
    retrieval_audit: RetrievalAuditSummary
    evaluation_fingerprint: str | None


@dataclass(frozen=True)
class _PreparedEdge:
    episode_id: str
    preferred_alternative_id: str
    other_alternative_id: str
    baseline_delta: float
    embedding_delta: tuple[float, ...]
    weight: float
    rating_gap: int


@dataclass(frozen=True)
class _PreparedProblem:
    request: InverseOptimizationRequest
    policy: dict[str, Any]
    decision_learning_policy_fingerprint: str
    optimizer_policy_fingerprint: str
    cohort_fingerprint: str
    edge_set_fingerprint: str
    problem_fingerprint: str
    baseline_policy_fingerprint: str
    ranking_contract_fingerprint: str
    embedding_model: str
    embedding_contract_fingerprint: str
    embedding_dimension: int
    solver_options_fingerprint: str
    compiler_results: tuple[PreferenceCompilerResult, ...]
    alternatives_by_episode: tuple[tuple[str, tuple[DecisionAlternative, ...]], ...]
    edges: tuple[_PreparedEdge, ...]
    diagnostics: InverseOptimizationDiagnostics


def _finite_float(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be finite")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be finite") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def _embedding(alternative: DecisionAlternative, dimension: int) -> tuple[float, ...]:
    try:
        payload = json.loads(alternative.normalized_embedding_json)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("normalized_embedding_json must be valid JSON") from exc
    if not isinstance(payload, list) or len(payload) != dimension:
        raise ValueError("normalized embedding dimension mismatch")
    vector = tuple(_finite_float(value, "normalized embedding") for value in payload)
    expected = build_contract_fingerprint({"normalized_embedding": list(vector)})
    if alternative.embedding_vector_fingerprint != expected:
        raise ValueError("embedding vector fingerprint mismatch")
    norm = math.sqrt(math.fsum(value * value for value in vector))
    if abs(norm - 1.0) > 1.0e-6:
        raise ValueError("normalized embedding must have unit norm")
    return vector


def _canonical_events(events: Iterable[DecisionRatingEvent]) -> tuple[DecisionRatingEvent, ...]:
    return tuple(
        sorted(
            events,
            key=lambda event: (
                event.event_sequence if event.event_sequence is not None else 2**63,
                event.event_id,
            ),
        )
    )


def _direction_diagnostics(
    edges: tuple[_PreparedEdge, ...],
    tolerance: float,
) -> tuple[int, int, int, str]:
    normalized: list[tuple[float, ...]] = []
    zero_count = 0
    for edge in edges:
        norm = math.sqrt(math.fsum(value * value for value in edge.embedding_delta))
        if norm <= tolerance:
            zero_count += 1
            continue
        normalized.append(tuple(value / norm for value in edge.embedding_delta))
    unique = {tuple(round(value, 12) for value in direction) for direction in normalized}
    if not normalized:
        return zero_count, 0, 0, "none"
    if len(unique) == 1:
        return zero_count, len(normalized), 1, "single_direction"
    reference = normalized[0]
    is_collinear = all(
        abs(abs(math.fsum(left * right for left, right in zip(reference, direction, strict=True))) - 1.0)
        <= tolerance
        for direction in normalized[1:]
    )
    return zero_count, len(normalized), len(unique), "collinear" if is_collinear else "multiple_directions"


def _empty_diagnostics(error_code: str | None = None) -> InverseOptimizationDiagnostics:
    return InverseOptimizationDiagnostics(0, 0, 0.0, 0, 0, 0, "none", error_code)


def _invalid_result(
    request: InverseOptimizationRequest,
    error_code: str,
) -> InverseOptimizationResult:
    return InverseOptimizationResult(
        schema_version=_RESULT_SCHEMA_VERSION,
        status="invalid_input",
        domain_id=request.domain_id,
        event_watermark=request.event_watermark,
        cohort_fingerprint=None,
        edge_set_fingerprint=None,
        optimizer_policy_fingerprint=None,
        decision_learning_policy_fingerprint=None,
        problem_fingerprint=None,
        candidate_preference_vector=None,
        objective_value=None,
        independently_recomputed_objective=None,
        max_preference_violation=None,
        preference_vector_norm=None,
        vector_norm_residual=None,
        embedding_model=None,
        embedding_dimension=None,
        embedding_contract_fingerprint=None,
        learned_alpha=None,
        solver_name=None,
        solver_version=None,
        solver_options_fingerprint=None,
        raw_solver_status=None,
        diagnostics=_empty_diagnostics(error_code),
    )


def _prepare_problem(
    request: InverseOptimizationRequest,
    decision_learning_policy: Any,
) -> _PreparedProblem:
    if request.schema_version != _REQUEST_SCHEMA_VERSION:
        raise ValueError("unsupported inverse optimization request")
    if request.event_watermark < 0:
        raise ValueError("event_watermark must be nonnegative")
    if not request.episodes:
        raise ValueError("request requires episodes")
    policy, full_fingerprint = validate_decision_learning_policy(decision_learning_policy)
    if request.domain_id != policy["domain_id"]:
        raise ValueError("request domain conflicts with policy")
    optimizer = policy["inverse_optimization"]
    optimizer_fingerprint = optimizer_policy_fingerprint(policy)
    ordered_episodes = tuple(sorted(request.episodes, key=lambda item: item.episode.episode_id))
    episode_ids = [item.episode.episode_id for item in ordered_episodes]
    if len(set(episode_ids)) != len(episode_ids):
        raise ValueError("episode IDs must be unique")
    first = ordered_episodes[0].episode
    shared_contract = (
        first.domain_id,
        first.preference_context_fingerprint,
        first.ranking_contract_fingerprint,
        first.baseline_policy_fingerprint,
        first.embedding_model,
        first.embedding_contract_fingerprint,
        first.embedding_dimension,
        first.rating_scale_version,
    )
    compiler_results: list[PreferenceCompilerResult] = []
    all_edges: list[_PreparedEdge] = []
    alternatives_by_episode: list[tuple[str, tuple[DecisionAlternative, ...]]] = []
    episode_payloads: list[dict[str, Any]] = []
    aggregate_edge_payloads: list[dict[str, Any]] = []
    for item in ordered_episodes:
        episode = item.episode
        if item.events_loaded_through_sequence < request.event_watermark:
            raise ValueError("events_loaded_through_sequence is below event_watermark")
        contract = (
            episode.domain_id,
            episode.preference_context_fingerprint,
            episode.ranking_contract_fingerprint,
            episode.baseline_policy_fingerprint,
            episode.embedding_model,
            episode.embedding_contract_fingerprint,
            episode.embedding_dimension,
            episode.rating_scale_version,
        )
        if contract != shared_contract:
            raise ValueError("episodes do not form one compatible cohort")
        alternatives = tuple(sorted(item.alternatives, key=lambda alt: alt.alternative_id))
        if not alternatives or len({alt.alternative_id for alt in alternatives}) != len(alternatives):
            raise ValueError("episode alternatives must be nonempty and unique")
        if any(alt.episode_id != episode.episode_id for alt in alternatives):
            raise ValueError("alternative episode mismatch")
        vectors = {
            alternative.alternative_id: _embedding(alternative, episode.embedding_dimension)
            for alternative in alternatives
        }
        events = _canonical_events(item.events)
        if any(event.episode_id != episode.episode_id for event in events):
            raise ValueError("event episode mismatch")
        compiler = compile_preference_edges(
            episode,
            alternatives,
            events,
            event_watermark=request.event_watermark,
            decision_learning_policy=policy,
        )
        compiler_results.append(compiler)
        alternatives_by_id = {alternative.alternative_id: alternative for alternative in alternatives}
        for edge in compiler.edges:
            preferred = alternatives_by_id[edge.preferred_alternative_id]
            other = alternatives_by_id[edge.other_alternative_id]
            embedding_delta = tuple(
                left - right
                for left, right in zip(
                    vectors[preferred.alternative_id],
                    vectors[other.alternative_id],
                    strict=True,
                )
            )
            prepared_edge = _PreparedEdge(
                episode_id=episode.episode_id,
                preferred_alternative_id=preferred.alternative_id,
                other_alternative_id=other.alternative_id,
                baseline_delta=preferred.baseline_fit - other.baseline_fit,
                embedding_delta=embedding_delta,
                weight=edge.episode_bounded_weight,
                rating_gap=edge.rating_gap,
            )
            all_edges.append(prepared_edge)
            aggregate_edge_payloads.append(dataclasses.asdict(prepared_edge))
        alternatives_by_episode.append((episode.episode_id, alternatives))
        episode_payloads.append(
            {
                "episode_id": episode.episode_id,
                "qualification_context_fingerprint": episode.qualification_context_fingerprint,
                "candidate_set_fingerprint": episode.candidate_set_fingerprint,
                "source_stage_artifact_fingerprint": episode.source_stage_artifact_fingerprint,
                "compiler_input_fingerprint": compiler.compiler_input_fingerprint,
                "edge_set_fingerprint": compiler.edge_set_fingerprint,
            }
        )
    edges = tuple(
        sorted(
            all_edges,
            key=lambda edge: (
                edge.episode_id,
                edge.preferred_alternative_id,
                edge.other_alternative_id,
            ),
        )
    )
    cohort_fingerprint = build_contract_fingerprint(
        {
            "domain_id": request.domain_id,
            "event_watermark": request.event_watermark,
            "episodes": episode_payloads,
        }
    )
    aggregate_edge_payloads.sort(
        key=lambda edge: (
            str(edge["episode_id"]),
            str(edge["preferred_alternative_id"]),
            str(edge["other_alternative_id"]),
        )
    )
    edge_set_fingerprint = build_contract_fingerprint(
        {"schema_version": "inverse_edge_set_v1", "edges": aggregate_edge_payloads}
    )
    solver_options = {
        "name": optimizer["solver"]["name"],
        "max_iter": optimizer["solver"]["max_iter"],
        "warm_start": False,
        "verbose": False,
    }
    solver_options_fingerprint = build_contract_fingerprint(solver_options)
    problem_fingerprint = build_contract_fingerprint(
        {
            "schema_version": _PROBLEM_SCHEMA_VERSION,
            "domain_id": request.domain_id,
            "event_watermark": request.event_watermark,
            "cohort_fingerprint": cohort_fingerprint,
            "optimizer_policy_fingerprint": optimizer_fingerprint,
            "decision_learning_policy_fingerprint": full_fingerprint,
            "baseline_policy_fingerprint": first.baseline_policy_fingerprint,
            "ranking_contract_fingerprint": first.ranking_contract_fingerprint,
            "embedding_model": first.embedding_model,
            "embedding_contract_fingerprint": first.embedding_contract_fingerprint,
            "embedding_dimension": first.embedding_dimension,
            "learned_alpha": optimizer["learned_alpha"],
            "preference_margin": optimizer["preference_margin"],
            "preference_regularization": optimizer["preference_regularization"],
            "preference_vector_norm_bound": optimizer["preference_vector_norm_bound"],
            "solver_options_fingerprint": solver_options_fingerprint,
            "episodes": episode_payloads,
        }
    )
    tolerance = optimizer["numeric_tolerances"]["numeric_equivalence_absolute"]
    zero_count, nonzero_count, unique_count, span = _direction_diagnostics(edges, tolerance)
    diagnostics = InverseOptimizationDiagnostics(
        episode_count=len(ordered_episodes),
        edge_count=len(edges),
        evidence_weight_sum=math.fsum(edge.weight for edge in edges),
        zero_direction_count=zero_count,
        nonzero_direction_count=nonzero_count,
        unique_direction_count=unique_count,
        direction_span_status=span,
    )
    return _PreparedProblem(
        request=request,
        policy=policy,
        decision_learning_policy_fingerprint=full_fingerprint,
        optimizer_policy_fingerprint=optimizer_fingerprint,
        cohort_fingerprint=cohort_fingerprint,
        edge_set_fingerprint=edge_set_fingerprint,
        problem_fingerprint=problem_fingerprint,
        baseline_policy_fingerprint=first.baseline_policy_fingerprint,
        ranking_contract_fingerprint=first.ranking_contract_fingerprint,
        embedding_model=first.embedding_model,
        embedding_contract_fingerprint=first.embedding_contract_fingerprint,
        embedding_dimension=first.embedding_dimension,
        solver_options_fingerprint=solver_options_fingerprint,
        compiler_results=tuple(compiler_results),
        alternatives_by_episode=tuple(alternatives_by_episode),
        edges=edges,
        diagnostics=diagnostics,
    )


def _result_from_prepared(
    prepared: _PreparedProblem,
    *,
    status: str,
    candidate_vector: tuple[float, ...] | None = None,
    objective_value: float | None = None,
    recomputed_objective: float | None = None,
    max_violation: float | None = None,
    vector_norm: float | None = None,
    vector_norm_residual: float | None = None,
    raw_solver_status: str | None = None,
    solver_version: str | None = None,
    error_code: str | None = None,
    solver_seconds: float | None = None,
) -> InverseOptimizationResult:
    diagnostics = dataclasses.replace(
        prepared.diagnostics,
        error_code=error_code,
        solver_seconds=solver_seconds,
    )
    optimizer = prepared.policy["inverse_optimization"]
    return InverseOptimizationResult(
        schema_version=_RESULT_SCHEMA_VERSION,
        status=status,
        domain_id=prepared.request.domain_id,
        event_watermark=prepared.request.event_watermark,
        cohort_fingerprint=prepared.cohort_fingerprint,
        edge_set_fingerprint=prepared.edge_set_fingerprint,
        optimizer_policy_fingerprint=prepared.optimizer_policy_fingerprint,
        decision_learning_policy_fingerprint=prepared.decision_learning_policy_fingerprint,
        problem_fingerprint=prepared.problem_fingerprint,
        candidate_preference_vector=candidate_vector,
        objective_value=objective_value,
        independently_recomputed_objective=recomputed_objective,
        max_preference_violation=max_violation,
        preference_vector_norm=vector_norm,
        vector_norm_residual=vector_norm_residual,
        embedding_model=prepared.embedding_model,
        embedding_dimension=prepared.embedding_dimension,
        embedding_contract_fingerprint=prepared.embedding_contract_fingerprint,
        learned_alpha=optimizer["learned_alpha"],
        solver_name=optimizer["solver"]["name"],
        solver_version=solver_version,
        solver_options_fingerprint=prepared.solver_options_fingerprint,
        raw_solver_status=raw_solver_status,
        diagnostics=diagnostics,
    )


def solve_preference_residual(
    request: InverseOptimizationRequest,
    decision_learning_policy: Any,
) -> InverseOptimizationResult:
    """@capability cv_system.preference-learning"""
    try:
        prepared = _prepare_problem(request, decision_learning_policy)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return _invalid_result(request, str(exc))
    if not prepared.edges:
        return _result_from_prepared(
            prepared,
            status="insufficient_evidence",
            error_code="zero_compiled_edges",
        )
    try:
        cp = importlib.import_module("cvxpy")
    except ImportError:
        return _result_from_prepared(
            prepared,
            status="solver_error",
            error_code="install fitcv[inverse-optimization]",
        )
    solver_name = prepared.policy["inverse_optimization"]["solver"]["name"]
    if solver_name not in cp.installed_solvers():
        return _result_from_prepared(
            prepared,
            status="solver_error",
            error_code="CLARABEL is not installed",
        )
    optimizer = prepared.policy["inverse_optimization"]
    preference_vector = cp.Variable(prepared.embedding_dimension)
    slack = cp.Variable(len(prepared.edges), nonneg=True)
    np = importlib.import_module("numpy")
    baseline_deltas = cp.Constant(np.asarray([edge.baseline_delta for edge in prepared.edges]))
    embedding_deltas = cp.Constant(
        np.asarray([edge.embedding_delta for edge in prepared.edges], dtype=float)
    )
    weights = cp.Constant(np.asarray([edge.weight for edge in prepared.edges]))
    score_differences = baseline_deltas + optimizer["learned_alpha"] * (
        embedding_deltas @ preference_vector
    )
    constraints = [
        score_differences >= optimizer["preference_margin"] - slack,
        cp.norm(preference_vector, 2) <= optimizer["preference_vector_norm_bound"],
    ]
    objective = cp.Minimize(
        optimizer["preference_regularization"] * cp.sum_squares(preference_vector)
        + cp.sum(cp.multiply(weights, slack))
    )
    problem = cp.Problem(objective, constraints)
    started = time.perf_counter()
    try:
        problem.solve(
            solver=cp.CLARABEL,
            max_iter=optimizer["solver"]["max_iter"],
            warm_start=False,
            verbose=False,
        )
    except Exception as exc:
        return _result_from_prepared(
            prepared,
            status="solver_error",
            raw_solver_status=str(getattr(problem, "status", "error")),
            error_code=f"solver_exception:{type(exc).__name__}",
            solver_seconds=time.perf_counter() - started,
        )
    solver_seconds = time.perf_counter() - started
    raw_status = str(problem.status or "unknown")
    if raw_status != "optimal":
        return _result_from_prepared(
            prepared,
            status="solver_error",
            raw_solver_status=raw_status,
            error_code=f"unsupported_solver_status:{raw_status}",
            solver_seconds=solver_seconds,
        )
    if preference_vector.value is None or slack.value is None or problem.value is None:
        return _result_from_prepared(
            prepared,
            status="solver_error",
            raw_solver_status=raw_status,
            error_code="missing_solver_values",
            solver_seconds=solver_seconds,
        )
    try:
        vector = tuple(float(value) for value in preference_vector.value)
        solver_slacks = tuple(float(value) for value in slack.value)
        objective_value = float(problem.value)
        vector_norm = math.sqrt(math.fsum(value * value for value in vector))
        violations = tuple(
            max(
                0.0,
                optimizer["preference_margin"]
                - (
                    edge.baseline_delta
                    + optimizer["learned_alpha"]
                    * math.fsum(
                        coefficient * value
                        for coefficient, value in zip(edge.embedding_delta, vector, strict=True)
                    )
                ),
            )
            for edge in prepared.edges
        )
        recomputed_objective = (
            optimizer["preference_regularization"]
            * math.fsum(value * value for value in vector)
            + math.fsum(edge.weight * violation for edge, violation in zip(prepared.edges, violations, strict=True))
        )
    except (TypeError, ValueError, OverflowError) as exc:
        return _result_from_prepared(
            prepared,
            status="solver_error",
            raw_solver_status=raw_status,
            error_code=f"invalid_solver_values:{type(exc).__name__}",
            solver_seconds=solver_seconds,
        )
    finite_values = (*vector, *solver_slacks, objective_value, vector_norm, recomputed_objective)
    if not all(math.isfinite(value) for value in finite_values):
        return _result_from_prepared(
            prepared,
            status="solver_error",
            raw_solver_status=raw_status,
            error_code="nonfinite_solver_values",
            solver_seconds=solver_seconds,
        )
    feasibility_tolerance = optimizer["numeric_tolerances"]["feasibility_absolute"]
    equivalence_tolerance = optimizer["numeric_tolerances"]["numeric_equivalence_absolute"]
    vector_norm_residual = max(0.0, vector_norm - optimizer["preference_vector_norm_bound"])
    slack_residual = max(
        (required - actual for required, actual in zip(violations, solver_slacks, strict=True)),
        default=0.0,
    )
    objective_delta = abs(objective_value - recomputed_objective)
    objective_limit = equivalence_tolerance * max(1.0, abs(objective_value))
    if (
        len(vector) != prepared.embedding_dimension
        or vector_norm_residual > feasibility_tolerance
        or slack_residual > feasibility_tolerance
        or objective_delta > objective_limit
    ):
        return _result_from_prepared(
            prepared,
            status="solver_error",
            raw_solver_status=raw_status,
            objective_value=objective_value,
            recomputed_objective=recomputed_objective,
            max_violation=max(violations, default=0.0),
            vector_norm=vector_norm,
            vector_norm_residual=vector_norm_residual,
            error_code="postsolve_validation_failed",
            solver_seconds=solver_seconds,
        )
    try:
        solver_version = importlib.metadata.version("clarabel")
    except importlib.metadata.PackageNotFoundError:
        solver_version = None
    return _result_from_prepared(
        prepared,
        status="optimal",
        candidate_vector=vector,
        objective_value=objective_value,
        recomputed_objective=recomputed_objective,
        max_violation=max(violations, default=0.0),
        vector_norm=vector_norm,
        vector_norm_residual=vector_norm_residual,
        raw_solver_status=raw_status,
        solver_version=solver_version,
        solver_seconds=solver_seconds,
    )


def _zero_metric() -> PreferenceMetricSummary:
    return PreferenceMetricSummary(0, 0.0, None, None, 0.0, None, None)


def _alternative_maps(
    prepared: _PreparedProblem,
) -> dict[str, dict[str, DecisionAlternative]]:
    return {
        episode_id: {alternative.alternative_id: alternative for alternative in alternatives}
        for episode_id, alternatives in prepared.alternatives_by_episode
    }


def _metric_summary(
    prepared: _PreparedProblem,
    edges: tuple[_PreparedEdge, ...],
    vector: tuple[float, ...],
) -> PreferenceMetricSummary:
    if not edges:
        return _zero_metric()
    optimizer = prepared.policy["inverse_optimization"]
    alpha = optimizer["learned_alpha"]
    margin = optimizer["preference_margin"]
    tolerance = optimizer["numeric_tolerances"]["feasibility_absolute"]
    agreements = 0
    satisfied = 0
    weighted_regret = 0.0
    for edge in edges:
        difference = edge.baseline_delta + alpha * math.fsum(
            coefficient * value
            for coefficient, value in zip(edge.embedding_delta, vector, strict=True)
        )
        agreements += difference > 0.0
        satisfied += difference + tolerance >= margin
        weighted_regret += edge.weight * max(0.0, margin - difference)
    alternative_maps = _alternative_maps(prepared)
    episode_ids = sorted({edge.episode_id for edge in edges})
    clipping_count = 0
    alternative_count = 0
    changed_rank_count = 0
    for episode_id in episode_ids:
        alternatives = tuple(alternative_maps[episode_id].values())
        scored = {
            alternative.alternative_id: alternative.baseline_fit
            + alpha
            * math.fsum(
                coefficient * value
                for coefficient, value in zip(
                    _embedding(alternative, prepared.embedding_dimension), vector, strict=True
                )
            )
            for alternative in alternatives
        }
        clipping_count += sum(not 0.0 <= score <= 1.0 for score in scored.values())
        alternative_count += len(alternatives)
        baseline_order = sorted(
            alternatives,
            key=lambda alternative: (-alternative.baseline_fit, alternative.alternative_id),
        )
        learned_order = sorted(
            alternatives,
            key=lambda alternative: (-scored[alternative.alternative_id], alternative.alternative_id),
        )
        baseline_ranks = {alternative.alternative_id: index for index, alternative in enumerate(baseline_order)}
        changed_rank_count += sum(
            baseline_ranks[alternative.alternative_id] != index
            for index, alternative in enumerate(learned_order)
        )
    pair_count = len(edges)
    return PreferenceMetricSummary(
        pair_count=pair_count,
        evidence_weight_sum=math.fsum(edge.weight for edge in edges),
        pair_agreement_rate=agreements / pair_count,
        margin_satisfaction_rate=satisfied / pair_count,
        weighted_regret=weighted_regret,
        clipping_frequency=clipping_count / alternative_count if alternative_count else None,
        rank_change_fraction=changed_rank_count / alternative_count if alternative_count else None,
    )


def _vector_stability(
    left: tuple[float, ...],
    right: tuple[float, ...],
) -> float:
    left_norm = math.sqrt(math.fsum(value * value for value in left))
    right_norm = math.sqrt(math.fsum(value * value for value in right))
    if left_norm == 0.0 and right_norm == 0.0:
        return 1.0
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return math.fsum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)


def _aggregate_metrics(metrics: tuple[PreferenceMetricSummary, ...]) -> PreferenceMetricSummary:
    if not metrics:
        return _zero_metric()
    pair_count = sum(metric.pair_count for metric in metrics)
    evidence_weight_sum = math.fsum(metric.evidence_weight_sum for metric in metrics)
    if pair_count == 0:
        return _zero_metric()
    agreement_count = math.fsum(
        (metric.pair_agreement_rate or 0.0) * metric.pair_count for metric in metrics
    )
    satisfaction_count = math.fsum(
        (metric.margin_satisfaction_rate or 0.0) * metric.pair_count for metric in metrics
    )
    clipping = tuple(metric.clipping_frequency for metric in metrics if metric.clipping_frequency is not None)
    rank_change = tuple(metric.rank_change_fraction for metric in metrics if metric.rank_change_fraction is not None)
    return PreferenceMetricSummary(
        pair_count=pair_count,
        evidence_weight_sum=evidence_weight_sum,
        pair_agreement_rate=agreement_count / pair_count,
        margin_satisfaction_rate=satisfaction_count / pair_count,
        weighted_regret=math.fsum(metric.weighted_regret for metric in metrics),
        clipping_frequency=math.fsum(clipping) / len(clipping) if clipping else None,
        rank_change_fraction=math.fsum(rank_change) / len(rank_change) if rank_change else None,
    )


def _count_pairs(values: Iterable[str | int]) -> tuple[tuple[str, int], ...]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value) if value not in (None, "") else "unknown"
        counts[key] = counts.get(key, 0) + 1
    return tuple(sorted(counts.items()))


def _coverage(prepared: _PreparedProblem) -> PreferenceCoverage:
    contexts = {
        item.episode.episode_id: item.evaluation_context
        for item in prepared.request.episodes
        if item.evaluation_context is not None
    }
    alternative_maps = _alternative_maps(prepared)
    labels: list[str] = []
    locations: list[str] = []
    languages: list[str] = []
    episode_ids = {edge.episode_id for edge in prepared.edges}
    for episode_id in sorted(episode_ids):
        context = contexts.get(episode_id)
        slices = {
            item.alternative_id: item
            for item in context.alternative_slices
        } if context is not None else {}
        for alternative in alternative_maps[episode_id].values():
            labels.append(alternative.baseline_fit_label)
            evaluation_slice = slices.get(alternative.alternative_id)
            locations.append(
                evaluation_slice.location_bucket
                if evaluation_slice is not None and evaluation_slice.location_bucket
                else "unknown"
            )
            languages.append(
                evaluation_slice.language_bucket
                if evaluation_slice is not None and evaluation_slice.language_bucket
                else "unknown"
            )
    return PreferenceCoverage(
        baseline_labels=_count_pairs(labels),
        rating_gaps=_count_pairs(edge.rating_gap for edge in prepared.edges),
        locations=_count_pairs(locations),
        languages=_count_pairs(languages),
    )


def _retrieval_audit(prepared: _PreparedProblem) -> RetrievalAuditSummary:
    audits = tuple(
        item.evaluation_context.retrieval_audit
        for item in prepared.request.episodes
        if item.evaluation_context is not None
        and item.evaluation_context.retrieval_audit is not None
    )
    if not audits:
        return RetrievalAuditSummary("not_available", None, 0, ())
    if any(audit.relevance_labels_available for audit in audits):
        raise ValueError("Phase 6 retrieval audit does not accept relevance labels")
    return RetrievalAuditSummary(
        status="unlabeled_inspection_only",
        recall=None,
        sample_count=sum(audit.sample_count for audit in audits),
        audit_fingerprints=tuple(sorted(audit.audit_fingerprint for audit in audits)),
    )


def _parent_status(
    prepared: _PreparedProblem,
    parent: CompatibleParentReference | None,
) -> str:
    if parent is None:
        return "not_provided"
    optimizer = prepared.policy["inverse_optimization"]
    vector_norm = math.sqrt(math.fsum(value * value for value in parent.preference_vector))
    compatible = (
        parent.parent_kind in {"zero_residual", "learned"}
        and parent.domain_id == prepared.request.domain_id
        and bool(parent.parent_ref)
        and parent.baseline_policy_fingerprint == prepared.baseline_policy_fingerprint
        and parent.ranking_contract_fingerprint == prepared.ranking_contract_fingerprint
        and parent.embedding_contract_fingerprint == prepared.embedding_contract_fingerprint
        and parent.embedding_dimension == prepared.embedding_dimension
        and len(parent.preference_vector) == prepared.embedding_dimension
        and all(math.isfinite(value) for value in parent.preference_vector)
        and vector_norm <= optimizer["preference_vector_norm_bound"]
        + optimizer["numeric_tolerances"]["feasibility_absolute"]
        and (parent.parent_kind != "zero_residual" or vector_norm == 0.0)
        and abs(parent.learned_alpha - optimizer["learned_alpha"])
        <= optimizer["numeric_tolerances"]["numeric_equivalence_absolute"]
    )
    return "compatible" if compatible else "incompatible"


def _evaluation_error(
    *,
    status: str,
    evaluation_version: str,
    cohort_fingerprint: str | None,
    full_problem_fingerprint: str | None,
    parent_status: str,
) -> PreferenceEvaluationResult:
    return PreferenceEvaluationResult(
        schema_version=_EVALUATION_RESULT_SCHEMA_VERSION,
        status=status,
        evaluation_version=evaluation_version,
        evaluation_mode="none",
        cohort_fingerprint=cohort_fingerprint,
        full_problem_fingerprint=full_problem_fingerprint,
        parent_comparison_status=parent_status,
        fold_results=(),
        aggregate_metrics=None,
        coverage=PreferenceCoverage((), (), (), ()),
        retrieval_audit=RetrievalAuditSummary("not_available", None, 0, ()),
        evaluation_fingerprint=None,
    )


def evaluate_preference_residual(
    request: InverseOptimizationRequest,
    full_result: InverseOptimizationResult,
    decision_learning_policy: Any,
    parent_reference: CompatibleParentReference | None = None,
) -> PreferenceEvaluationResult:
    """@capability cv_system.preference-learning"""
    try:
        prepared = _prepare_problem(request, decision_learning_policy)
        audit = _retrieval_audit(prepared)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return _evaluation_error(
            status="invalid_input",
            evaluation_version="unknown",
            cohort_fingerprint=None,
            full_problem_fingerprint=full_result.problem_fingerprint,
            parent_status="not_provided" if parent_reference is None else "incompatible",
        )
    optimizer = prepared.policy["inverse_optimization"]
    evaluation_version = optimizer["evaluation"]["evaluation_version"]
    parent_status = _parent_status(prepared, parent_reference)
    if (
        full_result.problem_fingerprint != prepared.problem_fingerprint
        or full_result.cohort_fingerprint != prepared.cohort_fingerprint
    ):
        return _evaluation_error(
            status="invalid_input",
            evaluation_version=evaluation_version,
            cohort_fingerprint=prepared.cohort_fingerprint,
            full_problem_fingerprint=full_result.problem_fingerprint,
            parent_status=parent_status,
        )
    if full_result.status == "solver_error":
        return _evaluation_error(
            status="solver_error",
            evaluation_version=evaluation_version,
            cohort_fingerprint=prepared.cohort_fingerprint,
            full_problem_fingerprint=prepared.problem_fingerprint,
            parent_status=parent_status,
        )
    episode_ids = sorted({edge.episode_id for edge in prepared.edges})
    if len(episode_ids) < 2 or full_result.candidate_preference_vector is None:
        return _evaluation_error(
            status="insufficient_evidence",
            evaluation_version=evaluation_version,
            cohort_fingerprint=prepared.cohort_fingerprint,
            full_problem_fingerprint=prepared.problem_fingerprint,
            parent_status=parent_status,
        )
    leave_one_out_max = optimizer["evaluation"]["leave_one_episode_out_max_episodes"]
    validation_groups: tuple[tuple[str, ...], ...]
    if len(episode_ids) <= leave_one_out_max:
        evaluation_mode = "leave_one_episode_out"
        validation_groups = tuple((episode_id,) for episode_id in episode_ids)
    else:
        evaluation_mode = "grouped_k_fold"
        fold_count = optimizer["evaluation"]["grouped_fold_count"]
        ordered = sorted(
            episode_ids,
            key=lambda episode_id: hashlib.sha256(
                f"{evaluation_version}:{episode_id}".encode("utf-8")
            ).hexdigest(),
        )
        groups: list[list[str]] = [[] for _ in range(fold_count)]
        for index, episode_id in enumerate(ordered):
            groups[index % fold_count].append(episode_id)
        validation_groups = tuple(tuple(sorted(group)) for group in groups if group)
    request_by_id = {item.episode.episode_id: item for item in request.episodes}
    fold_results: list[PreferenceFoldResult] = []
    baseline_metrics: list[PreferenceMetricSummary] = []
    candidate_metrics: list[PreferenceMetricSummary] = []
    parent_metrics: list[PreferenceMetricSummary] = []
    zero_vector = tuple(0.0 for _ in range(prepared.embedding_dimension))
    for fold_index, validation_ids in enumerate(validation_groups):
        validation_set = set(validation_ids)
        train_ids = tuple(episode_id for episode_id in episode_ids if episode_id not in validation_set)
        validation_edges = tuple(edge for edge in prepared.edges if edge.episode_id in validation_set)
        baseline_metric = _metric_summary(prepared, validation_edges, zero_vector)
        baseline_metrics.append(baseline_metric)
        if not train_ids or not validation_edges:
            fold_results.append(
                PreferenceFoldResult(
                    fold_index,
                    "unevaluable",
                    train_ids,
                    validation_ids,
                    None,
                    baseline_metric,
                    None,
                    None,
                    None,
                )
            )
            continue
        train_request = InverseOptimizationRequest(
            schema_version=request.schema_version,
            domain_id=request.domain_id,
            event_watermark=request.event_watermark,
            episodes=tuple(request_by_id[episode_id] for episode_id in train_ids),
        )
        fold_result = solve_preference_residual(train_request, prepared.policy)
        candidate_metric = None
        stability = None
        if fold_result.status == "optimal" and fold_result.candidate_preference_vector is not None:
            candidate_metric = _metric_summary(
                prepared,
                validation_edges,
                fold_result.candidate_preference_vector,
            )
            candidate_metrics.append(candidate_metric)
            stability = _vector_stability(
                full_result.candidate_preference_vector,
                fold_result.candidate_preference_vector,
            )
        parent_metric = None
        if parent_status == "compatible" and parent_reference is not None:
            parent_metric = _metric_summary(prepared, validation_edges, parent_reference.preference_vector)
            parent_metrics.append(parent_metric)
        fold_results.append(
            PreferenceFoldResult(
                fold_index=fold_index,
                status="evaluated" if candidate_metric is not None else "unevaluable",
                train_episode_ids=train_ids,
                validation_episode_ids=validation_ids,
                problem_fingerprint=fold_result.problem_fingerprint,
                baseline_metrics=baseline_metric,
                candidate_metrics=candidate_metric,
                parent_metrics=parent_metric,
                vector_stability=stability,
            )
        )
    aggregate = PreferenceAggregateMetrics(
        baseline=_aggregate_metrics(tuple(baseline_metrics)),
        candidate=_aggregate_metrics(tuple(candidate_metrics)) if candidate_metrics else None,
        parent=_aggregate_metrics(tuple(parent_metrics)) if parent_metrics else None,
    )
    coverage = _coverage(prepared)
    result_without_fingerprint = {
        "schema_version": _EVALUATION_RESULT_SCHEMA_VERSION,
        "status": "evaluated",
        "evaluation_version": evaluation_version,
        "evaluation_mode": evaluation_mode,
        "cohort_fingerprint": prepared.cohort_fingerprint,
        "full_problem_fingerprint": prepared.problem_fingerprint,
        "parent_comparison_status": parent_status,
        "fold_results": [dataclasses.asdict(fold) for fold in fold_results],
        "aggregate_metrics": dataclasses.asdict(aggregate),
        "coverage": dataclasses.asdict(coverage),
        "retrieval_audit": dataclasses.asdict(audit),
    }
    return PreferenceEvaluationResult(
        schema_version=_EVALUATION_RESULT_SCHEMA_VERSION,
        status="evaluated",
        evaluation_version=evaluation_version,
        evaluation_mode=evaluation_mode,
        cohort_fingerprint=prepared.cohort_fingerprint,
        full_problem_fingerprint=prepared.problem_fingerprint,
        parent_comparison_status=parent_status,
        fold_results=tuple(fold_results),
        aggregate_metrics=aggregate,
        coverage=coverage,
        retrieval_audit=audit,
        evaluation_fingerprint=build_contract_fingerprint(result_without_fingerprint),
    )
