"""
@meta
type: test
scope: integration
domain: fitcv_local
covers:
  - controller overlay validation and normalization
  - legacy routing overlay migration
  - canonical retry ownership
excludes:
  - live provider calls
  - packaged executable execution
tags:
  - fast
  - ci-safe
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from fitcv.config import normalize_prompt_addendum, validate_local_controller_overlay
from fitcv_cp.local_storage import activate_local_storage
from fitcv_cp.retry_settings import load_retry_settings


def test_controller_overlay_normalizes_prompt_addenda_and_rejects_identity_fields() -> None:
    payload = validate_local_controller_overlay(
        {
            "version": 1,
            "prompts": {
                "additional_instructions": {
                    "enrich_extraction": "  first\r\nsecond  ",
                    "ranking_ai_score": "   ",
                }
            },
        }
    )

    assert payload["prompts"]["additional_instructions"] == {
        "enrich_extraction": "first\nsecond"
    }
    assert normalize_prompt_addendum(" x\r\ny ") == "x\ny"
    with pytest.raises(ValueError, match="unsupported provider fields"):
        validate_local_controller_overlay(
            {
                "version": 1,
                "providers": {
                    "openai_compatible": {"display_name": "duplicate owner"}
                },
            }
        )


def test_activate_local_storage_migrates_legacy_overlay_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    data_root = tmp_path / "data"
    monkeypatch.setenv(
        "FITCV_LOCAL_CONTROLLER_OVERLAY_PATH",
        str(data_root / "config" / "local_controller_overlay.yaml"),
    )
    legacy_path = data_root / "config" / "local_routing_overlay.yaml"
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_text(
        "version: 1\n"
        "providers:\n"
        "  openai_compatible:\n"
        "    base_url: https://example.test/v1\n"
        "model_routing:\n"
        "  parts:\n"
        "    enrich_extraction:\n"
        "      provider: openai_compatible\n"
        "      model: test-model\n",
        encoding="utf-8",
    )

    paths = activate_local_storage(data_root=data_root, bundle_root=Path.cwd())

    assert paths.controller_overlay_path.exists()
    assert not paths.legacy_routing_overlay_path.exists()
    assert paths.migrated_routing_overlay_path.exists()
    assert os.environ["FITCV_LOCAL_CONTROLLER_OVERLAY_PATH"] == str(
        paths.controller_overlay_path
    )
    second = activate_local_storage(data_root=data_root, bundle_root=Path.cwd())
    assert second.controller_overlay_path.read_bytes() == paths.controller_overlay_path.read_bytes()


def test_retry_settings_use_scalar_initial_backoff() -> None:
    settings = load_retry_settings(
        {
            "fitcv_cp": {
                "retry": {
                    "maximum_attempts": 4,
                    "initial_backoff_seconds": 12,
                    "lease_seconds": 240,
                    "reconciler_interval_seconds": 20,
                    "error_detail_limit": 8000,
                }
            }
        }
    )

    assert settings.maximum_attempts == 4
    assert settings.initial_backoff_seconds == 12
    assert settings.lease_seconds == 240
    assert settings.reconciler_interval_seconds == 20
    assert settings.error_detail_limit == 8000

def test_effective_controller_merges_prompt_addenda(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from fitcv.config import (
        get_prompt_addendum,
        get_prompt_addendum_metadata,
        load_control_plane_config,
    )

    overlay_path = tmp_path / "local_controller_overlay.yaml"
    overlay_path.write_text(
        "version: 1\nprompts:\n  additional_instructions:\n"
        "    enrich_extraction: Prefer direct evidence.\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("FITCV_LOCAL_CONTROLLER_OVERLAY_PATH", str(overlay_path))

    effective = load_control_plane_config()

    assert effective["prompts"]["additional_instructions"]["enrich_extraction"] == (
        "Prefer direct evidence."
    )
    assert get_prompt_addendum("enrich_extraction", effective) == "Prefer direct evidence."
    assert get_prompt_addendum("enrich_extraction", {}) == "Prefer direct evidence."
    metadata = get_prompt_addendum_metadata("enrich_extraction", {})
    assert metadata["customized"] is True
    assert metadata["addendum_char_count"] == len("Prefer direct evidence.")

def test_prompt_addendum_metadata_excludes_raw_text() -> None:
    from fitcv.config import get_prompt_addendum_metadata

    raw = "Private operator guidance"
    metadata = get_prompt_addendum_metadata(
        "ranking_ai_score",
        {"prompts": {"additional_instructions": {"ranking_ai_score": raw}}},
    )

    assert metadata["customized"] is True
    assert metadata["addendum_char_count"] == len(raw)
    assert metadata["addendum_sha256"] == __import__("hashlib").sha256(
        raw.encode("utf-8")
    ).hexdigest()
    assert raw not in str(metadata)
