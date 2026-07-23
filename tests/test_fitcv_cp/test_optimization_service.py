"""
@meta
type: test
scope: unit
domain: inverse_optimization
covers:
  - shared candidate orchestration
  - stale evidence and parent compare tokens
excludes:
  - HTTP rendering
  - live solver execution
tags:
  - fast
  - ci-safe
"""

import datetime
from types import SimpleNamespace
from typing import Any, cast

from fitcv.config import load_config
from fitcv.decision_feedback import (
    DecisionAlternative,
    DecisionEpisode,
    DecisionRatingEvent,
    RatingEventType,
    RatingValue,
)
from fitcv.inverse_optimization import InverseOptimizationRequest, InverseTrainingEpisode
from fitcv.preference_policy import build_preference_optimization_run_id
from fitcv.shortlist_runtime import build_contract_fingerprint
import fitcv_cp.optimization_service as service_module
from fitcv_cp.optimization_service import create_ranking_policy_candidate
from fitcv_cp.settings_store import settings_revision
from fitcv_cp.store import ControlPlaneStore


def _rated_request() -> InverseOptimizationRequest:
    created_at = datetime.datetime(2026, 7, 23, 8, 0, tzinfo=datetime.timezone.utc)
    vector_fingerprint = build_contract_fingerprint(
        {"normalized_embedding": [1.0, 0.0]}
    )
    candidate_set_fingerprint = build_contract_fingerprint(
        {
            "alternatives": [
                {
                    "alternative_id": "job-1",
                    "displayed_rank": 1,
                    "baseline_fit": 0.82,
                    "baseline_fit_label": "strong",
                    "embedding_vector_fingerprint": vector_fingerprint,
                    "shortlist_origin": "vector_search",
                }
            ]
        }
    )
    episode = DecisionEpisode(
        episode_id="episode-1",
        domain_id="ranking_v1",
        run_id="run-1",
        preference_context_fingerprint="preference",
        qualification_context_fingerprint="qualification",
        ranking_contract_fingerprint="ranking",
        embedding_contract_fingerprint="embedding",
        baseline_policy_fingerprint="baseline",
        embedding_model="model",
        embedding_dimension=2,
        rating_scale_version="application-interest-v1",
        candidate_set_fingerprint=candidate_set_fingerprint,
        source_stage_artifact_fingerprint="artifact",
        created_at=created_at,
    )
    alternative = DecisionAlternative(
        episode_id=episode.episode_id,
        alternative_id="job-1",
        displayed_rank=1,
        baseline_fit=0.82,
        baseline_fit_label="strong",
        normalized_embedding_json="[1.0,0.0]",
        embedding_vector_fingerprint=vector_fingerprint,
        source_job_url="https://example.test/job-1",
        shortlist_origin="vector_search",
        created_at=created_at,
    )
    event = DecisionRatingEvent(
        event_sequence=1,
        event_id="event-1",
        episode_id=episode.episode_id,
        alternative_id=alternative.alternative_id,
        event_type=RatingEventType.SET_RATING,
        rating=RatingValue(5),
        rating_scale_version=episode.rating_scale_version,
        acted_by="local_workspace",
        created_at=created_at,
    )
    return InverseOptimizationRequest(
        schema_version="inverse_optimization_request_v1",
        domain_id="ranking_v1",
        event_watermark=1,
        episodes=(
            InverseTrainingEpisode(
                episode=episode,
                alternatives=(alternative,),
                events=(event,),
                events_loaded_through_sequence=1,
            ),
        ),
    )


def test_candidate_rejects_submitted_stale_evidence_before_solving() -> None:
    request = InverseOptimizationRequest(
        schema_version="inverse_optimization_request_v1",
        domain_id="ranking_v1",
        event_watermark=0,
        episodes=(),
    )
    store = ControlPlaneStore(
        get_decision_evidence_head_fn=lambda domain_id: {
            "schema_version": "decision_evidence_head_v1",
            "domain_id": domain_id,
            "event_watermark": 0,
            "episodes": [],
            "evidence_head_fingerprint": "current-head",
        }
    )

    result = create_ranking_policy_candidate(
        request,
        store=store,
        config={},
        ranking_mode="personalized",
        personalization_strength=0.05,
        settings_revision="settings-1",
        expected_evidence_head_fingerprint="stale-head",
    )

    assert result == {"status": "stale", "error_code": "stale_evidence"}


def test_candidate_rejects_changed_parent_before_solving(monkeypatch: Any) -> None:
    first = SimpleNamespace(
        baseline_policy_fingerprint="baseline",
        ranking_contract_fingerprint="ranking-contract",
        embedding_model="embedding-model",
        embedding_dimension=2,
        embedding_contract_fingerprint="embedding-contract",
    )
    request = cast(
        InverseOptimizationRequest,
        SimpleNamespace(
            domain_id="ranking_v1",
            episodes=(SimpleNamespace(episode=first),),
        ),
    )
    monkeypatch.setattr(
        service_module,
        "_request_evidence_head",
        lambda _request: {"evidence_head_fingerprint": "current-head"},
    )
    monkeypatch.setattr(
        service_module,
        "solve_preference_residual",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("solver called")),
    )
    store = ControlPlaneStore(
        get_decision_evidence_head_fn=lambda domain_id: {
            "domain_id": domain_id,
            "evidence_head_fingerprint": "current-head",
        },
        resolve_active_ranking_policy_fn=lambda domain_id, runtime_fingerprint: {
            "policy_snapshot_id": "active-snapshot",
            "preference_vector_json": [0.0, 0.0],
        },
    )

    result = create_ranking_policy_candidate(
        request,
        store=store,
        config=load_config(),
        ranking_mode="personalized",
        personalization_strength=0.05,
        settings_revision="settings-1",
        expected_evidence_head_fingerprint="current-head",
        expected_parent_ref="zero_residual:baseline",
    )

    assert result == {"status": "stale", "error_code": "candidate_parent_changed"}


def test_baseline_mode_creates_no_optimization_run(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        service_module,
        "solve_preference_residual",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("solver called")),
    )
    store = ControlPlaneStore(
        persist_candidate_attempt_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("persist called")
        )
    )

    result = create_ranking_policy_candidate(
        _rated_request(),
        store=store,
        config=load_config(),
        ranking_mode="baseline",
        personalization_strength=0.05,
        settings_revision="settings-1",
    )

    assert result == {
        "status": "not_started",
        "error_code": "personalized_ranking_required",
    }


def test_terminal_attempt_persists_public_run_and_historical_evidence(
    monkeypatch: Any,
) -> None:
    request = _rated_request()
    head = service_module._request_evidence_head(request)
    active_settings = {
        "preference_optimization.ranking_mode": "personalized",
        "preference_optimization.personalization_strength": 0.08,
    }
    revision = settings_revision(active_settings)
    captured: dict[str, Any] = {}
    solve = service_module.solve_preference_residual

    def solve_with_strength(request_value: Any, policy: dict[str, Any]) -> Any:
        captured["solver_strength"] = policy["inverse_optimization"]["learned_alpha"]
        return solve(request_value, policy)

    def persist(training: dict[str, Any], snapshot: Any, projection: dict[str, Any]) -> dict[str, Any]:
        captured["training"] = training
        captured["snapshot"] = snapshot
        captured["projection"] = projection
        public_id = build_preference_optimization_run_id(training["training_run_id"])
        return {
            "training_run": training,
            "snapshot": snapshot,
            "optimization_run": {"preference_optimization_run_id": public_id},
        }

    monkeypatch.setattr(service_module, "solve_preference_residual", solve_with_strength)
    monkeypatch.setattr(service_module, "load_active_settings", lambda: active_settings)
    store = ControlPlaneStore(
        get_decision_evidence_head_fn=lambda _domain_id: head,
        resolve_active_ranking_policy_fn=lambda _domain_id, _runtime: None,
        get_run_job_fn=lambda _run_id, _run_job_id: {
            "job_title": "Data Analyst",
            "company": "Example",
        },
        persist_candidate_attempt_fn=persist,
    )

    result = create_ranking_policy_candidate(
        request,
        store=store,
        config=load_config(),
        ranking_mode="personalized",
        personalization_strength=0.08,
        settings_revision=revision,
        expected_evidence_head_fingerprint=str(head["evidence_head_fingerprint"]),
        expected_parent_ref="zero_residual:baseline",
    )

    assert result["status"] == "insufficient_evidence"
    assert result["display_status"] == "Not Created"
    assert result["preference_optimization_run_id"].startswith("por_")
    assert "training_run_id" not in result
    assert captured["solver_strength"] == 0.08
    assert captured["training"]["learned_alpha"] == 0.08
    assert captured["projection"] == {
        "settings_revision": revision,
        "ranking_mode": "personalized",
        "personalization_strength": 0.08,
        "evidence_head_fingerprint": head["evidence_head_fingerprint"],
        "event_watermark": 1,
        "source_rating_event_ids": ["event-1"],
        "rating_evidence_rows": [
            {
                "source_rating_event_id": "event-1",
                "run_id": "run-1",
                "alternative_id": "job-1",
                "job_label": "Data Analyst at Example",
                "source_job_url": "https://example.test/job-1",
                "displayed_rank": 1,
                "baseline_fit": 0.82,
                "baseline_fit_label": "strong",
                "rating": 5,
                "rated_at": "2026-07-23T08:00:00+00:00",
            }
        ],
    }


def test_stale_after_solve_does_not_persist(monkeypatch: Any) -> None:
    request = _rated_request()
    head = service_module._request_evidence_head(request)
    active_settings = {
        "preference_optimization.ranking_mode": "personalized",
        "preference_optimization.personalization_strength": 0.05,
    }
    calls = 0

    def evidence_head(_domain_id: str) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        if calls == 1:
            return head
        return {**head, "evidence_head_fingerprint": "changed-head"}

    monkeypatch.setattr(service_module, "load_active_settings", lambda: active_settings)
    store = ControlPlaneStore(
        get_decision_evidence_head_fn=evidence_head,
        resolve_active_ranking_policy_fn=lambda _domain_id, _runtime: None,
        get_run_job_fn=lambda _run_id, _run_job_id: None,
        persist_candidate_attempt_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("persist called")
        ),
    )

    result = create_ranking_policy_candidate(
        request,
        store=store,
        config=load_config(),
        ranking_mode="personalized",
        personalization_strength=0.05,
        settings_revision=settings_revision(active_settings),
        expected_evidence_head_fingerprint=str(head["evidence_head_fingerprint"]),
        expected_parent_ref="zero_residual:baseline",
    )

    assert result == {
        "status": "stale",
        "error_code": "optimization_precondition_changed",
    }


def test_duplicate_retry_reuses_public_run_identity(monkeypatch: Any) -> None:
    request = _rated_request()
    head = service_module._request_evidence_head(request)
    active_settings = {
        "preference_optimization.ranking_mode": "personalized",
        "preference_optimization.personalization_strength": 0.05,
    }
    persisted: dict[str, dict[str, Any]] = {}

    def persist(training: dict[str, Any], snapshot: Any, projection: dict[str, Any]) -> dict[str, Any]:
        training_id = str(training["training_run_id"])
        public_id = build_preference_optimization_run_id(training_id)
        persisted.setdefault(
            training_id,
            {
                "training_run": training,
                "snapshot": snapshot,
                "optimization_run": {"preference_optimization_run_id": public_id},
            },
        )
        return persisted[training_id]

    monkeypatch.setattr(service_module, "load_active_settings", lambda: active_settings)
    store = ControlPlaneStore(
        get_decision_evidence_head_fn=lambda _domain_id: head,
        resolve_active_ranking_policy_fn=lambda _domain_id, _runtime: None,
        get_run_job_fn=lambda _run_id, _run_job_id: None,
        persist_candidate_attempt_fn=persist,
    )
    kwargs = {
        "store": store,
        "config": load_config(),
        "ranking_mode": "personalized",
        "personalization_strength": 0.05,
        "settings_revision": settings_revision(active_settings),
        "expected_evidence_head_fingerprint": str(head["evidence_head_fingerprint"]),
        "expected_parent_ref": "zero_residual:baseline",
    }

    first = create_ranking_policy_candidate(request, **kwargs)
    second = create_ranking_policy_candidate(request, **kwargs)

    assert first["preference_optimization_run_id"] == second[
        "preference_optimization_run_id"
    ]
    assert len(persisted) == 1


def test_solver_exception_persists_terminal_solver_error(monkeypatch: Any) -> None:
    request = _rated_request()
    head = service_module._request_evidence_head(request)
    active_settings = {
        "preference_optimization.ranking_mode": "personalized",
        "preference_optimization.personalization_strength": 0.05,
    }
    captured: dict[str, Any] = {}

    def persist(training: dict[str, Any], snapshot: Any, projection: dict[str, Any]) -> dict[str, Any]:
        captured["training"] = training
        captured["snapshot"] = snapshot
        captured["projection"] = projection
        return {
            "training_run": training,
            "snapshot": snapshot,
            "optimization_run": {
                "preference_optimization_run_id": build_preference_optimization_run_id(
                    training["training_run_id"]
                )
            },
        }

    monkeypatch.setattr(
        service_module,
        "solve_preference_residual",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("solver failed")),
    )
    monkeypatch.setattr(service_module, "load_active_settings", lambda: active_settings)
    store = ControlPlaneStore(
        get_decision_evidence_head_fn=lambda _domain_id: head,
        resolve_active_ranking_policy_fn=lambda _domain_id, _runtime: None,
        get_run_job_fn=lambda _run_id, _run_job_id: None,
        persist_candidate_attempt_fn=persist,
    )

    result = create_ranking_policy_candidate(
        request,
        store=store,
        config=load_config(),
        ranking_mode="personalized",
        personalization_strength=0.05,
        settings_revision=settings_revision(active_settings),
        expected_evidence_head_fingerprint=str(head["evidence_head_fingerprint"]),
        expected_parent_ref="zero_residual:baseline",
    )

    assert result["status"] == "solver_error"
    assert result["display_status"] == "Failed"
    assert result["preference_optimization_run_id"].startswith("por_")
    assert captured["training"]["status"] == "solver_error"
    assert captured["snapshot"] is None
    assert captured["training"]["result_json"]["error_code"] == (
        "solver_execution_failed"
    )


def test_empty_rating_evidence_persists_terminal_insufficient_evidence(
    monkeypatch: Any,
) -> None:
    request = InverseOptimizationRequest(
        schema_version="inverse_optimization_request_v1",
        domain_id="ranking_v1",
        event_watermark=0,
        episodes=(),
    )
    head = service_module._request_evidence_head(request)
    active_settings = {
        "preference_optimization.ranking_mode": "personalized",
        "preference_optimization.personalization_strength": 0.05,
    }
    captured: dict[str, Any] = {}

    def persist(training: dict[str, Any], snapshot: Any, projection: dict[str, Any]) -> dict[str, Any]:
        captured["training"] = training
        captured["snapshot"] = snapshot
        captured["projection"] = projection
        return {
            "training_run": training,
            "snapshot": snapshot,
            "optimization_run": {
                "preference_optimization_run_id": build_preference_optimization_run_id(
                    training["training_run_id"]
                )
            },
        }

    monkeypatch.setattr(service_module, "load_active_settings", lambda: active_settings)
    store = ControlPlaneStore(
        get_decision_evidence_head_fn=lambda _domain_id: head,
        resolve_active_ranking_policy_fn=lambda _domain_id, _runtime: None,
        persist_candidate_attempt_fn=persist,
    )

    result = create_ranking_policy_candidate(
        request,
        store=store,
        config=load_config(),
        ranking_mode="personalized",
        personalization_strength=0.05,
        settings_revision=settings_revision(active_settings),
        expected_evidence_head_fingerprint=str(head["evidence_head_fingerprint"]),
        expected_parent_ref=None,
    )

    assert result["status"] == "insufficient_evidence"
    assert result["display_status"] == "Not Created"
    assert result["preference_optimization_run_id"].startswith("por_")
    assert captured["training"]["status"] == "insufficient_evidence"
    assert captured["training"]["result_json"]["error_code"] == (
        "zero_rating_evidence"
    )
    assert captured["projection"]["source_rating_event_ids"] == []
    assert captured["projection"]["rating_evidence_rows"] == []


def test_invalid_historical_evidence_persists_terminal_invalid_input(
    monkeypatch: Any,
) -> None:
    request = _rated_request()
    head = service_module._request_evidence_head(request)
    active_settings = {
        "preference_optimization.ranking_mode": "personalized",
        "preference_optimization.personalization_strength": 0.05,
    }
    captured: dict[str, Any] = {}

    def persist(training: dict[str, Any], snapshot: Any, projection: dict[str, Any]) -> dict[str, Any]:
        captured["training"] = training
        captured["snapshot"] = snapshot
        captured["projection"] = projection
        return {
            "training_run": training,
            "snapshot": snapshot,
            "optimization_run": {
                "preference_optimization_run_id": build_preference_optimization_run_id(
                    training["training_run_id"]
                )
            },
        }

    monkeypatch.setattr(service_module, "load_active_settings", lambda: active_settings)
    store = ControlPlaneStore(
        get_decision_evidence_head_fn=lambda _domain_id: head,
        resolve_active_ranking_policy_fn=lambda _domain_id, _runtime: None,
        get_run_job_fn=lambda _run_id, _run_job_id: (_ for _ in ()).throw(
            ValueError("invalid historical row")
        ),
        persist_candidate_attempt_fn=persist,
    )

    result = create_ranking_policy_candidate(
        request,
        store=store,
        config=load_config(),
        ranking_mode="personalized",
        personalization_strength=0.05,
        settings_revision=settings_revision(active_settings),
        expected_evidence_head_fingerprint=str(head["evidence_head_fingerprint"]),
        expected_parent_ref="zero_residual:baseline",
    )

    assert result["status"] == "invalid_input"
    assert result["display_status"] == "Failed"
    assert result["preference_optimization_run_id"].startswith("por_")
    assert captured["training"]["result_json"]["error_code"] == (
        "rating_evidence_unavailable"
    )
    assert captured["projection"]["source_rating_event_ids"] == []
    assert captured["projection"]["rating_evidence_rows"] == []
