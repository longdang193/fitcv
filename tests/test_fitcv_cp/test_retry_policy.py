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

from fitcv_cp.retry_policy import classify_exception_for_retry


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

