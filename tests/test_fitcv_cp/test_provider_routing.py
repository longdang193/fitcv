"""
@meta
type: test
scope: unit
domain: provider_routing
covers:
  - part-based provider/model routing resolution
excludes:
  - live provider network calls
tags:
  - fast
  - ci-safe
"""

import pytest

from fitcv.config import load_control_plane_config
from fitcv.runtime_routing import resolve_llm_routing
from fitcv_cp.adapters.contracts import resolve_part_routing


def test_resolve_llm_routing_resolves_hydrated_candidate_profile_task(monkeypatch) -> None:
    monkeypatch.setenv("FITCV_LOCAL_MODE", "1")
    snapshot = {
        "revision": 3,
        "tasks": {
            "candidate_profile_base_mapping": {
                "provider": "openai_compatible",
                "base_url": "http://localhost:1234/v1",
                "wire_api": "responses",
                "model": "candidate-model",
                "model_record_id": "model-ref",
                "timeout_seconds": 120,
                "temperature": 0.2,
            }
        },
    }

    with monkeypatch.context() as context:
        context.setattr(
            "fitcv.runtime_routing.build_packaged_llm_configuration_snapshot",
            lambda: snapshot,
        )
        route = resolve_llm_routing("candidate_profile_base_mapping")

    assert route.model == "candidate-model"
    assert route.model_record_id == "model-ref"
    assert route.configuration_revision == 3


def test_resolve_part_routing_reads_provider_and_model_from_control_plane() -> None:
    cfg = load_control_plane_config()

    selection = resolve_part_routing(cfg, "enrich_extraction")

    assert selection.provider == "openai_compatible"
    assert selection.model == cfg["model_routing"]["parts"]["enrich_extraction"]["model"]


def test_resolve_part_routing_rejects_unknown_part() -> None:
    cfg = load_control_plane_config()

    with pytest.raises(ValueError, match="Unsupported model routing part"):
        resolve_part_routing(cfg, "unknown_part")


def test_resolve_part_routing_rejects_provider_missing_from_registry() -> None:
    cfg = {
        "providers": {"openai": {"base_url": "https://api.openai.com/v1"}},
        "model_routing": {
            "parts": {
                "enrich_extraction": {
                    "provider": "openai_compatible",
                    "model": "kimi-k2-instruct",
                }
            }
        },
    }

    with pytest.raises(ValueError, match="Unsupported provider"):
        resolve_part_routing(cfg, "enrich_extraction")
