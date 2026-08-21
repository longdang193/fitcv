from __future__ import annotations

import datetime
from typing import Any

from fitcv.job_sources import acquire_scanner_jobs, build_scanner_request
from fitcv.ingest import canonicalize_jobs
from fitcv_cp import sqlite_store
from fitcv_cp.models import build_process_event

def _emit_scan_event(
    scan_id: str, operation: str, state: str, message: str, payload: dict[str, Any] | None = None
) -> None:
    try:
        sqlite_store.append_process_event(
            build_process_event(
                process_type="scan",
                process_id=scan_id,
                operation=operation,
                state=state,
                level="info" if state not in {"failed", "cancelled"} else "warning",
                message=message,
                payload=payload,
            )
        )
    except Exception:
        pass


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


def execute_scan(scan_id: str, job_id: str | None = None) -> None:
    _ = job_id
    if not sqlite_store.claim_scan_execution(scan_id):
        return
    _emit_scan_event(scan_id, "claim", "started", "Scan worker claimed execution.")
    claim_id = sqlite_store.get_scan_claim_id(scan_id)
    if not claim_id:
        sqlite_store.fail_scan_execution(
            scan_id,
            error_code="scan_claim_missing",
            error_message="Scan claim was not persisted.",
        )
        _emit_scan_event(scan_id, "claim", "failed", "Scan claim was not persisted.")
        return
    try:
        detail = sqlite_store.get_scan_detail(scan_id)
        if detail is None:
            raise RuntimeError("scan_not_found")
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
            if not sqlite_store.update_scan_heartbeat(scan_id, claim_id=claim_id):
                raise RuntimeError("scan_claim_lost")
            remaining_rows = limit - len(jobs)
            if remaining_rows <= 0:
                break
            request = build_scanner_request(
                provider=str(company["provider_id"]),
                company_name=str(company["company_name"]),
                careers_url=str(company["careers_url"]),
                keywords=tuple(logical_input.get("job_titles") or []),
                max_jobs=min(remaining_rows, 200),
                timeout_seconds=60,
            )
            _emit_scan_event(
                scan_id,
                "provider",
                "started",
                "Provider acquisition started.",
                {"company_id": company["company_id"], "max_jobs": request.max_jobs},
            )
            acquired_jobs = acquire_scanner_jobs(request).artifact.jobs
            current = sqlite_store.get_scan_detail(scan_id)
            if current and current.get("execution_status") == "cancelling":
                sqlite_store.cancel_scan_execution(scan_id)
                _emit_scan_event(scan_id, "cancel", "cancelled", "Scan cancelled before output commit.")
                return
            if not sqlite_store.update_scan_heartbeat(scan_id, claim_id=claim_id):
                raise RuntimeError("scan_claim_lost")
            for job in acquired_jobs:
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
        current = sqlite_store.get_scan_detail(scan_id)
        if current and current.get("execution_status") == "cancelling":
            sqlite_store.cancel_scan_execution(scan_id)
            _emit_scan_event(scan_id, "cancel", "cancelled", "Scan cancelled before output commit.")
            return
        sqlite_store.commit_scan_output(scan_id, output_json=canonicalize_jobs(jobs).json_text)
        _emit_scan_event(
            scan_id,
            "output",
            "succeeded",
            "Scan output committed.",
            {"record_count": len(jobs)},
        )
    except Exception as exc:
        sqlite_store.fail_scan_execution(
            scan_id,
            error_code=getattr(exc, "code", "scan_execution_failed"),
            error_message=str(exc),
        )
        _emit_scan_event(scan_id, "execution", "failed", "Scan execution failed.", {"error": str(exc)})
        raise
