"""Seed one disposable, review-required CV run for browser verification."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fitcv_cp import sqlite_store
from fitcv.agentic_cv_analysis import build_evidence_projection
from fitcv_cp.models import PipelineRun, RunStatus


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--no-cv-version", action="store_true")
    args = parser.parse_args()
    database = args.database.resolve()
    if database.exists():
        raise SystemExit(f"database_exists: {database}")
    database.parent.mkdir(parents=True, exist_ok=True)
    import os

    os.environ["FITCV_CP_SQLITE_PATH"] = str(database)
    now = datetime.datetime.now(datetime.timezone.utc)
    run_id = "e2e-review-run"
    job_url = "https://jobs.example.test/e2e-review"
    jobs = [{
        "jobUrl": job_url,
        "title": "Analytics Engineer",
        "companyName": "FitCV E2E",
        "description": "Build analytics systems with SQL and Python.",
        "required_skills": ["Python"],
        "location": "Remote",
    }]
    profile = {
        "name": "E2E Candidate",
        "candidate_profile_id": "e2e-profile",
        "revision": 1,
        "skills": ["SQL"],
        "experience": [{
            "title": "Analyst",
            "company": "Example",
            "bullets": [
                "Built SQL reports.",
                "Used Python for analytics automation.",
            ],
        }],
    }
    source_profile_fingerprint = str(build_evidence_projection(profile).get("fingerprint") or "")
    run = PipelineRun(
        run_id=run_id,
        status=RunStatus.SUCCEEDED,
        triggered_by="e2e",
        trigger_source="e2e_fixture",
        jobs_path="e2e-fixture.json",
        config_path="e2e-fixture.json",
        created_at=now,
        run_name="FitCV review E2E",
        jobs_input_source="path",
        jobs_input_json=json.dumps(jobs, sort_keys=True),
        jobs_input_manifest_json=json.dumps({"source_filenames": ["e2e-fixture.json"]}),
        candidate_profile_source="e2e-fixture",
        candidate_profile_json=json.dumps(profile, sort_keys=True),
        effective_settings_json=json.dumps(
            {
                "cv_generation_model": "e2e-fixture",
                "required_cv_sections": ["Summary", "Experience", "Skills"],
                "pipeline": {"evidence_top_k": 3},
            },
            sort_keys=True,
        ),
    )
    sqlite_store.insert_run(run)
    run_job_id = sqlite_store.list_run_job_ids_for_run(run_id)[0]
    content = b"# Analytics Engineer\n\n## Summary\nExperienced SQL analyst.\n"
    version_id = "e2e-cv-version-1"
    quality = {
        "artifact_version_id": version_id,
        "content_checksum": hashlib.sha256(content).hexdigest(),
        "render_proof": {
            "content_sha256": hashlib.sha256(content).hexdigest(),
            "page_fit_status": "pass",
            "render_status": "pass",
            "artifact_checksum": hashlib.sha256(content).hexdigest(),
            "page_count": 1,
            "template_sha256": hashlib.sha256(b"e2e-template").hexdigest(),
            "render_config_fingerprint": hashlib.sha256(b"e2e-render-config").hexdigest(),
            "renderer_contract_version": "e2e-render-v1",
        },
    }
    with sqlite_store._sqlite_connection(database) as conn:
        checksum = hashlib.sha256(content).hexdigest()
        if not args.no_cv_version:
            conn.execute(
            """INSERT INTO cv_versions (
                version_id, run_job_id, ordinal, generation_status, created_at,
                finished_at, generator_id, model_id, content_length, content_checksum,
                content_blob, media_type, filename, run_id, job_url,
                quality_warnings_json
            ) VALUES (?, ?, 1, 'review_required', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    version_id, run_job_id, now.isoformat(), now.isoformat(),
                    "e2e_fixture", "e2e-fixture", len(content), checksum, content,
                    "text/markdown", "e2e-cv.md", run_id, job_url, json.dumps(quality),
                ),
            )
            conn.execute(
                "UPDATE run_jobs SET current_cv_version_id=? WHERE run_job_id=?",
                (version_id, run_job_id),
            )
        conn.execute(
            """INSERT INTO run_job_stage_results (
                run_job_id, stage_id, status, reason_code, evidence_json
            ) VALUES (?, 'cv-generation', 'review_required', 'review_required', ?)""",
            (run_job_id, json.dumps({"status": "review_required", "version_id": version_id})),
        )
        conn.commit()
    debug = {
        "debug_records": [{
            "job_url": job_url,
            "job_title": "Analytics Engineer",
            "status": "review_required",
            "review_item_id": "e2e-review-item",
            "candidate_profile_id": "e2e-profile",
            "candidate_profile_revision": "1",
            "source_profile_fingerprint": source_profile_fingerprint,
            "fit_classification": "stretch",
            "reason": "One requirement needs candidate confirmation.",
            "markdown_preview": content.decode(),
            "uncertainties": [{
                "uncertainty_id": "e2e-uncertainty",
                "resolution_key": "required_skill:python",
                "requirement_instance_id": "required_skill:python",
                "question": "How have you used Python?",
                "affected_fact": "Python experience",
                "resolution_status": "pending",
            }],
        }],
        "hitl_review_actions": [],
    }
    sqlite_store.update_run_cv_generation_debug(run_id, json.dumps(debug, sort_keys=True))
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps({
        "database": str(database),
        "run_id": run_id,
        "run_job_id": run_job_id,
        "job_url": job_url,
        "uncertainty_id": "e2e-uncertainty",
        "source_profile_fingerprint": source_profile_fingerprint,
        "expected_terminal_state": "review_required",
        "cv_versions_count": 0 if args.no_cv_version else 1,
        "cleanup_owner": "run_fitcv_review_e2e.ps1",
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"database": str(database), "run_id": run_id, "run_job_id": run_job_id}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
