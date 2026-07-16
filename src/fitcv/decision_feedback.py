"""@meta
name: decision_feedback
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.decision-feedback
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


_POLICY_KEYS = {"policy_version", "domain_id", "rating_scale"}
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
    validated = {
        "policy_version": _EXPECTED_POLICY_VERSION,
        "domain_id": _EXPECTED_DOMAIN_ID,
        "rating_scale": {
            "version": _EXPECTED_SCALE_VERSION,
            "unrated_label": _EXPECTED_UNRATED_LABEL,
            "labels": {key: str(labels[key]).strip() for key in sorted(labels)},
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
    candidate_set_payload = [
        {
            "alternative_id": row["alternative_id"],
            "displayed_rank": row["displayed_rank"],
            "baseline_fit": row["baseline_fit"],
            "baseline_fit_label": row["baseline_fit_label"],
            "embedding_vector_fingerprint": row["embedding_vector_fingerprint"],
            "shortlist_origin": row["shortlist_origin"],
        }
        for row in alternatives
    ]
    candidate_set_fingerprint = build_contract_fingerprint({"alternatives": candidate_set_payload})
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
    candidate_set_payload = [
        {
            "alternative_id": row["alternative_id"],
            "displayed_rank": row["displayed_rank"],
            "baseline_fit": row["baseline_fit"],
            "baseline_fit_label": row["baseline_fit_label"],
            "embedding_vector_fingerprint": row["embedding_vector_fingerprint"],
            "shortlist_origin": row["shortlist_origin"],
        }
        for row in validated_alternatives
    ]
    expected_candidate_fingerprint = build_contract_fingerprint({"alternatives": candidate_set_payload})
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


def reduce_rating_events(
    events: Iterable[DecisionRatingEvent],
) -> dict[tuple[str, str], RatingValue | str]:
    latest: dict[tuple[str, str], DecisionRatingEvent] = {}
    for event in events:
        if event.event_sequence is None:
            raise ValueError("persisted event requires event_sequence")
        key = (event.episode_id, event.alternative_id)
        current = latest.get(key)
        if current is None or int(event.event_sequence) > int(current.event_sequence or 0):
            latest[key] = event
    return {
        key: cast(RatingValue, event.rating) if event.event_type is RatingEventType.SET_RATING else "unrated"
        for key, event in latest.items()
    }