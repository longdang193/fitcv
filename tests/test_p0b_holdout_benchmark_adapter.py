from __future__ import annotations

from pathlib import Path

import yaml

from fitcv.evidence import project_candidate_evidence
from scripts.build_p0b_holdout_benchmark_fixture import build_fixture, load_json, load_raw_jobs, write_fixture


ROOT = Path(__file__).parents[1]
P0B = ROOT / "data" / "fitcv-p0-corpus" / "p0b"


def test_p0b_adapter_preserves_all_human_accepted_rows_and_evidence() -> None:
    packet = load_json(P0B / "p0b_holdout_170_human_accepted_v1.json")
    profile = yaml.safe_load((ROOT / "data/candidate_profile.private.final.2026-09-27-reviewed-updated.yaml").read_text(encoding="utf-8"))
    jobs = load_raw_jobs(ROOT / "data/linkedin-2026-09-29-16-10-19.json")

    fixture = build_fixture(packet, profile, jobs)
    assert fixture["benchmark_scope"]["all_packet_requirements"] == 170
    assert fixture["benchmark_scope"]["supported_packet_requirements"] == 17
    assert len(fixture["scenarios"]) == 10
    assert sum(len(value) for value in fixture["acceptance_rows"].values()) == 170
    assert all(
        str(entity.get("source_requirement_id") or "")
        for context in fixture["job_contexts"].values()
        for entity in context["required_skill_entities"]
    )
    assert all(
        requirement_id.startswith("req_")
        for support in fixture["expected_support_maps"].values()
        for requirement_id in support
    )
    assert all(
        row["final_support_verdict"] in {"supported", "unknown", "unsupported"}
        for rows in fixture["acceptance_rows"].values()
        for row in rows
    )
    projected_ids = {item["evidence_id"] for item in project_candidate_evidence(profile)}
    assert all(
        evidence_id in projected_ids or evidence_id.startswith("ev_profile_")
        for support in fixture["expected_support_maps"].values()
        for evidence_ids in support.values()
        for evidence_id in evidence_ids
    )


def test_p0b_adapter_emits_one_runtime_mapping_per_reviewed_requirement() -> None:
    packet = load_json(P0B / "p0b_holdout_170_human_accepted_v1.json")
    profile = yaml.safe_load((ROOT / "data/candidate_profile.private.final.2026-09-27-reviewed-updated.yaml").read_text(encoding="utf-8"))
    jobs = load_raw_jobs(ROOT / "data/linkedin-2026-09-29-16-10-19.json")

    fixture = build_fixture(packet, profile, jobs)
    rows = [row for case_rows in fixture["acceptance_rows"].values() for row in case_rows]

    assert len(rows) == 170
    assert len({row["requirement_id"] for row in rows}) == 170
    assert all(row["mapping_source"] == "source_requirement_id" for row in rows)
    assert all(row["runtime_descriptor_ref"].startswith("required_skill:") for row in rows)
    assert all(row["runtime_requirement_instance_id"] for row in rows)
    assert all(
        link["runtime_descriptor_ref"] == row["runtime_descriptor_ref"]
        and link["runtime_requirement_instance_id"] == row["runtime_requirement_instance_id"]
        and link["mapping_source"] == "source_requirement_id"
        for row in rows
        for link in row["minimal_sufficient_evidence"]
    )


def test_p0b_adapter_fails_closed_for_missing_source_job() -> None:
    packet = load_json(P0B / "p0b_holdout_170_human_accepted_v1.json")
    profile = yaml.safe_load((ROOT / "data/candidate_profile.private.final.2026-09-27-reviewed-updated.yaml").read_text(encoding="utf-8"))
    jobs = load_raw_jobs(ROOT / "data/linkedin-2026-09-29-16-10-19.json")
    jobs.pop(str(packet["cases"][0]["source_record_id"]))

    try:
        build_fixture(packet, profile, jobs)
    except ValueError as exc:
        assert "Missing raw job record" in str(exc)
    else:
        raise AssertionError("missing raw source must fail closed")


def test_p0b_adapter_accepts_relative_output_path(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(ROOT)
    output = Path(".tmp/p0b-adapter-relative-test.json")
    write_fixture(
        Path("data/fitcv-p0-corpus/p0b/p0b_holdout_170_human_accepted_v1.json"),
        Path("data/candidate_profile.private.final.2026-09-27-reviewed-updated.yaml"),
        Path("data/linkedin-2026-09-29-16-10-19.json"),
        output,
    )
    assert output.resolve().exists()
    assert output.with_name(f"{output.stem}_manifest.json").resolve().exists()
    output.resolve().unlink()
    output.with_name(f"{output.stem}_manifest.json").resolve().unlink()
