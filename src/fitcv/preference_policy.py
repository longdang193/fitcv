"""@meta
name: preference_policy
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.preference-learning
  - cv_system.ranking-policy-lifecycle
responsibility:
  - Validate solver-free preference policy payloads and project personalized scores.
inputs:
  - Runtime ranking contracts, preference vectors, and normalized embeddings
outputs:
  - Deterministic policy identities, resolved policies, and score projections
lifecycle:
  - status: active
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from collections.abc import Callable
from typing import Any, Literal

from fitcv.shortlist_runtime import build_contract_fingerprint

ResolutionStatus = Literal[
    "active",
    "zero_residual_no_active",
    "zero_residual_incompatible",
    "zero_residual_invalid",
    "zero_residual_unavailable",
]

_SNAPSHOT_ENVELOPE_FIELDS = frozenset(
    {
        "policy_snapshot_id",
        "payload_fingerprint",
        "status",
        "activated_at",
        "created_at",
        "updated_at",
    }
)
_TRAINING_ENVELOPE_FIELDS = frozenset({"training_run_id", "created_at", "updated_at"})


def _text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} must be nonempty")
    return text


def _finite(value: Any, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be finite") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def _content(payload: dict[str, Any], excluded: frozenset[str]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key not in excluded}


def build_policy_snapshot_identity(payload: dict[str, Any]) -> tuple[str, str]:
    fingerprint = build_contract_fingerprint(_content(payload, _SNAPSHOT_ENVELOPE_FIELDS))
    return fingerprint, f"rps_{fingerprint}"


def build_training_run_identity(payload: dict[str, Any]) -> str:
    fingerprint = build_contract_fingerprint(_content(payload, _TRAINING_ENVELOPE_FIELDS))
    return f"itr_{fingerprint}"


def preference_vector_fingerprint(vector: tuple[float, ...]) -> str:
    return str(build_contract_fingerprint({"preference_vector": list(vector)}))


@dataclass(frozen=True)
class PreferenceRuntimeContract:
    schema_version: str
    domain_id: str
    baseline_policy_fingerprint: str
    ranking_contract_fingerprint: str
    embedding_model: str
    embedding_dimension: int
    embedding_contract_fingerprint: str
    learned_alpha: float
    preference_vector_norm_bound: float
    runtime_contract_fingerprint: str

    @classmethod
    def build(
        cls,
        *,
        domain_id: str,
        baseline_policy_fingerprint: str,
        ranking_contract_fingerprint: str,
        embedding_model: str,
        embedding_dimension: int,
        embedding_contract_fingerprint: str,
        learned_alpha: float,
        preference_vector_norm_bound: float,
    ) -> "PreferenceRuntimeContract":
        if isinstance(embedding_dimension, bool) or embedding_dimension <= 0:
            raise ValueError("embedding_dimension must be positive")
        alpha = _finite(learned_alpha, "learned_alpha")
        norm_bound = _finite(preference_vector_norm_bound, "preference_vector_norm_bound")
        if not 0.0 < alpha <= 0.25:
            raise ValueError("learned_alpha must be within (0, 0.25]")
        if norm_bound <= 0.0:
            raise ValueError("preference_vector_norm_bound must be positive")
        payload = {
            "schema_version": "preference_runtime_contract_v1",
            "domain_id": _text(domain_id, "domain_id"),
            "baseline_policy_fingerprint": _text(
                baseline_policy_fingerprint, "baseline_policy_fingerprint"
            ),
            "ranking_contract_fingerprint": _text(
                ranking_contract_fingerprint, "ranking_contract_fingerprint"
            ),
            "embedding_model": _text(embedding_model, "embedding_model"),
            "embedding_dimension": embedding_dimension,
            "embedding_contract_fingerprint": _text(
                embedding_contract_fingerprint, "embedding_contract_fingerprint"
            ),
            "learned_alpha": alpha,
            "preference_vector_norm_bound": norm_bound,
        }
        return cls(
            schema_version="preference_runtime_contract_v1",
            domain_id=str(payload["domain_id"]),
            baseline_policy_fingerprint=str(payload["baseline_policy_fingerprint"]),
            ranking_contract_fingerprint=str(payload["ranking_contract_fingerprint"]),
            embedding_model=str(payload["embedding_model"]),
            embedding_dimension=embedding_dimension,
            embedding_contract_fingerprint=str(payload["embedding_contract_fingerprint"]),
            learned_alpha=alpha,
            preference_vector_norm_bound=norm_bound,
            runtime_contract_fingerprint=str(build_contract_fingerprint(payload)),
        )


@dataclass(frozen=True)
class ResolvedPreferencePolicy:
    schema_version: str
    resolution_status: ResolutionStatus
    runtime_contract: PreferenceRuntimeContract
    policy_snapshot_id: str | None
    preference_vector: tuple[float, ...]
    preference_vector_fingerprint: str
    payload_fingerprint: str | None
    diagnostic_code: str | None


@dataclass(frozen=True)
class PersonalizedScoreProjection:
    baseline_fit: float
    preference_residual: float
    personalized_rank_score: float
    personalized_display_score: float
    score_was_clipped: bool


@dataclass(frozen=True)
class PromotionDecision:
    passed: bool
    reason_code: str


_HIGHER_IS_BETTER = ("pair_agreement_rate", "margin_satisfaction_rate")
_LOWER_IS_BETTER = ("weighted_regret", "clipping_frequency")


def max_coordinate_delta(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if not left or not right:
        raise ValueError("preference vectors must be nonempty")
    if len(left) != len(right):
        raise ValueError("preference vector dimension mismatch")
    return max(
        abs(_finite(left_value, "preference_vector") - _finite(right_value, "comparator_vector"))
        for left_value, right_value in zip(left, right, strict=True)
    )


def evaluate_promotion_gate(
    *,
    candidate_metrics: dict[str, Any],
    comparator_metrics: tuple[dict[str, Any], ...],
    fold_stabilities: tuple[float, ...],
    tolerance: float,
    minimum_fold_vector_stability: float,
) -> PromotionDecision:
    required = _HIGHER_IS_BETTER + _LOWER_IS_BETTER
    if any(candidate_metrics.get(key) is None for key in required):
        return PromotionDecision(False, "missing_metric")
    if not comparator_metrics or any(
        comparator.get(key) is None for comparator in comparator_metrics for key in required
    ):
        return PromotionDecision(False, "missing_metric")
    threshold = _finite(minimum_fold_vector_stability, "minimum_fold_vector_stability")
    if not fold_stabilities or any(
        _finite(value, "fold_stability") < threshold for value in fold_stabilities
    ):
        return PromotionDecision(False, "fold_stability")
    epsilon = abs(_finite(tolerance, "tolerance"))
    candidate = {key: _finite(candidate_metrics[key], key) for key in required}
    strict_gain = False
    for comparator_payload in comparator_metrics:
        comparator = {key: _finite(comparator_payload[key], key) for key in required}
        if any(candidate[key] < comparator[key] - epsilon for key in _HIGHER_IS_BETTER):
            return PromotionDecision(False, "metric_regression")
        if any(candidate[key] > comparator[key] + epsilon for key in _LOWER_IS_BETTER):
            return PromotionDecision(False, "metric_regression")
        strict_gain = strict_gain or any(
            candidate[key] > comparator[key] + epsilon for key in _HIGHER_IS_BETTER
        ) or any(candidate[key] < comparator[key] - epsilon for key in _LOWER_IS_BETTER)
    return PromotionDecision(strict_gain, "passed" if strict_gain else "no_strict_gain")


def resolve_zero_residual_policy(
    runtime_contract: PreferenceRuntimeContract,
    *,
    status: ResolutionStatus,
    diagnostic_code: str | None = None,
) -> ResolvedPreferencePolicy:
    if status == "active":
        raise ValueError("zero residual status cannot be active")
    vector = (0.0,) * runtime_contract.embedding_dimension
    return ResolvedPreferencePolicy(
        schema_version="resolved_preference_policy_v1",
        resolution_status=status,
        runtime_contract=runtime_contract,
        policy_snapshot_id=None,
        preference_vector=vector,
        preference_vector_fingerprint=preference_vector_fingerprint(vector),
        payload_fingerprint=None,
        diagnostic_code=diagnostic_code,
    )


def resolved_preference_policy_from_snapshot(
    runtime_contract: PreferenceRuntimeContract,
    snapshot: dict[str, Any],
) -> ResolvedPreferencePolicy:
    if snapshot.get("status") != "active":
        raise ValueError("snapshot must be active")
    if snapshot.get("runtime_contract_fingerprint") != runtime_contract.runtime_contract_fingerprint:
        raise ValueError("snapshot runtime contract mismatch")
    raw_vector = snapshot.get("preference_vector_json")
    if not isinstance(raw_vector, list):
        raise ValueError("snapshot preference vector must be a list")
    vector = tuple(_finite(value, "preference_vector") for value in raw_vector)
    if len(vector) != runtime_contract.embedding_dimension:
        raise ValueError("snapshot preference vector dimension mismatch")
    expected_vector_fingerprint = preference_vector_fingerprint(vector)
    if snapshot.get("preference_vector_fingerprint") != expected_vector_fingerprint:
        raise ValueError("snapshot preference vector fingerprint mismatch")
    return ResolvedPreferencePolicy(
        schema_version="resolved_preference_policy_v1",
        resolution_status="active",
        runtime_contract=runtime_contract,
        policy_snapshot_id=_text(snapshot.get("policy_snapshot_id"), "policy_snapshot_id"),
        preference_vector=vector,
        preference_vector_fingerprint=expected_vector_fingerprint,
        payload_fingerprint=_text(snapshot.get("payload_fingerprint"), "payload_fingerprint"),
        diagnostic_code=None,
    )


def resolved_preference_policy_to_dict(policy: ResolvedPreferencePolicy) -> dict[str, Any]:
    return asdict(policy)


def resolved_preference_policy_from_dict(payload: dict[str, Any]) -> ResolvedPreferencePolicy:
    runtime_payload = dict(payload["runtime_contract"])
    runtime_fingerprint = runtime_payload.pop("runtime_contract_fingerprint")
    runtime_payload.pop("schema_version", None)
    runtime = PreferenceRuntimeContract.build(**runtime_payload)
    if runtime.runtime_contract_fingerprint != runtime_fingerprint:
        raise ValueError("runtime contract fingerprint mismatch")
    status = str(payload["resolution_status"])
    if status not in {
        "active",
        "zero_residual_no_active",
        "zero_residual_incompatible",
        "zero_residual_invalid",
        "zero_residual_unavailable",
    }:
        raise ValueError("unknown preference policy resolution status")
    return ResolvedPreferencePolicy(
        schema_version=str(payload["schema_version"]),
        resolution_status=status,  # type: ignore[arg-type]
        runtime_contract=runtime,
        policy_snapshot_id=payload.get("policy_snapshot_id"),
        preference_vector=tuple(float(value) for value in payload["preference_vector"]),
        preference_vector_fingerprint=str(payload["preference_vector_fingerprint"]),
        payload_fingerprint=payload.get("payload_fingerprint"),
        diagnostic_code=payload.get("diagnostic_code"),
    )


def resolve_run_preference_policy(
    *,
    ranking_rows: list[dict[str, Any]],
    config: dict[str, Any],
    existing_payload: dict[str, Any] | None = None,
    resolver: Callable[[PreferenceRuntimeContract], ResolvedPreferencePolicy] | None = None,
) -> ResolvedPreferencePolicy:
    if existing_payload:
        return resolved_preference_policy_from_dict(existing_payload)
    if not ranking_rows:
        raise ValueError("ranking rows are required to resolve preference policy")
    first = ranking_rows[0]
    embedding = first.get("normalized_embedding")
    embedding_values = embedding if isinstance(embedding, list) else []
    embedding_available = bool(embedding_values)
    policy = config["decision_learning_policy"]["inverse_optimization"]
    runtime = PreferenceRuntimeContract.build(
        domain_id=config["decision_learning_policy"]["domain_id"],
        baseline_policy_fingerprint=build_contract_fingerprint(config["ranking_policy"]),
        ranking_contract_fingerprint=str(
            first.get("ranking_contract_fingerprint")
            or build_contract_fingerprint(config["ranking_policy"])
        ),
        embedding_model=str(
            config.get("shortlist_embedding_model")
            or config.get("embedding_model")
            or "unknown"
        ),
        embedding_dimension=len(embedding_values) if embedding_available else 1,
        embedding_contract_fingerprint=str(
            first.get("embedding_contract_fingerprint") or "unavailable"
        ),
        learned_alpha=policy["learned_alpha"],
        preference_vector_norm_bound=policy["preference_vector_norm_bound"],
    )
    if not embedding_available:
        return resolve_zero_residual_policy(
            runtime,
            status="zero_residual_invalid",
            diagnostic_code="missing_embedding_contract",
        )
    if resolver is None:
        return resolve_zero_residual_policy(runtime, status="zero_residual_no_active")
    try:
        resolved = resolver(runtime)
    except Exception:
        return resolve_zero_residual_policy(
            runtime,
            status="zero_residual_unavailable",
            diagnostic_code="policy_store_unavailable",
        )
    if resolved.runtime_contract != runtime:
        return resolve_zero_residual_policy(
            runtime,
            status="zero_residual_invalid",
            diagnostic_code="runtime_contract_mismatch",
        )
    return resolved


def project_personalized_score(
    *,
    runtime_contract: PreferenceRuntimeContract,
    baseline_fit: float,
    preference_vector: tuple[float, ...],
    normalized_embedding: tuple[float, ...],
) -> PersonalizedScoreProjection:
    baseline = _finite(baseline_fit, "baseline_fit")
    if len(preference_vector) != runtime_contract.embedding_dimension:
        raise ValueError("preference vector dimension mismatch")
    if len(normalized_embedding) != runtime_contract.embedding_dimension:
        raise ValueError("embedding dimension mismatch")
    vector = tuple(_finite(value, "preference_vector") for value in preference_vector)
    embedding = tuple(_finite(value, "normalized_embedding") for value in normalized_embedding)
    vector_norm = math.sqrt(math.fsum(value * value for value in vector))
    if vector_norm > runtime_contract.preference_vector_norm_bound + 1.0e-9:
        raise ValueError("preference vector exceeds norm bound")
    embedding_norm = math.sqrt(math.fsum(value * value for value in embedding))
    if not math.isclose(embedding_norm, 1.0, rel_tol=0.0, abs_tol=1.0e-6):
        raise ValueError("normalized_embedding must have unit norm")
    residual = runtime_contract.learned_alpha * math.fsum(
        left * right for left, right in zip(vector, embedding, strict=True)
    )
    raw_score = baseline + residual
    display_score = min(1.0, max(0.0, raw_score))
    return PersonalizedScoreProjection(
        baseline_fit=baseline,
        preference_residual=residual,
        personalized_rank_score=raw_score,
        personalized_display_score=display_score,
        score_was_clipped=raw_score != display_score,
    )
