"""Verify FitCV acceptance claims against current local evidence."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

try:
    from scripts.render_acceptance_state import _validate_state
    from scripts.benchmark_cv_efficiency import material_report_digest
except ModuleNotFoundError:
    from render_acceptance_state import _validate_state
    from benchmark_cv_efficiency import material_report_digest


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
P0B_ORACLE = "data/fitcv-p0-corpus/p0b/p0b_source_job_support_oracle_v1.jsonl"


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
    if int(accepted_cv.get("accepted_non_one_page_count") or 0):
        measurement_gate_reasons.append("accepted_non_one_page_artifacts_present")
    measurement_eligible = not measurement_gate_reasons
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
    for priority in ("p0_b", "p0_c", "p1_b"):
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

    for priority in ("p0_a", "p1_a", "p1_c", "p2"):
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
        if priority in {"p0_b", "p0_c", "p1_b"}:
            lines.append(
                f"{priority}: {details.get('acceptance_status')}"
                + (f" ({', '.join(details.get('failure_reasons') or [])})" if details.get("failure_reasons") else "")
            )
    failures = list(report.get("failures") or [])
    if failures:
        lines.append(f"Failures: {', '.join(failures)}")
    return "\n".join(lines)


def verify_acceptance(
    *,
    state_path: Path = DEFAULT_STATE,
    output_path: Path = DEFAULT_OUTPUT,
    repo_root: Path = REPO_ROOT,
    timeout_seconds: int = 180,
) -> dict[str, Any]:
    state = yaml.safe_load(state_path.read_text(encoding="utf-8")) or {}
    checks = {
        priority: _run_check(repo_root, paths, timeout_seconds)
        for priority, paths in CHECKS.items()
    }
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
    report = build_acceptance_report(
        state,
        repo_root=repo_root,
        current_commit=_head(repo_root),
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
    args = parser.parse_args()
    report = verify_acceptance(
        state_path=args.state,
        output_path=args.output,
        timeout_seconds=args.timeout_seconds,
    )
    print(format_acceptance_summary(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
