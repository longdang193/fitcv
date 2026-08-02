"""Company-portal job acquisition with one FitCV boundary contract."""

from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from xml.etree import ElementTree

import fitcv.ats_export as _ats
from fitcv.ats_export import (
    build_greenhouse_api_url,
    parse_greenhouse_jobs,
    parse_workday_jobs,
)
from fitcv.ingest import CanonicalJobs, canonicalize_jobs, write_canonical_jobs
from fitcv.personio_export import (
    build_personio_feed_url,
    extract_personio_job_page_description,
    parse_personio_jobs,
)

ProviderMap = Mapping[str, "ProviderDefinition"]


class JobSourceError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        provider_id: str | None = None,
        careers_url: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.provider_id = provider_id
        self.careers_url = careers_url


@dataclass(frozen=True)
class ScannerRequest:
    provider: str
    company_name: str
    careers_url: str
    keywords: tuple[str, ...]
    max_jobs: int
    timeout_seconds: int


@dataclass(frozen=True)
class ProviderDefinition:
    provider_id: str
    label: str
    detect: Callable[[str], bool]
    acquire: Callable[[ScannerRequest], list[dict[str, Any]]]


@dataclass(frozen=True)
class AcquisitionResult:
    provider_id: str
    selection_mode: str
    artifact: CanonicalJobs


def _provider_map(providers: ProviderMap | None) -> ProviderMap:
    return PROVIDERS if providers is None else providers


def _canonical_https_url(value: str) -> str:
    raw = str(value or "").strip()
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError as exc:
        raise JobSourceError("invalid_scanner_request", "careers_url is invalid") from exc
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme.lower() != "https" or not hostname:
        raise JobSourceError("invalid_scanner_request", "careers_url must be an absolute HTTPS URL")
    if parsed.username or parsed.password:
        raise JobSourceError("invalid_scanner_request", "careers_url must not contain credentials")
    if port is not None:
        raise JobSourceError("invalid_scanner_request", "careers_url must not contain a custom port")
    if parsed.query:
        raise JobSourceError("invalid_scanner_request", "careers_url must not contain a query")
    if parsed.fragment:
        raise JobSourceError("invalid_scanner_request", "careers_url must not contain a fragment")
    path = parsed.path.rstrip("/")
    return urlunsplit(("https", hostname, path, "", ""))


def _bounded_int(name: str, value: object, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise JobSourceError(
            "invalid_scanner_request",
            f"{name} must be an integer from {minimum} through {maximum}",
        )
    return value


def _normalize_keywords(values: Sequence[str] | None) -> tuple[str, ...]:
    keywords: list[str] = []
    seen: set[str] = set()
    for raw in values or ():
        keyword = str(raw or "").strip()
        folded = keyword.casefold()
        if not keyword or folded in seen:
            continue
        seen.add(folded)
        keywords.append(keyword)
    return tuple(keywords)


def build_scanner_request(
    *,
    company_name: str,
    careers_url: str,
    provider: str = "auto",
    keywords: Sequence[str] | None = None,
    max_jobs: int = 50,
    timeout_seconds: int = 60,
    providers: ProviderMap | None = None,
) -> ScannerRequest:
    registry = _provider_map(providers)
    provider_id = str(provider or "auto").strip().lower()
    if provider_id != "auto" and provider_id not in registry:
        raise JobSourceError("unknown_provider", f"Unknown provider: {provider_id}")
    company = str(company_name or "").strip()
    if not company or len(company) > 200:
        raise JobSourceError(
            "invalid_scanner_request",
            "company_name must contain 1 through 200 characters",
        )
    return ScannerRequest(
        provider=provider_id,
        company_name=company,
        careers_url=_canonical_https_url(careers_url),
        keywords=_normalize_keywords(keywords),
        max_jobs=_bounded_int("max_jobs", max_jobs, 1, 200),
        timeout_seconds=_bounded_int("timeout_seconds", timeout_seconds, 1, 120),
    )


def list_provider_options(providers: ProviderMap | None = None) -> list[dict[str, str]]:
    return [
        {"id": definition.provider_id, "label": definition.label}
        for definition in _provider_map(providers).values()
    ]

def verify_scanner_portal(
    *, company_name: str, careers_url: str, providers: ProviderMap | None = None
) -> dict[str, str]:
    request = build_scanner_request(
        provider="auto", company_name=company_name, careers_url=careers_url,
        keywords=(), max_jobs=1, timeout_seconds=60, providers=providers,
    )
    definition = resolve_provider(request, providers=providers)
    return {
        "company_name": request.company_name,
        "careers_url": request.careers_url,
        "provider_id": definition.provider_id,
        "provider_label": definition.label,
    }


def resolve_provider(
    request: ScannerRequest,
    *,
    providers: ProviderMap | None = None,
) -> ProviderDefinition:
    registry = _provider_map(providers)
    if request.provider != "auto":
        definition = registry.get(request.provider)
        if definition is None:
            raise JobSourceError("unknown_provider", f"Unknown provider: {request.provider}")
        if not definition.detect(request.careers_url):
            raise JobSourceError(
                "unsupported_provider_url",
                f"URL is not supported by provider {definition.provider_id}",
                provider_id=definition.provider_id,
                careers_url=request.careers_url,
            )
        return definition

    matches = [definition for definition in registry.values() if definition.detect(request.careers_url)]
    if not matches:
        raise JobSourceError(
            "unsupported_provider_url",
            "No provider supports this careers URL",
            careers_url=request.careers_url,
        )
    if len(matches) > 1:
        provider_ids = ", ".join(sorted(definition.provider_id for definition in matches))
        raise JobSourceError(
            "ambiguous_provider_url",
            f"Careers URL matches multiple providers: {provider_ids}",
            careers_url=request.careers_url,
        )
    return matches[0]


def _remaining_timeout(deadline: float, provider_id: str, careers_url: str) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise JobSourceError(
            "provider_timeout",
            f"Provider {provider_id} exceeded acquisition deadline",
            provider_id=provider_id,
            careers_url=careers_url,
        )
    return min(30.0, remaining)


def _mapped_provider_error(
    provider_id: str,
    careers_url: str,
    exc: BaseException,
    *,
    detail: bool = False,
) -> JobSourceError:
    cause: BaseException | None = exc
    while cause is not None:
        if isinstance(cause, TimeoutError):
            code = "provider_timeout"
            break
        if isinstance(cause, HTTPError):
            code = "provider_http_error"
            break
        if isinstance(cause, URLError):
            code = "provider_timeout" if isinstance(cause.reason, TimeoutError) else "provider_http_error"
            break
        cause = cause.__cause__
    else:
        code = "provider_detail_error" if detail else "provider_payload_error"
    return JobSourceError(
        code,
        f"Provider {provider_id} could not return usable jobs",
        provider_id=provider_id,
        careers_url=careers_url,
    )


def _is_personio(url: str) -> bool:
    try:
        build_personio_feed_url(url)
    except ValueError:
        return False
    return True


def _is_greenhouse(url: str) -> bool:
    try:
        build_greenhouse_api_url(url)
    except ValueError:
        return False
    return True


def _is_workday(url: str) -> bool:
    try:
        _ats._workday_endpoints(url)
    except ValueError:
        return False
    return True


def _fetch_detail(url: str, deadline: float, provider_id: str, careers_url: str) -> str:
    try:
        return _ats._fetch_text(url, math.ceil(_remaining_timeout(deadline, provider_id, careers_url)))
    except Exception as exc:
        raise _mapped_provider_error(provider_id, careers_url, exc, detail=True) from exc


def _acquire_personio(request: ScannerRequest) -> list[dict[str, Any]]:
    deadline = time.monotonic() + request.timeout_seconds
    try:
        xml_text = _ats._fetch_text(
            build_personio_feed_url(request.careers_url),
            math.ceil(_remaining_timeout(deadline, "personio", request.careers_url)),
        )
        jobs = parse_personio_jobs(
            xml_text,
            company_name=request.company_name,
            careers_url=request.careers_url,
            keywords=request.keywords,
            description_loader=lambda url: extract_personio_job_page_description(
                _fetch_detail(url, deadline, "personio", request.careers_url)
            ),
        )
    except JobSourceError:
        raise
    except (ElementTree.ParseError, ValueError, RuntimeError) as exc:
        raise _mapped_provider_error("personio", request.careers_url, exc) from exc
    return jobs[: request.max_jobs]


def _acquire_greenhouse(request: ScannerRequest) -> list[dict[str, Any]]:
    deadline = time.monotonic() + request.timeout_seconds
    try:
        payload = _ats._fetch_json(
            build_greenhouse_api_url(request.careers_url),
            math.ceil(_remaining_timeout(deadline, "greenhouse", request.careers_url)),
        )
        jobs = parse_greenhouse_jobs(
            payload,
            company_name=request.company_name,
            careers_url=request.careers_url,
            keywords=request.keywords,
        )
    except JobSourceError:
        raise
    except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
        raise _mapped_provider_error("greenhouse", request.careers_url, exc) from exc
    return jobs[: request.max_jobs]


def _acquire_workday(request: ScannerRequest) -> list[dict[str, Any]]:
    deadline = time.monotonic() + request.timeout_seconds
    api_url, _ = _ats._workday_endpoints(request.careers_url)
    jobs: list[dict[str, Any]] = []
    seen: set[str] = set()
    offset = 0
    while len(jobs) < request.max_jobs:
        try:
            payload = _ats._fetch_json(
                api_url,
                math.ceil(_remaining_timeout(deadline, "workday", request.careers_url)),
                body={
                    "limit": _ats._PAGE_SIZE,
                    "offset": offset,
                    "searchText": " ".join(request.keywords),
                    "appliedFacets": {},
                },
            )
            page_jobs = parse_workday_jobs(
                payload,
                company_name=request.company_name,
                careers_url=request.careers_url,
                keywords=request.keywords,
                description_loader=lambda url: _fetch_detail(
                    url, deadline, "workday", request.careers_url
                ),
            )
        except JobSourceError:
            raise
        except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
            raise _mapped_provider_error("workday", request.careers_url, exc) from exc

        for job in page_jobs:
            job_url = str(job.get("jobUrl") or "")
            if job_url and job_url not in seen:
                seen.add(job_url)
                jobs.append(job)
                if len(jobs) >= request.max_jobs:
                    break
        postings = payload.get("jobPostings")
        count = len(postings) if isinstance(postings, list) else 0
        total = payload.get("total")
        offset += _ats._PAGE_SIZE
        if count < _ats._PAGE_SIZE or isinstance(total, int) and offset >= total:
            break
    return jobs


PROVIDERS: dict[str, ProviderDefinition] = {
    "personio": ProviderDefinition("personio", "Personio", _is_personio, _acquire_personio),
    "greenhouse": ProviderDefinition(
        "greenhouse", "Greenhouse", _is_greenhouse, _acquire_greenhouse
    ),
    "workday": ProviderDefinition("workday", "Workday", _is_workday, _acquire_workday),
}


def acquire_scanner_jobs(
    request: ScannerRequest,
    *,
    providers: ProviderMap | None = None,
) -> AcquisitionResult:
    definition = resolve_provider(request, providers=providers)
    try:
        jobs = definition.acquire(request)
        artifact = canonicalize_jobs(jobs[: request.max_jobs])
    except JobSourceError:
        raise
    except Exception as exc:
        raise _mapped_provider_error(definition.provider_id, request.careers_url, exc) from exc
    return AcquisitionResult(
        provider_id=definition.provider_id,
        selection_mode="auto" if request.provider == "auto" else "explicit",
        artifact=artifact,
    )


def export_scanner_jobs(
    request: ScannerRequest,
    output_path: str | Path,
    *,
    providers: ProviderMap | None = None,
) -> AcquisitionResult:
    result = acquire_scanner_jobs(request, providers=providers)
    write_canonical_jobs(output_path, result.artifact)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export company-portal jobs in FitCV format.")
    parser.add_argument("--provider", default="auto")
    parser.add_argument("--company", required=True)
    parser.add_argument("--careers-url", required=True)
    parser.add_argument("--keyword", action="append", default=[])
    parser.add_argument("--max-jobs", type=int, default=50)
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        request = build_scanner_request(
            provider=args.provider,
            company_name=args.company,
            careers_url=args.careers_url,
            keywords=args.keyword,
            max_jobs=args.max_jobs,
            timeout_seconds=args.timeout_seconds,
        )
        result = export_scanner_jobs(request, args.output)
    except JobSourceError as exc:
        parser.error(f"{exc.code}: {exc}")
    print(f"Exported {len(result.artifact.jobs)} {result.provider_id} jobs to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
