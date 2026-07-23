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

import pytest

from fitcv.runtime_routing import build_runtime_routing_snapshot, resolve_cv_generation_routing, resolve_cv_generation_routing_snapshot, resolve_cv_generation_runtime_provenance
from fitcv.runtime_routing import resolve_llm_api_key, resolve_llm_routing, resolve_openai_compatible_api_key, validate_cv_generation_routing_ready, validate_llm_routing_ready


def test_resolve_openai_compatible_api_key_uses_fitcv_llm_key_only() -> None:
    with patch.dict(
        "os.environ",
        {
            "FITCV_LLM_API_KEY": "llm-key",
            "OPENAI_API_KEY": "openai-key",
            "OPENAI_COMPATIBLE_API_KEY": "compat-key",
            "FITCV_LANGGRAPH_OPENAI_API_KEY": "langgraph-key",
        },
        clear=False,
    ):
        assert resolve_openai_compatible_api_key() == "llm-key"


def test_resolve_openai_compatible_api_key_ignores_deprecated_aliases() -> None:
    with patch.dict(
        "os.environ",
        {
            "FITCV_LLM_API_KEY": "",
            "OPENAI_API_KEY": "openai-key",
            "OPENAI_COMPATIBLE_API_KEY": "compat-key",
            "FITCV_LANGGRAPH_OPENAI_API_KEY": "langgraph-key",
        },
        clear=False,
    ):
        assert resolve_openai_compatible_api_key() == ""


def test_local_mode_resolves_provider_credential_not_env() -> None:
    with patch.dict(
        "os.environ",
        {"FITCV_LOCAL_MODE": "1", "FITCV_LLM_API_KEY": "env-secret"},
        clear=False,
    ), patch("fitcv_cp.local_credentials.get_credential", return_value="stored-secret"):
        assert resolve_openai_compatible_api_key("openai") == "stored-secret"

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
            "timeout_seconds": "300",
            "auth_mode": "required",
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
            "timeout_seconds": "300",
            "auth_mode": "required",
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
            "wire_api": "builtin",
            "timeout_seconds": "300",
            "auth_mode": "none",
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
            "timeout_seconds": "300",
            "auth_mode": "required",
        },
    ), patch("fitcv.runtime_routing.resolve_openai_compatible_api_key", return_value=""):
        try:
            validate_cv_generation_routing_ready({})
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert "FITCV_LLM_API_KEY" in str(exc)


def test_local_cv_readiness_names_credential_store() -> None:
    with patch.dict("os.environ", {"FITCV_LOCAL_MODE": "1"}, clear=False), patch(
        "fitcv.runtime_routing.build_packaged_llm_configuration_snapshot",
        return_value={
            "revision": 1,
            "tasks": {
                "cv_generation_structured_write": {
                    "provider": "openai_compatible",
                    "model": "cx/gpt-5.2",
                    "base_url": "http://localhost:1234/v1",
                    "wire_api": "responses",
                    "timeout_seconds": 300,
                    "temperature": 0.2,
                }
            },
        },
    ), patch("fitcv.runtime_routing.resolve_openai_compatible_api_key", return_value=""):
        with pytest.raises(RuntimeError, match="Windows credential"):
            validate_cv_generation_routing_ready({})


def test_validate_cv_generation_routing_ready_builtin_provider_no_api_key_needed() -> None:
    with patch(
        "fitcv.runtime_routing.resolve_model_routing_part",
        return_value={
            "provider": "fitcv_builtin",
            "model": "cx/gpt-5.4-mini",
            "base_url": "",
            "wire_api": "builtin",
            "timeout_seconds": "300",
            "auth_mode": "none",
        },
    ):
        validate_cv_generation_routing_ready({})

def test_resolve_llm_routing_matches_cv_wrapper() -> None:
    route_payload = {
        "provider": "OPENAI_COMPATIBLE",
        "model": "cx/test-model",
        "base_url": "https://provider.example/v1",
        "wire_api": "CHAT_COMPLETIONS",
        "timeout_seconds": "42",
        "auth_mode": "required",
    }
    with patch("fitcv.runtime_routing.resolve_model_routing_part", return_value=route_payload):
        generic = resolve_llm_routing("cv_generation_structured_write", model_fallback="fallback")
        cv_route = resolve_cv_generation_routing({})

    assert generic.provider == cv_route.provider == "openai_compatible"
    assert generic.base_url == cv_route.base_url == "https://provider.example/v1"
    assert generic.wire_api == cv_route.wire_api == "chat_completions"
    assert generic.model == cv_route.model == "cx/test-model"
    assert generic.timeout_seconds == cv_route.timeout_seconds == 42.0

def test_resolve_llm_routing_carries_global_request_start_interval() -> None:
    route_payload = {
        "provider": "openai_compatible",
        "model": "cx/test-model",
        "base_url": "https://provider.example/v1",
        "wire_api": "responses",
        "timeout_seconds": "42",
        "auth_mode": "required",
    }
    with patch("fitcv.runtime_routing.resolve_model_routing_part", return_value=route_payload):
        route = resolve_llm_routing(
            "ranking_ai_score",
            runtime_config={"llm_runtime": {"request_start_interval_secs": 1.25}},
        )

    assert route.request_start_interval_secs == pytest.approx(1.25)


def test_generic_readiness_uses_env_only_openai_credential() -> None:
    with patch(
        "fitcv.runtime_routing.resolve_model_routing_part",
        return_value={
            "provider": "openai_compatible",
            "model": "cx/test-model",
            "base_url": "https://provider.example/v1",
            "wire_api": "responses",
            "timeout_seconds": "300",
            "auth_mode": "required",
        },
    ):
        route = resolve_llm_routing("ranking_ai_score")
    with patch("fitcv.runtime_routing.resolve_openai_compatible_api_key", return_value="secret"):
        assert resolve_llm_api_key(route) == "secret"
        validate_llm_routing_ready(route)


def test_validate_llm_routing_ready_requires_control_plane_model() -> None:
    from fitcv.runtime_routing import LlmRouting

    route = LlmRouting(
        provider="openai_compatible",
        base_url="https://provider.example/v1",
        wire_api="responses",
        model="",
        timeout_seconds=12.0,
    )

    with patch("fitcv.runtime_routing.resolve_openai_compatible_api_key", return_value="secret"):
        try:
            validate_llm_routing_ready(route)
        except RuntimeError as exc:
            assert "requires model" in str(exc)
        else:
            raise AssertionError("missing routed model must fail")


def test_resolve_llm_routing_rejects_missing_canonical_transport_fields() -> None:
    with patch(
        "fitcv.runtime_routing.resolve_model_routing_part",
        return_value={
            "provider": "openai_compatible",
            "model": "cx/test-model",
            "base_url": "https://provider.example/v1",
            "wire_api": "",
            "timeout_seconds": "",
            "auth_mode": "required",
        },
    ):
        with pytest.raises(ValueError, match="wire_api is required"):
            resolve_llm_routing("ranking_ai_score")
