"""@meta
type: test
scope: unit
domain: run_orchestration
covers:
  - fitcv_cp.retry_settings load_retry_settings
tags:
  - fast
  - ci-safe
"""

from fitcv_cp.retry_settings import load_retry_settings


def test_load_retry_settings_applies_defaults_when_missing() -> None:
    settings = load_retry_settings({})
    assert settings.enabled is False
    assert settings.max_attempts == 1
    assert settings.backoff_seconds == (1, 2, 4, 8)


def test_load_retry_settings_parses_values_from_control_plane_cfg() -> None:
    settings = load_retry_settings(
        {
            "fitcv_cp": {
                "retry": {
                    "enabled": True,
                    "max_attempts": 3,
                    "backoff_seconds": [1, 5],
                    "lease_seconds": 120,
                    "reconciler_interval_seconds": 10,
                    "error_details_max_chars": 4096,
                }
            }
        }
    )
    assert settings.enabled is True
    assert settings.max_attempts == 3
    assert settings.backoff_seconds == (1, 5)
    assert settings.lease_seconds == 120
    assert settings.reconciler_interval_seconds == 10
    assert settings.error_details_max_chars == 4096
