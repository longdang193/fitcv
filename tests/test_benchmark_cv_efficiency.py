import json

from scripts.benchmark_cv_efficiency import build_baseline
from fitcv_cp.run_artifact_contracts import accepted_cv_artifact_event_v1


def _run(run_id: str, payload: dict) -> dict:
    return {
        "run_id": run_id,
        "status": "succeeded",
        "cv_generation_debug_json": json.dumps(payload),
    }


def test_baseline_reads_debug_payload_from_compatibility_snapshot() -> None:
    trace = {
        "trace_id": "trace-compat",
        "run_id": "run-compat",
        "job_url": "job-compat",
        "attempts": [{"attempt_index": 1, "provider_status": "accepted"}],
        "efficiency_summary": {
            "provider_call_count": 1,
            "token_usage": [{"total_tokens": 7}],
        },
    }
    artifact = accepted_cv_artifact_event_v1(
        artifact_id="cv-compat",
        job_url="job-compat",
        run_id="run-compat",
        trace_id="trace-compat",
        acceptance_mode="automatic",
        accepted_at="2026-10-02T00:01:00Z",
        finalized_at="2026-10-02T00:01:00Z",
    )

    report = build_baseline(
        [
            {
                "run_id": "run-compat",
                "status": "succeeded",
                "cv_generation_debug_json": None,
                "compatibility_json": json.dumps(
                    {
                        "cv_generation_debug_json": json.dumps(
                            {
                                "debug_records": [{"status": "accepted", "job_url": "job-compat"}],
                                "cv_generation_trace": {"records": [trace]},
                                "accepted_artifact_events": [artifact],
                            }
                        )
                    }
                ),
            }
        ]
    )

    assert report["status"] == "complete"
    assert report["workload"]["provider_call_count"] == 1
    assert report["accepted_cv"]["count"] == 1


def test_baseline_aggregates_persisted_workload_and_cost_per_accepted_cv() -> None:
    trace = {
        "trace_id": "trace-1",
        "run_id": "run-1",
        "job_url": "job-1",
        "attempts": [{"attempt_index": 1, "provider_status": "accepted"}],
        "efficiency_summary": {
            "provider_call_count": 2,
            "token_usage": [{"total_tokens": 20}],
        },
    }
    artifact = accepted_cv_artifact_event_v1(
        artifact_id="cv-1",
        job_url="job-1",
        run_id="run-1",
        trace_id="trace-1",
        acceptance_mode="automatic",
        accepted_at="2026-10-02T00:01:00Z",
        finalized_at="2026-10-02T00:01:00Z",
    )
    report = build_baseline(
        [
            _run(
                "run-1",
                {
                    "debug_records": [{"status": "accepted", "job_url": "job-1"}],
                    "cv_generation_trace": {"records": [trace]},
                    "accepted_artifact_events": [artifact],
                },
            )
        ]
    )

    assert report["status"] == "complete"
    assert report["workload"]["provider_call_count"] == 2
    assert report["workload"]["token_total"] == 20
    assert report["accepted_cv"]["count"] == 1
    assert report["accepted_cv"]["cost_per_accepted_cv"]["provider_call_count"] == 2.0


def test_baseline_keeps_unattributed_cost_null_and_workload_totals_visible() -> None:
    report = build_baseline(
        [
            _run(
                "run-1",
                {
                    "cv_generation_trace": {
                        "records": [
                            {
                                "run_id": "run-2",
                                "job_url": "other-job",
                                "efficiency_summary": {"provider_call_count": 4, "token_usage": [{"total_tokens": 40}]},
                            }
                        ]
                    },
                    "accepted_artifact_events": [
                        accepted_cv_artifact_event_v1(
                            artifact_id="cv-1",
                            job_url="job-1",
                            run_id="run-1",
                            acceptance_mode="automatic",
                            accepted_at="2026-10-02T00:01:00Z",
                            finalized_at="2026-10-02T00:01:00Z",
                        )
                    ],
                },
            )
        ]
    )

    assert report["status"] == "incomplete"
    assert report["workload"]["provider_call_count"] == 4
    assert report["workload"]["token_total"] == 40
    assert report["accepted_cv"]["cost_per_accepted_cv"] is None
    assert report["attribution"]["unattributed_accepted_artifact_count"] == 1


def test_baseline_marks_missing_persisted_runs_unavailable() -> None:
    report = build_baseline([{"run_id": "failed", "status": "failed"}])

    assert report["status"] == "not_available"
    assert report["selection"]["run_count"] == 0
    assert report["accepted_cv"]["cost_per_accepted_cv"] is None
