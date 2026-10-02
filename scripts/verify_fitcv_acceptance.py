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
except ModuleNotFoundError:
    from render_acceptance_state import _validate_state


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = REPO_ROOT / "config/acceptance_state.yaml"
DEFAULT_OUTPUT = REPO_ROOT / ".tmp/fitcv-acceptance-report.json"
CHECKS = {
    "p0_b": [
        "tests/test_p0b_source_job_relevance_evaluator.py",
        "tests/test_calibrate_p0b_recovery.py",
        "tests/test_p0b_support_oracle.py",
    ],
    "p0_c": ["tests/test_evidence.py", "tests/test_agentic_cv_analysis.py"],
    "p1_b": [
        "tests/test_fitcv_cp/test_run_artifact_contracts.py",
        "tests/test_fitcv_cp/test_worker_job.py",
        "tests/test_fitcv_cp/test_sqlite_store.py",
        "tests/test_fitcv_cp/test_app.py",
    ],
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
            "measurement_status": str(check.get("measurement_status") or "not_run"),
            "evidence_paths": list(check.get("evidence_paths") or []),
            "failure_reasons": sorted(set(reasons)),
        }

    for priority in ("p0_a", "p1_a", "p1_c", "p2"):
        status = statuses.get(priority)
        priorities[priority] = {
            "implementation_status": "not_in_scope" if status in {"rejected", "deferred"} else status,
            "acceptance_status": status,
            "measurement_status": "not_applicable" if status in {"rejected", "deferred"} else "not_run",
            "evidence_paths": [],
            "failure_reasons": [],
        }

    return {
        "schema_version": "fitcv.acceptance_report.v1",
        "repository": state.get("repository"),
        "current_commit": current_commit,
        "evaluation_freeze_commit": state.get("evaluation_freeze_commit"),
        "priorities": priorities,
        "failures": sorted(set(failures)),
        "passed": not failures,
    }


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
    report = build_acceptance_report(
        state,
        repo_root=repo_root,
        current_commit=_head(repo_root),
        checks=checks,
    )
    report["checks"] = checks
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
