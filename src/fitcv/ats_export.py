"""Greenhouse and Workday provider parsing and transport helpers."""

from __future__ import annotations

import json
import re
import ssl
from datetime import date, timedelta
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

_GREENHOUSE_HOSTS = {"job-boards.greenhouse.io", "job-boards.eu.greenhouse.io"}
_WORKDAY_HOST = re.compile(r"^(?P<tenant>[\w-]+)\.(?P<instance>wd[\w-]*)\.myworkdayjobs\.com$")
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


def _build_https_opener() -> OpenerDirector:
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=certifi.where())
    return build_opener(_NoRedirect, HTTPSHandler(context=context))


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
    return f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"


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
        raise RuntimeError(f"{url} returned a non-bytes response")
    charset = charset_value if isinstance(charset_value, str) else "utf-8"
    return payload.decode(charset)


def _fetch_text(url: str, timeout_seconds: int) -> str:
    request = Request(
        url,
        headers={"Accept": "text/html", "User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"},
    )
    try:
        with _build_https_opener().open(request, timeout=timeout_seconds) as response:
            return _response_text(response, url)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"failed to fetch {url}: {exc}") from exc


def _fetch_json(
    url: str,
    timeout_seconds: int,
    *,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
        with _build_https_opener().open(request, timeout=timeout_seconds) as response:
            payload = json.loads(_response_text(response, url))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"failed to fetch JSON {url}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"{url} returned non-object JSON")
    return payload


