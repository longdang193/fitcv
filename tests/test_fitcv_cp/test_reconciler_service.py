"""
name: test_reconciler_service
type: test
scope: unit
domain: run_orchestration
covers:
  - fitcv_cp.reconciler_service interval safety floor
tags:
  - fast
  - ci-safe
"""

from unittest.mock import patch

import pytest

from fitcv_cp.reconciler_service import run_reconciler_forever
from fitcv_cp.retry_settings import RetrySettings


def _settings(interval: int) -> RetrySettings:
    return RetrySettings(
        maximum_attempts=3,
        initial_backoff_seconds=10,
        lease_seconds=900,
        reconciler_interval_seconds=interval,
        error_detail_limit=2048,
    )


def test_reconciler_service_sleeps_canonical_minimum_five_seconds() -> None:
    with patch("fitcv_cp.reconciler_service._build_store"), patch(
        "fitcv_cp.reconciler_service.reconcile_abandoned_attempts"
    ), patch("fitcv_cp.reconciler_service.load_retry_settings", return_value=_settings(5)), patch(
        "fitcv_cp.reconciler_service.time.sleep", side_effect=KeyboardInterrupt
    ) as sleep_mock:
        with pytest.raises(KeyboardInterrupt):
            run_reconciler_forever()

    sleep_mock.assert_called_once_with(5)


def test_reconciler_service_enforces_one_second_floor_for_injected_zero() -> None:
    with patch("fitcv_cp.reconciler_service._build_store"), patch(
        "fitcv_cp.reconciler_service.reconcile_abandoned_attempts"
    ), patch("fitcv_cp.reconciler_service.load_retry_settings", return_value=_settings(0)), patch(
        "fitcv_cp.reconciler_service.time.sleep", side_effect=KeyboardInterrupt
    ) as sleep_mock:
        with pytest.raises(KeyboardInterrupt):
            run_reconciler_forever()

    sleep_mock.assert_called_once_with(1)
