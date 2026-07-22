"""
@meta
type: test
scope: unit
domain: fitcv_local_setup
covers:
  - provider schema and API-root validation
  - non-secret routing overlay and readiness
excludes:
  - live provider network calls
tags:
  - fast
  - ci-safe
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from fitcv_cp.local_setup import (
    ProviderSetup,
    build_routing_overlay,
    discover_models,
    normalize_api_root,
    readiness,
    test_provider as run_provider_test,
    write_routing_overlay,
)


def test_local_provider_contracts_use_shared_ssot_constants() -> None:
    from fitcv.config import SUPPORTED_PROVIDER_IDS
    from fitcv.llm_runtime import SUPPORTED_PROVIDER_IDS as ADAPTER_PROVIDER_IDS
    from fitcv_cp.local_routes import PROVIDER_DRAFT_FIELDS
    from fitcv_cp.local_setup import PROVIDER_IDS, TASK_PARTS

    assert ADAPTER_PROVIDER_IDS is SUPPORTED_PROVIDER_IDS
    assert PROVIDER_IDS is SUPPORTED_PROVIDER_IDS
    assert PROVIDER_DRAFT_FIELDS[-len(TASK_PARTS) :] == TASK_PARTS


def _setup(auth_mode: str = "required") -> ProviderSetup:
    return ProviderSetup(
        provider_id="openai_compatible",
        provider_type="openai_compatible",
        display_name="Local provider",
        base_url="http://127.0.0.1:1234/v1/",
        auth_mode=auth_mode,  # type: ignore[arg-type]
        wire_api="responses",
        timeout_seconds=30,
        default_model="test-model",
        task_models={},
    )


def test_normalize_api_root_rejects_operation_endpoint() -> None:
    with pytest.raises(ValueError, match="API root"):
        normalize_api_root("https://example.test/v1/chat/completions")


def test_overlay_is_narrow_and_secret_free(tmp_path: Path) -> None:
    path = tmp_path / "overlay.yaml"
    payload = build_routing_overlay(_setup())
    write_routing_overlay(path, payload)

    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert set(loaded) == {"version", "providers", "model_routing"}
    assert "secret" not in path.read_text(encoding="utf-8").lower()
    assert loaded["providers"]["openai_compatible"]["base_url"] == "http://127.0.0.1:1234/v1"


@pytest.mark.parametrize(
    ("auth_mode", "credential_configured", "expected"),
    [("required", False, False), ("required", True, True), ("optional", False, True), ("none", False, True)],
)
def test_readiness_uses_same_auth_mode_contract(
    auth_mode: str, credential_configured: bool, expected: bool
) -> None:
    result = readiness(
        _setup(auth_mode),
        credential_configured=credential_configured,
        provider_test_ok=True,
    )
    assert result["ready"] is expected


def test_discover_models_uses_api_root_and_returns_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    response = type(
        "Response",
        (),
        {"raise_for_status": lambda self: None, "json": lambda self: {"data": [{"id": "b"}, {"id": "a"}]}},
    )()
    client = type(
        "Client",
        (),
        {
            "__enter__": lambda self: self,
            "__exit__": lambda self, *_args: None,
            "get": lambda self, url, headers: response,
        },
    )()
    monkeypatch.setattr("httpx.Client", lambda **_kwargs: client)

    assert discover_models(_setup("none")) == ["a", "b"]


def test_provider_test_returns_sanitized_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "fitcv_cp.provider_registry.validate_connection_draft",
        lambda **_kwargs: {
            "ok": False,
            "failure_code": "provider_auth_failed",
            "http_status": 401,
        },
    )

    summary = run_provider_test(_setup(), api_key="secret")

    assert summary == {"ok": False, "failure_code": "provider_auth_failed", "http_status": 401}
