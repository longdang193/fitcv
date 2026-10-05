import json
from pathlib import Path

from scripts.benchmark_cv_efficiency import (
    _markdown,
    build_canonical_evidence,
    build_baseline,
    material_report_digest,
    material_report_metrics,
    _load_run_manifest,
    _apply_manifest_measurement_gate,
)
from fitcv_cp.run_artifact_contracts import accepted_cv_artifact_event_v1 as _accepted_cv_artifact_event_v1


def accepted_cv_artifact_event_v1(**kwargs):
    kwargs.setdefault("page_fit_status", "pass")
    kwargs.setdefault(
        "render_acceptance",
        {
            "render_status": "pass",
            "renderer_status": "rendered",
            "page_count": 1,
            "page_fit_status": "pass",
            "artifact_checksum": "a" * 64,
            "content_sha256": "b" * 64,
            "template_sha256": "c" * 64,
            "render_config_fingerprint": "d" * 64,
            "renderer_contract_version": "fitcv_native_render_v1",
        },
    )
    return _accepted_cv_artifact_event_v1(**kwargs)


def test_run_manifest_rejects_duplicate_run_ids(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"run_ids": ["run-1", "run-1"]}), encoding="utf-8")
    try:
        _load_run_manifest(path)
    except ValueError as exc:
        assert str(exc) == "run_manifest_duplicate_run_ids"
    else:
        raise AssertionError("duplicate manifest accepted")


def test_manifest_measurement_gate_rejects_fewer_than_declared_repeats() -> None:
    report = {"status": "complete", "selection": {"run_count": 4, "exclusions": {"succeeded": 6}}}

    gated = _apply_manifest_measurement_gate(report, {"repeat_count": 10, "run_ids": [str(i) for i in range(10)]})

    assert gated["status"] == "incomplete"
    assert gated["selection"]["manifest_expected_run_count"] == 10
    assert gated["selection"]["manifest_run_count_shortfall"] == 6


def _run(run_id: str, payload: dict, status: str = "succeeded") -> dict:
    trace_block = payload.get("cv_generation_trace")
    if isinstance(trace_block, dict):
        for trace in list(trace_block.get("records") or []):
            if isinstance(trace, dict):
                trace.setdefault("trace_contract_version", "fitcv.trace.v1")
        if trace_block.get("attempts"):
            trace_block.setdefault("trace_contract_version", "fitcv.trace.v1")
    return {
        "run_id": run_id,
        "status": status,
        "cv_generation_debug_json": json.dumps(payload),
    }


def test_baseline_reads_debug_payload_from_compatibility_snapshot() -> None:
    trace = {
        "trace_id": "trace-compat",
        "trace_contract_version": "fitcv.trace.v1",
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


def test_baseline_reports_lossless_stage_latency_percentiles() -> None:
    trace = {
        "trace_id": "trace-stage-latency",
        "run_id": "run-stage-latency",
        "job_url": "job-stage-latency",
        "stage_timings_ms": {"analysis": [10, 20], "render": [30]},
        "attempts": [
            {
                "attempt_index": 1,
                "provider_status": "accepted",
                "llm_runtime_evidence": {"provenance": {"latency_ms": 100}},
            },
            {
                "attempt_index": 2,
                "provider_status": "accepted",
                "llm_runtime_evidence": {"provenance": {"latency_ms": 200}},
            },
        ],
        "efficiency_summary": {
            "provider_call_count": 2,
            "elapsed_ms": 300,
            "token_usage": [{"total_tokens": 20}],
        },
    }
    artifact = accepted_cv_artifact_event_v1(
        artifact_id="cv-stage-latency",
        job_url="job-stage-latency",
        run_id="run-stage-latency",
        trace_id="trace-stage-latency",
        acceptance_mode="automatic",
        accepted_at="2026-10-02T00:01:00Z",
        finalized_at="2026-10-02T00:01:00Z",
    )

    report = build_baseline([
        _run(
            "run-stage-latency",
            {
                "debug_records": [{"status": "accepted", "job_url": "job-stage-latency"}],
                "cv_generation_trace": {"records": [trace]},
                "accepted_artifact_events": [artifact],
            },
        )
    ])

    stage_latency = report["timing"]["stage_latency_ms"]
    assert stage_latency["analysis"] == {
        "p50_ms": 15.0,
        "p95_ms": 19.5,
        "measured": 2,
        "coverage": True,
    }
    assert stage_latency["provider_generation"]["p50_ms"] == 150.0
    assert stage_latency["provider_generation"]["p95_ms"] == 195.0
    assert stage_latency["render"]["p50_ms"] == 30.0
    assert stage_latency["validation"]["p50_ms"] is None
    assert stage_latency["validation"]["coverage"] is False


def test_baseline_counts_embedded_only_trace_for_timing_and_yield() -> None:
    trace = {
        "trace_id": "trace-embedded-only",
        "run_id": "run-embedded-only",
        "job_url": "job-embedded-only",
        "attempts": [{"attempt_index": 1, "provider_status": "accepted"}],
        "output_summary": {"final_status": "accepted"},
        "efficiency_summary": {"provider_call_count": 1, "elapsed_ms": 100},
    }
    artifact = accepted_cv_artifact_event_v1(
        artifact_id="cv-embedded-only",
        job_url="job-embedded-only",
        run_id="run-embedded-only",
        trace_id="trace-embedded-only",
        acceptance_mode="automatic",
        accepted_at="2026-10-02T00:01:00Z",
        finalized_at="2026-10-02T00:01:00Z",
    )

    report = build_baseline(
        [
            _run(
                "run-embedded-only",
                {
                    "debug_records": [{"status": "accepted", "job_url": "job-embedded-only", "cv_generation_trace": trace}],
                    "accepted_artifact_events": [artifact],
                },
            )
        ]
    )

    assert report["workload"]["attempted_generation_job_count"] == 1
    assert report["workload"]["generation_elapsed_ms"] == 100.0
    assert report["yield"]["first_pass_acceptance_count"] == 1


def test_baseline_deduplicates_duplicate_top_level_trace_for_timing_and_yield() -> None:
    trace = {
        "trace_id": "trace-duplicate",
        "run_id": "run-duplicate",
        "job_url": "job-duplicate",
        "attempts": [{"attempt_index": 1, "provider_status": "accepted"}],
        "output_summary": {"final_status": "accepted"},
        "efficiency_summary": {"provider_call_count": 1, "elapsed_ms": 100},
    }
    artifact = accepted_cv_artifact_event_v1(
        artifact_id="cv-duplicate",
        job_url="job-duplicate",
        run_id="run-duplicate",
        trace_id="trace-duplicate",
        acceptance_mode="automatic",
        accepted_at="2026-10-02T00:01:00Z",
        finalized_at="2026-10-02T00:01:00Z",
    )

    report = build_baseline(
        [
            _run(
                "run-duplicate",
                {
                    "cv_generation_trace": {"records": [trace, dict(trace)]},
                    "debug_records": [{"status": "accepted", "job_url": "job-duplicate"}],
                    "accepted_artifact_events": [artifact],
                },
            )
        ]
    )

    assert report["workload"]["attempted_generation_job_count"] == 1
    assert report["workload"]["generation_elapsed_ms"] == 100.0
    assert report["yield"]["first_pass_acceptance_count"] == 1


def test_baseline_merges_enriched_top_level_and_embedded_trace_for_timing_and_yield() -> None:
    embedded = {
        "trace_id": "trace-enriched-duplicate",
        "run_id": "run-enriched-duplicate",
        "scope_key": "job-enriched-duplicate",
        "attempts": [{"attempt_index": 1, "provider_status": "accepted"}],
        "output_summary": {"final_status": "accepted"},
        "efficiency_summary": {"provider_call_count": 1, "elapsed_ms": 100},
    }
    top_level = {
        **embedded,
        "record_id": "job-enriched-duplicate",
        "status": "accepted",
        "artifact_refs": {"stage_artifact": "cv_generation.json"},
    }
    artifact = accepted_cv_artifact_event_v1(
        artifact_id="cv-enriched-duplicate",
        job_url="job-enriched-duplicate",
        run_id="run-enriched-duplicate",
        trace_id="trace-enriched-duplicate",
        acceptance_mode="automatic",
        accepted_at="2026-10-02T00:01:00Z",
        finalized_at="2026-10-02T00:01:00Z",
    )

    report = build_baseline(
        [
            _run(
                "run-enriched-duplicate",
                {
                    "cv_generation_trace": {"records": [top_level]},
                    "debug_records": [
                        {
                            "status": "accepted",
                            "job_url": "job-enriched-duplicate",
                            "cv_generation_trace": embedded,
                        }
                    ],
                    "accepted_artifact_events": [artifact],
                },
            )
        ]
    )

    assert report["workload"]["attempted_generation_job_count"] == 1
    assert report["workload"]["generation_elapsed_ms"] == 100.0
    assert report["yield"]["first_pass_acceptance_count"] == 1
    assert report["runs"][0]["projection"]["trace_normalization"] == {
        "duplicate_count": 1,
        "conflict_count": 0,
        "conflict_trace_ids": [],
        "source_candidate_count": 2,
        "normalized_trace_count": 1,
    }


def test_baseline_does_not_turn_missing_generation_timing_into_zero() -> None:
    trace = {
        "trace_id": "trace-no-timing",
        "run_id": "run-no-timing",
        "job_url": "job-no-timing",
        "attempts": [{"attempt_index": 1, "provider_status": "accepted"}],
        "output_summary": {"final_status": "accepted"},
        "efficiency_summary": {"provider_call_count": 1},
    }
    artifact = accepted_cv_artifact_event_v1(
        artifact_id="cv-no-timing",
        job_url="job-no-timing",
        run_id="run-no-timing",
        trace_id="trace-no-timing",
        acceptance_mode="automatic",
        accepted_at="2026-10-02T00:01:00Z",
        finalized_at="2026-10-02T00:01:00Z",
    )

    report = build_baseline(
        [
            _run(
                "run-no-timing",
                {
                    "cv_generation_trace": {"records": [trace]},
                    "debug_records": [{"status": "accepted", "job_url": "job-no-timing"}],
                    "accepted_artifact_events": [artifact],
                },
            )
        ]
    )

    assert report["timing"]["generation_elapsed_ms"] is None
    assert report["timing"]["generation_timing_coverage"] == {"measured": 0, "unavailable": 1}


def test_material_report_metrics_ignore_volatile_report_fields() -> None:
    first = {"generated_at": "2026-10-02T00:00:00Z", "environment": {"python": "3.13"}, "status": "complete"}
    second = {"generated_at": "2026-10-02T01:00:00Z", "environment": {"python": "3.14"}, "status": "complete"}

    assert material_report_metrics(first) == material_report_metrics(second)


def test_material_report_digest_changes_only_for_material_metrics() -> None:
    first = {"generated_at": "2026-10-02T00:00:00Z", "status": "complete"}
    second = {"generated_at": "2026-10-02T01:00:00Z", "status": "complete"}
    changed = {"generated_at": "2026-10-02T01:00:00Z", "status": "incomplete"}

    assert material_report_digest(first) == material_report_digest(second)
    assert material_report_digest(first) != material_report_digest(changed)


def test_material_report_digest_binds_experiment_input_manifest() -> None:
    first = {"status": "complete", "input_manifest": {"arm": "local_first", "run_ids": ["one"]}}
    changed = {"status": "complete", "input_manifest": {"arm": "provider_first", "run_ids": ["one"]}}

    assert material_report_digest(first) != material_report_digest(changed)


def test_material_report_digest_binds_analysis_input_identity() -> None:
    first = {
        "analysis_input_identity": [{"fingerprints": ["one"], "selected_evidence_ids": ["ev-1"]}],
    }
    changed = {
        **first,
        "analysis_input_identity": [{"fingerprints": ["two"], "selected_evidence_ids": ["ev-2"]}],
    }

    assert material_report_digest(first) != material_report_digest(changed)


def test_canonical_evidence_redacts_local_paths_and_credentials() -> None:
    report = {
        "schema_version": "fitcv_runtime_efficiency_baseline_v3",
        "status": "complete",
        "environment": {"platform": "Windows"},
        "input_manifest": {
            "database_path": r"C:\Users\private\fitcv.sqlite3",
            "arm": "local_first",
        },
        "run": {
            "database_path": r"C:\Users\private\fitcv.sqlite3",
            "fixture_path": r"C:\Users\private\fixture.json",
            "api_key": "secret-canary",
            "accepted": 1,
        },
    }
    report["material_metrics_sha256"] = material_report_digest(report)

    evidence = build_canonical_evidence(
        report,
        source_commit="a" * 40,
        fixture_sha256="b" * 64,
        source_fixture_sha256="c" * 64,
    )

    assert evidence["evidence_status"] == "canonical"
    assert evidence["source_commit"] == "a" * 40
    assert evidence["run"] == {"accepted": 1}
    assert "environment" not in evidence
    assert evidence["material_metrics_sha256"] == material_report_digest(evidence)


def test_baseline_reports_unavailable_avoidance_fields_without_inventing_zeroes() -> None:
    report = build_baseline([])

    assert report["optimization_scorecard"]["provider_calls_avoided"]["status"] == "unavailable"
    assert report["optimization_scorecard"]["renders_avoided"]["status"] == "unavailable"


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


def test_baseline_fails_closed_when_failed_trace_identity_conflicts() -> None:
    accepted_trace = {
        "trace_id": "trace-accepted",
        "run_id": "run-1",
        "job_url": "job-accepted",
        "attempts": [{"attempt_index": 1, "provider_status": "accepted"}],
        "efficiency_summary": {"provider_call_count": 2, "token_usage": [{"total_tokens": 20}]},
    }
    failed_trace_a = {
        "trace_id": "trace-failed",
        "run_id": "run-1",
        "job_url": "job-failed",
        "attempts": [{"attempt_index": 1, "provider_status": "failed"}],
        "efficiency_summary": {"provider_call_count": 3, "token_usage": [{"total_tokens": 30}]},
    }
    failed_trace_b = {
        **failed_trace_a,
        "efficiency_summary": {"provider_call_count": 4, "token_usage": [{"total_tokens": 40}]},
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

    report = build_baseline(
        [
            _run(
                "run-1",
                {
                    "debug_records": [{"status": "accepted", "job_url": "job-accepted"}],
                    "cv_generation_trace": {
                        "records": [accepted_trace, failed_trace_a, failed_trace_b]
                    },
                    "accepted_artifact_events": [artifact],
                },
            )
        ]
    )

    assert report["status"] == "incomplete"
    assert report["accepted_cv"]["total_workload_cost_per_accepted_cv"] is None
    assert report["trace_normalization"]["conflict_trace_ids"] == ["trace-failed"]


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


def test_baseline_reports_measurement_coverage_without_fabricating_page_fit() -> None:
    trace = {
        "trace_id": "trace-coverage",
        "run_id": "run-coverage",
        "job_url": "job-coverage",
        "attempts": [{"attempt_index": 1, "provider_status": "accepted"}],
        "efficiency_summary": {
            "provider_call_count": 1,
            "elapsed_ms": 100,
            "token_usage": [{"total_tokens": 10}],
            "review_question_count": 1,
            "human_action_count": 0,
        },
    }
    artifact = {
        "artifact_id": "cv-coverage",
        "job_url": "job-coverage",
        "run_id": "run-coverage",
        "trace_id": "trace-coverage",
        "acceptance_mode": "automatic",
        "accepted_at": "2026-10-02T00:01:00Z",
        "finalized_at": "2026-10-02T00:01:00Z",
    }

    report = build_baseline([
        _run(
            "run-coverage",
            {
                "debug_records": [{"status": "accepted", "job_url": "job-coverage"}],
                "cv_generation_trace": {"records": [trace]},
                "accepted_artifact_events": [artifact],
            },
        )
    ])

    assert report["coverage"]["attribution"]["complete"] is True
    assert report["coverage"]["page_fit"]["measured"] == 0
    assert report["coverage"]["page_fit"]["complete"] is False
    assert report["run_job_diversity"]["run_count"] == 1


def test_baseline_counts_measured_page_fit_failure_as_failure_not_unavailable() -> None:
    trace = {
        "trace_id": "trace-page-fit-fail",
        "run_id": "run-page-fit-fail",
        "job_url": "job-page-fit-fail",
        "attempts": [{"attempt_index": 1, "provider_status": "accepted"}],
        "output_summary": {"final_status": "accepted"},
        "efficiency_summary": {"provider_call_count": 1, "elapsed_ms": 100},
    }
    artifact = accepted_cv_artifact_event_v1(
        artifact_id="cv-page-fit-fail",
        job_url="job-page-fit-fail",
        run_id="run-page-fit-fail",
        trace_id="trace-page-fit-fail",
        acceptance_mode="automatic",
        accepted_at="2026-10-02T00:01:00Z",
        finalized_at="2026-10-02T00:01:00Z",
    )
    artifact["page_fit_status"] = "fail"
    artifact["render_acceptance"] = {"page_count": 2, "page_fit_status": "fail"}

    report = build_baseline([
        _run(
            "run-page-fit-fail",
            {
                "debug_records": [{"status": "accepted", "job_url": "job-page-fit-fail"}],
                "cv_generation_trace": {"records": [trace]},
                "accepted_artifact_events": [artifact],
            },
        )
    ])

    success = report["runs"][0]["coverage"]["page_fit_success"]
    assert success["measured"] == 1
    assert success["unavailable"] == 0
    assert success["fail"] == 1
    assert success["complete"] is True
    assert report["outcomes"]["page_fit"]["fail"] == 1
    assert report["status"] == "incomplete"


def test_baseline_marks_pre_contract_records_historical() -> None:
    trace = {
        "trace_id": "trace-historical",
        "run_id": "run-historical",
        "job_url": "job-historical",
        "attempts": [{"attempt_index": 1, "provider_status": "accepted"}],
        "output_summary": {"final_status": "accepted"},
        "efficiency_summary": {"provider_call_count": 1, "elapsed_ms": 100},
    }
    artifact = accepted_cv_artifact_event_v1(
        artifact_id="cv-historical",
        job_url="job-historical",
        run_id="run-historical",
        trace_id="trace-historical",
        acceptance_mode="automatic",
        accepted_at="2026-10-02T00:01:00Z",
        finalized_at="2026-10-02T00:01:00Z",
    )
    artifact.pop("final_artifact_contract_version")

    report = build_baseline([
        _run(
            "run-historical",
            {
                "debug_records": [{"status": "accepted", "job_url": "job-historical"}],
                "cv_generation_trace": {"records": [trace]},
                "accepted_artifact_events": [artifact],
            },
        )
    ])

    assert report["selection"]["current_contract_record_count"] == 0
    assert report["selection"]["historical_record_count"] == 1
    assert report["status"] == "incomplete"


def test_baseline_uses_canonical_run_job_types_not_scope_type() -> None:
    traces = [
        {
            "trace_id": "trace-job-type-1",
            "run_id": "run-job-types",
            "run_job_id": "run-job-types-1",
            "job_url": "job-type-1",
            "scope_type": "job",
            "attempts": [{"attempt_index": 1, "provider_status": "accepted"}],
            "efficiency_summary": {"provider_call_count": 1, "elapsed_ms": 100, "token_usage": [{"total_tokens": 10}]},
        },
        {
            "trace_id": "trace-job-type-2",
            "run_id": "run-job-types",
            "run_job_id": "run-job-types-2",
            "job_url": "job-type-2",
            "scope_type": "job",
            "attempts": [{"attempt_index": 1, "provider_status": "accepted"}],
            "efficiency_summary": {"provider_call_count": 1, "elapsed_ms": 100, "token_usage": [{"total_tokens": 10}]},
        },
    ]
    artifacts = [
        accepted_cv_artifact_event_v1(
            artifact_id=f"cv-job-type-{index}",
            job_url=f"job-type-{index}",
            run_id="run-job-types",
            run_job_id=f"run-job-types-{index}",
            trace_id=f"trace-job-type-{index}",
            acceptance_mode="automatic",
            accepted_at="2026-10-02T00:01:00Z",
            finalized_at="2026-10-02T00:01:00Z",
        )
        for index in (1, 2)
    ]

    report = build_baseline(
        [
            _run(
                "run-job-types",
                {
                    "debug_records": [
                        {"status": "accepted", "job_url": "job-type-1"},
                        {"status": "accepted", "job_url": "job-type-2"},
                    ],
                    "cv_generation_trace": {"records": traces},
                    "accepted_artifact_events": artifacts,
                },
            )
        ],
        run_jobs_by_run_id={
            "run-job-types": [
                {"run_job_id": "run-job-types-1", "source_snapshot": {"contractType": "Part-time"}},
                {"run_job_id": "run-job-types-2", "source_snapshot": {"contractType": "Internship"}},
            ]
        },
    )

    assert report["run_job_diversity"]["job_type_count"] == 2
    assert report["run_job_diversity"]["job_types"] == ["Internship", "Part-time"]
