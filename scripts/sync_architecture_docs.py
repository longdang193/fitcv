"""
@meta
repo: private
name: sync_architecture_docs
type: script
domain: docs
responsibility:
  - Run the canonical architecture metadata sync and verification workflow.
  - Provide one stable entrypoint for contributors to refresh generated architecture docs before repo-wide validation.
  - Enforce metadata-derived refs for generated feature and stage contracts.
inputs:
  - docs/features/*/feature.source.yaml
  - docs/stages/*.source.yaml
  - docs/superpowers/specs/*.md
  - docs/superpowers/plans/*.md
  - YAML # @architecture metadata in configs and AML components
  - Python @meta, @capability, and @proves markers
outputs:
  - docs/features/<feature_id>/<feature_id>.yaml
  - docs/features/<feature_id>/lineage.generated.yaml
  - docs/features/<feature_id>/history.md
  - docs/stages/<stage_id>.yaml
  - docs/generated/capability_lineage.yaml
  - docs/generated/architecture_dag.yaml
  - Awareness report for disallowed feature-source manual_refs
tags:
  - docs
  - lineage
  - sync
lifecycle:
  status: active
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


def repo_root(repo_override: str | None = None) -> Path:
    if repo_override:
        return Path(repo_override).resolve()
    return Path(__file__).resolve().parents[1]


def pytest_basetemp(default_relative: str) -> str:
    override = os.environ.get("REPO_VALIDATOR_PYTEST_BASETEMP")
    if override:
        return override
    return default_relative


def build_steps(*, root: Path, check_only: bool, python_executable: str, isolated_repo: bool) -> list[list[str]]:
    generator = str(root / "tools" / "docs" / "generate_architecture_metadata.py")
    awareness_audit = str(root / "scripts" / "audit_architecture_linkage.py")
    formatter = str(root / "scripts" / "format_contract_yaml.py")
    adoption_validator = str(root / "scripts" / "validate_adoption_shape.py")
    steps: list[list[str]] = []
    if not check_only:
        steps.append([python_executable, generator])
    if isolated_repo:
        if check_only:
            steps.append([python_executable, generator, "--check"])
        else:
            steps.append([python_executable, formatter])
            steps.append([python_executable, generator, "--validate-only"])
        return steps
    steps.extend(
        [
            [python_executable, adoption_validator],
            [python_executable, generator, "--validate-only"],
            [python_executable, generator, "--check"],
            [python_executable, awareness_audit, "--strict-awareness", "--report-awareness"],
            [python_executable, formatter, "--check"],
            [
                python_executable,
                "-m",
                "pytest",
                "--basetemp",
                pytest_basetemp(".tmp-tests/architecture-pytest"),
                "tests/test_architecture_metadata_generation.py",
                "tests/test_architecture_linkage_audit.py",
                "tests/test_format_contract_yaml.py",
                "tests/test_validate_adoption_shape.py",
                "tests/test_setup_hooks.py",
                "-q",
            ],
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
        "--check",
        action="store_true",
        help="Run validation and verification without rewriting generated outputs first.",
    )
    parser.add_argument(
        "--repo-root",
        help="Optional repository root override (used by tests and isolated validation runs).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root(args.repo_root)
    basetemp = Path(pytest_basetemp(".tmp-tests/architecture-pytest"))
    basetemp_parent = basetemp.parent if basetemp.is_absolute() else (root / basetemp).parent
    basetemp_parent.mkdir(parents=True, exist_ok=True)
    for step in build_steps(
        root=root,
        check_only=args.check,
        python_executable=sys.executable,
        isolated_repo=bool(args.repo_root),
    ):
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
