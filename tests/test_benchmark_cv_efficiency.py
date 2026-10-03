from scripts.benchmark_cv_efficiency import summarize


def test_summarize_keeps_unknown_timings_unknown() -> None:
    result = summarize({"records": [{"status": "accepted", "provider_call_count": 2}]})
    assert result["metrics"]["provider_calls"] == 2
    assert result["metrics"]["latency_ms"]["p50"] is None


def test_summarize_rejects_non_comparable_cohort_for_promotion() -> None:
    result = summarize(
        {
            "comparability": {"comparable_to_historical_169_job_workload": False},
            "records": [{"status": "accepted", "attempt_count": 1, "page_count": 1}],
        }
    )
    assert result["metrics"]["first_pass_acceptance_rate"] == 1.0
    assert result["promotion_allowed"] is False
