"""Company-portal job acquisition with one FitCV boundary contract."""

from __future__ import annotations

import argparse
import ipaddress
import json
import math
import re
import socket
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
    trusted_provider_config: Mapping[str, Any] | None = None


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


_SLUG = re.compile(r"[a-z0-9][a-z0-9._-]{0,119}\Z")
_PERSONIO_HOST = re.compile(r"[a-z0-9][a-z0-9-]*\.jobs\.personio\.(de|com)\Z")
_WORKDAY_HOST = re.compile(r"[a-z0-9][a-z0-9-]*\.(wd[a-z0-9-]*)\.myworkdayjobs\.com\Z")
_CONFIG_KEYS = {
    "greenhouse": ("schema_version", "provider_id", "host", "region", "board_slug"),
    "ashby": ("schema_version", "provider_id", "host", "region", "board_slug"),
    "lever": ("schema_version", "provider_id", "host", "region", "company_slug"),
    "personio": ("schema_version", "provider_id", "host", "region", "company_slug"),
    "workday": ("schema_version", "provider_id", "host", "region", "tenant", "instance", "site_path"),
    "gem": ("schema_version", "provider_id", "host", "region", "board_slug"),
}
_ALLOWED_HOSTS = {
    "greenhouse": {"boards.greenhouse.io", "job-boards.greenhouse.io", "job-boards.eu.greenhouse.io"},
    "ashby": {"jobs.ashbyhq.com"},
    "lever": {"jobs.lever.co", "jobs.eu.lever.co"},
    "gem": {"jobs.gem.com"},
}


def _invalid_config(message: str) -> JobSourceError:
    return JobSourceError("provider_config_invalid", message)


def _validate_host(host: object) -> str:
    if not isinstance(host, str) or not host or host != host.lower() or host.endswith("."):
        raise _invalid_config("host must be lowercase without trailing dot")
    if "\\" in host or "." not in host:
        raise _invalid_config("host is invalid")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return host
    raise _invalid_config("host must not be an IP literal")


def validate_trusted_provider_config(config: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(config, Mapping):
        raise _invalid_config("provider config must be an object")
    provider_id = config.get("provider_id")
    if not isinstance(provider_id, str) or provider_id not in _CONFIG_KEYS:
        raise _invalid_config("provider_id is unsupported")
    expected_keys = _CONFIG_KEYS[provider_id]
    if set(config) != set(expected_keys):
        raise _invalid_config("provider config keys are invalid")
    if config.get("schema_version") != 1:
        raise _invalid_config("schema_version must be 1")
    host = _validate_host(config.get("host"))
    allowed_hosts = _ALLOWED_HOSTS.get(provider_id)
    if allowed_hosts is not None:
        if host not in allowed_hosts:
            raise _invalid_config("host is not allowed for provider")
    elif provider_id == "personio":
        if _PERSONIO_HOST.fullmatch(host) is None:
            raise _invalid_config("host is not allowed for provider")
    elif provider_id == "workday":
        if _WORKDAY_HOST.fullmatch(host) is None:
            raise _invalid_config("host is not allowed for provider")
    region = config.get("region")
    allowed_regions = {
        "greenhouse": {"global", "eu"},
        "ashby": {"global"},
        "lever": {"global", "eu"},
        "personio": {"de", "com"},
        "workday": {"global"},
        "gem": {"global"},
    }[provider_id]
    if not isinstance(region, str) or region not in allowed_regions:
        raise _invalid_config("region is invalid")
    if provider_id == "personio" and not host.endswith(f".{region}"):
        raise _invalid_config("region does not match host")
    if provider_id == "personio" and config.get("company_slug") != host.split(".", 1)[0]:
        raise _invalid_config("company_slug does not match host")
    if provider_id == "greenhouse" and host.endswith(".eu.greenhouse.io") != (region == "eu"):
        raise _invalid_config("region does not match host")
    if provider_id == "lever" and host.endswith(".eu.lever.co") != (region == "eu"):
        raise _invalid_config("region does not match host")
    for key in expected_keys[4:]:
        value = config.get(key)
        if not isinstance(value, str) or not value:
            raise _invalid_config(f"{key} is required")
    if provider_id in {"greenhouse", "ashby", "lever", "personio", "gem"}:
        if not _SLUG.fullmatch(str(config.get(expected_keys[-1]))):
            raise _invalid_config("slug is invalid")
    else:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", str(config["tenant"])):
            raise _invalid_config("tenant is invalid")
        if not re.fullmatch(r"wd[a-z0-9-]*", str(config["instance"])):
            raise _invalid_config("instance is invalid")
        host_parts = host.split(".")
        if config["tenant"] != host_parts[0] or config["instance"] != host_parts[1]:
            raise _invalid_config("Workday host fields do not match host")
        site_path = config["site_path"]
        if (
            not isinstance(site_path, str)
            or not site_path.startswith("/")
            or "?" in site_path
            or "#" in site_path
            or "\\" in site_path
            or re.search(r"%(?:2f|2F|5c|5C)", site_path)
            or any(segment in {"", ".", ".."} for segment in site_path.split("/")[1:])
        ):
            raise _invalid_config("site_path is invalid")
    return config


def _canonical_https_url(value: str) -> str:
    raw = str(value or "").strip()
    if "\\" in raw or re.search(r"%(?:2f|2F|5c|5C)", raw):
        raise JobSourceError("invalid_scanner_request", "careers_url contains an encoded separator")
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
    if "//" in parsed.path:
        raise JobSourceError("invalid_scanner_request", "careers_url path contains an empty segment")
    if hostname.endswith("."):
        raise JobSourceError("invalid_scanner_request", "careers_url host must not have a trailing dot")
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise JobSourceError("invalid_scanner_request", "careers_url host must not be an IP literal")
    path_segments = parsed.path.strip("/").split("/") if parsed.path.strip("/") else []
    if any(not segment or segment in {".", ".."} for segment in path_segments):
        raise JobSourceError("invalid_scanner_request", "careers_url path contains an invalid segment")
    path = parsed.path.rstrip("/")
    return urlunsplit(("https", hostname, path, "", ""))


def _config_url(config: Mapping[str, Any]) -> str:
    provider_id = str(config["provider_id"])
    host = str(config["host"])
    if provider_id in {"greenhouse", "ashby", "gem"}:
        return f"https://{host}/{config['board_slug']}"
    if provider_id == "lever":
        return f"https://{host}/{config['company_slug']}"
    if provider_id == "personio":
        return f"https://{host}"
    return f"https://{host}{config['site_path']}"


def build_trusted_provider_config(
    *, provider: str | None = None, provider_id: str | None = None, careers_url: str
) -> dict[str, Any]:
    selected_provider = str(provider_id or provider or "").strip().lower()
    try:
        canonical_url = _canonical_https_url(careers_url)
    except JobSourceError as exc:
        raise _invalid_config(str(exc)) from exc
    parsed = urlsplit(canonical_url)
    host = parsed.hostname or ""
    parts = [segment for segment in parsed.path.split("/") if segment]
    if selected_provider in {"greenhouse", "ashby", "lever", "gem"}:
        if len(parts) != 1 or not _SLUG.fullmatch(parts[0]):
            raise _invalid_config("careers_url path must contain one valid provider slug")
        if selected_provider == "greenhouse":
            region = "eu" if host == "job-boards.eu.greenhouse.io" else "global"
            config = {"schema_version": 1, "provider_id": selected_provider, "host": host, "region": region, "board_slug": parts[0]}
        elif selected_provider == "ashby":
            config = {"schema_version": 1, "provider_id": selected_provider, "host": host, "region": "global", "board_slug": parts[0]}
        elif selected_provider == "gem":
            config = {"schema_version": 1, "provider_id": selected_provider, "host": host, "region": "global", "board_slug": parts[0]}
        else:
            region = "eu" if host == "jobs.eu.lever.co" else "global"
            config = {"schema_version": 1, "provider_id": selected_provider, "host": host, "region": region, "company_slug": parts[0]}
    elif selected_provider == "personio":
        if parts or _PERSONIO_HOST.fullmatch(host) is None:
            raise _invalid_config("careers_url is not a Personio root URL")
        config = {"schema_version": 1, "provider_id": selected_provider, "host": host, "region": host.rsplit(".", 1)[1], "company_slug": host.split(".", 1)[0]}
    elif selected_provider == "workday":
        match = _WORKDAY_HOST.fullmatch(host)
        if match is None:
            raise _invalid_config("careers_url is not a Workday URL")
        if len(parts) == 2 and re.fullmatch(r"[a-z]{2}-[A-Z]{2}", parts[0]):
            parts = parts[1:]
        if len(parts) != 1:
            raise _invalid_config("careers_url must contain one Workday site path")
        config = {"schema_version": 1, "provider_id": selected_provider, "host": host, "region": "global", "tenant": match.group(0).split(".", 1)[0], "instance": match.group(1), "site_path": f"/{parts[0]}"}
    else:
        raise _invalid_config("provider_id is unsupported")
    validate_trusted_provider_config(config)
    return config


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
    trusted_provider_config: Mapping[str, Any] | None = None,
) -> ScannerRequest:
    registry = _provider_map(providers)
    provider_id = str(provider or "auto").strip().lower()
    validated_config = None
    if trusted_provider_config is not None:
        validated_config = validate_trusted_provider_config(trusted_provider_config)
        config_provider = str(validated_config["provider_id"])
        if provider_id != "auto" and provider_id != config_provider:
            raise JobSourceError("invalid_scanner_request", "provider disagrees with trusted provider config")
        derived_url = _config_url(validated_config)
        canonical_careers_url = _canonical_https_url(careers_url)
        if canonical_careers_url != derived_url:
            parsed_careers_url = urlsplit(canonical_careers_url)
            path_parts = [part for part in parsed_careers_url.path.split("/") if part]
            locale_prefixed_workday_url = (
                config_provider == "workday"
                and len(path_parts) == 2
                and re.fullmatch(r"[a-z]{2}-[A-Z]{2}", path_parts[0]) is not None
                and urlunsplit(("https", parsed_careers_url.netloc, f"/{path_parts[1]}", "", "")) == derived_url
            )
            if not locale_prefixed_workday_url:
                raise JobSourceError("invalid_scanner_request", "careers_url disagrees with trusted provider config")
        provider_id = config_provider
    if provider_id != "auto" and provider_id not in registry and provider_id != "wellfound":
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
        careers_url=derived_url if validated_config is not None else _canonical_https_url(careers_url),
        keywords=_normalize_keywords(keywords),
        max_jobs=_bounded_int("max_jobs", max_jobs, 1, 200),
        timeout_seconds=_bounded_int("timeout_seconds", timeout_seconds, 1, 120),
        trusted_provider_config=validated_config,
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
        if request.provider == "wellfound":
            raise JobSourceError("unsupported_provider_url", "Wellfound is discovery-only")
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


def _request_config(request: ScannerRequest, provider_id: str) -> Mapping[str, Any]:
    config = request.trusted_provider_config
    if config is None:
        config = build_trusted_provider_config(provider_id=provider_id, careers_url=request.careers_url)
    validate_trusted_provider_config(config)
    if config["provider_id"] != provider_id:
        raise JobSourceError("invalid_scanner_request", "provider config provider mismatch")
    return config


def _check_public_dns(url: str, provider_id: str, careers_url: str) -> None:
    hostname = urlsplit(url).hostname or ""
    try:
        answers = socket.getaddrinfo(
            hostname,
            443,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
    except OSError as exc:
        raise JobSourceError("provider_ssrf_blocked", "Provider host DNS validation failed", provider_id=provider_id, careers_url=careers_url) from exc
    if not answers:
        raise JobSourceError("provider_ssrf_blocked", "Provider host DNS validation failed", provider_id=provider_id, careers_url=careers_url)
    for answer in answers:
        address_text = answer[4][0]
        try:
            address = ipaddress.ip_address(address_text)
        except ValueError as exc:
            raise JobSourceError("provider_ssrf_blocked", "Provider host DNS validation failed", provider_id=provider_id, careers_url=careers_url) from exc
        if address.version == 6 and address.ipv4_mapped is not None:
            address = address.ipv4_mapped
        if (
            address.is_loopback
            or address.is_private
            or address.is_link_local
            or address.is_multicast
            or address.is_unspecified
            or address.is_reserved
            or not address.is_global
            or (address.version == 4 and address in ipaddress.ip_network("192.0.2.0/24"))
            or (address.version == 4 and address in ipaddress.ip_network("198.51.100.0/24"))
            or (address.version == 4 and address in ipaddress.ip_network("203.0.113.0/24"))
            or (address.version == 6 and address in ipaddress.ip_network("2001:db8::/32"))
        ):
            raise JobSourceError("provider_ssrf_blocked", "Provider host DNS validation failed", provider_id=provider_id, careers_url=careers_url)


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
        if isinstance(cause, _ats.RedirectRejectedError):
            code = "provider_redirect_rejected"
            break
        if isinstance(cause, _ats.ProviderSSRFError):
            code = "provider_ssrf_blocked"
            break
        if isinstance(cause, JobSourceError):
            code = cause.code
            break
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
        build_trusted_provider_config(provider_id="personio", careers_url=url)
    except (JobSourceError, ValueError):
        return False
    return True


def _is_greenhouse(url: str) -> bool:
    try:
        build_trusted_provider_config(provider_id="greenhouse", careers_url=url)
    except (JobSourceError, ValueError):
        return False
    return True


def _is_workday(url: str) -> bool:
    try:
        build_trusted_provider_config(provider_id="workday", careers_url=url)
    except (JobSourceError, ValueError):
        return False
    return True


def _is_ashby(url: str) -> bool:
    try:
        build_trusted_provider_config(provider_id="ashby", careers_url=url)
    except (JobSourceError, ValueError):
        return False
    return True


def _is_lever(url: str) -> bool:
    try:
        build_trusted_provider_config(provider_id="lever", careers_url=url)
    except (JobSourceError, ValueError):
        return False
    return True


def _is_gem(url: str) -> bool:
    try:
        build_trusted_provider_config(provider_id="gem", careers_url=url)
    except (JobSourceError, ValueError):
        return False
    return True


def _fetch_detail(url: str, deadline: float, provider_id: str, careers_url: str) -> str:
    try:
        _check_public_dns(url, provider_id, careers_url)
        return _ats._fetch_text(url, math.ceil(_remaining_timeout(deadline, provider_id, careers_url)))
    except Exception as exc:
        raise _mapped_provider_error(provider_id, careers_url, exc, detail=True) from exc


def _acquire_ashby(request: ScannerRequest) -> list[dict[str, Any]]:
    deadline = time.monotonic() + request.timeout_seconds
    try:
        _request_config(request, "ashby")
        _check_public_dns(request.careers_url, "ashby", request.careers_url)
        api_url = _ats.build_ashby_api_url(request.careers_url)
        _check_public_dns(api_url, "ashby", request.careers_url)
        payload = _ats._fetch_json(api_url, math.ceil(_remaining_timeout(deadline, "ashby", request.careers_url)))
        jobs = _ats.parse_ashby_jobs(payload, company_name=request.company_name, careers_url=request.careers_url, keywords=request.keywords)
    except JobSourceError:
        raise
    except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
        raise _mapped_provider_error("ashby", request.careers_url, exc) from exc
    return jobs[: request.max_jobs]


def _acquire_lever(request: ScannerRequest) -> list[dict[str, Any]]:
    deadline = time.monotonic() + request.timeout_seconds
    try:
        _request_config(request, "lever")
        _check_public_dns(request.careers_url, "lever", request.careers_url)
        api_url = _ats.build_lever_api_url(request.careers_url)
        _check_public_dns(api_url, "lever", request.careers_url)
        payload = _ats._fetch_json(api_url, math.ceil(_remaining_timeout(deadline, "lever", request.careers_url)))
        jobs = _ats.parse_lever_jobs(payload, company_name=request.company_name, careers_url=request.careers_url, keywords=request.keywords)
    except JobSourceError:
        raise
    except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
        raise _mapped_provider_error("lever", request.careers_url, exc) from exc
    return jobs[: request.max_jobs]


def _acquire_personio(request: ScannerRequest) -> list[dict[str, Any]]:
    deadline = time.monotonic() + request.timeout_seconds
    try:
        _request_config(request, "personio")
        _check_public_dns(request.careers_url, "personio", request.careers_url)
        feed_url = build_personio_feed_url(request.careers_url)
        _check_public_dns(feed_url, "personio", request.careers_url)
        xml_text = _ats._fetch_text(
            feed_url,
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
        _request_config(request, "greenhouse")
        _check_public_dns(request.careers_url, "greenhouse", request.careers_url)
        api_url = build_greenhouse_api_url(request.careers_url)
        _check_public_dns(api_url, "greenhouse", request.careers_url)
        payload = _ats._fetch_json(
            api_url,
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
    _request_config(request, "workday")
    _check_public_dns(request.careers_url, "workday", request.careers_url)
    api_url, _ = _ats._workday_endpoints(request.careers_url)
    jobs: list[dict[str, Any]] = []
    seen: set[str] = set()
    offset = 0
    while len(jobs) < request.max_jobs:
        try:
            _check_public_dns(api_url, "workday", request.careers_url)
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


def _acquire_gem(request: ScannerRequest) -> list[dict[str, Any]]:
    deadline = time.monotonic() + request.timeout_seconds
    try:
        config = _request_config(request, "gem")
        _check_public_dns(request.careers_url, "gem", request.careers_url)
        api_url = _ats.build_gem_api_url(request.careers_url)
        _check_public_dns(api_url, "gem", request.careers_url)
        board_slug = str(config["board_slug"])
        list_query = "query JobBoardList($boardId: String!) { oatsExternalJobPostings(boardId: $boardId) { jobPostings { id extId title locations { id name city isoCountry isRemote extId } job { id locationType employmentType } } } }"
        payload = _ats._fetch_json(api_url, math.ceil(_remaining_timeout(deadline, "gem", request.careers_url)), body={"query": list_query, "variables": {"boardId": board_slug}})
        postings = (((payload.get("data") or {}).get("oatsExternalJobPostings") or {}).get("jobPostings"))
        if not isinstance(postings, list):
            raise ValueError("Gem payload must contain data.oatsExternalJobPostings.jobPostings")
        detail_query = "query ExternalJobPosting($boardId: String!, $extId: String!) { oatsExternalJobPosting(boardId: $boardId, extId: $extId) { title descriptionHtml extId firstPublishedTsSec locations { id extId name city isoCountry isRemote } job { id locationType employmentType } } }"
        selected: list[dict[str, Any]] = []
        for row in postings:
            if not isinstance(row, dict) or not _ats._matches(str(row.get("title") or ""), request.keywords):
                continue
            ext_id = str(row.get("extId") or "")
            detail_payload = _ats._fetch_json(api_url, math.ceil(_remaining_timeout(deadline, "gem", request.careers_url)), body={"query": detail_query, "variables": {"boardId": board_slug, "extId": ext_id}})
            detail = ((detail_payload.get("data") or {}).get("oatsExternalJobPosting"))
            if isinstance(detail, dict):
                selected.append({**row, "detail": detail})
            if len(selected) >= request.max_jobs:
                break
        return _ats.parse_gem_jobs({"data": {"oatsExternalJobPostings": {"jobPostings": selected}}}, company_name=request.company_name, careers_url=request.careers_url, keywords=request.keywords)
    except JobSourceError:
        raise
    except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
        raise _mapped_provider_error("gem", request.careers_url, exc) from exc


PROVIDERS: dict[str, ProviderDefinition] = {
    "personio": ProviderDefinition("personio", "Personio", _is_personio, _acquire_personio),
    "greenhouse": ProviderDefinition(
        "greenhouse", "Greenhouse", _is_greenhouse, _acquire_greenhouse
    ),
    "ashby": ProviderDefinition("ashby", "Ashby", _is_ashby, _acquire_ashby),
    "lever": ProviderDefinition("lever", "Lever", _is_lever, _acquire_lever),
    "workday": ProviderDefinition("workday", "Workday", _is_workday, _acquire_workday),
    "gem": ProviderDefinition("gem", "Gem", _is_gem, _acquire_gem),
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
