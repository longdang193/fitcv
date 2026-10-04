"""Validate and manifest an isolated FitCV repair-arm cohort."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "tests/fixtures/fitcv-p1ab-repair-experiment.json"
VALID_ARMS = {"local_first", "provider_first"}
VALID_EVIDENCE_CATEGORIES = {"grounding", "final_artifact", "page_fit", "review_outcome"}
REUSE_STAGES = ("enrich", "ranking", "cv_analysis", "cv_generation", "synonym_triage")
DECLARED_INPUTS = (
    "scripts/run_fitcv_repair_experiment.py",
    "scripts/benchmark_cv_efficiency.py",
    "scripts/verify_fitcv_acceptance.py",
    "scripts/run_fitcv_review_e2e.ps1",
    "scripts/serve_fitcv_review_e2e.py",
    "tests/fixtures/fitcv-p1ab-repair-experiment.json",
    "data/candidate_profile.yaml",
    "src/fitcv/agentic_cv_generation.py",
    "src/fitcv/config.py",
    "src/fitcv/pipeline.py",
    "src/fitcv_cp/app.py",
    "src/fitcv_cp/worker_job.py",
    "tests/test_fitcv_cp/acceptance_harness.py",
    "config/runtime/control_plane.yaml",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _diff_hash() -> str:
    completed = subprocess.run(["git", "diff", "--binary"], cwd=ROOT, check=True, capture_output=True)
    return hashlib.sha256(completed.stdout).hexdigest()


def _load_fixture(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != "fitcv.p1ab.repair_experiment_fixture.v1":
        raise ValueError("fixture_schema_invalid")
    job_types = [str(value).strip() for value in list(payload.get("job_types") or [])]
    categories = [str(value).strip().casefold() for value in list(payload.get("required_evidence_categories") or [])]
    arms = dict(payload.get("arms") or {})
    incumbent = str(arms.get("INCUMBENT_ARM") or "").strip()
    candidate = str(arms.get("CANDIDATE_ARM") or "").strip()
    normalized_job_types = [value.casefold() for value in job_types if value]
    if len(set(normalized_job_types)) != len(normalized_job_types):
        raise ValueError("fixture_requires_unique_job_types")
    if len(set(normalized_job_types)) < 2:
        raise ValueError("fixture_requires_two_job_types")
    if not categories:
        raise ValueError("fixture_missing_evidence_categories")
    unknown_categories = sorted(set(categories) - VALID_EVIDENCE_CATEGORIES)
    if unknown_categories:
        raise ValueError(f"fixture_unknown_evidence_category:{','.join(unknown_categories)}")
    if incumbent not in VALID_ARMS or candidate not in VALID_ARMS:
        raise ValueError("arm_selector_invalid")
    if incumbent == candidate:
        raise ValueError("arm_selectors_identical")
    if int(payload.get("repeat_count") or 0) != 10:
        raise ValueError("repeat_count_must_be_10")
    profile = yaml.safe_load((ROOT / "data" / "candidate_profile.yaml").read_text(encoding="utf-8")) or {}
    _validate_job_types_against_exclusions(
        job_types,
        list(dict(profile.get("preferences") or {}).get("exclude_contract_types") or []),
    )
    return payload


def _validate_job_types_against_exclusions(
    job_types: list[str],
    excluded_contract_types: list[str],
) -> None:
    overlap = sorted(
        {
            job_type
            for job_type in (str(value).strip() for value in job_types)
            if job_type
            for excluded in (str(value).strip() for value in excluded_contract_types)
            if excluded and job_type.casefold() == excluded.casefold()
        }
    )
    if overlap:
        raise ValueError(f"fixture_job_type_excluded_by_profile: {','.join(overlap)}")


def _input_fingerprint(fixture: Path) -> str:
    digest = hashlib.sha256()
    for relative in sorted(set(DECLARED_INPUTS) | {str(fixture.relative_to(ROOT)).replace("\\", "/")}):
        path = ROOT / relative
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def capture_input_identity(fixture: Path) -> dict[str, Any]:
    payload = _load_fixture(fixture)
    return {
        "fixture_sha256": _sha256(fixture),
        "source_commit": _git("rev-parse", "HEAD"),
        "working_tree_diff_sha256": _diff_hash(),
        "declared_input_fingerprint": _input_fingerprint(fixture),
        "model": payload.get("model"),
        "runtime": payload.get("runtime"),
        "repeat_count": int(payload["repeat_count"]),
        "job_types": sorted(str(value) for value in payload["job_types"]),
    }


def build_manifest(
    *,
    fixture: Path,
    arm: str,
    database: Path,
    run_ids: list[str],
    frozen_input_identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _load_fixture(fixture)
    if arm not in VALID_ARMS:
        raise ValueError("arm_selector_invalid")
    if arm not in set(dict(payload["arms"]).values()):
        raise ValueError("arm_selector_not_declared")
    if len(run_ids) != int(payload["repeat_count"]):
        raise ValueError("run_id_count_must_match_repeat_count")
    if len(set(run_ids)) != len(run_ids):
        raise ValueError("duplicate_run_ids")
    input_identity = capture_input_identity(fixture)
    if frozen_input_identity is not None and input_identity != frozen_input_identity:
        raise ValueError("input_identity_changed_after_cohort")
    return {
        "schema_version": "fitcv.p1ab.repair_experiment_manifest.v1",
        "fixture": str(fixture.resolve()),
        "fixture_sha256": input_identity["fixture_sha256"],
        "database_path": str(database.resolve()),
        "arm": arm,
        "repeat_count": len(run_ids),
        "run_ids": run_ids,
        "source_commit": input_identity["source_commit"],
        "working_tree_diff_sha256": input_identity["working_tree_diff_sha256"],
        "declared_input_fingerprint": input_identity["declared_input_fingerprint"],
        "model": input_identity["model"],
        "runtime": input_identity["runtime"],
        "job_types": input_identity["job_types"],
        "cache_policy": "isolated_per_arm",
        "provider_credentials": "loaded_from_existing_env_or_dotenv_only",
    }


def _require_fresh_path(path: Path) -> None:
    if path.exists():
        raise ValueError(f"path_must_be_fresh: {path}")


def _experiment_jobs(job_types: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "title": f"Senior Data Engineer — {job_type}",
            "location": "Remote",
            "postedTime": "1 day ago",
            "publishedAt": "2026-10-01",
            "jobUrl": f"https://fitcv.example/repair-experiment/{ordinal}",
            "companyName": "FitCV Experiment Fixture",
                "description": (
                    "Build BigQuery ecommerce analytics pipelines and Azure ML "
                    "customer-churn models with Python and SQL. Create reliable "
                    "dashboards, document decisions, and collaborate with "
                    "engineering stakeholders."
                ),
                "seniority": "senior",
            "contractType": job_type,
            "experienceLevel": "Mid-Senior level",
            "workType": "Remote",
        }
        for ordinal, job_type in enumerate(job_types, start=1)
    ]


def _load_run_config(run: Any) -> dict[str, Any]:
    raw = str(
        getattr(run, "effective_settings_json", None)
        or getattr(run, "settings_used_json", None)
        or ""
    ).strip()
    if not raw:
        raise RuntimeError("queued_run_missing_settings_snapshot")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise RuntimeError("queued_run_settings_snapshot_invalid")
    return payload


def _disable_cross_run_reuse(settings: dict[str, Any]) -> dict[str, Any]:
    isolated = dict(settings)
    reuse = {
        str(stage): dict(policy)
        for stage, policy in dict(settings.get("reuse") or {}).items()
        if isinstance(policy, dict)
    }
    for stage in REUSE_STAGES:
        policy = dict(reuse.get(stage) or {})
        policy["enabled"] = False
        reuse[stage] = policy
    isolated["reuse"] = reuse
    isolated["experiment_reuse_policy"] = "fresh_generation_no_cross_run_reuse_v1"
    return isolated


def _response_run_id(response: Any) -> str:
    payload = response.json()
    if not isinstance(payload, dict):
        return ""
    data = payload.get("data")
    return str(payload.get("run_id") or (data or {}).get("run_id") or "").strip()


def _bind_repair_arm(*, run_id: str, arm: str, database: Path) -> None:
    import sys

    sys.path.insert(0, str(ROOT / "src"))
    from fitcv_cp import sqlite_store

    run = sqlite_store.get_run(run_id, database_path=database)
    if run is None:
        raise RuntimeError(f"run_not_found_before_execution: {run_id}")
    settings = _disable_cross_run_reuse(_load_run_config(run))
    settings["cv_generation_repair_arm"] = arm
    result = sqlite_store.update_run_effective_settings(
        run_id,
        json.dumps(settings, ensure_ascii=False, sort_keys=True),
        database_path=database,
    )
    if result.get("persistence_status") != "persisted":
        raise RuntimeError(f"repair_arm_binding_failed: {result}")


def _run_real_cohort(*, fixture: Path, arm: str, database: Path) -> list[str]:
    import sys

    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT))
    from fastapi.testclient import TestClient
    from fitcv import config as fitcv_config
    from fitcv_cp import local_app, local_routes, sqlite_store
    from fitcv_cp.app import create_app
    from fitcv_cp.env_defaults import load_dotenv_defaults
    from fitcv_cp.local_storage import (
        activate_local_storage,
        migrate_packaged_local_integration_state,
        write_controller_overlay,
    )
    from tests.test_fitcv_cp.acceptance_harness import (
        ControlledLocalJobExecutor,
        configure_local_provider_credential_from_env,
        create_profile_fixture,
    )
    import yaml

    payload = _load_fixture(fixture)
    _require_fresh_path(database)
    database.parent.mkdir(parents=True, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix=f"fitcv-repair-{arm}-", dir=str(database.parent)))
    executor = None
    try:
        load_dotenv_defaults(ROOT / ".env")
        appdata = workspace / "appdata"
        localappdata = workspace / "localappdata"
        appdata.mkdir()
        localappdata.mkdir()
        os.environ.update(
            {
                "APPDATA": str(appdata),
                "LOCALAPPDATA": str(localappdata),
                "FITCV_LOCAL_MODE": "1",
                "FITCV_CP_INLINE_EXECUTION": "1",
            }
        )
        os.environ.pop("REDIS_URL", None)
        paths = activate_local_storage(data_root=workspace / "data-root")
        os.environ["FITCV_CP_SQLITE_PATH"] = str(paths.sqlite_path)
        shutil.copyfile(ROOT / "data" / "candidate_profile.private.yaml", paths.candidate_profile_path)
        control = yaml.safe_load(
            (ROOT / "config" / "runtime" / "control_plane.yaml").read_text(encoding="utf-8")
        )["control_plane"]
        write_controller_overlay(
            paths.controller_overlay_path,
            {
                "version": fitcv_config.LOCAL_CONTROLLER_OVERLAY_VERSION,
                "providers": dict(control.get("providers") or {}),
                "model_routing": {
                    "parts": dict((control.get("model_routing") or {}).get("parts") or {})
                },
                "fitcv_cp": dict(control.get("fitcv_cp") or {}),
            },
        )
        sqlite_store.initialize_control_plane_database(paths.sqlite_path, paths.candidate_profile_path)
        migrate_packaged_local_integration_state(paths)
        configure_local_provider_credential_from_env("openai_compatible")
        canonical = yaml.safe_load(
            (ROOT / "data" / "candidate_profile.yaml").read_text(encoding="utf-8")
        )
        profile = create_profile_fixture(paths.sqlite_path, canonical)

        executor = ControlledLocalJobExecutor()
        local_app._LOCAL_EXECUTOR = executor
        local_routes.onboarding_is_complete = lambda: True
        local_routes.local_readiness_status = lambda: {"ready": True, "reasons": []}
        app = create_app(redis_url="")
        client = TestClient(app, base_url="http://127.0.0.1")
        headers_base = {
            "Origin": "http://127.0.0.1",
            "X-FitCV-CSRF": str(app.state.csrf_token),
        }
        run_ids: list[str] = []
        job_types = sorted(str(value) for value in payload["job_types"])
        for repeat in range(int(payload["repeat_count"])):
            jobs_json = json.dumps(
                _experiment_jobs([job_types[repeat % len(job_types)]]),
                ensure_ascii=False,
            ).encode("utf-8")
            response = client.post(
                "/runs",
                headers={**headers_base, "Idempotency-Key": f"fitcv-repair-{arm}-{repeat}"},
                data={"profile_id": str(profile["candidate_profile_id"]), "run_name": f"fitcv-repair-{arm}-{repeat}"},
                files={"jobs_file": ("fitcv-repair-experiment.json", jobs_json, "application/json")},
            )
            if response.status_code != 201:
                raise RuntimeError(f"cohort_submission_failed: {response.status_code}")
            run_id = _response_run_id(response)
            if not run_id:
                raise RuntimeError("cohort_submission_missing_run_id")
            executor.wait_submitted()
            _bind_repair_arm(run_id=run_id, arm=arm, database=paths.sqlite_path)
            executor.release()
            executor.result(timeout=900)
            run = sqlite_store.get_run(run_id, database_path=paths.sqlite_path)
            if run is None or str(getattr(run.status, "value", run.status)) != "succeeded":
                raise RuntimeError(f"cohort_run_not_succeeded: {run_id}")
            run_ids.append(run_id)
        executor.shutdown()
        executor = None
        shutil.copy2(paths.sqlite_path, database)
        return run_ids
    finally:
        if executor is not None:
            executor.shutdown()
        shutil.rmtree(workspace, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--arm", choices=sorted(VALID_ARMS))
    parser.add_argument("--database", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--run-id", action="append", default=[])
    parser.add_argument("--preflight-fixture", action="store_true")
    parser.add_argument("--produce-real", action="store_true")
    args = parser.parse_args()
    fixture = args.fixture.resolve()
    try:
        payload = _load_fixture(fixture)
        if args.preflight_fixture:
            print(json.dumps({
                "status": "eligible_shape",
                "fixture": str(fixture),
                "fixture_sha256": _sha256(fixture),
                "arms": payload["arms"],
                "repeat_count": payload["repeat_count"],
                "job_types": sorted(payload["job_types"]),
                "required_evidence_categories": sorted(payload["required_evidence_categories"]),
            }, indent=2, sort_keys=True))
            return 0
        if not args.arm or not args.database or not args.manifest:
            parser.error("normal run requires --arm, --database, and --manifest")
        database = args.database.resolve()
        manifest_path = args.manifest.resolve()
        frozen_input_identity = capture_input_identity(fixture) if args.produce_real else None
        if args.produce_real:
            _require_fresh_path(manifest_path)
            run_ids = _run_real_cohort(fixture=fixture, arm=args.arm, database=database)
        else:
            run_ids = [str(value).strip() for value in args.run_id if str(value).strip()]
        manifest = build_manifest(
            fixture=fixture,
            arm=args.arm,
            database=database,
            run_ids=run_ids,
            frozen_input_identity=frozen_input_identity,
        )
        manifest["producer"] = {
            "mode": "provider_backed" if args.produce_real else "manifest_only",
            "provider_credentials": "loaded_from_dotenv_without_emission" if args.produce_real else "not_loaded",
        }
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"status": "manifested", "manifest": str(manifest_path), "arm": args.arm, "run_count": len(run_ids)}, sort_keys=True))
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"status": "rejected", "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
