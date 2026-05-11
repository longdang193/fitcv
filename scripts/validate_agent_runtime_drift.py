"""
@meta
name: validate_agent_runtime_drift
type: script
domain: validation
responsibility:
  - Validate drift across generated agent artifacts and deployed runtime targets.
  - Execute adapter sync and deploy-runtime checks in deterministic validation order.
inputs:
  - Repo root with scripts and generated adapter artifacts
  - Optional deploy drift skip flag
outputs:
  - Exit status and drift validation diagnostics
lifecycle:
  status: active
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate generated/deployed agent runtime drift.")
    parser.add_argument("--repo-root", default=str(repo_root()))
    parser.add_argument(
        "--skip-deploy-check",
        action="store_true",
        help="Skip home-directory deploy drift checks.",
    )
    return parser.parse_args()


def _run(command: list[str], cwd: Path) -> int:
    print("> " + " ".join(command))
    return subprocess.run(command, cwd=cwd, check=False).returncode


def main() -> int:
    args = parse_args()
    root = Path(args.repo_root).resolve()
    py = sys.executable
    steps = [
        [py, str(root / "scripts" / "sync_agent_adapters.py"), "--check"],
    ]
    if not args.skip_deploy_check:
        steps.append([py, str(root / "scripts" / "deploy_agent_runtime.py"), "--target", "all", "--check"])
    failures = 0
    for step in steps:
        failures += _run(step, root)
    if failures:
        print("Agent runtime drift validation failed.")
        return 1
    print("Agent runtime drift validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
