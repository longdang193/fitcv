from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "evaluate_requirement_support_live.py"


def _module() -> Any:
    spec = importlib.util.spec_from_file_location("evaluate_requirement_support_live", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _payload() -> dict[str, Any]:
    shared = {
        "fixture_sha256": "fixture",
        "scenario_id": "scenario",
        "model": "model",
        "template": "template-v1",
        "generation_settings": {"temperature": 0},
        "output_budget": 1000,
    }
    return {
        "offline_gate": {"passed": True, "fixture_sha256": "fixture"},
        "provider": {
            "model": "model",
            "template": "template-v1",
            "generation_settings": {"temperature": 0},
            "output_budget": 1000,
            "credential_env": "FITCV_TEST_PROVIDER_KEY",
        },
        "cost_ceiling_usd": 1,
        "pairs": [{"pair_id": "pair-1", "baseline": shared, "fitcv": dict(shared)}],
    }


def test_dry_run_validates_pairs_without_provider_calls() -> None:
    module = _module()

    result = module.evaluate(_payload())

    assert result["mode"] == "dry-run"
    assert result["provider_calls"] is False
    assert result["pair_count"] == 1


def test_rag_impact_fixture_has_stable_profile_and_non_overlapping_splits() -> None:
    module = _module()
    fixture = json.loads(
        (REPO_ROOT / "tests" / "fixtures" / "rag_impact_benchmark.json").read_text(
            encoding="utf-8"
        )
    )

    assert module.validate_benchmark_fixture(fixture) == []


def test_dry_run_rejects_mismatched_model() -> None:
    module = _module()
    payload = _payload()
    payload["pairs"][0]["fitcv"]["model"] = "other-model"

    with pytest.raises(ValueError, match="model mismatch"):
        module.evaluate(payload)


def test_live_mode_fails_closed_without_credentials() -> None:
    module = _module()

    with pytest.raises(RuntimeError, match="credentials"):
        module.evaluate(_payload(), dry_run=False, environ={})


def test_provider_usage_extracts_optional_metadata() -> None:
    module = _module()

    assert module.extract_provider_usage({"usage": {"total_tokens": 12}})["total_tokens"] == 12
    assert module.extract_provider_usage({"usage": {"input_tokens": 7, "output_tokens": 5}}) == {
        "prompt_tokens": 7,
        "completion_tokens": 5,
        "total_tokens": None,
        "cost": None,
        "available": True,
    }
    assert module.extract_provider_usage({})["available"] is False


def test_live_mode_reports_paired_variant_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _module()
    payload = _payload()
    payload["pairs"][0]["baseline"].update(
        {"prompt": "baseline", "review": {"requirements": [{"requirement_id": "r", "terms": ["SQL"], "approved_evidence_ids": ["ev-1"]}]}}
    )
    payload["pairs"][0]["fitcv"].update(
        {"prompt": "fitcv", "review": {"requirements": [{"requirement_id": "r", "terms": ["SQL"], "approved_evidence_ids": ["ev-1"]}]}}
    )

    def fake_call(
        prompt: str,
        provider: dict[str, Any],
        environ: dict[str, str],
        *,
        output_budget: int | None = None,
    ) -> dict[str, Any]:
        assert output_budget == 1000
        return {
            "status": "succeeded",
            "text": "SQL",
            "output_sha256": "hash",
            "output_chars": 3,
            "latency_ms": 1,
            "attempt_count": 1,
            "response_id_present": True,
            "usage": {"available": True, "total_tokens": 10, "cost": 0.1},
        }

    monkeypatch.setattr(module, "_call_provider", fake_call)
    result = module.evaluate(
        payload,
        dry_run=False,
        environ={"FITCV_TEST_PROVIDER_KEY": "configured"},
    )

    assert result["provider_calls"] == 2
    assert result["metrics"]["by_variant"]["baseline"]["final_acceptance"] == 1.0
    assert result["metrics"]["fitcv_minus_baseline"]["final_acceptance"] == 0.0


def test_live_mode_fails_closed_when_provider_cost_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    payload = _payload()
    for variant_name in ("baseline", "fitcv"):
        payload["pairs"][0][variant_name].update(
            {"prompt": variant_name, "review": {"requirements": []}}
        )

    def fake_call(
        prompt: str,
        provider: dict[str, Any],
        environ: dict[str, str],
        *,
        output_budget: int | None = None,
    ) -> dict[str, Any]:
        return {
            "status": "succeeded",
            "text": "SQL",
            "output_sha256": "hash",
            "output_chars": 3,
            "latency_ms": 1,
            "attempt_count": 1,
            "response_id_present": True,
            "usage": {"available": True, "total_tokens": 10, "cost": None},
        }

    monkeypatch.setattr(module, "_call_provider", fake_call)

    result = module.evaluate(
        payload,
        dry_run=False,
        environ={"FITCV_TEST_PROVIDER_KEY": "configured"},
    )
    assert result["metrics"]["provider_usage"]["cost_available"] is False


def test_live_metrics_keep_failed_calls_in_attempted_denominator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    payload = _payload()
    for variant_name in ("baseline", "fitcv"):
        payload["pairs"][0][variant_name].update(
            {
                "prompt": variant_name,
                "review": {
                    "requirements": [
                        {"requirement_id": "r", "terms": ["SQL"], "approved_evidence_ids": ["ev-1"]}
                    ]
                },
            }
        )

    def fake_call(prompt: str, provider: dict[str, Any], environ: dict[str, str], *, output_budget: int | None = None) -> dict[str, Any]:
        if prompt == "fitcv":
            return {"status": "failed", "failure": {"code": "timeout"}}
        return {
            "status": "succeeded",
            "text": "SQL",
            "usage": {"available": True, "prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14, "cost": None},
        }

    monkeypatch.setattr(module, "_call_provider", fake_call)
    result = module.evaluate(payload, dry_run=False, environ={"FITCV_TEST_PROVIDER_KEY": "configured"})

    fitcv = result["metrics"]["by_variant"]["fitcv"]
    assert fitcv["attempted_calls"] == 1
    assert fitcv["failed_calls"] == 1
    assert fitcv["accepted_cv_rate_over_attempts"] == 0.0


def test_review_output_does_not_count_negated_requirement_term() -> None:
    module = _module()

    result = module._review_output(
        "No SQL experience.",
        {
            "requirements": [
                {"requirement_id": "r", "terms": ["SQL"], "approved_evidence_ids": ["ev-1"]}
            ]
        },
    )

    assert result["covered_requirements"] == []
    assert result["requirement_coverage"] == 0.0
