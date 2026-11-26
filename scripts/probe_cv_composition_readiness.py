"""Run a deterministic, credential-free CV composition shadow/replay probe."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from fitcv.agentic_cv_generation import build_cv_content_plan
from fitcv.cv_generator import build_empty_structured_cv, serialize_mycvs_v1, validate_mycvs_v1_markdown


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _document(job: dict[str, Any], profile: dict[str, Any], config: dict[str, Any], plan: dict[str, Any], handoff: str) -> str:
    document = build_empty_structured_cv(
        jd={"job_url": job.get("jobUrl") or job.get("job_url"), "title": job.get("title") or job.get("job_title")},
        profile=profile,
        config=config,
        fit_classification="unclassified",
    )
    document.update({"profile_revision": profile.get("revision"), "ranking_cv_handoff": {"handoff_fingerprint": handoff}, "composition_plan": plan})
    sections = document["sections"]
    sections["summary"] = {"text": profile.get("headline") or profile.get("name") or "Candidate profile"}
    sections["education"] = [dict(item) for item in profile.get("education") or [] if isinstance(item, dict)]
    sections["experience"] = []
    for item in profile.get("experiences") or []:
        if not isinstance(item, dict):
            continue
        entry = dict(item)
        bullets = [bullet.get("text", "") if isinstance(bullet, dict) else str(bullet) for bullet in item.get("bullets") or []]
        entry["overview"] = bullets[0] or f"Worked as {item.get('role', '')} at {item.get('company', '')}."
        entry["bullets"] = bullets[:3]
        sections["experience"].append(entry)
    sections["projects"] = []
    for item in profile.get("projects") or []:
        if not isinstance(item, dict):
            continue
        entry = dict(item)
        entry["overview"] = item.get("business_value") or item.get("description") or item.get("name")
        entry["bullets"] = [str(value) for value in (item.get("highlights") or [])[:2]]
        sections["projects"].append(entry)
    sections["certifications"] = [dict(item) for item in profile.get("certifications") or [] if isinstance(item, dict)]
    groups: dict[str, list[str]] = defaultdict(list)
    for item in profile.get("skills") or []:
        if isinstance(item, dict) and str(item.get("name") or "").strip():
            groups[str(item.get("category") or "Skills")].append(str(item["name"]).strip())
    sections["skills"] = {"groups": [{"label": key, "items": values} for key, values in sorted(groups.items())]}
    return serialize_mycvs_v1(document)


def _run(jobs: list[dict[str, Any]], profile: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for job in jobs:
        job_url = str(job.get("jobUrl") or job.get("job_url") or "")
        job_identity = {"id": job.get("id"), "url": job_url, "title": job.get("title") or job.get("job_title")}
        job_bytes = _canonical_json(job_identity)
        handoff = _sha256_bytes(job_bytes + b"|" + str(profile.get("revision") or "").encode("utf-8"))
        analysis = {
            "analysis_input_fingerprint": _sha256_bytes(job_bytes),
            "candidate_profile_revision": profile.get("revision"),
            "job_url": job_url,
            "job_title": job.get("title") or job.get("job_title"),
            "job_snapshot": job,
            "canonical_profile": profile,
            "evidence_payload": [],
            "requirement_coverage": [
                {"requirement_instance_id": f"required_skill:{index}", "requirement": str(skill), "selected_support": "unknown", "supporting_evidence_ids": []}
                for index, skill in enumerate(job.get("required_skills") or [])
            ],
            "ranking_cv_handoff": {"handoff_fingerprint": handoff, "candidate_profile_revision": profile.get("revision")},
        }
        plan = build_cv_content_plan(analysis, job, config, profile)
        markdown = _document(job, profile, config, plan, handoff)
        validation = validate_mycvs_v1_markdown(markdown, content_plan=plan, expected_handoff=handoff)
        records.append(
            {
                "job_id": str(job.get("id") or job_url),
                "job_url": job_url,
                "composition_plan_fingerprint": plan["plan_fingerprint"],
                "ranking_handoff_identity": handoff,
                "markdown_checksum": validation["content_sha256"],
                "lifecycle_envelope": {
                    "generation_status": "shadow_ready",
                    "review_status": "not_run",
                    "pdf_status": "blocked",
                    "submission_clearance": "blocked",
                },
                "blocked_render_diagnostics": {
                    "code": "external_converter_release_unpinned",
                    "renderer_strategy": plan["renderer_strategy"],
                    "credential_free": True,
                },
            }
        )
    return {"record_count": len(records), "records": records}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", required=True, type=Path)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    jobs_bytes = args.jobs.read_bytes()
    profile_bytes = args.profile.read_bytes()
    jobs = json.loads(jobs_bytes)
    profile = yaml.safe_load(profile_bytes)
    if not isinstance(jobs, list) or not isinstance(profile, dict):
        raise ValueError("jobs must be a JSON list and profile must be a YAML mapping")
    config = {"cv": {"preset": "mycvs", "renderer": {"strategy": "mycvs_v1"}, "final_artifact_acceptance": {"enabled": True}}}
    first = _run(jobs, profile, config)
    second = _run(jobs, profile, config)
    first_bytes = _canonical_json(first)
    second_bytes = _canonical_json(second)
    args.output.mkdir(parents=True, exist_ok=True)
    summary = {
        "probe": "cv_composition_shadow_replay_v1",
        "jobs_path": str(args.jobs),
        "profile_path": str(args.profile),
        "jobs_sha256": _sha256_bytes(jobs_bytes),
        "profile_sha256": _sha256_bytes(profile_bytes),
        "record_count": len(jobs),
        "replay_byte_identical": first_bytes == second_bytes,
        "run_a_sha256": _sha256_bytes(first_bytes),
        "run_b_sha256": _sha256_bytes(second_bytes),
        "render_blocked_count": sum(1 for item in first["records"] if item["lifecycle_envelope"]["pdf_status"] == "blocked"),
        "blocked_render_code": "external_converter_release_unpinned",
    }
    (args.output / "run-a.json").write_bytes(first_bytes)
    (args.output / "run-b.json").write_bytes(second_bytes)
    (args.output / "summary.json").write_bytes(_canonical_json(summary) + b"\n")
    if not summary["replay_byte_identical"] or summary["record_count"] != 278:
        raise SystemExit("readiness probe failed")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
