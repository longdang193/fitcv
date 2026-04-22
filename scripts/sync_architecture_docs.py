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
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def repo_root(default_root: Path | None = None) -> Path:
    if default_root is not None:
        return default_root
    return Path(__file__).resolve().parents[1]


def pytest_basetemp(default_relative: str) -> str:
    override = os.environ.get("REPO_VALIDATOR_PYTEST_BASETEMP")
    if override:
        return override
    normalized = default_relative.replace("/", "-").replace("\\", "-").strip(".-")
    return str(Path(tempfile.gettempdir()) / f"codex-{normalized}-{os.getpid()}")


def venv_site_packages(root: Path) -> Path | None:
    site_packages = root / ".venv" / "Lib" / "site-packages"
    if site_packages.exists():
        return site_packages
    return None


def resolve_python_executable(root: Path) -> str:
    pyvenv_cfg = root / ".venv" / "pyvenv.cfg"
    if pyvenv_cfg.exists():
        for line in pyvenv_cfg.read_text(encoding="utf-8").splitlines():
            if not line.startswith("home = "):
                continue
            home = line.split("=", 1)[1].strip()
            candidate = Path(home) / "python.exe"
            if candidate.exists():
                return str(candidate)
    return sys.executable


def build_steps(*, root: Path, check_only: bool, python_executable: str) -> list[list[str]]:
    generator = str(root / "tools" / "docs" / "generate_architecture_metadata.py")
    awareness_audit = str(root / "scripts" / "audit_architecture_linkage.py")
    formatter = str(root / "scripts" / "format_contract_yaml.py")
    adoption_validator = str(root / "scripts" / "validate_adoption_shape.py")
    steps: list[list[str]] = []
    if not check_only:
        steps.append([python_executable, generator, "--repo-root", str(root)])
    steps.extend(
        [
            [python_executable, adoption_validator, "--repo-root", str(root)],
            [python_executable, generator, "--repo-root", str(root), "--validate-only"],
            [python_executable, generator, "--repo-root", str(root), "--check"],
            [
                python_executable,
                awareness_audit,
                "--repo-root",
                str(root),
                "--strict-awareness",
                "--report-awareness",
            ],
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
    env = os.environ.copy()
    site_packages = venv_site_packages(cwd)
    if site_packages is not None and command and command[0].lower().endswith("python.exe"):
        existing = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            str(site_packages)
            if not existing
            else os.pathsep.join([str(site_packages), existing])
        )
    completed = subprocess.run(command, cwd=cwd, check=False, env=env)
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
    python_executable = resolve_python_executable(root)
    for step in build_steps(root=root, check_only=args.check, python_executable=python_executable):
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
