from __future__ import annotations

from pathlib import Path

from scripts.verify_fitcv_acceptance import build_acceptance_report


def _state(tmp_path: Path, *, freeze: str = "a" * 40) -> dict[str, object]:
    manifest = tmp_path / "manifest.json"
    evidence = tmp_path / "evidence.md"
    manifest.write_text("{}", encoding="utf-8")
    evidence.write_text("evidence", encoding="utf-8")
    return {
        "schema_version": "fitcv.acceptance_state.v2",
        "repository": "longdang193/fitcv",
        "evaluation_freeze_commit": freeze,
        "sanitizer_version": "fitcv-p0-corpus-sanitizer.v1",
        "contract_versions": {"corpus": "p0.public.v1"},
        "corpus_manifests": ["manifest.json"],
        "evidence_paths": ["evidence.md"],
        "statuses": {
            "p0_a": "rejected",
            "p0_b": "passed",
            "p0_c": "passed",
            "p1_a": "maintenance_only",
            "p1_b": "passed",
            "p1_c": "deferred",
            "p2": "deferred",
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


def test_acceptance_verifier_rejects_stale_passed_claims(tmp_path: Path) -> None:
    report = build_acceptance_report(
        _state(tmp_path),
        repo_root=tmp_path,
        current_commit="b" * 40,
        checks=_checks(),
    )

    assert report["passed"] is False
    assert "evaluation_freeze_commit_stale" in report["failures"]
    assert report["priorities"]["p0_b"]["acceptance_status"] == "blocked"


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
