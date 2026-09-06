"""@meta
type: test
scope: unit
domain: run_orchestration
covers:
  - fitcv_cp.retry_policy classify_exception_for_retry
tags:
  - fast
  - ci-safe
"""

import httpx
import pytest

from fitcv_cp.retry_policy import (
    RETRY_POLICY_BOUNDS,
    RETRY_POLICY_DEFAULTS,
    classify_exception_for_retry,
    normalize_retry_policy,
)


def test_normalize_retry_policy_uses_canonical_scalar_fields() -> None:
    values = normalize_retry_policy(
        {
            "maximum_attempts": 4,
            "initial_backoff_seconds": 7,
            "lease_seconds": 900,
            "reconciler_interval_seconds": 30,
            "error_detail_limit": 2048,
            "enabled": False,
            "max_attempts": 9,
            "backoff_seconds": [99, 100],
            "error_details_max_chars": 9999,
        },
        strict=True,
    )

    assert values == {
        "maximum_attempts": 4,
        "initial_backoff_seconds": 7,
        "lease_seconds": 900,
        "reconciler_interval_seconds": 30,
        "error_detail_limit": 2048,
    }


def test_normalize_retry_policy_maps_legacy_fields_and_disabled_retry() -> None:
    values = normalize_retry_policy(
        {
            "enabled": False,
            "max_attempts": 5,
            "backoff_seconds": [7, 20],
            "lease_seconds": 900,
            "reconciler_interval_seconds": 0,
            "error_details_max_chars": 25000,
        },
        strict=True,
    )

    assert values == {
        "maximum_attempts": 1,
        "initial_backoff_seconds": 7,
        "lease_seconds": 900,
        "reconciler_interval_seconds": 30,
        "error_detail_limit": 25000,
    }


def test_normalize_retry_policy_rejects_empty_legacy_backoff_before_mapping() -> None:
    with pytest.raises(ValueError, match="backoff_seconds"):
        normalize_retry_policy({"backoff_seconds": []}, strict=True)


def test_retry_policy_constants_define_canonical_bounds_and_defaults() -> None:
    assert tuple(RETRY_POLICY_DEFAULTS) == (
        "maximum_attempts",
        "initial_backoff_seconds",
        "lease_seconds",
        "reconciler_interval_seconds",
        "error_detail_limit",
    )
    assert RETRY_POLICY_BOUNDS["maximum_attempts"] == (1, 10)
    assert RETRY_POLICY_BOUNDS["initial_backoff_seconds"] == (0, 3600)
    assert RETRY_POLICY_BOUNDS["lease_seconds"] == (30, 86400)
    assert RETRY_POLICY_BOUNDS["reconciler_interval_seconds"] == (5, 3600)
    assert RETRY_POLICY_BOUNDS["error_detail_limit"] == (1000, 100000)




def test_classify_exception_for_retry_timeout_is_transient() -> None:
    result = classify_exception_for_retry(httpx.ReadTimeout("timeout"))
    assert result.classification == "transient"
    assert result.summary == "timeout"


def test_classify_exception_for_retry_http_429_is_transient() -> None:
    request = httpx.Request("GET", "https://example.test")
    response = httpx.Response(429, request=request)
    exc = httpx.HTTPStatusError("rate limited", request=request, response=response)
    result = classify_exception_for_retry(exc)
    assert result.classification == "transient"
    assert result.summary == "http_429"


def test_classify_exception_for_retry_http_401_is_permanent() -> None:
    request = httpx.Request("GET", "https://example.test")
    response = httpx.Response(401, request=request)
    exc = httpx.HTTPStatusError("unauthorized", request=request, response=response)
    result = classify_exception_for_retry(exc)
    assert result.classification == "permanent"
    assert result.summary == "http_401"

