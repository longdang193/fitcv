from __future__ import annotations

import json
from pathlib import Path

from scripts import verify_fitcv_acceptance as verifier
from scripts.benchmark_cv_efficiency import material_report_digest
from scripts.verify_fitcv_acceptance import (
    _run_current_contract_evidence_check,
    _run_experiment_report_check,
    _run_runtime_efficiency_evidence_check,
    build_acceptance_report,
    format_acceptance_summary,
)
from scripts.run_fitcv_repair_experiment import DECLARED_INPUTS


def test_experiment_report_check_rejects_unavailable_report(tmp_path: Path) -> None:
    report_path = tmp_path / "experiment.json"
    markdown_path = tmp_path / "experiment.md"
    report_path.write_text(
        json.dumps({"status": "incomplete", "selection": {}, "input_manifest": {}}),
        encoding="utf-8",
    )
    markdown_path.write_text("## CORRECTNESS\n## PRODUCT PARITY\n## EFFICIENCY\n## HUMAN EFFORT\n", encoding="utf-8")

    result = _run_experiment_report_check(report_path, markdown_path, tmp_path)

    assert result["passed"] is False
    assert "experiment_report_incomplete" in result["failures"]
    assert "experiment_input_fingerprint_missing" in result["failures"]
    assert "experiment_peer_json_required" in result["failures"]


def test_experiment_report_check_rejects_stale_material_dependency_fingerprint(
    monkeypatch, tmp_path: Path
) -> None:
    fixture = tmp_path / "tests" / "fixtures" / "fitcv-p1ab-repair-experiment.json"
    fixture.parent.mkdir(parents=True)
    fixture.write_text("fixture", encoding="utf-8")
    dependency = tmp_path / "src" / "fitcv" / "llm_runtime.py"
    dependency.parent.mkdir(parents=True)
    dependency.write_text("baseline", encoding="utf-8")
    monkeypatch.setattr(verifier, "DECLARED_INPUTS", ("src/fitcv/llm_runtime.py",))
    _, baseline_fingerprint = verifier._current_experiment_input_identity(tmp_path)

    manifest_path = tmp_path / "manifest.json"
    run_ids = [f"run-{index}" for index in range(10)]
    manifest = {
        "fixture_sha256": verifier.hashlib.sha256(fixture.read_bytes()).hexdigest(),
        "declared_input_fingerprint": baseline_fingerprint,
        "arm": "local_first",
        "repeat_count": 10,
        "database_path": "database.sqlite3",
        "declared_model": "model",
        "resolved_models": ["model"],
        "run_ids": run_ids,
        "runtime": "runtime",
        "source_commit": "new-commit",
        "working_tree_diff_sha256": "diff",
        "producer": {"mode": "provider_backed"},
        "cohort_setup": {"upstream_reuse_policy": "cold_first_then_frozen"},
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    report = {
        "status": "complete",
        "selection": {
            "current_contract_record_count": 10,
            "run_count": 10,
            "manifest_run_count_shortfall": 0,
            "run_ids": run_ids,
        },
        "input_manifest": {**manifest, "path": str(manifest_path)},
        "accepted_cv": {"recorded_acceptance_count": 10},
        "coverage": {name: {"complete": True} for name in (
            "timing", "cost", "attribution", "page_fit", "page_fit_success",
            "review_questions", "human_actions", "resolution_reuse",
        )},
        "timing": {"generation_elapsed_ms": 1, "generation_timing_coverage": {"measured": 10}},
        "run_job_diversity": {"run_count": 10, "job_type_count": 2},
    }
    report["material_metrics_sha256"] = material_report_digest(report)
    report_path = tmp_path / "experiment.json"
    markdown_path = tmp_path / "experiment.md"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    markdown_path.write_text("## CORRECTNESS\n## PRODUCT PARITY\n## EFFICIENCY\n## HUMAN EFFORT\n", encoding="utf-8")
    dependency.write_text("changed", encoding="utf-8")

    result = verifier._run_experiment_report_check(
        report_path, markdown_path, tmp_path, current_commit="new-commit", require_peer=False
    )

    assert result["passed"] is False
    assert "experiment_declared_input_fingerprint_not_current" in result["failures"]


def test_experiment_report_check_rejects_non_object_json(tmp_path: Path) -> None:
    report_path = tmp_path / "experiment.json"
    markdown_path = tmp_path / "experiment.md"
    report_path.write_text("[]", encoding="utf-8")
    markdown_path.write_text("## CORRECTNESS\n## PRODUCT PARITY\n## EFFICIENCY\n## HUMAN EFFORT\n", encoding="utf-8")

    result = _run_experiment_report_check(report_path, markdown_path, tmp_path)

    assert result["passed"] is False
    assert "experiment_json_object_required" in result["failures"]


def test_experiment_report_check_rejects_mismatched_peer_analysis_inputs(tmp_path: Path) -> None:
    report_path = tmp_path / "experiment.json"
    peer_path = tmp_path / "peer.json"
    markdown_path = tmp_path / "experiment.md"
    base = {"analysis_input_identity": [{"fingerprints": ["one"], "selected_evidence_ids": ["ev-1"]}]}
    report_path.write_text(json.dumps(base), encoding="utf-8")
    peer_path.write_text(json.dumps({"analysis_input_identity": [{"fingerprints": ["two"], "selected_evidence_ids": ["ev-2"]}]}), encoding="utf-8")
    markdown_path.write_text("## CORRECTNESS\n## PRODUCT PARITY\n## EFFICIENCY\n## HUMAN EFFORT\n", encoding="utf-8")

    result = _run_experiment_report_check(report_path, markdown_path, tmp_path, peer_path)

    assert result["passed"] is False
    assert "experiment_peer_manifest_path_missing" in result["failures"]


def test_experiment_report_check_rejects_unbound_non_provider_peer(tmp_path: Path) -> None:
    report_path = tmp_path / "experiment.json"
    peer_path = tmp_path / "peer.json"
    markdown_path = tmp_path / "experiment.md"
    manifest_path = tmp_path / "manifest.json"
    peer_manifest_path = tmp_path / "peer-manifest.json"
    run_ids = [f"run-{index}" for index in range(10)]
    common = {
        "fixture_sha256": "fixture",
        "declared_input_fingerprint": "input",
        "repeat_count": 10,
        "database_path": "database.sqlite3",
        "declared_model": "model",
        "resolved_models": ["resolved"],
        "run_ids": run_ids,
        "runtime": "runtime",
        "source_commit": "old-commit",
        "working_tree_diff_sha256": "diff",
        "producer": {"mode": "manifest_only"},
        "cohort_setup": {"upstream_reuse_policy": "cold_first_then_frozen"},
    }
    manifest = {**common, "arm": "local_first"}
    peer_manifest = {**common, "arm": "local_first"}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    peer_manifest_path.write_text(json.dumps(peer_manifest), encoding="utf-8")
    report = {
        "status": "complete",
        "selection": {
            "current_contract_record_count": 10,
            "run_count": 10,
            "manifest_run_count_shortfall": 0,
            "run_ids": run_ids,
        },
        "input_manifest": {**manifest, "path": str(manifest_path)},
        "analysis_input_identity": [{"fingerprints": ["same"]}],
        "accepted_cv": {"recorded_acceptance_count": 10},
        "coverage": {name: {"complete": True} for name in (
            "timing", "cost", "attribution", "page_fit", "page_fit_success",
            "review_questions", "human_actions", "resolution_reuse",
        )},
        "timing": {"generation_elapsed_ms": 1, "generation_timing_coverage": {"measured": 10}},
        "run_job_diversity": {"run_count": 10, "job_type_count": 2},
    }
    peer_report = {**report, "input_manifest": {**peer_manifest, "path": str(peer_manifest_path)}}
    peer_report["analysis_input_identity"] = [{"fingerprints": ["different"], "selected_evidence_ids": ["ev-2"]}]
    report["material_metrics_sha256"] = material_report_digest(report)
    peer_report["material_metrics_sha256"] = material_report_digest(peer_report)
    report_path.write_text(json.dumps(report), encoding="utf-8")
    peer_report["status"] = "incomplete"
    peer_report["material_metrics_sha256"] = material_report_digest(peer_report)
    peer_path.write_text(json.dumps(peer_report), encoding="utf-8")
    markdown_path.write_text("## CORRECTNESS\n## PRODUCT PARITY\n## EFFICIENCY\n## HUMAN EFFORT\n", encoding="utf-8")
    for relative in set(DECLARED_INPUTS) | {"tests/fixtures/fitcv-p1ab-repair-experiment.json"}:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("current-input", encoding="utf-8")

    result = _run_experiment_report_check(report_path, markdown_path, tmp_path, peer_path, "new-commit")

    assert result["passed"] is False
    assert "experiment_source_commit_not_current" in result["failures"]
    assert "experiment_provider_backed_required" in result["failures"]
    assert "experiment_declared_input_fingerprint_not_current" in result["failures"]
    assert "experiment_peer_arm_must_differ" in result["failures"]
    assert "experiment_peer_report_incomplete" in result["failures"]
    assert "experiment_peer_analysis_input_identity_not_identical" in result["failures"]


def test_experiment_report_check_rejects_incomplete_cohort_metadata(tmp_path: Path) -> None:
    report_path = tmp_path / "experiment.json"
    markdown_path = tmp_path / "experiment.md"
    report = {
        "status": "complete",
        "selection": {
            "current_contract_record_count": 1,
            "run_count": 1,
            "manifest_run_count_shortfall": 0,
        },
        "input_manifest": {
            "declared_input_fingerprint": "input",
            "fixture_sha256": "fixture",
            "arm": "local_first",
            "repeat_count": 10,
            "run_ids": ["run-1"],
        },
        "timing": {"generation_elapsed_ms": 1, "generation_timing_coverage": {"measured": 1}},
        "coverage": {},
        "run_job_diversity": {"run_count": 1, "job_type_count": 1},
    }
    report["material_metrics_sha256"] = material_report_digest(report)
    report_path.write_text(json.dumps(report), encoding="utf-8")
    markdown_path.write_text("## CORRECTNESS\n## PRODUCT PARITY\n## EFFICIENCY\n## HUMAN EFFORT\n", encoding="utf-8")

    result = _run_experiment_report_check(report_path, markdown_path, tmp_path)

    assert result["passed"] is False
    assert "experiment_manifest_run_ids_invalid" in result["failures"]
    assert "experiment_run_count_invalid" in result["failures"]
    assert "experiment_coverage_incomplete_attribution" in result["failures"]
    assert "experiment_job_diversity_insufficient" in result["failures"]


def _state(tmp_path: Path, *, freeze: str = "a" * 40) -> dict[str, object]:
    manifest = tmp_path / "manifest.json"
    evidence = tmp_path / "evidence.md"
    runtime_json = tmp_path / "runtime-efficiency.json"
    runtime_markdown = tmp_path / "runtime-efficiency.md"
    manifest.write_text("{}", encoding="utf-8")
    evidence.write_text("evidence", encoding="utf-8")
    runtime_json.write_text("{}", encoding="utf-8")
    runtime_markdown.write_text("runtime", encoding="utf-8")
    return {
        "schema_version": "fitcv.acceptance_state.v2",
        "repository": "longdang193/fitcv",
        "evaluation_freeze_commit": freeze,
        "sanitizer_version": "fitcv-p0-corpus-sanitizer.v1",
        "contract_versions": {"corpus": "p0.public.v1"},
        "corpus_manifests": ["manifest.json"],
        "evidence_paths": ["evidence.md"],
        "runtime_efficiency": {
            "measurement_status": "incomplete",
            "baseline_evidence": {"json": "runtime-efficiency.json", "markdown": "runtime-efficiency.md"},
            "accepted_artifact_and_total_workload_metrics": True,
            "p1_c": "deferred",
            "p2": "deferred",
        },
        "statuses": {
            "p0_a": "rejected",
            "p0_b": "passed",
            "p0_c": "passed",
            "p1_a": "maintenance_only",
            "p1_b": "passed",
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
            "support_recall_threshold": 1.0,
        },
    }


def _checks(passed: bool = True) -> dict[str, dict[str, object]]:
    return {
        priority: {"passed": passed, "measurement_status": "measured"}
        for priority in ("p0_b", "p0_c", "p1_b")
    }


def test_acceptance_verifier_accepts_frozen_input_commit_different_from_head(
    tmp_path: Path,
) -> None:
    report = build_acceptance_report(
        _state(tmp_path),
        repo_root=tmp_path,
        current_commit="b" * 40,
        checks=_checks(),
    )

    assert report["passed"] is True
    assert "evaluation_freeze_commit_stale" not in report["failures"]
    assert report["priorities"]["p0_b"]["acceptance_status"] == "passed"


def test_acceptance_verifier_uses_declared_measurement_status_when_check_does_not_report_one(
    tmp_path: Path,
) -> None:
    checks = {priority: {"passed": True} for priority in ("p0_b", "p0_c", "p1_b")}

    report = build_acceptance_report(
        _state(tmp_path),
        repo_root=tmp_path,
        current_commit="b" * 40,
        checks=checks,
    )

    assert report["priorities"]["p1_b"]["measurement_status"] == "incomplete"


def test_acceptance_verifier_surfaces_runtime_efficiency_status_and_deferrals(tmp_path: Path) -> None:
    report = build_acceptance_report(
        _state(tmp_path),
        repo_root=tmp_path,
        current_commit="b" * 40,
        checks=_checks(),
    )

    assert report["runtime_efficiency"]["measurement_status"] == "incomplete"
    assert report["runtime_efficiency"]["p1_c"] == "deferred"
    assert report["runtime_efficiency"]["p2"] == "deferred"


def test_acceptance_verifier_rejects_missing_manifest(tmp_path: Path) -> None:
    state = _state(tmp_path, freeze="b" * 40)
    state["corpus_manifests"] = ["missing.json"]

    report = build_acceptance_report(
        state,
        repo_root=tmp_path,
        current_commit="b" * 40,
        checks=_checks(),
    )

    assert report["passed"] is False
    assert any("missing reference" in reason for reason in report["failures"])


def test_acceptance_verifier_preserves_deferred_and_rejected_statuses(tmp_path: Path) -> None:
    report = build_acceptance_report(
        _state(tmp_path, freeze="b" * 40),
        repo_root=tmp_path,
        current_commit="b" * 40,
        checks=_checks(),
    )

    assert report["passed"] is True
    assert report["priorities"]["p0_a"]["acceptance_status"] == "rejected"
    assert report["priorities"]["p1_c"]["acceptance_status"] == "deferred"
    assert report["priorities"]["p2"]["acceptance_status"] == "deferred"


def test_acceptance_verifier_blocks_failed_passed_priority(tmp_path: Path) -> None:
    report = build_acceptance_report(
        _state(tmp_path, freeze="b" * 40),
        repo_root=tmp_path,
        current_commit="b" * 40,
        checks=_checks(False),
    )

    assert report["passed"] is False
    assert "p0_b_passed_claim_not_proven" in report["failures"]


def test_runtime_efficiency_evidence_check_requires_canonical_v3_report(tmp_path: Path) -> None:
    state = _state(tmp_path)
    runtime_json = tmp_path / "runtime-efficiency.json"
    runtime_markdown = tmp_path / "runtime-efficiency.md"
    runtime_report = {
        "schema_version": "fitcv_runtime_efficiency_baseline_v3",
        "evidence_status": "canonical",
        "workload": {"attempted_generation_job_count": 1},
        "timing": {"generation_elapsed_ms": 100, "generation_timing_coverage": {"measured": 1, "unavailable": 0}},
        "selection": {"run_count": 1},
    }
    runtime_report["material_metrics_sha256"] = material_report_digest(runtime_report)
    runtime_json.write_text(json.dumps(runtime_report), encoding="utf-8")
    runtime_markdown.write_text("Evidence status: `canonical`", encoding="utf-8")

    result = _run_runtime_efficiency_evidence_check(state, tmp_path)

    assert result["passed"] is True


def test_current_contract_evidence_rejects_dropped_attempted_outcome(tmp_path: Path) -> None:
    evidence_json = tmp_path / "current.json"
    evidence_markdown = tmp_path / "current.md"
    evidence_sha = tmp_path / "current.sha256"
    evidence = {
        "evidence_status": "canonical",
        "evidence_schema_version": "fitcv.p1_ab.current_contract.v1",
        "source_commit": "a" * 40,
        "fixture_sha256": "b" * 64,
        "source_fixture_sha256": "c" * 64,
        "selection": {"current_contract_record_count": 1, "historical_record_count": 0},
        "workload": {"attempted_generation_job_count": 2},
        "attempted_outcomes": [{"trace_id": "one"}],
        "accepted_cv": {"count": 1, "accepted_non_one_page_count": 0, "page_fit_success": {"fail": 0}},
        "coverage": {"page_fit": {"complete": True}, "page_fit_success": {"complete": True}},
        "attribution": {"unattributed_accepted_artifact_count": 0},
    }
    evidence_json.write_text(json.dumps(evidence), encoding="utf-8")
    evidence_markdown.write_text("Evidence status: `canonical`", encoding="utf-8")
    import hashlib

    evidence_sha.write_text(
        f"{hashlib.sha256(evidence_json.read_bytes()).hexdigest()}  {evidence_json.name}\n",
        encoding="utf-8",
    )

    result = _run_current_contract_evidence_check(
        {"current_contract_evidence": {"json": evidence_json.name, "markdown": evidence_markdown.name, "sha256": evidence_sha.name}},
        tmp_path,
    )

    assert result["passed"] is False
    assert "current_contract_evidence_outcomes_incomplete" in result["failures"]


def test_current_contract_evidence_digest_accepts_crlf_checkout(tmp_path: Path) -> None:
    evidence_json = tmp_path / "current.json"
    evidence_markdown = tmp_path / "current.md"
    evidence_sha = tmp_path / "current.sha256"
    evidence = {
        "evidence_status": "canonical",
        "evidence_schema_version": "fitcv.p1_ab.current_contract.v1",
        "source_commit": "a" * 40,
        "fixture_sha256": "b" * 64,
        "source_fixture_sha256": "c" * 64,
        "selection": {"current_contract_record_count": 1, "historical_record_count": 0},
        "workload": {"attempted_generation_job_count": 1},
        "attempted_outcomes": [{"trace_id": "one"}],
        "accepted_cv": {"count": 1, "accepted_non_one_page_count": 0, "page_fit_success": {"fail": 0}},
        "coverage": {"page_fit": {"complete": True}, "page_fit_success": {"complete": True}},
        "attribution": {"unattributed_accepted_artifact_count": 0},
    }
    payload = (json.dumps(evidence, indent=2) + "\n").replace("\n", "\r\n").encode("utf-8")
    evidence_json.write_bytes(payload)
    evidence_markdown.write_text("Evidence status: `canonical`", encoding="utf-8")
    import hashlib

    normalized_digest = hashlib.sha256(payload.replace(b"\r\n", b"\n")).hexdigest()
    evidence_sha.write_text(f"{normalized_digest}  {evidence_json.name}\n", encoding="utf-8")

    result = _run_current_contract_evidence_check(
        {"current_contract_evidence": {"json": evidence_json.name, "markdown": evidence_markdown.name, "sha256": evidence_sha.name}},
        tmp_path,
    )

    assert result["passed"] is True


def test_runtime_efficiency_measurement_gate_blocks_measured_claim_with_incomplete_coverage(
    tmp_path: Path,
) -> None:
    state = _state(tmp_path)
    state["runtime_efficiency"]["measurement_status"] = "measured"
    runtime_json = tmp_path / "runtime-efficiency.json"
    runtime_markdown = tmp_path / "runtime-efficiency.md"
    runtime_json.write_text(
        '{"schema_version":"fitcv_runtime_efficiency_baseline_v3",'
        '"evidence_status":"canonical",'
        '"workload":{"attempted_generation_job_count":1},'
        '"timing":{"generation_elapsed_ms":100,"generation_timing_coverage":{"measured":1,"unavailable":0}},'
        '"selection":{"run_count":1},"material_metrics_sha256":"digest",'
        '"coverage":{"attribution":{"complete":true},"cost":{"complete":true},'
        '"timing":{"complete":true},"page_fit":{"complete":false},'
        '"page_fit_success":{"complete":true},'
        '"review_questions":{"complete":true},"human_actions":{"complete":true},'
        '"resolution_reuse":{"complete":true}},'
        '"run_job_diversity":{"run_count":1,"job_type_count":1}}',
        encoding="utf-8",
    )
    runtime_markdown.write_text("Evidence status: `canonical`", encoding="utf-8")

    result = _run_runtime_efficiency_evidence_check(state, tmp_path)

    assert result["passed"] is False
    assert result["measurement_eligible"] is False
    assert "page_fit_coverage_incomplete" in result["measurement_gate_reasons"]
    assert "runtime_efficiency_page_fit_coverage_incomplete" in result["failures"]


def test_acceptance_summary_names_failed_priority_and_commit(tmp_path: Path) -> None:
    report = build_acceptance_report(
        _state(tmp_path, freeze="b" * 40),
        repo_root=tmp_path,
        current_commit="c" * 40,
        checks=_checks(False),
    )

    summary = format_acceptance_summary(report)

    assert "FitCV acceptance: FAILED" in summary
    assert "Commit: " + "c" * 40 in summary
    assert "p0_b: blocked" in summary
