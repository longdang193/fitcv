"""Run canonical FitCV Local P20 retry acceptance probe only."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any

def _events(database_path: Path, run_id: str) -> list[dict[str, Any]]:
    from fitcv_cp import sqlite_store

    return [
        {
            "stage": event.stage,
            "payload": json.loads(event.payload_json) if event.payload_json else None,
        }
        for event in sqlite_store.get_events(run_id)
    ]

def run(root: Path, output_path: Path) -> dict[str, Any]:
    sys.path.insert(0, str(root / "src"))
    sys.path.insert(0, str(root))

    import yaml
    from fastapi.testclient import TestClient

    from fitcv import config as fitcv_config
    from fitcv import candidate as fitcv_candidate
    from fitcv_cp import local_app, local_routes, settings_store, sqlite_store, worker_job
    from fitcv_cp.app import create_app
    from fitcv_cp.env_defaults import load_dotenv_defaults
    from fitcv_cp.local_storage import (
        activate_local_storage,
        migrate_packaged_local_integration_state,
        write_controller_overlay,
    )
    from tests.test_fitcv_cp.acceptance_harness import ControlledLocalJobExecutor, create_profile_fixture
    from scripts.run_fitcv_local_p0_acceptance import (
        _git_state,
        _read_inputs,
        _request_headers,
        _submit_upload,
        _valid_jobs,
    )

    result: dict[str, Any] = {
        "result": "BLOCKED",
        "probe": "P20",
        "baseline": _git_state(root),
        "local_runtime_contract": {
            "FITCV_LOCAL_MODE": "1",
            "FITCV_CP_INLINE_EXECUTION": "1",
            "REDIS_URL": None,
            "docker": "not required",
            "rq_worker": "not required",
        },
    }
    workspace = Path(tempfile.mkdtemp(prefix="fitcv-p20-acceptance-"))
    appdata = workspace / "appdata"
    localappdata = workspace / "localappdata"
    data_root = workspace / "data-root"
    appdata.mkdir()
    localappdata.mkdir()
    executor = None
    try:
        load_dotenv_defaults(root / ".env")
        os.environ.update({
            "APPDATA": str(appdata),
            "LOCALAPPDATA": str(localappdata),
            "FITCV_LOCAL_MODE": "1",
            "FITCV_CP_INLINE_EXECUTION": "1",
        })
        os.environ.pop("REDIS_URL", None)
        paths = activate_local_storage(data_root=data_root)
        result["database"] = str(paths.sqlite_path)
        shutil.copyfile(root / "data" / "candidate_profile.private.yaml", paths.candidate_profile_path)
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
        canonical = yaml.safe_load((root / "data" / "candidate_profile.yaml").read_text(encoding="utf-8"))
        validation_errors = fitcv_candidate.validate_profile(canonical)
        if validation_errors:
            raise RuntimeError(f"acceptance profile fixture is invalid: {validation_errors}")
        profile = create_profile_fixture(paths.sqlite_path, canonical)
        jobs = _valid_jobs()
        executor = ControlledLocalJobExecutor()
        local_app._LOCAL_EXECUTOR = executor
        local_routes.onboarding_is_complete = lambda: True
        local_routes.local_readiness_status = lambda: {"ready": True, "reasons": []}
        app = create_app(redis_url="")
        client = TestClient(app, base_url="http://127.0.0.1")
        profile_id = str(profile["candidate_profile_id"])

        settings = settings_store.load_system_settings()
        settings_store.patch_system_settings(
            {"maximum_attempts": 1}, expected_revision=int(settings["revision"])
        )
        failed_response = _submit_upload(client, app, profile_id, jobs[:1], "P20-initial-failure")
        if failed_response.status_code != 201:
            raise RuntimeError(f"initial P20 submission failed: {failed_response.status_code} {failed_response.text[:300]}")
        run_id = str(failed_response.json()["data"]["run_id"])
        executor.wait_submitted()
        initial_inputs = _read_inputs(paths.sqlite_path, run_id)
        real_run_pipeline = worker_job.run_pipeline

        def fail_once(*args: Any, **kwargs: Any) -> Any:
            worker_job.run_pipeline = real_run_pipeline
            raise RuntimeError("acceptance injected worker failure")

        worker_job.run_pipeline = fail_once
        executor.release()
        executor.result(timeout=300)
        before_retry = sqlite_store.get_run(run_id)
        if before_retry is None or before_retry.status.value != "failed":
            raise RuntimeError("P20 initial run did not reach failed")
        before_attempts = [
            str(event["payload"].get("attempt", {}).get("attempt_id"))
            for event in _events(paths.sqlite_path, run_id)
            if event["stage"] == "run_attempt" and isinstance(event["payload"], dict)
        ]
        before_jobs = len(sqlite_store.query_run_jobs(run_id)["items"])
        before_queue_job_id = before_retry.queue_job_id

        retry_settings = settings_store.load_system_settings()
        settings_store.patch_system_settings(
            {"maximum_attempts": 2}, expected_revision=int(retry_settings["revision"])
        )
        retry_response = client.post(
            f"/admin/runs/{run_id}/retry",
            headers=_request_headers(app, "P20-retry-only"),
        )
        if retry_response.status_code != 200:
            raise RuntimeError(f"retry status {retry_response.status_code}: {retry_response.text[:300]}")
        queued = sqlite_store.get_run(run_id)
        if queued is None or queued.status.value not in {"queued", "running"} or queued.finished_at is not None:
            raise RuntimeError("retry did not establish valid nonterminal state")
        retry_submission_id = queued.queue_job_id
        executor.wait_submitted()
        executor.release()
        executor.result(timeout=300)
        after_retry = sqlite_store.get_run(run_id)
        if after_retry is None:
            raise RuntimeError("retried Run missing")
        after_inputs = _read_inputs(paths.sqlite_path, run_id)
        after_attempts = [
            str(event["payload"].get("attempt", {}).get("attempt_id"))
            for event in _events(paths.sqlite_path, run_id)
            if event["stage"] == "run_attempt" and isinstance(event["payload"], dict)
        ]
        unique_attempts = list(dict.fromkeys(after_attempts))
        after_jobs = len(sqlite_store.query_run_jobs(run_id)["items"])
        immutable = all(
            after_inputs[key] == initial_inputs[key]
            for key in ("jobs_snapshot_json", "candidate_profile_json", "candidate_profile_checksum", "settings_snapshot_json")
        )
        passed = (
            after_retry.status.value == "succeeded"
            and after_retry.run_id == run_id
            and after_retry.finished_at is not None
            and retry_submission_id
            and retry_submission_id != before_queue_job_id
            and len(unique_attempts) == 2
            and unique_attempts[0] == before_attempts[0]
            and unique_attempts[1] != unique_attempts[0]
            and before_jobs == after_jobs
            and immutable
            and any(event["stage"] == "retry_requested" for event in _events(paths.sqlite_path, run_id))
        )
        result["result"] = "PASS" if passed else "FAIL"
        result["evidence"] = {
            "run_id": run_id,
            "before_status": before_retry.status.value,
            "before_finished_at": before_retry.finished_at.isoformat() if before_retry.finished_at else None,
            "after_status": after_retry.status.value,
            "after_finished_at": after_retry.finished_at.isoformat() if after_retry.finished_at else None,
            "initial_submission_id": before_queue_job_id,
            "retry_submission_id": retry_submission_id,
            "attempt_ids": unique_attempts,
            "attempt_identity_distinct": len(unique_attempts) == 2,
            "run_jobs_before": before_jobs,
            "run_jobs_after": after_jobs,
            "immutable_snapshots_unchanged": immutable,
        }
    except Exception as exc:
        result["result"] = "FAIL"
        result["error"] = str(exc)
    finally:
        if executor is not None:
            executor.shutdown()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result

def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(".tmp/fitcv-local-p20-acceptance.json"))
    args = parser.parse_args()
    root = Path(__file__).parents[1].resolve()
    report = run(root, args.output)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["result"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
