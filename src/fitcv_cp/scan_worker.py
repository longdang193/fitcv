from __future__ import annotations

import datetime
from typing import Any

from fitcv.job_sources import acquire_scanner_jobs, build_scanner_request
from fitcv.ingest import canonicalize_jobs
from fitcv_cp import sqlite_store


def _published_at(value: Any) -> datetime.datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed.astimezone(datetime.timezone.utc)


def execute_scan(scan_id: str) -> None:
    if not sqlite_store.claim_scan_execution(scan_id):
        return
    try:
        detail = sqlite_store.get_scan_detail(scan_id)
        if detail is None:
            return
        logical_input = dict(detail.get("input") or {})
        titles = [str(value).casefold() for value in logical_input.get("job_titles") or []]
        locations = [str(value).casefold() for value in logical_input.get("locations") or []]
        cutoff = _published_at(detail.get("publication_cutoff"))
        limit = int(logical_input.get("total_rows") or 50)
        jobs: list[dict[str, Any]] = []
        for company in detail.get("company_snapshots") or []:
            current = sqlite_store.get_scan_detail(scan_id)
            if current and current.get("execution_status") == "cancelling":
                sqlite_store.cancel_scan_execution(scan_id)
                return
            request = build_scanner_request(
                provider=str(company["provider_id"]),
                company_name=str(company["company_name"]),
                careers_url=str(company["careers_url"]),
                keywords=tuple(logical_input.get("job_titles") or []),
                max_jobs=max(1, limit - len(jobs)),
                timeout_seconds=60,
            )
            for job in acquire_scanner_jobs(request).artifact.jobs:
                if titles and not any(value in str(job.get("title") or "").casefold() for value in titles):
                    continue
                if locations and not any(value in str(job.get("location") or "").casefold() for value in locations):
                    continue
                published = _published_at(job.get("publishedAt"))
                if cutoff and (published is None or published < cutoff):
                    continue
                jobs.append(job)
                if len(jobs) >= limit:
                    break
            if len(jobs) >= limit:
                break
        sqlite_store.commit_scan_output(scan_id, output_json=canonicalize_jobs(jobs).json_text)
    except Exception as exc:
        sqlite_store.fail_scan_execution(
            scan_id,
            error_code=getattr(exc, "code", "scan_execution_failed"),
            error_message=str(exc),
        )
        raise
