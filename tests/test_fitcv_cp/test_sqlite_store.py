import concurrent.futures
import datetime
import json
import sqlite3
import uuid
from pathlib import Path

import pytest

from fitcv.preference_policy import build_policy_snapshot_identity, build_training_run_identity
from fitcv_cp import sqlite_store
from fitcv_cp.models import PipelineRun, RunEvent, RunStatus


@pytest.fixture(autouse=True)
def _sqlite_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "fitcv_cp.sqlite3"))
    monkeypatch.setattr(sqlite_store, "get_backend_runtime", lambda: None)


def _make_run(run_id: str = "run-1") -> PipelineRun:
    return PipelineRun(
        run_id=run_id,
        status=RunStatus.QUEUED,
        triggered_by="admin",
        trigger_source="ui",
        jobs_path="data/sample_jobs.json",
        config_path=".env.yaml",
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )


def test_insert_run_round_trips_from_sqlite() -> None:
    run = _make_run()

    sqlite_store.insert_run(run)
    stored = sqlite_store.get_run(run.run_id)

    assert stored is not None
    assert stored.run_id == run.run_id
    assert stored.status == RunStatus.QUEUED


def test_update_status_and_events_persist() -> None:
    run = _make_run("run-events")
    sqlite_store.insert_run(run)

    result = sqlite_store.update_run_status(
        run.run_id,
        RunStatus.RUNNING,
        None,
        project = "local",
        dataset = "fitcv",
        started_at=datetime.datetime.now(datetime.timezone.utc),
    )
    event = RunEvent(
        run_id=run.run_id,
        event_id=str(uuid.uuid4()),
        stage="enrich",
        level="info",
        message="started",
        created_at=datetime.datetime.now(datetime.timezone.utc),
        payload_json=json.dumps({"attempt": 1}),
    )
    sqlite_store.append_event(event)

    stored = sqlite_store.get_run(run.run_id)
    events = sqlite_store.get_events(run.run_id)

    assert result["persistence_status"] == "persisted"
    assert stored is not None
    assert stored.status == RunStatus.RUNNING
    assert len(events) == 1
    assert json.loads(str(events[0].payload_json)) == {"attempt": 1}


def test_run_json_updates_and_schema_status_use_sqlite_only_terms() -> None:
    run = _make_run("run-json")
    sqlite_store.insert_run(run)

    sqlite_store.update_run_results_export(
        run.run_id,
        json.dumps({"jobs": [{"job_url": "https://example.com/1"}]}),
        None,
        project = "local",
        dataset = "fitcv",
    )
    sqlite_store.update_run_stage_transition_artifacts(
        run.run_id,
        json.dumps({"artifacts": {"stages": {"enrich": {"status": "completed"}}}}),
        None,
        project = "local",
        dataset = "fitcv",
    )

    stored = sqlite_store.get_run(run.run_id)
    schema_status = sqlite_store.get_pipeline_runs_schema_status(None, project = "local", dataset = "fitcv")

    assert stored is not None
    assert json.loads(str(stored.results_export_json))["jobs"][0]["job_url"] == "https://example.com/1"
    assert schema_status["warning"] == "sqlite_mode_no_remote_schema_check"


def test_list_filter_results_for_run_decodes_marks_and_reasons() -> None:
    db_path = Path(sqlite_store._local_sqlite_path())
    with sqlite_store._sqlite_connection(db_path) as conn:
        sqlite_store._ensure_local_rule_filter_results_table(conn)
        conn.execute(
            """
            INSERT INTO rule_filter_results (
                run_id,
                job_url,
                passed,
                reasons,
                filtered_at,
                marks_json,
                raw_job_fingerprint,
                source_job_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "run-filter",
                "https://example.com/job-1",
                1,
                json.dumps(["matched_required_skills"]),
                datetime.datetime.now(datetime.timezone.utc).isoformat(),
                json.dumps([{"code": "required_skill"}]),
                "fp-1",
                "https://example.com/job-1",
            ),
        )
        conn.commit()

    rows = sqlite_store.list_filter_results_for_run("run-filter")

    assert len(rows) == 1
    assert rows[0]["passed"] is True
    assert rows[0]["reasons"] == ["matched_required_skills"]
    assert rows[0]["marks"] == [{"code": "required_skill"}]


def test_local_sqlite_path_uses_control_plane_config_when_env_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FITCV_CP_SQLITE_PATH", raising=False)
    config_path = tmp_path / "config" / "runtime" / "control_plane.yaml"
    config_path.parent.mkdir(parents=True)
    canonical_text = (
        Path(__file__).parents[2] / "config" / "runtime" / "control_plane.yaml"
    ).read_text(encoding="utf-8")
    assert "path: data/fitcv_cp.sqlite3" in canonical_text
    config_path.write_text(
        canonical_text.replace(
            "path: data/fitcv_cp.sqlite3",
            f"path: {(tmp_path / 'from-config.sqlite3').as_posix()}",
        ),
        encoding="utf-8",
    )

    assert Path(sqlite_store._local_sqlite_path()) == tmp_path / "from-config.sqlite3"


def _training_row() -> dict[str, object]:
    result = {"status": "candidate_created", "preference_vector": [0.1, -0.1]}
    row: dict[str, object] = {
        "schema_version": "inverse_training_run_v1",
        "domain_id": "ranking_v1",
        "status": "candidate_created",
        "cohort_fingerprint": "cohort",
        "event_watermark": 2,
        "edge_set_fingerprint": "edges",
        "rating_scale_version": "application-interest-v1",
        "compiler_version": "preference-compiler-v1",
        "compiler_policy_fingerprint": "compiler",
        "decision_learning_policy_fingerprint": "decision",
        "optimizer_policy_fingerprint": "optimizer",
        "activation_policy_fingerprint": "activation",
        "baseline_policy_fingerprint": "baseline",
        "ranking_contract_fingerprint": "ranking",
        "embedding_model": "model",
        "embedding_contract_fingerprint": "embedding",
        "embedding_dimension": 2,
        "learned_alpha": 0.05,
        "parent_policy_kind": "zero_residual",
        "parent_policy_ref": "zero_residual:baseline",
        "problem_fingerprint": "problem",
        "evaluation_fingerprint": "evaluation",
        "result_json": result,
    }
    row["training_run_id"] = build_training_run_identity(row)
    return row


def _snapshot_row(training_run_id: str, *, vector: list[float], suffix: str = "") -> dict[str, object]:
    row: dict[str, object] = {
        "schema_version": "ranking_policy_snapshot_v1",
        "domain_id": "ranking_v1",
        "status": "candidate",
        "runtime_contract_fingerprint": "runtime",
        "baseline_policy_fingerprint": "baseline",
        "ranking_contract_fingerprint": "ranking",
        "embedding_model": "model",
        "embedding_contract_fingerprint": "embedding",
        "embedding_dimension": 2,
        "learned_alpha": 0.05,
        "preference_vector_norm_bound": 1.0,
        "parent_policy_kind": "zero_residual",
        "parent_policy_ref": "zero_residual:baseline",
        "preference_vector_json": vector,
        "preference_vector_fingerprint": f"vector{suffix}",
        "training_run_id": training_run_id,
        "event_watermark": 2,
        "cohort_fingerprint": "cohort",
        "edge_set_fingerprint": "edges",
        "rating_scale_version": "application-interest-v1",
        "compiler_version": "preference-compiler-v1",
        "compiler_policy_fingerprint": "compiler",
        "decision_learning_policy_fingerprint": "decision",
        "optimizer_policy_fingerprint": "optimizer",
        "activation_policy_fingerprint": "activation",
        "problem_fingerprint": "problem",
        "solver_metadata_json": {"solver": "CLARABEL"},
        "evaluation_version": "episode-grouped-v1",
        "evaluation_fingerprint": "evaluation",
        "evaluation_json": {"passed": True},
    }
    fingerprint, snapshot_id = build_policy_snapshot_identity(row)
    row["payload_fingerprint"] = fingerprint
    row["policy_snapshot_id"] = snapshot_id
    return row


def _activation_provenance(**overrides: str) -> dict[str, str]:
    return {
        "current_runtime_contract_fingerprint": "runtime",
        "current_compiler_policy_fingerprint": "compiler",
        "current_decision_learning_policy_fingerprint": "decision",
        "current_optimizer_policy_fingerprint": "optimizer",
        "current_activation_policy_fingerprint": "activation",
        **overrides,
    }


def test_preference_policy_schema_enforces_immutable_payload_and_one_active() -> None:
    training = _training_row()
    sqlite_store.persist_inverse_training_result(training)
    first = _snapshot_row(str(training["training_run_id"]), vector=[0.1, -0.1], suffix="-a")
    second = _snapshot_row(str(training["training_run_id"]), vector=[-0.1, 0.1], suffix="-b")
    sqlite_store.insert_ranking_policy_candidate(first)
    sqlite_store.insert_ranking_policy_candidate(second)

    sqlite_store.activate_ranking_policy_candidate(
        str(first["policy_snapshot_id"]),
        expected_parent_ref="zero_residual:baseline",
        acted_by="operator",
        **_activation_provenance(),
    )

    db_path = Path(sqlite_store._local_sqlite_path())
    with sqlite_store._sqlite_connection(db_path) as conn:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute(
                "UPDATE ranking_policy_snapshots SET learned_alpha = 0.1 WHERE policy_snapshot_id = ?",
                (first["policy_snapshot_id"],),
            )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "UPDATE ranking_policy_snapshots SET status = 'active' WHERE policy_snapshot_id = ?",
                (second["policy_snapshot_id"],),
            )


def test_preference_policy_lifecycle_is_atomic_and_auditable() -> None:
    training = _training_row()
    sqlite_store.persist_inverse_training_result(training)
    snapshot = _snapshot_row(str(training["training_run_id"]), vector=[0.1, -0.1])
    sqlite_store.insert_ranking_policy_candidate(snapshot)

    activated = sqlite_store.activate_ranking_policy_candidate(
        str(snapshot["policy_snapshot_id"]),
        expected_parent_ref="zero_residual:baseline",
        acted_by="operator",
        **_activation_provenance(),
    )
    resolved = sqlite_store.resolve_active_ranking_policy("ranking_v1", "runtime")
    inspected = sqlite_store.inspect_ranking_policy_lifecycle("ranking_v1")

    assert activated["status"] == "active"
    assert resolved is not None
    assert resolved["policy_snapshot_id"] == snapshot["policy_snapshot_id"]
    assert [event["action"] for event in inspected["events"]] == ["activate"]

    rolled_back = sqlite_store.rollback_ranking_policy(
        "ranking_v1",
        expected_active=str(snapshot["policy_snapshot_id"]),
        target="zero_residual",
        acted_by="operator",
    )

    assert rolled_back["status"] == "zero_residual"
    assert sqlite_store.resolve_active_ranking_policy("ranking_v1", "runtime") is None


def test_activation_marks_candidate_stale_when_evidence_head_changed() -> None:
    training = _training_row()
    training["result_json"] = {
        **training["result_json"],
        "evidence_head_fingerprint": "head-before",
    }
    training["training_run_id"] = build_training_run_identity(training)
    snapshot = _snapshot_row(str(training["training_run_id"]), vector=[0.1, -0.1])
    sqlite_store.persist_candidate_attempt(training, snapshot)

    with pytest.raises(ValueError, match="candidate evidence changed"):
        sqlite_store.activate_ranking_policy_candidate(
            str(snapshot["policy_snapshot_id"]),
            expected_parent_ref="zero_residual:baseline",
            evidence_head_fingerprint="head-after",
            acted_by="operator",
            **_activation_provenance(),
        )

    lifecycle = sqlite_store.inspect_ranking_policy_lifecycle("ranking_v1")
    assert lifecycle["snapshots"][0]["status"] == "stale"
    assert lifecycle["events"][0]["reason_code"] == "evidence_changed"
    assert sqlite_store.resolve_active_ranking_policy("ranking_v1", "runtime") is None


@pytest.mark.parametrize(
    ("changed_field", "reason_code", "message"),
    (
        (
            "current_runtime_contract_fingerprint",
            "runtime_contract_changed",
            "candidate runtime contract changed",
        ),
        (
            "current_compiler_policy_fingerprint",
            "compiler_policy_changed",
            "candidate compiler policy changed",
        ),
        (
            "current_activation_policy_fingerprint",
            "activation_policy_changed",
            "candidate activation policy changed",
        ),
        (
            "current_optimizer_policy_fingerprint",
            "optimizer_policy_changed",
            "candidate optimizer policy changed",
        ),
        (
            "current_decision_learning_policy_fingerprint",
            "decision_learning_policy_changed",
            "candidate decision learning policy changed",
        ),
    ),
)
def test_activation_marks_candidate_stale_when_current_provenance_changed(
    changed_field: str,
    reason_code: str,
    message: str,
) -> None:
    training = _training_row()
    snapshot = _snapshot_row(str(training["training_run_id"]), vector=[0.1, -0.1])
    sqlite_store.persist_candidate_attempt(training, snapshot)

    with pytest.raises(ValueError, match=message):
        sqlite_store.activate_ranking_policy_candidate(
            str(snapshot["policy_snapshot_id"]),
            expected_parent_ref="zero_residual:baseline",
            acted_by="operator",
            **_activation_provenance(**{changed_field: "changed"}),
        )

    lifecycle = sqlite_store.inspect_ranking_policy_lifecycle("ranking_v1")
    assert lifecycle["snapshots"][0]["status"] == "stale"
    assert lifecycle["events"][0]["reason_code"] == reason_code


def test_concurrent_sibling_activation_has_one_winner() -> None:
    training = _training_row()
    sqlite_store.persist_inverse_training_result(training)
    snapshots = [
        _snapshot_row(str(training["training_run_id"]), vector=vector, suffix=suffix)
        for vector, suffix in (([0.1, -0.1], "-a"), ([-0.1, 0.1], "-b"))
    ]
    for snapshot in snapshots:
        sqlite_store.insert_ranking_policy_candidate(snapshot)

    def activate(snapshot_id: str) -> str:
        try:
            sqlite_store.activate_ranking_policy_candidate(
                snapshot_id,
                expected_parent_ref="zero_residual:baseline",
                acted_by="operator",
                **_activation_provenance(),
            )
        except ValueError as exc:
            return str(exc)
        return "active"

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(
            executor.map(activate, [str(snapshot["policy_snapshot_id"]) for snapshot in snapshots])
        )

    lifecycle = sqlite_store.inspect_ranking_policy_lifecycle("ranking_v1")
    assert sorted(outcomes) == ["active", "candidate parent changed"]
    assert [row["status"] for row in lifecycle["snapshots"]].count("active") == 1
    assert [row["status"] for row in lifecycle["snapshots"]].count("stale") == 1


def test_activation_event_failure_rolls_back_candidate_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    training = _training_row()
    snapshot = _snapshot_row(str(training["training_run_id"]), vector=[0.1, -0.1])
    sqlite_store.persist_candidate_attempt(training, snapshot)
    monkeypatch.setattr(
        sqlite_store,
        "_append_policy_event",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("event failed")),
    )

    with pytest.raises(RuntimeError, match="event failed"):
        sqlite_store.activate_ranking_policy_candidate(
            str(snapshot["policy_snapshot_id"]),
            expected_parent_ref="zero_residual:baseline",
            acted_by="operator",
            **_activation_provenance(),
        )

    lifecycle = sqlite_store.inspect_ranking_policy_lifecycle("ranking_v1")
    assert lifecycle["snapshots"][0]["status"] == "candidate"
    assert lifecycle["events"] == []


def test_rollback_restores_exact_learned_snapshot_then_zero_residual() -> None:
    training = _training_row()
    sqlite_store.persist_inverse_training_result(training)
    first = _snapshot_row(str(training["training_run_id"]), vector=[0.1, -0.1], suffix="-a")
    sqlite_store.insert_ranking_policy_candidate(first)
    sqlite_store.activate_ranking_policy_candidate(
        str(first["policy_snapshot_id"]),
        expected_parent_ref="zero_residual:baseline",
        acted_by="operator",
        **_activation_provenance(),
    )
    second = _snapshot_row(str(training["training_run_id"]), vector=[-0.1, 0.1], suffix="-b")
    second["parent_policy_kind"] = "learned"
    second["parent_policy_ref"] = f"learned:{first['policy_snapshot_id']}"
    fingerprint, snapshot_id = build_policy_snapshot_identity(second)
    second["payload_fingerprint"] = fingerprint
    second["policy_snapshot_id"] = snapshot_id
    sqlite_store.insert_ranking_policy_candidate(second)
    sqlite_store.activate_ranking_policy_candidate(
        str(second["policy_snapshot_id"]),
        expected_parent_ref=str(second["parent_policy_ref"]),
        acted_by="operator",
        **_activation_provenance(),
    )

    sqlite_store.rollback_ranking_policy(
        "ranking_v1",
        expected_active=str(second["policy_snapshot_id"]),
        target=str(first["policy_snapshot_id"]),
        acted_by="operator",
    )
    restored = sqlite_store.resolve_active_ranking_policy("ranking_v1", "runtime")

    assert restored is not None
    assert restored["payload_fingerprint"] == first["payload_fingerprint"]
    assert restored["preference_vector_json"] == first["preference_vector_json"]

    sqlite_store.rollback_ranking_policy(
        "ranking_v1",
        expected_active=str(first["policy_snapshot_id"]),
        target="zero_residual",
        acted_by="operator",
    )
    assert sqlite_store.resolve_active_ranking_policy("ranking_v1", "runtime") is None

def test_training_and_candidate_insert_is_atomic_and_idempotent() -> None:
    training = _training_row()
    snapshot = _snapshot_row(str(training["training_run_id"]), vector=[0.1, -0.1])

    first = sqlite_store.persist_candidate_attempt(training, snapshot)
    second = sqlite_store.persist_candidate_attempt(training, snapshot)

    assert first == second
    lifecycle = sqlite_store.inspect_ranking_policy_lifecycle("ranking_v1")
    assert len(lifecycle["training_runs"]) == 1
    assert len(lifecycle["snapshots"]) == 1


def test_reject_exact_retry_does_not_append_second_event_and_reason_conflicts() -> None:
    training = _training_row()
    snapshot = _snapshot_row(str(training["training_run_id"]), vector=[0.1, -0.1])
    sqlite_store.persist_candidate_attempt(training, snapshot)

    sqlite_store.reject_ranking_policy_candidate(
        str(snapshot["policy_snapshot_id"]), acted_by="operator", reason="bad_metrics"
    )
    sqlite_store.reject_ranking_policy_candidate(
        str(snapshot["policy_snapshot_id"]), acted_by="operator", reason="bad_metrics"
    )
    with pytest.raises(ValueError, match="conflicting rejection reason"):
        sqlite_store.reject_ranking_policy_candidate(
            str(snapshot["policy_snapshot_id"]), acted_by="operator", reason="other"
        )

    lifecycle = sqlite_store.inspect_ranking_policy_lifecycle("ranking_v1")
    assert [event["action"] for event in lifecycle["events"]] == ["reject"]


def test_cv_version_lookup_and_markdown_round_trip() -> None:
    row = {
        "version_id": "ver-1",
        "run_id": "run-cv",
        "job_url": "https://example.com/job-1",
        "fit_classification": "strong",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cv_generation_model": "gpt-test",
        "cv_prompt_version": "v1",
        "cv_schema_version": "cv_doc_v1",
        "cv_structured_json": json.dumps({"schema_version": "cv_doc_v1"}),
        "cv_markdown": "# CV",
        "cv_generation_input_fingerprint": "fp-1",
        "cv_generation_reuse_status": "new",
    }

    sqlite_store.insert_cv_version_row(row)

    rows = sqlite_store.list_cvs_for_run("run-cv")
    indexed = sqlite_store.lookup_reusable_cv_versions(["fp-1"], limit=10)
    markdown = sqlite_store.get_cv_markdown("ver-1")

    assert len(rows) == 1
    assert rows[0]["version_id"] == "ver-1"
    assert indexed["fp-1"]["version_id"] == "ver-1"
    assert markdown == "# CV"


def test_delete_archived_runs_prunes_old_rows_only() -> None:
    old_run = _make_run("run-old")
    recent_run = _make_run("run-recent")
    active_run = _make_run("run-active")
    now = datetime.datetime.now(datetime.timezone.utc)
    old_run.archived_at = now - datetime.timedelta(days=10)
    old_run.archived_by = "admin"
    recent_run.archived_at = now - datetime.timedelta(days=1)
    recent_run.archived_by = "admin"

    for run in (old_run, recent_run, active_run):
        sqlite_store.insert_run(run)

    summary = sqlite_store.delete_archived_runs(older_than_days=5)

    assert summary["deleted_count"] == 1
    assert sqlite_store.get_run("run-old") is None
    assert sqlite_store.get_run("run-recent") is not None
    assert sqlite_store.get_run("run-active") is not None






def test_rule_filter_schema_upgrade_adds_eligibility_columns() -> None:
    db_path = Path(sqlite_store._local_sqlite_path())
    with sqlite_store._sqlite_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE rule_filter_results (
                run_id TEXT NOT NULL,
                job_url TEXT NOT NULL,
                passed INTEGER NOT NULL,
                reasons TEXT NOT NULL,
                marks_json TEXT,
                filtered_at TEXT NOT NULL
            )
            """
        )
        sqlite_store._ensure_local_rule_filter_results_table(conn)
        columns = {
            str(row[1])
            for row in conn.execute("PRAGMA table_info(rule_filter_results)").fetchall()
        }

    assert {
        "raw_job_fingerprint",
        "source_job_url",
        "fit_factor_results_json",
        "eligibility_policy_fingerprint",
        "eligibility_decision",
        "eligibility_reason_codes_json",
    }.issubset(columns)


def test_replace_filter_results_round_trips_explicit_eligibility_columns() -> None:
    factor_results = {
        "language_fit": {
            "factor_id": "language_fit",
            "policy_version": "eligibility-v1",
            "mode": "gate_required",
            "eligibility_decision": "reject",
            "ranking_enabled": False,
            "ranking_value": None,
            "diagnostic_code": "language_required_unmet",
            "evaluation": {
                "factor_id": "language_fit",
                "status": "fail",
                "score": 0.0,
                "confidence": 1.0,
                "reason_code": "language_required_unmet",
                "evidence": {},
                "evaluator_version": "language-fit-evaluator-v1",
                "normalizer_version": "language-fit-normalizer-v1",
            },
        }
    }
    sqlite_store.replace_filter_results(
        "run-eligibility",
        [
            {
                "job_url": "https://example.com/job-1",
                "source_job_url": "https://example.com/job-1",
                "raw_job_fingerprint": "raw-1",
                "passed": False,
                "reasons": ["eligibility_language_fit_failed"],
                "marks": [{"code": "legacy_mark"}],
                "filtered_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "fit_factor_results": factor_results,
                "eligibility_policy_fingerprint": "policy-fingerprint",
                "eligibility_decision": "reject",
                "eligibility_reason_codes": ["language_required_unmet"],
            }
        ],
    )

    rows = sqlite_store.list_filter_results_for_run("run-eligibility")

    assert rows[0]["fit_factor_results"] == factor_results
    assert rows[0]["eligibility_policy_fingerprint"] == "policy-fingerprint"
    assert rows[0]["eligibility_decision"] == "reject"
    assert rows[0]["eligibility_reason_codes"] == ["language_required_unmet"]
    assert rows[0]["marks"] == [{"code": "legacy_mark"}]
    assert "fit_factor_results" not in rows[0]["marks"][0]


def test_list_filter_results_for_run_defaults_legacy_eligibility_columns() -> None:
    db_path = Path(sqlite_store._local_sqlite_path())
    with sqlite_store._sqlite_connection(db_path) as conn:
        sqlite_store._ensure_local_rule_filter_results_table(conn)
        conn.execute(
            """
            INSERT INTO rule_filter_results (
                run_id, job_url, passed, reasons, filtered_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                "run-legacy-filter",
                "https://example.com/legacy",
                1,
                "[]",
                datetime.datetime.now(datetime.timezone.utc).isoformat(),
            ),
        )
        conn.commit()

    rows = sqlite_store.list_filter_results_for_run("run-legacy-filter")

    assert rows[0]["fit_factor_results"] == {}
    assert rows[0]["eligibility_reason_codes"] == []
    assert rows[0]["eligibility_policy_fingerprint"] is None
    assert rows[0]["eligibility_decision"] is None

def _decision_records(*, target_alternative: str = "job-1"):
    from fitcv.decision_feedback import (
        DecisionAlternative,
        DecisionEpisode,
        DecisionRatingEvent,
        RatingEventType,
        RatingValue,
    )

    now = datetime.datetime(2026, 7, 16, tzinfo=datetime.timezone.utc)
    episode = DecisionEpisode(
        episode_id="episode-1",
        domain_id="ranking_v1",
        run_id="run-feedback",
        preference_context_fingerprint="preference",
        qualification_context_fingerprint="qualification",
        ranking_contract_fingerprint="ranking",
        embedding_contract_fingerprint="embedding",
        baseline_policy_fingerprint="baseline",
        embedding_model="model",
        embedding_dimension=2,
        rating_scale_version="application-interest-v1",
        candidate_set_fingerprint="candidates",
        source_stage_artifact_fingerprint="source",
        created_at=now,
    )
    alternatives = (
        DecisionAlternative(
            episode_id=episode.episode_id,
            alternative_id="job-1",
            displayed_rank=1,
            baseline_fit=0.9,
            baseline_fit_label="strong",
            normalized_embedding_json="[1.0,0.0]",
            embedding_vector_fingerprint="vector",
            source_job_url="https://example.test/1",
            shortlist_origin="vector_search",
            created_at=now,
        ),
    )
    event = DecisionRatingEvent(
        event_sequence=None,
        event_id=str(uuid.uuid4()),
        episode_id=episode.episode_id,
        alternative_id=target_alternative,
        event_type=RatingEventType.SET_RATING,
        rating=RatingValue.FOUR,
        rating_scale_version=episode.rating_scale_version,
        acted_by="local_operator",
        created_at=now,
    )
    return episode, alternatives, event


def test_decision_feedback_ledger_is_atomic_ordered_and_append_only() -> None:
    from dataclasses import replace
    from fitcv.decision_feedback import RatingValue

    episode, alternatives, event = _decision_records()
    sqlite_store.materialize_episode_and_append_rating(episode, alternatives, event)
    _, _, second = _decision_records()
    later = episode.created_at + datetime.timedelta(minutes=1)
    repeated_episode = replace(episode, created_at=later)
    repeated_alternatives = tuple(replace(item, created_at=later) for item in alternatives)
    second = replace(second, event_id=str(uuid.uuid4()), rating=RatingValue.FIVE, created_at=later)
    sqlite_store.materialize_episode_and_append_rating(repeated_episode, repeated_alternatives, second)

    events = sqlite_store.list_decision_rating_events_for_run("run-feedback")
    assert [item.event_sequence for item in events] == [1, 2]
    assert [int(item.rating) for item in events if item.rating is not None] == [4, 5]

    db_path = Path(sqlite_store._local_sqlite_path())
    with sqlite_store._sqlite_connection(db_path) as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("UPDATE decision_rating_events SET acted_by = 'other'")


def test_decision_feedback_first_write_rolls_back_on_unknown_alternative() -> None:
    episode, alternatives, event = _decision_records(target_alternative="missing")
    with pytest.raises(ValueError, match="unknown decision alternative"):
        sqlite_store.materialize_episode_and_append_rating(episode, alternatives, event)

    db_path = Path(sqlite_store._local_sqlite_path())
    with sqlite_store._sqlite_connection(db_path) as conn:
        sqlite_store._ensure_local_decision_feedback_tables(conn)
        assert conn.execute("SELECT COUNT(*) FROM decision_episodes").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM decision_episode_alternatives").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM decision_rating_events").fetchone()[0] == 0

def test_decision_evidence_head_characterization_and_request_loading() -> None:
    from dataclasses import replace

    from fitcv.shortlist_runtime import build_contract_fingerprint

    episode, alternatives, event = _decision_records()
    event = replace(event, event_id="event-fixed")
    sqlite_store.materialize_episode_and_append_rating(episode, alternatives, event)

    expected_payload = {
        "schema_version": "decision_evidence_head_v1",
        "domain_id": "ranking_v1",
        "event_watermark": 1,
        "episodes": [
            {
                "episode_id": "episode-1",
                "domain_id": "ranking_v1",
                "preference_context_fingerprint": "preference",
                "qualification_context_fingerprint": "qualification",
                "ranking_contract_fingerprint": "ranking",
                "embedding_contract_fingerprint": "embedding",
                "baseline_policy_fingerprint": "baseline",
                "embedding_model": "model",
                "embedding_dimension": 2,
                "rating_scale_version": "application-interest-v1",
                "candidate_set_fingerprint": "candidates",
                "source_stage_artifact_fingerprint": "source",
                "alternatives": [
                    {
                        "alternative_id": "job-1",
                        "displayed_rank": 1,
                        "baseline_fit": 0.9,
                        "baseline_fit_label": "strong",
                        "normalized_embedding": [1.0, 0.0],
                        "embedding_vector_fingerprint": "vector",
                        "shortlist_origin": "vector_search",
                    }
                ],
                "events": [
                    {
                        "event_sequence": 1,
                        "event_id": "event-fixed",
                        "episode_id": "episode-1",
                        "alternative_id": "job-1",
                        "event_type": "set_rating",
                        "rating": 4,
                        "rating_scale_version": "application-interest-v1",
                    }
                ],
            }
        ],
    }
    head = sqlite_store.get_decision_evidence_head("ranking_v1")
    assert head == {
        **expected_payload,
        "evidence_head_fingerprint": build_contract_fingerprint(expected_payload),
    }

    request = sqlite_store.load_inverse_optimization_request("ranking_v1")
    assert request.schema_version == "inverse_optimization_request_v1"
    assert request.event_watermark == 1
    assert len(request.episodes) == 1
    training_episode = request.episodes[0]
    assert training_episode.episode.run_id == "run-feedback"
    assert training_episode.alternatives[0].source_job_url == "https://example.test/1"
    assert training_episode.events[0].acted_by == "local_operator"
    assert training_episode.events_loaded_through_sequence == 1
    assert training_episode.evaluation_context is None


def test_policy_lifecycle_inspection_limits_in_sql_and_marks_rollback_eligibility() -> None:
    first_training = _training_row()
    first_snapshot = _snapshot_row(str(first_training["training_run_id"]), vector=[0.1, -0.1])
    first = sqlite_store.persist_candidate_attempt(first_training, first_snapshot)["snapshot"]
    sqlite_store.activate_ranking_policy_candidate(
        str(first["policy_snapshot_id"]),
        expected_parent_ref=str(first["parent_policy_ref"]),
        acted_by="operator",
        **_activation_provenance(),
    )

    second_training = _training_row()
    second_training["problem_fingerprint"] = "problem-2"
    second_training["training_run_id"] = build_training_run_identity(second_training)
    second_snapshot = _snapshot_row(
        str(second_training["training_run_id"]), vector=[0.2, -0.2], suffix="-2"
    )
    second_snapshot["parent_policy_kind"] = "learned"
    second_snapshot["parent_policy_ref"] = f"learned:{first['policy_snapshot_id']}"
    second_snapshot["payload_fingerprint"], second_snapshot["policy_snapshot_id"] = (
        build_policy_snapshot_identity(second_snapshot)
    )
    second = sqlite_store.persist_candidate_attempt(second_training, second_snapshot)["snapshot"]
    sqlite_store.activate_ranking_policy_candidate(
        str(second["policy_snapshot_id"]),
        expected_parent_ref=str(second["parent_policy_ref"]),
        acted_by="operator",
        **_activation_provenance(),
    )

    inspected = sqlite_store.inspect_ranking_policy_lifecycle("ranking_v1", limit=1)
    assert len(inspected["training_runs"]) == 1
    assert len(inspected["snapshots"]) == 1
    assert len(inspected["events"]) == 1
    assert inspected["snapshots"][0]["policy_snapshot_id"] == second["policy_snapshot_id"]
    assert inspected["active_snapshot"]["policy_snapshot_id"] == second["policy_snapshot_id"]

    unbounded = sqlite_store.inspect_ranking_policy_lifecycle("ranking_v1")
    first_row = next(
        row for row in unbounded["snapshots"]
        if row["policy_snapshot_id"] == first["policy_snapshot_id"]
    )
    assert first_row["rollback_eligible"] is True


def test_process_event_ledger_merges_sqlite_and_atomic_journal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from fitcv_cp.models import build_process_event

    monkeypatch.setenv("FITCV_CP_LOCAL_EVENT_HISTORY_DIR", str(tmp_path / "events"))
    first = build_process_event(
        process_type="pipeline",
        process_id="a/b",
        operation="start",
        state="started",
        level="info",
        message="started",
        payload={"attempt": 1},
        event_id="event-1",
    )
    second = build_process_event(
        process_type="pipeline",
        process_id="a:b",
        operation="finish",
        state="succeeded",
        level="info",
        message="finished",
        payload={"attempt": 1},
        event_id="event-2",
    )

    sqlite_store.append_process_event(first)
    monkeypatch.setattr(
        sqlite_store,
        "_insert_process_event",
        lambda *args, **kwargs: (_ for _ in ()).throw(sqlite3.OperationalError("disk I/O error")),
    )
    result = sqlite_store.append_process_event(second)

    page = sqlite_store.get_process_events("pipeline", "a/b")
    other_page = sqlite_store.get_process_events("pipeline", "a:b")

    assert result["persistence_backend"] == "journal"
    assert [event.event_id for event in page["events"]] == ["event-1"]
    assert [event.event_id for event in other_page["events"]] == ["event-2"]
    assert sqlite_store._process_event_journal_dir("pipeline", "a/b") != sqlite_store._process_event_journal_dir("pipeline", "a:b")


def test_process_event_contract_freezes_sanitizer_and_fingerprint() -> None:
    from fitcv_cp.models import build_process_event

    left = build_process_event(
        process_type="pipeline",
        process_id="run-1",
        operation="enrich",
        state="started",
        level="info",
        message="x" * 600,
        payload={"z": 1, "password_value": "secret", "a": [1] * 25},
        event_id="event-stable",
    )
    right = build_process_event(
        process_type="pipeline",
        process_id="run-1",
        operation="enrich",
        state="started",
        level="info",
        message="x" * 600,
        payload={"a": [1] * 25, "password_value": "different", "z": 1},
        event_id="event-stable",
        recorded_at=left.recorded_at,
    )

    assert left.payload_json == right.payload_json
    assert left.event_fingerprint == right.event_fingerprint
    assert len(left.message) == 514
    assert json.loads(left.payload_json or "{}") ["password_value"] == "[REDACTED]"


def test_candidate_attempt_process_event_is_atomic(monkeypatch: pytest.MonkeyPatch) -> None:
    training = _training_row()
    snapshot = _snapshot_row(str(training["training_run_id"]), vector=[0.1, -0.1])

    persisted = sqlite_store.persist_candidate_attempt(training, snapshot)
    page = sqlite_store.get_process_events("optimization", "ranking_v1")

    assert persisted["snapshot"] is not None
    assert [(event.operation, event.state) for event in page["events"]] == [("candidate_create", "succeeded")]

    failing_training = _training_row()
    failing_training["event_watermark"] = 3
    failing_training.pop("training_run_id")
    failing_training["training_run_id"] = build_training_run_identity(failing_training)
    failing_snapshot = _snapshot_row(str(failing_training["training_run_id"]), vector=[0.2, -0.2], suffix="-atomic")
    original_insert = sqlite_store._insert_process_event
    monkeypatch.setattr(
        sqlite_store,
        "_insert_process_event",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("event failed")),
    )
    with pytest.raises(RuntimeError, match="event failed"):
        sqlite_store.persist_candidate_attempt(failing_training, failing_snapshot)
    monkeypatch.setattr(sqlite_store, "_insert_process_event", original_insert)

    lifecycle = sqlite_store.inspect_ranking_policy_lifecycle("ranking_v1")
    assert len(lifecycle["training_runs"]) == 1
    assert len(lifecycle["snapshots"]) == 1
