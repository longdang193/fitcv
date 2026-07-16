"""Tests for immutable Phase 4 decision-feedback contracts."""

from __future__ import annotations

import copy
import datetime

import pytest

from fitcv.decision_feedback import (
    DecisionRatingEvent,
    RatingEventType,
    compile_preference_edges,
    RatingValue,
    build_decision_feedback_source,
    build_episode_records,
    reduce_rating_event_states,
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
        "preference_compiler": {
            "compiler_version": "preference-compiler-v1",
            "minimum_rating_gap": 2,
            "gap_evidence_weights": {"1": 1.0, "2": 2.0, "3": 3.0, "4": 4.0},
            "max_episode_evidence_budget": 12.0,
        },
    }


def _config() -> dict:
    return {
        "decision_learning_policy": _policy(),
        "ranking_policy": {"policy_version": "ranking-v2"},
        "ranking_contract": {"ranking_contract_fingerprint": "ranking-contract"},
        "embedding_model": "local-test-model",
    }


def _rating_event(
    episode,
    alternative_id: str,
    sequence: int,
    event_id: str,
    rating: int,
) -> DecisionRatingEvent:
    return DecisionRatingEvent(
        event_sequence=sequence,
        event_id=event_id,
        episode_id=episode.episode_id,
        alternative_id=alternative_id,
        event_type=RatingEventType.SET_RATING,
        rating=RatingValue(rating),
        rating_scale_version=episode.rating_scale_version,
        acted_by="local_operator",
        created_at=datetime.datetime(2026, 7, 16, tzinfo=datetime.timezone.utc),
    )


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


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda block: block.update({"future": True}), "unknown keys"),
        (lambda block: block.update({"minimum_rating_gap": 0}), "minimum_rating_gap"),
        (lambda block: block.update({"minimum_rating_gap": True}), "minimum_rating_gap"),
        (lambda block: block.update({"gap_evidence_weights": {"1": 1.0}}), "gap_evidence_weights"),
        (
            lambda block: block.update(
                {"gap_evidence_weights": {"1": 1.0, "2": 1.0, "3": 3.0, "4": 4.0}}
            ),
            "strictly increasing",
        ),
        (lambda block: block.update({"max_episode_evidence_budget": float("inf")}), "budget"),
    ],
)
def test_compiler_policy_validation_rejects_invalid_values(mutate, message: str) -> None:
    policy = _policy()
    mutate(policy["preference_compiler"])
    with pytest.raises(ValueError, match=message):
        validate_decision_learning_policy(policy)


def test_full_policy_fingerprint_tracks_rating_labels() -> None:
    policy = _policy()
    changed = copy.deepcopy(policy)
    changed["rating_scale"]["labels"]["4"] = "high application interest"
    _, first_fingerprint = validate_decision_learning_policy(policy)
    _, changed_fingerprint = validate_decision_learning_policy(changed)
    assert first_fingerprint != changed_fingerprint


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
    assert first["candidate_set_fingerprint"] == "864066b4418f95a9e7e51af1128821894f220fa31ff6d1d57cc611604e88ccf4"
    assert first["source_stage_artifact_fingerprint"] == "73ac785a4a121ae0b3332ac99340047bb4dbe0ece5d5f99521262c90b5c155d2"
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
    states = reduce_rating_event_states(events, event_watermark=2)
    assert states[(episode.episode_id, "job-a")].rating == "unrated"
    assert states[(episode.episode_id, "job-a")].source_event_id == "event-a"
    assert states[(episode.episode_id, "job-a")].event_sequence == 2
    assert reduce_rating_events(events)[(episode.episode_id, "job-a")] == "unrated"


def test_preference_compiler_emits_directed_edges_with_provenance() -> None:
    """@proves cv_system.preference-compilation"""
    source = build_decision_feedback_source(
        run_id="run-1", candidate_profile=_profile(), config=_config(), scoring_rows=_rows()
    )
    episode, alternatives = build_episode_records(source)
    events = [
        _rating_event(episode, "job-a", 1, "event-a", 5),
        _rating_event(episode, "job-b", 2, "event-b", 3),
    ]
    result = compile_preference_edges(
        episode, alternatives, events, event_watermark=2, decision_learning_policy=_policy()
    )
    assert result.status == "compiled"
    assert len(result.edges) == 1
    edge = result.edges[0]
    assert edge.preferred_alternative_id == "job-a"
    assert edge.other_alternative_id == "job-b"
    assert edge.rating_gap == 2
    assert edge.evidence_weight == 2.0
    assert edge.episode_bounded_weight == 2.0
    assert edge.source_event_ids == ("event-a", "event-b")
    assert result.diagnostics.unordered_pair_count == 1
    assert result.diagnostics.emitted_edge_count == 1


def test_preference_compiler_accounts_for_sparse_unrated_alternatives() -> None:
    rows = _rows() + [
        {
            "raw_job_fingerprint": "job-c",
            "source_job_url": "https://example.test/c",
            "baseline_fit": 0.6,
            "baseline_fit_label": "stretch",
            "normalized_embedding": [1.0, 0.0],
            "embedding_contract_fingerprint": "embedding-contract",
            "shortlist_origin": "vector_search",
        },
        {
            "raw_job_fingerprint": "job-d",
            "source_job_url": "https://example.test/d",
            "baseline_fit": 0.5,
            "baseline_fit_label": "skip",
            "normalized_embedding": [0.0, 1.0],
            "embedding_contract_fingerprint": "embedding-contract",
            "shortlist_origin": "vector_search",
        },
    ]
    source = build_decision_feedback_source(
        run_id="run-1", candidate_profile=_profile(), config=_config(), scoring_rows=rows
    )
    episode, alternatives = build_episode_records(source)
    result = compile_preference_edges(
        episode,
        alternatives,
        [_rating_event(episode, "job-a", 1, "event-a", 5), _rating_event(episode, "job-b", 2, "event-b", 3)],
        event_watermark=2,
        decision_learning_policy=_policy(),
    )
    assert result.diagnostics.alternative_count == 4
    assert result.diagnostics.rated_alternative_count == 2
    assert result.diagnostics.unordered_pair_count == 6
    assert result.diagnostics.omitted_unrated_pair_count == 5
    assert result.diagnostics.emitted_edge_count == 1


def test_preference_compiler_preserves_all_qualifying_pairs_and_caps_episode_weight() -> None:
    rows = [
        {
            "raw_job_fingerprint": f"job-{rating}",
            "source_job_url": f"https://example.test/{rating}",
            "baseline_fit": 0.9 - index * 0.1,
            "baseline_fit_label": "strong",
            "normalized_embedding": [1.0, 0.0],
            "embedding_contract_fingerprint": "embedding-contract",
            "shortlist_origin": "vector_search",
        }
        for index, rating in enumerate(range(5, 0, -1))
    ]
    source = build_decision_feedback_source(
        run_id="run-1", candidate_profile=_profile(), config=_config(), scoring_rows=rows
    )
    episode, alternatives = build_episode_records(source)
    events = [
        _rating_event(episode, f"job-{rating}", index + 1, f"event-{rating}", rating)
        for index, rating in enumerate(range(5, 0, -1))
    ]
    result = compile_preference_edges(
        episode, alternatives, events, event_watermark=5, decision_learning_policy=_policy()
    )
    assert len(result.edges) == 6
    assert result.diagnostics.raw_evidence_weight_sum == 16.0
    assert result.diagnostics.episode_scale == 0.75
    assert result.diagnostics.bounded_evidence_weight_sum == 12.0
    assert {edge.rating_gap for edge in result.edges} == {2, 3, 4}


def test_preference_compiler_returns_insufficient_evidence_for_equal_ratings() -> None:
    source = build_decision_feedback_source(
        run_id="run-1", candidate_profile=_profile(), config=_config(), scoring_rows=_rows()
    )
    episode, alternatives = build_episode_records(source)
    events = [
        _rating_event(episode, "job-a", 1, "event-a", 4),
        _rating_event(episode, "job-b", 2, "event-b", 4),
    ]
    result = compile_preference_edges(
        episode, alternatives, events, event_watermark=2, decision_learning_policy=_policy()
    )
    assert result.status == "insufficient_evidence"
    assert result.edges == ()
    assert result.diagnostics.omitted_equal_pair_count == 1


def test_preference_compiler_fingerprint_tracks_full_policy_and_input_order() -> None:
    source = build_decision_feedback_source(
        run_id="run-1", candidate_profile=_profile(), config=_config(), scoring_rows=_rows()
    )
    episode, alternatives = build_episode_records(source)
    events = [
        _rating_event(episode, "job-a", 1, "event-a", 5),
        _rating_event(episode, "job-b", 2, "event-b", 3),
    ]
    first = compile_preference_edges(
        episode, alternatives, events, event_watermark=2, decision_learning_policy=_policy()
    )
    reordered = compile_preference_edges(
        episode, tuple(reversed(alternatives)), list(reversed(events)), event_watermark=2, decision_learning_policy=_policy()
    )
    changed_policy = copy.deepcopy(_policy())
    changed_policy["rating_scale"]["labels"]["4"] = "high application interest"
    changed = compile_preference_edges(
        episode, alternatives, events, event_watermark=2, decision_learning_policy=changed_policy
    )
    assert first == reordered
    assert first.compiler_policy_fingerprint == reordered.compiler_policy_fingerprint
    assert first.decision_learning_policy_fingerprint != changed.decision_learning_policy_fingerprint
    assert first.edge_set_fingerprint != changed.edge_set_fingerprint


@pytest.mark.parametrize("left_rating", [None, 1, 2, 3, 4, 5])
@pytest.mark.parametrize("right_rating", [None, 1, 2, 3, 4, 5])
def test_preference_compiler_exhaustive_pair_matrix(
    left_rating: int | None, right_rating: int | None
) -> None:
    source = build_decision_feedback_source(
        run_id="run-1", candidate_profile=_profile(), config=_config(), scoring_rows=_rows()
    )
    episode, alternatives = build_episode_records(source)
    events = []
    if left_rating is not None:
        events.append(_rating_event(episode, "job-a", 1, "event-a", left_rating))
    if right_rating is not None:
        events.append(_rating_event(episode, "job-b", 2, "event-b", right_rating))
    result = compile_preference_edges(
        episode, alternatives, events, event_watermark=2, decision_learning_policy=_policy()
    )
    if left_rating is None or right_rating is None:
        assert result.edges == ()
        assert result.diagnostics.omitted_unrated_pair_count == 1
    elif left_rating == right_rating:
        assert result.edges == ()
        assert result.diagnostics.omitted_equal_pair_count == 1
    elif abs(left_rating - right_rating) < 2:
        assert result.edges == ()
        assert result.diagnostics.omitted_below_gap_pair_count == 1
    else:
        assert len(result.edges) == 1
        assert result.edges[0].rating_gap == abs(left_rating - right_rating)
        expected_preferred = "job-a" if left_rating > right_rating else "job-b"
        assert result.edges[0].preferred_alternative_id == expected_preferred


def test_preference_compiler_uses_alternate_valid_policy_without_branches() -> None:
    source = build_decision_feedback_source(
        run_id="run-1", candidate_profile=_profile(), config=_config(), scoring_rows=_rows()
    )
    episode, alternatives = build_episode_records(source)
    events = [
        _rating_event(episode, "job-a", 1, "event-a", 5),
        _rating_event(episode, "job-b", 2, "event-b", 4),
    ]
    default_result = compile_preference_edges(
        episode, alternatives, events, event_watermark=2, decision_learning_policy=_policy()
    )
    alternate_policy = copy.deepcopy(_policy())
    alternate_policy["preference_compiler"] = {
        "compiler_version": "preference-compiler-v1",
        "minimum_rating_gap": 1,
        "gap_evidence_weights": {"1": 2.0, "2": 4.0, "3": 6.0, "4": 8.0},
        "max_episode_evidence_budget": 1.0,
    }
    alternate_result = compile_preference_edges(
        episode, alternatives, events, event_watermark=2, decision_learning_policy=alternate_policy
    )
    assert default_result.status == "insufficient_evidence"
    assert alternate_result.status == "compiled"
    assert alternate_result.edges[0].evidence_weight == 2.0
    assert alternate_result.edges[0].episode_bounded_weight == 1.0
    assert default_result.compiler_policy_fingerprint != alternate_result.compiler_policy_fingerprint
    assert default_result.edge_set_fingerprint != alternate_result.edge_set_fingerprint


def test_preference_compiler_rejects_incompatible_inputs() -> None:
    source = build_decision_feedback_source(
        run_id="run-1", candidate_profile=_profile(), config=_config(), scoring_rows=_rows()
    )
    episode, alternatives = build_episode_records(source)
    unknown_event = _rating_event(episode, "unknown", 1, "event-unknown", 5)
    with pytest.raises(ValueError, match="unknown alternative"):
        compile_preference_edges(
            episode, alternatives, [unknown_event], event_watermark=1, decision_learning_policy=_policy()
        )
    with pytest.raises(ValueError, match="event_watermark"):
        compile_preference_edges(
            episode, alternatives, [], event_watermark=-1, decision_learning_policy=_policy()
        )


def test_rating_state_reducer_watermark_and_duplicate_guards() -> None:
    source = build_decision_feedback_source(
        run_id="run-1", candidate_profile=_profile(), config=_config(), scoring_rows=_rows()
    )
    episode, _ = build_episode_records(source)
    same_time = datetime.datetime(2026, 7, 16, tzinfo=datetime.timezone.utc)
    event = DecisionRatingEvent(
        event_sequence=1,
        event_id="event-1",
        episode_id=episode.episode_id,
        alternative_id="job-a",
        event_type=RatingEventType.SET_RATING,
        rating=RatingValue.FIVE,
        rating_scale_version=episode.rating_scale_version,
        acted_by="local_operator",
        created_at=same_time,
    )
    assert reduce_rating_event_states([event], event_watermark=0) == {}
    with pytest.raises(ValueError, match="duplicate event_id"):
        reduce_rating_event_states([event, event])
    duplicate_sequence = copy.copy(event)
    object.__setattr__(duplicate_sequence, "event_id", "event-2")
    with pytest.raises(ValueError, match="duplicate event_sequence"):
        reduce_rating_event_states([event, duplicate_sequence])