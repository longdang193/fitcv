"""
@meta
type: test
scope: unit
domain: runtime_routing
covers:
  - cv generation runtime provenance resolution
excludes:
  - live provider calls
tags:
  - fast
  - ci-safe
"""

from __future__ import annotations

from unittest.mock import patch

from fitcv.runtime_routing import build_langgraph_env_overrides, build_runtime_routing_snapshot, langgraph_override_drift_fields, resolve_cv_generation_routing_snapshot, resolve_cv_generation_runtime_provenance
from fitcv.runtime_routing import resolve_langgraph_openai_compatible_api_key, resolve_openai_compatible_api_key, validate_cv_generation_routing_ready


def test_resolve_openai_compatible_api_key_prefers_fitcv_llm_key() -> None:
    with patch.dict(
        "os.environ",
        {
            "FITCV_LLM_API_KEY": "llm-key",
            "OPENAI_API_KEY": "openai-key",
            "OPENAI_COMPATIBLE_API_KEY": "compat-key",
        },
        clear=False,
    ):
        assert resolve_openai_compatible_api_key() == "llm-key"


def test_resolve_langgraph_openai_compatible_api_key_prefers_langgraph_key() -> None:
    with patch.dict(
        "os.environ",
        {
            "FITCV_LANGGRAPH_OPENAI_API_KEY": "langgraph-key",
            "OPENAI_API_KEY": "openai-key",
            "OPENAI_COMPATIBLE_API_KEY": "compat-key",
        },
        clear=False,
    ):
        assert resolve_langgraph_openai_compatible_api_key() == "langgraph-key"


def test_build_langgraph_env_overrides_uses_cv_generation_route_consistently() -> None:
    def _route(part: str, model_fallback: str | None = None) -> dict[str, str]:
        del model_fallback
        if part == "enrich_extraction":
            return {
                "provider": "vertexai_gemini",
                "model": "cx/gpt-5.4-mini",
                "base_url": "",
                "wire_api": "",
            }
        if part == "cv_generation_structured_write":
            return {
                "provider": "openai_compatible",
                "model": "cx/gpt-5.2",
                "base_url": "http://localhost:1234/v1",
                "wire_api": "responses",
            }
        raise AssertionError(f"unexpected routing part: {part}")

    with patch("fitcv.runtime_routing.resolve_model_routing_part", side_effect=_route):
        overrides = build_langgraph_env_overrides()

    assert overrides == {
        "FITCV_LANGGRAPH_PROVIDER": "openai_compatible",
        "FITCV_LANGGRAPH_OPENAI_BASE_URL": "http://localhost:1234/v1",
        "FITCV_LANGGRAPH_WIRE_API": "responses",
        "FITCV_LANGGRAPH_MODEL": "cx/gpt-5.2",
    }

def test_build_runtime_routing_snapshot_normalizes_and_marks_api_key_presence() -> None:
    snapshot = build_runtime_routing_snapshot(
        provider="OpenAI_Compatible",
        model=" cx/gpt-5.2 ",
        base_url=" http://localhost:1234/v1 ",
        wire_api=" Responses ",
        api_key="secret",
        default_provider="fitcv_builtin",
        default_model="fallback-model",
        default_wire_api="responses",
    )
    assert snapshot == {
        "provider": "openai_compatible",
        "model": "cx/gpt-5.2",
        "base_url": "http://localhost:1234/v1",
        "wire_api": "responses",
        "api_key_available": True,
    }

def test_resolve_cv_generation_routing_snapshot_openai_compatible() -> None:
    with patch(
        "fitcv.runtime_routing.resolve_model_routing_part",
        return_value={
            "provider": "openai_compatible",
            "model": "cx/gpt-5.2",
            "base_url": "http://localhost:1234/v1",
            "wire_api": "responses",
        },
    ), patch("fitcv.runtime_routing.resolve_openai_compatible_api_key", return_value="test-key"):
        snapshot = resolve_cv_generation_routing_snapshot({}, default_model="fallback-model")
    assert snapshot["runtime_path"] == "fitcv_cv_generation_openai_compatible"
    assert snapshot["provider"] == "openai_compatible"
    assert snapshot["model"] == "cx/gpt-5.2"
    assert snapshot["base_url"] == "http://localhost:1234/v1"
    assert snapshot["wire_api"] == "responses"
    assert snapshot["api_key_available"] is True

def test_resolve_cv_generation_runtime_provenance_openai_compatible() -> None:
    with patch(
        "fitcv.runtime_routing.resolve_model_routing_part",
        return_value={
            "provider": "openai_compatible",
            "model": "cx/gpt-5.2",
            "base_url": "http://localhost:1234/v1",
            "wire_api": "responses",
        },
    ):
        provenance = resolve_cv_generation_runtime_provenance({}, default_model="fallback-model")
    assert provenance["runtime_path"] == "fitcv_cv_generation_openai_compatible"
    assert provenance["provider"] == "openai_compatible"
    assert provenance["model"] == "cx/gpt-5.2"


def test_resolve_cv_generation_runtime_provenance_builtin_provider() -> None:
    with patch(
        "fitcv.runtime_routing.resolve_model_routing_part",
        return_value={
            "provider": "vertexai_gemini",
            "model": "cx/gpt-5.4-mini",
            "base_url": "",
            "wire_api": "",
        },
    ):
        provenance = resolve_cv_generation_runtime_provenance({}, default_model="fallback-model")
    assert provenance["runtime_path"] == "fitcv_cv_generation_builtin"
    assert provenance["provider"] == "vertexai_gemini"
    assert provenance["model"] == "cx/gpt-5.4-mini"


def test_resolve_cv_generation_runtime_provenance_falls_back_on_routing_error() -> None:
    with patch(
        "fitcv.runtime_routing.resolve_model_routing_part",
        side_effect=RuntimeError("routing unavailable"),
    ):
        provenance = resolve_cv_generation_runtime_provenance({}, default_model="fallback-model")
    assert provenance == {
        "runtime_path": "fitcv_cv_generation_builtin",
        "provider": "fitcv_builtin",
        "model": "fallback-model",
    }


def test_validate_cv_generation_routing_ready_openai_compatible_requires_api_key() -> None:
    with patch(
        "fitcv.runtime_routing.resolve_model_routing_part",
        return_value={
            "provider": "openai_compatible",
            "model": "cx/gpt-5.2",
            "base_url": "http://localhost:1234/v1",
            "wire_api": "responses",
        },
    ), patch("fitcv.runtime_routing.resolve_openai_compatible_api_key", return_value=""):
        try:
            validate_cv_generation_routing_ready({})
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert "API key" in str(exc)


def test_validate_cv_generation_routing_ready_builtin_provider_no_api_key_needed() -> None:
    with patch(
        "fitcv.runtime_routing.resolve_model_routing_part",
        return_value={
            "provider": "vertexai_gemini",
            "model": "cx/gpt-5.4-mini",
            "base_url": "",
            "wire_api": "",
        },
    ):
        validate_cv_generation_routing_ready({})

def test_langgraph_override_drift_fields_reports_only_conflicting_override_fields() -> None:
    with patch(
        "fitcv.runtime_routing.resolve_model_routing_part",
        return_value={
            "provider": "openai_compatible",
            "model": "cx/gpt-5.2",
            "base_url": "http://router.local/v1",
            "wire_api": "responses",
        },
    ), patch.dict(
        "os.environ",
        {
            "FITCV_LANGGRAPH_PROVIDER": "9router",
            "FITCV_LANGGRAPH_MODEL": "cx/gpt-5.2",
            "FITCV_LANGGRAPH_OPENAI_BASE_URL": "http://override.local/v1",
            "FITCV_LANGGRAPH_WIRE_API": "responses",
        },
        clear=False,
    ):
        assert langgraph_override_drift_fields() == ["provider", "base_url"]

def test_langgraph_override_drift_fields_ignores_empty_override_env() -> None:
    with patch(
        "fitcv.runtime_routing.resolve_model_routing_part",
        return_value={
            "provider": "openai_compatible",
            "model": "cx/gpt-5.2",
            "base_url": "http://router.local/v1",
            "wire_api": "responses",
        },
    ), patch.dict(
        "os.environ",
        {
            "FITCV_LANGGRAPH_PROVIDER": "",
            "FITCV_LANGGRAPH_MODEL": "",
            "FITCV_LANGGRAPH_OPENAI_BASE_URL": "",
            "FITCV_LANGGRAPH_WIRE_API": "",
        },
        clear=False,
    ):
        assert langgraph_override_drift_fields() == []
