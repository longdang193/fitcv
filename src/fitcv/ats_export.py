"""ATS provider parsing and transport helpers."""

from __future__ import annotations

import json
import ipaddress
import re
import socket
import ssl
from datetime import date, timedelta
from http.client import HTTPSConnection
from html.parser import HTMLParser
from typing import Any, Callable, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import (
    HTTPSHandler,
    HTTPRedirectHandler,
    OpenerDirector,
    Request,
    build_opener,
)

import certifi

from fitcv.ingest import validate_linkedin_schema

_GREENHOUSE_HOSTS = {"boards.greenhouse.io", "job-boards.greenhouse.io", "job-boards.eu.greenhouse.io"}
_ASHBY_HOST = "jobs.ashbyhq.com"
_LEVER_HOSTS = {"jobs.lever.co", "jobs.eu.lever.co"}
_WORKDAY_HOST = re.compile(r"^(?P<tenant>[\w-]+)\.(?P<instance>wd[\w-]*)\.myworkdayjobs\.com$")
_GEM_HOST = "jobs.gem.com"
_BLOCK_TAGS = {"br", "div", "h1", "h2", "h3", "h4", "li", "ol", "p", "ul"}
_PAGE_SIZE = 20


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag == "li":
            self.parts.append("\n- ")
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


class _MetaDescriptionParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.description = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "meta" or self.description:
            return
        values = {key.lower(): value or "" for key, value in attrs}
        if values.get("property", "").lower() == "og:description":
            self.description = values.get("content", "").strip()


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: object,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> None:
        del req, fp, code, msg, headers, newurl
        return None


class RedirectRejectedError(RuntimeError):
    pass


class ProviderSSRFError(RuntimeError):
    pass


class _PinnedHTTPSConnection(HTTPSConnection):
    def __init__(self, host: str, pinned_address: str, **kwargs: Any) -> None:
        kwargs.pop("check_hostname", None)
        super().__init__(host, **kwargs)
        self._pinned_address = pinned_address

    def connect(self) -> None:
        self.sock = socket.create_connection((self._pinned_address, self.port), self.timeout, self.source_address)
        if self._tunnel_host:
            self._tunnel()
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self._tunnel_host or self.host)


class _PinnedHTTPSHandler(HTTPSHandler):
    def __init__(self, context: ssl.SSLContext, pinned_address: str) -> None:
        super().__init__(context=context)
        self._pinned_address = pinned_address
        self._check_hostname = context.check_hostname

    def https_open(self, request: Request) -> Any:
        return self.do_open(
            lambda host, **kwargs: _PinnedHTTPSConnection(host, self._pinned_address, **kwargs),
            request,
            context=self._context,
            check_hostname=self._check_hostname,
        )


def _resolve_public_address(url: str) -> str:
    hostname = urlsplit(url).hostname or ""
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise ProviderSSRFError("provider host must not be an IP literal")
    try:
        answers = socket.getaddrinfo(
            hostname,
            443,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
    except OSError as exc:
        raise ProviderSSRFError("provider host DNS validation failed") from exc
    if not answers:
        raise ProviderSSRFError("provider host DNS validation failed")
    addresses: list[str] = []
    for answer in answers:
        address = ipaddress.ip_address(answer[4][0])
        if address.version == 6 and address.ipv4_mapped is not None:
            address = address.ipv4_mapped
        if not address.is_global:
            raise ProviderSSRFError("provider host DNS validation failed")
        addresses.append(str(address))
    return addresses[0]


def _build_https_opener(pinned_address: str) -> OpenerDirector:
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=certifi.where())
    return build_opener(_NoRedirect, _PinnedHTTPSHandler(context, pinned_address))


def _html_to_text(value: str) -> str:
    parser = _TextParser()
    parser.feed(value)
    lines = (" ".join(line.split()) for line in "".join(parser.parts).splitlines())
    return "\n".join(line for line in lines if line)


def _experience_from_title(title: str) -> str:
    lowered = title.casefold()
    for keyword, label in (
        ("principal", "Principal"),
        ("lead", "Lead"),
        ("senior", "Senior"),
        ("junior", "Junior"),
        ("intern", "Intern"),
    ):
        if keyword in lowered:
            return label
    return ""


def _matches(title: str, keywords: Sequence[str]) -> bool:
    normalized = tuple(keyword.strip().casefold() for keyword in keywords if keyword.strip())
    return not normalized or any(keyword in title.casefold() for keyword in normalized)


def _validate_job(job: dict[str, str]) -> None:
    errors = validate_linkedin_schema(job)
    if errors:
        raise ValueError(f"exported job violates FitCV contract: {', '.join(errors)}")


def build_greenhouse_api_url(careers_url: str) -> str:
    parsed = urlsplit(careers_url)
    hostname = (parsed.hostname or "").lower()
    slug = parsed.path.strip("/").split("/", 1)[0]
    if parsed.scheme != "https" or hostname not in _GREENHOUSE_HOSTS or not slug:
        raise ValueError("careers URL must be an HTTPS Greenhouse job-board URL")
    if parsed.username or parsed.password or parsed.port:
        raise ValueError("Greenhouse careers URL must not contain credentials or a custom port")
    if len(parsed.path.strip("/").split("/")) != 1 or parsed.query or parsed.fragment:
        raise ValueError("Greenhouse careers URL path is invalid")
    return f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"


def build_ashby_api_url(careers_url: str) -> str:
    parsed = urlsplit(careers_url)
    slug = parsed.path.strip("/")
    if (
        parsed.scheme != "https"
        or parsed.hostname != _ASHBY_HOST
        or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,119}", slug)
        or parsed.username
        or parsed.password
        or parsed.port
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("careers URL must be an HTTPS Ashby job-board URL")
    return f"https://api.ashbyhq.com/posting-api/job-board/{slug}"


def build_lever_api_url(careers_url: str) -> str:
    parsed = urlsplit(careers_url)
    slug = parsed.path.strip("/")
    if (
        parsed.scheme != "https"
        or parsed.hostname not in _LEVER_HOSTS
        or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,119}", slug)
        or parsed.username
        or parsed.password
        or parsed.port
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("careers URL must be an HTTPS Lever job-board URL")
    return f"https://api.lever.co/v0/postings/{slug}?mode=json"


def build_gem_api_url(careers_url: str) -> str:
    parsed = urlsplit(careers_url)
    slug = parsed.path.strip("/")
    if (
        parsed.scheme != "https"
        or parsed.hostname != _GEM_HOST
        or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,119}", slug)
        or parsed.username
        or parsed.password
        or parsed.port
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("careers URL must be an HTTPS Gem job-board URL")
    return f"https://{_GEM_HOST}/api/public/graphql"


def _metadata_value(metadata: Any, name: str) -> str:
    if not isinstance(metadata, list):
        return ""
    for item in metadata:
        if not isinstance(item, dict) or str(item.get("name") or "").casefold() != name.casefold():
            continue
        value = item.get("value")
        if isinstance(value, list):
            return ", ".join(str(entry).strip() for entry in value if str(entry).strip())
        return str(value or "").strip()
    return ""


def parse_greenhouse_jobs(
    payload: dict[str, Any],
    *,
    company_name: str,
    careers_url: str,
    keywords: Sequence[str] = (),
) -> list[dict[str, str]]:
    build_greenhouse_api_url(careers_url)
    if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
        raise ValueError("Greenhouse payload must contain a jobs array")
    rows = payload.get("jobs")
    jobs: list[dict[str, str]] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").strip()
        job_url = str(row.get("absolute_url") or "").strip()
        description = _html_to_text(str(row.get("content") or ""))
        if not title or not job_url or not description or not _matches(title, keywords):
            continue
        location = row.get("location")
        location_text = str(location.get("name") or "") if isinstance(location, dict) else ""
        first_published = str(row.get("first_published") or "")
        metadata = row.get("metadata")
        job = {
            "title": title,
            "location": location_text,
            "publishedAt": first_published[:10]
            if re.match(r"^\d{4}-\d{2}-\d{2}", first_published)
            else "",
            "jobUrl": job_url,
            "companyName": company_name,
            "companyUrl": careers_url.rstrip("/"),
            "description": description,
            "contractType": _metadata_value(metadata, "Type of Employment"),
            "experienceLevel": _experience_from_title(title),
            "workType": _metadata_value(metadata, "Team"),
            "applyUrl": job_url,
            "applyType": "EXTERNAL",
            "source": "career-ops:greenhouse",
            "greenhouseId": str(row.get("id") or ""),
        }
        _validate_job(job)
        jobs.append(job)
    return jobs


def _date_from_epoch(value: Any) -> str:
    try:
        timestamp = float(value)
    except (TypeError, ValueError):
        return ""
    if timestamp > 10_000_000_000:
        timestamp /= 1000
    try:
        return date.fromtimestamp(timestamp).isoformat()
    except (OverflowError, OSError, ValueError):
        return ""


def parse_ashby_jobs(
    payload: dict[str, Any],
    *,
    company_name: str,
    careers_url: str,
    keywords: Sequence[str] = (),
) -> list[dict[str, str]]:
    build_ashby_api_url(careers_url)
    if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
        raise ValueError("Ashby payload must contain a jobs array")
    jobs: list[dict[str, str]] = []
    for row in payload["jobs"]:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").strip()
        job_id = str(row.get("id") or "").strip()
        job_url = str(row.get("jobUrl") or row.get("applyUrl") or "").strip()
        if not job_url and job_id:
            slug = urlsplit(careers_url).path.strip("/")
            job_url = f"https://jobs.ashbyhq.com/{slug}/{job_id}"
        description = str(row.get("descriptionPlain") or "").strip()
        if not description:
            description = _html_to_text(str(row.get("descriptionHtml") or ""))
        if not title or not job_url or not description or not _matches(title, keywords):
            continue
        location = row.get("location")
        location_text = str(location.get("name") or "") if isinstance(location, dict) else str(location or "")
        job = {
            "title": title,
            "location": location_text,
            "publishedAt": str(row.get("publishedAt") or "")[:10],
            "jobUrl": job_url,
            "companyName": company_name,
            "companyUrl": careers_url.rstrip("/"),
            "description": description,
            "contractType": str(row.get("employmentType") or ""),
            "experienceLevel": _experience_from_title(title),
            "workType": "Remote" if row.get("isRemote") is True else "",
            "applyUrl": str(row.get("applyUrl") or job_url),
            "applyType": "EXTERNAL",
            "source": "career-ops:ashby",
            "ashbyId": job_id,
        }
        _validate_job(job)
        jobs.append(job)
    return jobs


def parse_lever_jobs(
    payload: list[dict[str, Any]],
    *,
    company_name: str,
    careers_url: str,
    keywords: Sequence[str] = (),
) -> list[dict[str, str]]:
    build_lever_api_url(careers_url)
    if not isinstance(payload, list):
        raise ValueError("Lever payload must be an array")
    jobs: list[dict[str, str]] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        title = str(row.get("text") or "").strip()
        job_id = str(row.get("id") or "").strip()
        categories = row.get("categories") if isinstance(row.get("categories"), dict) else {}
        job_url = str(row.get("hostedUrl") or row.get("applyUrl") or "").strip()
        description = str(row.get("descriptionPlain") or "").strip()
        if not description:
            description = _html_to_text(str(row.get("description") or ""))
        if not title or not job_url or not description or not _matches(title, keywords):
            continue
        job = {
            "title": title,
            "location": str(categories.get("location") or ""),
            "publishedAt": _date_from_epoch(row.get("createdAt")),
            "jobUrl": job_url,
            "companyName": company_name,
            "companyUrl": careers_url.rstrip("/"),
            "description": description,
            "contractType": str(categories.get("commitment") or ""),
            "experienceLevel": _experience_from_title(title),
            "workType": str(categories.get("workplaceType") or ""),
            "applyUrl": str(row.get("applyUrl") or job_url),
            "applyType": "EXTERNAL",
            "source": "career-ops:lever",
            "leverId": job_id,
        }
        _validate_job(job)
        jobs.append(job)
    return jobs


def parse_gem_jobs(
    payload: dict[str, Any],
    *,
    company_name: str,
    careers_url: str,
    keywords: Sequence[str] = (),
) -> list[dict[str, str]]:
    build_gem_api_url(careers_url)
    postings = (((payload.get("data") or {}).get("oatsExternalJobPostings") or {}).get("jobPostings"))
    if not isinstance(payload, dict) or not isinstance(postings, list):
        raise ValueError("Gem payload must contain data.oatsExternalJobPostings.jobPostings")
    slug = urlsplit(careers_url).path.strip("/")
    jobs: list[dict[str, str]] = []
    for row in postings:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").strip()
        ext_id = str(row.get("extId") or "").strip()
        detail = row.get("detail") if isinstance(row.get("detail"), dict) else row
        description = _html_to_text(str(detail.get("descriptionHtml") or detail.get("description") or ""))
        job_url = f"https://{_GEM_HOST}/{slug}/{ext_id}" if ext_id else ""
        locations = row.get("locations") or detail.get("locations")
        location_text = ", ".join(str(item.get("name") or "").strip() for item in locations if isinstance(item, dict) and str(item.get("name") or "").strip()) if isinstance(locations, list) else ""
        job = detail.get("job") if isinstance(detail.get("job"), dict) else row.get("job")
        if not isinstance(job, dict):
            job = {}
        if not title or not ext_id or not job_url or not description or not _matches(title, keywords):
            continue
        job_data = {
            "title": title,
            "location": location_text,
            "publishedAt": _date_from_epoch(detail.get("firstPublishedTsSec")),
            "jobUrl": job_url,
            "companyName": company_name,
            "companyUrl": careers_url.rstrip("/"),
            "description": description,
            "contractType": str(job.get("employmentType") or ""),
            "experienceLevel": _experience_from_title(title),
            "workType": str(job.get("locationType") or "").replace("_", " ").title(),
            "applyUrl": job_url,
            "applyType": "EXTERNAL",
            "source": "career-ops:gem",
            "gemId": ext_id,
        }
        _validate_job(job_data)
        jobs.append(job_data)
    return jobs


def _workday_endpoints(careers_url: str) -> tuple[str, str]:
    parsed = urlsplit(careers_url)
    hostname = (parsed.hostname or "").lower()
    match = _WORKDAY_HOST.fullmatch(hostname)
    parts = [part for part in parsed.path.split("/") if part]
    if parts and re.fullmatch(r"[a-z]{2}-[A-Z]{2}", parts[0]):
        parts.pop(0)
    if parsed.scheme != "https" or match is None or not parts:
        raise ValueError("careers URL must be an HTTPS Workday site URL")
    if parsed.username or parsed.password or parsed.port:
        raise ValueError("Workday careers URL must not contain credentials or a custom port")
    if len(parts) != 1 or parsed.query or parsed.fragment:
        raise ValueError("Workday careers URL path is invalid")
    tenant = match.group("tenant")
    site = parts[0]
    origin = urlunsplit(("https", hostname, "", "", ""))
    return f"{origin}/wday/cxs/{tenant}/{site}/jobs", f"{origin}/{site}"


def _workday_date(posted_on: str, today: date) -> str:
    if re.search(r"posted\s+today", posted_on, re.IGNORECASE):
        return today.isoformat()
    if re.search(r"posted\s+yesterday", posted_on, re.IGNORECASE):
        return (today - timedelta(days=1)).isoformat()
    match = re.search(r"posted\s+(\d+)(\+?)\s+day", posted_on, re.IGNORECASE)
    if match and not match.group(2):
        return (today - timedelta(days=int(match.group(1)))).isoformat()
    return ""


def _meta_description(html_text: str) -> str:
    parser = _MetaDescriptionParser()
    parser.feed(html_text)
    return parser.description


def parse_workday_jobs(
    payload: dict[str, Any],
    *,
    company_name: str,
    careers_url: str,
    keywords: Sequence[str] = (),
    today: date | None = None,
    description_loader: Callable[[str], str] | None = None,
) -> list[dict[str, str]]:
    _, job_base = _workday_endpoints(careers_url)
    rows = payload.get("jobPostings")
    jobs: list[dict[str, str]] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").strip()
        external_path = str(row.get("externalPath") or "").strip()
        if not title or not external_path.startswith("/job/") or not _matches(title, keywords):
            continue
        job_url = f"{job_base}{external_path}"
        page_html = description_loader(job_url) if description_loader is not None else ""
        description = _meta_description(page_html)
        if not description:
            continue
        job = {
            "title": title,
            "location": str(row.get("locationsText") or ""),
            "publishedAt": _workday_date(str(row.get("postedOn") or ""), today or date.today()),
            "jobUrl": job_url,
            "companyName": company_name,
            "companyUrl": careers_url.rstrip("/"),
            "description": description,
            "contractType": str(row.get("timeType") or ""),
            "experienceLevel": _experience_from_title(title),
            "workType": "",
            "applyUrl": job_url,
            "applyType": "EXTERNAL",
            "source": "career-ops:workday",
            "workdayId": ", ".join(str(value) for value in row.get("bulletFields", [])),
        }
        _validate_job(job)
        jobs.append(job)
    return jobs


def _response_text(response: Any, url: str) -> str:
    payload = response.read()
    charset_value = response.headers.get_content_charset()
    if not isinstance(payload, bytes):
        raise RuntimeError("provider returned a non-bytes response")
    charset = charset_value if isinstance(charset_value, str) else "utf-8"
    return payload.decode(charset)


def _fetch_text(url: str, timeout_seconds: int) -> str:
    request = Request(
        url,
        headers={"Accept": "text/html", "User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"},
    )
    try:
        with _build_https_opener(_resolve_public_address(url)).open(request, timeout=timeout_seconds) as response:
            if response.headers.get("Location"):
                raise RedirectRejectedError("provider redirect rejected")
            return _response_text(response, url)
    except HTTPError as exc:
        if 300 <= exc.code <= 399:
            raise RedirectRejectedError("provider redirect rejected") from exc
        raise RuntimeError("provider HTTP request failed") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError("provider request failed") from exc


def _fetch_json(
    url: str,
    timeout_seconds: int,
    *,
    body: dict[str, Any] | None = None,
) -> Any:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    try:
        with _build_https_opener(_resolve_public_address(url)).open(request, timeout=timeout_seconds) as response:
            if response.headers.get("Location"):
                raise RedirectRejectedError("provider redirect rejected")
            payload = json.loads(_response_text(response, url))
    except HTTPError as exc:
        if 300 <= exc.code <= 399:
            raise RedirectRejectedError("provider redirect rejected") from exc
        raise RuntimeError("provider HTTP request failed") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError("provider JSON request failed") from exc
    return payload

