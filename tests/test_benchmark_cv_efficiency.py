import json

from scripts.benchmark_cv_efficiency import _markdown, build_baseline
from fitcv_cp.run_artifact_contracts import accepted_cv_artifact_event_v1


def _run(run_id: str, payload: dict, status: str = "succeeded") -> dict:
    return {
        "run_id": run_id,
        "status": status,
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
            "elapsed_ms": 100,
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


def test_baseline_separates_accepted_artifact_and_total_workload_cost() -> None:
    accepted_trace = {
        "trace_id": "trace-accepted",
        "run_id": "run-1",
        "job_url": "job-accepted",
        "attempts": [{"attempt_index": 1, "provider_status": "accepted"}],
        "efficiency_summary": {
            "provider_call_count": 2,
            "elapsed_ms": 100,
            "token_usage": [{"total_tokens": 20}],
        },
    }
    failed_trace = {
        "trace_id": "trace-failed",
        "run_id": "run-1",
        "job_url": "job-failed",
        "attempts": [{"attempt_index": 1, "provider_status": "failed"}],
        "efficiency_summary": {
            "provider_call_count": 3,
            "elapsed_ms": 50,
            "token_usage": [{"total_tokens": 30}],
        },
    }
    artifact = accepted_cv_artifact_event_v1(
        artifact_id="cv-1",
        job_url="job-accepted",
        run_id="run-1",
        trace_id="trace-accepted",
        acceptance_mode="automatic",
        accepted_at="2026-10-02T00:01:00Z",
        finalized_at="2026-10-02T00:01:00Z",
    )

    run = _run(
        "run-1",
        {
            "debug_records": [{"status": "accepted", "job_url": "job-accepted"}],
            "cv_generation_trace": {"records": [accepted_trace, failed_trace]},
            "accepted_artifact_events": [artifact],
        },
    )
    run.update({"started_at": "2026-10-02T00:00:00Z", "finished_at": "2026-10-02T00:00:05Z"})
    report = build_baseline([run])

    assert report["accepted_cv"]["accepted_artifact_cost_per_accepted_cv"]["provider_call_count"] == 2.0
    assert report["accepted_cv"]["accepted_artifact_cost_per_accepted_cv"]["token_total"] == 20.0
    assert report["accepted_cv"]["total_workload_cost_per_accepted_cv"]["provider_call_count"] == 5.0
    assert report["accepted_cv"]["total_workload_cost_per_accepted_cv"]["token_total"] == 50.0
    assert report["accepted_cv"]["accepted_artifact_cost_per_accepted_cv"]["generation_elapsed_ms"] == 100.0
    assert report["accepted_cv"]["total_workload_cost_per_accepted_cv"]["generation_elapsed_ms"] == 150.0
    assert report["accepted_cv"]["total_workload_cost_per_accepted_cv"]["end_to_end_wall_ms"] == 5000.0
    assert report["accepted_cv"]["cost_per_accepted_cv"] == report["accepted_cv"]["accepted_artifact_cost_per_accepted_cv"]
    markdown = _markdown(report)
    assert "Accepted-artifact cost per accepted CV" in markdown
    assert "Total-workload cost per accepted CV" in markdown


def test_baseline_reports_first_pass_and_retry_yield() -> None:
    traces = [
        {
            "trace_id": "trace-first-pass",
            "run_id": "run-yield",
            "job_url": "job-first-pass",
            "attempts": [{"attempt_index": 1, "provider_status": "accepted"}],
            "output_summary": {"final_status": "accepted"},
            "efficiency_summary": {"provider_call_count": 1},
        },
        {
            "trace_id": "trace-retry-success",
            "run_id": "run-yield",
            "job_url": "job-retry-success",
            "attempts": [
                {"attempt_index": 1, "provider_status": "validation_failed"},
                {"attempt_index": 2, "provider_status": "accepted"},
            ],
            "output_summary": {"final_status": "accepted"},
            "efficiency_summary": {"provider_call_count": 2},
        },
        {
            "trace_id": "trace-retry-failure",
            "run_id": "run-yield",
            "job_url": "job-retry-failure",
            "attempts": [
                {"attempt_index": 1, "provider_status": "validation_failed"},
                {"attempt_index": 2, "provider_status": "failed"},
            ],
            "output_summary": {"final_status": "failed"},
            "efficiency_summary": {"provider_call_count": 2},
        },
    ]
    artifacts = [
        accepted_cv_artifact_event_v1(
            artifact_id="cv-first-pass",
            job_url="job-first-pass",
            run_id="run-yield",
            trace_id="trace-first-pass",
            acceptance_mode="automatic",
            accepted_at="2026-10-02T00:01:00Z",
            finalized_at="2026-10-02T00:01:00Z",
        ),
        accepted_cv_artifact_event_v1(
            artifact_id="cv-retry-success",
            job_url="job-retry-success",
            run_id="run-yield",
            trace_id="trace-retry-success",
            acceptance_mode="automatic",
            accepted_at="2026-10-02T00:01:00Z",
            finalized_at="2026-10-02T00:01:00Z",
        ),
    ]
    report = build_baseline(
        [
            _run(
                "run-yield",
                {
                    "debug_records": [
                        {"status": "accepted", "job_url": "job-first-pass"},
                        {"status": "accepted", "job_url": "job-retry-success"},
                    ],
                    "cv_generation_trace": {"records": traces},
                    "accepted_artifact_events": artifacts,
                },
            )
        ]
    )

    assert report["yield"]["attempted_generation_job_count"] == 3
    assert report["yield"]["first_pass_acceptance_count"] == 1
    assert report["yield"]["first_pass_acceptance_rate"] == 1 / 3
    assert report["yield"]["retry_success_count"] == 1
    assert report["yield"]["retry_failure_count"] == 1


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


def test_baseline_includes_failed_and_cancelled_runs_with_measurable_generation_work() -> None:
    def payload(run_id: str, calls: int, tokens: int) -> dict:
        return {
            "cv_generation_trace": {
                "records": [
                    {
                        "run_id": run_id,
                        "job_url": f"job-{run_id}",
                        "attempts": [{"attempt_index": 1, "provider_status": "failed"}],
                        "efficiency_summary": {
                            "provider_call_count": calls,
                            "token_usage": [{"total_tokens": tokens}],
                        },
                    }
                ]
            }
        }

    report = build_baseline(
        [
            _run("run-failed", payload("run-failed", 2, 20), status="failed"),
            _run("run-cancelled", payload("run-cancelled", 3, 30), status="cancelled"),
        ]
    )

    assert report["selection"]["run_count"] == 2
    assert report["workload"]["provider_call_count"] == 5
    assert report["workload"]["token_total"] == 50
    assert report["accepted_cv"]["count"] == 0
    assert report["accepted_cv"]["cost_per_accepted_cv"] is None


def test_baseline_counts_validation_failed_retry_as_failure_even_if_provider_accepted() -> None:
    report = build_baseline(
        [
            _run(
                "run-validation-failed",
                {
                    "cv_generation_trace": {
                        "records": [
                            {
                                "run_id": "run-validation-failed",
                                "job_url": "job-validation-failed",
                                "attempts": [
                                    {"attempt_index": 1, "provider_status": "validation_failed"},
                                    {"attempt_index": 2, "provider_status": "accepted"},
                                ],
                                "output_summary": {"final_status": "validation_failed"},
                                "efficiency_summary": {"provider_call_count": 2},
                            }
                        ]
                    }
                },
            )
        ]
    )

    assert report["yield"]["retry_success_count"] == 0
    assert report["yield"]["retry_failure_count"] == 1


def test_baseline_keeps_generation_elapsed_separate_from_artifact_elapsed() -> None:
    trace = {
        "trace_id": "trace-latency",
        "run_id": "run-latency",
        "job_url": "job-latency",
        "run_started_at": "2026-10-02T00:00:00Z",
        "attempts": [{"attempt_index": 1, "provider_status": "accepted"}],
        "efficiency_summary": {
            "provider_call_count": 1,
            "elapsed_ms": 100,
            "token_usage": [{"total_tokens": 10}],
        },
    }
    artifact = accepted_cv_artifact_event_v1(
        artifact_id="cv-latency",
        job_url="job-latency",
        run_id="run-latency",
        trace_id="trace-latency",
        acceptance_mode="automatic",
        accepted_at="2026-10-02T01:00:00Z",
        finalized_at="2026-10-02T01:00:00Z",
    )

    report = build_baseline(
        [
            _run(
                "run-latency",
                {
                    "debug_records": [{"status": "accepted", "job_url": "job-latency"}],
                    "cv_generation_trace": {"records": [trace]},
                    "accepted_artifact_events": [artifact],
                },
            )
        ]
    )

    accepted_cost = report["accepted_cv"]["accepted_artifact_cost_per_accepted_cv"]
    assert accepted_cost["generation_elapsed_ms"] == 100.0
    assert accepted_cost["elapsed_ms"] == 3_600_000.0
    assert report["aggregate"]["generation_elapsed_ms"] == 100.0
