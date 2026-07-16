"""@meta
name: decision_feedback
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.decision-feedback
  - cv_system.preference-compilation
responsibility:
  - Validate ordinal decision-learning policy and immutable feedback evidence.
  - Build canonical decision episodes and reduce append-only rating events.
inputs:
  - Validated effective config, candidate profile snapshot, and scored result rows.
outputs:
  - Versioned feedback-source payloads and immutable decision records.
lifecycle:
  - status: active
"""

from __future__ import annotations

import datetime
import json
import math
from itertools import combinations
from dataclasses import dataclass
from enum import IntEnum, StrEnum
from typing import Any, Iterable, cast

from fitcv.shortlist_runtime import build_contract_fingerprint


class RatingValue(IntEnum):
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5


class RatingEventType(StrEnum):
    SET_RATING = "set_rating"
    CLEAR_RATING = "clear_rating"


@dataclass(frozen=True)
class DecisionEpisode:
    episode_id: str
    domain_id: str
    run_id: str
    preference_context_fingerprint: str
    qualification_context_fingerprint: str
    ranking_contract_fingerprint: str
    embedding_contract_fingerprint: str
    baseline_policy_fingerprint: str
    embedding_model: str
    embedding_dimension: int
    rating_scale_version: str
    candidate_set_fingerprint: str
    source_stage_artifact_fingerprint: str
    created_at: datetime.datetime


@dataclass(frozen=True)
class DecisionAlternative:
    episode_id: str
    alternative_id: str
    displayed_rank: int
    baseline_fit: float
    baseline_fit_label: str
    normalized_embedding_json: str
    embedding_vector_fingerprint: str
    source_job_url: str
    shortlist_origin: str
    created_at: datetime.datetime


@dataclass(frozen=True)
class RatingCommand:
    alternative_id: str
    event_type: RatingEventType
    rating: RatingValue | None
    rating_scale_version: str
    source_stage_artifact_fingerprint: str


@dataclass(frozen=True)
class DecisionRatingEvent:
    event_sequence: int | None
    event_id: str
    episode_id: str
    alternative_id: str
    event_type: RatingEventType
    rating: RatingValue | None
    rating_scale_version: str
    acted_by: str
    created_at: datetime.datetime

    def __post_init__(self) -> None:
        if self.event_sequence is not None and self.event_sequence <= 0:
            raise ValueError("event_sequence must be positive")
        if self.event_type is RatingEventType.SET_RATING and self.rating is None:
            raise ValueError("set_rating requires rating")
        if self.event_type is RatingEventType.CLEAR_RATING and self.rating is not None:
            raise ValueError("clear_rating requires no rating")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")


@dataclass(frozen=True)
class EffectiveRatingState:
    episode_id: str
    alternative_id: str
    rating: RatingValue | str
    source_event_id: str | None
    event_sequence: int | None


@dataclass(frozen=True)
class PreferenceEdge:
    preferred_alternative_id: str
    other_alternative_id: str
    rating_gap: int
    evidence_weight: float
    episode_bounded_weight: float
    source_event_ids: tuple[str, str]
    compiler_version: str


@dataclass(frozen=True)
class PreferenceCompilerDiagnostics:
    alternative_count: int
    rated_alternative_count: int
    unordered_pair_count: int
    omitted_unrated_pair_count: int
    omitted_equal_pair_count: int
    omitted_below_gap_pair_count: int
    emitted_edge_count: int
    raw_evidence_weight_sum: float
    episode_scale: float
    bounded_evidence_weight_sum: float


@dataclass(frozen=True)
class PreferenceCompilerResult:
    schema_version: str
    status: str
    episode_id: str
    event_watermark: int
    compiler_version: str
    compiler_policy_fingerprint: str
    decision_learning_policy_fingerprint: str
    compiler_input_fingerprint: str
    edge_set_fingerprint: str
    edges: tuple[PreferenceEdge, ...]
    diagnostics: PreferenceCompilerDiagnostics

_POLICY_KEYS = {"policy_version", "domain_id", "rating_scale", "preference_compiler"}
_COMPILER_KEYS = {"compiler_version", "minimum_rating_gap", "gap_evidence_weights", "max_episode_evidence_budget"}
_GAP_WEIGHT_KEYS = {str(value) for value in range(1, 5)}
_EXPECTED_COMPILER_VERSION = "preference-compiler-v1"
_SCALE_KEYS = {"version", "unrated_label", "labels"}
_EXPECTED_LABEL_KEYS = {str(value.value) for value in RatingValue}
_EXPECTED_POLICY_VERSION = "decision-learning-v1"
_EXPECTED_DOMAIN_ID = "ranking_v1"
_EXPECTED_SCALE_VERSION = "application-interest-v1"
_EXPECTED_UNRATED_LABEL = "unrated"
_FIT_LABELS = {"strong", "stretch", "skip"}
_SOURCE_SCHEMA_VERSION = "decision_feedback_source_v1"
_PREFERENCE_CONTEXT_VERSION = "preference_context_v1"
_QUALIFICATION_CONTEXT_VERSION = "qualification_context_v1"
_PREFERENCE_COMPILER_RESULT_SCHEMA_VERSION = "preference_compiler_result_v1"
_PREFERENCE_EDGE_SET_SCHEMA_VERSION = "preference_edge_set_v1"
_UNRATED_LABEL = "unrated"


def _required_text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} must be nonempty")
    return text


def _exact_keys(payload: dict[str, Any], expected: set[str], field: str) -> None:
    unknown = sorted(set(payload) - expected)
    missing = sorted(expected - set(payload))
    if unknown:
        raise ValueError(f"{field} contains unknown keys: {', '.join(unknown)}")
    if missing:
        raise ValueError(f"{field} missing keys: {', '.join(missing)}")


def validate_decision_learning_policy(policy: Any) -> tuple[dict[str, Any], str]:
    if not isinstance(policy, dict):
        raise ValueError("decision_learning_policy must be a mapping")
    _exact_keys(policy, _POLICY_KEYS, "decision_learning_policy")
    if _required_text(policy["policy_version"], "policy_version") != _EXPECTED_POLICY_VERSION:
        raise ValueError(f"policy_version must be {_EXPECTED_POLICY_VERSION}")
    if _required_text(policy["domain_id"], "domain_id") != _EXPECTED_DOMAIN_ID:
        raise ValueError(f"domain_id must be {_EXPECTED_DOMAIN_ID}")
    scale = policy["rating_scale"]
    if not isinstance(scale, dict):
        raise ValueError("rating_scale must be a mapping")
    _exact_keys(scale, _SCALE_KEYS, "rating_scale")
    if _required_text(scale["version"], "rating_scale.version") != _EXPECTED_SCALE_VERSION:
        raise ValueError(f"rating_scale.version must be {_EXPECTED_SCALE_VERSION}")
    if _required_text(scale["unrated_label"], "rating_scale.unrated_label").casefold() != _EXPECTED_UNRATED_LABEL:
        raise ValueError(f"rating_scale.unrated_label must be {_EXPECTED_UNRATED_LABEL}")
    labels = scale["labels"]
    if not isinstance(labels, dict):
        raise ValueError("rating_scale.labels must be a mapping")
    if set(labels) != _EXPECTED_LABEL_KEYS:
        raise ValueError("rating_scale.labels must contain exactly 1 through 5")
    normalized_labels = [_required_text(labels[key], f"rating_scale.labels.{key}").casefold() for key in sorted(labels)]
    if len(set(normalized_labels)) != len(normalized_labels):
        raise ValueError("rating_scale labels must be unique")
    compiler = policy["preference_compiler"]
    if not isinstance(compiler, dict):
        raise ValueError("preference_compiler must be a mapping")
    _exact_keys(compiler, _COMPILER_KEYS, "preference_compiler")
    compiler_version = _required_text(compiler["compiler_version"], "preference_compiler.compiler_version")
    if compiler_version != _EXPECTED_COMPILER_VERSION:
        raise ValueError(f"compiler_version must be {_EXPECTED_COMPILER_VERSION}")
    minimum_gap = compiler["minimum_rating_gap"]
    if isinstance(minimum_gap, bool) or not isinstance(minimum_gap, int) or not 1 <= minimum_gap <= 4:
        raise ValueError("minimum_rating_gap must be an integer from 1 through 4")
    raw_weights = compiler["gap_evidence_weights"]
    if not isinstance(raw_weights, dict):
        raise ValueError("gap_evidence_weights must be a mapping")
    if set(raw_weights) != _GAP_WEIGHT_KEYS:
        raise ValueError("gap_evidence_weights must contain exactly 1 through 4")
    weights: dict[str, float] = {}
    for key in sorted(raw_weights):
        value = raw_weights[key]
        if isinstance(value, bool):
            raise ValueError("gap_evidence_weights values must be finite positive numbers")
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("gap_evidence_weights values must be finite positive numbers") from exc
        if not math.isfinite(number) or number <= 0.0:
            raise ValueError("gap_evidence_weights values must be finite positive numbers")
        weights[key] = number
    if any(weights[str(key)] >= weights[str(key + 1)] for key in range(1, 4)):
        raise ValueError("gap_evidence_weights must be strictly increasing")
    budget = compiler["max_episode_evidence_budget"]
    if isinstance(budget, bool):
        raise ValueError("max_episode_evidence_budget must be finite and positive")
    try:
        normalized_budget = float(budget)
    except (TypeError, ValueError) as exc:
        raise ValueError("max_episode_evidence_budget must be finite and positive") from exc
    if not math.isfinite(normalized_budget) or normalized_budget <= 0.0:
        raise ValueError("max_episode_evidence_budget must be finite and positive")
    validated = {
        "policy_version": _EXPECTED_POLICY_VERSION,
        "domain_id": _EXPECTED_DOMAIN_ID,
        "rating_scale": {
            "version": _EXPECTED_SCALE_VERSION,
            "unrated_label": _EXPECTED_UNRATED_LABEL,
            "labels": {key: str(labels[key]).strip() for key in sorted(labels)},
        },
        "preference_compiler": {
            "compiler_version": compiler_version,
            "minimum_rating_gap": minimum_gap,
            "gap_evidence_weights": weights,
            "max_episode_evidence_budget": normalized_budget,
        },
    }
    return validated, build_contract_fingerprint(validated)


def _normalized_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({str(item).strip() for item in value if str(item).strip()}, key=str.casefold)


def _preference_context(candidate_profile: dict[str, Any], domain_id: str) -> dict[str, Any]:
    preferences = candidate_profile.get("preferences")
    if not isinstance(preferences, dict):
        preferences = {}
    return {
        "context_version": _PREFERENCE_CONTEXT_VERSION,
        "domain_id": domain_id,
        "target_role": str(preferences.get("target_role") or candidate_profile.get("target_role") or "").strip(),
        "role_families": _normalized_text_list(preferences.get("role_families") or candidate_profile.get("role_families")),
        "domains": _normalized_text_list(preferences.get("domains") or candidate_profile.get("domains")),
        "seniority_target": str(preferences.get("seniority_target") or candidate_profile.get("seniority_target") or "").strip(),
        "preferred_locations": _normalized_text_list(preferences.get("preferred_locations") or candidate_profile.get("preferred_locations")),
        "work_modes": _normalized_text_list(preferences.get("work_modes") or candidate_profile.get("work_modes")),
    }


def _normalized_embedding(value: Any) -> list[float]:
    if not isinstance(value, list) or not value:
        raise ValueError("normalized_embedding must be a nonempty list")
    vector: list[float] = []
    for item in value:
        if isinstance(item, bool):
            raise ValueError("normalized_embedding must contain finite numbers")
        try:
            number = float(item)
        except (TypeError, ValueError) as exc:
            raise ValueError("normalized_embedding must contain finite numbers") from exc
        if not math.isfinite(number):
            raise ValueError("normalized_embedding must contain finite numbers")
        vector.append(number)
    norm = math.sqrt(sum(number * number for number in vector))
    if norm <= 0.0:
        raise ValueError("normalized_embedding must be nonzero")
    if not math.isclose(norm, 1.0, rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError("normalized_embedding must have unit norm")
    return vector


def _candidate_set_fingerprint(rows: Iterable[dict[str, Any]]) -> str:
    payload = [
        {
            "alternative_id": str(row["alternative_id"]),
            "displayed_rank": int(row["displayed_rank"]),
            "baseline_fit": float(row["baseline_fit"]),
            "baseline_fit_label": str(row["baseline_fit_label"]),
            "embedding_vector_fingerprint": str(row["embedding_vector_fingerprint"]),
            "shortlist_origin": str(row["shortlist_origin"]),
        }
        for row in sorted(rows, key=lambda item: int(item["displayed_rank"]))
    ]
    return str(build_contract_fingerprint({"alternatives": payload}))


def _compiler_policy_fingerprint(policy: dict[str, Any]) -> str:
    return str(build_contract_fingerprint(policy["preference_compiler"]))


def build_decision_feedback_source(
    *,
    run_id: str,
    candidate_profile: dict[str, Any],
    config: dict[str, Any],
    scoring_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    run_id = _required_text(run_id, "run_id")
    policy, _ = validate_decision_learning_policy(config.get("decision_learning_policy"))
    ranking_policy = config.get("ranking_policy")
    if not isinstance(ranking_policy, dict):
        raise ValueError("ranking_policy must be a mapping")
    ranking_contract = config.get("ranking_contract")
    if not isinstance(ranking_contract, dict):
        raise ValueError("ranking_contract must be a mapping")
    ranking_contract_fingerprint = _required_text(
        ranking_contract.get("ranking_contract_fingerprint"), "ranking_contract_fingerprint"
    )
    preference_context = _preference_context(candidate_profile, policy["domain_id"])
    preference_context_fingerprint = build_contract_fingerprint(preference_context)
    qualification_context = {
        "context_version": _QUALIFICATION_CONTEXT_VERSION,
        "candidate_profile": candidate_profile,
    }
    qualification_context_fingerprint = build_contract_fingerprint(qualification_context)
    baseline_policy_fingerprint = build_contract_fingerprint(ranking_policy)

    eligible: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    embedding_contracts: set[str] = set()
    dimensions: set[int] = set()
    for row in scoring_rows:
        if str(row.get("shortlist_origin") or "").strip() != "vector_search":
            continue
        alternative_id = str(row.get("raw_job_fingerprint") or "").strip()
        if not alternative_id:
            continue
        if alternative_id in seen_ids:
            raise ValueError(f"duplicate alternative_id: {alternative_id}")
        scores = row.get("scores")
        score_fields: dict[str, Any] = scores if isinstance(scores, dict) else row
        if score_fields.get("baseline_fit") is None or not str(score_fields.get("baseline_fit_label") or "").strip():
            continue
        try:
            baseline_fit = float(score_fields["baseline_fit"])
        except (TypeError, ValueError) as exc:
            raise ValueError("baseline_fit must be finite within 0 and 1") from exc
        baseline_fit_label = str(score_fields["baseline_fit_label"]).strip().lower()
        if not math.isfinite(baseline_fit) or not 0.0 <= baseline_fit <= 1.0:
            raise ValueError("baseline_fit must be finite within 0 and 1")
        if baseline_fit_label not in _FIT_LABELS:
            raise ValueError("baseline_fit_label must be strong, stretch, or skip")
        try:
            vector = _normalized_embedding(row.get("normalized_embedding"))
        except ValueError:
            continue
        vector_fingerprint = str(row.get("embedding_vector_fingerprint") or "").strip()
        expected_vector_fingerprint = build_contract_fingerprint({"normalized_embedding": vector})
        if vector_fingerprint and vector_fingerprint != expected_vector_fingerprint:
            continue
        embedding_contract = _required_text(
            row.get("embedding_contract_fingerprint"), "embedding_contract_fingerprint"
        )
        embedding_contracts.add(embedding_contract)
        dimensions.add(len(vector))
        seen_ids.add(alternative_id)
        eligible.append(
            {
                "alternative_id": alternative_id,
                "baseline_fit": baseline_fit,
                "baseline_fit_label": baseline_fit_label,
                "normalized_embedding": vector,
                "embedding_vector_fingerprint": expected_vector_fingerprint,
                "source_job_url": str(row.get("source_job_url") or row.get("job_url") or "").strip(),
                "shortlist_origin": "vector_search",
            }
        )
    if not eligible:
        raise ValueError("decision feedback source requires at least one evidence-complete alternative")
    if len(embedding_contracts) != 1 or len(dimensions) != 1:
        raise ValueError("alternatives must share one embedding contract and dimension")
    eligible.sort(key=lambda row: (-float(row["baseline_fit"]), str(row["alternative_id"])))
    alternatives = [{**row, "displayed_rank": index + 1} for index, row in enumerate(eligible)]
    candidate_set_fingerprint = _candidate_set_fingerprint(alternatives)
    source_payload = {
        "schema_version": _SOURCE_SCHEMA_VERSION,
        "domain_id": policy["domain_id"],
        "run_id": run_id,
        "preference_context_version": _PREFERENCE_CONTEXT_VERSION,
        "preference_context_fingerprint": preference_context_fingerprint,
        "qualification_context_version": _QUALIFICATION_CONTEXT_VERSION,
        "qualification_context_fingerprint": qualification_context_fingerprint,
        "ranking_contract_fingerprint": ranking_contract_fingerprint,
        "baseline_policy_fingerprint": baseline_policy_fingerprint,
        "embedding_model": str(config.get("embedding_model") or config.get("shortlist_embedding_model") or "").strip(),
        "embedding_dimension": next(iter(dimensions)),
        "embedding_contract_fingerprint": next(iter(embedding_contracts)),
        "rating_scale_version": policy["rating_scale"]["version"],
        "candidate_set_fingerprint": candidate_set_fingerprint,
        "alternatives": alternatives,
    }
    fingerprint_payload = {
        **source_payload,
        "alternatives": [
            {key: value for key, value in row.items() if key != "source_job_url"}
            for row in alternatives
        ],
    }
    source_payload["source_stage_artifact_fingerprint"] = build_contract_fingerprint(fingerprint_payload)
    return source_payload


def build_episode_records(
    source: dict[str, Any],
    *,
    created_at: datetime.datetime | None = None,
) -> tuple[DecisionEpisode, tuple[DecisionAlternative, ...]]:
    if source.get("schema_version") != _SOURCE_SCHEMA_VERSION:
        raise ValueError("unsupported decision feedback source")
    source_alternatives = source.get("alternatives")
    if not isinstance(source_alternatives, list) or not source_alternatives:
        raise ValueError("episode requires alternatives")
    validated_alternatives: list[dict[str, Any]] = []
    seen_alternative_ids: set[str] = set()
    seen_ranks: set[int] = set()
    for row in source_alternatives:
        if not isinstance(row, dict):
            raise ValueError("decision feedback alternative must be a mapping")
        alternative_id = _required_text(row.get("alternative_id"), "alternative_id")
        displayed_rank = int(row.get("displayed_rank") or 0)
        if alternative_id in seen_alternative_ids or displayed_rank <= 0 or displayed_rank in seen_ranks:
            raise ValueError("decision feedback alternatives require unique IDs and ranks")
        vector = _normalized_embedding(row.get("normalized_embedding"))
        vector_fingerprint = build_contract_fingerprint({"normalized_embedding": vector})
        if str(row.get("embedding_vector_fingerprint") or "") != vector_fingerprint:
            raise ValueError("embedding_vector_fingerprint does not match normalized_embedding")
        try:
            baseline_fit = float(row["baseline_fit"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid decision feedback baseline evidence") from exc
        baseline_fit_label = str(row.get("baseline_fit_label") or "").strip().lower()
        if not math.isfinite(baseline_fit) or not 0.0 <= baseline_fit <= 1.0 or baseline_fit_label not in _FIT_LABELS:
            raise ValueError("invalid decision feedback baseline evidence")
        seen_alternative_ids.add(alternative_id)
        seen_ranks.add(displayed_rank)
        validated_alternatives.append(
            {
                **row,
                "alternative_id": alternative_id,
                "displayed_rank": displayed_rank,
                "baseline_fit": baseline_fit,
                "baseline_fit_label": baseline_fit_label,
                "normalized_embedding": vector,
                "embedding_vector_fingerprint": vector_fingerprint,
            }
        )
    validated_alternatives.sort(key=lambda row: (int(row["displayed_rank"]), str(row["alternative_id"])))
    if [int(row["displayed_rank"]) for row in validated_alternatives] != list(range(1, len(validated_alternatives) + 1)):
        raise ValueError("decision feedback displayed ranks must be contiguous")
    expected_candidate_fingerprint = _candidate_set_fingerprint(validated_alternatives)
    if str(source.get("candidate_set_fingerprint") or "") != expected_candidate_fingerprint:
        raise ValueError("candidate_set_fingerprint does not match alternatives")
    source_fingerprint_payload = {
        key: value
        for key, value in source.items()
        if key != "source_stage_artifact_fingerprint"
    }
    source_fingerprint_payload["alternatives"] = [
        {key: value for key, value in row.items() if key != "source_job_url"}
        for row in validated_alternatives
    ]
    expected_source_fingerprint = build_contract_fingerprint(source_fingerprint_payload)
    if str(source.get("source_stage_artifact_fingerprint") or "") != expected_source_fingerprint:
        raise ValueError("source_stage_artifact_fingerprint does not match source")
    if any(len(row["normalized_embedding"]) != int(source.get("embedding_dimension") or 0) for row in validated_alternatives):
        raise ValueError("embedding dimension conflicts with source")
    timestamp = created_at or datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
    if timestamp.tzinfo is None:
        raise ValueError("created_at must be timezone-aware")
    identity = {
        key: source.get(key)
        for key in (
            "domain_id",
            "run_id",
            "preference_context_fingerprint",
            "qualification_context_fingerprint",
            "ranking_contract_fingerprint",
            "baseline_policy_fingerprint",
            "embedding_contract_fingerprint",
            "rating_scale_version",
            "candidate_set_fingerprint",
            "source_stage_artifact_fingerprint",
        )
    }
    for key, value in identity.items():
        _required_text(value, key)
    episode_id = build_contract_fingerprint(identity)
    episode = DecisionEpisode(
        episode_id=episode_id,
        domain_id=str(source["domain_id"]),
        run_id=str(source["run_id"]),
        preference_context_fingerprint=str(source["preference_context_fingerprint"]),
        qualification_context_fingerprint=str(source["qualification_context_fingerprint"]),
        ranking_contract_fingerprint=str(source["ranking_contract_fingerprint"]),
        embedding_contract_fingerprint=str(source["embedding_contract_fingerprint"]),
        baseline_policy_fingerprint=str(source["baseline_policy_fingerprint"]),
        embedding_model=_required_text(source.get("embedding_model"), "embedding_model"),
        embedding_dimension=int(source["embedding_dimension"]),
        rating_scale_version=str(source["rating_scale_version"]),
        candidate_set_fingerprint=str(source["candidate_set_fingerprint"]),
        source_stage_artifact_fingerprint=str(source["source_stage_artifact_fingerprint"]),
        created_at=timestamp,
    )
    alternatives = tuple(
        DecisionAlternative(
            episode_id=episode_id,
            alternative_id=_required_text(row.get("alternative_id"), "alternative_id"),
            displayed_rank=int(row["displayed_rank"]),
            baseline_fit=float(row["baseline_fit"]),
            baseline_fit_label=str(row["baseline_fit_label"]),
            normalized_embedding_json=json.dumps(row["normalized_embedding"], separators=(",", ":")),
            embedding_vector_fingerprint=str(row["embedding_vector_fingerprint"]),
            source_job_url=str(row.get("source_job_url") or ""),
            shortlist_origin=str(row["shortlist_origin"]),
            created_at=timestamp,
        )
        for row in validated_alternatives
    )
    if not alternatives:
        raise ValueError("episode requires alternatives")
    return episode, alternatives


def reduce_rating_event_states(
    events: Iterable[DecisionRatingEvent],
    *,
    event_watermark: int | None = None,
) -> dict[tuple[str, str], EffectiveRatingState]:
    if event_watermark is not None and (isinstance(event_watermark, bool) or event_watermark < 0):
        raise ValueError("event_watermark must be nonnegative")
    latest: dict[tuple[str, str], DecisionRatingEvent] = {}
    seen_event_ids: set[str] = set()
    seen_sequences: set[int] = set()
    for event in events:
        if event.event_sequence is None:
            raise ValueError("persisted event requires event_sequence")
        sequence = int(event.event_sequence)
        if event_watermark is not None and sequence > event_watermark:
            continue
        if event.event_id in seen_event_ids:
            raise ValueError("duplicate event_id")
        if sequence in seen_sequences:
            raise ValueError("duplicate event_sequence")
        seen_event_ids.add(event.event_id)
        seen_sequences.add(sequence)
        key = (event.episode_id, event.alternative_id)
        current = latest.get(key)
        if current is None or sequence > int(current.event_sequence or 0):
            latest[key] = event
    return {
        key: EffectiveRatingState(
            episode_id=event.episode_id,
            alternative_id=event.alternative_id,
            rating=cast(RatingValue, event.rating) if event.event_type is RatingEventType.SET_RATING else "unrated",
            source_event_id=event.event_id,
            event_sequence=event.event_sequence,
        )
        for key, event in latest.items()
    }


def reduce_rating_events(
    events: Iterable[DecisionRatingEvent],
) -> dict[tuple[str, str], RatingValue | str]:
    return {key: state.rating for key, state in reduce_rating_event_states(events).items()}

def _validate_preference_compiler_inputs(
    episode: DecisionEpisode,
    alternatives: tuple[DecisionAlternative, ...],
    events: tuple[DecisionRatingEvent, ...],
    event_watermark: int,
    decision_learning_policy: Any,
) -> tuple[dict[str, Any], str, str]:
    if isinstance(event_watermark, bool) or not isinstance(event_watermark, int) or event_watermark < 0:
        raise ValueError("event_watermark must be a nonnegative integer")
    policy, decision_learning_policy_fingerprint = validate_decision_learning_policy(
        decision_learning_policy
    )
    if policy["domain_id"] != episode.domain_id:
        raise ValueError("policy domain conflicts with episode")
    if policy["rating_scale"]["version"] != episode.rating_scale_version:
        raise ValueError("policy rating scale conflicts with episode")
    if not alternatives:
        raise ValueError("compiler requires alternatives")
    seen_ids: set[str] = set()
    seen_ranks: set[int] = set()
    candidate_rows: list[dict[str, Any]] = []
    for alternative in alternatives:
        if alternative.episode_id != episode.episode_id:
            raise ValueError("alternative belongs to another episode")
        if not alternative.alternative_id or alternative.alternative_id in seen_ids:
            raise ValueError("alternatives require unique IDs")
        if alternative.displayed_rank <= 0 or alternative.displayed_rank in seen_ranks:
            raise ValueError("alternatives require unique positive ranks")
        seen_ids.add(alternative.alternative_id)
        seen_ranks.add(alternative.displayed_rank)
        candidate_rows.append(
            {
                "alternative_id": alternative.alternative_id,
                "displayed_rank": alternative.displayed_rank,
                "baseline_fit": alternative.baseline_fit,
                "baseline_fit_label": alternative.baseline_fit_label,
                "embedding_vector_fingerprint": alternative.embedding_vector_fingerprint,
                "shortlist_origin": alternative.shortlist_origin,
            }
        )
    if _candidate_set_fingerprint(candidate_rows) != episode.candidate_set_fingerprint:
        raise ValueError("candidate_set_fingerprint does not match alternatives")
    for event in events:
        if event.episode_id != episode.episode_id:
            raise ValueError("event belongs to another episode")
        if event.alternative_id not in seen_ids:
            raise ValueError("event references unknown alternative")
        if event.rating_scale_version != episode.rating_scale_version:
            raise ValueError("event rating scale conflicts with episode")
    return policy, decision_learning_policy_fingerprint, _compiler_policy_fingerprint(policy)


def _compile_rated_pairs(
    rated_states: tuple[EffectiveRatingState, ...],
    minimum_rating_gap: int,
    gap_evidence_weights: dict[str, float],
    compiler_version: str,
) -> tuple[tuple[PreferenceEdge, ...], int, int, float]:
    edges: list[PreferenceEdge] = []
    omitted_equal_count = 0
    omitted_below_gap_count = 0
    raw_weight_sum = 0.0
    for left_state, right_state in combinations(rated_states, 2):
        left_rating = int(left_state.rating)
        right_rating = int(right_state.rating)
        rating_gap = abs(left_rating - right_rating)
        if rating_gap == 0:
            omitted_equal_count += 1
            continue
        if rating_gap < minimum_rating_gap:
            omitted_below_gap_count += 1
            continue
        preferred, other = (left_state, right_state) if left_rating > right_rating else (right_state, left_state)
        if not preferred.source_event_id or not other.source_event_id:
            raise ValueError("rated edge endpoint lacks source event")
        evidence_weight = gap_evidence_weights[str(rating_gap)]
        raw_weight_sum += evidence_weight
        edges.append(
            PreferenceEdge(
                preferred_alternative_id=preferred.alternative_id,
                other_alternative_id=other.alternative_id,
                rating_gap=rating_gap,
                evidence_weight=evidence_weight,
                episode_bounded_weight=0.0,
                source_event_ids=(preferred.source_event_id, other.source_event_id),
                compiler_version=compiler_version,
            )
        )
    return tuple(sorted(edges, key=lambda edge: (edge.preferred_alternative_id, edge.other_alternative_id))), omitted_equal_count, omitted_below_gap_count, raw_weight_sum


def _edge_payload(edges: tuple[PreferenceEdge, ...]) -> list[dict[str, Any]]:
    return [
        {
            "preferred_alternative_id": edge.preferred_alternative_id,
            "other_alternative_id": edge.other_alternative_id,
            "rating_gap": edge.rating_gap,
            "evidence_weight": edge.evidence_weight,
            "episode_bounded_weight": edge.episode_bounded_weight,
            "source_event_ids": list(edge.source_event_ids),
            "compiler_version": edge.compiler_version,
        }
        for edge in edges
    ]


def compile_preference_edges(
    episode: DecisionEpisode,
    alternatives: Iterable[DecisionAlternative],
    events: Iterable[DecisionRatingEvent],
    *,
    event_watermark: int,
    decision_learning_policy: Any,
) -> PreferenceCompilerResult:
    """@capability cv_system.preference-compilation"""
    alternative_tuple = tuple(alternatives)
    event_tuple = tuple(events)
    policy, decision_learning_policy_fingerprint, compiler_policy_fingerprint = (
        _validate_preference_compiler_inputs(
            episode, alternative_tuple, event_tuple, event_watermark, decision_learning_policy
        )
    )
    compiler_policy = policy["preference_compiler"]
    states_by_key = reduce_rating_event_states(event_tuple, event_watermark=event_watermark)
    sorted_states = tuple(
        states_by_key.get(
            (episode.episode_id, alternative.alternative_id),
            EffectiveRatingState(
                episode_id=episode.episode_id,
                alternative_id=alternative.alternative_id,
                rating=_UNRATED_LABEL,
                source_event_id=None,
                event_sequence=None,
            ),
        )
        for alternative in sorted(alternative_tuple, key=lambda item: item.alternative_id)
    )
    rated_states = tuple(state for state in sorted_states if isinstance(state.rating, RatingValue))
    unordered_pair_count = len(sorted_states) * (len(sorted_states) - 1) // 2
    rated_pair_count = len(rated_states) * (len(rated_states) - 1) // 2
    edges, omitted_equal_count, omitted_below_gap_count, raw_weight_sum = _compile_rated_pairs(
        rated_states,
        int(compiler_policy["minimum_rating_gap"]),
        dict(compiler_policy["gap_evidence_weights"]),
        str(compiler_policy["compiler_version"]),
    )
    budget = float(compiler_policy["max_episode_evidence_budget"])
    episode_scale = min(1.0, budget / raw_weight_sum) if raw_weight_sum else 1.0
    bounded_edges = tuple(
        PreferenceEdge(
            **{**edge.__dict__, "episode_bounded_weight": edge.evidence_weight * episode_scale}
        )
        for edge in edges
    )
    effective_state_payload = [
        {
            "alternative_id": state.alternative_id,
            "rating": int(state.rating) if isinstance(state.rating, RatingValue) else _UNRATED_LABEL,
            "source_event_id": state.source_event_id,
            "event_sequence": state.event_sequence,
        }
        for state in sorted_states
    ]
    compiler_input_fingerprint = build_contract_fingerprint(
        {
            "schema_version": "preference_compiler_input_v1",
            "episode_id": episode.episode_id,
            "candidate_set_fingerprint": episode.candidate_set_fingerprint,
            "rating_scale_version": episode.rating_scale_version,
            "event_watermark": event_watermark,
            "compiler_version": compiler_policy["compiler_version"],
            "compiler_policy_fingerprint": compiler_policy_fingerprint,
            "decision_learning_policy_fingerprint": decision_learning_policy_fingerprint,
            "effective_states": effective_state_payload,
        }
    )
    edge_payload = _edge_payload(bounded_edges)
    edge_set_fingerprint = build_contract_fingerprint(
        {
            "schema_version": _PREFERENCE_EDGE_SET_SCHEMA_VERSION,
            "episode_id": episode.episode_id,
            "event_watermark": event_watermark,
            "compiler_version": compiler_policy["compiler_version"],
            "compiler_policy_fingerprint": compiler_policy_fingerprint,
            "decision_learning_policy_fingerprint": decision_learning_policy_fingerprint,
            "compiler_input_fingerprint": compiler_input_fingerprint,
            "edges": edge_payload,
        }
    )
    diagnostics = PreferenceCompilerDiagnostics(
        alternative_count=len(sorted_states),
        rated_alternative_count=len(rated_states),
        unordered_pair_count=unordered_pair_count,
        omitted_unrated_pair_count=unordered_pair_count - rated_pair_count,
        omitted_equal_pair_count=omitted_equal_count,
        omitted_below_gap_pair_count=omitted_below_gap_count,
        emitted_edge_count=len(bounded_edges),
        raw_evidence_weight_sum=raw_weight_sum,
        episode_scale=episode_scale,
        bounded_evidence_weight_sum=sum(edge.episode_bounded_weight for edge in bounded_edges),
    )
    return PreferenceCompilerResult(
        schema_version=_PREFERENCE_COMPILER_RESULT_SCHEMA_VERSION,
        status="compiled" if bounded_edges else "insufficient_evidence",
        episode_id=episode.episode_id,
        event_watermark=event_watermark,
        compiler_version=str(compiler_policy["compiler_version"]),
        compiler_policy_fingerprint=compiler_policy_fingerprint,
        decision_learning_policy_fingerprint=decision_learning_policy_fingerprint,
        compiler_input_fingerprint=compiler_input_fingerprint,
        edge_set_fingerprint=edge_set_fingerprint,
        edges=bounded_edges,
        diagnostics=diagnostics,
    )
