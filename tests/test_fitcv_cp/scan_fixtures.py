from __future__ import annotations

import copy
import datetime
import hashlib
import json
import threading
import time
import uuid
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from fitcv_cp.app import create_app
from fitcv_cp.scan_contracts import derive_scan_capabilities


def _utc(value: str) -> str:
    return f"2026-08-02T{value}+00:00"


def _jobs() -> list[dict[str, Any]]:
    templates = [
        {
            "jobUrl": "https://jobs.example/acme/data-engineer",
            "title": "Data Engineer",
            "companyName": "Acme Analytics",
            "description": "Build reliable data products and pipelines.",
            "contractType": "Full-time",
            "experienceLevel": "Mid-Senior",
            "location": "Berlin, Germany",
            "publishedAt": "2026-08-01T09:00:00Z",
            "companyUrl": "https://www.acme.example",
            "applyUrl": "https://jobs.example/acme/data-engineer/apply",
        },
        {
            "jobUrl": "https://jobs.example/acme/analytics-engineer",
            "title": "Analytics Engineer",
            "companyName": "Acme Analytics",
            "description": "Own metrics, models, and trusted reporting layers.",
            "contractType": "Full-time",
            "experienceLevel": "Mid-level",
            "location": "Remote, Germany",
            "publishedAt": "2026-07-31T11:30:00Z",
            "companyUrl": "https://www.acme.example",
            "applyUrl": "https://jobs.example/acme/analytics-engineer/apply",
        },
    ]
    return [
        {
            **templates[index % len(templates)],
            "jobUrl": f"https://jobs.example/mock/job-{index + 1}",
            "applyUrl": f"https://jobs.example/mock/job-{index + 1}/apply",
        }
        for index in range(38)
    ]


class MockScenarioRequest(BaseModel):
    scenario: str


class MockScanBackend:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            now = _utc("10:00:00")
            self.companies = {
                "company-personio": {
                    "company_id": "company-personio",
                    "company_name": "Acme Analytics",
                    "careers_url": "https://acme.jobs.personio.com/",
                    "provider_id": "personio",
                    "provider_label": "Personio",
                    "row_revision": 1,
                    "created_at": now,
                    "updated_at": now,
                },
                "company-greenhouse": {
                    "company_id": "company-greenhouse",
                    "company_name": "Green Labs",
                    "careers_url": "https://boards.greenhouse.io/greenlabs/",
                    "provider_id": "greenhouse",
                    "provider_label": "Greenhouse",
                    "row_revision": 1,
                    "created_at": now,
                    "updated_at": now,
                },
                "company-workday": {
                    "company_id": "company-workday",
                    "company_name": "Workday Demo",
                    "careers_url": "https://demo.wd3.myworkdayjobs.com/jobs/",
                    "provider_id": "workday",
                    "provider_label": "Workday",
                    "row_revision": 1,
                    "created_at": now,
                    "updated_at": now,
                },
            }
            self.outputs: dict[str, str] = {
                "scan-1048": json.dumps(_jobs(), ensure_ascii=False, separators=(",", ":")),
                "scan-1044": "[]",
                "scan-0940": json.dumps(_jobs()[:1], ensure_ascii=False, separators=(",", ":")),
            }
            self.scans = {
                "scan-1048": self._scan(
                    "scan-1048", "Germany data roles", "succeeded", "active", 2, _utc("09:45:00"), output_count=38
                ),
                "scan-1047": self._scan(
                    "scan-1047", "Berlin platform roles", "running", "active", 2, _utc("09:30:00"), progress=(1, 3)
                ),
                "scan-1046": self._scan(
                    "scan-1046", "Workday data roles", "failed", "active", 1, _utc("09:15:00"), failure_code="provider_http_error"
                ),
                "scan-1045": self._scan(
                    "scan-1045", "Cancelled test", "cancelled", "active", 1, _utc("09:00:00")
                ),
                "scan-1044": self._scan(
                    "scan-1044", "No recent matches", "succeeded", "active", 1, _utc("08:45:00"), output_count=0
                ),
                "scan-1043": self._scan(
                    "scan-1043", "Cancellation pending", "cancelling", "active", 1, _utc("08:30:00"), progress=(1, 1)
                ),
                "scan-0940": self._scan(
                    "scan-0940", "Archived successful scan", "succeeded", "archived", 1, _utc("08:00:00"), output_count=1, referenced=True
                ),
                "scan-0939": self._scan(
                    "scan-0939", "Archived failed scan", "failed", "archived", 1, _utc("07:45:00"), failure_code="provider_timeout"
                ),
            }
            self.actions: dict[tuple[str, str], dict[str, Any]] = {}
            self.fail_next_scan_list = False
            self.delay_next_company_list = False
            self.preview_revision = "mock-preview-1"
            self.next_scan_number = 2000

    def _scan(
        self,
        scan_id: str,
        name: str,
        status: str,
        lifecycle: str,
        company_count: int,
        created_at: str,
        *,
        output_count: int | None = None,
        progress: tuple[int, int] = (0, 0),
        failure_code: str | None = None,
        referenced: bool = False,
    ) -> dict[str, Any]:
        input_data = {
            "scan_name": name,
            "company_ids": list(self.companies)[:company_count],
            "job_titles": ["Data Engineer"],
            "locations": ["Germany"],
            "published_window": "past_7_days",
            "total_rows": 50,
        }
        resource = {
            "scan_id": scan_id,
            "scan_name": name,
            "execution_status": status,
            "lifecycle": lifecycle,
            "row_revision": 1,
            "created_at": created_at,
            "started_at": created_at if status != "queued" else None,
            "finished_at": created_at if status in {"succeeded", "failed", "cancelled"} else None,
            "company_count": company_count,
            "output_record_count": output_count,
            "progress_completed": progress[0],
            "progress_total": progress[1],
            "failure_code": failure_code,
            "failure_message": "Provider request failed safely." if failure_code else None,
            "input": input_data,
            "company_snapshots": [copy.deepcopy(self.companies[company_id]) for company_id in input_data["company_ids"]],
            "output_integrity_valid": status == "succeeded",
            "referenced_by_run": referenced,
            "warnings": [],
        }
        return self._project(resource)

    def _project(self, resource: dict[str, Any]) -> dict[str, Any]:
        output = self.outputs.get(resource["scan_id"])
        if output is not None:
            raw = output.encode("utf-8")
            resource["output_manifest"] = {
                "sha256": hashlib.sha256(raw).hexdigest(),
                "byte_length": len(raw),
                "record_count": resource.get("output_record_count") or 0,
            }
        else:
            resource["output_manifest"] = None
        resource["capabilities"] = derive_scan_capabilities(
            execution_status=resource["execution_status"],
            lifecycle=resource["lifecycle"],
            output_manifest_exists=output is not None,
            output_integrity_valid=bool(resource.get("output_integrity_valid")),
            output_record_count=resource.get("output_record_count"),
            cancellation_requested=bool(resource.get("cancel_requested_at")),
            referenced_by_run=bool(resource.get("referenced_by_run")),
        ).model_dump()
        return resource

    def query_tracked_companies(self, *, search: str = "", page: int = 1, page_size: int = 20) -> dict[str, Any]:
        if self.delay_next_company_list:
            self.delay_next_company_list = False
            time.sleep(1.2)
        needle = search.casefold()
        rows = [
            copy.deepcopy(row)
            for row in self.companies.values()
            if not needle
            or needle in row["company_name"].casefold()
            or needle in row["provider_id"].casefold()
            or needle in row["careers_url"].casefold()
        ]
        return {"items": rows[(page - 1) * page_size : page * page_size], "total": len(rows)}

    def create_tracked_company(self, **verified: Any) -> dict[str, Any]:
        with self._lock:
            if any(row["careers_url"] == verified["careers_url"] for row in self.companies.values()):
                raise ValueError("tracked_company_url_conflict")
            company_id = f"company-{uuid.uuid4().hex[:8]}"
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            resource = {"company_id": company_id, **verified, "row_revision": 1, "created_at": now, "updated_at": now}
            self.companies[company_id] = resource
            return copy.deepcopy(resource)

    def create_scan(self, *, request: dict[str, Any], rerun_of_scan_id: str | None = None, **_kwargs: Any) -> dict[str, Any]:
        with self._lock:
            missing = [company_id for company_id in request.get("company_ids", []) if company_id not in self.companies]
            if missing:
                raise ValueError("tracked_company_unavailable")
            self.next_scan_number += 1
            scan_id = f"scan-{self.next_scan_number}"
            name = str(request.get("scan_name") or f"Scan {self.next_scan_number}")
            resource = self._scan(
                scan_id,
                name,
                "queued",
                "active",
                len(request["company_ids"]),
                datetime.datetime.now(datetime.timezone.utc).isoformat(),
            )
            resource["input"] = copy.deepcopy(request)
            resource["rerun_of_scan_id"] = rerun_of_scan_id
            self.scans[scan_id] = resource
            return copy.deepcopy(resource)

    def query_scans(
        self,
        *,
        lifecycle: str,
        execution_status: str | None = None,
        usable_for_run: bool | None = None,
        search: str = "",
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        if self.fail_next_scan_list:
            self.fail_next_scan_list = False
            raise RuntimeError("mock_scan_list_failure")
        needle = search.casefold()
        rows = []
        for resource in self.scans.values():
            projected = self._project(resource)
            if projected["lifecycle"] != lifecycle:
                continue
            if execution_status and projected["execution_status"] != execution_status:
                continue
            if usable_for_run is not None and projected["capabilities"]["use_for_run"] is not usable_for_run:
                continue
            if needle and needle not in projected["scan_id"].casefold() and needle not in projected["scan_name"].casefold():
                continue
            rows.append(copy.deepcopy(projected))
        rows.sort(key=lambda row: (row["created_at"], row["scan_id"]), reverse=True)
        return {"items": rows[(page - 1) * page_size : page * page_size], "total": len(rows)}

    def get_scan_detail(self, scan_id: str) -> dict[str, Any] | None:
        resource = self.scans.get(scan_id)
        return copy.deepcopy(self._project(resource)) if resource is not None else None

    def request_scan_cancel(self, scan_id: str, *, expected_revision: int | None = None) -> dict[str, Any]:
        with self._lock:
            resource = self.scans.get(scan_id)
            if resource is None:
                raise ValueError("scan_not_found")
            if expected_revision is not None and expected_revision != resource["row_revision"]:
                raise ValueError("scan_revision_conflict")
            if not resource["capabilities"]["cancel"]:
                raise ValueError("scan_not_cancellable")
            resource["execution_status"] = "cancelling"
            resource["cancel_requested_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            resource["row_revision"] += 1
            return copy.deepcopy(self._project(resource))

    def commit_scan_output(self, scan_id: str, *, output_json: str) -> dict[str, Any]:
        jobs = json.loads(output_json)
        self.outputs[scan_id] = output_json
        resource = self.scans[scan_id]
        resource["execution_status"] = "succeeded"
        resource["output_record_count"] = len(jobs)
        resource["output_integrity_valid"] = True
        resource["row_revision"] += 1
        return copy.deepcopy(self._project(resource))

    def get_scan_output(self, scan_id: str) -> dict[str, Any] | None:
        resource = self.scans.get(scan_id)
        if resource is None:
            return None
        output = self.outputs.get(scan_id)
        if output is None:
            raise ValueError("scan_output_not_ready" if resource["execution_status"] in {"queued", "running", "cancelling"} else "scan_output_unavailable")
        raw = output.encode("utf-8")
        if not resource.get("output_integrity_valid"):
            raise ValueError("scan_output_integrity_failed")
        return {"output_json": output, "sha256": hashlib.sha256(raw).hexdigest(), "byte_length": len(raw)}

    def query_scan_jobs(self, scan_id: str, *, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        output = self.get_scan_output(scan_id)
        if output is None:
            raise ValueError("scan_not_found")
        jobs = json.loads(output["output_json"])
        return {"items": jobs[(page - 1) * page_size : page * page_size], "total": len(jobs)}

    def transition_scan_lifecycle(self, items: list[dict[str, Any]], *, target: str) -> dict[str, Any]:
        with self._lock:
            resources: list[dict[str, Any]] = []
            for item in items:
                resource = self.scans.get(item["scan_id"])
                if resource is None:
                    raise ValueError("scan_not_found")
                if resource["row_revision"] != item["expected_revision"]:
                    raise ValueError("scan_revision_conflict")
                capability = "archive" if target == "archived" else "unarchive"
                if not resource["capabilities"][capability]:
                    raise ValueError(f"scan_not_{capability}able")
                resources.append(resource)
            for resource in resources:
                resource["lifecycle"] = target
                resource["row_revision"] += 1
                self._project(resource)
            return {"items": [copy.deepcopy(resource) for resource in resources]}

    def preview_delete_archived_scans(self, scan_ids: list[str]) -> dict[str, Any]:
        eligible: list[str] = []
        referenced: list[dict[str, Any]] = []
        blocked: list[str] = []
        missing: list[str] = []
        for scan_id in scan_ids:
            resource = self.scans.get(scan_id)
            if resource is None:
                missing.append(scan_id)
            elif resource.get("referenced_by_run"):
                referenced.append({"scan_id": scan_id, "run_count": 1})
            elif resource["capabilities"]["delete"]:
                eligible.append(scan_id)
            else:
                blocked.append(scan_id)
        self.preview_revision = f"mock-preview-{uuid.uuid4().hex[:8]}"
        return {
            "requested_scan_ids": list(scan_ids),
            "eligible_scan_ids": eligible,
            "referenced_scan_ids": referenced,
            "blocked_scan_ids": blocked,
            "missing_scan_ids": missing,
            "preview_revision": self.preview_revision,
        }

    def delete_archived_scans(self, scan_ids: list[str], *, preview_revision: str) -> dict[str, Any]:
        if preview_revision != self.preview_revision:
            raise ValueError("delete_preview_stale")
        preview = self.preview_delete_archived_scans(scan_ids)
        if preview["referenced_scan_ids"] or preview["blocked_scan_ids"] or preview["missing_scan_ids"]:
            raise ValueError("delete_preview_stale")
        for scan_id in preview["eligible_scan_ids"]:
            self.scans.pop(scan_id, None)
            self.outputs.pop(scan_id, None)
        return {"deleted_count": len(preview["eligible_scan_ids"]), "deleted_scan_ids": preview["eligible_scan_ids"]}

    def reserve_idempotent_action(self, scope: str, key: str, fingerprint: str) -> dict[str, Any]:
        with self._lock:
            action_key = (scope, key)
            action = self.actions.get(action_key)
            if action is not None:
                if action["fingerprint"] != fingerprint:
                    raise ValueError("idempotency_conflict")
                return {"action_id": action["action_id"], "replayed": True, "response": copy.deepcopy(action.get("response"))}
            action = {"action_id": f"action-{uuid.uuid4().hex}", "fingerprint": fingerprint, "response": None}
            self.actions[action_key] = action
            return {"action_id": action["action_id"], "replayed": False, "response": None}

    def complete_idempotent_action(self, action_id: str, response: dict[str, Any]) -> None:
        with self._lock:
            for action in self.actions.values():
                if action["action_id"] == action_id:
                    action["response"] = copy.deepcopy(response)
                    return
        raise KeyError(action_id)

    def get_process_events(self, process_type: str, process_id: str, *, limit: int = 200, cursor: str | None = None) -> dict[str, Any]:
        if process_type != "scan" or process_id not in self.scans:
            return {"events": [], "integrity_conflicts": [], "deliveries": [], "total_count": 0, "next_cursor": None}
        resource = self.scans[process_id]
        events = [
            {
                "event_id": f"{process_id}-requested",
                "process_type": "scan",
                "process_id": process_id,
                "operation": "registry_resolution",
                "state": "requested",
                "level": "info",
                "message": "Scan request accepted.",
                "recorded_at": resource["created_at"],
            }
        ]
        if resource["execution_status"] != "queued":
            events.append(
                {
                    "event_id": f"{process_id}-progress",
                    "process_type": "scan",
                    "process_id": process_id,
                    "operation": "company_retrieval",
                    "state": "progress",
                    "level": "info",
                    "message": f"Processed {resource.get('progress_completed') or resource.get('company_count')} of {resource.get('progress_total') or resource.get('company_count')} companies.",
                    "recorded_at": resource["created_at"],
                }
            )
        return {"events": events[:limit], "integrity_conflicts": [], "deliveries": [], "total_count": len(events), "next_cursor": None}

    def get_candidate_profile(self, profile_id: str) -> dict[str, Any] | None:
        return {"profile_id": profile_id, "name": "Mock Candidate", "revision": 1, "is_active": True, "profile": {}}

    def query_candidate_profiles(self, **_kwargs: Any) -> dict[str, Any]:
        return {
            "items": [
                {
                    "profile_id": "profile-1",
                    "profile_name": "Mock Candidate",
                    "display_name": "Mock Candidate",
                    "original_filename": "mock-candidate.yaml",
                    "creation_status": "succeeded",
                    "lifecycle": "active",
                    "created_at": _utc("08:00:00"),
                    "updated_at": _utc("08:00:00"),
                    "archived_at": None,
                    "profile_revision_id": "profile-revision-1",
                    "failure": None,
                    "related_run_count": 0,
                    "capabilities": {"inspect": True, "archive": True, "restore": False, "use_for_run": True},
                    "revision": 1,
                }
            ],
            "total": 1,
        }

    def apply_scenario(self, scenario: str) -> dict[str, Any]:
        if scenario == "reset":
            self.reset()
        elif scenario == "empty":
            self.scans.clear()
            self.outputs.clear()
        elif scenario == "empty_registry":
            self.companies.clear()
        elif scenario == "list_error":
            self.fail_next_scan_list = True
        elif scenario == "delayed":
            self.delay_next_company_list = True
        elif scenario == "integrity":
            self.scans["scan-1048"]["output_integrity_valid"] = False
            self._project(self.scans["scan-1048"])
        elif scenario == "pending":
            self.scans = {"scan-1047": self.scans["scan-1047"]}
            self.outputs.clear()
        elif scenario == "terminal":
            self.scans = {scan_id: scan for scan_id, scan in self.scans.items() if scan["execution_status"] in {"succeeded", "failed", "cancelled"}}
        else:
            raise ValueError("unknown_mock_scenario")
        return {"scenario": scenario}


def install_mock_scan_store(app: FastAPI, backend: MockScanBackend) -> None:
    store = app.state.run_store
    store.query_tracked_companies_fn = backend.query_tracked_companies
    store.create_tracked_company_fn = backend.create_tracked_company
    store.create_scan_fn = backend.create_scan
    store.query_scans_fn = backend.query_scans
    store.get_scan_detail_fn = backend.get_scan_detail
    store.request_scan_cancel_fn = backend.request_scan_cancel
    store.commit_scan_output_fn = backend.commit_scan_output
    store.get_scan_output_fn = backend.get_scan_output
    store.query_scan_jobs_fn = backend.query_scan_jobs
    store.transition_scan_lifecycle_fn = backend.transition_scan_lifecycle
    store.preview_delete_archived_scans_fn = backend.preview_delete_archived_scans
    store.delete_archived_scans_fn = backend.delete_archived_scans
    store.reserve_idempotent_action_fn = backend.reserve_idempotent_action
    store.complete_idempotent_action_fn = backend.complete_idempotent_action
    store.get_process_events_fn = backend.get_process_events
    store.get_candidate_profile_fn = backend.get_candidate_profile
    store.query_candidate_profiles_fn = backend.query_candidate_profiles
    app.state.enqueue_scan = lambda scan_id: f"mock:{scan_id}"
    app.state.managed_run_result_fn = lambda sources: {
        "run_id": f"mock-run-{uuid.uuid4().hex[:8]}",
        "status": "queued",
        "jobs_input_manifest": {"sources": sources},
        "warnings": [],
    }


def create_mock_app() -> FastAPI:
    app = create_app(redis_url="redis://127.0.0.1:6379/0")
    backend = MockScanBackend()
    install_mock_scan_store(app, backend)
    app.state.scan_mock_backend = backend

    @app.post("/__mock__/scenario", include_in_schema=False)
    def set_mock_scenario(body: MockScenarioRequest) -> dict[str, Any]:
        return {"data": backend.apply_scenario(body.scenario)}

    return app
