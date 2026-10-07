from scripts.compare_fitcv_optimization import compare_reports


def _report(*, provider_calls: int, tokens: int, accepted: int = 10) -> dict:
    return {
        "input_manifest": {
            "declared_input_fingerprint": "same-input",
            "fixture_sha256": "same-fixture",
            "repeat_count": 10,
        },
        "aggregate": {
            "provider_call_count": provider_calls,
            "token_total": tokens,
            "regeneration_count": 2,
        },
        "timing": {"stage_latency_ms": {"provider_generation": {"p95_ms": 100.0}}},
        "accepted_cv": {"count": accepted},
        "coverage": {"page_fit_success": {"complete": True}},
        "optimization_scorecard": {"human_actions": {"count": 0}},
    }


def test_compare_promotes_only_with_same_workload_and_quality_preserved() -> None:
    result = compare_reports(_report(provider_calls=10, tokens=1000), _report(provider_calls=8, tokens=800), min_relative_improvement=0.1)

    assert result["decision"] == "promote"
    assert result["production_defaults_changed"] is False


def test_compare_holds_on_workload_mismatch_or_quality_regression() -> None:
    baseline = _report(provider_calls=10, tokens=1000)
    optimized = _report(provider_calls=8, tokens=800, accepted=9)
    optimized["input_manifest"]["fixture_sha256"] = "different-fixture"

    result = compare_reports(baseline, optimized, min_relative_improvement=0.1)

    assert result["decision"] == "hold"
    assert result["workload_match"] is False
    assert result["quality"]["quality_regression"] is True
