from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from scripts.render_acceptance_state import render_acceptance_state


def _canonical_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")


def _valid_state() -> dict[str, object]:
    return {
        "schema_version": "fitcv.acceptance_state.v2",
        "repository": "longdang193/fitcv",
        "evaluation_freeze_commit": "a" * 40,
        "sanitizer_version": "fitcv-p0-corpus-sanitizer.v1",
        "contract_versions": {"corpus": "p0.public.v1"},
        "corpus_manifests": ["data/manifest.json"],
        "statuses": {
            "p0_a": "rejected",
            "p0_b": "blocked",
            "p0_c": "protected",
            "p1_a": "maintenance_only",
            "p1_b": "measurement_only",
            "p1_c": "deferred",
            "p2": "deferred",
        },
        "status_dimensions": {
            "p0_a": {"implementation_status": "rejected", "acceptance_status": "rejected", "measurement_status": "not_applicable"},
            "p0_b": {"implementation_status": "verified", "acceptance_status": "passed", "measurement_status": "frozen_scope_only"},
            "p0_c": {"implementation_status": "verified", "acceptance_status": "passed", "measurement_status": "frozen_scope_only"},
            "p1_a": {"implementation_status": "maintenance_only", "acceptance_status": "maintenance_only", "measurement_status": "not_applicable"},
            "p1_b": {"implementation_status": "verified", "acceptance_status": "passed", "measurement_status": "incomplete"},
            "p1_c": {"implementation_status": "deferred", "acceptance_status": "deferred", "measurement_status": "not_applicable"},
            "p2": {"implementation_status": "deferred", "acceptance_status": "deferred", "measurement_status": "not_applicable"},
        },
        "support_thresholds": {
            "maximum_pair_false_positives": 0,
            "minimum_review_completeness": 1.0,
            "minimum_oracle_coverage": 1.0,
            "support_recall_threshold": None,
        },
        "evidence_paths": ["docs/evidence.md"],
        "runtime_efficiency": {
            "measurement_status": "incomplete",
            "baseline_evidence": {
                "json": "docs/runtime-efficiency.json",
                "markdown": "docs/runtime-efficiency.md",
            },
            "accepted_artifact_and_total_workload_metrics": True,
            "p1_c": "deferred",
            "p2": "deferred",
        },
    }


def test_render_acceptance_state_is_deterministic(tmp_path: Path) -> None:
    source = tmp_path / "state.json"
    output = tmp_path / "rendered.json"
    (tmp_path / "data").mkdir()
    (tmp_path / "data/manifest.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/evidence.md").write_text("evidence\n", encoding="utf-8")
    (tmp_path / "docs/runtime-efficiency.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "docs/runtime-efficiency.md").write_text("runtime\n", encoding="utf-8")
    source.write_text(json.dumps(_valid_state()), encoding="utf-8")

    first = render_acceptance_state(source, output, repo_root=tmp_path)
    first_bytes = output.read_bytes()
    second = render_acceptance_state(source, output, repo_root=tmp_path)

    assert first == second
    assert first_bytes == output.read_bytes()
    assert first["evaluation_freeze_commit"] == "a" * 40


def test_committed_acceptance_state_matches_fresh_render(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    rendered = tmp_path / "acceptance_state.json"
    render_acceptance_state(
        repo_root / "config/acceptance_state.yaml",
        rendered,
        repo_root=repo_root,
    )
    assert _canonical_bytes(rendered) == _canonical_bytes(repo_root / "artifacts/acceptance_state.json")


def test_committed_acceptance_registry_fixture_hashes_match_declared_input() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    registry = yaml.safe_load((repo_root / "config/evidence_registry.yaml").read_text(encoding="utf-8"))
    expected = hashlib.sha256(_canonical_bytes(repo_root / "config/acceptance_state.yaml")).hexdigest()
    records = [
        record
        for record in registry["records"]
        if record.get("declared_inputs") == ["config/acceptance_state.yaml"]
    ]

    assert records
    assert {record["fixture_sha256"] for record in records} == {expected}
    assert {record["material_metrics_sha256"] for record in records} == {expected}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("evaluation_freeze_commit", ""),
        ("repository", "other/repo"),
        ("statuses", {"p0_a": "unknown"}),
    ],
)
def test_render_acceptance_state_rejects_invalid_contract(
    tmp_path: Path, field: str, value: object
) -> None:
    state = _valid_state()
    state[field] = value
    source = tmp_path / "state.json"
    output = tmp_path / "rendered.json"
    source.write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(ValueError):
        render_acceptance_state(source, output, repo_root=tmp_path)


def test_render_acceptance_state_rejects_missing_references(tmp_path: Path) -> None:
    source = tmp_path / "state.json"
    output = tmp_path / "rendered.json"
    state = _valid_state()
    state["evidence_paths"] = ["docs/missing.md"]
    source.write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(ValueError, match="missing reference"):
        render_acceptance_state(source, output, repo_root=tmp_path)


def test_render_acceptance_state_rejects_runtime_efficiency_claim_without_deferrals(tmp_path: Path) -> None:
    source = tmp_path / "state.json"
    output = tmp_path / "rendered.json"
    state = _valid_state()
    state["runtime_efficiency"] = {
        "measurement_status": "measured",
        "baseline_evidence": {"json": "docs/runtime-efficiency.json", "markdown": "docs/runtime-efficiency.md"},
        "accepted_artifact_and_total_workload_metrics": True,
        "p1_c": "complete",
        "p2": "complete",
    }
    source.write_text(json.dumps(state), encoding="utf-8")
    (tmp_path / "data").mkdir()
    (tmp_path / "data/manifest.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/evidence.md").write_text("evidence\n", encoding="utf-8")
    (tmp_path / "docs/runtime-efficiency.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "docs/runtime-efficiency.md").write_text("runtime\n", encoding="utf-8")

    with pytest.raises(ValueError, match="runtime_efficiency"):
        render_acceptance_state(source, output, repo_root=tmp_path)


def test_render_acceptance_state_rejects_duplicate_current_evidence_claim(tmp_path: Path) -> None:
    source = tmp_path / "state.json"
    output = tmp_path / "rendered.json"
    state = _valid_state()
    state["evidence_registry"] = "config/evidence_registry.yaml"
    (tmp_path / "config").mkdir()
    (tmp_path / "config/evidence_registry.yaml").write_text(
        """
schema_version: fitcv.evidence_registry.v1
records:
  - evidence_id: evidence-1
    claim: p1_a
    schema_version: fitcv.acceptance_state.v2
    source_commit: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    declared_input_fingerprint: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
    fixture_sha256: cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc
    cohort_id: cohort-1
    cohort_type: acceptance_fixture
    material_metrics_sha256: dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd
    artifact_paths: [docs/evidence.md]
    status: current
  - evidence_id: evidence-2
    claim: p1_a
    schema_version: fitcv.acceptance_state.v2
    source_commit: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    declared_input_fingerprint: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
    fixture_sha256: cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc
    cohort_id: cohort-1
    cohort_type: acceptance_fixture
    material_metrics_sha256: dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd
    artifact_paths: [docs/evidence.md]
    status: current
""",
        encoding="utf-8",
    )
    (tmp_path / "data").mkdir()
    (tmp_path / "data/manifest.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/evidence.md").write_text("evidence\n", encoding="utf-8")
    (tmp_path / "docs/runtime-efficiency.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "docs/runtime-efficiency.md").write_text("runtime\n", encoding="utf-8")
    source.write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate current claim"):
        render_acceptance_state(source, output, repo_root=tmp_path)
