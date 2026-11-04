"""Download workingstudentjobs.de jobs into FitCV's upload format."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import ssl
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import certifi


API_URL = "https://www.workingstudentjobs.de/api/v1/jobs"
USER_AGENT = "FitCV workingstudentjobs.de importer/1.0"


def _ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=certifi.where())
    return context


def _open_url(request: Request, *, timeout: float) -> Any:
    return urlopen(request, timeout=timeout, context=_ssl_context())


def _string(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _join_values(values: Any, separator: str = ", ") -> str:
    if not isinstance(values, list):
        return ""
    return separator.join(_string(value) for value in values if _string(value))


def _label(value: Any) -> str:
    return _string(value).replace("_", " ").replace("-", " ").title()


def _format_location(location: Any) -> str:
    if not isinstance(location, dict):
        return ""
    parts = [location.get("city"), location.get("state"), location.get("country_code")]
    return ", ".join(_string(part) for part in parts if _string(part))


def _format_salary(salary: Any) -> str:
    if not isinstance(salary, dict):
        return ""
    minimum = salary.get("min")
    maximum = salary.get("max")
    currency = _string(salary.get("currency"))
    period = _label(salary.get("period"))
    if minimum is None and maximum is None:
        return ""
    if minimum is not None and maximum is not None:
        amount = f"{minimum}-{maximum}"
    elif minimum is not None:
        amount = f"{minimum}+"
    else:
        amount = f"up to {maximum}"
    return " ".join(part for part in (amount, currency, f"per {period.lower()}" if period else "") if part)


def _format_range(value: Any, unit: str) -> str:
    if not isinstance(value, dict):
        return ""
    minimum = value.get("min")
    maximum = value.get("max")
    if minimum is None and maximum is None:
        return ""
    if minimum is not None and maximum is not None:
        return f"{minimum}-{maximum} {unit}"
    if minimum is not None:
        return f"{minimum}+ {unit}"
    return f"up to {maximum} {unit}"


def build_structured_summary(job: dict[str, Any]) -> str:
    details = job.get("details") if isinstance(job.get("details"), dict) else {}
    languages = job.get("languages") if isinstance(job.get("languages"), dict) else {}
    types = job.get("types") if isinstance(job.get("types"), list) else []
    lines = [
        "Structured job summary from workingstudentjobs.de; the full posting text is used when available.",
        f"Job type: {_join_values([_label(value) for value in types])}",
        f"Field: {_label(job.get('field'))}",
        f"Sub-field: {_label(job.get('sub_field'))}",
        f"Working mode: {_label(job.get('working_mode'))}",
        f"Location: {_format_location(job.get('location'))}",
        f"Salary: {_format_salary(job.get('salary'))}",
        f"Skills: {_join_values(job.get('skills'))}",
        f"German: {_label(languages.get('german'))}",
        f"English: {_label(languages.get('english'))}",
        f"Study fields: {_join_values(details.get('study_fields'))}",
        f"Study levels: {_join_values(details.get('study_levels'))}",
        f"Hours per week: {_format_range(details.get('hours_per_week'), 'hours')}",
        f"Duration: {_format_range(details.get('duration_months'), 'months')}",
        f"Benefits: {_join_values(details.get('benefits'))}",
        f"Prior experience: {_label(details.get('prior_experience'))}",
    ]
    return "\n".join(line for line in lines if line.rsplit(": ", 1)[-1])


def _html_to_text(value: str) -> str:
    text = re.sub(r"(?is)<br\s*/?>", "\n", value)
    text = re.sub(r"(?is)</(?:p|div|li|h[1-6])\s*>", "\n", text)
    text = re.sub(r"(?is)<li\b[^>]*>", "• ", text)
    text = re.sub(r"(?is)<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_job_posting_json_ld(page_html: str) -> dict[str, Any] | None:
    pattern = re.compile(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(page_html):
        try:
            payload = json.loads(html.unescape(match.group(1).strip()))
        except json.JSONDecodeError:
            continue
        candidates = payload if isinstance(payload, list) else [payload]
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            types = candidate.get("@type")
            if types == "JobPosting" or isinstance(types, list) and "JobPosting" in types:
                return candidate
    return None


def _request_bytes(url: str, timeout: float, opener: Callable[..., Any] = _open_url) -> bytes:
    request = Request(url, headers={"Accept": "text/html,application/json", "User-Agent": USER_AGENT})
    try:
        with opener(request, timeout=timeout) as response:
            return response.read()
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code} for {url}: {body[:300]}") from error
    except URLError as error:
        raise RuntimeError(f"Request failed for {url}: {error.reason}") from error


def fetch_api_page(url: str, timeout: float, opener: Callable[..., Any] = _open_url, sleep: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    while True:
        request = Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
        try:
            with opener(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code == 429:
                retry_after = _string(error.headers.get("Retry-After")) or "60"
                sleep(float(retry_after))
                continue
            body = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {error.code} for {url}: {body[:300]}") from error
        except (URLError, json.JSONDecodeError) as error:
            raise RuntimeError(f"API request failed for {url}: {error}") from error
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise RuntimeError(f"Unexpected API response for {url}")
        return payload


def build_api_url(args: argparse.Namespace) -> str:
    params: dict[str, str | int] = {"limit": args.page_size, "ref": args.ref}
    for name in ("city", "field", "job_type", "language", "remote", "since"):
        value = getattr(args, name)
        if value:
            params["type" if name == "job_type" else name] = value
    return f"{API_URL}?{urlencode(params)}"


def fetch_all_jobs(
    first_url: str,
    timeout: float,
    max_jobs: int = 0,
    opener: Callable[..., Any] = _open_url,
    sleep: Callable[[float], None] = time.sleep,
) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    seen: set[str] = set()
    next_url: str | None = first_url
    while next_url:
        page = fetch_api_page(next_url, timeout, opener=opener, sleep=sleep)
        for job in page["data"]:
            if not isinstance(job, dict):
                continue
            identity = _string(job.get("id")) or _string(job.get("url"))
            if identity and identity in seen:
                continue
            if identity:
                seen.add(identity)
            jobs.append(job)
            if max_jobs and len(jobs) >= max_jobs:
                return jobs
        links = page.get("links")
        next_url = links.get("next") if isinstance(links, dict) else None
    return jobs


def job_to_fitcv_record(job: dict[str, Any], page_record: dict[str, Any] | None = None) -> dict[str, Any]:
    company = job.get("company") if isinstance(job.get("company"), dict) else {}
    location = job.get("location") if isinstance(job.get("location"), dict) else {}
    details = page_record or {}
    description = _html_to_text(_string(details.get("description"))) or build_structured_summary(job)
    types = [_label(value) for value in job.get("types", [])] if isinstance(job.get("types"), list) else []
    study_levels = job.get("details", {}).get("study_levels", []) if isinstance(job.get("details"), dict) else []
    record = {
        "id": _string(job.get("id")),
        "jobUrl": _string(job.get("url")),
        "title": _string(job.get("title")),
        "companyName": _string(company.get("name")),
        "companyUrl": _string(company.get("url")),
        "companyId": _string(company.get("slug")),
        "companyWebsite": _string(company.get("website_domain")),
        "description": description,
        "postedTime": _string(job.get("posted_at")),
        "publishedAt": _string(job.get("posted_at"))[:10],
        "location": _format_location(location),
        "contractType": ", ".join(types),
        "experienceLevel": ", ".join(_string(value) for value in study_levels),
        "workType": _label(job.get("working_mode")),
        "sector": _string(job.get("field")),
        "salary": _format_salary(job.get("salary")),
        "applyUrl": _string(details.get("applyLink")) or _string(job.get("apply_url")),
        "applyType": "EXTERNAL",
        "source": "workingstudentjobs",
        "sourceJobId": _string(job.get("id")),
        "sourceDescription": "job_page_json_ld" if details.get("description") else "api_structured_summary",
        "sourceRecord": job,
    }
    if page_record:
        record["sourcePageRecord"] = page_record
    return record


def write_json_array(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as temporary_file:
            json.dump(records, temporary_file, ensure_ascii=False, indent=2)
            temporary_file.write("\n")
            temporary_path = Path(temporary_file.name)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/workingstudentjobs.json"))
    parser.add_argument("--ref", default="fitcv")
    parser.add_argument("--page-size", type=int, default=300, choices=range(1, 301))
    parser.add_argument("--max-jobs", type=int, default=0, help="Stop after this many jobs; 0 means all jobs.")
    parser.add_argument("--city", help="Comma-separated city slugs.")
    parser.add_argument("--field", help="Comma-separated fields.")
    parser.add_argument("--type", dest="job_type", help="working_student, internship, or both.")
    parser.add_argument("--language", choices=("en", "de"))
    parser.add_argument("--remote", help="Comma-separated working modes.")
    parser.add_argument("--since", help="ISO 8601 lower bound for first_seen_at.")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--detail-delay", type=float, default=1.0)
    parser.add_argument("--no-details", action="store_true", help="Do not fetch job pages; not recommended for FitCV.")
    parser.add_argument("--require-details", action="store_true", help="Fail if a job page or description cannot be fetched.")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.max_jobs < 0 or args.detail_delay < 0 or args.timeout <= 0:
        raise SystemExit("--max-jobs must be >= 0; --detail-delay must be >= 0; --timeout must be > 0")
    jobs = fetch_all_jobs(build_api_url(args), args.timeout, max_jobs=args.max_jobs)
    records: list[dict[str, Any]] = []
    detail_failures = 0
    for index, job in enumerate(jobs, start=1):
        page_record: dict[str, Any] | None = None
        if not args.no_details and _string(job.get("url")):
            try:
                page_html = _request_bytes(_string(job["url"]), args.timeout).decode("utf-8", errors="replace")
                page_record = extract_job_posting_json_ld(page_html)
                if page_record is None:
                    raise RuntimeError("JobPosting JSON-LD not found")
            except RuntimeError as error:
                detail_failures += 1
                print(f"warning: detail fetch failed for {_string(job.get('id'))}: {error}", file=sys.stderr)
                if args.require_details:
                    raise SystemExit(1) from error
            if index < len(jobs) and args.detail_delay:
                time.sleep(args.detail_delay)
        records.append(job_to_fitcv_record(job, page_record))
    write_json_array(args.output, records)
    print(f"wrote {len(records)} jobs to {args.output}")
    if detail_failures:
        print(f"warning: {detail_failures} jobs use API structured summaries instead of full descriptions", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
