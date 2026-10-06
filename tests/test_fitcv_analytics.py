from scripts.fitcv_analytics import (
    build_bronze_observations,
    build_gold_acceptance_state,
    build_gold_candidate_gap,
    build_gold_cv_effort,
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
