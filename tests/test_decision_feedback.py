"""Tests for immutable Phase 4 decision-feedback contracts."""

from __future__ import annotations

import datetime

import pytest

from fitcv.decision_feedback import (
    DecisionRatingEvent,
    RatingEventType,
    RatingValue,
    build_decision_feedback_source,
    build_episode_records,
    reduce_rating_events,
    validate_decision_learning_policy,
)


def _policy() -> dict:
    return {
        "policy_version": "decision-learning-v1",
        "domain_id": "ranking_v1",
        "rating_scale": {
            "version": "application-interest-v1",
            "unrated_label": "unrated",
            "labels": {
                "1": "definitely not interested",
                "2": "low application interest",
                "3": "might consider applying",
                "4": "strong application interest",
                "5": "would prioritize applying",
            },
        },
    }


def _config() -> dict:
    return {
        "decision_learning_policy": _policy(),
        "ranking_policy": {"policy_version": "ranking-v2"},
        "ranking_contract": {"ranking_contract_fingerprint": "ranking-contract"},
        "embedding_model": "local-test-model",
    }


def _profile(preferred_locations: list[str] | None = None) -> dict:
    return {
        "headline": "Data Engineer",
        "preferences": {
            "target_role": "Data Engineer",
            "role_families": ["data"],
            "domains": ["analytics"],
            "seniority_target": "mid",
            "preferred_locations": preferred_locations or ["Berlin"],
            "work_modes": ["hybrid"],
        },
        "languages": [{"language": "German", "level": "B1"}],
    }


def _rows() -> list[dict]:
    return [
        {
            "raw_job_fingerprint": "job-b",
            "source_job_url": "https://example.test/b",
            "baseline_fit": 0.7,
            "baseline_fit_label": "stretch",
            "normalized_embedding": [0.0, 1.0],
            "embedding_contract_fingerprint": "embedding-contract",
            "shortlist_origin": "vector_search",
        },
        {
            "raw_job_fingerprint": "job-a",
            "source_job_url": "https://example.test/a",
            "baseline_fit": 0.9,
            "baseline_fit_label": "strong",
            "normalized_embedding": [1.0, 0.0],
            "embedding_contract_fingerprint": "embedding-contract",
            "shortlist_origin": "vector_search",
        },
    ]


def test_policy_validation_is_exact_and_fingerprinted() -> None:
    validated, fingerprint = validate_decision_learning_policy(_policy())
    assert validated == _policy()
    assert len(fingerprint) == 64
    with pytest.raises(ValueError, match="unknown keys"):
        validate_decision_learning_policy({**_policy(), "future": True})


def test_source_fingerprints_are_permutation_invariant_and_location_sensitive() -> None:
    first = build_decision_feedback_source(
        run_id="run-1", candidate_profile=_profile(), config=_config(), scoring_rows=_rows()
    )
    reordered = build_decision_feedback_source(
        run_id="run-1", candidate_profile=_profile(), config=_config(), scoring_rows=list(reversed(_rows()))
    )
    moved = build_decision_feedback_source(
        run_id="run-1", candidate_profile=_profile(["Magdeburg"]), config=_config(), scoring_rows=_rows()
    )
    assert first == reordered
    assert first["preference_context_fingerprint"] != moved["preference_context_fingerprint"]
    assert [row["alternative_id"] for row in first["alternatives"]] == ["job-a", "job-b"]


def test_source_excludes_malformed_vectors_and_rejects_corrupt_persisted_source() -> None:
    rows = _rows()
    rows[0]["normalized_embedding"] = [0.0, float("nan")]
    source = build_decision_feedback_source(
        run_id="run-1", candidate_profile=_profile(), config=_config(), scoring_rows=rows
    )
    assert [row["alternative_id"] for row in source["alternatives"]] == ["job-a"]
    source["alternatives"][0]["normalized_embedding"] = [0.0, float("nan")]
    with pytest.raises(ValueError, match="normalized_embedding"):
        build_episode_records(source)


def test_episode_id_is_stable_and_reducer_uses_event_sequence() -> None:
    source = build_decision_feedback_source(
        run_id="run-1", candidate_profile=_profile(), config=_config(), scoring_rows=_rows()
    )
    episode, alternatives = build_episode_records(source)
    repeated_episode, repeated_alternatives = build_episode_records(source)
    assert episode == repeated_episode
    assert alternatives == repeated_alternatives

    same_time = datetime.datetime(2026, 7, 16, tzinfo=datetime.timezone.utc)
    events = [
        DecisionRatingEvent(
            event_sequence=2,
            event_id="event-a",
            episode_id=episode.episode_id,
            alternative_id="job-a",
            event_type=RatingEventType.CLEAR_RATING,
            rating=None,
            rating_scale_version=episode.rating_scale_version,
            acted_by="local_operator",
            created_at=same_time,
        ),
        DecisionRatingEvent(
            event_sequence=1,
            event_id="event-z",
            episode_id=episode.episode_id,
            alternative_id="job-a",
            event_type=RatingEventType.SET_RATING,
            rating=RatingValue.FIVE,
            rating_scale_version=episode.rating_scale_version,
            acted_by="local_operator",
            created_at=same_time,
        ),
    ]
    assert reduce_rating_events(events)[(episode.episode_id, "job-a")] == "unrated"