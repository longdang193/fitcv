import datetime

from fitcv_cp.models import PipelineRun, RunStatus
from fitcv_cp.models import RunEvent
from fitcv_cp.store import ControlPlaneStore


def _run() -> PipelineRun:
    return PipelineRun(
        run_id="rid-1",
        status=RunStatus.QUEUED,
        triggered_by="tester",
        trigger_source="web",
        jobs_path="data/jobs.json",
        config_path=".env.yaml",
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )


def test_control_plane_store_uses_injected_insert_fn() -> None:
    captured: dict[str, object] = {}

    def _insert(run):
        captured["run"] = run

    store = ControlPlaneStore(insert_run_fn=_insert)
    store.insert_run(_run())
    assert isinstance(captured["run"], PipelineRun)


def test_control_plane_store_uses_injected_binding_fn() -> None:
    captured: dict[str, object] = {}

    def _binding(run_id, *, queue_job_id, orchestration_backend, orchestration_run_id):
        captured["run_id"] = run_id
        captured["queue_job_id"] = queue_job_id
        captured["backend"] = orchestration_backend
        captured["backend_run_id"] = orchestration_run_id
        return {"persistence_status": "persisted", "degradation_reason": "none"}

    store = ControlPlaneStore(update_run_orchestration_binding_fn=_binding)
    store.update_run_orchestration_binding(
        "rid-1",
        queue_job_id="q1",
        orchestration_backend="inline",
        orchestration_run_id="inline-1",
    )
    assert captured["run_id"] == "rid-1"
    assert captured["queue_job_id"] == "q1"
    assert captured["backend"] == "inline"


def test_control_plane_store_uses_injected_get_run_fn() -> None:
    run = _run()

    def _get(run_id):
        assert run_id == run.run_id
        return run

    store = ControlPlaneStore(get_run_fn=_get)
    result = store.get_run(run.run_id)
    assert result is run


def test_control_plane_store_uses_injected_update_status_fn() -> None:
    captured: dict[str, object] = {}

    def _update(run_id, status, **kwargs):
        captured["run_id"] = run_id
        captured["status"] = status
        captured["kwargs"] = kwargs
        return {"persistence_status": "persisted", "degradation_reason": "none"}

    store = ControlPlaneStore(update_run_status_fn=_update)
    store.update_run_status("rid-1", RunStatus.RUNNING, started_at=datetime.datetime.now(datetime.timezone.utc))
    assert captured["run_id"] == "rid-1"
    assert captured["status"] == RunStatus.RUNNING


def test_control_plane_store_uses_injected_archive_fn() -> None:
    captured: dict[str, object] = {}

    def _archive(run_id, archived_by):
        captured["run_id"] = run_id
        captured["archived_by"] = archived_by

    store = ControlPlaneStore(archive_run_fn=_archive)
    store.archive_run("rid-1", "admin")
    assert captured["run_id"] == "rid-1"
    assert captured["archived_by"] == "admin"


def test_control_plane_store_uses_injected_delete_archived_runs_fn() -> None:
    captured: dict[str, object] = {}

    def _delete_archived_runs(older_than_days, run_ids=None):
        captured["older_than_days"] = older_than_days
        captured["run_ids"] = run_ids
        return {"deleted_count": 2, "deleted_run_ids": ["rid-1", "rid-2"]}

    store = ControlPlaneStore(delete_archived_runs_fn=_delete_archived_runs)
    result = store.delete_archived_runs(30, ["run-old-archived"])
    assert captured["older_than_days"] == 30
    assert captured["run_ids"] == ["run-old-archived"]
    assert result["deleted_count"] == 2


def test_control_plane_store_uses_injected_cv_read_fns() -> None:
    def _list_cvs(run_id):
        assert run_id == "rid-1"
        return [{"version_id": "v1"}]

    def _get_md(version_id):
        assert version_id == "v1"
        return "# CV"

    store = ControlPlaneStore(
        list_cvs_for_run_fn=_list_cvs,
        get_cv_markdown_fn=_get_md,
    )
    rows = store.list_cvs_for_run("rid-1")
    assert rows == [{"version_id": "v1"}]
    assert store.get_cv_markdown("v1") == "# CV"


def test_control_plane_store_uses_injected_pipeline_runs_schema_status_fn() -> None:
    def _schema_status():
        return {"status": "complete", "missing_columns": [], "warning": None}

    store = ControlPlaneStore(get_pipeline_runs_schema_status_fn=_schema_status)
    status = store.get_pipeline_runs_schema_status()
    assert status["status"] == "complete"


def test_control_plane_store_uses_injected_event_and_snapshot_write_fns() -> None:
    captured: dict[str, object] = {}

    def _append(event):
        captured["event_id"] = event.event_id
        return {"persistence_status": "persisted", "degradation_reason": "none"}

    def _effective(run_id, effective_settings_json):
        captured["effective_run_id"] = run_id
        captured["effective_json"] = effective_settings_json
        return {"persistence_status": "persisted", "degradation_reason": "none"}

    def _synonyms(run_id, synonym_proposals_json):
        captured["syn_run_id"] = run_id
        return {"persistence_status": "persisted", "degradation_reason": ""}

    def _cv_debug(run_id, cv_generation_debug_json):
        captured["cv_debug_run_id"] = run_id
        return {"persistence_status": "persisted", "degradation_reason": "none"}

    def _insert_cv(row):
        captured["cv_row_version_id"] = row.get("version_id")
        return []

    store = ControlPlaneStore(
        append_event_fn=_append,
        update_run_effective_settings_fn=_effective,
        update_run_synonym_proposals_fn=_synonyms,
        update_run_cv_generation_debug_fn=_cv_debug,
        insert_cv_version_row_fn=_insert_cv,
    )
    event = RunEvent(
        run_id="rid-1",
        event_id="ev-1",
        stage="test",
        level="info",
        message="ok",
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )
    response = store.append_event(event)
    store.update_run_effective_settings("rid-1", "{}")
    store.update_run_synonym_proposals("rid-1", "{}")
    store.update_run_cv_generation_debug("rid-1", "{}")
    store.insert_cv_version_row({"version_id": "v1"})

    assert response["persistence_status"] == "persisted"
    assert captured["effective_run_id"] == "rid-1"
    assert captured["syn_run_id"] == "rid-1"
    assert captured["cv_debug_run_id"] == "rid-1"
    assert captured["cv_row_version_id"] == "v1"


def test_control_plane_store_lists_run_attempt_payloads_from_events() -> None:
    import json as _json

    from fitcv_cp.run_artifact_contracts import run_attempt_payload_v1

    now = datetime.datetime.now(datetime.timezone.utc)
    attempt_payload = run_attempt_payload_v1(attempt_id="a1", status="running")
    store = ControlPlaneStore(
        get_events_fn=lambda run_id: [
            RunEvent(
                run_id=run_id,
                event_id="ev-1",
                stage="test",
                level="info",
                message="ok",
                created_at=now,
                payload_json=_json.dumps(attempt_payload),
            )
        ],
    )

    payloads = store.list_run_attempt_payloads("rid-1")
    assert len(payloads) == 1
    assert payloads[0]["attempt"]["attempt_id"] == "a1"


def test_control_plane_store_delegates_decision_feedback() -> None:
    captured: dict[str, object] = {}

    def _write(episode, alternatives, event):
        captured["episode"] = episode
        captured["alternatives"] = alternatives
        captured["event"] = event
        return {"persistence_status": "persisted", "degradation_reason": "none"}

    store = ControlPlaneStore(
        materialize_episode_and_append_rating_fn=_write,
        list_decision_rating_events_for_run_fn=lambda run_id: [run_id],
    )
    result = store.materialize_episode_and_append_rating("episode", ["alternative"], "event")

    assert result["persistence_status"] == "persisted"
    assert captured == {
        "episode": "episode",
        "alternatives": ["alternative"],
        "event": "event",
    }
    assert store.list_decision_rating_events_for_run("run-1") == ["run-1"]


def test_control_plane_store_preference_policy_adapters() -> None:
    captured: dict[str, object] = {}
    store = ControlPlaneStore(
        persist_inverse_training_result_fn=lambda row: {**row, "stored": True},
        insert_ranking_policy_candidate_fn=lambda row: {**row, "inserted": True},
        resolve_active_ranking_policy_fn=lambda domain, runtime: {
            "domain_id": domain,
            "runtime_contract_fingerprint": runtime,
        },
        inspect_ranking_policy_lifecycle_fn=lambda domain: {"domain_id": domain},
        activate_ranking_policy_candidate_fn=lambda snapshot, **kwargs: captured.update(
            {"snapshot": snapshot, **kwargs}
        )
        or {"status": "active"},
    )

    assert store.persist_inverse_training_result({"id": "training"})["stored"] is True
    assert store.insert_ranking_policy_candidate({"id": "snapshot"})["inserted"] is True
    assert store.resolve_active_ranking_policy("ranking_v1", "runtime")["domain_id"] == "ranking_v1"
    assert store.inspect_ranking_policy_lifecycle("ranking_v1") == {"domain_id": "ranking_v1"}
    assert store.activate_ranking_policy_candidate(
        "snapshot", expected_parent_ref="zero_residual:baseline", acted_by="operator"
    )["status"] == "active"
    assert captured["snapshot"] == "snapshot"


def test_control_plane_store_candidate_attempt_and_evidence_head_adapters() -> None:
    store = ControlPlaneStore(
        persist_candidate_attempt_fn=lambda training, snapshot=None: {
            "training_run": training,
            "snapshot": snapshot,
        },
        get_decision_evidence_head_fn=lambda domain: {
            "domain_id": domain,
            "evidence_head_fingerprint": "head",
        },
    )

    result = store.persist_candidate_attempt(
        {"training_run_id": "training"}, {"policy_snapshot_id": "snapshot"}
    )
    assert result["snapshot"] == {"policy_snapshot_id": "snapshot"}
    assert store.get_decision_evidence_head("ranking_v1")["evidence_head_fingerprint"] == "head"
