"""@meta
name: retry_policy
type: module
domain: run_orchestration
ownership: infrastructure
responsibility:
  - Classify runtime failures into retry policy buckets.
  - Provide stable error summaries for SSOT persistence and UI display.
inputs:
  - Exceptions raised during orchestration / worker execution.
outputs:
  - Retry classification (`transient|permanent|canceled|unknown`) + stable summary.
lifecycle:
  - status: active
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


RETRY_POLICY_FIELDS = (
    "maximum_attempts",
    "initial_backoff_seconds",
    "lease_seconds",
    "reconciler_interval_seconds",
    "error_detail_limit",
)
RETRY_POLICY_DEFAULTS = {
    "maximum_attempts": 3,
    "initial_backoff_seconds": 10,
    "lease_seconds": 300,
    "reconciler_interval_seconds": 30,
    "error_detail_limit": 10000,
}
RETRY_POLICY_BOUNDS = {
    "maximum_attempts": (1, 10),
    "initial_backoff_seconds": (0, 3600),
    "lease_seconds": (30, 86400),
    "reconciler_interval_seconds": (5, 3600),
    "error_detail_limit": (1000, 100000),
}
_RETRY_POLICY_INPUT_FIELDS = frozenset(
    RETRY_POLICY_FIELDS
    + (
        "enabled",
        "max_attempts",
        "backoff_seconds",
        "error_details_max_chars",
    )
)


@dataclass(frozen=True)
class RetryPolicy:
    maximum_attempts: int
    initial_backoff_seconds: int
    lease_seconds: int
    reconciler_interval_seconds: int
    error_detail_limit: int


@dataclass(frozen=True)
class RetryClassification:
    classification: str
    summary: str
    details: dict[str, Any] | None = None


def _coerce_integer(value: Any, *, field: str, strict: bool) -> int | None:
    if isinstance(value, bool):
        if strict:
            raise ValueError(f"{field} must be an integer")
        return None
    if isinstance(value, float) and not value.is_integer():
        if strict:
            raise ValueError(f"{field} must be an integer")
        return None
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        if strict:
            raise ValueError(f"{field} must be an integer") from exc
        return None


def _bounded_value(
    value: Any,
    *,
    field: str,
    strict: bool,
    minimum: int,
    maximum: int,
) -> int | None:
    parsed = _coerce_integer(value, field=field, strict=strict)
    if parsed is None:
        return None
    if strict and not minimum <= parsed <= maximum:
        raise ValueError(f"{field} must be between {minimum} and {maximum}")
    return max(minimum, min(maximum, parsed))


def normalize_retry_policy(
    values: dict[str, Any] | None,
    *,
    strict: bool = False,
    include_defaults: bool = True,
) -> dict[str, int]:
    """Normalize canonical retry scalars and legacy control-plane input."""
    raw = dict(values or {})
    if strict:
        unsupported = sorted(set(raw) - _RETRY_POLICY_INPUT_FIELDS)
        if unsupported:
            raise ValueError(f"unsupported retry fields: {unsupported}")

    result: dict[str, int] = {}

    def resolve(canonical: str, aliases: tuple[str, ...]) -> tuple[Any, bool]:
        if canonical in raw:
            return raw[canonical], True
        for alias in aliases:
            if alias in raw:
                return raw[alias], True
        return RETRY_POLICY_DEFAULTS[canonical], include_defaults

    maximum_attempts, has_maximum_attempts = resolve("maximum_attempts", ("max_attempts",))
    if "maximum_attempts" not in raw and raw.get("enabled") is False:
        maximum_attempts, has_maximum_attempts = 1, True
    elif "enabled" in raw and not isinstance(raw["enabled"], bool):
        if strict:
            raise ValueError("enabled must be boolean")
    if has_maximum_attempts:
        normalized = _bounded_value(
            maximum_attempts,
            field="maximum_attempts",
            strict=strict,
            minimum=RETRY_POLICY_BOUNDS["maximum_attempts"][0],
            maximum=RETRY_POLICY_BOUNDS["maximum_attempts"][1],
        )
        result["maximum_attempts"] = (
            RETRY_POLICY_DEFAULTS["maximum_attempts"] if normalized is None else normalized
        )

    if "initial_backoff_seconds" in raw:
        backoff_value = raw["initial_backoff_seconds"]
        backoff_present = True
    elif "backoff_seconds" in raw:
        backoff_value = raw["backoff_seconds"]
        if (
            not isinstance(backoff_value, list)
            or not backoff_value
            or len(backoff_value) > 20
        ):
            if strict:
                raise ValueError("backoff_seconds must contain 1 to 20 integers")
            backoff_present = include_defaults
            backoff_value = RETRY_POLICY_DEFAULTS["initial_backoff_seconds"]
        else:
            parsed_backoff: list[int] = []
            for item in backoff_value:
                normalized_item = _bounded_value(
                    item,
                    field="backoff_seconds",
                    strict=strict,
                    minimum=RETRY_POLICY_BOUNDS["initial_backoff_seconds"][0],
                    maximum=RETRY_POLICY_BOUNDS["initial_backoff_seconds"][1],
                )
                if normalized_item is None:
                    parsed_backoff = []
                    break
                parsed_backoff.append(normalized_item)
            backoff_present = bool(parsed_backoff)
            backoff_value = parsed_backoff[0] if parsed_backoff else RETRY_POLICY_DEFAULTS["initial_backoff_seconds"]
    else:
        backoff_value = RETRY_POLICY_DEFAULTS["initial_backoff_seconds"]
        backoff_present = include_defaults
    if backoff_present:
        normalized = _bounded_value(
            backoff_value,
            field="initial_backoff_seconds",
            strict=strict,
            minimum=RETRY_POLICY_BOUNDS["initial_backoff_seconds"][0],
            maximum=RETRY_POLICY_BOUNDS["initial_backoff_seconds"][1],
        )
        result["initial_backoff_seconds"] = (
            RETRY_POLICY_DEFAULTS["initial_backoff_seconds"] if normalized is None else normalized
        )

    for canonical, aliases in (
        ("lease_seconds", ()),
        ("error_detail_limit", ("error_details_max_chars",)),
    ):
        value, present = resolve(canonical, aliases)
        if present:
            normalized = _bounded_value(
                value,
                field=canonical,
                strict=strict,
                minimum=RETRY_POLICY_BOUNDS[canonical][0],
                maximum=RETRY_POLICY_BOUNDS[canonical][1],
            )
            result[canonical] = RETRY_POLICY_DEFAULTS[canonical] if normalized is None else normalized

    legacy_input = any(
        field in raw
        for field in ("enabled", "max_attempts", "backoff_seconds", "error_details_max_chars")
    )
    interval_is_legacy = legacy_input and not any(
        field in raw
        for field in (
            "maximum_attempts",
            "initial_backoff_seconds",
            "error_detail_limit",
        )
    )
    if "reconciler_interval_seconds" in raw:
        normalized_interval = _coerce_integer(
            raw["reconciler_interval_seconds"],
            field="reconciler_interval_seconds",
            strict=strict,
        )
        if normalized_interval is None:
            normalized_interval = RETRY_POLICY_DEFAULTS["reconciler_interval_seconds"]
        elif interval_is_legacy and normalized_interval == 0:
            normalized_interval = RETRY_POLICY_DEFAULTS["reconciler_interval_seconds"]
        elif interval_is_legacy:
            normalized_interval = max(
                RETRY_POLICY_BOUNDS["reconciler_interval_seconds"][0],
                min(RETRY_POLICY_BOUNDS["reconciler_interval_seconds"][1], normalized_interval),
            )
        elif strict and not (
            RETRY_POLICY_BOUNDS["reconciler_interval_seconds"][0]
            <= normalized_interval
            <= RETRY_POLICY_BOUNDS["reconciler_interval_seconds"][1]
        ):
            raise ValueError("reconciler_interval_seconds must be between 5 and 3600")
        else:
            normalized_interval = max(
                RETRY_POLICY_BOUNDS["reconciler_interval_seconds"][0],
                min(RETRY_POLICY_BOUNDS["reconciler_interval_seconds"][1], normalized_interval),
            )
        result["reconciler_interval_seconds"] = normalized_interval
    elif include_defaults:
        result["reconciler_interval_seconds"] = RETRY_POLICY_DEFAULTS["reconciler_interval_seconds"]

    if include_defaults:
        return {field: result[field] for field in RETRY_POLICY_FIELDS}
    return result


_TRANSIENT_HTTP_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}
_PERMANENT_HTTP_STATUS_CODES = {400, 401, 403, 404, 409, 422}


def classify_exception_for_retry(exc: BaseException) -> RetryClassification:
    if isinstance(exc, KeyboardInterrupt):
        return RetryClassification("canceled", "keyboard_interrupt")

    try:
        import httpx
    except Exception:
        httpx = None  # type: ignore[assignment]

    if httpx is not None:
        timeout_types = (
            getattr(httpx, "TimeoutException", Exception),
        )
        if isinstance(exc, timeout_types):
            return RetryClassification("transient", "timeout")

        status_error_type = getattr(httpx, "HTTPStatusError", None)
        if status_error_type is not None and isinstance(exc, status_error_type):
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            if isinstance(status_code, int):
                if status_code in _TRANSIENT_HTTP_STATUS_CODES:
                    return RetryClassification("transient", f"http_{status_code}")
                if status_code in _PERMANENT_HTTP_STATUS_CODES:
                    return RetryClassification("permanent", f"http_{status_code}")
                return RetryClassification("unknown", f"http_{status_code}")
            return RetryClassification("unknown", "http_status_error")

        transport_error_type = getattr(httpx, "TransportError", None)
        if transport_error_type is not None and isinstance(exc, transport_error_type):
            return RetryClassification("transient", "transport_error")

    if isinstance(exc, TimeoutError):
        return RetryClassification("transient", "timeout")

    return RetryClassification("unknown", exc.__class__.__name__)

