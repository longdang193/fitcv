"""Fetch, normalize, and deduplicate jobs from approved sources."""

from __future__ import annotations

import argparse
import copy
import hashlib
import html
import json
import os
import re
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from fitcv.ingest import validate_job_schema

try:
    import scripts.fetch_workingstudentjobs as workingstudentjobs
except ModuleNotFoundError:
    import fetch_workingstudentjobs as workingstudentjobs


APIFY_API_BASE = "https://api.apify.com/v2"
SUPPORTED_SOURCES = ("workingstudentjobs", "linkedin", "indeed")
SOURCE_PRIORITY = {source: index for index, source in enumerate(("linkedin", "workingstudentjobs", "indeed"))}
TERMINAL_STATUSES = {"SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"}
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in",
    "is", "it", "of", "on", "or", "that", "the", "this", "to", "with",
}


class FetchError(RuntimeError):
    """Raised when a source cannot produce a safe result."""


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def resolve_env(name: str, file_values: dict[str, str]) -> str:
    return os.environ.get(name, file_values.get(name, ""))


def load_source_config(config_dir: Path, source: str) -> dict[str, Any]:
    path = config_dir / f"{source}.json"
    if not path.exists():
        raise FetchError(f"Missing source configuration: {path}")
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise FetchError(f"Invalid source configuration: {path}: {error.msg}") from error
    if not isinstance(config, dict) or config.get("source") != source:
        raise FetchError(f"Source configuration identity mismatch: {path}")
    return config


def load_source_configs(config_dir: Path) -> dict[str, dict[str, Any]]:
    return {source: load_source_config(config_dir, source) for source in SUPPORTED_SOURCES if (config_dir / f"{source}.json").exists()}


def _redact(value: str, token: str) -> str:
    return value.replace(token, "[REDACTED]") if token and len(token) >= 8 else value


def request_json(
    method: str,
    url: str,
    token: str,
    payload: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> Any:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")[:300]
        raise FetchError(_redact(f"Apify HTTP {error.code}: {body}", token)) from error
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise FetchError(_redact(f"Apify request failed: {error}", token)) from error


def _data(value: Any) -> Any:
    if isinstance(value, dict) and "data" in value:
        return value["data"]
    return value


def run_apify_actor(
    actor_id: str,
    input_payload: dict[str, Any],
    token: str,
    *,
    timeout_secs: int = 120,
    poll_timeout_secs: int = 150,
    poll_interval_secs: float = 2.0,
    max_items: int | None = None,
    request: Callable[..., Any] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    if request is None:
        request = request_json
    actor_path = actor_id.replace("/", "~")
    query = {"timeout": str(timeout_secs), "format": "json"}
    if max_items:
        query["maxItems"] = str(max_items)
    start_url = f"{APIFY_API_BASE}/acts/{actor_path}/runs?{urlencode(query)}"
    started = _data(request("POST", start_url, token, payload=input_payload, timeout=30.0))
    if not isinstance(started, dict) or not started.get("id"):
        raise FetchError("Apify start response did not include a run id")
    run_id = str(started["id"])
    status = str(started.get("status") or "RUNNING")
    deadline = time.monotonic() + poll_timeout_secs
    run = started
    while status not in TERMINAL_STATUSES:
        now = time.monotonic()
        if now >= deadline:
            request("PUT", f"{APIFY_API_BASE}/actor-runs/{quote(run_id, safe='~')}/abort", token, timeout=30.0)
            raise FetchError(f"Apify run {run_id} exceeded client deadline")
        sleep(max(0.0, min(poll_interval_secs, deadline - now)))
        run = _data(request("GET", f"{APIFY_API_BASE}/actor-runs/{quote(run_id, safe='~')}", token, timeout=30.0))
        if not isinstance(run, dict):
            raise FetchError(f"Apify run {run_id} returned malformed status")
        status = str(run.get("status") or "")
    if status != "SUCCEEDED":
        raise FetchError(f"Apify run {run_id} ended with status {status}")
    dataset_id = str(run.get("defaultDatasetId") or "")
    if not dataset_id:
        raise FetchError(f"Apify run {run_id} succeeded without a default dataset")
    dataset = _data(request("GET", f"{APIFY_API_BASE}/datasets/{quote(dataset_id, safe='~')}/items?format=json&clean=true", token, timeout=30.0))
    if not isinstance(dataset, list) or not all(isinstance(item, dict) for item in dataset):
        raise FetchError(f"Apify dataset {dataset_id} returned malformed items")
    return {"runId": run_id, "datasetId": dataset_id, "items": dataset}


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _html_to_text(value: str) -> str:
    text = re.sub(r"(?is)<br\s*/?>", "\n", value)
    text = re.sub(r"(?is)</(?:p|div|li|h[1-6])\s*>", "\n", text)
    text = re.sub(r"(?is)<li\b[^>]*>", "• ", text)
    text = re.sub(r"(?is)<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _description_status(description: str, source_description: str) -> str:
    normalized = description.strip()
    if source_description == "api_structured_summary":
        return "fallback_summary"
    if not normalized:
        return "missing"
    if normalized.casefold() in {"description not available", "n/a", "not available", "apply now"}:
        return "partial"
    if len(normalized) < 80:
        return "partial"
    return "full"


def _location_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if not isinstance(value, dict):
        return ""
    parts = [value.get("city"), value.get("admin1Name"), value.get("region"), value.get("countryName"), value.get("country")]
    return ", ".join(_text(part) for part in parts if _text(part))


def _company_details(value: Any) -> tuple[str, str]:
    if isinstance(value, dict):
        return _text(value.get("name") or value.get("companyName")), _text(value.get("url") or value.get("companyUrl"))
    return _text(value), ""


def _date_value(raw: dict[str, Any]) -> str:
    return _text(raw.get("publishedAt") or raw.get("datePublished") or raw.get("datePosted"))[:10]


def _canonical_record(
    raw: dict[str, Any],
    *,
    source: str,
    source_job_id: str,
    job_url: str,
    apply_url: str,
    title: str,
    company_name: str,
    company_url: str,
    location: str,
    description: str,
    source_description: str,
    contract_type: str = "",
    experience_level: str = "",
    run_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = {
        "id": source_job_id,
        "jobUrl": job_url,
        "title": title,
        "companyName": company_name,
        "companyUrl": company_url,
        "location": location,
        "postedTime": _text(raw.get("postedTime") or raw.get("dateOnIndeed") or raw.get("datePosted")),
        "publishedAt": _date_value(raw),
        "description": description,
        "contractType": contract_type,
        "experienceLevel": experience_level,
        "workType": _text(raw.get("workType")),
        "sector": _text(raw.get("sector")),
        "applyType": _text(raw.get("applyType")) or "EXTERNAL",
        "applyUrl": apply_url,
        "source": source,
        "sourceJobId": source_job_id,
        "sourceDescription": source_description,
        "descriptionStatus": _description_status(description, source_description),
        "sourceRecord": raw,
    }
    if isinstance(raw.get("descriptionHtml"), str):
        record["descriptionHtml"] = raw["descriptionHtml"]
    if run_meta:
        record["sourceRunId"] = _text(run_meta.get("runId"))
        record["sourceDatasetId"] = _text(run_meta.get("datasetId"))
    return record


def linkedin_to_fitcv_record(raw: dict[str, Any], run_meta: dict[str, Any] | None) -> dict[str, Any]:
    description = _text(raw.get("description"))
    source_description = "description"
    if not description and _text(raw.get("descriptionHtml")):
        description = _html_to_text(_text(raw["descriptionHtml"]))
        source_description = "descriptionHtml"
    company_name, company_url = _company_details(raw.get("employer"))
    company_name = _text(raw.get("companyName")) or company_name
    company_url = _text(raw.get("companyUrl")) or company_url
    source_job_id = _text(raw.get("id") or raw.get("jobId") or raw.get("jobUrl"))
    return _canonical_record(
        raw,
        source="linkedin",
        source_job_id=source_job_id,
        job_url=_text(raw.get("jobUrl") or raw.get("url")),
        apply_url=_text(raw.get("applyUrl") or raw.get("applicationUrl")),
        title=_text(raw.get("title")),
        company_name=company_name,
        company_url=company_url,
        location=_location_text(raw.get("location")),
        description=description,
        source_description=source_description,
        contract_type=_text(raw.get("contractType")),
        experience_level=_text(raw.get("experienceLevel")),
        run_meta=run_meta,
    )


def indeed_to_fitcv_record(raw: dict[str, Any], run_meta: dict[str, Any] | None) -> dict[str, Any]:
    description_value = raw.get("description")
    description = _text(description_value.get("text")) if isinstance(description_value, dict) else _text(description_value)
    company_name, company_url = _company_details(raw.get("employer"))
    source_job_id = _text(raw.get("key") or raw.get("refNum") or raw.get("id") or raw.get("url"))
    job_types = raw.get("jobTypes")
    if isinstance(job_types, dict):
        contract_type = ", ".join(_text(value) for value in job_types.values() if _text(value))
    elif isinstance(job_types, list):
        contract_type = ", ".join(_text(value) for value in job_types if _text(value))
    else:
        contract_type = _text(job_types)
    return _canonical_record(
        raw,
        source="indeed",
        source_job_id=source_job_id,
        job_url=_text(raw.get("url")),
        apply_url=_text(raw.get("jobUrl") or raw.get("url")),
        title=_text(raw.get("title")),
        company_name=company_name,
        company_url=company_url,
        location=_location_text(raw.get("location")),
        description=description,
        source_description="description",
        contract_type=contract_type,
        run_meta=run_meta,
    )


def _workingstudent_args(request: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        ref=_text(request.get("ref") or "fitcv"),
        page_size=int(request.get("pageSize") or 100),
        city=request.get("city"),
        field=request.get("field"),
        job_type=request.get("type"),
        language=request.get("language"),
        remote=request.get("remote"),
        since=request.get("since"),
    )


def fetch_workingstudentjobs_source(config: dict[str, Any], max_records: int = 0) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    request_config = config.get("request") or config.get("input") or {}
    details = config.get("details") if isinstance(config.get("details"), dict) else {}
    max_jobs = int(request_config.get("maxJobs") or 0)
    if max_records:
        max_jobs = min(max_jobs or max_records, max_records)
    args = _workingstudent_args(request_config)
    jobs = workingstudentjobs.fetch_all_jobs(
        workingstudentjobs.build_api_url(args),
        float(details.get("timeout") or 30),
        max_jobs=max_jobs,
    )
    records: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    delay = float(details.get("delay") or 0)
    for index, job in enumerate(jobs):
        page_record = None
        try:
            page_url = _text(job.get("url"))
            if page_url:
                page_html = workingstudentjobs._request_bytes(page_url, float(details.get("timeout") or 30)).decode("utf-8", errors="replace")
                page_record = workingstudentjobs.extract_job_posting_json_ld(page_html)
            if not page_record or not _text(page_record.get("description")):
                raise FetchError("missing full description")
        except (FetchError, RuntimeError) as error:
            failures.append({"sourceJobId": _text(job.get("id") or job.get("url")), "reason": "missing_full_description"})
            if index < len(jobs) - 1 and delay:
                time.sleep(delay)
            continue
        record = workingstudentjobs.job_to_fitcv_record(job, page_record)
        record["descriptionStatus"] = "full"
        records.append(record)
        if index < len(jobs) - 1 and delay:
            time.sleep(delay)
    return records[:max_records] if max_records else records, failures


def _smoke_config(config: dict[str, Any], source: str, max_records: int) -> tuple[dict[str, Any], int | None]:
    if not max_records:
        return copy.deepcopy(config), None
    bounded = copy.deepcopy(config)
    if source == "linkedin":
        bounded["input"]["rows"] = min(int(bounded["input"].get("rows") or max_records), max_records)
        for key in ("titles", "locations"):
            values = bounded["input"].get(key)
            if isinstance(values, list) and values:
                bounded["input"][key] = values[:1]
        return bounded, max_records
    if source == "indeed":
        bounded["input"]["limit"] = min(int(bounded["input"].get("limit") or max_records), max_records)
        return bounded, max_records
    bounded.setdefault("request", {})["maxJobs"] = min(int(bounded.get("request", {}).get("maxJobs") or max_records), max_records)
    bounded.setdefault("details", {})["require"] = True
    return bounded, max_records


def fetch_sources(
    configs: dict[str, dict[str, Any]],
    sources: list[str],
    token: str,
    *,
    max_records_per_source: int = 0,
    run_timeout_secs: int = 120,
    poll_timeout_secs: int = 150,
    request: Callable[..., Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, str]], dict[str, dict[str, Any]]]:
    if request is None:
        request = request_json
    records: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    runs: dict[str, dict[str, Any]] = {}
    for source in sources:
        if source not in SUPPORTED_SOURCES:
            raise FetchError(f"Unsupported source: {source}")
        if source not in configs:
            raise FetchError(f"Missing source configuration: {source}")
        config, bounded_limit = _smoke_config(configs[source], source, max_records_per_source)
        if source == "workingstudentjobs":
            source_records, source_failures = fetch_workingstudentjobs_source(config, bounded_limit or 0)
            records.extend(source_records)
            failures.extend(source_failures)
            continue
        if not token:
            raise FetchError("APIFY_API_TOKEN is required for Apify sources")
        run_config = config.get("run") if isinstance(config.get("run"), dict) else {}
        configured_max_items = run_config.get("maxItems")
        run_max_items = int(configured_max_items) if configured_max_items else None
        result = run_apify_actor(
            _text(config.get("actor")),
            config.get("input") if isinstance(config.get("input"), dict) else {},
            token,
            timeout_secs=run_timeout_secs,
            poll_timeout_secs=poll_timeout_secs,
            poll_interval_secs=float(run_config.get("pollIntervalSecs") or 2),
            max_items=run_max_items,
            request=request,
        )
        runs[source] = {"runId": result["runId"], "datasetId": result["datasetId"], "started": 1}
        mapper = linkedin_to_fitcv_record if source == "linkedin" else indeed_to_fitcv_record
        mapped = [mapper(item, result) for item in result["items"] if isinstance(item, dict)]
        incomplete = [record for record in mapped if record["descriptionStatus"] != "full"]
        failures.extend({"sourceJobId": record["sourceJobId"], "reason": "incomplete_description"} for record in incomplete)
        records.extend(record for record in mapped if record["descriptionStatus"] == "full")
        if bounded_limit:
            records = records[:]
            source_records = [record for record in records if record["source"] == source]
            if len(source_records) > bounded_limit:
                remove_ids = {record["sourceJobId"] for record in source_records[bounded_limit:]}
                records = [record for record in records if not (record["source"] == source and record["sourceJobId"] in remove_ids)]
    return records, failures, runs


def _normalized_url(value: Any) -> str:
    raw = _text(value)
    if not raw:
        return ""
    parts = urlsplit(raw)
    return urlunsplit((parts.scheme.casefold(), parts.netloc.casefold(), parts.path.rstrip("/"), parts.query, ""))


def record_identity(record: dict[str, Any]) -> str:
    source = _text(record.get("source")) or "unknown"
    source_job_id = _text(record.get("sourceJobId")) or _normalized_url(record.get("jobUrl"))
    return f"{source}:{source_job_id}"


def description_tokens(description: str) -> set[str]:
    tokens = re.findall(r"[^\W_]+", _html_to_text(description).casefold(), flags=re.UNICODE)
    return {token for token in tokens if len(token) >= 2 and token not in STOPWORDS}


def description_intersection_rate(left: str, right: str) -> float:
    left_tokens = description_tokens(left)
    right_tokens = description_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))


def _published_sort_value(record: dict[str, Any]) -> tuple[int, int]:
    value = _text(record.get("publishedAt"))
    if not value:
        return (1, 0)
    try:
        return (0, datetime.fromisoformat(value[:10]).toordinal())
    except ValueError:
        return (1, 0)


def _record_sort_key(record: dict[str, Any]) -> tuple[Any, ...]:
    missing_date, ordinal = _published_sort_value(record)
    return (
        0 if record.get("descriptionStatus") == "full" else 1,
        missing_date,
        -ordinal,
        SOURCE_PRIORITY.get(_text(record.get("source")), len(SOURCE_PRIORITY)),
        _text(record.get("sourceJobId")),
        _normalized_url(record.get("jobUrl")),
    )


def _bucket_key(record: dict[str, Any]) -> tuple[str, str, str] | None:
    values = tuple(re.sub(r"\W+", " ", _text(record.get(field)).casefold()).strip() for field in ("companyName", "title", "location"))
    return values if all(values) else None


def deduplicate_records(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered = sorted(records, key=_record_sort_key)
    kept: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    exact_seen: dict[str, dict[str, Any]] = {}
    bucket_kept: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for record in ordered:
        exact_keys = [record_identity(record)]
        url = _normalized_url(record.get("jobUrl"))
        if url:
            exact_keys.append(f"url:{url}")
        duplicate = next((exact_seen[key] for key in exact_keys if key in exact_seen), None)
        if duplicate is not None:
            excluded.append({"duplicateOf": record_identity(duplicate), "similarity": 1.0, "source": record.get("source"), "sourceJobId": record.get("sourceJobId"), "jobUrl": record.get("jobUrl"), "reason": "exact_identity"})
            continue
        bucket = _bucket_key(record)
        duplicate = None
        similarity = 0.0
        tokens = description_tokens(_text(record.get("description")))
        if bucket and len(tokens) >= 40:
            for candidate in bucket_kept.get(bucket, []):
                candidate_tokens = description_tokens(_text(candidate.get("description")))
                if len(candidate_tokens) < 40:
                    continue
                candidate_similarity = description_intersection_rate(_text(record.get("description")), _text(candidate.get("description")))
                if candidate_similarity > 0.90:
                    duplicate = candidate
                    similarity = candidate_similarity
                    break
        if duplicate is not None:
            excluded.append({"duplicateOf": record_identity(duplicate), "similarity": similarity, "source": record.get("source"), "sourceJobId": record.get("sourceJobId"), "jobUrl": record.get("jobUrl"), "reason": "description_intersection_gt_0.90"})
            continue
        kept.append(record)
        for key in exact_keys:
            exact_seen[key] = record
        if bucket:
            bucket_kept.setdefault(bucket, []).append(record)
    return kept, excluded


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            handle.write(content)
            temporary = Path(handle.name)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_outputs(output: Path, report_path: Path, records: list[dict[str, Any]], excluded: list[dict[str, Any]], runs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    output_text = json.dumps(records, ensure_ascii=False, indent=2) + "\n"
    run_id = uuid.uuid4().hex
    report = {
        "runId": run_id,
        "outputSha256": hashlib.sha256(output_text.encode("utf-8")).hexdigest(),
        "retained": [record_identity(record) for record in records],
        "excluded": excluded,
        "sourceRuns": runs,
    }
    report_text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    _atomic_write(output, output_text)
    _atomic_write(report_path, report_text)
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("all", *SUPPORTED_SOURCES), default="all")
    parser.add_argument("--config-dir", type=Path, default=Path("config/job_sources"))
    parser.add_argument("--output", type=Path, default=Path("data/jobs.json"))
    parser.add_argument("--dedupe-report", type=Path, default=Path("data/jobs.dedupe.json"))
    parser.add_argument("--max-records-per-source", type=int, default=0)
    parser.add_argument("--run-timeout", type=int, default=120)
    parser.add_argument("--poll-timeout", type=int, default=150)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.max_records_per_source < 0 or args.run_timeout <= 0 or args.poll_timeout <= 0:
        raise SystemExit("record and timeout limits must be positive")
    env_values = load_env_file(Path(".env"))
    token = resolve_env("APIFY_API_TOKEN", env_values)
    selected = list(SUPPORTED_SOURCES) if args.source == "all" else [args.source]
    try:
        configs = load_source_configs(args.config_dir)
        records, failures, runs = fetch_sources(
            configs,
            selected,
            token,
            max_records_per_source=args.max_records_per_source,
            run_timeout_secs=args.run_timeout,
            poll_timeout_secs=args.poll_timeout,
        )
        if failures:
            print(f"warning: excluded {len(failures)} incomplete source records", file=sys.stderr)
        invalid = [(record_identity(record), validate_job_schema(record)) for record in records if validate_job_schema(record)]
        if invalid:
            raise FetchError(f"normalized output failed FitCV schema validation: {invalid[0][0]}")
        kept, excluded = deduplicate_records(records)
        write_outputs(args.output, args.dedupe_report, kept, excluded, runs)
    except FetchError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(f"wrote {len(kept)} jobs to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
