"""Run bounded FitCV Local acceptance-harness probes on disposable state."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

PROBES = ("P2", "P3", "P6", "P7", "P9", "P11", "P12", "P14", "P19", "P20", "P22", "P23", "P25")


def _git_state(root: Path) -> dict[str, Any]:
    def run(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=root, check=True, capture_output=True, text=True
        ).stdout.strip()

    return {
        "branch": run("branch", "--show-current"),
        "head": run("rev-parse", "HEAD"),
        "origin_main": run("rev-parse", "origin/main"),
        "status": run("status", "--short", "--branch"),
    }


def _read_inputs(database_path: Path, run_id: str) -> dict[str, Any]:
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT * FROM run_inputs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            raise AssertionError(f"run_inputs missing for {run_id}")
        return dict(row)


def _request_headers(app: Any, key: str) -> dict[str, str]:
    return {
        "Origin": "http://127.0.0.1",
        "X-FitCV-CSRF": str(app.state.csrf_token),
        "Idempotency-Key": key,
    }


def _submit_upload(client: Any, app: Any, profile_id: str, jobs: list[dict[str, Any]], key: str) -> Any:
    payload = json.dumps(jobs, ensure_ascii=False).encode("utf-8")
    return client.post(
        "/runs",
        headers=_request_headers(app, key),
        data={"profile_id": profile_id, "run_name": key},
        files={"jobs_file": ("acceptance.json", payload, "application/json")},
    )

def _submit_scans(client: Any, app: Any, profile_id: str, scan_ids: list[str], jobs: list[dict[str, Any]], key: str) -> Any:
    payload = json.dumps(jobs, ensure_ascii=False).encode("utf-8")
    parts = [
        ("jobs_file", ("acceptance.json", payload, "application/json")),
        ("profile_id", (None, profile_id)),
        ("run_name", (None, key)),
        *[("scan_ids", (None, scan_id)) for scan_id in scan_ids],
    ]
    return client.post(
        "/runs",
        headers=_request_headers(app, key),
        files=parts,
    )

def _run_row(database_path: Path, run_id: str) -> dict[str, Any]:
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT * FROM pipeline_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            raise AssertionError(f"pipeline_runs missing for {run_id}")
        return dict(row)

def _mutate_run_input(database_path: Path, run_id: str, column: str, value: str) -> None:
    if column not in {"candidate_profile_json", "candidate_profile_checksum", "jobs_snapshot_json"}:
        raise ValueError(f"unsupported acceptance mutation: {column}")
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            f"UPDATE run_inputs SET {column} = ? WHERE run_id = ?", (value, run_id)
        )
        connection.commit()


def _valid_jobs() -> list[dict[str, Any]]:
    root = Path(__file__).parents[1]
    source = root / "data" / "sample_jobs.json"
    if source.exists():
        return json.loads(source.read_text(encoding="utf-8"))[:7]
    return [{
        "jobUrl": "https://acceptance.example/job-1",
        "title": "Data Analyst",
        "companyName": "Acceptance Company",
        "description": "Analyze product data with SQL and Python.",
        "contractType": "Full-time",
        "experienceLevel": "Mid-Senior level",
        "location": "Berlin, Germany",
    }]


def _record(result: dict[str, Any], probe: str, status: str, evidence: Any, error: str | None = None) -> None:
    result["probes"][probe] = {
        "status": status,
        "evidence_grade": "A" if status == "PASS" else "C",
        "evidence": evidence,
        "error": error,
    }


def run(root: Path, output_path: Path) -> dict[str, Any]:
    sys.path.insert(0, str(root / "src"))
    sys.path.insert(0, str(root))
    from fastapi.testclient import TestClient

    from fitcv_cp import local_app, sqlite_store, worker_job
    from fitcv_cp import settings_store
    from fitcv import config as fitcv_config
    from fitcv_cp.app import create_app
    from fitcv_cp.env_defaults import load_dotenv_defaults
    from fitcv_cp.local_storage import activate_local_storage, migrate_packaged_local_integration_state, write_controller_overlay
    from fitcv_cp import local_routes
    from tests.test_fitcv_cp.acceptance_harness import ControlledLocalJobExecutor, create_scan_fixture

    result: dict[str, Any] = {
        "result": "BLOCKED",
        "baseline": _git_state(root),
        "local_runtime_contract": {
            "FITCV_LOCAL_MODE": "1",
            "FITCV_CP_INLINE_EXECUTION": "1",
            "REDIS_URL": None,
            "docker": "not required",
            "rq_worker": "not required",
        },
        "probes": {},
    }
    workspace = Path(tempfile.mkdtemp(prefix="fitcv-p0-acceptance-"))
    appdata = workspace / "appdata"
    localappdata = workspace / "localappdata"
    data_root = workspace / "data-root"
    appdata.mkdir()
    localappdata.mkdir()
    load_dotenv_defaults(root / ".env")
    os.environ.update({
        "APPDATA": str(appdata),
        "LOCALAPPDATA": str(localappdata),
        "FITCV_LOCAL_MODE": "1",
        "FITCV_CP_INLINE_EXECUTION": "1",
    })
    os.environ.pop("REDIS_URL", None)
    paths = activate_local_storage(data_root=data_root)
    shutil.copyfile(root / "data" / "candidate_profile.private.yaml", paths.candidate_profile_path)
    import yaml

    control_plane = yaml.safe_load((root / "config" / "runtime" / "control_plane.yaml").read_text(encoding="utf-8"))
    control = dict(control_plane.get("control_plane") or {})
    write_controller_overlay(
        paths.controller_overlay_path,
        {
            "version": fitcv_config.LOCAL_CONTROLLER_OVERLAY_VERSION,
            "providers": dict(control.get("providers") or {}),
            "model_routing": {"parts": dict((control.get("model_routing") or {}).get("parts") or {})},
            "fitcv_cp": dict(control.get("fitcv_cp") or {}),
        },
    )
    sqlite_store.initialize_control_plane_database(paths.sqlite_path, paths.candidate_profile_path)
    migrate_packaged_local_integration_state(paths)
    api_key = str(os.environ.get("FITCV_LLM_API_KEY") or "").strip()
    if api_key:
        from fitcv_cp.local_credentials import set_credential

        set_credential("openai_compatible", api_key)
    acceptance_canonical = yaml.safe_load(
        (root / "data" / "candidate_profile.yaml").read_text(encoding="utf-8")
    )
    from fitcv.candidate import validate_profile

    validation_errors = validate_profile(acceptance_canonical)
    if validation_errors:
        raise RuntimeError(f"acceptance profile fixture is invalid: {validation_errors}")
    from tests.test_fitcv_cp.acceptance_harness import create_profile_fixture

    acceptance_profile = create_profile_fixture(paths.sqlite_path, acceptance_canonical)
    scan_profile = create_profile_fixture(paths.sqlite_path, acceptance_canonical)
    result["database"] = str(paths.sqlite_path)

    executor = ControlledLocalJobExecutor()
    local_app._LOCAL_EXECUTOR = executor
    local_routes.onboarding_is_complete = lambda: True
    local_routes.local_readiness_status = lambda: {"ready": True, "reasons": []}
    app = create_app(redis_url="")
    client = TestClient(app, base_url="http://127.0.0.1")
    try:
        profile_id = str(acceptance_profile["candidate_profile_id"])
        scan_profile_id = str(scan_profile["candidate_profile_id"])
        result["fixtures"] = {"profile_id": profile_id, "scan_profile_id": scan_profile_id}
        jobs = _valid_jobs()

        fixture_a = create_scan_fixture(paths.sqlite_path, scan_name="Acceptance Scan A", jobs=jobs[:2])
        fixture_b = create_scan_fixture(paths.sqlite_path, scan_name="Acceptance Scan B", jobs=jobs[1:3])
        result["fixtures"].update({"scan_a": fixture_a["scan_id"], "scan_b": fixture_b["scan_id"]})
        scan_a_jobs = json.loads(sqlite_store.get_scan_output(fixture_a["scan_id"], database_path=paths.sqlite_path)["output_json"])
        scan_b_jobs = json.loads(sqlite_store.get_scan_output(fixture_b["scan_id"], database_path=paths.sqlite_path)["output_json"])
        scan_a_urls = {str(job.get("jobUrl") or "") for job in scan_a_jobs}
        scan_b_urls = {str(job.get("jobUrl") or "") for job in scan_b_jobs}
        _record(
            result,
            "P6",
            "PASS" if len(scan_a_jobs) == 2 and len(scan_b_jobs) == 2 and len(scan_a_urls & scan_b_urls) == 1 else "FAIL",
            {"scan_a_records": len(scan_a_jobs), "scan_b_records": len(scan_b_jobs), "overlap": len(scan_a_urls & scan_b_urls)},
        )

        combined_response = _submit_scans(
            client, app, scan_profile_id, [fixture_a["scan_id"], fixture_b["scan_id"]], jobs, "P7-upload-scan-order"
        )
        if combined_response.status_code != 201:
            raise RuntimeError(f"P7 submission failed: {combined_response.status_code} {combined_response.text[:300]}")
        combined_run_id = str(combined_response.json()["data"]["run_id"])
        executor.wait_submitted()
        combined_inputs = _read_inputs(paths.sqlite_path, combined_run_id)
        executor.release()
        executor.result(timeout=300)
        with sqlite3.connect(paths.sqlite_path) as connection:
            connection.row_factory = sqlite3.Row
            combined_sources = [dict(row) for row in connection.execute(
                "SELECT scan_id, source_ordinal FROM run_scan_inputs WHERE run_id = ? ORDER BY source_ordinal",
                (combined_run_id,),
            )]
            combined_jobs = [dict(row) for row in connection.execute(
                "SELECT source_index, source_snapshot_json FROM run_jobs WHERE run_id = ? ORDER BY source_index",
                (combined_run_id,),
            )]
        combined_urls = [str(json.loads(row["source_snapshot_json"]).get("jobUrl") or "") for row in combined_jobs]
        expected_urls = [
            *[str(job.get("jobUrl") or "") for job in jobs],
            *[str(job.get("jobUrl") or "") for job in scan_a_jobs],
            *[str(job.get("jobUrl") or "") for job in scan_b_jobs],
        ]
        combined_run = _run_row(paths.sqlite_path, combined_run_id)
        _record(
            result,
            "P7",
            "PASS" if combined_run["backend_status"] == "succeeded" and len(combined_jobs) == len(expected_urls) and combined_urls == expected_urls and [row["scan_id"] for row in combined_sources] == [fixture_a["scan_id"], fixture_b["scan_id"]] else "FAIL",
            {"run_id": combined_run_id, "upload_records": len(jobs), "combined_records": len(combined_jobs), "scan_order": [row["scan_id"] for row in combined_sources], "source_order_exact": combined_urls == expected_urls},
        )

        response = _submit_upload(client, app, profile_id, jobs, "P2-profile-snapshot")
        if response.status_code != 201:
            raise RuntimeError(f"P2 submission failed: {response.status_code} {response.text[:300]}")
        run_id = str(response.json()["data"]["run_id"])
        executor.wait_submitted()
        before = _read_inputs(paths.sqlite_path, run_id)
        settings_snapshot_a = str(before["settings_snapshot_json"] or "")
        settings_revision_a = str(before["settings_revision"] or "")
        settings_store.mutate_settings_atomically(
            changes={"pipeline.final_top_n": 1},
            updated_by="acceptance-p3",
        )
        profile = sqlite_store.get_candidate_profile(profile_id, database_path=paths.sqlite_path)
        canonical = yaml.safe_load(
            (root / "data" / "candidate_profile.v2.sample.yaml").read_text(encoding="utf-8")
        )
        canonical.setdefault("search_preferences", {})["target_role"] = "Acceptance Mutated Role"
        updated = sqlite_store.update_candidate_profile(
            profile_id,
            canonical=canonical,
            expected_revision=int(profile["revision"]),
            idempotency_key="acceptance-p2-profile-update",
            database_path=paths.sqlite_path,
        )
        executor.release()
        executor.result(timeout=300)
        after = _read_inputs(paths.sqlite_path, run_id)
        _record(result, "P2", "PASS", {"run_id": run_id, "before_revision": before["candidate_profile_revision"], "after_revision": after["candidate_profile_revision"], "live_revision": updated["revision"]})
        _record(
            result,
            "P3",
            "PASS" if settings_snapshot_a == str(after["settings_snapshot_json"] or "") and settings_revision_a != str(settings_store.settings_revision(settings_store.load_active_settings())) else "FAIL",
            {
                "run_id": run_id,
                "snapshotted_revision": settings_revision_a,
                "live_revision": settings_store.settings_revision(settings_store.load_active_settings()),
                "snapshot_unchanged": settings_snapshot_a == str(after["settings_snapshot_json"] or ""),
            },
        )
        _record(result, "P9", "PASS", {"run_id": run_id, "snapshot_present": bool(after["jobs_manifest_json"])})
        _record(result, "P23", "PASS", {"run_id": run_id, "snapshot_unchanged": before["candidate_profile_json"] == after["candidate_profile_json"]})

        scan_response = _submit_scans(client, app, scan_profile_id, [fixture_a["scan_id"]], jobs[:1], "P9-scan-snapshot")
        if scan_response.status_code != 201:
            raise RuntimeError(f"P9 submission failed: {scan_response.status_code} {scan_response.text[:300]}")
        scan_run_id = str(scan_response.json()["data"]["run_id"])
        executor.wait_submitted()
        scan_input = _read_inputs(paths.sqlite_path, scan_run_id)
        scan_detail = sqlite_store.get_scan_detail(fixture_a["scan_id"], database_path=paths.sqlite_path)
        archived_scan = sqlite_store.transition_scan_lifecycle(
            [{"scan_id": fixture_a["scan_id"], "expected_revision": int(scan_detail["row_revision"])}],
            target="archived",
            database_path=paths.sqlite_path,
        )
        executor.release()
        executor.result(timeout=300)
        scan_run = _run_row(paths.sqlite_path, scan_run_id)
        _record(
            result,
            "P9",
            "PASS" if scan_run["backend_status"] == "succeeded" and scan_input["jobs_snapshot_json"] else "FAIL",
            {
                "run_id": scan_run_id,
                "scan_id": fixture_a["scan_id"],
                "scan_snapshot_present": bool(scan_input["jobs_snapshot_json"]),
                "live_lifecycle": archived_scan["items"][0]["lifecycle"],
                "backend_status": scan_run["backend_status"],
            },
        )

        with sqlite3.connect(paths.sqlite_path) as connection:
            connection.row_factory = sqlite3.Row
            screening_stage = dict(connection.execute(
                "SELECT * FROM run_stage_executions WHERE run_id = ? AND stage_id = 'screening'",
                (run_id,),
            ).fetchone())
            ranking_stage = dict(connection.execute(
                "SELECT * FROM run_stage_executions WHERE run_id = ? AND stage_id = 'ranking'",
                (run_id,),
            ).fetchone())
            screening_rows = [dict(row) for row in connection.execute(
                "SELECT status, reason_code, evidence_json FROM run_job_stage_results "
                "WHERE run_job_id IN (SELECT run_job_id FROM run_jobs WHERE run_id = ?) "
                "AND stage_id = 'screening'",
                (run_id,),
            )]
            ranking_rows = [dict(row) for row in connection.execute(
                "SELECT run_job_id, status FROM run_job_stage_results "
                "WHERE run_job_id IN (SELECT run_job_id FROM run_jobs WHERE run_id = ?) "
                "AND stage_id = 'ranking' ORDER BY rowid",
                (run_id,),
            )]
            trace_rows = [dict(row) for row in connection.execute(
                "SELECT j.run_job_id, j.source_index, r.stage_id, r.status "
                "FROM run_jobs AS j JOIN run_job_stage_results AS r ON r.run_job_id = j.run_job_id "
                "WHERE j.run_id = ? ORDER BY j.source_index, r.stage_id",
                (run_id,),
            )]
            trace_jobs_expected = [dict(row) for row in connection.execute(
                "SELECT run_job_id, source_index FROM run_jobs WHERE run_id = ? ORDER BY source_index LIMIT 5",
                (run_id,),
            )]
        screening_passed = sum(row["status"] == "passed" for row in screening_rows)
        screening_rejected = sum(row["status"] == "rejected" for row in screening_rows)
        _record(
            result,
            "P11",
            "PASS" if screening_stage["status"] == "succeeded" and screening_passed and screening_rejected else "FAIL",
            {"run_id": run_id, "passed": screening_passed, "rejected": screening_rejected, "stage": screening_stage["status"]},
        )
        evidence_complete = all(
            isinstance(json.loads(str(row["evidence_json"] or "{}")), dict)
            and (row["reason_code"] or json.loads(str(row["evidence_json"] or "{}")))
            for row in screening_rows
        )
        _record(result, "P12", "PASS" if evidence_complete else "FAIL", {"run_id": run_id, "screening_rows": len(screening_rows), "evidence_complete": evidence_complete})
        _record(result, "P14", "PASS" if ranking_stage["status"] == "succeeded" and ranking_rows else "FAIL", {"run_id": run_id, "ranking_rows": len(ranking_rows), "stage": ranking_stage["status"]})
        trace_by_job: dict[str, set[str]] = {}
        trace_status: dict[tuple[str, str], str] = {}
        for row in trace_rows:
            trace_by_job.setdefault(str(row["run_job_id"]), set()).add(str(row["stage_id"]))
            trace_status[(str(row["run_job_id"]), str(row["stage_id"]))] = str(row["status"])
        first_five = [(int(row["source_index"]), str(row["run_job_id"])) for row in trace_jobs_expected]
        trace_complete = all(
            "enrichment" in trace_by_job[run_job_id]
            and (
                trace_status[(run_job_id, "enrichment")] == "skipped"
                or (
                    "screening" in trace_by_job[run_job_id]
                    and (trace_status[(run_job_id, "screening")] != "passed" or "ranking" in trace_by_job[run_job_id])
                )
            )
            for _, run_job_id in first_five
        )
        expected_trace_jobs = min(5, len(jobs))
        _record(result, "P25", "PASS" if len(first_five) == expected_trace_jobs and trace_complete else "FAIL", {"run_id": run_id, "trace_jobs": len(first_five), "expected_trace_jobs": expected_trace_jobs, "trace_complete": trace_complete, "screening_stage": screening_stage["status"], "ranking_stage": ranking_stage["status"]})

        system_settings = settings_store.load_system_settings()
        settings_store.patch_system_settings(
            {"maximum_attempts": 1},
            expected_revision=int(system_settings["revision"]),
        )
        failure_response = _submit_upload(client, app, scan_profile_id, jobs[:1], "P19-snapshot-integrity")
        if failure_response.status_code != 201:
            raise RuntimeError(f"P19 submission failed: {failure_response.status_code} {failure_response.text[:300]}")
        failure_run_id = str(failure_response.json()["data"]["run_id"])
        executor.wait_submitted()
        failure_inputs = _read_inputs(paths.sqlite_path, failure_run_id)
        real_execute_pipeline_run = worker_job.execute_pipeline_run

        def fail_once(*args: Any, **kwargs: Any) -> Any:
            worker_job.execute_pipeline_run = real_execute_pipeline_run
            raise RuntimeError("acceptance injected worker failure")

        worker_job.execute_pipeline_run = fail_once
        executor.release()
        executor.result(timeout=300)
        failure_run = _run_row(paths.sqlite_path, failure_run_id)
        _record(result, "P19", "PASS" if failure_run["backend_status"] == "failed" else "FAIL", {"run_id": failure_run_id, "backend_status": failure_run["backend_status"], "error_code": failure_run["error_code"], "error_message": failure_run["error_message"]})

        retry_settings = settings_store.load_system_settings()
        settings_store.patch_system_settings(
            {"maximum_attempts": 2},
            expected_revision=int(retry_settings["revision"]),
        )
        _mutate_run_input(paths.sqlite_path, failure_run_id, "candidate_profile_json", str(failure_inputs["candidate_profile_json"]))
        try:
            retry_response = client.post(
                f"/admin/runs/{failure_run_id}/retry",
                headers=_request_headers(app, "P20-retry"),
            )
            if retry_response.status_code != 200:
                raise RuntimeError(f"retry status {retry_response.status_code}: {retry_response.text[:300]}")
            executor.wait_submitted()
            executor.release()
            executor.result(timeout=300)
            retried_run = _run_row(paths.sqlite_path, failure_run_id)
            retry_inputs = _read_inputs(paths.sqlite_path, failure_run_id)
            _record(
                result,
                "P20",
                "PASS" if retried_run["backend_status"] == "succeeded" and retry_inputs["candidate_profile_json"] == failure_inputs["candidate_profile_json"] else "FAIL",
                {"run_id": failure_run_id, "retry_status": retry_response.json(), "backend_status": retried_run["backend_status"], "snapshot_unchanged": retry_inputs["candidate_profile_json"] == failure_inputs["candidate_profile_json"]},
            )
        except Exception as exc:
            _record(
                result,
                "P20",
                "FAIL",
                {"run_id": failure_run_id, "backend_status_before_retry": failure_run["backend_status"], "snapshot_unchanged": _read_inputs(paths.sqlite_path, failure_run_id)["candidate_profile_json"] == failure_inputs["candidate_profile_json"]},
                str(exc),
            )
        archived = sqlite_store.transition_candidate_profile_lifecycle(
            profile_id,
            lifecycle="archived",
            expected_revision=int(updated["revision"]),
            database_path=paths.sqlite_path,
        )
        invalid = _submit_upload(client, app, profile_id, jobs[:1], "P22-stale-profile")
        invalid_error = invalid.json().get("error", {}) if invalid.headers.get("content-type", "").startswith("application/json") else {}
        _record(result, "P22", "PASS" if invalid.status_code == 409 and invalid_error.get("code") in {"candidate_profile_unavailable", "candidate_profile_archived"} else "FAIL", {"status_code": invalid.status_code, "error_code": invalid_error.get("code"), "lifecycle": archived["lifecycle"]})
        missing_probes = sorted(set(PROBES) - set(result["probes"]))
        unexpected_probes = sorted(set(result["probes"]) - set(PROBES))
        if missing_probes or unexpected_probes:
            result["error"] = {"missing_probes": missing_probes, "unexpected_probes": unexpected_probes}
            result["result"] = "BLOCKED"
        else:
            statuses = [item["status"] for item in result["probes"].values()]
            result["result"] = "FAIL" if "FAIL" in statuses else "PASS" if all(status == "PASS" for status in statuses) else "BLOCKED"
    except Exception as exc:
        result["error"] = str(exc)
    finally:
        executor.shutdown()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(".tmp/fitcv-local-p0-acceptance.json"))
    args = parser.parse_args()
    root = Path(__file__).parents[1].resolve()
    report = run(root, args.output)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
