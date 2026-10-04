"""Validate and manifest an isolated FitCV repair-arm cohort."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "tests/fixtures/fitcv-p1ab-repair-experiment.json"
VALID_ARMS = {"local_first", "provider_first"}
DECLARED_INPUTS = (
    "scripts/run_fitcv_repair_experiment.py",
    "scripts/benchmark_cv_efficiency.py",
    "scripts/verify_fitcv_acceptance.py",
    "scripts/run_fitcv_review_e2e.ps1",
    "scripts/serve_fitcv_review_e2e.py",
    "tests/fixtures/fitcv-p1ab-repair-experiment.json",
    "src/fitcv/agentic_cv_generation.py",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _diff_hash() -> str:
    completed = subprocess.run(["git", "diff", "--binary"], cwd=ROOT, check=True, capture_output=True)
    return hashlib.sha256(completed.stdout).hexdigest()


def _load_fixture(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != "fitcv.p1ab.repair_experiment_fixture.v1":
        raise ValueError("fixture_schema_invalid")
    job_types = list(payload.get("job_types") or [])
    categories = list(payload.get("required_evidence_categories") or [])
    arms = dict(payload.get("arms") or {})
    incumbent = str(arms.get("INCUMBENT_ARM") or "").strip()
    candidate = str(arms.get("CANDIDATE_ARM") or "").strip()
    if len(set(job_types)) < 2:
        raise ValueError("fixture_requires_two_job_types")
    if not categories:
        raise ValueError("fixture_missing_evidence_categories")
    if incumbent not in VALID_ARMS or candidate not in VALID_ARMS:
        raise ValueError("arm_selector_invalid")
    if incumbent == candidate:
        raise ValueError("arm_selectors_identical")
    if int(payload.get("repeat_count") or 0) != 10:
        raise ValueError("repeat_count_must_be_10")
    return payload


def _input_fingerprint(fixture: Path) -> str:
    digest = hashlib.sha256()
    for relative in sorted(set(DECLARED_INPUTS) | {str(fixture.relative_to(ROOT)).replace("\\", "/")}):
        path = ROOT / relative
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def build_manifest(*, fixture: Path, arm: str, database: Path, run_ids: list[str]) -> dict[str, Any]:
    payload = _load_fixture(fixture)
    if arm not in VALID_ARMS:
        raise ValueError("arm_selector_invalid")
    if arm not in set(dict(payload["arms"]).values()):
        raise ValueError("arm_selector_not_declared")
    if len(run_ids) != int(payload["repeat_count"]):
        raise ValueError("run_id_count_must_match_repeat_count")
    if len(set(run_ids)) != len(run_ids):
        raise ValueError("duplicate_run_ids")
    return {
        "schema_version": "fitcv.p1ab.repair_experiment_manifest.v1",
        "fixture": str(fixture.resolve()),
        "fixture_sha256": _sha256(fixture),
        "database_path": str(database.resolve()),
        "arm": arm,
        "repeat_count": len(run_ids),
        "run_ids": run_ids,
        "source_commit": _git("rev-parse", "HEAD"),
        "working_tree_diff_sha256": _diff_hash(),
        "declared_input_fingerprint": _input_fingerprint(fixture),
        "model": payload.get("model"),
        "runtime": payload.get("runtime"),
        "job_types": sorted(str(value) for value in payload["job_types"]),
        "cache_policy": "isolated_per_arm",
        "provider_credentials": "loaded_from_existing_env_or_dotenv_only",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--arm", choices=sorted(VALID_ARMS))
    parser.add_argument("--database", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--run-id", action="append", default=[])
    parser.add_argument("--preflight-fixture", action="store_true")
    args = parser.parse_args()
    fixture = args.fixture.resolve()
    try:
        payload = _load_fixture(fixture)
        if args.preflight_fixture:
            print(json.dumps({
                "status": "eligible_shape",
                "fixture": str(fixture),
                "fixture_sha256": _sha256(fixture),
                "arms": payload["arms"],
                "repeat_count": payload["repeat_count"],
                "job_types": sorted(payload["job_types"]),
                "required_evidence_categories": sorted(payload["required_evidence_categories"]),
            }, indent=2, sort_keys=True))
            return 0
        if not args.arm or not args.database or not args.manifest:
            parser.error("normal run requires --arm, --database, and --manifest")
        manifest = build_manifest(
            fixture=fixture,
            arm=args.arm,
            database=args.database,
            run_ids=[str(value).strip() for value in args.run_id if str(value).strip()],
        )
        args.manifest.resolve().parent.mkdir(parents=True, exist_ok=True)
        args.manifest.resolve().write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"status": "manifested", "manifest": str(args.manifest.resolve()), "arm": args.arm}, sort_keys=True))
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"status": "rejected", "reason": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
