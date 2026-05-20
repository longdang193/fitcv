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

from fitcv.runtime_routing import resolve_cv_generation_runtime_provenance
from fitcv.runtime_routing import validate_cv_generation_routing_ready


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
            "model": "gemini-2.5-flash",
            "base_url": "",
            "wire_api": "",
        },
    ):
        provenance = resolve_cv_generation_runtime_provenance({}, default_model="fallback-model")
    assert provenance["runtime_path"] == "fitcv_cv_generation_builtin"
    assert provenance["provider"] == "vertexai_gemini"
    assert provenance["model"] == "gemini-2.5-flash"


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
            "model": "gemini-2.5-flash",
            "base_url": "",
            "wire_api": "",
        },
    ):
        validate_cv_generation_routing_ready({})
