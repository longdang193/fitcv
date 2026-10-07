from scripts.compare_fitcv_optimization import compare_reports


def _report(*, provider_calls: int, tokens: int, accepted: int = 10) -> dict:
    return {
        "input_manifest": {
            "declared_input_fingerprint": "same-input",
            "fixture_sha256": "same-fixture",
            "repeat_count": 10,
            "declared_model": "fixture-model",
            "resolved_models": ["fixture-model"],
            "runtime": "fitcv-runtime",
        },
        "aggregate": {
            "provider_call_count": provider_calls,
            "token_total": tokens,
            "regeneration_count": 2,
        },
        "timing": {"stage_latency_ms": {"provider_generation": {"p95_ms": 100.0}}},
        "accepted_cv": {"count": accepted},
        "coverage": {
            "grounding": {"complete": True, "rate": 1.0},
            "page_fit_success": {"complete": True, "rate": 1.0},
        },
        "optimization_scorecard": {"human_actions": {"count": 0}},
    }


def test_compare_promotes_only_with_same_workload_and_quality_preserved() -> None:
    result = compare_reports(_report(provider_calls=10, tokens=1000), _report(provider_calls=8, tokens=800), min_relative_improvement=0.1)

    assert result["decision"] == "promote"
    assert result["production_defaults_changed"] is False



def test_compare_uses_total_workload_when_aggregate_excludes_failed_work() -> None:
    baseline = _report(provider_calls=10, tokens=1000)
    optimized = _report(provider_calls=8, tokens=800)
    baseline["aggregate"].update({"provider_call_count": 0, "token_total": 0})
    optimized["aggregate"].update({"provider_call_count": 0, "token_total": 0})
    baseline["workload"] = {"provider_call_count": 30, "token_total": 143904, "regeneration_count": 2}
    optimized["workload"] = {"provider_call_count": 30, "token_total": 143904, "regeneration_count": 1}

    result = compare_reports(baseline, optimized, min_relative_improvement=0.1)

    assert result["decision"] == "promote"
    assert result["metrics"]["provider_calls"]["baseline"] == 30
    assert result["metrics"]["token_total"]["optimized"] == 143904


def test_compare_holds_on_workload_mismatch_or_quality_regression() -> None:
    baseline = _report(provider_calls=10, tokens=1000)
    optimized = _report(provider_calls=8, tokens=800, accepted=9)
    optimized["input_manifest"]["fixture_sha256"] = "different-fixture"

    result = compare_reports(baseline, optimized, min_relative_improvement=0.1)

    assert result["decision"] == "hold"
    assert result["workload_match"] is False
    assert result["quality"]["quality_regression"] is True


def test_compare_holds_when_identity_or_quality_evidence_is_missing() -> None:
    baseline = _report(provider_calls=10, tokens=1000)
    optimized = _report(provider_calls=8, tokens=800)
    del optimized["input_manifest"]
    assert compare_reports(baseline, optimized, min_relative_improvement=0.1)["decision"] == "hold"

    optimized = _report(provider_calls=8, tokens=800)
    del optimized["coverage"]["grounding"]
    result = compare_reports(baseline, optimized, min_relative_improvement=0.1)
    assert result["decision"] == "hold"
    assert result["quality"]["quality_evidence_missing"] is True


def test_compare_holds_on_grounding_or_one_page_regression() -> None:
    baseline = _report(provider_calls=10, tokens=1000)
    optimized = _report(provider_calls=8, tokens=800)
    optimized["coverage"]["grounding"]["rate"] = 0.0
    optimized["coverage"]["page_fit_success"]["rate"] = 0.0

    result = compare_reports(baseline, optimized, min_relative_improvement=0.1)

    assert result["decision"] == "hold"
    assert result["quality"]["grounding_regression"] is True
    assert result["quality"]["one_page_regression"] is True


def test_compare_holds_when_provider_cost_increases() -> None:
    baseline = _report(provider_calls=10, tokens=1000)
    optimized = _report(provider_calls=11, tokens=1100)

    result = compare_reports(baseline, optimized, min_relative_improvement=-0.1)

    assert result["decision"] == "hold"
    assert result["quality"]["cost_regression"] is True


def test_compare_holds_when_accepted_or_cost_evidence_is_missing() -> None:
    baseline = _report(provider_calls=10, tokens=1000)
    optimized = _report(provider_calls=8, tokens=800)

    del optimized["accepted_cv"]["count"]
    result = compare_reports(baseline, optimized, min_relative_improvement=0.1)
    assert result["decision"] == "hold"
    assert result["quality"]["accepted_evidence_missing"] is True

    optimized = _report(provider_calls=8, tokens=800)
    del optimized["aggregate"]["token_total"]
    result = compare_reports(baseline, optimized, min_relative_improvement=0.1)
    assert result["decision"] == "hold"
    assert result["quality"]["cost_evidence_missing"] is True


def test_compare_holds_on_runtime_identity_mismatch() -> None:
    baseline = _report(provider_calls=10, tokens=1000)
    optimized = _report(provider_calls=8, tokens=800)
    baseline["input_manifest"].update(
        {"declared_model": "model-a", "resolved_models": ["model-a"], "runtime": "runtime-a"}
    )
    optimized["input_manifest"].update(
        {"declared_model": "model-b", "resolved_models": ["model-b"], "runtime": "runtime-a"}
    )

    result = compare_reports(baseline, optimized, min_relative_improvement=0.1)

    assert result["decision"] == "hold"
    assert result["workload_match"] is False
    assert result["workload_mismatch_reason"] == "workload_mismatch:declared_model"
