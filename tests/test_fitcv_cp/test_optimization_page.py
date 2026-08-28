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
import re
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

import fitcv_cp.app as app_module
import fitcv_cp.local_routes as local_routes_module
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
    monkeypatch.setenv("FITCV_LOCAL_MODE", "1")
    active_settings = overrides.pop(
        "active_settings",
        {
            "preference_optimization.ranking_mode": "personalized",
            "preference_optimization.personalization_strength": 0.05,
        },
    )
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
        "list_preference_optimization_runs": lambda limit=100: [],
        "get_preference_optimization_run": lambda run_id: (_ for _ in ()).throw(
            KeyError(run_id)
        ),
        "activate_preference_optimization_run": lambda run_id, **kwargs: {
            "preference_optimization_run_id": run_id,
            "policy_status": "active",
        },
        "inactivate_preference_optimization_run": lambda run_id, **kwargs: {
            "preference_optimization_run_id": run_id,
            "policy_status": "retired",
        },
        "hide_preference_optimization_run": lambda run_id: {
            "preference_optimization_run_id": run_id,
            "hidden_at": "2026-07-23T12:00:00+00:00",
        },
        "get_process_events": lambda process_type, process_id, limit=200, cursor=None: {
            "events": [],
            "integrity_conflicts": [],
            "deliveries": [],
            "total_count": 0,
            "next_cursor": None,
        },
    }
    defaults.update(overrides)
    for name, value in defaults.items():
        monkeypatch.setattr(app_module.sqlite_store_module, name, value)
    monkeypatch.setattr(app_module, "load_active_settings", lambda: active_settings)
    monkeypatch.setattr(local_routes_module, "onboarding_is_complete", lambda: True)
    app = app_module.create_app(redis_url="redis://localhost:6379/0")
    client = TestClient(app, base_url="http://127.0.0.1")
    client.headers.update(
        {
            "Origin": "http://127.0.0.1",
            "X-FitCV-CSRF": str(app.state.csrf_token),
        }
    )
    return client

def _button_tag(html: str, label: str) -> str:
    match = re.search(rf"<button[^>]*>{re.escape(label)}</button>", html)
    assert match is not None
    return match.group(0)

def test_optimization_context_reads_settings_after_projection_migration(
    monkeypatch: Any,
) -> None:
    migrated = False
    active_settings = {
        "preference_optimization.ranking_mode": "baseline",
        "preference_optimization.personalization_strength": 0.05,
    }

    class MigratingStore:
        def inspect_ranking_policy_lifecycle(self, domain_id: str, limit: int) -> dict[str, Any]:
            nonlocal migrated
            migrated = True
            return {"training_runs": [], "snapshots": [], "events": []}

        def get_decision_evidence_head(self, domain_id: str) -> dict[str, Any]:
            return {**EVIDENCE_HEAD, "domain_id": domain_id}

        def load_inverse_optimization_request(self, domain_id: str) -> InverseOptimizationRequest:
            return _empty_request()

        def resolve_active_ranking_policy(
            self, domain_id: str, runtime_fingerprint: str
        ) -> None:
            return None

        def list_preference_optimization_runs(self, limit: int) -> list[dict[str, Any]]:
            return []

        def get_process_events(
            self, process_type: str, process_id: str, limit: int
        ) -> dict[str, Any]:
            return {
                "events": [],
                "integrity_conflicts": [],
                "deliveries": [],
                "total_count": 0,
                "next_cursor": None,
            }

    monkeypatch.setattr(
        app_module,
        "load_active_settings",
        lambda: active_settings if migrated else {},
    )

    context = app_module._optimization_page_context(MigratingStore())

    assert context["settings_revision"] == app_module.settings_revision(active_settings)


def test_optimization_page_allows_grid_to_shrink_on_narrow_viewports(
    monkeypatch: Any,
) -> None:
    response = _client(monkeypatch).get("/admin/optimization")

    assert ".optimization-stack { display:grid; gap:14px; min-width:0; }" in response.text
    assert (
        ".optimization-stack > .section-card, .optimization-stack > .card "
        "{ margin-bottom:0; min-width:0; }"
    ) in response.text


def test_optimization_notice_projection_marks_stale_and_retryable_states() -> None:
    from fitcv_cp.app import _optimization_notice_projection

    stale = _optimization_notice_projection("stale_evidence")
    retryable = _optimization_notice_projection("operation_failed")

    assert stale["kind"] == "stale"
    assert stale["action"] == "Reload current state"
    assert retryable["kind"] == "retryable"
    assert retryable["action"] == "Retry"


def test_optimization_page_renders_empty_native_state(monkeypatch: Any) -> None:
    """@proves admin_control_plane_core.jinja2-admin-pages
    @proves inspection_debugging.ranking-diagnostics
    @proves ui_consistency_theming.shared-component-classes
    @proves ui_consistency_theming.human-readable-section-headings
    """
    response = _client(monkeypatch).get("/admin/optimization")

    assert response.status_code == 200
    assert "Preference Optimization" in response.text
    assert "Ranking Mode" in response.text
    assert "Baseline Ranking" in response.text
    assert "Personalized Ranking" in response.text
    assert "Personalization Strength" in response.text
    assert "Rating Evidence" in response.text
    assert "Optimization Runs" in response.text
    assert 'class="page-head"' in response.text
    assert response.text.count(
        'class="section-card collapsible-section setting-section" open'
    ) == 4
    assert 'class="section-content settings-card"' in response.text
    assert 'class="btn primary"' in response.text
    assert 'class="field preference-mode-field" id="preferenceRankingMode"' in response.text
    assert 'data-header-description="Configure ranking mode, rating evidence, and optimization runs."' in response.text
    assert "Higher values allow larger changes from Baseline Ranking." in response.text
    assert 'class="empty-state"' in response.text
    assert "No saved ratings" in response.text
    assert "Ratings from completed runs will appear here." in response.text
    assert "No optimization runs" in response.text
    assert "Use Optimize Current Ratings to create one." in response.text
    assert "Optimize Current Ratings" in response.text
    assert "Training Runs" not in response.text
    assert "Policy Snapshots" not in response.text
    assert "Activation Events" not in response.text
    assert "Technical Details" not in response.text

def test_baseline_page_disables_personalization_and_run_actions(monkeypatch: Any) -> None:
    run = {
        "preference_optimization_run_id": "por_public",
        "domain_id": DOMAIN_ID,
        "status": "candidate_created",
        "policy_snapshot_id": "rps_policy",
        "policy_status": "candidate",
        "hidden_at": None,
        "created_at": "2026-07-23T12:00:00+00:00",
        "personalization_strength": 0.05,
        "evidence_head_fingerprint": "evidence-head",
        "rating_evidence_rows_json": [],
    }
    response = _client(
        monkeypatch,
        active_settings={
            "preference_optimization.ranking_mode": "baseline",
            "preference_optimization.personalization_strength": 0.05,
        },
        list_preference_optimization_runs=lambda limit=100: [run],
    ).get("/admin/optimization")

    assert response.status_code == 200
    assert "disabled" in _button_tag(response.text, "Manage")
    assert "disabled" in _button_tag(response.text, "Optimize Current Ratings")
    assert "disabled" in _button_tag(response.text, "Activate Policy")
    assert "disabled" in _button_tag(response.text, "Remove")
    assert 'class="small-action"' in response.text
    assert 'class="optimization-status"' in response.text
    assert "Choose Personalized Ranking to manage this setting." in response.text
    assert "Choose Personalized Ranking to optimize ratings." in response.text
    assert "Choose Personalized Ranking to use these actions." in response.text

def test_personalized_fallback_and_incompatible_active_policy_are_visible(
    monkeypatch: Any,
) -> None:
    active_snapshot = {
        "policy_snapshot_id": "rps_active",
        "training_run_id": "itr_internal",
        "status": "active",
        "parent_policy_ref": "zero_residual:baseline",
    }
    run = {
        "preference_optimization_run_id": "por_public",
        "domain_id": DOMAIN_ID,
        "status": "candidate_created",
        "policy_snapshot_id": "rps_active",
        "policy_status": "active",
        "hidden_at": None,
        "created_at": "2026-07-23T12:00:00+00:00",
        "personalization_strength": 0.05,
        "evidence_head_fingerprint": "evidence-head",
        "rating_evidence_rows_json": [],
    }
    response = _client(
        monkeypatch,
        inspect_ranking_policy_lifecycle=lambda domain_id, limit=None: {
            "training_runs": [],
            "snapshots": [active_snapshot],
            "events": [],
            "active_snapshot": active_snapshot,
        },
        resolve_active_ranking_policy=lambda domain_id, runtime_fingerprint: None,
        list_preference_optimization_runs=lambda limit=100: [run],
    ).get("/admin/optimization")

    assert response.status_code == 200
    assert "Baseline Ranking is being used until a policy is activated." in response.text
    assert "Active · Not in use" in response.text
    assert "disabled" not in _button_tag(response.text, "Inactivate Policy")
    assert "disabled" in _button_tag(response.text, "Remove")
    assert "Inactivate Policy before removing this run." in response.text

def test_run_without_policy_is_not_projected_as_active(monkeypatch: Any) -> None:
    run = {
        "preference_optimization_run_id": "por_no_policy",
        "domain_id": DOMAIN_ID,
        "status": "insufficient_evidence",
        "policy_snapshot_id": None,
        "policy_status": None,
        "hidden_at": None,
        "created_at": "2026-07-23T12:00:00+00:00",
        "personalization_strength": 0.05,
        "evidence_head_fingerprint": "evidence-head",
        "rating_evidence_rows_json": [],
    }
    response = _client(
        monkeypatch,
        list_preference_optimization_runs=lambda limit=100: [run],
    ).get("/admin/optimization")

    assert response.status_code == 200
    assert "Not Created" in response.text
    assert "Not created" in response.text
    assert "Activate Policy" not in response.text
    assert "Inactivate Policy" not in response.text
    assert "disabled" not in _button_tag(response.text, "Remove")


def test_candidate_post_uses_submitted_compare_tokens_and_prg(monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}
    active_settings = {
        "preference_optimization.ranking_mode": "personalized",
        "preference_optimization.personalization_strength": 0.08,
    }

    def create_candidate(request: Any, **kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        assert request == _empty_request()
        return {"status": "candidate_created", "policy_snapshot_id": "snapshot-1"}

    monkeypatch.setattr(app_module, "create_ranking_policy_candidate", create_candidate)
    monkeypatch.setattr(app_module, "load_active_settings", lambda: active_settings)
    evidence = {
        **EVIDENCE_HEAD,
        "episodes": [{"episode_id": "episode-1", "events": [{"event_id": "event-1"}]}],
    }
    response = _client(
        monkeypatch,
        active_settings=active_settings,
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
    assert captured["ranking_mode"] == "personalized"
    assert captured["personalization_strength"] == 0.08
    assert captured["settings_revision"] == app_module.settings_revision(active_settings)
    assert "optimizer_numeric_parameter" not in captured


def test_candidate_post_persists_accepted_insufficient_evidence(monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}
    active_settings = {
        "preference_optimization.ranking_mode": "personalized",
        "preference_optimization.personalization_strength": 0.05,
    }

    def create_candidate(request: Any, **kwargs: Any) -> dict[str, Any]:
        captured["request"] = request
        captured.update(kwargs)
        return {
            "status": "insufficient_evidence",
            "error_code": "zero_rating_evidence",
            "preference_optimization_run_id": "por_test",
        }

    monkeypatch.setattr(app_module, "create_ranking_policy_candidate", create_candidate)
    monkeypatch.setattr(app_module, "load_active_settings", lambda: active_settings)

    response = _client(monkeypatch).post(
        "/admin/optimization/candidate",
        data={
            "domain_id": DOMAIN_ID,
            "evidence_head_fingerprint": "evidence-head",
            "expected_parent_ref": "zero_residual:baseline",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/admin/optimization?notice=insufficient_evidence"
    )
    assert captured["request"] == _empty_request()


def test_candidate_post_prefers_service_error_code_for_stale_prg(monkeypatch: Any) -> None:
    active_settings = {
        "preference_optimization.ranking_mode": "personalized",
        "preference_optimization.personalization_strength": 0.05,
    }

    monkeypatch.setattr(
        app_module,
        "create_ranking_policy_candidate",
        lambda *_args, **_kwargs: {
            "status": "stale",
            "error_code": "optimization_precondition_changed",
        },
    )
    monkeypatch.setattr(app_module, "load_active_settings", lambda: active_settings)

    response = _client(monkeypatch).post(
        "/admin/optimization/candidate",
        data={
            "domain_id": DOMAIN_ID,
            "evidence_head_fingerprint": "evidence-head",
            "expected_parent_ref": "zero_residual:baseline",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/admin/optimization?notice=optimization_precondition_changed"
    )


def test_ranking_mode_post_uses_revisioned_workspace_setting(monkeypatch: Any) -> None:
    active_settings = {
        "preference_optimization.ranking_mode": "baseline",
        "preference_optimization.personalization_strength": 0.05,
    }
    captured: dict[str, Any] = {}

    def mutate(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {**active_settings, **kwargs["changes"]}

    monkeypatch.setattr(app_module, "mutate_settings_atomically", mutate)
    response = _client(monkeypatch, active_settings=active_settings).post(
        "/admin/optimization/ranking-mode",
        data={
            "ranking_mode": "personalized",
            "settings_revision": app_module.settings_revision(active_settings),
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/optimization?notice=ranking_mode_saved"
    assert captured == {
        "changes": {"preference_optimization.ranking_mode": "personalized"},
        "updated_by": "local_workspace",
        "expected_revision": app_module.settings_revision(active_settings),
    }


def test_personalization_strength_post_rejects_baseline(monkeypatch: Any) -> None:
    response = _client(
        monkeypatch,
        active_settings={
            "preference_optimization.ranking_mode": "baseline",
            "preference_optimization.personalization_strength": 0.05,
        },
    ).post(
        "/admin/optimization/personalization-strength",
        data={"value": "0.08", "settings_revision": "revision"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/admin/optimization?notice=personalized_ranking_required"
    )

def test_personalization_strength_post_rejects_active_policy(monkeypatch: Any) -> None:
    response = _client(
        monkeypatch,
        inspect_ranking_policy_lifecycle=lambda domain_id, limit=None: {
            "training_runs": [],
            "snapshots": [{"policy_snapshot_id": "rps_active", "status": "active"}],
            "events": [],
        },
    ).post(
        "/admin/optimization/personalization-strength",
        data={"value": "0.08", "settings_revision": "revision"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/admin/optimization?notice=active_policy_must_be_inactivated"
    )


def test_public_run_mutations_use_server_actor_and_baseline_guards(
    monkeypatch: Any,
) -> None:
    run = {
        "preference_optimization_run_id": "por_public",
        "domain_id": DOMAIN_ID,
        "policy_snapshot_id": "rps_policy",
        "policy_status": "candidate",
        "hidden_at": None,
        "evidence_head_fingerprint": "evidence-head",
    }
    captured: dict[str, Any] = {}

    def activate(run_id: str, **kwargs: Any) -> dict[str, Any]:
        captured["run_id"] = run_id
        captured.update(kwargs)
        return {**run, "policy_status": "active"}

    response = _client(
        monkeypatch,
        get_preference_optimization_run=lambda run_id: run,
        activate_preference_optimization_run=activate,
    ).post(
        "/admin/optimization/runs/por_public/activate",
        data={
            "actor": "spoofed",
            "expected_parent_ref": "zero_residual:baseline",
            "evidence_head_fingerprint": "evidence-head",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/admin/optimization/runs/por_public?notice=activation_completed"
    )
    assert captured["run_id"] == "por_public"
    assert "actor" not in captured
    assert "acted_by" not in captured

    blocked = _client(
        monkeypatch,
        active_settings={
            "preference_optimization.ranking_mode": "baseline",
            "preference_optimization.personalization_strength": 0.05,
        },
        get_preference_optimization_run=lambda run_id: run,
    ).post(
        "/admin/optimization/runs/por_public/remove",
        follow_redirects=False,
    )

    assert blocked.status_code == 303
    assert blocked.headers["location"] == (
        "/admin/optimization/runs/por_public?notice=personalized_ranking_required"
    )

def test_public_run_inactivation_requires_confirmation_and_uses_active_snapshot(
    monkeypatch: Any,
) -> None:
    captured: dict[str, Any] = {}

    def inactivate(run_id: str, **kwargs: Any) -> dict[str, Any]:
        captured["run_id"] = run_id
        captured.update(kwargs)
        return {
            "preference_optimization_run_id": run_id,
            "policy_status": "retired",
        }

    client = _client(
        monkeypatch,
        inactivate_preference_optimization_run=inactivate,
    )
    blocked = client.post(
        "/admin/optimization/runs/por_public/inactivate",
        data={"expected_active_snapshot_id": "rps_active"},
        follow_redirects=False,
    )

    assert blocked.status_code == 303
    assert blocked.headers["location"] == (
        "/admin/optimization/runs/por_public?notice=inactivation_confirmation_required"
    )
    assert captured == {}

    response = client.post(
        "/admin/optimization/runs/por_public/inactivate",
        data={"confirm": "on", "expected_active_snapshot_id": "rps_active"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/admin/optimization/runs/por_public?notice=inactivation_completed"
    )
    assert captured == {
        "run_id": "por_public",
        "expected_active_snapshot_id": "rps_active",
    }

def test_public_run_remove_hides_non_active_run_and_rejects_active_owner(
    monkeypatch: Any,
) -> None:
    captured: list[str] = []

    response = _client(
        monkeypatch,
        hide_preference_optimization_run=lambda run_id: captured.append(run_id),
    ).post(
        "/admin/optimization/runs/por_public/remove",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/admin/optimization?notice=optimization_run_removed"
    )
    assert captured == ["por_public"]

    def reject_active(run_id: str) -> None:
        raise ValueError("active_policy_must_be_inactivated")

    blocked = _client(
        monkeypatch,
        hide_preference_optimization_run=reject_active,
    ).post(
        "/admin/optimization/runs/por_public/remove",
        follow_redirects=False,
    )

    assert blocked.status_code == 303
    assert blocked.headers["location"] == (
        "/admin/optimization/runs/por_public?notice=active_policy_must_be_inactivated"
    )


def test_optimization_detail_uses_public_id_only(monkeypatch: Any) -> None:
    response = _client(monkeypatch).get(
        "/admin/optimization/runs/itr_internal",
        follow_redirects=False,
    )

    assert response.status_code == 404


def test_optimization_console_matches_public_run_and_policy_snapshot_refs() -> None:
    console = {
        "events": [
            SimpleNamespace(
                diagnostic_refs=None,
                diagnostic_refs_json='[{"id":"por_public"}]',
            ),
            SimpleNamespace(
                diagnostic_refs=None,
                diagnostic_refs_json='[{"id":"rps_policy"}]',
            ),
            SimpleNamespace(
                diagnostic_refs=None,
                diagnostic_refs_json='[{"id":"por_other"}]',
            ),
        ],
        "total_count": 3,
    }

    filtered = app_module._optimization_console_for_run(
        console,
        {
            "preference_optimization_run_id": "por_public",
            "policy_snapshot_id": "rps_policy",
        },
    )

    assert len(filtered["events"]) == 2
    assert filtered["total_count"] == 2


def test_optimization_detail_renders_public_run_and_unknown_public_id_is_404(
    monkeypatch: Any,
) -> None:
    run = {
        "preference_optimization_run_id": "por_public",
        "domain_id": DOMAIN_ID,
        "status": "candidate_created",
        "policy_snapshot_id": "rps_policy",
        "policy_status": "candidate",
        "hidden_at": None,
        "created_at": "2026-07-23T12:00:00+00:00",
        "personalization_strength": 0.05,
        "evidence_head_fingerprint": "evidence-head",
        "rating_evidence_rows_json": [],
    }
    client = _client(
        monkeypatch,
        get_preference_optimization_run=lambda run_id: (
            run if run_id == "por_public" else (_ for _ in ()).throw(KeyError(run_id))
        ),
    )

    response = client.get("/admin/optimization/runs/por_public")
    missing = client.get("/admin/optimization/runs/por_missing")

    assert response.status_code == 200
    assert "Optimization por_public" in response.text
    assert "Overview" in response.text
    assert "Rating Evidence" in response.text
    assert "Console Log" in response.text
    assert 'class="details-grid"' in response.text
    assert 'class="console-log"' in response.text
    assert "Review one optimization run." in response.text
    assert 'data-header-title="Preference Optimization"' in response.text
    assert 'class="details-page-back"' in response.text
    assert response.text.count(
        'class="section-card collapsible-section drawer-section'
    ) == 3
    assert "Activate Policy" in response.text
    assert "Results Summary" not in response.text
    assert "Technical Details" not in response.text
    assert "Reject Version" not in response.text
    assert missing.status_code == 404

    run["hidden_at"] = "2026-07-23T12:30:00+00:00"
    hidden = client.get("/admin/optimization/runs/por_public")

    assert hidden.status_code == 200
    assert "Removed from Optimization Runs" in hidden.text
    assert "Activate Policy" not in hidden.text
    assert "Inactivate Policy" not in hidden.text


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
    assert "5 / 5" in response.text
    assert ">7<" in response.text
