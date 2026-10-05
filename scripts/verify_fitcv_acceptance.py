"""Verify FitCV acceptance claims against current local evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

try:
    from scripts.render_acceptance_state import _validate_state
    from scripts.benchmark_cv_efficiency import material_report_digest
    from scripts.run_fitcv_repair_experiment import DECLARED_INPUTS
except ModuleNotFoundError:
    from render_acceptance_state import _validate_state
    from benchmark_cv_efficiency import material_report_digest
    from run_fitcv_repair_experiment import DECLARED_INPUTS

from fitcv_cp.run_artifact_contracts import (
    FINAL_ARTIFACT_CONTRACT_VERSION,
    TRACE_CONTRACT_VERSION,
)
from fitcv.contracts import EFFICIENCY_CONTRACT_VERSION


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = REPO_ROOT / "config/acceptance_state.yaml"
DEFAULT_OUTPUT = REPO_ROOT / ".tmp/fitcv-acceptance-report.json"
CHECKS = {
    "p0_b": [
        "tests/test_p0b_source_job_relevance_evaluator.py",
    ],
    "p0_c": ["tests/test_evidence.py"],
    "p1_b": ["tests/test_fitcv_cp/test_run_artifact_contracts.py"],
}


def _canonical_file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
P0B_ORACLE = "data/fitcv-p0-corpus/p0b/p0b_source_job_support_oracle_v1.jsonl"


def _current_experiment_input_identity(repo_root: Path) -> tuple[str | None, str | None]:
    fixture = repo_root / "tests/fixtures/fitcv-p1ab-repair-experiment.json"
    paths = sorted(set(DECLARED_INPUTS) | {"tests/fixtures/fitcv-p1ab-repair-experiment.json"})
    if not fixture.is_file():
        return None, None
    available_paths = [relative for relative in paths if (repo_root / relative).is_file()]
    if len(available_paths) != len(paths):
        return _canonical_file_digest(fixture), None
    digest = hashlib.sha256()
    for relative in available_paths:
        path = repo_root / relative
        digest.update(relative.replace("\\", "/").encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return _canonical_file_digest(fixture), digest.hexdigest()


def _normalized_analysis_input_identity(report: dict[str, Any]) -> tuple[str, ...] | None:
    identities = report.get("analysis_input_identity")
    if not isinstance(identities, list) or not identities:
        return None
    normalized: list[str] = []
    for identity in identities:
        if not isinstance(identity, dict):
            return None
        normalized.append(
            json.dumps(
                {
                    "fingerprints": sorted(str(value) for value in identity.get("fingerprints") or []),
                    "selected_evidence_ids": sorted(
                        str(value) for value in identity.get("selected_evidence_ids") or []
                    ),
                    "job_types": sorted(str(value) for value in identity.get("job_types") or []),
                },
                sort_keys=True,
            )
        )
    return tuple(sorted(normalized))


def _source_inputs_match_current(source_commit: Any, current_commit: str | None, repo_root: Path) -> bool:
    if not isinstance(source_commit, str) or not source_commit.strip():
        return False
    completed = subprocess.run(
        ["git", "diff", "--quiet", source_commit, "--", *DECLARED_INPUTS],
        cwd=repo_root,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return completed.returncode == 0


def _head(repo_root: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, text=True
    ).strip()


def _run_check(repo_root: Path, paths: list[str], timeout_seconds: int) -> dict[str, Any]:
    command = [sys.executable, "-m", "pytest", "-q", *paths]
    try:
        result = subprocess.run(
            command,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"passed": False, "command": command, "reason": "timeout"}
    return {
        "passed": result.returncode == 0,
        "command": command,
        "returncode": result.returncode,
        "stdout_tail": result.stdout[-2000:],
        "stderr_tail": result.stderr[-2000:],
    }


def _run_runtime_check(repo_root: Path, output_path: Path, timeout_seconds: int) -> dict[str, Any]:
    command = [
        sys.executable,
        "scripts/evaluate_p0b_source_job_relevance.py",
        "--oracle",
        P0B_ORACLE,
        "--output",
        str(output_path),
    ]
    try:
        result = subprocess.run(
            command,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"passed": False, "command": command, "reason": "timeout"}
    report = {}
    if output_path.is_file():
        try:
            report = json.loads(output_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            report = {"status": "invalid_report"}
    passed = result.returncode == 0 and bool(report.get("eligible"))
    return {
        "passed": passed,
        "command": command,
        "returncode": result.returncode,
        "eligible": bool(report.get("eligible")),
        "status": report.get("status"),
        "metrics": report.get("metrics", {}),
        "gates": report.get("gates", {}),
        "stdout_tail": result.stdout[-1000:],
        "stderr_tail": result.stderr[-1000:],
    }


def _run_runtime_efficiency_evidence_check(
    state: dict[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    runtime_efficiency = dict(state.get("runtime_efficiency") or {})
    evidence = dict(runtime_efficiency.get("baseline_evidence") or {})
    json_path = repo_root / str(evidence.get("json") or "")
    markdown_path = repo_root / str(evidence.get("markdown") or "")
    failures: list[str] = []
    report: dict[str, Any] = {}
    analysis_input_identity: tuple[str, ...] | None = None
    if not json_path.is_file():
        failures.append("runtime_efficiency_json_missing")
    else:
        try:
            report = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            failures.append("runtime_efficiency_json_invalid")
    if not markdown_path.is_file():
        failures.append("runtime_efficiency_markdown_missing")
    else:
        markdown = markdown_path.read_text(encoding="utf-8")
        if "Evidence status: `canonical`" not in markdown:
            failures.append("runtime_efficiency_markdown_not_canonical")
    if isinstance(report, dict):
        if report.get("schema_version") != "fitcv_runtime_efficiency_baseline_v3":
            failures.append("runtime_efficiency_schema_not_v3")
        if report.get("evidence_status") != "canonical":
            failures.append("runtime_efficiency_json_not_canonical")
        workload = dict(report.get("workload") or {})
        timing = dict(report.get("timing") or {})
        coverage = dict(timing.get("generation_timing_coverage") or {})
        attempted = int(workload.get("attempted_generation_job_count") or 0)
        measured = int(coverage.get("measured") or 0)
        unavailable = int(coverage.get("unavailable") or 0)
        if measured + unavailable != attempted:
            failures.append("runtime_efficiency_timing_coverage_mismatch")
        if measured == 0 and timing.get("generation_elapsed_ms") is not None:
            failures.append("runtime_efficiency_unknown_timing_not_null")
        if measured > 0 and timing.get("generation_elapsed_ms") is None:
            failures.append("runtime_efficiency_measured_timing_missing")
        if not str(report.get("material_metrics_sha256") or "").strip():
            failures.append("runtime_efficiency_material_digest_missing")
        elif report.get("material_metrics_sha256") != material_report_digest(report):
            failures.append("runtime_efficiency_material_digest_mismatch")
    coverage = dict(report.get("coverage") or {}) if isinstance(report, dict) else {}
    accepted_cv = dict(report.get("accepted_cv") or {}) if isinstance(report, dict) else {}
    attribution = dict(report.get("attribution") or {}) if isinstance(report, dict) else {}
    normalization = dict(report.get("trace_normalization") or {}) if isinstance(report, dict) else {}
    diversity = dict(report.get("run_job_diversity") or {}) if isinstance(report, dict) else {}
    outcomes = dict(report.get("outcomes") or {}) if isinstance(report, dict) else {}
    measurement_gate_reasons: list[str] = []
    for name, reason in (
        ("attribution", "attribution_coverage_incomplete"),
        ("cost", "cost_coverage_incomplete"),
        ("timing", "timing_coverage_incomplete"),
        ("page_fit_coverage", "page_fit_coverage_incomplete"),
        ("page_fit_success", "page_fit_success_coverage_incomplete"),
        ("review_questions", "review_questions_coverage_incomplete"),
        ("human_actions", "human_actions_coverage_incomplete"),
        ("resolution_reuse", "resolution_reuse_coverage_incomplete"),
    ):
        details = dict(coverage.get(name) or {})
        if name == "page_fit_coverage" and not details:
            details = dict(coverage.get("page_fit") or {})
        if not details.get("complete"):
            measurement_gate_reasons.append(reason)
    if int(diversity.get("run_count") or 0) < 2:
        measurement_gate_reasons.append("run_diversity_insufficient")
    if int(diversity.get("job_type_count") or 0) < 2:
        measurement_gate_reasons.append("job_type_diversity_insufficient")
    if int(normalization.get("conflict_count") or 0):
        measurement_gate_reasons.append("trace_conflicts_present")
    if int(attribution.get("unmatched_trace_count") or 0):
        measurement_gate_reasons.append("unmatched_traces_present")
    if int(attribution.get("unattributed_accepted_artifact_count") or 0):
        measurement_gate_reasons.append("unattributed_accepted_artifacts_present")
    selection = dict(report.get("selection") or {}) if isinstance(report, dict) else {}
    if int(selection.get("historical_record_count") or 0):
        measurement_gate_reasons.append("historical_contract_records_present")
    if int(selection.get("current_contract_record_count") or 0) == 0:
        measurement_gate_reasons.append("current_contract_records_missing")
    if int(accepted_cv.get("accepted_non_one_page_count") or 0):
        measurement_gate_reasons.append("accepted_non_one_page_artifacts_present")
    page_fit_success = dict(coverage.get("page_fit_success") or {})
    page_fit_outcome = dict(outcomes.get("page_fit") or {})
    if page_fit_success.get("complete") and int(page_fit_success.get("total") or 0) > 0:
        if int(page_fit_outcome.get("fail") or page_fit_success.get("fail") or 0) > 0:
            measurement_gate_reasons.append("page_fit_success_not_perfect")
        elif int(page_fit_outcome.get("pass") or page_fit_success.get("pass") or 0) != int(page_fit_success.get("total") or 0):
            measurement_gate_reasons.append("page_fit_success_outcome_mismatch")
    measurement_eligible = not measurement_gate_reasons
    if runtime_efficiency.get("measurement_status") == "measured":
        expected_versions = {
            "final_artifact": FINAL_ARTIFACT_CONTRACT_VERSION,
            "trace": TRACE_CONTRACT_VERSION,
            "efficiency": EFFICIENCY_CONTRACT_VERSION,
        }
        if dict(report.get("contract_versions") or {}) != expected_versions:
            measurement_gate_reasons.append("current_contract_versions_missing_or_mismatched")
            measurement_eligible = False
    if runtime_efficiency.get("measurement_status") == "measured" and not measurement_eligible:
        failures.extend(f"runtime_efficiency_{reason}" for reason in measurement_gate_reasons)
    return {
        "passed": not failures,
        "evidence_json": str(json_path),
        "evidence_markdown": str(markdown_path),
        "failures": failures,
        "run_count": dict(report.get("selection") or {}).get("run_count", 0),
        "measurement_status": runtime_efficiency.get("measurement_status"),
        "measurement_eligible": measurement_eligible,
        "measurement_gate_reasons": measurement_gate_reasons,
    }


def _run_current_contract_evidence_check(
    state: dict[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    references = dict(state.get("current_contract_evidence") or {})
    json_path = repo_root / str(references.get("json") or "")
    markdown_path = repo_root / str(references.get("markdown") or "")
    digest_path = repo_root / str(references.get("sha256") or "")
    failures: list[str] = []
    evidence: dict[str, Any] = {}
    if not json_path.is_file():
        failures.append("current_contract_evidence_json_missing")
    else:
        try:
            evidence = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            failures.append("current_contract_evidence_json_invalid")
    if not markdown_path.is_file():
        failures.append("current_contract_evidence_markdown_missing")
    elif "Evidence status: `canonical`" not in markdown_path.read_text(encoding="utf-8"):
        failures.append("current_contract_evidence_markdown_not_canonical")
    if not digest_path.is_file():
        failures.append("current_contract_evidence_digest_missing")
    else:
        digest_line = digest_path.read_text(encoding="utf-8").strip().split()
        actual_digest = _canonical_file_digest(json_path) if json_path.is_file() else ""
        if len(digest_line) != 2 or digest_line[0] != actual_digest or digest_line[1] != json_path.name:
            failures.append("current_contract_evidence_digest_mismatch")
    if isinstance(evidence, dict):
        if evidence.get("evidence_status") != "canonical":
            failures.append("current_contract_evidence_not_canonical")
        if evidence.get("evidence_schema_version") != "fitcv.p1_ab.current_contract.v1":
            failures.append("current_contract_evidence_schema_invalid")
        if not isinstance(evidence.get("source_commit"), str) or len(evidence["source_commit"]) != 40:
            failures.append("current_contract_evidence_source_commit_invalid")
        for name in ("fixture_sha256", "source_fixture_sha256"):
            if not isinstance(evidence.get(name), str) or len(evidence[name]) != 64:
                failures.append(f"current_contract_evidence_{name}_invalid")
        if "input_manifest" in evidence:
            current_fixture_sha256, current_declared_input_fingerprint = _current_experiment_input_identity(repo_root)
            input_manifest = dict(evidence.get("input_manifest") or {})
            if current_fixture_sha256 is None:
                failures.append("current_contract_evidence_inputs_unavailable")
            else:
                if evidence.get("fixture_sha256") != current_fixture_sha256:
                    failures.append("current_contract_evidence_fixture_sha256_not_current")
                if (
                    current_declared_input_fingerprint is not None
                    and input_manifest.get("declared_input_fingerprint") != current_declared_input_fingerprint
                ):
                    failures.append("current_contract_evidence_declared_input_fingerprint_not_current")
        selection = dict(evidence.get("selection") or {})
        if int(selection.get("current_contract_record_count") or 0) <= 0:
            failures.append("current_contract_evidence_has_no_current_records")
        if int(selection.get("historical_record_count") or 0):
            failures.append("current_contract_evidence_contains_historical_records")
        workload = dict(evidence.get("workload") or {})
        outcomes = [record for record in list(evidence.get("attempted_outcomes") or []) if isinstance(record, dict)]
        if int(workload.get("attempted_generation_job_count") or 0) != len(outcomes):
            failures.append("current_contract_evidence_outcomes_incomplete")
        accepted = dict(evidence.get("accepted_cv") or {})
        page_fit = dict(accepted.get("page_fit_success") or {})
        coverage = dict(evidence.get("coverage") or {})
        if int(accepted.get("count") or 0) <= 0:
            failures.append("current_contract_evidence_no_accepted_cv")
        if not bool(coverage.get("page_fit", {}).get("complete")):
            failures.append("current_contract_evidence_page_fit_coverage_incomplete")
        if not bool(coverage.get("page_fit_success", {}).get("complete")):
            failures.append("current_contract_evidence_page_fit_success_incomplete")
        if int(page_fit.get("fail") or 0) != 0 or int(accepted.get("accepted_non_one_page_count") or 0) != 0:
            failures.append("current_contract_evidence_non_one_page_accepted")
        attribution = dict(evidence.get("attribution") or {})
        if int(attribution.get("unattributed_accepted_artifact_count") or 0) != 0:
            failures.append("current_contract_evidence_unattributed_acceptance")
    return {
        "passed": not failures,
        "evidence_json": str(json_path),
        "evidence_markdown": str(markdown_path),
        "evidence_digest": str(digest_path),
        "failures": failures,
        "accepted_count": int(dict(evidence.get("accepted_cv") or {}).get("count") or 0) if isinstance(evidence, dict) else 0,
    }


def build_acceptance_report(
    state: dict[str, Any],
    *,
    repo_root: Path,
    current_commit: str,
    checks: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    failures: list[str] = []
    try:
        _validate_state(state, repo_root)
    except (ValueError, OSError) as exc:
        failures.append(f"acceptance_state_invalid:{exc}")

    statuses = dict(state.get("statuses") or {})
    status_dimensions = dict(state.get("status_dimensions") or {})
    runtime_efficiency = dict(state.get("runtime_efficiency") or {})
    if (
        runtime_efficiency.get("measurement_status") == "measured"
        and dict(status_dimensions.get("p1_b") or {}).get("measurement_status") != "measured"
    ):
        failures.append("runtime_efficiency_measured_without_p1_b_measurement")
    priorities: dict[str, dict[str, Any]] = {}
    for priority in ("p0_b", "p0_c", "p1_a", "p1_b"):
        check = dict(checks.get(priority) or {})
        claimed = statuses.get(priority)
        passed = bool(check.get("passed"))
        reasons = list(check.get("reasons") or [])
        if claimed == "passed" and not passed:
            reasons.append("passed_claim_without_fresh_evidence")
            failures.append(f"{priority}_passed_claim_not_proven")
        priorities[priority] = {
            "implementation_status": "verified" if passed else "unverified",
            "acceptance_status": "passed" if claimed == "passed" and passed else "blocked",
            "measurement_status": str(
                check.get("measurement_status")
                or dict(status_dimensions.get(priority) or {}).get("measurement_status")
                or "not_run"
            ),
            "evidence_paths": list(check.get("evidence_paths") or []),
            "failure_reasons": sorted(set(reasons)),
        }

    for priority in ("p0_a", "p1_c", "p2"):
        status = statuses.get(priority)
        declared = dict(status_dimensions.get(priority) or {})
        priorities[priority] = {
            "implementation_status": declared.get(
                "implementation_status",
                "not_in_scope" if status in {"rejected", "deferred"} else status,
            ),
            "acceptance_status": declared.get("acceptance_status", status),
            "measurement_status": declared.get(
                "measurement_status",
                "not_applicable" if status in {"rejected", "deferred"} else "not_run",
            ),
            "evidence_paths": [],
            "failure_reasons": [],
        }

    return {
        "schema_version": "fitcv.acceptance_report.v1",
        "repository": state.get("repository"),
        "current_commit": current_commit,
        "evaluation_freeze_commit": state.get("evaluation_freeze_commit"),
        "runtime_efficiency": runtime_efficiency,
        "priorities": priorities,
        "failures": sorted(set(failures)),
        "passed": not failures,
    }


def format_acceptance_summary(report: dict[str, Any]) -> str:
    status = "PASSED" if report.get("passed") else "FAILED"
    lines = [
        f"FitCV acceptance: {status}",
        f"Commit: {report.get('current_commit') or 'unknown'}",
    ]
    for priority, details in sorted(dict(report.get("priorities") or {}).items()):
        if priority in {"p0_b", "p0_c", "p1_a", "p1_b"}:
            lines.append(
                f"{priority}: {details.get('acceptance_status')}"
                + (f" ({', '.join(details.get('failure_reasons') or [])})" if details.get("failure_reasons") else "")
            )
    failures = list(report.get("failures") or [])
    if failures:
        lines.append(f"Failures: {', '.join(failures)}")
    return "\n".join(lines)


def _run_experiment_report_check(
    experiment_json: Path | None,
    experiment_markdown: Path | None,
    repo_root: Path,
    peer_experiment_json: Path | None = None,
    current_commit: str | None = None,
    require_peer: bool = True,
) -> dict[str, Any]:
    if experiment_json is None and experiment_markdown is None:
        return {"passed": True, "status": "not_requested", "failures": []}
    failures: list[str] = []
    report: dict[str, Any] = {}
    persisted_manifest: dict[str, Any] = {}
    current_fixture_sha256, current_declared_input_fingerprint = _current_experiment_input_identity(repo_root)
    if experiment_json is None or not experiment_json.is_file():
        failures.append("experiment_json_missing")
    else:
        try:
            report = json.loads(experiment_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            failures.append("experiment_json_invalid")
    if experiment_markdown is None or not experiment_markdown.is_file():
        failures.append("experiment_markdown_missing")
    else:
        text = experiment_markdown.read_text(encoding="utf-8")
        for heading in ("CORRECTNESS", "PRODUCT PARITY", "EFFICIENCY", "HUMAN EFFORT"):
            if f"## {heading}" not in text:
                failures.append(f"experiment_markdown_missing_{heading.lower().replace(' ', '_')}")
    if not isinstance(report, dict):
        failures.append("experiment_json_object_required")
    if isinstance(report, dict):
        analysis_input_identity = _normalized_analysis_input_identity(report)
        if analysis_input_identity is None:
            failures.append("experiment_analysis_input_identity_missing")
        selection = dict(report.get("selection") or {})
        if str(report.get("status") or "") != "complete":
            failures.append("experiment_report_incomplete")
        manifest = dict(report.get("input_manifest") or {})
        manifest_run_ids = [str(value).strip() for value in list(manifest.get("run_ids") or []) if str(value).strip()]
        if int(manifest.get("repeat_count") or 0) != 10:
            failures.append("experiment_manifest_repeat_count_invalid")
        if len(manifest_run_ids) != 10 or len(set(manifest_run_ids)) != 10:
            failures.append("experiment_manifest_run_ids_invalid")
        run_count = int(selection.get("run_count") or 0)
        if run_count != 10:
            failures.append("experiment_run_count_invalid")
        if int(selection.get("manifest_run_count_shortfall") or 0) != 0:
            failures.append("experiment_manifest_shortfall")
        current_records = int(selection.get("current_contract_record_count") or 0)
        recorded_acceptance = int(dict(report.get("accepted_cv") or {}).get("recorded_acceptance_count") or 0)
        if current_records == 0 or current_records < recorded_acceptance:
            failures.append("experiment_current_contract_missing")
        coverage = dict(report.get("coverage") or {})
        for name in ("timing", "cost", "attribution", "page_fit", "page_fit_success", "review_questions", "human_actions", "resolution_reuse"):
            if not bool(dict(coverage.get(name) or {}).get("complete")):
                failures.append(f"experiment_coverage_incomplete_{name}")
        timing = dict(report.get("timing") or {})
        generation_elapsed = float(timing.get("generation_elapsed_ms") or 0)
        generation_coverage = dict(timing.get("generation_timing_coverage") or {})
        if generation_elapsed <= 0 or int(generation_coverage.get("measured") or 0) < run_count:
            failures.append("experiment_generation_timing_incomplete")
        diversity = dict(report.get("run_job_diversity") or {})
        if int(diversity.get("run_count") or 0) != 10 or int(diversity.get("job_type_count") or 0) < 2:
            failures.append("experiment_job_diversity_insufficient")
        if not manifest.get("declared_input_fingerprint"):
            failures.append("experiment_input_fingerprint_missing")
        if not manifest.get("fixture_sha256"):
            failures.append("experiment_fixture_hash_missing")
        if not manifest.get("arm"):
            failures.append("experiment_arm_missing")
        manifest_path = manifest.get("path")
        if not manifest_path:
            failures.append("experiment_manifest_path_missing")
        else:
            manifest_file = Path(str(manifest_path))
            if not manifest_file.is_absolute():
                manifest_file = repo_root / manifest_file
            try:
                persisted_manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                failures.append("experiment_manifest_unreadable")
            else:
                for field in ("fixture_sha256", "declared_input_fingerprint", "arm", "repeat_count", "database_path", "declared_model", "resolved_models"):
                    if persisted_manifest.get(field) != manifest.get(field):
                        failures.append(f"experiment_manifest_{field}_mismatch")
                if set(str(value) for value in persisted_manifest.get("run_ids") or []) != set(manifest_run_ids):
                    failures.append("experiment_manifest_run_ids_mismatch")
                if set(str(value) for value in selection.get("run_ids") or []) != set(manifest_run_ids):
                    failures.append("experiment_selection_run_ids_mismatch")
                if current_commit and not _source_inputs_match_current(
                    persisted_manifest.get("source_commit"), current_commit, repo_root
                ):
                    failures.append("experiment_source_commit_not_current")
                if current_fixture_sha256 is None or current_declared_input_fingerprint is None:
                    failures.append("experiment_current_declared_inputs_unavailable")
                else:
                    if persisted_manifest.get("fixture_sha256") != current_fixture_sha256:
                        failures.append("experiment_fixture_sha256_not_current")
                    if persisted_manifest.get("declared_input_fingerprint") != current_declared_input_fingerprint:
                        failures.append("experiment_declared_input_fingerprint_not_current")
                if dict(persisted_manifest.get("producer") or {}).get("mode") != "provider_backed":
                    failures.append("experiment_provider_backed_required")
                if not isinstance(persisted_manifest.get("cohort_setup"), dict):
                    failures.append("experiment_cohort_setup_missing")
        if report.get("material_metrics_sha256") != material_report_digest(report):
            failures.append("experiment_material_digest_mismatch")
        if peer_experiment_json is None and require_peer:
            failures.append("experiment_peer_json_required")
        elif peer_experiment_json is not None:
            try:
                peer_report = json.loads(peer_experiment_json.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                failures.append("experiment_peer_json_invalid")
            else:
                if not isinstance(peer_report, dict):
                    failures.append("experiment_peer_json_object_required")
                else:
                    peer_analysis_input_identity = _normalized_analysis_input_identity(peer_report)
                    if analysis_input_identity is None:
                        failures.append("experiment_analysis_input_identity_missing")
                    elif peer_analysis_input_identity is None:
                        failures.append("experiment_peer_analysis_input_identity_missing")
                    elif analysis_input_identity != peer_analysis_input_identity:
                        failures.append("experiment_peer_analysis_input_identity_not_identical")
                    peer_validation = _run_experiment_report_check(
                        peer_experiment_json,
                        experiment_markdown,
                        repo_root,
                        current_commit=current_commit,
                        require_peer=False,
                    )
                    failures.extend(
                        f"experiment_peer_{failure.removeprefix('experiment_')}"
                        for failure in peer_validation["failures"]
                    )
                    peer_manifest = dict(peer_report.get("input_manifest") or {})
                    peer_manifest_path = peer_manifest.get("path")
                    persisted_peer_manifest: dict[str, Any] = {}
                    if not peer_manifest_path:
                        failures.append("experiment_peer_manifest_path_missing")
                    else:
                        peer_manifest_file = Path(str(peer_manifest_path))
                        if not peer_manifest_file.is_absolute():
                            peer_manifest_file = repo_root / peer_manifest_file
                        try:
                            persisted_peer_manifest = json.loads(peer_manifest_file.read_text(encoding="utf-8"))
                        except (OSError, json.JSONDecodeError):
                            failures.append("experiment_peer_manifest_unreadable")
                    if persisted_manifest and persisted_peer_manifest:
                        if persisted_manifest.get("arm") == persisted_peer_manifest.get("arm"):
                            failures.append("experiment_peer_arm_must_differ")
                        if {persisted_manifest.get("arm"), persisted_peer_manifest.get("arm")} != {"local_first", "provider_first"}:
                            failures.append("experiment_peer_arms_invalid")
                        for field in (
                            "fixture_sha256",
                            "declared_input_fingerprint",
                            "repeat_count",
                            "declared_model",
                            "resolved_models",
                            "runtime",
                            "source_commit",
                            "working_tree_diff_sha256",
                            "producer",
                            "cohort_setup",
                        ):
                            if persisted_manifest.get(field) != persisted_peer_manifest.get(field):
                                failures.append(f"experiment_peer_{field}_not_identical")
                        if current_commit and not _source_inputs_match_current(
                            persisted_peer_manifest.get("source_commit"), current_commit, repo_root
                        ):
                            failures.append("experiment_peer_source_commit_not_current")
                        if dict(persisted_peer_manifest.get("producer") or {}).get("mode") != "provider_backed":
                            failures.append("experiment_peer_provider_backed_required")
    return {
        "passed": not failures,
        "status": "checked",
        "failures": sorted(set(failures)),
        "experiment_json": str(experiment_json) if experiment_json else None,
        "experiment_markdown": str(experiment_markdown) if experiment_markdown else None,
    }


def verify_acceptance(
    *,
    state_path: Path = DEFAULT_STATE,
    output_path: Path = DEFAULT_OUTPUT,
    repo_root: Path = REPO_ROOT,
    timeout_seconds: int = 180,
    experiment_json: Path | None = None,
    experiment_markdown: Path | None = None,
    experiment_peer_json: Path | None = None,
) -> dict[str, Any]:
    state = yaml.safe_load(state_path.read_text(encoding="utf-8")) or {}
    current_commit = _head(repo_root)
    checks = {
        priority: _run_check(repo_root, paths, timeout_seconds)
        for priority, paths in CHECKS.items()
    }
    current_contract_check = _run_current_contract_evidence_check(state, repo_root)
    checks["p1_a"] = current_contract_check
    runtime_check = _run_runtime_check(
        repo_root,
        output_path.parent / "p0b-runtime-acceptance-verifier.json",
        timeout_seconds,
    )
    checks["p0_b"]["passed"] = checks["p0_b"]["passed"] and runtime_check["passed"]
    checks["p0_b"]["runtime"] = runtime_check
    efficiency_check = _run_runtime_efficiency_evidence_check(state, repo_root)
    checks["p1_b"]["passed"] = checks["p1_b"]["passed"] and efficiency_check["passed"]
    checks["p1_b"]["runtime_efficiency"] = efficiency_check
    experiment_check = _run_experiment_report_check(
        experiment_json,
        experiment_markdown,
        repo_root,
        experiment_peer_json,
        current_commit,
    )
    checks["p1_b"]["experiment"] = experiment_check
    checks["p1_b"]["passed"] = checks["p1_b"]["passed"] and experiment_check["passed"]
    report = build_acceptance_report(
        state,
        repo_root=repo_root,
        current_commit=current_commit,
        checks=checks,
    )
    report["checks"] = checks
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--experiment-json", type=Path)
    parser.add_argument("--experiment-markdown", type=Path)
    parser.add_argument("--experiment-peer-json", type=Path)
    args = parser.parse_args()
    report = verify_acceptance(
        state_path=args.state,
        output_path=args.output,
        timeout_seconds=args.timeout_seconds,
        experiment_json=args.experiment_json,
        experiment_markdown=args.experiment_markdown,
        experiment_peer_json=args.experiment_peer_json,
    )
    print(format_acceptance_summary(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
