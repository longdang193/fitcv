from __future__ import annotations

from pathlib import Path

import yaml

from fitcv.evidence import project_candidate_evidence
from scripts.build_p0b_holdout_benchmark_fixture import build_fixture, load_json, load_raw_jobs, write_fixture


ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "p0b"


def _inputs() -> tuple[dict, dict, dict[str, dict]]:
    packet = load_json(FIXTURES / "sanitized_packet.json")
    profile = yaml.safe_load((FIXTURES / "sanitized_profile.yaml").read_text(encoding="utf-8"))
    jobs = load_raw_jobs(FIXTURES / "sanitized_jobs.json")
    return packet, profile, jobs


def test_p0b_adapter_preserves_sanitized_rows_and_evidence() -> None:
    packet, profile, jobs = _inputs()
    fixture = build_fixture(packet, profile, jobs)

    assert fixture["benchmark_scope"]["all_packet_requirements"] == 2
    assert fixture["benchmark_scope"]["supported_packet_requirements"] == 0
    assert len(fixture["scenarios"]) == 1
    assert sum(len(value) for value in fixture["acceptance_rows"].values()) == 2
    projected_ids = {item["evidence_id"] for item in project_candidate_evidence(profile)}
    assert all(
        evidence_id in projected_ids or evidence_id.startswith("ev_profile_")
        for support in fixture["expected_support_maps"].values()
        for evidence_ids in support.values()
        for evidence_id in evidence_ids
    )


def test_p0b_adapter_emits_one_runtime_mapping_per_reviewed_requirement() -> None:
    packet, profile, jobs = _inputs()
    fixture = build_fixture(packet, profile, jobs)
    rows = [row for case_rows in fixture["acceptance_rows"].values() for row in case_rows]

    assert len(rows) == 2
    assert len({row["requirement_id"] for row in rows}) == 2
    assert all(row["mapping_source"] == "source_requirement_id" for row in rows)
    assert all(row["runtime_descriptor_ref"].startswith("required_skill:") for row in rows)
    assert all(row["runtime_requirement_instance_id"] for row in rows)


def test_p0b_adapter_fails_closed_for_missing_source_job() -> None:
    packet, profile, jobs = _inputs()
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
        FIXTURES / "sanitized_packet.json",
        FIXTURES / "sanitized_profile.yaml",
        FIXTURES / "sanitized_jobs.json",
        output,
    )
    assert output.resolve().exists()
    assert output.with_name(f"{output.stem}_manifest.json").resolve().exists()
    output.resolve().unlink()
    output.with_name(f"{output.stem}_manifest.json").resolve().unlink()
