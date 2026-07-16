"""
@meta
type: test
scope: integration
domain: inverse_optimization
covers:
  - native preference optimization admin page
  - candidate and lifecycle redirect-after-POST actions
excludes:
  - live solver execution
  - browser visual regression
tags:
  - fast
  - ci-safe
"""

from __future__ import annotations

import datetime
from typing import Any

from fastapi.testclient import TestClient

import fitcv_cp.app as app_module
from fitcv.decision_feedback import (
    DecisionAlternative,
    DecisionEpisode,
    DecisionRatingEvent,
    RatingEventType,
    RatingValue,
)
from fitcv.inverse_optimization import InverseOptimizationRequest, InverseTrainingEpisode


DOMAIN_ID = "ranking_v1"
EVIDENCE_HEAD = {
    "schema_version": "decision_evidence_head_v1",
    "domain_id": DOMAIN_ID,
    "event_watermark": 0,
    "episodes": [],
    "evidence_head_fingerprint": "evidence-head",
}


def _empty_request() -> InverseOptimizationRequest:
    return InverseOptimizationRequest(
        schema_version="inverse_optimization_request_v1",
        domain_id=DOMAIN_ID,
        event_watermark=0,
        episodes=(),
    )


def _rated_request() -> InverseOptimizationRequest:
    created_at = datetime.datetime(2026, 7, 16, 12, 0, tzinfo=datetime.timezone.utc)
    episode = DecisionEpisode(
        episode_id="episode-1",
        domain_id=DOMAIN_ID,
        run_id="run-1",
        preference_context_fingerprint="preference",
        qualification_context_fingerprint="qualification",
        ranking_contract_fingerprint="ranking",
        embedding_contract_fingerprint="embedding",
        baseline_policy_fingerprint="baseline",
        embedding_model="model",
        embedding_dimension=2,
        rating_scale_version="application-interest-v1",
        candidate_set_fingerprint="candidate-set",
        source_stage_artifact_fingerprint="artifact",
        created_at=created_at,
    )
    alternative = DecisionAlternative(
        episode_id=episode.episode_id,
        alternative_id="job-1",
        displayed_rank=7,
        baseline_fit=0.82,
        baseline_fit_label="strong",
        normalized_embedding_json="[1.0,0.0]",
        embedding_vector_fingerprint="vector",
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
        acted_by="local operator",
        created_at=created_at,
    )
    return InverseOptimizationRequest(
        schema_version="inverse_optimization_request_v1",
        domain_id=DOMAIN_ID,
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


def _client(monkeypatch: Any, **overrides: Any) -> TestClient:
    defaults = {
        "get_decision_evidence_head": lambda domain_id: {**EVIDENCE_HEAD, "domain_id": domain_id},
        "load_inverse_optimization_request": lambda domain_id: _empty_request(),
        "inspect_ranking_policy_lifecycle": lambda domain_id, limit=None: {
            "training_runs": [],
            "snapshots": [],
            "events": [],
        },
        "resolve_active_ranking_policy": lambda domain_id, runtime_fingerprint: None,
        "activate_ranking_policy_candidate": lambda snapshot_id, **kwargs: {
            "policy_snapshot_id": snapshot_id,
            "status": "active",
        },
        "reject_ranking_policy_candidate": lambda snapshot_id, **kwargs: {
            "policy_snapshot_id": snapshot_id,
            "status": "rejected",
        },
        "rollback_ranking_policy": lambda domain_id, **kwargs: {"status": "zero_residual"},
    }
    defaults.update(overrides)
    for name, value in defaults.items():
        monkeypatch.setattr(app_module.sqlite_store_module, name, value)
    return TestClient(app_module.create_app(redis_url="redis://localhost:6379/0"))


def test_optimization_page_renders_empty_native_state(monkeypatch: Any) -> None:
    """@proves admin_control_plane_core.jinja2-admin-pages
    @proves inspection_debugging.ranking-diagnostics
    @proves ui_consistency_theming.shared-component-classes
    @proves ui_consistency_theming.human-readable-section-headings
    """
    response = _client(monkeypatch).get("/admin/optimization")

    assert response.status_code == 200
    assert "Preference Optimization" in response.text
    assert 'href="/admin/optimization"' in response.text
    assert "zero residual" in response.text
    assert "No saved rating evidence yet" in response.text
    assert "Optimize Current Evidence" in response.text
    assert "disabled" in response.text
    assert "Training Runs" in response.text
    assert "Policy Snapshots" in response.text
    assert "Activation Events" in response.text


def test_candidate_post_uses_submitted_compare_tokens_and_prg(monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}

    def create_candidate(request: Any, **kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        assert request == _empty_request()
        return {"status": "candidate_created", "policy_snapshot_id": "snapshot-1"}

    monkeypatch.setattr(app_module, "create_ranking_policy_candidate", create_candidate)
    evidence = {
        **EVIDENCE_HEAD,
        "episodes": [{"episode_id": "episode-1", "events": [{"event_id": "event-1"}]}],
    }
    response = _client(
        monkeypatch,
        get_decision_evidence_head=lambda domain_id: {**evidence, "domain_id": domain_id},
    ).post(
        "/admin/optimization/candidate",
        data={
            "domain_id": DOMAIN_ID,
            "evidence_head_fingerprint": "submitted-head",
            "expected_parent_ref": "zero_residual:baseline",
            "optimizer_numeric_parameter": "999",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/optimization?notice=candidate_created"
    assert captured["expected_evidence_head_fingerprint"] == "submitted-head"
    assert captured["expected_parent_ref"] == "zero_residual:baseline"
    assert "optimizer_numeric_parameter" not in captured


def test_activate_candidate_normalizes_actor_and_uses_cas_tokens(monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}
    candidate = {
        "policy_snapshot_id": "snapshot-1",
        "domain_id": DOMAIN_ID,
        "status": "candidate",
        "parent_policy_ref": "zero_residual:baseline",
    }

    def activate(snapshot_id: str, **kwargs: Any) -> dict[str, Any]:
        captured["snapshot_id"] = snapshot_id
        captured.update(kwargs)
        return {**candidate, "status": "active"}

    response = _client(
        monkeypatch,
        inspect_ranking_policy_lifecycle=lambda domain_id, limit=None: {
            "training_runs": [],
            "snapshots": [candidate],
            "events": [],
        },
        activate_ranking_policy_candidate=activate,
    ).post(
        "/admin/optimization/candidates/snapshot-1/activate",
        data={
            "actor": "  local operator  ",
            "expected_parent_ref": "zero_residual:baseline",
            "evidence_head_fingerprint": "evidence-head",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/optimization?notice=activation_completed"
    assert captured["snapshot_id"] == "snapshot-1"
    assert captured["acted_by"] == "local operator"
    assert captured["expected_parent_ref"] == "zero_residual:baseline"
    assert captured["evidence_head_fingerprint"] == "evidence-head"


def test_optimization_page_shows_canonical_saved_rating_evidence(monkeypatch: Any) -> None:
    """@proves inspection_debugging.decision-feedback-review"""
    request = _rated_request()
    evidence = {
        **EVIDENCE_HEAD,
        "event_watermark": 1,
        "episodes": [{"episode_id": "episode-1", "events": [{"event_id": "event-1"}]}],
    }

    response = _client(
        monkeypatch,
        get_decision_evidence_head=lambda domain_id: {**evidence, "domain_id": domain_id},
        load_inverse_optimization_request=lambda domain_id: request,
    ).get("/admin/optimization")

    assert response.status_code == 200
    assert "Rating Evidence" in response.text
    assert 'href="/admin/runs/run-1"' in response.text
    assert 'href="https://example.test/job-1"' in response.text
    assert "5 stars" in response.text
    assert ">7<" in response.text
    assert "strong" in response.text
