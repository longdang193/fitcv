from scripts.fitcv_analytics import (
    build_bronze_observations,
    build_gold_acceptance_state,
    build_gold_cv_effort,
    build_silver_facts,
    material_gold_digest,
)


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


def test_gold_acceptance_state_preserves_current_and_historical() -> None:
    rows = build_gold_acceptance_state(
        {"records": [
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
