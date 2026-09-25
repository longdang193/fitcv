from __future__ import annotations

import importlib.util
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
        {"prompt": "baseline", "review": {"requirements": [{"requirement_id": "r", "terms": ["SQL"]}]}}
    )
    payload["pairs"][0]["fitcv"].update(
        {"prompt": "fitcv", "review": {"requirements": [{"requirement_id": "r", "terms": ["SQL"]}]}}
    )

    def fake_call(prompt: str, provider: dict[str, Any], environ: dict[str, str]) -> dict[str, Any]:
        return {
            "status": "succeeded",
            "text": "SQL",
            "output_sha256": "hash",
            "output_chars": 3,
            "latency_ms": 1,
            "attempt_count": 1,
            "response_id_present": True,
            "usage": {"available": True, "total_tokens": 10},
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
