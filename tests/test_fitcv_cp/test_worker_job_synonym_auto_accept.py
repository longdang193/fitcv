from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch


def _auto_accept_run(checkpoint_payload_json: str | None = None) -> MagicMock:
    run = MagicMock(
        effective_settings_json=json.dumps(
            {"synonym_management": {"auto_accept_suggestions_enabled": True}}
        )
    )
    run.checkpoint_payload_json = checkpoint_payload_json
    return run


def test_worker_auto_accept_routes_domain_proposals_through_central_queue() -> None:
    from fitcv_cp.worker_job import _sync_central_synonym_suggestions

    payload = {
        "proposals": [
            {
                "field": "domain",
                "alias": "fintech",
                "canonical": "financial technology",
                "evidence_summary": {"occurrence_count": 3},
                "conflict_summary": {"has_conflict": False},
            }
        ]
    }
    run = MagicMock(
        effective_settings_json=json.dumps(
            {"synonym_management": {"auto_accept_suggestions_enabled": True}}
        )
    )

    with (
        patch(
            "fitcv_cp.worker_job.ingest_synonym_suggestions",
            return_value={"actionable_suggestion_ids": ["suggestion-domain"]},
        ) as ingest_mock,
        patch(
            "fitcv_cp.worker_job.preflight_synonym_suggestion_automation",
            return_value={"safe_ids": ["suggestion-domain"], "skipped": []},
        ),
        patch("fitcv_cp.worker_job.record_synonym_automation_checkpoint"),
        patch("fitcv_cp.worker_job.update_run_checkpoint"),
        patch("fitcv_cp.worker_job.apply_synonym_suggestion_action") as approve_mock,
    ):
        _sync_central_synonym_suggestions(
            run_id="run-domain",
            run_record=run,
            payload=payload,
        )

    ingest_mock.assert_called_once_with(
        [
            {
                "synonym_type": "domain",
                "alias": "fintech",
                "canonical": "financial technology",
                "run_id": "run-domain",
                "confidence": None,
                "candidate_canonicals": [],
                "evidence_note": None,
                "evidence": {
                    "evidence_summary": {"occurrence_count": 3},
                    "conflict_summary": {"has_conflict": False},
                },
            }
        ]
    )
    approve_mock.assert_called_once()
    assert approve_mock.call_args.args[0] == ["suggestion-domain"]
    assert approve_mock.call_args.kwargs["action"] == "approve"
    assert approve_mock.call_args.kwargs["acted_by"] == "automation"
    assert approve_mock.call_args.kwargs["automation"] is True


def test_worker_auto_accept_chunks_each_synonym_type_at_store_limit() -> None:
    from fitcv_cp.worker_job import _sync_central_synonym_suggestions

    suggestion_ids = [f"suggestion-{index}" for index in range(1001)]
    payload = {
        "proposals": [
            {
                "field": "skill",
                "alias": f"alias-{index}",
                "canonical": f"canonical-{index}",
            }
            for index in range(1001)
        ]
    }

    with (
        patch(
            "fitcv_cp.worker_job.ingest_synonym_suggestions",
            return_value={"actionable_suggestion_ids": suggestion_ids},
        ),
        patch(
            "fitcv_cp.worker_job.preflight_synonym_suggestion_automation",
            return_value={"safe_ids": suggestion_ids, "skipped": []},
        ),
        patch("fitcv_cp.worker_job.record_synonym_automation_checkpoint"),
        patch("fitcv_cp.worker_job.update_run_checkpoint"),
        patch("fitcv_cp.worker_job.apply_synonym_suggestion_action") as approve_mock,
    ):
        _sync_central_synonym_suggestions(
            run_id="run-large", run_record=_auto_accept_run(), payload=payload
        )

    assert [call.args[0] for call in approve_mock.call_args_list] == [
        suggestion_ids[:1000],
        suggestion_ids[1000:],
    ]
    assert all(call.kwargs["automation"] is True for call in approve_mock.call_args_list)


def test_worker_auto_accept_skips_full_set_conflicts_before_chunk_activation() -> None:
    from fitcv_cp.worker_job import _sync_central_synonym_suggestions

    payload = {
        "proposals": [
            {"field": "skill", "alias": "one", "canonical": "first"},
            {"field": "skill", "alias": "one", "canonical": "second"},
        ]
    }
    skipped = [
        {"suggestion_id": "conflict-a", "reason": "alias_conflict"},
        {"suggestion_id": "conflict-b", "reason": "alias_conflict"},
    ]

    with (
        patch(
            "fitcv_cp.worker_job.ingest_synonym_suggestions",
            return_value={"actionable_suggestion_ids": ["conflict-a", "conflict-b"]},
        ),
        patch(
            "fitcv_cp.worker_job.preflight_synonym_suggestion_automation",
            return_value={"safe_ids": [], "skipped": skipped},
        ),
        patch("fitcv_cp.worker_job.record_synonym_automation_checkpoint") as checkpoint_mock,
        patch("fitcv_cp.worker_job.update_run_checkpoint"),
        patch("fitcv_cp.worker_job.apply_synonym_suggestion_action") as approve_mock,
    ):
        _sync_central_synonym_suggestions(
            run_id="run-conflict", run_record=_auto_accept_run(), payload=payload
        )

    approve_mock.assert_not_called()
    assert any(
        "conflict-a" in call.args[1]["skipped_ids"]
        and "conflict-b" in call.args[1]["skipped_ids"]
        for call in checkpoint_mock.call_args_list
    )


def test_worker_auto_accept_resumes_checkpoint_without_reingesting() -> None:
    from fitcv_cp.worker_job import _sync_central_synonym_suggestions

    checkpoint = {
        "operation_id": "synonym-auto:run-resume:fingerprint",
        "run_id": "run-resume",
        "candidate_fingerprint": "fingerprint",
        "candidate_ids": ["done", "remaining"],
        "safe_ids": ["done", "remaining"],
        "completed_ids": ["done"],
        "skipped_ids": [],
        "failed_ids": [],
        "remaining_ids": ["remaining"],
        "outcomes": {},
    }
    payload = {
        "proposals": [
            {"field": "skill", "alias": "resume", "canonical": "resume"},
        ]
    }

    with (
        patch(
            "fitcv_cp.worker_job.get_synonym_automation_checkpoint",
            return_value=checkpoint,
        ),
        patch("fitcv_cp.worker_job.ingest_synonym_suggestions") as ingest_mock,
        patch("fitcv_cp.worker_job.record_synonym_automation_checkpoint"),
        patch("fitcv_cp.worker_job.update_run_checkpoint"),
        patch("fitcv_cp.worker_job.apply_synonym_suggestion_action") as approve_mock,
    ):
        _sync_central_synonym_suggestions(
            run_id="run-resume", run_record=_auto_accept_run(), payload=payload
        )

    ingest_mock.assert_not_called()
    assert approve_mock.call_args.args[0] == ["remaining"]


def test_worker_auto_accept_persists_middle_chunk_failure_and_resumes_after_restart() -> None:
    from fitcv_cp.worker_job import _sync_central_synonym_suggestions

    suggestion_ids = [f"suggestion-{index}" for index in range(2001)]
    payload = {
        "proposals": [
            {
                "field": "skill",
                "alias": f"alias-{index}",
                "canonical": f"canonical-{index}",
            }
            for index in range(2001)
        ]
    }
    persisted: list[dict[str, object]] = []
    apply_calls = 0
    fail_middle_chunk = True

    def save_checkpoint(_operation_id: str, checkpoint: dict[str, object]) -> None:
        persisted.append(checkpoint)

    def load_checkpoint(_operation_id: str) -> dict[str, object] | None:
        return persisted[-1] if persisted else None

    def apply_chunk(*args: object, **kwargs: object) -> dict[str, object]:
        nonlocal apply_calls
        apply_calls += 1
        if fail_middle_chunk and apply_calls == 2:
            raise RuntimeError("middle chunk failed")
        return {}

    with (
        patch(
            "fitcv_cp.worker_job.ingest_synonym_suggestions",
            return_value={"actionable_suggestion_ids": suggestion_ids},
        ) as ingest_mock,
        patch(
            "fitcv_cp.worker_job.preflight_synonym_suggestion_automation",
            return_value={"safe_ids": suggestion_ids, "skipped": [], "mapping_set": []},
        ),
        patch(
            "fitcv_cp.worker_job.get_synonym_automation_checkpoint",
            side_effect=load_checkpoint,
        ),
        patch(
            "fitcv_cp.worker_job.record_synonym_automation_checkpoint",
            side_effect=save_checkpoint,
        ),
        patch("fitcv_cp.worker_job.update_run_checkpoint"),
        patch(
            "fitcv_cp.worker_job.apply_synonym_suggestion_action",
            side_effect=apply_chunk,
        ) as apply_mock,
    ):
        try:
            _sync_central_synonym_suggestions(
                run_id="run-restart",
                run_record=_auto_accept_run(),
                payload=payload,
            )
        except RuntimeError as exc:
            assert str(exc) == "middle chunk failed"
        else:
            raise AssertionError("middle chunk failure was not surfaced")

        failed_checkpoint = persisted[-1]
        assert failed_checkpoint["completed_ids"] == suggestion_ids[:1000]
        assert failed_checkpoint["failed_ids"] == suggestion_ids[1000:2000]
        assert failed_checkpoint["remaining_ids"] == suggestion_ids[1000:]

        fail_middle_chunk = False
        _sync_central_synonym_suggestions(
            run_id="run-restart",
            run_record=_auto_accept_run(),
            payload=payload,
        )

    assert ingest_mock.call_count == 1
    assert [len(call.args[0]) for call in apply_mock.call_args_list] == [1000, 1000, 1000, 1]


def test_worker_auto_accept_applies_1001_valid_suggestions_with_real_sqlite(
    monkeypatch, tmp_path: Path
) -> None:
    from fitcv_cp import sqlite_store
    from fitcv_cp.models import PipelineRun, RunStatus
    from fitcv_cp.worker_job import _sync_central_synonym_suggestions
    import datetime

    database_path = tmp_path / "fitcv.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(database_path))
    sqlite_store.initialize_control_plane_database(
        database_path, tmp_path / "missing-profile.yaml"
    )
    sqlite_store.insert_run(
        PipelineRun(
            run_id="run-real-large",
            status=RunStatus.RUNNING,
            triggered_by="tester",
            trigger_source="test",
            jobs_path="jobs.json",
            config_path="config.yaml",
            created_at=datetime.datetime.now(datetime.timezone.utc),
        )
    )
    payload = {
        "proposals": [
            {
                "field": "skill",
                "alias": f"alias-{index}",
                "canonical": f"canonical-{index}",
            }
            for index in range(1001)
        ]
    }

    _sync_central_synonym_suggestions(
        run_id="run-real-large",
        run_record=_auto_accept_run(),
        payload=payload,
    )

    suggestions = sqlite_store.query_synonym_suggestions(
        synonym_type="skills", review_status="approved"
    )
    assert suggestions["total"] == 1001
    assert all(item["policy_effect"] == "active" for item in suggestions["items"])
