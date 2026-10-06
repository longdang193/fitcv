import json
from pathlib import Path

from scripts.fitcv_analytics import (
    build_bronze_observations,
    build_gold_acceptance_state,
    build_gold_candidate_gap,
    build_gold_cv_effort,
    build_gold_optimization_state,
    build_gold_semantic_metric,
    build_gold_requirement_demand,
    build_silver_facts,
    compute_projection_input_fingerprint,
    load_metric_registry,
    material_gold_digest,
    rebuild_analytics_bundle,
    write_analytics_sqlite,
)


def test_metric_registry_has_unique_contracts_and_claim_mapping() -> None:
    registry = load_metric_registry()
    assert {metric["metric_id"] for metric in registry["metrics"]} >= {
        "acceptance_yield",
        "provider_calls_per_accepted_cv",
        "tokens_per_accepted_cv",
        "evidence_gap",
    }
    assert registry["claim_priority_map"]["p0_acceptance_scope"] == ["p0_a", "p0_b", "p0_c"]
    assert registry["claim_priority_map"]["p1b_current_contract_measurement"] == ["p1_b"]


def test_acceptance_state_rejects_unknown_claim_priority() -> None:
    try:
        build_gold_acceptance_state({"records": [{"claim": "unknown"}]}, {"status_dimensions": {}})
    except ValueError as exc:
        assert str(exc) == "analytics_claim_priority_mapping_missing:unknown"
    else:
        raise AssertionError("unknown claim accepted")


def test_silver_reconciles_mutable_snapshots_but_bronze_keeps_history() -> None:
    bronze = build_bronze_observations(
        {
            "provider_attempt": [
                {"source_id": "attempt-1", "run_job_id": "job-1", "observed_at": "2026-10-01T00:00:00Z", "token_total": 10},
                {"source_id": "attempt-1", "run_job_id": "job-1", "observed_at": "2026-10-01T00:01:00Z", "token_total": 20},
            ]
        },
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="2026-10-05T00:00:00Z",
    )
    silver = build_silver_facts(bronze)
    assert len(bronze) == 2
    assert len(silver) == 1
    assert silver[0]["payload"]["token_total"] == 20
    assert len(silver[0]["superseded_observation_ids"]) == 1


def test_newer_authoritative_invalidation_supersedes_older_valid_snapshot() -> None:
    bronze = build_bronze_observations(
        {
            "provider_attempt": [
                {"source_id": "attempt-1", "run_job_id": "job-1", "revision": 1, "observed_at": "2026-10-01T00:00:00Z", "token_total": 10, "validity": "valid"},
                {"source_id": "attempt-1", "run_job_id": "job-1", "revision": 2, "observed_at": "2026-10-01T00:01:00Z", "token_total": 10, "validity": "invalid"},
            ]
        },
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="2026-10-05T00:00:00Z",
    )

    silver = build_silver_facts(bronze)

    assert len(silver) == 1
    assert silver[0]["validity"] == "invalid"
    assert silver[0]["payload"]["revision"] == 2
    assert len(silver[0]["superseded_observation_ids"]) == 1


def test_silver_preserves_conflicting_trace_observations() -> None:
    bronze = build_bronze_observations(
        {
            "trace": [
                {"source_id": "trace-1", "run_job_id": "job-1", "observed_at": "2026-10-01T00:00:00Z", "status": "accepted"},
                {"source_id": "trace-1", "run_job_id": "job-1", "observed_at": "2026-10-01T00:01:00Z", "status": "failed"},
            ]
        },
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="2026-10-05T00:00:00Z",
    )
    silver = build_silver_facts(bronze)
    assert len(silver) == 2


def test_rebuild_is_deterministic_and_sql_views_match_gold(tmp_path) -> None:
    bundle = {
        "sources": {
            "provider_attempt": [{"source_id": "p-1", "run_job_id": "job-1", "provider_call_count": 2, "token_total": 10}],
            "accepted_artifact": [{"source_id": "a-1", "run_job_id": "job-1", "artifact_id": "cv-1", "status": "accepted"}],
        },
        "registry": {"records": []},
        "state": {},
    }
    first = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="one")
    second = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="two")
    assert first["material_metrics_sha256"] == second["material_metrics_sha256"]

    database = tmp_path / "analytics.sqlite3"
    write_analytics_sqlite(
        path=database,
        artifacts=first["gold"]["gold_cv_artifact"],
        run_jobs=first["gold"]["gold_run_job_effort"],
        cohorts=first["gold"]["gold_cohort_effort"],
        acceptance=first["gold"]["gold_acceptance_state"],
    )
    import sqlite3
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT artifact_id FROM gold_cv_artifact").fetchone() == ("cv-1",)
        assert connection.execute("SELECT provider_call_count FROM gold_run_job_effort").fetchone() == (2,)


def test_semantic_metric_builder_emits_registry_fields_and_expected_value() -> None:
    bundle = json.loads(Path("tests/fixtures/analytics_semantic_contract.json").read_text(encoding="utf-8"))
    rebuilt = rebuild_analytics_bundle(
        bundle,
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="now",
    )
    rows = rebuilt["gold"]["gold_semantic_metric"]
    acceptance = next(row for row in rows if row["metric_id"] == "acceptance_yield")
    assert {"numerator", "denominator", "value", "coverage_status", "unavailable_reason"} <= set(acceptance)
    assert acceptance["value"] is None
    assert acceptance["coverage_status"] == "unavailable"
    assert {row["metric_id"] for row in rows} == {metric["metric_id"] for metric in load_metric_registry()["metrics"]}


def test_semantic_metric_uses_metric_coverage_and_run_job_denominators() -> None:
    registry = load_metric_registry()
    gold = {
        "gold_cohort_effort": [{
            "cohort_id": "c",
            "cohort_type": "fixture",
            "successful_run_job_count": 1,
            "attempted_job_count": 1,
            "generation_job_count": 1,
            "first_pass_success_count": 1,
            "generation_attempt_coverage": "complete",
            "verified_one_page_count": 1,
            "render_proof_count": 1,
            "coverage": "complete",
            "render_proof_coverage": "unavailable",
        }],
        "gold_run_job_effort": [{
            "run_job_id": "job-1",
            "review_action_count": 1,
            "manual_attempted_run_job_count": 1,
            "review_action_coverage": "complete",
            "coverage": "complete",
        }],
        "gold_requirement_demand": [],
        "gold_candidate_gap": [],
    }
    rows = build_gold_semantic_metric(gold, registry, source_commit="head", input_fingerprint="input")
    accepted = next(row for row in rows if row["metric_id"] == "acceptance_yield")
    first_pass = next(row for row in rows if row["metric_id"] == "first_pass_success")
    render = next(row for row in rows if row["metric_id"] == "verified_one_page_rate")
    effort = next(row for row in rows if row["metric_id"] == "manual_effort")
    assert accepted["value"] == 1.0
    assert first_pass["value"] == 1.0
    assert render["value"] is None
    assert render["coverage_status"] == "unavailable"
    assert effort["denominator"] == 1
    assert effort["value"] == 1.0


def test_run_job_gold_ignores_requirement_and_gap_sources() -> None:
    bundle = json.loads(Path("tests/fixtures/analytics_semantic_contract.json").read_text(encoding="utf-8"))
    result = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    assert result["gold"]["gold_cohort_effort"][0]["attempted_job_count"] == 1


def test_gold_cohort_exposes_declared_first_pass_and_render_metrics() -> None:
    bundle = json.loads(Path("tests/fixtures/analytics_semantic_contract.json").read_text(encoding="utf-8"))
    cohort = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")["gold"]["gold_cohort_effort"][0]
    assert "first_pass_success_count" in cohort
    assert "verified_one_page_rate" in cohort
    assert cohort["provider_call_coverage"] == "complete"
    assert cohort["token_coverage"] == "complete"


def test_cohort_provider_metrics_ignore_incomplete_review_coverage() -> None:
    bundle = json.loads(Path("tests/fixtures/analytics_semantic_contract.json").read_text(encoding="utf-8"))
    bundle["sources"]["review_action"] = [{
        "source_id": "review-invalid",
        "run_job_id": "job-1",
        "action": "approve",
        "validity": "invalid",
        "cohort_id": "cohort-1",
        "cohort_type": "fixture",
    }]
    result = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    cohort = result["gold"]["gold_cohort_effort"][0]
    assert cohort["provider_call_coverage"] == "complete"
    assert cohort["token_coverage"] == "complete"
    metrics = {row["metric_id"]: row for row in result["gold"]["gold_semantic_metric"]}
    assert metrics["provider_calls_per_accepted_cv"]["value"] == 2.0
    assert metrics["tokens_per_accepted_cv"]["value"] == 100.0


def test_provider_call_metric_stays_known_when_tokens_are_missing() -> None:
    bundle = json.loads(Path("tests/fixtures/analytics_semantic_contract.json").read_text(encoding="utf-8"))
    bundle["sources"]["provider_attempt"][0]["token_total"] = None
    result = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")
    cohort = result["gold"]["gold_cohort_effort"][0]
    assert cohort["provider_call_count"] == 2
    assert cohort["provider_call_coverage"] == "complete"
    assert cohort["token_coverage"] == "unavailable"
    metrics = {row["metric_id"]: row for row in result["gold"]["gold_semantic_metric"]}
    assert metrics["provider_calls_per_accepted_cv"]["value"] == 2.0
    assert metrics["tokens_per_accepted_cv"]["value"] is None


def test_oversized_token_totals_stay_unavailable_without_overflow() -> None:
    result = rebuild_analytics_bundle(
        {
            "sources": {
                "provider_attempt": [
                    {"source_id": "provider-1", "run_job_id": "job-1", "provider_call_count": 1, "token_total": 10**400, "cohort_id": "c", "cohort_type": "fixture"},
                    {"source_id": "provider-2", "run_job_id": "job-1", "provider_call_count": 1, "token_total": 1e308, "cohort_id": "c", "cohort_type": "fixture"},
                ],
            },
            "registry": {},
            "state": {},
        },
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="now",
    )
    row = result["gold"]["gold_run_job_effort"][0]
    assert row["token_total"] is None
    assert row["token_coverage"] == "unavailable"


def test_acceptance_yield_excludes_artifacts_without_generation_history() -> None:
    result = rebuild_analytics_bundle(
        {
            "sources": {
                "generation_attempt": [{"source_id": "generation", "run_job_id": "job-1", "status": "succeeded", "attempt_count": 1, "cohort_id": "c", "cohort_type": "fixture"}],
                "accepted_artifact": [
                    {"source_id": "artifact-1", "run_job_id": "job-1", "artifact_id": "cv-1", "status": "accepted", "cohort_id": "c", "cohort_type": "fixture"},
                    {"source_id": "artifact-2", "run_job_id": "job-2", "artifact_id": "cv-2", "status": "accepted", "cohort_id": "c", "cohort_type": "fixture"},
                ],
            },
            "registry": {},
            "state": {},
        },
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="now",
    )
    cohort = result["gold"]["gold_cohort_effort"][0]
    assert cohort["successful_run_job_count"] == 1
    assert cohort["generation_job_count"] == 1
    acceptance = next(row for row in result["gold"]["gold_semantic_metric"] if row["metric_id"] == "acceptance_yield")
    assert acceptance["value"] == 1.0


def test_acceptance_yield_excludes_ineligible_generation_jobs() -> None:
    result = rebuild_analytics_bundle(
        {
            "sources": {
                "generation_attempt": [
                    {"source_id": "eligible", "run_job_id": "job-1", "status": "succeeded", "attempt_count": 1, "cohort_id": "c", "cohort_type": "fixture", "eligible": True},
                    {"source_id": "ineligible", "run_job_id": "job-2", "status": "succeeded", "attempt_count": 1, "cohort_id": "c", "cohort_type": "fixture", "eligible": False},
                ],
                "provider_attempt": [
                    {"source_id": "provider-1", "run_job_id": "job-1", "provider_call_count": 1, "token_total": 10, "cohort_id": "c", "cohort_type": "fixture"},
                    {"source_id": "provider-2", "run_job_id": "job-2", "provider_call_count": 1, "token_total": 10, "cohort_id": "c", "cohort_type": "fixture"},
                ],
                "accepted_artifact": [
                    {"source_id": "artifact-1", "run_job_id": "job-1", "artifact_id": "cv-1", "status": "accepted", "cohort_id": "c", "cohort_type": "fixture"},
                    {"source_id": "artifact-2", "run_job_id": "job-2", "artifact_id": "cv-2", "status": "accepted", "cohort_id": "c", "cohort_type": "fixture"},
                ],
            },
            "registry": {},
            "state": {},
        },
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="now",
    )
    cohort = result["gold"]["gold_cohort_effort"][0]
    assert cohort["successful_run_job_count"] == 1
    assert cohort["generation_job_count"] == 1
    assert cohort["accepted_artifact_count"] == 2
    metrics = {row["metric_id"]: row for row in result["gold"]["gold_semantic_metric"]}
    assert metrics["provider_calls_per_accepted_cv"]["value"] == 1.0
    assert metrics["tokens_per_accepted_cv"]["value"] == 10.0


def test_registry_fallback_preserves_supplied_records() -> None:
    result = rebuild_analytics_bundle(
        {
            "sources": {},
            "registry": {
                "claim_priority_map": {"claim": ["priority"]},
                "records": [{"evidence_id": "fixture-evidence", "claim": "claim", "status": "current"}],
            },
            "state": {"implementation": {"priority": "accepted"}, "acceptance": {"priority": "accepted"}},
        },
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="now",
    )
    assert result["gold"]["gold_acceptance_state"][0]["evidence_id"] == "fixture-evidence"


def test_persistence_failed_is_terminal_generation_evidence() -> None:
    result = rebuild_analytics_bundle(
        {
            "sources": {
                "generation_attempt": [{"source_id": "generation", "run_job_id": "job", "status": "persistence_failed", "attempt_count": 1, "cohort_id": "c", "cohort_type": "fixture"}],
            },
            "registry": {},
            "state": {},
        },
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="now",
    )
    row = result["gold"]["gold_run_job_effort"][0]
    assert row["generation_attempt_coverage"] == "complete"
    assert row["failed_generation_attempt_count"] == 1


def test_direct_invalid_token_facts_become_unavailable() -> None:
    bronze = build_bronze_observations(
        {"provider_attempt": [{"source_id": "provider", "run_job_id": "job", "token_total": "not_recorded", "cohort_id": "c", "cohort_type": "fixture"}]},
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="now",
    )
    row = rebuild_analytics_bundle({"sources": {"provider_attempt": [{"source_id": "provider", "run_job_id": "job", "token_total": -1, "cohort_id": "c", "cohort_type": "fixture"}]}, "registry": {}, "state": {}}, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")["gold"]["gold_run_job_effort"][0]
    assert row["token_total"] is None


def test_malformed_attempt_count_is_unavailable_without_crashing() -> None:
    result = rebuild_analytics_bundle(
        {
            "sources": {
                "generation_attempt": [{
                    "source_id": "generation",
                    "run_job_id": "job",
                    "status": "succeeded",
                    "attempt_count": "not_recorded",
                    "cohort_id": "c",
                    "cohort_type": "fixture",
                }],
            },
            "registry": {},
            "state": {},
        },
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="now",
    )

    row = result["gold"]["gold_run_job_effort"][0]
    assert row["first_pass_success_count"] == 0
    assert row["generation_attempt_coverage"] == "unavailable"


def test_first_pass_rate_uses_generation_jobs_not_attempt_rows() -> None:
    result = rebuild_analytics_bundle(
        {
            "sources": {
                    "generation_attempt": [
                        {"source_id": "first", "run_job_id": "job-1", "status": "failed", "attempt_count": 2, "cohort_id": "c", "cohort_type": "fixture"},
                        {"source_id": "second", "run_job_id": "job-2", "status": "succeeded", "attempt_count": 1, "cohort_id": "c", "cohort_type": "fixture"},
                    ],
                    "accepted_artifact": [{"source_id": "artifact-2", "run_job_id": "job-2", "artifact_id": "cv-2", "status": "accepted"}],
            },
            "registry": {},
            "state": {},
        },
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="now",
    )

    cohort = result["gold"]["gold_cohort_effort"][0]
    assert cohort["first_pass_success_count"] == 1
    assert cohort["first_pass_success_rate"] == 0.5


def test_multiple_generation_rows_do_not_claim_first_pass_success() -> None:
    result = rebuild_analytics_bundle(
        {
            "sources": {
                "generation_attempt": [
                    {"source_id": "first", "run_job_id": "job", "status": "failed", "attempt_count": 1, "cohort_id": "c", "cohort_type": "fixture"},
                    {"source_id": "retry", "run_job_id": "job", "status": "succeeded", "attempt_count": 1, "cohort_id": "c", "cohort_type": "fixture"},
                ],
            },
            "registry": {},
            "state": {},
        },
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="now",
    )

    cohort = result["gold"]["gold_cohort_effort"][0]
    assert cohort["first_pass_success_count"] == 0
    assert cohort["first_pass_success_rate"] == 0.0


def test_first_pass_requires_durable_accepted_artifact() -> None:
    result = rebuild_analytics_bundle(
        {
            "sources": {
                "generation_attempt": [{"source_id": "generation", "run_job_id": "job", "status": "succeeded", "attempt_count": 1, "cohort_id": "c", "cohort_type": "fixture"}],
            },
            "registry": {},
            "state": {},
        },
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="now",
    )

    assert result["gold"]["gold_run_job_effort"][0]["first_pass_success_count"] == 0


def test_invalid_generation_fact_keeps_first_pass_rate_unavailable() -> None:
    result = rebuild_analytics_bundle(
        {
            "sources": {
                    "generation_attempt": [
                        {"source_id": "valid", "run_job_id": "job-1", "status": "succeeded", "attempt_count": 1, "cohort_id": "c", "cohort_type": "fixture"},
                        {"source_id": "invalid", "run_job_id": "job-2", "status": "failed", "attempt_count": 2, "validity": "invalid", "cohort_id": "c", "cohort_type": "fixture"},
                    ],
                    "accepted_artifact": [{"source_id": "artifact-1", "run_job_id": "job-1", "artifact_id": "cv-1", "status": "accepted"}],
            },
            "registry": {},
            "state": {},
        },
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="now",
    )

    cohort = result["gold"]["gold_cohort_effort"][0]
    assert cohort["first_pass_success_count"] == 1
    assert cohort["first_pass_success_rate"] is None
    assert cohort["generation_attempt_coverage"] == "unavailable"


def test_invalid_provider_fact_keeps_cost_ratio_unavailable() -> None:
    result = rebuild_analytics_bundle(
        {
            "sources": {
                "provider_attempt": [
                    {"source_id": "valid", "run_job_id": "job", "provider_call_count": 2, "token_total": 10, "cohort_id": "c", "cohort_type": "fixture"},
                    {"source_id": "invalid", "run_job_id": "job", "provider_call_count": 3, "token_total": 12, "validity": "invalid", "cohort_id": "c", "cohort_type": "fixture"},
                ],
                "accepted_artifact": [{"source_id": "artifact", "run_job_id": "job", "artifact_id": "cv", "status": "accepted", "cohort_id": "c", "cohort_type": "fixture"}],
            },
            "registry": {},
            "state": {},
        },
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="now",
    )

    row = result["gold"]["gold_cohort_effort"][0]
    assert row["provider_call_count"] is None
    assert row["token_total"] is None
    assert row["per_accepted_artifact"] is None


def test_incomplete_provider_and_artifact_coverage_keeps_cost_ratio_unavailable() -> None:
    result = rebuild_analytics_bundle(
        {
            "sources": {
                "provider_attempt": [{"source_id": "provider", "run_job_id": "job", "provider_call_count": 2, "token_total": 10, "coverage": "incomplete", "cohort_id": "c", "cohort_type": "fixture"}],
                "accepted_artifact": [
                    {"source_id": "valid-artifact", "run_job_id": "job", "artifact_id": "cv", "status": "accepted", "cohort_id": "c", "cohort_type": "fixture"},
                    {"source_id": "invalid-artifact", "run_job_id": "job", "artifact_id": "cv-invalid", "status": "accepted", "validity": "invalid", "cohort_id": "c", "cohort_type": "fixture"},
                ],
            },
            "registry": {},
            "state": {},
        },
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="now",
    )

    row = result["gold"]["gold_cohort_effort"][0]
    assert row["coverage"] == "unavailable"
    assert row["per_accepted_artifact"] is None


def test_malformed_render_proof_stays_unavailable() -> None:
    for render_acceptance in (True, "bad", ["bad"], {"render_status": "pass", "page_count": True, "page_fit_status": "pass"}):
        result = rebuild_analytics_bundle(
            {
                "sources": {
                    "accepted_artifact": [{
                        "source_id": "artifact",
                        "run_job_id": "job",
                        "artifact_id": "cv",
                        "status": "accepted",
                        "render_acceptance": render_acceptance,
                        "cohort_id": "c",
                        "cohort_type": "fixture",
                    }],
                },
                "registry": {},
                "state": {},
            },
            source_commit="head",
            declared_input_fingerprint="inputs",
            ingested_at="now",
        )

        artifact = result["gold"]["gold_cv_artifact"][0]
        assert artifact["render_proof"] is False
        assert artifact["verified_one_page"] is False


def test_fractional_and_boolean_telemetry_stays_unavailable() -> None:
    result = rebuild_analytics_bundle(
        {
            "sources": {
                "provider_attempt": [{"source_id": "provider", "run_job_id": "job", "provider_call_count": 1.5, "token_total": True, "cohort_id": "c", "cohort_type": "fixture"}],
            },
            "registry": {},
            "state": {},
        },
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="now",
    )

    row = result["gold"]["gold_run_job_effort"][0]
    assert row["provider_call_count"] is None
    assert row["token_total"] is None


def test_deferred_status_dimension_sets_deferred_flag() -> None:
    rows = build_gold_acceptance_state(
        {"claim_priority_map": {"claim": ["p1_c"]}, "records": [{"evidence_id": "e", "claim": "claim", "status": "current"}]},
        {"status_dimensions": {"p1_c": {"implementation_status": "deferred", "acceptance_status": "deferred", "measurement_status": "not_applicable"}}},
    )
    assert rows[0]["deferred"] is True


def test_requirement_and_gap_gold_have_explicit_grains_and_distinct_denominators() -> None:
    bronze = build_bronze_observations(
        {
            "posting_requirement": [
                {"source_id": "pr-1", "posting_id": "post-1", "requirement": "python", "cohort_id": "c", "cohort_type": "fixture"},
                {"source_id": "pr-2", "posting_id": "post-1", "requirement": "python", "cohort_id": "c", "cohort_type": "fixture"},
                {"source_id": "pr-3", "posting_id": "post-2", "requirement": "python", "cohort_id": "c", "cohort_type": "fixture"},
            ],
            "candidate_gap": [
                {"source_id": "gap-1", "posting_id": "post-1", "requirement": "python", "gap_category": "missing_evidence", "cohort_id": "c", "cohort_type": "fixture"},
            ],
        },
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="now",
    )
    silver = build_silver_facts(bronze)
    demand = build_gold_requirement_demand(silver)
    gaps = build_gold_candidate_gap(silver)
    assert demand[0]["grain"] == "requirement_and_cohort"
    assert demand[0]["numerator_posting_count"] == 2
    assert demand[0]["denominator_posting_count"] == 2
    assert gaps[0]["grain"] == "requirement_and_gap_category_and_cohort"
    assert gaps[0]["numerator_requirement_count"] == 1
    assert gaps[0]["denominator_requirement_count"] == 2


def test_requirement_gold_filters_unrelated_and_invalid_facts_and_marks_coverage() -> None:
    bronze = build_bronze_observations(
        {
            "posting_requirement": [
                {"source_id": "valid", "posting_id": "post-1", "requirement": "python", "cohort_id": "c", "cohort_type": "fixture"},
                {"source_id": "invalid", "posting_id": "post-2", "requirement": "python", "validity": "invalid", "cohort_id": "c", "cohort_type": "fixture"},
            ],
            "provider_attempt": [
                {"source_id": "noise", "posting_id": "post-noise", "requirement": "python", "cohort_id": "c", "cohort_type": "fixture"},
            ],
        },
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="now",
    )
    demand = build_gold_requirement_demand(build_silver_facts(bronze))
    assert demand[0]["numerator_posting_count"] == 1
    assert demand[0]["coverage"] == "unavailable"
    assert demand[0]["unavailable_reason"] == "invalid_source_fact"


def test_invalid_only_requirement_fact_still_emits_unavailable_gold_row() -> None:
    bronze = build_bronze_observations(
        {"posting_requirement": [{"source_id": "invalid", "posting_id": "post-1", "requirement": "python", "validity": "invalid", "cohort_id": "c", "cohort_type": "fixture"}]},
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="now",
    )
    demand = build_gold_requirement_demand(build_silver_facts(bronze))
    assert demand == [{
        "schema_version": "fitcv.analytics.v2",
        "metric": "gold_requirement_demand",
        "grain": "requirement_and_cohort",
        "requirement": "python",
        "cohort_id": "c",
        "cohort_type": "fixture",
        "numerator_posting_count": 0,
        "denominator_posting_count": 0,
        "coverage": "unavailable",
        "posting_inventory_coverage": "unavailable",
        "unavailable_reason": "invalid_source_fact",
    }]


def test_candidate_gap_filters_unmatched_and_invalid_facts() -> None:
    bronze = build_bronze_observations(
        {
            "posting_requirement": [{"source_id": "pr", "posting_id": "post-1", "requirement": "python", "cohort_id": "c", "cohort_type": "fixture"}],
            "candidate_gap": [
                {"source_id": "unmatched", "posting_id": "post-2", "requirement": "python", "gap_category": "missing_evidence", "cohort_id": "c", "cohort_type": "fixture"},
                {"source_id": "invalid", "posting_id": "post-3", "requirement": "python", "gap_category": "missing_evidence", "validity": "invalid", "cohort_id": "c", "cohort_type": "fixture"},
            ],
        },
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="now",
    )
    gaps = build_gold_candidate_gap(build_silver_facts(bronze))
    assert gaps[0]["numerator_requirement_count"] == 0
    assert gaps[0]["denominator_requirement_count"] == 1
    assert gaps[0]["coverage"] == "unavailable"


def test_invalid_only_candidate_gap_emits_unavailable_gold_row() -> None:
    bronze = build_bronze_observations(
        {"candidate_gap": [{"source_id": "invalid", "posting_id": "post-1", "requirement": "python", "gap_category": "missing_evidence", "validity": "invalid", "cohort_id": "c", "cohort_type": "fixture"}]},
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="now",
    )
    gaps = build_gold_candidate_gap(build_silver_facts(bronze))
    assert gaps[0]["coverage"] == "unavailable"
    assert gaps[0]["unavailable_reason"] == "invalid_source_fact"


def test_requirement_demand_uses_explicit_posting_inventory_denominator() -> None:
    bundle = {
        "sources": {
            "posting_inventory": [
                {"source_id": "posting-1", "posting_id": "posting-1", "eligible": True, "extraction_status": "complete", "cohort_id": "c", "cohort_type": "fixture"},
                {"source_id": "posting-2", "posting_id": "posting-2", "eligible": True, "extraction_status": "complete", "cohort_id": "c", "cohort_type": "fixture"},
            ],
            "posting_requirement": [
                {"source_id": "requirement-1", "posting_id": "posting-1", "requirement": "python", "cohort_id": "c", "cohort_type": "fixture"},
            ],
        },
        "registry": {},
        "state": {},
    }

    demand = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")["gold"]["gold_requirement_demand"]

    row = next(item for item in demand if item["requirement"] == "python")
    assert row["numerator_posting_count"] == 1
    assert row["denominator_posting_count"] == 2
    assert row["coverage"] == "complete"


def test_unknown_posting_inventory_extraction_makes_demand_unavailable() -> None:
    bundle = {
        "sources": {
            "posting_inventory": [
                {"source_id": "posting-1", "posting_id": "posting-1", "eligible": True, "extraction_status": "unknown", "cohort_id": "c", "cohort_type": "fixture"},
            ],
            "posting_requirement": [
                {"source_id": "requirement-1", "posting_id": "posting-1", "requirement": "python", "cohort_id": "c", "cohort_type": "fixture"},
            ],
        },
        "registry": {},
        "state": {},
    }

    row = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")["gold"]["gold_requirement_demand"][0]

    assert row["denominator_posting_count"] == 0
    assert row["coverage"] == "unavailable"
    assert row["unavailable_reason"] == "extraction_status_incomplete"


def test_same_requirement_remains_in_each_declared_cohort() -> None:
    bronze = build_bronze_observations(
        {
            "posting_requirement": [
                {"source_id": "r-1", "posting_id": "posting-1", "requirement": "python", "cohort_id": "old", "cohort_type": "fixture"},
                {"source_id": "r-2", "posting_id": "posting-1", "requirement": "python", "cohort_id": "new", "cohort_type": "fixture"},
            ],
        },
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="now",
    )

    rows = build_gold_requirement_demand(build_silver_facts(bronze))

    assert {(row["cohort_id"], row["requirement"]) for row in rows} == {("old", "python"), ("new", "python")}


def test_candidate_gap_is_partitioned_by_candidate_profile_revision() -> None:
    bundle = {
        "sources": {
            "posting_requirement": [
                {"source_id": "requirement-1", "posting_id": "posting-1", "requirement": "python", "cohort_id": "c", "cohort_type": "fixture"},
            ],
            "candidate_gap": [
                {"source_id": "gap-1", "posting_id": "posting-1", "requirement": "python", "gap_category": "missing_evidence", "candidate_profile_id": "candidate-1", "candidate_profile_revision": "1", "candidate_profile_fingerprint": "fp-1", "cohort_id": "c", "cohort_type": "fixture"},
                {"source_id": "gap-2", "posting_id": "posting-1", "requirement": "python", "gap_category": "missing_evidence", "candidate_profile_id": "candidate-1", "candidate_profile_revision": "2", "candidate_profile_fingerprint": "fp-2", "cohort_id": "c", "cohort_type": "fixture"},
            ],
        },
        "registry": {},
        "state": {},
    }

    gaps = rebuild_analytics_bundle(bundle, source_commit="head", declared_input_fingerprint="inputs", ingested_at="now")["gold"]["gold_candidate_gap"]

    assert {(row["candidate_profile_revision"], row["candidate_profile_fingerprint"]) for row in gaps} == {("1", "fp-1"), ("2", "fp-2")}


def test_acceptance_and_optimization_state_are_separate() -> None:
    result = rebuild_analytics_bundle(
        {
            "sources": {},
            "registry": {"records": [{"claim": "p1_acceptance_scope", "evidence_id": "evidence-1", "status": "unavailable"}]},
            "state": {"status_dimensions": {"p1_b": {"implementation_status": "verified", "acceptance_status": "passed", "measurement_status": "incomplete", "optimization_status": "rejected"}}},
        },
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="now",
    )

    assert "optimization_status" not in result["gold"]["gold_acceptance_state"][0]
    assert result["gold"]["gold_optimization_state"][0]["optimization_status"] == "rejected"


def test_projection_fingerprint_changes_with_declared_input(tmp_path) -> None:
    registry = tmp_path / "metrics.yaml"
    source = tmp_path / "source.txt"
    source.write_text("one\n", encoding="utf-8")
    registry.write_text(
        "schema_version: fitcv.analytics_metrics.v1\n"
        "projection_inputs: [source.txt]\n"
        "metrics: [{metric_id: x, version: 1, source_model: x, grain: x, numerator: x, denominator: x, dimensions: [], cohort_policy: x, null_policy: x, coverage_metric: x, owner: x, description: x}]\n"
        "claim_priority_map: {x: [p1]}\n",
        encoding="utf-8",
    )
    first = compute_projection_input_fingerprint(tmp_path, registry)
    source.write_text("two\n", encoding="utf-8")
    assert compute_projection_input_fingerprint(tmp_path, registry) != first


def test_gold_effort_aggregates_one_to_many_sources_before_artifact_join() -> None:
    bronze = build_bronze_observations(
        {
            "generation_attempt": [
                {"source_id": "g-1", "run_job_id": "job-1", "status": "failed"},
                {"source_id": "g-2", "run_job_id": "job-1", "status": "accepted"},
            ],
            "provider_attempt": [
                {"source_id": "p-1", "run_job_id": "job-1", "provider_call_count": 2, "token_total": 10},
            ],
            "review_action": [{"source_id": "r-1", "run_job_id": "job-1", "status": "resolved"}],
            "artifact": [{"source_id": "a-1", "run_job_id": "job-1", "version_id": "v-1", "status": "accepted"}],
        },
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="2026-10-05T00:00:00Z",
    )
    gold = build_gold_cv_effort(build_silver_facts(bronze))[0]

    assert gold["accepted_artifact_count"] == 1
    assert gold["generation_attempt_count"] == 2
    assert gold["failed_generation_attempt_count"] == 1
    assert gold["provider_call_count"] == 2
    assert gold["review_action_count"] == 1


def test_gold_effort_does_not_turn_zero_accepted_into_zero_cost() -> None:
    bronze = build_bronze_observations(
        {"generation_attempt": [{"source_id": "g-1", "run_job_id": "job-1", "status": "failed"}]},
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="2026-10-05T00:00:00Z",
    )
    gold = build_gold_cv_effort(build_silver_facts(bronze))[0]
    assert gold["accepted_artifact_count"] == 0
    assert gold["per_accepted_artifact"] is None
    assert gold["unavailable_reason"] == "accepted_artifact_count_zero"


def test_gold_effort_uses_canonical_artifact_id_for_accepted_denominator() -> None:
    bronze = build_bronze_observations(
        {
            "provider_attempt": [
                {"source_id": "p-1", "run_job_id": "job-1", "provider_call_count": 2, "token_total": 100},
            ],
            "accepted_artifact": [
                {"source_id": "a-1", "run_job_id": "job-1", "artifact_id": "cv-1", "status": "accepted"},
            ],
        },
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="2026-10-05T00:00:00Z",
    )
    gold = build_gold_cv_effort(build_silver_facts(bronze))[0]

    assert gold["accepted_artifact_count"] == 1
    assert gold["per_accepted_artifact"] == {"provider_call_count": 2.0, "token_total": 100.0}
    assert gold["unavailable_reason"] is None


def test_gold_effort_excludes_unidentified_accepted_artifacts_from_denominator() -> None:
    bronze = build_bronze_observations(
        {
            "provider_attempt": [
                {"source_id": "p-1", "run_job_id": "job-1", "provider_call_count": 2, "token_total": 100},
            ],
            "accepted_artifact": [
                {"source_id": "a-missing", "run_job_id": "job-1", "status": "accepted"},
                {"source_id": "a-valid", "run_job_id": "job-1", "artifact_id": "cv-1", "status": "accepted"},
            ],
        },
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="2026-10-05T00:00:00Z",
    )
    gold = build_gold_cv_effort(build_silver_facts(bronze))[0]

    assert gold["accepted_artifact_count"] == 1
    assert gold["per_accepted_artifact"] == {"provider_call_count": 2.0, "token_total": 100.0}


def test_gold_effort_marks_missing_artifact_identity_unavailable() -> None:
    bronze = build_bronze_observations(
        {
            "provider_attempt": [
                {"source_id": "p-1", "run_job_id": "job-1", "provider_call_count": 2, "token_total": 100},
            ],
            "accepted_artifact": [
                {"source_id": "a-missing", "run_job_id": "job-1", "status": "accepted"},
            ],
        },
        source_commit="head",
        declared_input_fingerprint="inputs",
        ingested_at="2026-10-05T00:00:00Z",
    )
    gold = build_gold_cv_effort(build_silver_facts(bronze))[0]

    assert gold["accepted_artifact_count"] == 0
    assert gold["per_accepted_artifact"] is None
    assert gold["unavailable_reason"] == "accepted_artifact_count_zero"


def test_gold_acceptance_state_preserves_current_and_historical() -> None:
    rows = build_gold_acceptance_state(
        {"claim_priority_map": {"claim": ["p1"]}, "records": [
            {"evidence_id": "old", "claim": "claim", "status": "historical", "cohort_id": "c1", "cohort_type": "replay"},
            {"evidence_id": "new", "claim": "claim", "status": "current", "cohort_id": "c2", "cohort_type": "fixture"},
        ]},
        {"implementation": {"p1": "accepted"}, "acceptance": {"p1": "accepted"}},
    )
    assert [row["evidence_id"] for row in rows] == ["new", "old"]
    assert rows[0]["historical"] is False
    assert rows[1]["historical"] is True


def test_material_gold_digest_ignores_ingestion_clock() -> None:
    first = {"metric": "gold", "value": 1, "ingested_at": "one"}
    second = {"metric": "gold", "value": 1, "ingested_at": "two"}
    assert material_gold_digest(first) == material_gold_digest(second)
