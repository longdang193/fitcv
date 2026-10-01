"""Build source-backed P0-B requirement-support benchmark fixture."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from fitcv.evidence import (
    build_required_skill_descriptors,
    canonicalize_skill,
    project_candidate_evidence,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def load_raw_jobs(path: Path) -> dict[str, dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    rows = value if isinstance(value, list) else value.get("records")
    if not isinstance(rows, list):
        raise ValueError(f"Raw job snapshot has no records list: {path}")
    jobs: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not str(row.get("id") or ""):
            raise ValueError("Raw job snapshot contains record without id")
        job_id = str(row["id"])
        if job_id in jobs:
            raise ValueError(f"Duplicate raw job id: {job_id}")
        jobs[job_id] = row
    return jobs


def _field_evidence(profile: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    fields = {
        "experiences": ("role", "company", "start", "end"),
        "education": ("degree", "field", "institution", "start", "end"),
        "languages": ("name", "level", "read", "write", "speak", "native"),
        "skills": ("name", "level"),
    }
    for section, names in fields.items():
        for index, parent in enumerate(profile.get(section) or []):
            parent_id = str(parent.get("id") or "")
            if not parent_id:
                identity = str(parent.get("name") or parent.get("role") or parent.get("degree") or index)
                parent_id = "profile_" + hashlib.sha256(
                    f"{section}\0{identity}".encode("utf-8")
                ).hexdigest()[:16]
            for name in names:
                text = str(parent.get(name) or "").strip()
                if not text:
                    continue
                source_ref = f"{section}/{parent_id}/{name}"
                evidence_id = "ev_profile_" + hashlib.sha256(
                    f"{source_ref}\0{text}".encode("utf-8")
                ).hexdigest()[:16]
                items.append(
                    {
                        "schema_version": "candidate-evidence.v1",
                        "evidence_id": evidence_id,
                        "kind": "canonical_profile_field",
                        "title": name,
                        "text": text,
                        "source_section": section,
                        "parent_id": parent_id,
                        "source_ref": source_ref,
                        "source_refs": [],
                        "scoring_context": text,
                        "evidence_type": "canonical_profile_field",
                        "name": text,
                        "business_value": text,
                        "skills": [text] if section == "skills" and name == "name" else [],
                        "role": str(parent.get("role") or parent.get("degree") or parent.get("name") or ""),
                        "company": str(parent.get("company") or parent.get("institution") or ""),
                    }
                )
    return items


def _profile_evidence(profile: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    projected = project_candidate_evidence(profile)
    fields = _field_evidence(profile)
    by_ref: dict[str, str] = {}
    items: list[dict[str, Any]] = []
    for item in [*projected, *fields]:
        source_ref = str(item.get("source_ref") or "")
        evidence_id = str(item.get("evidence_id") or "")
        if not source_ref or not evidence_id:
            raise ValueError("Profile projection contains evidence without source_ref/evidence_id")
        if source_ref in by_ref and by_ref[source_ref] != evidence_id:
            raise ValueError(f"Conflicting profile evidence source_ref: {source_ref}")
        by_ref[source_ref] = evidence_id
        items.append(copy.deepcopy(item))
    unique: dict[str, dict[str, Any]] = {}
    for item in items:
        unique[str(item["evidence_id"])] = item
    return list(unique.values()), by_ref


def _raw_description(job: dict[str, Any], source_id: str) -> str:
    description = str(job.get("description") or "")
    if not description:
        raise ValueError(f"Raw job {source_id} has no description")
    expected_hash = str(job.get("description_sha256") or "")
    actual_hash = hashlib.sha256(description.encode("utf-8")).hexdigest()
    if expected_hash and expected_hash != actual_hash:
        raise ValueError(f"Raw job description hash mismatch: {source_id}")
    return description


def _job_context(case: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    requirements = list(case.get("requirements") or [])
    texts = [str(row.get("requirement_text") or "").strip() for row in requirements]
    if not texts or any(not text for text in texts):
        raise ValueError(f"Case {case.get('case_id')} contains empty requirement text")
    entities = [
        {
            "raw_text": text,
            "canonical": canonicalize_skill(text),
            "source_requirement_id": str(row["requirement_id"]),
        }
        for row, text in zip(requirements, texts)
    ]
    description = _raw_description(job, str(case["source_record_id"]))
    return {
        "job_url": str(job.get("jobUrl") or ""),
        "title": str(job.get("title") or case.get("title") or ""),
        "job_family": "source-backed-p0b",
        "domain": str(job.get("sector") or ""),
        "source_record_id": str(case["source_record_id"]),
        "source_description_sha256": hashlib.sha256(description.encode("utf-8")).hexdigest(),
        "source_description": description,
        "required_skills": texts,
        "required_skills_canonical": [canonicalize_skill(text) for text in texts],
        "required_skill_entities": entities,
        "responsibilities": texts,
        "baseline_fit": 0.8,
        "baseline_fit_label": "strong",
    }


def _runtime_mapping(descriptor: dict[str, Any]) -> dict[str, str]:
    runtime_descriptor_ref = str(descriptor.get("requirement_id") or "").strip()
    runtime_requirement_instance_id = str(
        descriptor.get("requirement_instance_id") or runtime_descriptor_ref
    ).strip()
    if not runtime_descriptor_ref or not runtime_requirement_instance_id:
        raise ValueError("Runtime descriptor mapping is incomplete")
    return {
        "runtime_descriptor_ref": runtime_descriptor_ref,
        "runtime_requirement_instance_id": runtime_requirement_instance_id,
        "mapping_source": "source_requirement_id",
    }


def build_fixture(packet: dict[str, Any], profile: dict[str, Any], jobs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    projected_items, field_refs = _profile_evidence(profile)
    projected_ids = {str(item["evidence_id"]) for item in projected_items}
    scenarios: list[dict[str, Any]] = []
    profiles: dict[str, Any] = {}
    job_contexts: dict[str, Any] = {}
    expected_maps: dict[str, dict[str, list[str]]] = {}
    acceptance_rows: dict[str, Any] = {}
    fixture_profile = {
        "schema_version": "candidate-profile.v2",
        "name": str(profile.get("name") or "P0-B source-backed benchmark candidate"),
        "experiences": [],
        "education": [],
        "projects": [],
        "achievements": [],
        "certifications": [],
        "volunteering": [],
        "languages": [],
        "skills": [],
        "role_families": [],
        "domain_tags": [],
        "responsibility_themes": [],
    }

    for case in packet.get("cases") or []:
        source_id = str(case.get("source_record_id") or "")
        if source_id not in jobs:
            raise ValueError(f"Missing raw job record: {source_id}")
        scenario_id = f"p0b-{source_id}"
        profile_ref = f"profile-{source_id}"
        job_ref = f"job-{source_id}"
        support_ref = f"support-{source_id}"
        context = _job_context(case, jobs[source_id])
        descriptors = build_required_skill_descriptors(context)
        descriptor_by_source_id: dict[str, dict[str, Any]] = {}
        for descriptor in descriptors:
            source_requirement_id = str(descriptor.get("source_requirement_id") or "").strip()
            if not source_requirement_id:
                raise ValueError("Runtime descriptor mapping requires source_requirement_id")
            if source_requirement_id in descriptor_by_source_id:
                raise ValueError(f"Duplicate runtime descriptor mapping: {source_requirement_id}")
            descriptor_by_source_id[source_requirement_id] = descriptor
        support_map: dict[str, list[str]] = {
            source_requirement_id: []
            for source_requirement_id in descriptor_by_source_id
        }
        rows: list[dict[str, Any]] = []
        seen_requirement_ids: set[str] = set()
        for requirement in case.get("requirements") or []:
            requirement_id = str(requirement.get("requirement_id") or "").strip()
            if not requirement_id:
                raise ValueError("Reviewed requirement is missing source requirement_id")
            if requirement_id in seen_requirement_ids:
                raise ValueError(f"Duplicate reviewed requirement mapping: {requirement_id}")
            seen_requirement_ids.add(requirement_id)
            text = str(requirement["requirement_text"])
            descriptor = descriptor_by_source_id.get(requirement_id)
            if descriptor is None:
                raise ValueError(f"Requirement descriptor mapping missing: {requirement_id}")
            runtime_mapping = _runtime_mapping(descriptor)
            adjudication = dict(requirement.get("adjudication") or {})
            label = str(adjudication.get("final_support_verdict") or "")
            if label not in {"supported", "unknown", "unsupported"}:
                raise ValueError(f"Invalid final support verdict: {requirement_id}")
            evidence_ids: list[str] = []
            for evidence in adjudication.get("minimal_sufficient_evidence") or []:
                evidence_id = str(evidence.get("evidence_id") or "")
                source_ref = str(evidence.get("source_ref") or "")
                mapped_id = evidence_id or field_refs.get(source_ref, "")
                if not mapped_id:
                    raise ValueError(f"Supported requirement has unresolved evidence: {requirement_id}")
                if mapped_id not in projected_ids:
                    raise ValueError(f"Evidence not present in canonical projection: {mapped_id}")
                evidence_ids.append(mapped_id)
            if label == "supported":
                if not evidence_ids:
                    raise ValueError(f"Supported requirement has no evidence: {requirement_id}")
                support_map[requirement_id] = list(dict.fromkeys(evidence_ids))
            minimal_sufficient_evidence = []
            for evidence in adjudication.get("minimal_sufficient_evidence") or []:
                if not isinstance(evidence, dict):
                    raise ValueError(f"Evidence link mapping is not an object: {requirement_id}")
                minimal_sufficient_evidence.append({**copy.deepcopy(evidence), **runtime_mapping})
            rows.append({
                "requirement_id": requirement_id,
                "requirement_text": text,
                "final_support_verdict": label,
                "benchmark_requirement_ref": requirement_id,
                **runtime_mapping,
                "expected_evidence_ids": support_map[requirement_id],
                "minimal_sufficient_evidence": minimal_sufficient_evidence,
            })
        if len(seen_requirement_ids) != len(case.get("requirements") or []):
            raise ValueError(f"Runtime descriptor mapping count mismatch: {source_id}")
        acceptance_rows[scenario_id] = rows
        profiles[profile_ref] = {
            **copy.deepcopy(fixture_profile),
            "_projected_evidence_pool": copy.deepcopy(projected_items),
        }
        job_contexts[job_ref] = context
        expected_maps[support_ref] = support_map
        scenarios.append({
            "scenario_id": scenario_id,
            "purpose": "human-accepted P0-B source-backed requirement support",
            "measurement_mode": "accepted_evidence_links",
            "profile_ref": profile_ref,
            "job_context_ref": job_ref,
            "expected_support_ref": support_ref,
            "evidence_budget": 5,
            "top_k": 5,
            "validation_case_ids": [f"validate-{source_id}"],
        })

    skill_names = [str(item.get("name") or "") for item in profile.get("skills") or [] if item.get("name")]
    validation_cases = [
        {
            "case_id": f"validate-{case['source_record_id']}",
            "cv_text": "# Candidate\n## Skills\n" + ", ".join(skill_names),
            "expected_valid": True,
            "expected_violation_class": "none",
        }
        for case in packet.get("cases") or []
    ]
    return {
        "evaluation_schema_version": 1,
        "fixture_schema_version": "p0b.requirement_support.source_backed.v2",
        "status": "source_backed_human_accepted_diagnostic",
        "source_provenance": {
            "packet_path": "data/fitcv-p0-corpus/p0b/p0b_holdout_170_human_accepted_v1.json",
            "packet_sha256": "",
            "profile_path": "data/candidate_profile.private.final.2026-09-27-reviewed-updated.yaml",
            "profile_sha256": "",
            "raw_snapshot_path": "data/linkedin-2026-09-29-16-10-19.json",
            "raw_snapshot_sha256": "",
        },
        "human_acceptance": copy.deepcopy(packet.get("human_acceptance") or {}),
        "label_semantics": copy.deepcopy(packet.get("support_semantics") or {}),
        "packet_counts": copy.deepcopy(packet.get("counts") or {}),
        "benchmark_scope": {
            "all_packet_requirements": sum(len(case.get("requirements") or []) for case in packet.get("cases") or []),
            "supported_packet_requirements": sum(
                1
                for rows in acceptance_rows.values()
                for row in rows
                if row["final_support_verdict"] == "supported"
            ),
            "expected_positive_requirement_refs": sum(
                bool(ids) for support in expected_maps.values() for ids in support.values()
            ),
            "promotion_eligible": False,
            "promotion_status": "blocked_until_benchmark_gate_review",
        },
        "acceptance_rows": acceptance_rows,
        "evaluation_source": {
            "projection": "fitcv.evidence.project_candidate_evidence plus deterministic canonical profile fields",
            "raw_job_text_verified": True,
            "reviewer_judgments_preserved": True,
        },
        "profiles": profiles,
        "job_contexts": job_contexts,
        "expected_support_maps": expected_maps,
        "scenarios": scenarios,
        "top_k": 5,
        "prompt_template": "## Skills\n...",
        "validation_cases": validation_cases,
        "validation": {
            "cv_text": "# Candidate\n## Skills\n" + ", ".join(skill_names),
            "config": {
                "required_cv_sections": ["Skills"],
                "cv_max_pages": 2,
                "cv": {"validation": {"allow_profile_skill_outside_selected_evidence": True}},
            },
        },
    }


def write_fixture(packet_path: Path, profile_path: Path, raw_path: Path, output_path: Path) -> Path:
    packet_path = packet_path.resolve()
    profile_path = profile_path.resolve()
    raw_path = raw_path.resolve()
    output_path = output_path.resolve()
    packet = load_json(packet_path)
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    if not isinstance(profile, dict):
        raise ValueError(f"Expected YAML object: {profile_path}")
    jobs = load_raw_jobs(raw_path)
    fixture = build_fixture(packet, profile, jobs)
    fixture["source_provenance"].update({
        "packet_sha256": sha256(packet_path),
        "profile_sha256": sha256(profile_path),
        "raw_snapshot_sha256": sha256(raw_path),
    })
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(fixture, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "p0b.requirement_support.source_backed_manifest.v2",
        "status": "fixture_frozen_benchmark_gate_pending",
        "fixture_path": output_path.relative_to(REPO_ROOT).as_posix(),
        "fixture_sha256": sha256(output_path),
        "packet_path": fixture["source_provenance"]["packet_path"],
        "packet_sha256": fixture["source_provenance"]["packet_sha256"],
        "profile_path": fixture["source_provenance"]["profile_path"],
        "profile_sha256": fixture["source_provenance"]["profile_sha256"],
        "raw_snapshot_path": fixture["source_provenance"]["raw_snapshot_path"],
        "raw_snapshot_sha256": fixture["source_provenance"]["raw_snapshot_sha256"],
        "counts": {
            "scenarios": len(fixture["scenarios"]),
            "requirements": fixture["benchmark_scope"]["all_packet_requirements"],
            "supported_requirements": fixture["benchmark_scope"]["supported_packet_requirements"],
            "expected_positive_requirement_refs": fixture["benchmark_scope"]["expected_positive_requirement_refs"],
        },
        "packet_counts": fixture["packet_counts"],
        "human_acceptance": fixture["human_acceptance"],
        "reviewer_judgments_preserved": True,
        "promotion_eligible": False,
        "promotion_status": "blocked_until_benchmark_gate_review",
    }
    manifest_path = output_path.with_name(f"{output_path.stem}_manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--raw-snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(write_fixture(args.packet, args.profile, args.raw_snapshot, args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
