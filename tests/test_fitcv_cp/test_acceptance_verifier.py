from __future__ import annotations

from pathlib import Path

from scripts.verify_fitcv_acceptance import build_acceptance_report, format_acceptance_summary


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
