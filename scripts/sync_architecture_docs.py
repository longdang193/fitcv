"""
@meta
name: sync_architecture_docs
type: script
domain: docs
responsibility:
  - Run the canonical architecture metadata sync and verification workflow.
  - Provide one stable entrypoint for contributors to refresh generated architecture docs before repo-wide validation.
  - Keep the wrapper shape aligned with the starter model while delegating generation to the repo-local helper.
inputs:
  - docs/features/*/feature.source.yaml
  - docs/stages/*.source.yaml
  - docs/superpowers/specs/*.md
  - docs/superpowers/plans/*.md
  - config/**/*.yaml
  - Python @meta, @capability, and @proves markers
outputs:
  - docs/features/<feature_id>/<feature_id>.yaml
  - docs/features/<feature_id>/lineage.generated.yaml
  - docs/stages/<stage_id>.yaml
  - docs/generated/capability_lineage.yaml
  - docs/generated/architecture_dag.yaml
tags:
  - docs
  - lineage
  - sync
lifecycle:
  status: active
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


def repo_root(default_root: Path | None = None) -> Path:
    if default_root is not None:
        return default_root
    return Path(__file__).resolve().parents[1]


def build_steps(*, root: Path, check_only: bool, python_executable: str) -> list[list[str]]:
    generator = str(root / "tools" / "docs" / "generate_architecture_metadata.py")
    validator = str(root / "scripts" / "validate_adoption_shape.py")
    steps: list[list[str]] = []
    if not check_only:
        steps.append([python_executable, generator, "--repo-root", str(root)])
    steps.extend(
        [
            [python_executable, validator, "--repo-root", str(root)],
            [python_executable, generator, "--repo-root", str(root), "--check"],
        ]
    )
    return steps


def run_step(command: list[str], *, cwd: Path) -> int:
    rendered = " ".join(command)
    print(f"> {rendered}")
    completed = subprocess.run(command, cwd=cwd, check=False)
    return completed.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the canonical architecture metadata sync and verification workflow."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=repo_root(),
        help="Repository root. Defaults to this script's repository.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run validation and generation checks without rewriting outputs first.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root(args.repo_root).resolve()
    for step in build_steps(root=root, check_only=args.check, python_executable=sys.executable):
        status = run_step(step, cwd=root)
        if status != 0:
            return status
    print(
        "Architecture sync checks passed."
        if args.check
        else "Architecture sync and checks completed. Run scripts/validate_repo_contracts.py for the repo-wide contract gate."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
